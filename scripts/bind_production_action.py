"""Private host-terminal login and single-action binding; never logs credentials."""
import getpass
import json
from pathlib import Path
import re
import subprocess
import sys
from runtime_secrets import load_runtime, CHAT_IMAGE

ROOT = Path(__file__).resolve().parents[1]
STAGES = frozenset({'provider_load', 'spec_conversion', 'login_request', 'login_contract', 'agent_request',
                    'agent_preconditions', 'actions_request', 'action_already_present', 'action_save',
                    'agent_readback', 'actions_readback_request', 'action_readback_contract', 'input_or_contract'})


def checked_result(result):
    if result.returncode:
        try:
            error = json.loads(result.stderr)
            if set(error) == {'status', 'stage'} and error['status'] == 'failed' and error['stage'] in STAGES:
                print('Private action setup stopped at stage: ' + error['stage'], file=sys.stderr)
        except (TypeError, ValueError):
            pass
        raise ValueError()
    return json.loads(result.stdout)


def main():
    try:
        if len(sys.argv) != 2 or not sys.stdin.isatty() or not sys.stdout.isatty():
            raise ValueError()
        agent_id = sys.argv[1]
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', agent_id):
            raise ValueError()
        result = subprocess.run(['docker', 'ps', '-q', '--filter',
                                 'label=com.docker.compose.project=apicompass-prod', '--filter',
                                 'label=com.docker.compose.service=chat'], capture_output=True, timeout=10, check=True)
        targets = result.stdout.decode().split()
        if len(targets) != 1 or not re.fullmatch(r'[0-9a-f]{12,64}', targets[0]):
            raise ValueError()
        image = subprocess.run(['docker', 'inspect', '--format', '{{.Config.Image}}', targets[0]],
                               capture_output=True, timeout=10, check=True).stdout.decode().strip()
        if image != CHAT_IMAGE:
            raise ValueError()
        # Validate files and runtime before requesting the user's password.
        raw_spec = (ROOT / 'actions/datacheck.production.openapi.json').read_text(encoding='utf-8')
        instructions = (ROOT / 'actions/instructions-v3.txt').read_text(encoding='utf-8')
        # Public converter compatibility is checked BEFORE collecting credentials.
        spec_check = subprocess.run(['docker', 'exec', '-i', '--workdir', '/app', targets[0],
                                     'node', '/app/bind-production-action.cjs', '--check-spec'],
                                    input=json.dumps({'rawSpec': raw_spec}).encode(),
                                    capture_output=True, timeout=30, check=False)
        if checked_result(spec_check) != dict(status='spec_valid', operation_count=4):
            raise ValueError()
        secrets = load_runtime('ap-southeast-1')
        email = getpass.getpass('Application login email (hidden): ')
        password = getpass.getpass('Application password (hidden): ')
        payload = json.dumps(dict(agentId=agent_id, email=email, password=password,
                                  apiKey=secrets['DATACHECK_API_TOKEN'], rawSpec=raw_spec,
                                  instructions=instructions)).encode()
        result = subprocess.run(['docker', 'exec', '-i', '--workdir', '/app', targets[0],
                                 'node', '/app/bind-production-action.cjs'], input=payload,
                                capture_output=True, timeout=120, check=False)
        summary = checked_result(result)
        if summary != dict(status='verified', agent_id=agent_id, action_count=1, operation_count=4):
            raise ValueError()
        print('Verified: DataCheck agent has exactly one action with four operations.')
        return 0
    except (Exception, KeyboardInterrupt):
        print('Private action setup stopped. No credentials were printed; inspect agent state before retrying.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
