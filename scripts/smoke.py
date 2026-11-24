"""Run inside the DataCheck container; emit sanitized verification JSON."""
import json
from datetime import datetime, timezone
import os
from time import perf_counter
import urllib.error
import urllib.request

base = os.environ.get('DATACHECK_URL', 'http://127.0.0.1:8000').rstrip('/')
token = os.environ.get('DATACHECK_API_TOKEN', '')
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
reports = []


def get(path):
    headers = {'Authorization': f'Bearer {token}'} if token else {}
    request = urllib.request.Request(base + path, headers=headers)
    started = perf_counter()
    try:
        with opener.open(request, timeout=8) as response:
            body = json.load(response)
            return response.status, body, round((perf_counter() - started) * 1000, 3)
    except urllib.error.HTTPError as error:
        error.close()
        return error.code, {}, round((perf_counter() - started) * 1000, 3)


for dataset, count in [('inventory', 6), ('shipments', 7), ('equipment', 7)]:
    status, report, elapsed = get(f'/datasets/{dataset}/issues')
    passed = (status == 200 and report.get('row_count') == 60 and
              report.get('issue_count') == count and report.get('affected_row_count') == count)
    reports.append({'dataset': dataset, 'status': status, 'passed': passed,
                    'row_count': report.get('row_count'), 'issue_count': report.get('issue_count'),
                    'affected_row_count': report.get('affected_row_count'),
                    'source': report.get('source'), 'request_id': report.get('request_id'),
                    'duration_ms': elapsed})
status, body, elapsed = get('/health/ready')
reports.append({'check': 'readiness', 'status': status,
                'passed': status == 200 and body.get('checked_datasets') == ['inventory', 'shipments', 'equipment'],
                'duration_ms': elapsed})
status, _, elapsed = get('/datasets/unknown/issues')
reports.append({'check': 'unknown_dataset', 'status': status, 'passed': status == 404,
                'duration_ms': elapsed})
print(json.dumps({'observed_at': datetime.now(timezone.utc).isoformat(),
                  'measurement': 'API smoke checks; not AI answer evaluation', 'checks': reports}, indent=2))
raise SystemExit(0 if all(report['passed'] for report in reports) else 1)
