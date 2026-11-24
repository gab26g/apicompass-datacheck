import unittest

from fastapi.testclient import TestClient
from datacheck.api import app


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_inventory_findings_match_fixture(self):
        result = self.client.get('/datasets/inventory/issues')
        self.assertEqual(result.status_code, 200)
        report = result.json()
        self.assertEqual(report['dataset_version'], 'inventory-v2')
        self.assertEqual(report['issue_count'], 6)
        self.assertEqual(report['affected_row_count'], 6)
        self.assertEqual([issue['row'] for issue in report['issues']], [1, 2, 3, 4, 5, 6])

    def test_catalog_profile_and_rules(self):
        self.assertEqual(self.client.get('/datasets').json()['datasets'][0]['id'], 'inventory')
        self.assertEqual(self.client.get('/datasets/inventory/profile').json()['row_count'], 60)
        self.assertEqual(len(self.client.get('/rules').json()['rules']), 5)

    def test_unknown_dataset_is_not_an_empty_report(self):
        self.assertEqual(self.client.get('/datasets/unknown/issues').status_code, 404)
