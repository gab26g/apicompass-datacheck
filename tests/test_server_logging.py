"""Exercise the actual Docker CMD to catch logs outside our custom logger."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request


class ServerLoggingTests(unittest.TestCase):
    def test_server_process_does_not_log_query_headers_or_unmatched_paths(self):
        root = Path(__file__).parents[1]
        cmd_line = next(line for line in (root / 'datacheck/Dockerfile').read_text().splitlines() if line.startswith('CMD '))
        command = json.loads(cmd_line[4:])
        command[0] = sys.executable
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        command[command.index('--host') + 1] = '127.0.0.1'
        command[command.index('--port') + 1] = str(port)
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        base = f'http://127.0.0.1:{port}'
        environment = {**os.environ, 'DATACHECK_ENV': 'local', 'DATACHECK_STORAGE': 'local', 'DATACHECK_API_TOKEN': ''}
        with tempfile.TemporaryFile(mode='w+b') as log:
            process = subprocess.Popen(command, cwd=root, env=environment, stdout=log, stderr=subprocess.STDOUT)
            try:
                deadline = time.monotonic() + 10
                while True:
                    try:
                        with opener.open(base + '/health/live', timeout=0.5):
                            break
                    except (urllib.error.URLError, OSError):
                        if time.monotonic() >= deadline or process.poll() is not None:
                            self.fail('Test server did not start')
                        time.sleep(0.05)
                for path in ('/datasets/inventory/issues?private_value=private-query-sentinel',
                             '/datasets/unknown/issues', '/unmatched-sensitive-sentinel'):
                    request = urllib.request.Request(base + path, headers={'Authorization': 'Bearer private-header-sentinel'})
                    try:
                        with opener.open(request, timeout=3) as response:
                            response.read()
                    except urllib.error.HTTPError as error:
                        error.close()
            finally:
                process.terminate()
                process.wait(timeout=5)
            log.seek(0)
            output = log.read().decode('utf-8', errors='replace')
        self.assertIn('api_request', output)
        self.assertIn('"status": 404', output)
        for sentinel in ('private-query-sentinel', 'private-header-sentinel', 'unmatched-sensitive-sentinel'):
            self.assertNotIn(sentinel, output)
