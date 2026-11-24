"""Linux host jobs. All runtime secrets travel through stdin or SDK memory only."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
from uuid import UUID, uuid4


class JobError(Exception):
    pass


# /run MUST be a container tmpfs. Chat is the only permitted application writer;
# stop it for the dump because standalone MongoDB does not support --oplog.
DUMP_COMMAND = ('set -eu; umask 077; '
                'trap "rm -f /run/apicompass-backup.yml" EXIT HUP INT TERM; '
                'cat > /run/apicompass-backup.yml; '
                'mongodump --config /run/apicompass-backup.yml --username root '
                '--authenticationDatabase admin --archive --gzip')
PROBE_CODE = '''import json,sys,urllib.request
p=json.load(sys.stdin)
def get(path):
 r=urllib.request.Request("http://127.0.0.1:8000"+path,headers={"Authorization":"Bearer "+p["token"]})
 with urllib.request.urlopen(r,timeout=15) as response: return json.load(response)
a=get("/health/ready"); b=get("/datasets/shipments/issues?limit=20")
b['issue_signature']=[[i.get('row'),i.get('column'),i.get('rule_id')] for i in b.get('issues',[])]
# Return only an explicit metadata allowlist, never findings or arbitrary error bodies.
print(json.dumps({"ready":{"status":a.get("status"),"checked_datasets":a.get("checked_datasets")},
"report":{k:b.get(k) for k in ["request_id","dataset_version","row_count","issue_count","affected_row_count","truncated","source","issue_signature"]}}))
'''
def command(argv, *, data=None, output=subprocess.PIPE, timeout=120):
    result = subprocess.run(argv, input=data, stdout=output, stderr=subprocess.PIPE,
                            timeout=timeout, check=False)
    if result.returncode:
        raise JobError('command_failed')  # No stderr, argv, or exception text in logs.
    return result.stdout


def container(service):
    result = command(['docker', 'ps', '-q', '--filter', 'label=com.docker.compose.project=apicompass-prod',
                      '--filter', f'label=com.docker.compose.service={service}']).decode().split()
    if len(result) != 1 or not re.fullmatch(r'[0-9a-f]{12,64}', result[0]):
        raise JobError('service_unavailable')
    return result[0]


def backup_key():
    stamp = datetime.now(timezone.utc).strftime('%Y/%m/%d/%Y%m%dT%H%M%S%fZ')
    return f'backups/mongodb/{stamp}-{uuid4().hex}.archive.gz'


def valid_health(ready, report):
    source = report.get('source') or {}
    return (ready.get('status') == 'ready'
            and set(ready.get('checked_datasets') or []) == {'inventory', 'shipments', 'equipment'}
            and report.get('dataset_version') == 'shipments-v2'
            and (report.get('row_count'), report.get('issue_count'), report.get('affected_row_count')) == (60, 7, 7)
            and report.get('truncated') is False and bool(report.get('request_id'))
            and report.get('issue_signature') == [
                [1, 'shipment_id', 'duplicate_id'], [2, 'shipment_id', 'duplicate_id'],
                [3, 'weight_kg', 'range'], [4, 'weight_kg', 'type'],
                [5, 'shipment_id', 'required'], [6, 'status', 'category'], [7, 'weight_kg', 'range']]
            and source.get('storage') == 's3' and source.get('object_version') not in (None, '', 'null'))


def backup_age(s3, bucket, now=None):
    now = now or datetime.now(timezone.utc)
    newest = None
    for page in s3.get_paginator('list_objects_v2').paginate(Bucket=bucket, Prefix='backups/mongodb/'):
        for obj in page.get('Contents', []):
            if obj['Key'].endswith('.archive.gz') and obj['Size'] > 0:
                newest = max(newest, obj['LastModified']) if newest else obj['LastModified']
    if newest is None:
        raise JobError('backup_missing')
    return max(0, (now - newest).total_seconds() / 3600)


def backup(s3, bucket, secrets):
    import fcntl  # Linux host only; no local service mutations during development.
    with open('/run/lock/apicompass-backup.lock', 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return locked_backup(s3, bucket, secrets)


def dump_with_quiescence(target, password, output):
    chat = command(['docker', 'ps', '-q', '--filter', 'label=com.docker.compose.project=apicompass-prod',
                    '--filter', 'label=com.docker.compose.service=chat']).decode().split()
    if len(chat) > 1 or (chat and not re.fullmatch(r'[0-9a-f]{12,64}', chat[0])):
        raise JobError('ambiguous_chat_writer')
    try:
        if chat:
            command(['docker', 'stop', '--time', '60', chat[0]], timeout=90)
        # Bound the command inside the container, not only the Docker client.
        # No persistent database write lock: a timed-out client cannot leave one behind.
        command(['docker', 'exec', '-i', target, 'timeout', '--signal=TERM',
                 '--kill-after=5s', '25m', 'sh', '-c', DUMP_COMMAND],
                data=('password: ' + json.dumps(password) + '\n').encode(),
                output=output, timeout=1560)
    finally:
        if chat:
            # Runs after stop/dump failure too. Any failure remains failed.
            command(['docker', 'start', chat[0]], timeout=90)


def locked_backup(s3, bucket, secrets):
    target = container('mongodb')
    config = json.loads(command(['docker', 'inspect', target]))[0]
    if '/run' not in (config.get('HostConfig', {}).get('Tmpfs') or {}):
        raise JobError('mongo_run_must_be_tmpfs')
    # Unique host temp directory is mode 0700; archive is 0600, removed on all exits.
    with tempfile.TemporaryDirectory(prefix='apicompass-backup-') as temporary:
        archive = Path(temporary) / 'mongo.archive.gz'
        with open(archive, 'xb') as output:
            os.chmod(archive, 0o600)
            dump_with_quiescence(target, secrets['MONGO_ROOT_PASSWORD'], output)
        if not 0 < archive.stat().st_size < 4 * 1024**3:
            raise JobError('archive_size_invalid')
        with archive.open('rb') as body:
            digest = hashlib.file_digest(body, 'sha256').hexdigest()
        key = backup_key()
        with archive.open('rb') as body:
            response = s3.put_object(Bucket=bucket, Key=key, Body=body,
                                     ServerSideEncryption='AES256', Metadata={'sha256': digest})
        if response.get('VersionId') in (None, '', 'null'):
            raise JobError('backup_not_versioned')
        head = s3.head_object(Bucket=bucket, Key=key, VersionId=response['VersionId'])
        if head['ContentLength'] != archive.stat().st_size or head.get('Metadata', {}).get('sha256') != digest:
            raise JobError('backup_verification_failed')
    return {'backup_key': key, 'archive_sha256': digest}


def restore_preflight(name, key, confirmation):
    if (not re.fullmatch(r'apicompass-restore-[a-z0-9-]{8,48}', name)
            or not re.fullmatch(r'backups/mongodb/[A-Za-z0-9/.-]+\.archive\.gz', key)
            or confirmation != 'confirmed-fresh-target'):
        raise JobError('unsafe_restore_target')


def restore(s3, bucket, args):
    restore_preflight(args.target, args.key, args.confirm)
    if not args.version or args.version == 'null':
        raise JobError('explicit_version_required')
    # Inspect success means the name already exists. Refuse both container and volume.
    for resource in ('container', 'volume'):
        result = subprocess.run(['docker', resource, 'inspect', args.target],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if result.returncode == 0:
            raise JobError('restore_target_exists')
    # Fail daemon connectivity before interpreting any missing-target result as safe.
    command(['docker', 'info', '--format', '{{.ServerVersion}}'])
    with tempfile.TemporaryDirectory(prefix='apicompass-restore-') as temporary:
        archive = Path(temporary) / 'mongo.archive.gz'
        with open(archive, 'xb') as output:
            os.chmod(archive, 0o600)
            response = s3.get_object(Bucket=bucket, Key=args.key, VersionId=args.version)
            try:
                shutil.copyfileobj(response['Body'], output)
            finally:
                response['Body'].close()
        with archive.open('rb') as body:
            digest = hashlib.file_digest(body, 'sha256').hexdigest()
        if response.get('Metadata', {}).get('sha256') != digest:
            raise JobError('restore_checksum_mismatch')
        # Docker atomically claims the container name and allocates an anonymous
        # volume. It cannot silently reuse a volume created since the preflight.
        command(['docker', 'create', '--name', args.target, '--network', 'none',
                 '--label', 'apicompass.purpose=isolated-restore', '--memory', '512m',
                 '--mount', 'type=volume,target=/data/db',
                 'mongo:8.0.20', 'mongod', '--bind_ip', '127.0.0.1'])
        command(['docker', 'start', args.target])
        ready = False
        for _ in range(30):
            try:
                command(['docker', 'exec', args.target, 'mongosh', '--quiet', '--eval', 'db.adminCommand({ping:1})'], timeout=5)
                ready = True
                break
            except JobError:
                time.sleep(1)
        if not ready:
            raise JobError('restore_target_not_ready')
        with archive.open('rb') as body:
            result = subprocess.run(['docker', 'exec', '-i', args.target, 'mongorestore',
                                     '--archive', '--gzip'], stdin=body,
                                    stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=1800)
        if result.returncode:
            raise JobError('restore_failed')
    # Preserve fresh target for manual known-state/login evidence; no automatic deletion.
    return {'target': args.target, 'verification': 'manual_known_state_pending'}


def clients():
    import boto3
    from botocore.config import Config
    session = boto3.Session(region_name=os.environ.get('AWS_REGION', 'ap-southeast-1'))
    config = Config(connect_timeout=3, read_timeout=20, retries={'max_attempts': 2})
    return {name: session.client(name, config=config) for name in ('ssm', 's3', 'cloudwatch', 'logs')}


def metric(name, value, unit):
    return {'MetricName': name, 'Value': value, 'Unit': unit,
            'Dimensions': [{'Name': 'Project', 'Value': 'APICompass'}]}


def run_job(args):
    aws = clients()
    bucket = os.environ['DATACHECK_S3_BUCKET']
    if args.job == 'restore':
        return restore(aws['s3'], bucket, args)
    started = time.monotonic()
    failed, result, metrics = False, {}, []
    try:
        secrets = json.loads(aws['ssm'].get_parameter(Name='/apicompass/prod/runtime', WithDecryption=True)['Parameter']['Value'])
        if args.job == 'backup':
            result = backup(aws['s3'], bucket, secrets)
        else:
            raw = command(['docker', 'exec', '-i', container('datacheck'), 'python', '-c', PROBE_CODE],
                          data=json.dumps({'token': secrets['DATACHECK_API_TOKEN']}).encode(), timeout=45)
            probe = json.loads(raw)
            if not valid_health(probe['ready'], probe['report']):
                raise JobError('health_mismatch')
            # Restrict request ID to safe syntax before adding it to telemetry.
            rid = probe['report']['request_id']
            if not isinstance(rid, str) or not re.fullmatch(r'[A-Za-z0-9-]{1,64}', rid):
                raise JobError('invalid_request_id')
            result['api_request_id'] = rid
    except Exception:
        failed = True
    duration = (time.monotonic() - started) * 1000
    if args.job == 'health':
        try:
            age = backup_age(aws['s3'], bucket)
            metrics.append(metric('BackupAgeHours', age, 'None'))
            failed = failed or age > 8
        except Exception:
            failed = True
        disk = shutil.disk_usage(os.environ.get('APICOMPASS_DISK_PATH', '/'))
        percent = 100 * disk.used / disk.total
        metrics.append(metric('DiskUsedPercent', percent, 'Percent'))
        failed = failed or percent >= 85
        metrics.append(metric('HealthLatencyMs', duration, 'Milliseconds'))
    metrics.append(metric('BackupFailure' if args.job == 'backup' else 'HealthFailure', int(failed), 'Count'))
    aws['cloudwatch'].put_metric_data(Namespace='APICompass', MetricData=metrics)
    if failed:
        raise JobError('job_failed')
    return result


def ship_job_event(event, *, logs=None):
    """Ship one terminal metadata event; never send arbitrary job results/errors."""
    from botocore.exceptions import ClientError

    def valid_id(value):
        try:
            return isinstance(value, str) and str(UUID(value)) == value
        except ValueError:
            return False

    duration = event.get('duration_ms')
    stamp = event.get('timestamp')
    if (event.get('job') not in ('health', 'backup', 'restore')
            or event.get('status') not in ('succeeded', 'failed')
            or not valid_id(event.get('request_id'))
            or type(duration) not in (int, float) or not math.isfinite(duration)
            or not 0 <= duration <= 86400000
            or not isinstance(stamp, str)
            or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z', stamp)):
        raise JobError('invalid_job_log')
    try:
        instant = datetime.fromisoformat(stamp.replace('Z', '+00:00'))
    except ValueError:
        raise JobError('invalid_job_log') from None
    safe = {key: event[key] for key in ('job', 'request_id', 'status', 'duration_ms', 'timestamp')}
    if 'api_request_id' in event:
        if not valid_id(event['api_request_id']):
            raise JobError('invalid_job_log')
        safe['api_request_id'] = event['api_request_id']
    message = json.dumps(safe, sort_keys=True, allow_nan=False)
    if len(message.encode('utf-8')) > 1024:
        raise JobError('job_log_limit')
    logs = logs if logs is not None else clients()['logs']
    group, stream = '/apicompass/prod/jobs', 'job-runs-' + instant.strftime('%Y-%m-%d')
    try:
        logs.create_log_stream(logGroupName=group, logStreamName=stream)
    except ClientError as error:
        if error.response.get('Error', {}).get('Code') != 'ResourceAlreadyExistsException':
            raise
    response = logs.put_log_events(logGroupName=group, logStreamName=stream,
                                   logEvents=[{'timestamp': int(instant.timestamp() * 1000),
                                               'message': message}])
    if (not isinstance(response, dict) or response.get('rejectedLogEventsInfo')
            or response.get('rejectedEntityInfo')):
        raise JobError('job_log_rejected')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('job', choices=['health', 'backup', 'restore'])
    parser.add_argument('--target')
    parser.add_argument('--key')
    parser.add_argument('--version')
    parser.add_argument('--confirm')
    args = parser.parse_args(argv)
    event = {'job': args.job, 'request_id': str(uuid4())}
    started = time.monotonic()
    try:
        event.update(run_job(args))
        event['status'] = 'succeeded'
    except Exception:
        event['status'] = 'failed'
    event['duration_ms'] = round((time.monotonic() - started) * 1000, 2)
    event['timestamp'] = datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
    try:
        ship_job_event(event)
        event['log_delivery'] = 'succeeded'
    except Exception:
        # Preserve the original job outcome. A delivery failure never reruns the
        # job or exposes an SDK exception; it independently fails this execution.
        event['log_delivery'] = 'failed'
    print(json.dumps(event, sort_keys=True))
    return 0 if event['status'] == 'succeeded' and event['log_delivery'] == 'succeeded' else 1


if __name__ == '__main__':
    raise SystemExit(main())
