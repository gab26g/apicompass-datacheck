import io
import os
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from datacheck.api import app
from datacheck.storage import MAX_BYTES
import boto3
from botocore.response import StreamingBody
from botocore.stub import Stubber


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    @contextmanager
    def s3_response(self, payload=None, version='test-object-v2', error=False, declared_length=None, dataset='inventory'):
        if payload is None:
            payload = (Path(__file__).parents[1] / f'datacheck/data/{dataset}.csv').read_bytes()
        client = boto3.client('s3', region_name='us-east-1',
                              aws_access_key_id='dummy', aws_secret_access_key='dummy')
        expected = {'Bucket': 'test-only-fixtures', 'Key': f'datasets/v2/{dataset}.csv'}
        raw_stream = io.BytesIO(payload)
        body = StreamingBody(raw_stream, len(payload))
        with Stubber(client) as stubber:
            if error:
                stubber.add_client_error('get_object', service_error_code='AccessDenied',
                                         http_status_code=403, expected_params=expected)
            else:
                response = {'Body': body, 'ContentLength': declared_length if declared_length is not None else len(payload)}
                if version is not None:
                    response['VersionId'] = version
                stubber.add_response('get_object', response, expected)
            with patch.dict(os.environ, {'DATACHECK_STORAGE': 's3', 'DATACHECK_S3_BUCKET': 'test-only-fixtures'}), patch('datacheck.storage.s3_client', return_value=client):
                yield raw_stream
            stubber.assert_no_pending_responses()

    def test_s3_content_returns_real_object_version_and_exact_findings(self):
        for dataset, count in [('inventory', 6), ('shipments', 7), ('equipment', 7)]:
            with self.subTest(dataset=dataset), self.s3_response(dataset=dataset) as body:
                response = self.client.get(f'/datasets/{dataset}/issues')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()['issue_count'], count)
            self.assertEqual(response.json()['source']['storage'], 's3')
            self.assertEqual(response.json()['source']['object_version'], 'test-object-v2')
            self.assertTrue(body.closed)

    def test_local_integrity_uses_raw_bytes_like_s3(self):
        source = Path(__file__).parents[1] / 'datacheck/data'
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            (target / 'manifest.json').write_bytes((source / 'manifest.json').read_bytes())
            content = (source / 'inventory.csv').read_bytes().replace(b'\n', b'\r\n')
            (target / 'inventory.csv').write_bytes(content)
            with patch('datacheck.storage.DATA_DIR', target):
                self.assertEqual(self.client.get('/datasets/inventory/issues').status_code, 503)

    def test_unversioned_or_changed_s3_content_is_unavailable(self):
        for version in (None, 'null'):
            with self.subTest(version=version), self.s3_response(version=version) as body:
                self.assertEqual(self.client.get('/datasets/inventory/issues').status_code, 503)
            self.assertTrue(body.closed)
        with self.s3_response(payload=b'sku,quantity,status\nA,1,active\n'):
            self.assertEqual(self.client.get('/datasets/inventory/issues').status_code, 503)

    def test_s3_denial_and_oversize_do_not_fall_back_to_local(self):
        with self.s3_response(error=True):
            response = self.client.get('/datasets/inventory/issues')
            self.assertEqual(response.status_code, 503)
            self.assertEqual(response.json(), {'detail': 'Dataset unavailable'})
        with self.s3_response(declared_length=MAX_BYTES + 1) as body:
            self.assertEqual(self.client.get('/datasets/inventory/issues').status_code, 503)
        self.assertTrue(body.closed)

    def test_corrupt_manifest_is_a_controlled_dependency_failure(self):
        with patch('pathlib.Path.read_text', return_value='{}'):
            response = self.client.get('/datasets/inventory/issues')
        self.assertEqual(response.status_code, 503)

    def test_invalid_storage_mode_cannot_silently_use_local_files(self):
        with patch.dict(os.environ, {'DATACHECK_STORAGE': 'typo'}):
            self.assertEqual(self.client.get('/datasets/inventory/issues').status_code, 503)

    def test_production_cannot_silently_use_local_files(self):
        with patch.dict(os.environ, {'DATACHECK_ENV': 'production', 'DATACHECK_API_TOKEN': 'test-only-never-deployed', 'DATACHECK_STORAGE': 'local'}):
            response = self.client.get('/datasets/inventory/issues', headers={'Authorization': 'Bearer test-only-never-deployed'})
            self.assertEqual(response.status_code, 503)

    def test_local_response_has_content_hash(self):
        response = self.client.get('/datasets/inventory/issues')
        self.assertEqual(response.status_code, 200)
        self.assertIn('source', response.json())
        self.assertEqual(response.json()['source']['storage'], 'local')
        self.assertEqual(len(response.json()['source']['sha256']), 64)


if __name__ == '__main__':
    unittest.main()
