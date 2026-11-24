import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from datacheck.api import app
from datacheck.storage import read_dataset


class OperationsTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_liveness_and_readiness_are_distinct(self):
        self.assertEqual(self.client.get('/health/live').status_code, 200)
        ready = self.client.get('/health/ready')
        self.assertEqual(ready.status_code, 200)
        self.assertEqual(ready.json()['checked_datasets'], ['inventory', 'shipments', 'equipment'])
        with patch('pathlib.Path.read_text', side_effect=OSError('unavailable')):
            self.assertEqual(self.client.get('/health/live').status_code, 200)
            self.assertEqual(self.client.get('/health/ready').status_code, 503)

    def test_production_fails_closed_without_tool_secret(self):
        with patch.dict(os.environ, {'DATACHECK_ENV': 'production', 'DATACHECK_API_TOKEN': ''}):
            self.assertEqual(self.client.get('/datasets').status_code, 503)

    def test_readiness_fails_if_any_dataset_is_unavailable(self):
        for unavailable in ('shipments', 'equipment'):
            def read_with_failure(dataset):
                if dataset == unavailable:
                    raise OSError('unavailable')
                return read_dataset(dataset)
            with self.subTest(unavailable=unavailable), patch('datacheck.api.read_dataset', side_effect=read_with_failure):
                self.assertEqual(self.client.get('/health/ready').status_code, 503)

    def test_configured_token_protects_every_product_operation(self):
        with patch.dict(os.environ, {'DATACHECK_API_TOKEN': 'test-only-never-deployed'}):
            for path in ('/datasets', '/datasets/inventory/profile', '/datasets/inventory/issues', '/rules', '/health/ready'):
                with self.subTest(path=path):
                    self.assertEqual(self.client.get(path).status_code, 401)
                    self.assertEqual(self.client.get(path, headers={'Authorization': 'Bearer wrong'}).status_code, 401)
                    self.assertEqual(self.client.get(path, headers={'Authorization': 'Bearer test-only-never-deployed'}).status_code, 200)

    def test_request_log_is_correlated_without_query_values(self):
        with self.assertLogs('datacheck.requests', level='INFO') as captured:
            response = self.client.get('/datasets/inventory/issues?private_value=do-not-log-this')
        self.assertIn(response.json()['request_id'], response.headers['x-request-id'])
        output = '\n'.join(captured.output)
        self.assertIn(response.json()['request_id'], output)
        self.assertIn('duration_ms', output)
        self.assertIn('api_version', output)
        self.assertNotIn('do-not-log-this', output)
        self.assertNotIn('KIT-014', output)


if __name__ == '__main__':
    unittest.main()
