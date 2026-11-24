"""Linux host: ship validated metadata and optional bounded sanitized question text, never raw chat logs."""
from datetime import datetime, timedelta, timezone
import json
import math
import os
from pathlib import Path
import re
import selectors
import subprocess
import time
from uuid import UUID, uuid4

GROUP = '/apicompass/prod/questions'
STATE_DIR = Path('/var/lib/apicompass-telemetry')
MAX_LINE_BYTES = 4096
MAX_SCAN_BYTES = 4 * 1024 * 1024
MAX_EVENTS = 500
MAX_BATCH_BYTES = 900 * 1024
MAX_SEEN = 10000
MAX_STATE_BYTES = 1024 * 1024
FIELDS = frozenset({'event', 'schema_version', 'request_id', 'app_version',
                    'librechat_version', 'outcome', 'reason', 'duration_ms',
                    'timestamp', 'http_status'})
REASONS = frozenset({'success', 'provider_error', 'uninspectable_stream', 'unfinished',
                     'missing_final', 'capacity_exceeded', 'observation_timeout',
                     'http_error', 'invalid_start_response', 'duplicate_start',
                     'disconnected', 'aborted', 'shutdown'})
TIMESTAMP = re.compile(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z')
DOCKER_TIMESTAMP = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,9})?Z ')


MAX_QUESTION = 500
QUESTION_STATUSES = frozenset({'captured', 'redacted', 'omitted_missing',
                               'omitted_over_limit', 'omitted_unavailable'})
# Keep these conservative rejection rules aligned with question-telemetry.cjs.
# A rejected candidate fails shipping instead of silently stripping its question.
UNSAFE_QUESTION = re.compile(
    r'[\x00-\x1f\x7f-\x9f\u200b-\u200f\u2028-\u202e\u2060-\u206f\ufeff\ud800-\udfff]'
    r'|[^\s@]+@[^\s@]+|\b[a-z][a-z0-9+.-]*://|www\.|\bbearer\s+\S+'
    r'|\b(?:password|passwd|secret|token|api[_-]?key|authorization|cookie)["\']?\s*[:=]'
    r'|\b(?:AIza|sk-|AKIA|ASIA)[A-Za-z0-9_-]*|-----BEGIN[^\r\n]*PRIVATE KEY-----'
    r'|[A-Za-z0-9_+\/=.-]{32,}|\+?\d[\d ().-]{5,}\d', re.IGNORECASE | re.ASCII)


class ShippingError(Exception):
    pass


def instant(value):
    if not isinstance(value, str) or not TIMESTAMP.fullmatch(value):
        raise ShippingError('invalid_timestamp')
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        raise ShippingError('invalid_timestamp') from None


def utc(value):
    return value.isoformat(timespec='milliseconds').replace('+00:00', 'Z')


def valid_uuid(value):
    try:
        return isinstance(value, str) and str(UUID(value)) == value
    except (ValueError, AttributeError):
        return False


def parse_line(line):
    if len(line.encode('utf-8')) > MAX_LINE_BYTES:
        raise ShippingError('line_limit_exceeded')
    line = DOCKER_TIMESTAMP.sub('', line, count=1).strip()
    try:
        value = json.loads(line)
    except (ValueError, TypeError):
        return None
    if not isinstance(value, dict) or value.get('event') != 'question_attempt':
        return None
    if not FIELDS.issubset(value):
        raise ShippingError('invalid_event')
    optional = {}
    if 'question' in value or 'question_status' in value:
        status = value.get('question_status')
        if not isinstance(status, str) or status not in QUESTION_STATUSES:
            raise ShippingError('invalid_question')
        optional['question_status'] = status
        if status == 'captured':
            question = value.get('question')
            if (not isinstance(question, str) or not question or len(question) > MAX_QUESTION
                    or question != question.strip() or UNSAFE_QUESTION.search(question)):
                raise ShippingError('invalid_question')
            optional['question'] = question
        elif 'question' in value:
            raise ShippingError('invalid_question')
    value = {key: value[key] for key in FIELDS}  # Unknown fields NEVER leave this process.
    value.update(optional)
    if not isinstance(value['reason'], str) or value['reason'] not in REASONS:
        raise ShippingError('invalid_event')
    expected = ('succeeded' if value['reason'] == 'success' else
                'aborted' if value['reason'] in {'disconnected', 'aborted'} else 'failed')
    duration = value['duration_ms']
    if (type(value['schema_version']) is not int or value['schema_version'] != 1
            or not valid_uuid(value['request_id'])
            or not isinstance(value['app_version'], str)
            or not re.fullmatch(r'[A-Za-z0-9._-]{1,64}', value['app_version'])
            or value['librechat_version'] != '0.8.8'
            or value['outcome'] != expected
            or type(duration) not in (int, float) or not math.isfinite(duration)
            or not 0 <= duration <= 300000
            or type(value['http_status']) is not int or not 0 <= value['http_status'] <= 599):
        raise ShippingError('invalid_event')
    instant(value['timestamp'])
    return value


def select_events(events, state):
    selected, seen = [], set(state['seen'])
    for event in events:
        if event['request_id'] not in seen:
            selected.append(event)
            seen.add(event['request_id'])
            if len(selected) > MAX_EVENTS:
                raise ShippingError('event_batch_limit')
    return selected


def save_state(path, state):
    content = json.dumps(state, sort_keys=True).encode()
    if len(content) > MAX_STATE_BYTES:
        raise ShippingError('state_limit')
    temporary = path.with_name('.state-' + uuid4().hex)
    try:
        descriptor = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(descriptor, 'wb') as output:
            output.write(content)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def load_state(path, now):
    if not path.exists():
        # Initial deployment may collect ten minutes of existing terminal events.
        return {'cursor': utc(now - timedelta(minutes=10)), 'seen': {}}
    if path.stat().st_size > MAX_STATE_BYTES:
        raise ShippingError('state_limit')
    state = json.loads(path.read_text())
    if (not isinstance(state, dict) or set(state) != {'cursor', 'seen'}
            or not isinstance(state['seen'], dict) or len(state['seen']) > MAX_SEEN):
        raise ShippingError('invalid_state')
    instant(state['cursor'])
    for request_id, timestamp in state['seen'].items():
        if not valid_uuid(request_id):
            raise ShippingError('invalid_state')
        instant(timestamp)
    return state


def deliver(logs, cloudwatch, events, state, path, until):
    events = select_events(events, state)
    end = instant(until)
    retained = {key: stamp for key, stamp in state['seen'].items()
                if instant(stamp) >= end - timedelta(hours=24)}
    for event in events:
        retained[event['request_id']] = event['timestamp']
    if len(retained) > MAX_SEEN:
        raise ShippingError('dedup_limit')
    new_state = {'cursor': utc(end - timedelta(seconds=5)), 'seen': retained}
    # Validate state bound BEFORE any delivery, not after sending metrics.
    if len(json.dumps(new_state).encode()) > MAX_STATE_BYTES:
        raise ShippingError('state_limit')
    # Question text increases event size. Bound the UTF-8 CloudWatch payload
    # including its per-event overhead BEFORE any cloud calls or cursor updates.
    batch = sorted(({'timestamp': int(instant(event['timestamp']).timestamp() * 1000),
                     'message': json.dumps(event, sort_keys=True, separators=(',', ':'), ensure_ascii=False)}
                    for event in events), key=lambda item: item['timestamp'])
    if sum(len(item['message'].encode('utf-8')) + 26 for item in batch) > MAX_BATCH_BYTES:
        raise ShippingError('log_batch_limit')
    if events:
        stream = 'question-attempts-' + end.strftime('%Y-%m-%d')
        try:
            logs.create_log_stream(logGroupName=GROUP, logStreamName=stream)
        except Exception as error:
            if getattr(error, 'response', {}).get('Error', {}).get('Code') != 'ResourceAlreadyExistsException':
                raise
        response = logs.put_log_events(logGroupName=GROUP, logStreamName=stream, logEvents=batch)
        if response.get('rejectedLogEventsInfo') or response.get('rejectedEntityInfo'):
            raise ShippingError('log_delivery_rejected')
    succeeded = sum(event['outcome'] == 'succeeded' for event in events)
    metric_data = [
        {'MetricName': name, 'Value': count, 'Unit': 'Count',
         'Dimensions': [{'Name': 'Project', 'Value': 'APICompass'}]}
        for name, count in [('AnswerSuccess', succeeded), ('AnswerFailure', len(events) - succeeded)]]
    # Actual terminal attempts only: idle scans must not fabricate zero latency.
    metric_data.extend({'MetricName': 'AnswerLatencyMs', 'Value': event['duration_ms'],
                        'Unit': 'Milliseconds', 'Timestamp': instant(event['timestamp']),
                        'Dimensions': [{'Name': 'Project', 'Value': 'APICompass'}]}
                       for event in events)
    cloudwatch.put_metric_data(Namespace='APICompass', MetricData=metric_data)
    # Cross-service exactly-once delivery is unavailable. Save only after BOTH
    # calls succeed; retry may duplicate logs/metrics if a prior response was lost.
    save_state(path, new_state)
    return len(events)


def chat_container():
    result = subprocess.run(['docker', 'ps', '-q',
                             '--filter', 'label=com.docker.compose.project=apicompass-prod',
                             '--filter', 'label=com.docker.compose.service=chat'],
                            capture_output=True, timeout=10, check=False)
    targets = result.stdout.decode().split()
    if result.returncode or len(targets) != 1 or not re.fullmatch(r'[0-9a-f]{12,64}', targets[0]):
        raise ShippingError('chat_unavailable')
    return targets[0]


def collect(container, since, until):
    """Read finite Docker logs with strict memory, byte and wall-clock bounds."""
    argv = ['docker', 'logs', '--timestamps', '--since', since, '--until', until, container]
    process = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)
    deadline, total, pending, events = time.monotonic() + 20, 0, b'', []
    try:
        while True:
            if time.monotonic() >= deadline:
                raise ShippingError('scan_timeout')
            ready = selector.select(timeout=min(1, max(0, deadline - time.monotonic())))
            if not ready:
                continue
            chunk = os.read(process.stdout.fileno(), 4096)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_SCAN_BYTES:
                raise ShippingError('scan_limit')
            pending += chunk
            while b'\n' in pending:
                line, pending = pending.split(b'\n', 1)
                event = parse_line(line.decode('utf-8', errors='replace'))
                if event is not None:
                    events.append(event)
                    if len(events) > MAX_EVENTS:
                        raise ShippingError('event_batch_limit')
            if len(pending) > MAX_LINE_BYTES:
                raise ShippingError('line_limit_exceeded')
        if pending:
            event = parse_line(pending.decode('utf-8', errors='replace'))
            if event is not None:
                events.append(event)
        if process.wait(timeout=3) != 0:
            raise ShippingError('docker_logs_failed')
        return events
    finally:
        selector.close()
        if process.poll() is None:
            process.kill()
            process.wait(timeout=3)
        process.stdout.close()


def run():
    import fcntl
    import boto3
    from botocore.config import Config
    STATE_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(STATE_DIR, 0o700)
    lock_descriptor = os.open(STATE_DIR / 'ship.lock', os.O_CREAT | os.O_RDWR, 0o600)
    with os.fdopen(lock_descriptor, 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        path = STATE_DIR / 'state.json'
        now = datetime.now(timezone.utc)
        state = load_state(path, now)
        until = utc(now)
        events = collect(chat_container(), state['cursor'], until)
        session = boto3.Session(region_name=os.environ.get('AWS_REGION', 'ap-southeast-1'))
        config = Config(connect_timeout=3, read_timeout=10,
                        retries={'mode': 'standard', 'total_max_attempts': 2})
        count = deliver(session.client('logs', config=config), session.client('cloudwatch', config=config),
                        events, state, path, until)
    return count


def main():
    started = time.monotonic()
    result = {'job': 'question_telemetry', 'request_id': str(uuid4())}
    try:
        result['attempts_delivered'] = run()
        result['status'] = 'succeeded'
    except Exception:
        result['status'] = 'failed'
    result['duration_ms'] = round((time.monotonic() - started) * 1000, 2)
    print(json.dumps(result, sort_keys=True))
    return 0 if result['status'] == 'succeeded' else 1


if __name__ == '__main__':
    raise SystemExit(main())
