"""Explicit assessment-only authenticated recovery stack; no production mutation."""
import argparse
import getpass
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import time
from urllib.parse import quote

try:
    from scripts import ops_jobs, runtime_secrets
except ImportError:
    import ops_jobs
    import runtime_secrets

ROOT = Path(__file__).resolve().parents[1]
PURPOSE = 'assessment-recovery'
SERVICES = ('mongodb', 'datacheck', 'chat')


class RecoveryError(Exception):
    pass


def validate_name(name):
    if not re.fullmatch(r'apicompass-recovery-[a-z0-9]{8,24}', name):
        raise RecoveryError('invalid_scope')


def command(argv, *, data=None, env=None, timeout=120):
    result = subprocess.run(argv, input=data, env=env, capture_output=True,
                            timeout=timeout, check=False)
    if result.returncode:
        raise RecoveryError('command_failed')
    return result.stdout


def labels(name):
    return ['--label', 'apicompass.purpose=' + PURPOSE,
            '--label', 'apicompass.recovery=' + name]


def check_labels(value, name):
    if (not isinstance(value, dict) or value.get('apicompass.purpose') != PURPOSE
            or value.get('apicompass.recovery') != name
            or value.get('com.docker.compose.project')):
        raise RecoveryError('unowned_resource')


def resource_labels(kind, target):
    field = '.Config.Labels' if kind == 'container' else '.Labels'
    return json.loads(command(['docker', kind, 'inspect', '--format', '{{json ' + field + '}}', target]))


def create_container(name, service, image, environment, options):
    # Docker inherits each named env value privately; no secret argv or env file.
    args = ['docker', 'create', '--name', name + '-' + service,
            *labels(name), '--label', 'com.docker.compose.project=',
            '--label', 'com.docker.compose.service=', '--network', name, '--network-alias', service,
            '--restart', 'no', '--log-driver', 'none']
    # The official Mongo entrypoint finally execs mongod as PID 1. Its readiness
    # guard distinguishes that final daemon from the temporary init daemon;
    # inserting Docker's init process would make that guard fail forever.
    if service != 'mongodb':
        args.append('--init')
    for key in environment:
        args.extend(['--env', key])
    env = dict(os.environ)
    env.update(environment)
    return command([*args, *options, image], env=env).decode().strip()


def chat_environment(keys, mongo_password):
    env = {k: keys[k] for k in ('JWT_SECRET', 'JWT_REFRESH_SECRET', 'CREDS_KEY', 'CREDS_IV', 'GOOGLE_KEY')}
    env.update(HOST='0.0.0.0', PORT='3080', NODE_ENV='production', SEARCH='false',
               SCHEDULES_SINGLE_PROCESS='true', SCHEDULES_DISABLED='true', ENDPOINTS='google,agents',
               GOOGLE_MODELS='gemini-3.5-flash-lite', GOOGLE_TITLE_MODEL='gemini-3.5-flash-lite',
               ALLOW_REGISTRATION='false', ALLOW_SOCIAL_LOGIN='false',
               DOMAIN_CLIENT='http://127.0.0.1:3081', DOMAIN_SERVER='http://127.0.0.1:3081',
               CONFIG_PATH='/app/librechat.yaml', APP_TITLE='APICompass Recovery Assessment')
    env['MONGO_URI'] = ('mongodb://root:' + quote(mongo_password, safe='') +
                        '@mongodb:27017/APICompass?authSource=admin')
    return env


def wait_for(argv, *, timeout=180):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            command(argv, timeout=10)
            return
        except (RecoveryError, subprocess.TimeoutExpired):
            time.sleep(2)
    raise RecoveryError('readiness_timeout')


def wait_datacheck(target, token, *, timeout=120):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            probe = json.loads(command(['docker', 'exec', '-i', target, 'python', '-c', ops_jobs.PROBE_CODE],
                                       data=json.dumps({'token': token}).encode(),
                                       timeout=min(35, max(1, deadline - time.monotonic()))))
            if ops_jobs.valid_health(probe['ready'], probe['report']):
                return
        except (RecoveryError, subprocess.TimeoutExpired, ValueError, KeyError, TypeError):
            pass
        time.sleep(2)
    raise RecoveryError('datacheck_known_answer_failed')


MONGO_PING = "if(require('fs').readFileSync('/proc/1/comm','utf8').trim()!=='mongod')quit(1); const a=db.getSiblingDB('admin'); if(!a.auth('root',process.env.MONGO_INITDB_ROOT_PASSWORD))quit(1); if(a.runCommand({ping:1}).ok!==1)quit(1);"
RESTORE_COMMAND = ('set -eu; umask 077; '
                   'trap "rm -f /run/recovery-auth.yml" EXIT HUP INT TERM; '
                   'cat > /run/recovery-auth.yml; '
                   'mongorestore --config /run/recovery-auth.yml --username root '
                   '--authenticationDatabase admin --nsInclude "APICompass.*" '
                   '--archive=/run/recovery.archive.gz --gzip')


def fresh_volume(name):
    # Omit a requested volume name so Docker allocates a new one atomically.
    value = command(['docker', 'volume', 'create', *labels(name)]).decode().strip()
    if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_.-]{0,127}', value):
        raise RecoveryError('invalid_volume')
    check_labels(resource_labels('volume', value), name)
    return value


def mount_volume(name, destination):
    return ['--mount', 'type=volume,source=' + fresh_volume(name) + ',target=' + destination]


def ensure_fresh(name):
    for kind, target in [('network', name), *[('container', name + '-' + s) for s in SERVICES]]:
        result = subprocess.run(['docker', kind, 'inspect', target],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
        if result.returncode == 0:
            raise RecoveryError('scope_already_exists')
    command(['docker', 'info', '--format', '{{.ServerVersion}}'])
    for kind in ('container', 'volume', 'network'):
        all_containers = ['--all'] if kind == 'container' else []
        existing = command(['docker', kind, 'ls', '-q', *all_containers,
                            '--filter', 'label=apicompass.recovery=' + name])
        if existing.strip():
            raise RecoveryError('scope_already_exists')


def start(args):
    validate_name(args.name)
    ops_jobs.restore_preflight('apicompass-restore-' + args.name.removeprefix('apicompass-recovery-'),
                               args.key or '', 'confirmed-fresh-target')
    if not args.version or args.version == 'null' or args.confirm != 'assessment-only-fresh-stack':
        raise RecoveryError('explicit_version_and_confirmation_required')
    if sys.platform != 'linux':
        raise RecoveryError('linux_host_required')
    ensure_fresh(args.name)
    # Root-owned trusted public config only; never mount production data.
    config = ROOT / 'librechat.production.yaml'
    if config.is_symlink() or not config.is_file():
        raise RecoveryError('invalid_public_config')
    mem = dict(line.split(':', 1) for line in Path('/proc/meminfo').read_text().splitlines())
    available = int(mem['MemAvailable'].split()[0])
    swap_free = int(mem.get('SwapFree', '0 kB').split()[0])
    if available < 768 * 1024 or available + swap_free < 1792 * 1024:
        raise RecoveryError('insufficient_memory_headroom')
    aws = ops_jobs.clients()
    keys = runtime_secrets.load_runtime(os.environ.get('AWS_REGION', 'ap-southeast-1'), aws['ssm'])
    data_id = ops_jobs.container('datacheck')
    # Only the immutable image ID leaves inspect, never production env/mounts.
    data_image = command(['docker', 'inspect', '--format', '{{.Image}}', data_id]).decode().strip()
    if not re.fullmatch(r'sha256:[0-9a-f]{64}', data_image):
        raise RecoveryError('invalid_datacheck_image')
    password = secrets.token_urlsafe(48)
    bucket = os.environ['DATACHECK_S3_BUCKET']
    with tempfile.TemporaryDirectory(prefix='apicompass-recovery-') as temporary:
        archive = Path(temporary) / 'mongo.archive.gz'
        response = aws['s3'].get_object(Bucket=bucket, Key=args.key, VersionId=args.version)
        try:
            size = response.get('ContentLength', 0)
            if not 0 < size < 4 * 1024**3 or shutil.disk_usage(temporary).free < size * 3 + 512 * 1024**2:
                raise RecoveryError('archive_size_or_disk_headroom')
            if response.get('VersionId') != args.version:
                raise RecoveryError('wrong_object_version')
            with open(archive, 'xb') as output:
                os.chmod(archive, 0o600)
                shutil.copyfileobj(response['Body'], output)
        finally:
            response['Body'].close()
        with open(archive, 'rb') as source:
            digest = hashlib.file_digest(source, 'sha256').hexdigest()
        if archive.stat().st_size != size or response.get('Metadata', {}).get('sha256') != digest:
            raise RecoveryError('archive_mismatch')
        command(['docker', 'network', 'create', '--driver', 'bridge', *labels(args.name), args.name])
        mongo = create_container(args.name, 'mongodb', 'mongo:8.0.20',
                                 {'MONGO_INITDB_ROOT_USERNAME': 'root', 'MONGO_INITDB_ROOT_PASSWORD': password},
                                 ['--memory', '384m', '--tmpfs', '/run:size=16m,mode=0700',
                                  *mount_volume(args.name, '/data/db'),
                                  *mount_volume(args.name, '/data/configdb')])
        command(['docker', 'start', mongo])
        wait_for(['docker', 'exec', mongo, 'mongosh', '--quiet', '--eval', MONGO_PING])
        # Copy archive into its fresh data volume, not RAM or any production mount.
        command(['docker', 'cp', str(archive), mongo + ':/data/db/recovery.archive.gz'])
        restore = RESTORE_COMMAND.replace('/run/recovery.archive.gz', '/data/db/recovery.archive.gz')
        try:
            command(['docker', 'exec', '-i', mongo, 'timeout', '--signal=TERM', '--kill-after=5s',
                     '25m', 'sh', '-c', restore],
                    data=('password: ' + json.dumps(password) + '\n').encode(), timeout=1560)
        finally:
            command(['docker', 'exec', mongo, 'rm', '-f', '/data/db/recovery.archive.gz'])
    data_env = {'DATACHECK_ENV': 'production', 'DATACHECK_STORAGE': 's3',
                'DATACHECK_API_TOKEN': keys['DATACHECK_API_TOKEN'], 'DATACHECK_S3_BUCKET': bucket,
                'AWS_DEFAULT_REGION': os.environ.get('AWS_REGION', 'ap-southeast-1'),
                'AWS_EC2_METADATA_DISABLED': 'false', 'PYTHONDONTWRITEBYTECODE': '1'}
    data = create_container(args.name, 'datacheck', data_image, data_env,
                            ['--memory', '192m', '--read-only', '--cap-drop', 'ALL',
                             '--security-opt', 'no-new-privileges:true', '--tmpfs', '/tmp:size=16m,mode=1777'])
    command(['docker', 'start', data])
    wait_datacheck(data, keys['DATACHECK_API_TOKEN'])
    chat = create_container(args.name, 'chat', runtime_secrets.CHAT_IMAGE, chat_environment(keys, password),
                            ['--memory', '768m', '--publish', '127.0.0.1:3081:3080',
                             '--mount', 'type=bind,source=' + str(config) + ',target=/app/librechat.yaml,readonly',
                             *mount_volume(args.name, '/app/data'), *mount_volume(args.name, '/app/uploads'),
                             *mount_volume(args.name, '/app/api/logs')])
    command(['docker', 'start', chat])
    wait_for(['docker', 'exec', chat, 'node', '-e',
              "fetch('http://127.0.0.1:3080/health').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"])
    return {'verification': 'restored_stack_ready_login_tool_pending', 'name': args.name,
            'archive_sha256': digest, 'loopback_port': 3081}


LOGIN_CODE = (ROOT / 'scripts/recovery_chat.cjs').read_text(encoding='utf-8') + '\nmain();\n'


def login(args):
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise RecoveryError('private_terminal_required')
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', args.conversation_id or ''):
        raise RecoveryError('invalid_conversation_id')
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', args.agent_id or ''):
        raise RecoveryError('invalid_agent_id')
    chat = args.name + '-chat'
    check_labels(resource_labels('container', chat), args.name)
    email = getpass.getpass('Existing synthetic account email (hidden): ')
    password = getpass.getpass('Existing account password (hidden): ')
    payload = json.dumps({'email': email, 'password': password, 'conversation_id': args.conversation_id,
                          'agent_id': args.agent_id}).encode()
    result = json.loads(command(['docker', 'exec', '-i', chat, 'node', '-e', LOGIN_CODE], data=payload, timeout=240))
    fields = {'login', 'conversation_present', 'action_present', 'tool_answer_verified', 'row_count',
              'issue_count', 'affected_row_count', 'request_id', 'dataset_version', 'ruleset_version'}
    stages = {'input', 'login', 'login_contract', 'conversation', 'agent', 'action', 'admission', 'stream', 'answer'}
    if (isinstance(result, dict) and set(result) == {'verified', 'stage', 'http_status'}
            and result['verified'] is False and result['stage'] in stages
            and type(result['http_status']) is int and 0 <= result['http_status'] <= 599):
        print('Recovery check stopped at stage: ' + result['stage'] + '; HTTP status: ' + str(result['http_status']), file=sys.stderr)
    if (not isinstance(result, dict) or set(result) != fields
            or any(result.get(k) is not True for k in ('login', 'conversation_present', 'action_present', 'tool_answer_verified'))
            or (result.get('row_count'), result.get('issue_count'), result.get('affected_row_count')) != (60, 7, 7)
            or result.get('dataset_version') != 'shipments-v2' or result.get('ruleset_version') != 'shipments-rules-v2'
            or not re.fullmatch(r'[a-f0-9-]{36}', result.get('request_id', ''))):
        raise RecoveryError('restored_tool_not_verified')
    return dict(result, verification='restored_login_conversation_action_tool_verified')


def owned_resources(name):
    result = {}
    for kind in ('container', 'volume', 'network'):
        all_containers = ['--all'] if kind == 'container' else []
        ids = command(['docker', kind, 'ls', '-q', *all_containers,
                       '--filter', 'label=apicompass.recovery=' + name]).decode().split()
        for target in ids:
            check_labels(resource_labels(kind, target), name)
        result[kind] = ids
    return result


def execute(args):
    validate_name(args.name)
    if args.action == 'start':
        return start(args)
    if args.action == 'login':
        return login(args)
    resources = owned_resources(args.name)
    if args.action == 'stop':
        if args.confirm != 'remove-only-assessment-resources':
            raise RecoveryError('teardown_confirmation_required')
        for target in resources['container']:
            command(['docker', 'stop', '--time', '30', target], timeout=60)
            command(['docker', 'container', 'rm', target])
        for target in resources['network']:
            command(['docker', 'network', 'rm', target])
        for target in resources['volume']:
            command(['docker', 'volume', 'rm', target])
    return {'name': args.name, 'resource_counts': {k: len(v) for k, v in resources.items()},
            'verification': 'assessment_removed' if args.action == 'stop' else 'inventory_only'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['start', 'status', 'login', 'stop'])
    parser.add_argument('--name', required=True)
    parser.add_argument('--key')
    parser.add_argument('--version')
    parser.add_argument('--confirm')
    parser.add_argument('--conversation-id')
    parser.add_argument('--agent-id')
    args = parser.parse_args(argv)
    try:
        event = dict(execute(args), status='succeeded')
    except Exception:
        event = {'status': 'failed', 'verification': 'not_verified',
                 'next_step': 'inspect_only_scoped_resources_then_explicit_teardown'}
    print(json.dumps(event, sort_keys=True))
    return 0 if event['status'] == 'succeeded' else 1


if __name__ == '__main__':
    raise SystemExit(main())
