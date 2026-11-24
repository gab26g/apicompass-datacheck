"""Private helper checks; clipboard calls are mocked and no real key is used."""
import io
import json
import subprocess
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import Mock, patch

from scripts import prepare_runtime_secret as helper
from scripts.runtime_secrets import REQUIRED, validate_runtime

DUMMY_KEY = 'synthetic-provider-key-never-real'


class PrivateHelperTests(unittest.TestCase):
    def test_fresh_gate_and_valid_exact_random_schema(self):
        with self.assertRaises(helper.PrivateSetupError):
            helper.generate_runtime(DUMMY_KEY)
        first = helper.generate_runtime(DUMMY_KEY, fresh_install=True)
        second = helper.generate_runtime(DUMMY_KEY, fresh_install=True)
        self.assertEqual(set(first), REQUIRED)
        self.assertEqual(validate_runtime(json.dumps(first)), first)
        self.assertNotEqual(first['JWT_SECRET'], second['JWT_SECRET'])
        self.assertEqual(len(first['CREDS_IV']), 32)

    def test_payload_uses_only_clipboard_stdin(self):
        runner = Mock(return_value=subprocess.CompletedProcess([], 0))
        helper.write_clipboard(b'synthetic-json', runner=runner, executable='clip.exe')
        args, kwargs = runner.call_args
        self.assertEqual(args[0], ['clip.exe'])
        self.assertEqual(kwargs['input'], b'synthetic-json')
        self.assertNotIn('env', kwargs)

    def test_main_never_echoes_key_or_json(self):
        output = io.StringIO()
        with patch('sys.stdin', io.StringIO(DUMMY_KEY)), \
                patch.object(helper, 'write_clipboard') as clipboard, redirect_stdout(output):
            self.assertEqual(helper.main(['--fresh-install-confirmed']), 0)
        self.assertNotIn(DUMMY_KEY, output.getvalue())
        self.assertNotIn('JWT_SECRET', output.getvalue())
        copied = json.loads(clipboard.call_args.args[0])
        self.assertEqual(set(copied), REQUIRED)

    def test_invalid_key_no_copy_no_echo(self):
        output = io.StringIO()
        with patch('sys.stdin', io.StringIO('user_provided')), \
                patch.object(helper, 'write_clipboard') as clipboard, redirect_stderr(output):
            self.assertEqual(helper.main(['--fresh-install-confirmed']), 1)
        clipboard.assert_not_called()
        self.assertNotIn('user_provided', output.getvalue())

    def test_clipboard_failures_redact_errors(self):
        runner = Mock(side_effect=OSError('arbitrary-secret'))
        with self.assertRaises(helper.PrivateSetupError) as caught:
            helper.write_clipboard(b'private', runner=runner, executable='clip.exe')
        self.assertNotIn('arbitrary-secret', str(caught.exception))

    def test_clear_uses_blank_only(self):
        with patch.object(helper, 'write_clipboard') as clipboard, redirect_stdout(io.StringIO()):
            self.assertEqual(helper.main(['--clear-clipboard']), 0)
        clipboard.assert_called_once_with(b' ')

    def test_interactive_fresh_gate_accepts_only_explicit_confirmation(self):
        for response in ('no', '', 'yes'):
            with self.subTest(response=response), patch('builtins.input', return_value=response), \
                    patch.object(helper.getpass, 'getpass') as hidden, \
                    patch.object(helper, 'generate_runtime') as generate, \
                    patch.object(helper, 'write_clipboard') as clipboard, redirect_stderr(io.StringIO()):
                self.assertEqual(helper.main(['--interactive']), 1)
                hidden.assert_not_called()
                generate.assert_not_called()
                clipboard.assert_not_called()

    def test_interactive_hidden_key_is_copied_without_stdout_disclosure(self):
        output = io.StringIO()
        with patch('builtins.input', return_value='FRESH'), \
                patch.object(helper.getpass, 'getpass', return_value=DUMMY_KEY) as hidden, \
                patch.object(helper, 'write_clipboard') as clipboard, redirect_stdout(output):
            self.assertEqual(helper.main(['--interactive']), 0)
        hidden.assert_called_once()
        self.assertEqual(json.loads(clipboard.call_args.args[0])['GOOGLE_KEY'], DUMMY_KEY)
        self.assertNotIn(DUMMY_KEY, output.getvalue())
        self.assertNotIn('JWT_SECRET', output.getvalue())
        self.assertEqual(output.getvalue().strip(),
                         'Copied. Return to prepared AWS tab and paste Value, click Create. Then tell Codex saved.')


if __name__ == '__main__':
    unittest.main()
