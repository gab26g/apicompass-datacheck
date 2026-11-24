import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from datacheck.api import app


class DatasetTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_catalog_has_three_versioned_datasets(self):
        datasets = self.client.get('/datasets').json()['datasets']
        self.assertEqual([item['id'] for item in datasets], ['inventory', 'shipments', 'equipment'])
        self.assertTrue(all(item['dataset_version'].endswith('-v2') for item in datasets))

    def test_all_fixtures_have_sixty_rows_and_independent_golden_findings(self):
        expected = {
            'inventory': [(1, 'sku', 'duplicate_id'), (2, 'sku', 'duplicate_id'),
                          (3, 'quantity', 'range'), (4, 'quantity', 'type'),
                          (5, 'sku', 'required'), (6, 'status', 'category')],
            'shipments': [(1, 'shipment_id', 'duplicate_id'), (2, 'shipment_id', 'duplicate_id'),
                          (3, 'weight_kg', 'range'), (4, 'weight_kg', 'type'),
                          (5, 'shipment_id', 'required'), (6, 'status', 'category'),
                          (7, 'weight_kg', 'range')],
            'equipment': [(1, 'asset_id', 'duplicate_id'), (2, 'asset_id', 'duplicate_id'),
                          (3, 'service_hours', 'range'), (4, 'service_hours', 'type'),
                          (5, 'asset_id', 'required'), (6, 'condition', 'category'),
                          (7, 'service_hours', 'range')],
        }
        for dataset, golden in expected.items():
            with self.subTest(dataset=dataset):
                response = self.client.get(f'/datasets/{dataset}/issues')
                self.assertEqual(response.status_code, 200)
                report = response.json()
                self.assertEqual(report['row_count'], 60)
                self.assertEqual(report['issue_count'], len(golden))
                self.assertEqual(report['affected_row_count'], len({row for row, _, _ in golden}))
                self.assertEqual([(i['row'], i['column'], i['rule_id']) for i in report['issues']], golden)
                self.assertFalse(report['truncated'])

    def test_findings_limit_preserves_exact_totals(self):
        report = self.client.get('/datasets/shipments/issues?limit=2').json()
        self.assertEqual(report['issue_count'], 7)
        self.assertEqual(report['affected_row_count'], 7)
        self.assertEqual(report['returned_issue_count'], 2)
        self.assertEqual(len(report['issues']), 2)
        self.assertTrue(report['truncated'])
        for limit in ('0', '101', 'oops'):
            self.assertEqual(self.client.get(f'/datasets/inventory/issues?limit={limit}').status_code, 422)

    def test_profiles_and_rules_describe_each_schema(self):
        expected_bounds = {'inventory': (-3, 60), 'shipments': (0, 1001), 'equipment': (-1, 100001)}
        for dataset, number in [('inventory', 'quantity'), ('shipments', 'weight_kg'),
                                ('equipment', 'service_hours')]:
            with self.subTest(dataset=dataset):
                profile = self.client.get(f'/datasets/{dataset}/profile').json()
                self.assertEqual(profile['row_count'], 60)
                summary = profile['numeric_summaries'][number]
                self.assertEqual(summary['parsed_count'], 59)
                self.assertEqual(summary['excluded_count'], 1)
                self.assertEqual((summary['min'], summary['max']), expected_bounds[dataset])
                self.assertEqual(list(profile['missing_counts'].values()), [1, 0, 0])
                self.assertEqual(profile['ruleset_version'], f'{dataset}-rules-v2')
        rules = self.client.get('/rules').json()
        self.assertEqual(len(rules['rules']), 5)
        self.assertEqual(set(rules['dataset_schemas']), {'inventory', 'shipments', 'equipment'})

    def test_source_failure_is_503_not_an_empty_success(self):
        with patch('pathlib.Path.read_text', side_effect=OSError('unavailable')):
            response = self.client.get('/datasets/inventory/issues')
        self.assertEqual(response.status_code, 503)
        self.assertNotIn('issues', response.json())


if __name__ == '__main__':
    unittest.main()
