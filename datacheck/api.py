from datetime import datetime, timezone
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Query

from datacheck.inventory import analyze_dataset
from datacheck.schemas import SCHEMAS, dataset_info
from datacheck.operations import log_request, request_id, require_tool_access
from datacheck.storage import read_dataset

VERSION = '0.2.0'
RULES = {
    'required': 'All declared columns require a non-whitespace value.',
    'duplicate_id': 'All occurrences of a repeated trimmed, nonempty ID are reported; IDs are case sensitive.',
    'type': 'The numeric column must be an integer of up to 12 digits, with optional sign.',
    'range': 'The parsed number must fall within its dataset schema bounds, inclusive.',
    'category': 'The category must match the dataset allowed values, ignoring case and surrounding spaces.',
}
app = FastAPI(title='DataCheck', version=VERSION, servers=[{'url': 'http://datacheck:8000'}])
app.middleware('http')(log_request)


def metadata(dataset_id=None):
    return {'api_version': VERSION,
            'ruleset_version': f'{dataset_id}-rules-v2' if dataset_id else 'datacheck-rules-v2',
            'request_id': request_id.get() or str(uuid4()), 'generated_at': datetime.now(timezone.utc).isoformat()}


def load_dataset(dataset_id):
    if dataset_id not in SCHEMAS:
        raise HTTPException(status_code=404, detail='Unknown dataset')
    try:
        text, source = read_dataset(dataset_id)
        return {**analyze_dataset(text, SCHEMAS[dataset_id]), 'source': source}
    except (OSError, ValueError) as error:
        raise HTTPException(status_code=503, detail='Dataset unavailable') from error


@app.get('/datasets', operation_id='list_datasets', dependencies=[Depends(require_tool_access)])
def list_datasets():
    """List the fixed, synthetic datasets and their versions."""
    return {**metadata(), 'datasets': [dataset_info(key) for key in SCHEMAS]}


@app.get('/datasets/{dataset_id}/profile', operation_id='get_dataset_profile', dependencies=[Depends(require_tool_access)])
def profile(dataset_id: str):
    """Get row count, columns, missing counts and integer summaries. Out-of-range integers remain in summaries."""
    result = load_dataset(dataset_id)
    fields = ('row_count', 'columns', 'missing_counts', 'numeric_summaries', 'source')
    response = {**metadata(dataset_id), **dataset_info(dataset_id), **{field: result[field] for field in fields}}
    if dataset_id == 'inventory':
        response['quantity_summary'] = result['quantity_summary']
    return response


@app.get('/datasets/{dataset_id}/issues', operation_id='get_dataset_issues', dependencies=[Depends(require_tool_access)])
def issues(dataset_id: str, limit: int = Query(default=20, ge=1, le=100)):
    """Get exact totals and a bounded sample of findings. If truncated is true, the findings are not the full report."""
    result = load_dataset(dataset_id)
    findings = result['issues'][:limit]
    return {**metadata(dataset_id), **dataset_info(dataset_id),
            'row_count': result['row_count'], 'issue_count': result['issue_count'],
            'source': result['source'],
            'affected_row_count': result['affected_row_count'], 'issues': findings,
            'returned_issue_count': len(findings), 'limit': limit,
            'truncated': len(findings) < result['issue_count']}


@app.get('/rules', operation_id='list_validation_rules', dependencies=[Depends(require_tool_access)])
def rules():
    """List five shared rule families and each dataset's columns, bounds and allowed values."""
    return {**metadata(), 'rules': [{'id': key, 'description': value} for key, value in RULES.items()],
            'dataset_schemas': SCHEMAS}


@app.get('/health/live', include_in_schema=False)
def live():
    return {**metadata(), 'status': 'alive'}


@app.get('/health/ready', include_in_schema=False, dependencies=[Depends(require_tool_access)])
def ready():
    for dataset_id in SCHEMAS:
        load_dataset(dataset_id)
    return {**metadata(), 'status': 'ready', 'checked_datasets': list(SCHEMAS)}
