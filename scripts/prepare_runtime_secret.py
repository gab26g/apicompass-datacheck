"""User-only fresh-install helper: generate runtime JSON directly to clipboard."""
import argparse
import getpass
import json
import secrets
import shutil
import subprocess
import sys
import warnings

try:
    from scripts.runtime_secrets import RuntimeConfigurationError, validate_runtime
except ModuleNotFoundError:
    from runtime_secrets import RuntimeConfigurationError, validate_runtime


class PrivateSetupError(ValueError):
    pass


def generate_runtime(google_key, *, fresh_install=False):
    if fresh_install is not True:
        raise PrivateSetupError('Fresh installation must be explicitly confirmed; never replace existing production keys.')
    value = {name: secrets.token_hex(32) for name in (
        'JWT_SECRET', 'JWT_REFRESH_SECRET', 'CREDS_KEY', 'MONGO_ROOT_PASSWORD',
        'MONGO_APP_PASSWORD', 'DATACHECK_API_TOKEN')}
    value['CREDS_IV'] = secrets.token_hex(16)
    value['GOOGLE_KEY'] = google_key
    # Use the same exact schema and fail-closed checks as production startup.
    try:
        return validate_runtime(json.dumps(value))
    except RuntimeConfigurationError:
        raise PrivateSetupError('The hidden provider key did not pass runtime validation; nothing was copied.') from None


def write_clipboard(payload, *, runner=subprocess.run, executable=None):
    executable = executable or shutil.which('clip.exe')
    if not executable:
        raise PrivateSetupError('Windows clip.exe is unavailable; run this helper in Windows PowerShell.')
    try:
        result = runner([executable], input=payload, stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL, timeout=15, check=False)
    except (OSError, subprocess.SubprocessError):
        raise PrivateSetupError('Clipboard transfer failed; no secret was printed or saved.') from None
    if result.returncode:
        raise PrivateSetupError('Clipboard transfer failed; no secret was printed or saved.')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument('--fresh-install-confirmed', action='store_true')
    actions.add_argument('--clear-clipboard', action='store_true')
    actions.add_argument('--interactive', action='store_true')
    args = parser.parse_args(argv)
    try:
        if args.clear_clipboard:
            # Replace the current clipboard with a blank, not another secret.
            write_clipboard(b' ')
            print('Clipboard replaced with a blank. Clear Windows clipboard history separately if enabled.')
            return 0
        if args.interactive:
            confirmation = input('Fresh installation only; never replace existing production keys. Type FRESH to continue: ')
            if confirmation != 'FRESH':
                raise PrivateSetupError('Cancelled. No credentials generated or copied.')
            # Refuse getpass fallback rather than allow a visible key prompt.
            with warnings.catch_warnings():
                warnings.simplefilter('error', getpass.GetPassWarning)
                try:
                    key = getpass.getpass('Paste Gemini API key (hidden), then press Enter: ')
                except getpass.GetPassWarning:
                    raise PrivateSetupError('Hidden input is unavailable. Run directly in Windows PowerShell.') from None
        else:
            if sys.stdin.isatty():
                raise PrivateSetupError('Use --interactive for hidden key entry in Windows PowerShell.')
            # The optional Bash wizard sends one hidden value without a newline.
            key = sys.stdin.read(4097)
        runtime = generate_runtime(key, fresh_install=args.interactive or args.fresh_install_confirmed)
        payload = json.dumps(runtime, separators=(',', ':'), ensure_ascii=True).encode('ascii')
        if len(payload) > 4096:
            raise PrivateSetupError('Runtime JSON exceeds the Standard parameter size; nothing was copied.')
        write_clipboard(payload)
        print('Copied. Return to prepared AWS tab and paste Value, click Create. Then tell Codex saved.')
        return 0
    except PrivateSetupError as error:
        print(str(error), file=sys.stderr)
        return 1
    except (KeyboardInterrupt, EOFError):
        print('Private setup cancelled. Clear the clipboard if JSON was already copied.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
