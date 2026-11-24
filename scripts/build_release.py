"""Create a minimal, allowlisted AWS application bundle; never archive the repo."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
FILES = (
    'scripts/recovery_chat.cjs',
    'compose.production.yaml', 'librechat.production.yaml', 'THIRD-PARTY-NOTICES.md',
    'infra/Caddyfile', 'branding/apicompass.css', 'branding/apicompass.svg',
    'scripts/runtime_secrets.py', 'scripts/start-production.sh', 'scripts/prepare-brand.cjs',
    'scripts/ops_jobs.py', 'scripts/question-telemetry.cjs', 'scripts/ship_questions.py',
    'scripts/create_production_user.cjs',
    'scripts/bind_production_action.py', 'scripts/bind_production_action.cjs',
    'scripts/ship_database.py',
    'scripts/verify_restore.py', 'scripts/recovery_stack.py',
    'actions/instructions-v3.txt', 'actions/datacheck.production.openapi.json',
    'infra/systemd/apicompass-backup.service', 'infra/systemd/apicompass-backup.timer',
    'infra/systemd/apicompass-health.service', 'infra/systemd/apicompass-health.timer',
    'infra/systemd/apicompass-question-telemetry.service', 'infra/systemd/apicompass-question-telemetry.timer',
    'infra/systemd/apicompass-database-logs.service', 'infra/systemd/apicompass-database-logs.timer',
    'datacheck/Dockerfile', 'datacheck/requirements.txt', 'datacheck/api.py',
    'datacheck/inventory.py', 'datacheck/schemas.py', 'datacheck/operations.py', 'datacheck/storage.py',
    'datacheck/data/inventory.csv', 'datacheck/data/shipments.csv',
    'datacheck/data/equipment.csv', 'datacheck/data/manifest.json',
)


def collect(root):
    root = Path(root).resolve()
    payload = {}
    for name in FILES:
        path = root / name
        if path.is_symlink() or not path.resolve().is_relative_to(root) or not path.is_file():
            raise ValueError('Required release file is missing or escapes the project: ' + name)
        content = path.read_bytes()
        # Preserve CSV raw bytes: their hashes are the DataCheck contract.
        if name.endswith(('.sh', '.service', '.timer')):
            content = content.replace(b'\r\n', b'\n')
        payload[name] = content
    manifest = json.loads(payload['datacheck/data/manifest.json'])
    for dataset in ('inventory', 'shipments', 'equipment'):
        digest = hashlib.sha256(payload[f'datacheck/data/{dataset}.csv']).hexdigest()
        if digest != manifest[dataset]['sha256']:
            raise ValueError('Fixture differs from the declared content hash: ' + dataset)
    return payload


def build(root, *, commit, dirty=False):
    root = Path(root).resolve()
    payload = collect(root)
    metadata = {'source_commit': commit, 'working_tree_dirty': dirty,
                'created_at_utc': datetime.now(timezone.utc).isoformat(),
                'files': {name: hashlib.sha256(content).hexdigest() for name, content in payload.items()}}
    payload['RELEASE-MANIFEST.json'] = (json.dumps(metadata, indent=2) + '\n').encode()
    output = root / '.local' / 'releases'
    output.mkdir(parents=True, exist_ok=True)
    temporary = output / 'building-release.zip'
    if temporary.exists():
        raise ValueError('A release build is already present; inspect it before retrying.')
    try:
        with zipfile.ZipFile(temporary, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
            for name, content in payload.items():
                info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                # This allowlist contains public code/config only, never secrets.
                # Non-root application containers must be able to read bind mounts.
                info.external_attr = 0o644 << 16
                archive.writestr(info, content)
        digest = hashlib.sha256(temporary.read_bytes()).hexdigest()
        destination = output / ('apicompass-' + digest[:20] + '.zip')
        if destination.exists():
            raise ValueError('Release already exists; do not overwrite an immutable artifact.')
        temporary.rename(destination)
        return destination, digest
    finally:
        if temporary.exists():
            temporary.unlink()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--require-clean', action='store_true')
    args = parser.parse_args()
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    dirty = bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True).strip())
    if args.require_clean and dirty:
        raise SystemExit('Commit reviewed source before building the deployment artifact.')
    path, digest = build(ROOT, commit=commit, dirty=dirty)
    print(json.dumps({'path': str(path), 'sha256': digest, 's3_key': 'releases/' + path.name,
                      'source_commit': commit, 'working_tree_dirty': dirty}, indent=2))
