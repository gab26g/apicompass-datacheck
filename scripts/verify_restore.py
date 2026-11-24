"""Read-only Mongo recovery metadata; never establishes login/tool recovery."""
import argparse
import json
import re
import subprocess

COLLECTIONS = ('users', 'conversations', 'messages', 'agents', 'actions')


class VerificationError(Exception):
    pass


# IDs travel through stdin, not shell interpolation. Only counts leave mongosh.
PROBE = '''const p=JSON.parse(require('fs').readFileSync('/dev/stdin','utf8'));
const a=db.getSiblingDB('APICompass');
if(p.authenticated && !a.auth('apicompass',process.env.MONGO_APP_PASSWORD))quit(1);
const names=['users','conversations','messages','agents','actions'];
const counts={},ttl_indexes={};
const existing=new Set(a.getCollectionNames());
for(const n of names){counts[n]=a.getCollection(n).countDocuments({});
ttl_indexes[n]=existing.has(n)?a.getCollection(n).getIndexes().filter(i=>i.expireAfterSeconds!==undefined).length:0;}
const known={conversation:a.conversations.countDocuments({conversationId:p.conversation_id}),
messages:a.messages.countDocuments({conversationId:p.conversation_id}),
agent:a.agents.countDocuments({id:p.agent_id}),actions:a.actions.countDocuments({agent_id:p.agent_id})};
print(JSON.stringify({counts,known,ttl_indexes}));'''


def command(argv, data=None):
    result = subprocess.run(argv, input=data, capture_output=True, timeout=60, check=False)
    if result.returncode:
        raise VerificationError('command_failed')
    return result.stdout


def inspect(target):
    # Project Docker metadata before it leaves Docker: never read Config.Env.
    template = ('{"Name":{{json .Name}},"State":{"Running":{{json .State.Running}}},'
                '"Config":{"Labels":{{json .Config.Labels}}},'
                '"HostConfig":{"NetworkMode":{{json .HostConfig.NetworkMode}},'
                '"PortBindings":{{json .HostConfig.PortBindings}}},'
                '"NetworkSettings":{"Networks":{{json .NetworkSettings.Networks}}},'
                '"Mounts":{{json .Mounts}}}')
    return json.loads(command(['docker', 'inspect', '--format', template, target]))


def production_mongo():
    ids = command(['docker', 'ps', '-q', '--filter',
                   'label=com.docker.compose.project=apicompass-prod', '--filter',
                   'label=com.docker.compose.service=mongodb']).decode().split()
    if len(ids) != 1 or not re.fullmatch(r'[0-9a-f]{12,64}', ids[0]):
        raise VerificationError('production_mongo_unavailable')
    return ids[0]


def validate_target(target, production_volumes):
    if (not re.fullmatch(r'/apicompass-restore-[a-z0-9-]{8,48}', target.get('Name', ''))
            or target.get('State', {}).get('Running') is not True
            or target.get('Config', {}).get('Labels', {}).get('apicompass.purpose') != 'isolated-restore'
            or target.get('HostConfig', {}).get('NetworkMode') != 'none'
            or target.get('HostConfig', {}).get('PortBindings')
            or set(target.get('NetworkSettings', {}).get('Networks', {})) - {'none'}):
        raise VerificationError('unsafe_target')
    mounts = target.get('Mounts', [])
    if (not any(m.get('Destination') == '/data/db' and m.get('Type') == 'volume' for m in mounts)
            or any(m.get('Type') != 'volume' or not m.get('Name')
                   or m['Name'] in production_volumes for m in mounts)):
        raise VerificationError('unsafe_mounts')


def validate_snapshot(snapshot):
    expected = {'counts': set(COLLECTIONS), 'ttl_indexes': set(COLLECTIONS),
                'known': {'conversation', 'messages', 'agent', 'actions'}}
    if not isinstance(snapshot, dict) or set(snapshot) != set(expected):
        raise VerificationError('invalid_metadata')
    for section, keys in expected.items():
        values = snapshot[section]
        if (not isinstance(values, dict) or set(values) != keys
                or any(type(n) is not int or not 0 <= n <= 10**12 for n in values.values())):
            raise VerificationError('invalid_metadata')
    return snapshot


def probe(target, conversation_id, agent_id, authenticated=False):
    payload = json.dumps(dict(conversation_id=conversation_id, agent_id=agent_id,
                              authenticated=authenticated)).encode()
    raw = command(['docker', 'exec', '-i', target, 'mongosh', '--quiet', '--eval', PROBE], data=payload)
    return validate_snapshot(json.loads(raw))


def compare(baseline, restored):
    validate_snapshot(baseline)
    validate_snapshot(restored)
    known = baseline['known']
    if (known['conversation'] != 1 or known['agent'] != 1 or known['messages'] < 1
            or known['actions'] != 1 or baseline != restored):
        raise VerificationError('known_state_mismatch')


def run(args):
    for value in (args.conversation_id, args.agent_id):
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', value):
            raise VerificationError('invalid_id')
    prod = production_mongo()
    if args.mode == 'baseline':
        result = probe(prod, args.conversation_id, args.agent_id, authenticated=True)
        compare(result, result)  # Refuse an empty/wrong known-state baseline.
        return {'metadata': result, 'verification': 'baseline_metadata_only'}
    if not args.target or not re.fullmatch(r'apicompass-restore-[a-z0-9-]{8,48}', args.target):
        raise VerificationError('unsafe_target')
    volumes = {m['Name'] for m in inspect(prod).get('Mounts', []) if m.get('Name')}
    validate_target(inspect(args.target), volumes)
    result = probe(args.target, args.conversation_id, args.agent_id)
    with open(args.baseline, encoding='utf-8') as source:
        baseline = json.load(source)
    if baseline.get('status') != 'succeeded' or baseline.get('verification') != 'baseline_metadata_only':
        raise VerificationError('invalid_baseline')
    compare(baseline['metadata'], result)
    return {'metadata': result, 'verification': 'metadata_matched_login_tool_pending'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['baseline', 'restore'])
    parser.add_argument('--conversation-id', required=True)
    parser.add_argument('--agent-id', required=True)
    parser.add_argument('--target')
    parser.add_argument('--baseline')
    args = parser.parse_args(argv)
    try:
        event = dict(run(args), status='succeeded')
    except Exception:
        event = {'status': 'failed', 'verification': 'not_verified'}
    print(json.dumps(event, sort_keys=True))
    return 0 if event['status'] == 'succeeded' else 1


if __name__ == '__main__':
    raise SystemExit(main())
