"""Ship bounded Mongo structured envelopes; never ship messages or attributes."""
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import subprocess
import time
from uuid import uuid4

try:
    from scripts.ship_questions import instant, utc, save_state
except ImportError:
    from ship_questions import instant, utc, save_state

GROUP = '/apicompass/prod/runtime'
STATE_DIR = Path('/var/lib/apicompass-database-logs')
MAX_LINE_BYTES = 65536
MAX_SCAN_BYTES = 4 * 1024**2
MAX_EVENTS = 2000  # Five-minute cold start includes routine authenticated health-check traffic.
MAX_BATCH_BYTES = 900 * 1024  # Includes CloudWatch's 26-byte per-event overhead.
MAX_SEEN = 10000
MAX_STATE_BYTES = 1024**2
COMPONENTS = frozenset({'ACCESS', 'ASIO', 'COMMAND', 'CONTROL', 'EXECUTOR', 'FTDC',
                        'GEO', 'INDEX', 'JOURNAL', 'NETWORK', 'QUERY', 'RECOVERY',
                        'REPL', 'REPL_HB', 'REPL_ROLLBACK', 'SHARDING', 'STORAGE',
                        'TXN', 'WRITE', 'WT', 'CONNPOOL', '-'})
CONTEXTS = frozenset({'initandlisten', 'listener', 'SignalHandler', 'ftdc',
                      'WTCheckpointThread', 'JournalFlusher',
                      'LogicalSessionCacheRefresh', 'LogicalSessionCacheReap'})
DOCKER_TIMESTAMP = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,9})?Z ')


class ShippingError(Exception):
    pass


def parse_line(line):
    if len(line.encode()) > MAX_LINE_BYTES:
        raise ShippingError('line_limit')
    try:
        raw = json.loads(DOCKER_TIMESTAMP.sub('', line, count=1))
        if not isinstance(raw, dict):
            return None
        stamp = raw.get('t', {}).get('$date')
        if not isinstance(stamp, str) or not re.fullmatch(
                r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|\+00:00)', stamp):
            return None
        stamp = utc(datetime.fromisoformat(stamp.replace('Z', '+00:00')))
        severity, component, event_id = raw.get('s'), raw.get('c'), raw.get('id')
        if (not isinstance(severity, str) or severity not in {'I', 'W', 'E', 'F', 'D1', 'D2', 'D3', 'D4', 'D5'}
                or not isinstance(component, str) or component not in COMPONENTS
                or type(event_id) is not int or not 0 <= event_id <= 10**9):
            return None
        context = raw.get('ctx')
        if not isinstance(context, str):
            context = 'other'
        elif re.fullmatch(r'conn\d{1,12}', context):
            context = 'connection'
        elif context not in CONTEXTS:
            context = 'other'
        classification = {'NETWORK': 'database_connection', 'STORAGE': 'database_storage',
                          'ACCESS': 'database_authentication', 'COMMAND': 'database_command',
                          'CONTROL': 'database_lifecycle'}.get(component, 'database_event')
        return {'t': stamp, 's': severity, 'c': component, 'id': event_id,
                'ctx': context, 'classification': classification}
    except (ValueError, TypeError, AttributeError):
        return None


def fingerprint(event):
    return hashlib.sha256(json.dumps(event, sort_keys=True).encode()).hexdigest()


def load_state(path, now):
    if not path.exists():
        return {'cursor': utc(now - timedelta(minutes=5)), 'seen': {}}
    if path.stat().st_size > MAX_STATE_BYTES:
        raise ShippingError('state_limit')
    state = json.loads(path.read_text())
    if (not isinstance(state, dict) or set(state) != {'cursor', 'seen'}
            or not isinstance(state['seen'], dict) or len(state['seen']) > MAX_SEEN):
        raise ShippingError('invalid_state')
    instant(state['cursor'])
    for key, stamp in state['seen'].items():
        if not re.fullmatch(r'[0-9a-f]{64}', key):
            raise ShippingError('invalid_state')
        instant(stamp)
    return state


def deliver(logs, events, state, path, until):
    end = instant(until)
    seen = {key: stamp for key, stamp in state['seen'].items()
            if instant(stamp) >= end - timedelta(minutes=10)}
    batch = []
    for event in events:
        key = fingerprint(event)
        if key not in seen:
            seen[key] = event['t']
            batch.append({'timestamp': int(instant(event['t']).timestamp() * 1000),
                          'message': json.dumps(event, sort_keys=True, separators=(',', ':'))})
    updated = {'cursor': utc(end - timedelta(seconds=5)), 'seen': seen}
    if (len(batch) > MAX_EVENTS or len(seen) > MAX_SEEN or len(json.dumps(updated).encode()) > MAX_STATE_BYTES
            or sum(len(event['message'].encode('utf-8')) + 26 for event in batch) > MAX_BATCH_BYTES):
        raise ShippingError('state_or_batch_limit')
    if batch:
        stream = 'database-' + end.strftime('%Y-%m-%d')
        try:
            logs.create_log_stream(logGroupName=GROUP, logStreamName=stream)
        except Exception as error:
            if getattr(error, 'response', {}).get('Error', {}).get('Code') != 'ResourceAlreadyExistsException':
                raise
        result = logs.put_log_events(logGroupName=GROUP, logStreamName=stream,
                                     logEvents=sorted(batch, key=lambda event: event['timestamp']))
        if result.get('rejectedLogEventsInfo') or result.get('rejectedEntityInfo'):
            raise ShippingError('delivery_rejected')
    save_state(path, updated)
    return len(batch)


def mongo_container():
    result = subprocess.run(['docker', 'ps', '-q', '--filter',
                             'label=com.docker.compose.project=apicompass-prod', '--filter',
                             'label=com.docker.compose.service=mongodb'],
                            capture_output=True, timeout=10, check=False)
    values = result.stdout.decode().split()
    if result.returncode or len(values) != 1 or not re.fullmatch(r'[0-9a-f]{12,64}', values[0]):
        raise ShippingError('mongo_unavailable')
    return values[0]


def collect(target, since, until):
    process = subprocess.Popen(['docker', 'logs', '--timestamps', '--since', since,
                                '--until', until, target], stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT)
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)
    deadline, total, pending, events = time.monotonic() + 20, 0, b'', []
    try:
        while True:
            if time.monotonic() >= deadline:
                raise ShippingError('scan_timeout')
            if not selector.select(timeout=1):
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
                        raise ShippingError('batch_limit')
            if len(pending) > MAX_LINE_BYTES:
                raise ShippingError('line_limit')
        if pending:
            event = parse_line(pending.decode('utf-8', errors='replace'))
            if event is not None:
                events.append(event)
        if len(events) > MAX_EVENTS or process.wait(timeout=3) != 0:
            raise ShippingError('docker_logs_or_batch_failed')
        return events
    finally:
        selector.close()
        if process.poll() is None:
            process.kill()
            process.wait(timeout=3)
        process.stdout.close()


def run():
    import boto3
    import fcntl
    from botocore.config import Config
    STATE_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(STATE_DIR, 0o700)
    descriptor = os.open(STATE_DIR / 'ship.lock', os.O_CREAT | os.O_RDWR, 0o600)
    with os.fdopen(descriptor, 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        now = datetime.now(timezone.utc)
        path = STATE_DIR / 'state.json'
        state = load_state(path, now)
        until = utc(now)
        events = collect(mongo_container(), state['cursor'], until)
        logs = boto3.client('logs', region_name=os.environ.get('AWS_REGION', 'ap-southeast-1'),
                            config=Config(connect_timeout=3, read_timeout=10,
                                          retries={'mode': 'standard', 'total_max_attempts': 2}))
        return deliver(logs, events, state, path, until)


def main():
    event = {'job': 'database_logs', 'request_id': str(uuid4())}
    started = time.monotonic()
    try:
        event.update(status='succeeded', events_delivered=run())
    except Exception:
        event['status'] = 'failed'
    event['duration_ms'] = round((time.monotonic() - started) * 1000, 2)
    print(json.dumps(event, sort_keys=True))
    return 0 if event['status'] == 'succeeded' else 1


if __name__ == '__main__':
    raise SystemExit(main())
