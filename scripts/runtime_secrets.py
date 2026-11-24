"""Production-only SSM runtime loader. Never serialize secrets or echo child output."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import quote

PARAMETER = '/apicompass/prod/runtime'
REQUIRED = frozenset({'JWT_SECRET', 'JWT_REFRESH_SECRET', 'CREDS_KEY', 'CREDS_IV',
                      'MONGO_ROOT_PASSWORD', 'MONGO_APP_PASSWORD',
                      'DATACHECK_API_TOKEN', 'GOOGLE_KEY'})
CHAT_IMAGE = 'ghcr.io/librechat-ai/librechat@sha256:1e3bd3ac2cdbbcd64bdc4ef04c850d6fef5392d1fcb22cea46c5dcba17da7b95'
ROOT = Path(__file__).resolve().parents[1]


class RuntimeConfigurationError(ValueError):
    """Safe, value-free errors suitable for operator output."""


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise RuntimeConfigurationError('Runtime JSON contains duplicate fields.')
        result[key] = value
    return result


def validate_runtime(raw):
    try:
        value = json.loads(raw, object_pairs_hook=_unique_object)
    except (TypeError, json.JSONDecodeError):
        raise RuntimeConfigurationError('Runtime parameter must be valid JSON.') from None
    if not isinstance(value, dict) or set(value) != REQUIRED:
        raise RuntimeConfigurationError('Runtime parameter must contain exactly the eight documented fields.')
    for name, secret in value.items():
        if not isinstance(secret, str) or not secret or len(secret) > 4096 or any(ord(c) < 33 or ord(c) == 127 for c in secret):
            raise RuntimeConfigurationError('Runtime fields must be nonempty strings without whitespace or control characters.')
        if secret.lower() in {'user_provided', 'changeme', 'placeholder'}:
            raise RuntimeConfigurationError('Runtime fields cannot use placeholder values.')
        if name in {'CREDS_KEY', 'CREDS_IV'}:
            length = 64 if name == 'CREDS_KEY' else 32
            if not re.fullmatch('[0-9a-fA-F]{' + str(length) + '}', secret):
                raise RuntimeConfigurationError('Credential encryption key/IV must have the required hexadecimal length.')
        elif len(secret) < (16 if name == 'GOOGLE_KEY' else 32):
            raise RuntimeConfigurationError('Runtime field is shorter than the required minimum.')
    if len({value[key] for key in REQUIRED - {'CREDS_IV', 'GOOGLE_KEY'}}) != 6:
        raise RuntimeConfigurationError('Security keys and database passwords must be independently generated.')
    return value


def load_runtime(region, client=None):
    """One SecureString read, with decryption; default SDK chain uses EC2 role."""
    try:
        if client is None:
            import boto3
            from botocore.config import Config
            client = boto3.client('ssm', region_name=region, config=Config(
                connect_timeout=3, read_timeout=5,
                retries={'mode': 'standard', 'total_max_attempts': 2}))
        parameter = client.get_parameter(Name=PARAMETER, WithDecryption=True)['Parameter']
        if parameter.get('Type') != 'SecureString' or parameter.get('Name') != PARAMETER:
            raise RuntimeConfigurationError('Expected the documented SecureString parameter.')
        return validate_runtime(parameter.get('Value'))
    except RuntimeConfigurationError:
        raise
    except Exception:
        # SDK exception messages and malformed values must never reach logs.
        raise RuntimeConfigurationError('Cannot read the production SecureString using the host role.') from None


def build_environment(secrets, base=None):
    base = dict(os.environ if base is None else base)
    hostname = base.get('APICOMPASS_HOSTNAME', '')
    bucket = base.get('DATACHECK_S3_BUCKET', '')
    region = base.get('AWS_REGION', base.get('AWS_DEFAULT_REGION', 'ap-southeast-1'))
    if (len(hostname) > 253 or '.' not in hostname or
            not all(re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?', label) for label in hostname.split('.'))):
        raise RuntimeConfigurationError('APICOMPASS_HOSTNAME must be a lowercase public DNS hostname, without scheme or port.')
    if not re.fullmatch(r'[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]', bucket):
        raise RuntimeConfigurationError('DATACHECK_S3_BUCKET must name the private project bucket.')
    if not re.fullmatch(r'[a-z]{2}(?:-[a-z]+)+-\d', region):
        raise RuntimeConfigurationError('AWS_REGION is invalid.')
    # Prevent ambient Compose overrides/.env files from silently changing the stack.
    for name in tuple(base):
        if name.startswith('COMPOSE_') or name in REQUIRED or name == 'MONGO_URI':
            base.pop(name)
    base.update(secrets)
    base.update(APICOMPASS_HOSTNAME=hostname, DATACHECK_S3_BUCKET=bucket, AWS_REGION=region,
                COMPOSE_DISABLE_ENV_FILE='1')
    base['MONGO_URI'] = ('mongodb://apicompass:' + quote(secrets['MONGO_APP_PASSWORD'], safe='') +
                         '@mongodb:27017/APICompass?authSource=APICompass')
    return base


def compose_command(*args):
    return ['docker', 'compose', '--env-file', os.devnull, '--project-name', 'apicompass-prod',
            '--file', str(ROOT / 'compose.production.yaml'), *args]


def load_environment(base=None, client=None):
    """Public operations contract: validated process environment, never log it."""
    configured = build_environment({name: 'x' for name in REQUIRED}, base)
    return build_environment(load_runtime(configured['AWS_REGION'], client), base)


def run_compose(args, env, runner=subprocess.run):
    result = runner(compose_command(*args), cwd=ROOT, env=env, capture_output=True, check=False)
    if result.returncode:
        raise RuntimeConfigurationError('Production Compose command failed; inspect service state through a privileged operator session.')
    return result


def prepare_brand(runner=subprocess.run):
    output = ROOT / '.local' / 'branding'
    output.mkdir(parents=True, exist_ok=True)
    # Trusted static build helper only: writes root-owned public assets. No runtime
    # secret environment or Docker socket is passed; chat itself stays non-root.
    result = runner(['docker', 'run', '--rm', '--user', '0:0', '--platform', 'linux/amd64', '--entrypoint', 'node',
                     '--mount', f'type=bind,source={ROOT / "scripts"},target=/brand-scripts,readonly',
                     '--mount', f'type=bind,source={output},target=/brand-output',
                     CHAT_IMAGE, '/brand-scripts/prepare-brand.cjs'],
                    cwd=ROOT, capture_output=True, check=False)
    if result.returncode:
        raise RuntimeConfigurationError('Static branding preparation failed.')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['up', 'stop', 'status', 'check'])
    args = parser.parse_args(argv)
    try:
        # Validate nonsecret configuration before any AWS call.
        env = load_environment()
        if args.action == 'up':
            prepare_brand()
            run_compose(['up', '--detach', '--build', '--wait', '--wait-timeout', '180'], env)
        elif args.action == 'stop':
            run_compose(['stop', '--timeout', '60'], env)
        elif args.action == 'status':
            result = run_compose(['ps', '--format', 'json'], env)
            print(result.stdout.decode() if isinstance(result.stdout, bytes) else result.stdout)
        else:
            # Only service names; never render expanded Compose configuration.
            run_compose(['config', '--quiet'], env)
        print('Production runtime ' + args.action + ' succeeded.')
        return 0
    except (RuntimeConfigurationError, OSError) as error:
        message = str(error) if isinstance(error, RuntimeConfigurationError) else 'Required runtime executable or file is unavailable.'
        print(message, file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
