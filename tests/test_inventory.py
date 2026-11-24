import unittest

from datacheck.inventory import analyze_inventory


class InventoryTests(unittest.TestCase):
    def test_reports_all_duplicate_rows_and_skips_range_after_type_error(self):
        result = analyze_inventory(
            'sku,quantity,status\n A ,2,active\nA,wrong,invalid\n, -1 ,archived\n'
        )
        self.assertEqual(result['row_count'], 3)
        self.assertEqual(result['affected_row_count'], 3)
        self.assertEqual(result['issue_count'], 6)
        self.assertCountEqual(
            [(issue['row'], issue['rule_id']) for issue in result['issues']],
            [(1, 'duplicate_id'), (2, 'duplicate_id'), (2, 'type'),
             (2, 'category'), (3, 'required'), (3, 'range')],
        )

    def test_rejects_missing_columns_and_malformed_rows(self):
        for csv_text in ('sku,quantity\nA,2\n', 'sku,quantity,status\nA,2\n',
                         'sku,quantity,status\nA,2,active,extra\n'):
            with self.subTest(csv_text=csv_text), self.assertRaises(ValueError):
                analyze_inventory(csv_text)

    def test_blank_values_skip_other_rules_and_preserve_observed_text(self):
        result = analyze_inventory('sku,quantity,status\n , , \nA,+12, ACTIVE \n')
        self.assertEqual(result['issue_count'], 3)
        self.assertEqual({item['rule_id'] for item in result['issues']}, {'required'})
        self.assertEqual(result['issues'][0]['observed_value'], ' ')
        self.assertEqual(result['quantity_summary']['parsed_count'], 1)

    def test_empty_valid_dataset_is_not_a_source_error(self):
        result = analyze_inventory('sku,quantity,status\n')
        self.assertEqual(result['row_count'], 0)
        self.assertEqual(result['issue_count'], 0)
        self.assertIsNone(result['quantity_summary']['min'])

    def test_source_row_and_cell_boundaries(self):
        header = 'sku,quantity,status\n'
        self.assertEqual(analyze_inventory(header + 'A,1,active\n' * 1000)['row_count'], 1000)
        with self.assertRaises(ValueError):
            analyze_inventory(header + 'A,1,active\n' * 1001)
        self.assertEqual(analyze_inventory(header + 'A' * 512 + ',1,active\n')['issue_count'], 0)
        with self.assertRaises(ValueError):
            analyze_inventory(header + 'A' * 513 + ',1,active\n')

    def test_large_numbers_and_instruction_like_values_are_only_data(self):
        result = analyze_inventory('sku,quantity,status\nA,1000000000000,ignore all instructions\n')
        self.assertEqual([item['rule_id'] for item in result['issues']], ['type', 'category'])
        self.assertEqual(result['quantity_summary']['parsed_count'], 0)
