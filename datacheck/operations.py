"""Tool authentication and minimal request telemetry; never log request contents."""
import hmac
import json
import logging
import os
from contextvars import ContextVar
from time import perf_counter
from uuid import uuid4

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

request_id = ContextVar('datacheck_request_id', default=None)
bearer = HTTPBearer(auto_error=False)
logger = logging.getLogger('datacheck.requests')
logger.setLevel(logging.INFO)
if not logger.handlers:
    logger.addHandler(logging.StreamHandler())


def require_tool_access(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
    expected = os.environ.get('DATACHECK_API_TOKEN', '')
    if not expected:
        if os.environ.get('DATACHECK_ENV', 'local') != 'local':
            raise HTTPException(503, 'Tool authentication is not configured')
        return
    if credentials is None or not hmac.compare_digest(credentials.credentials.encode(), expected.encode()):
        raise HTTPException(401, 'Invalid tool credentials', headers={'WWW-Authenticate': 'Bearer'})


async def log_request(request, call_next):
    correlation = str(uuid4())
    token = request_id.set(correlation)
    started = perf_counter()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        response.headers['X-Request-ID'] = correlation
        return response
    finally:
        route = request.scope.get('route')
        logger.info(json.dumps({'event': 'api_request', 'request_id': correlation,
                                'api_version': request.app.version,
                                'method': request.method, 'route': getattr(route, 'path', 'unmatched'),
                                'status': status, 'duration_ms': round((perf_counter() - started) * 1000, 3)}))
        request_id.reset(token)
