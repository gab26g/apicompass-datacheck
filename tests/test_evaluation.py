import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class EvaluationScoringTests(unittest.TestCase):
    def run_score(self, document):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'results.json'
            path.write_text(json.dumps(document), encoding='utf-8')
            return subprocess.run([sys.executable, str(Path(__file__).parents[1] / 'scripts/score_evaluation.py'), '--input', str(path)], capture_output=True, text=True, timeout=5)

    def test_scores_reviewed_outcomes_and_discloses_unrun_cases(self):
        rows = [{'id': 1, 'status': 'run', 'tool_correct': True, 'answer_supported': True, 'evidence': 'test-evidence-1'},
                {'id': 2, 'status': 'run', 'tool_correct': False, 'answer_supported': True, 'evidence': 'test-evidence-2'},
                {'id': 3, 'status': 'not_run'}]
        result = self.run_score({'mode': 'tool-grounded', 'cases': rows})
        self.assertEqual(result.returncode, 0, result.stderr)
        score = json.loads(result.stdout)
        self.assertEqual(score['passed'], 1)
        self.assertEqual(score['run'], 2)
        self.assertEqual(score['score'], 0.5)
        self.assertEqual(score['not_run'], list(range(3, 16)))

    def test_empty_template_does_not_claim_accuracy(self):
        result = self.run_score({'mode': 'tool-grounded', 'cases': [{'id': 1, 'status': 'not_run'}]})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIsNone(json.loads(result.stdout)['score'])

    def test_rejects_duplicate_case_ids_and_string_booleans(self):
        row = {'id': 1, 'status': 'run', 'tool_correct': True, 'answer_supported': True, 'evidence': 'test-evidence'}
        duplicate = self.run_score({'mode': 'tool-grounded', 'cases': [row, row]})
        self.assertNotEqual(duplicate.returncode, 0)
        self.assertIn('Duplicate', duplicate.stderr)
        invalid = self.run_score({'mode': 'tool-grounded', 'cases': [{**row, 'tool_correct': 'false'}]})
        self.assertNotEqual(invalid.returncode, 0)
        self.assertIn('boolean', invalid.stderr)

    def test_baseline_scores_answer_support_without_a_tool_requirement(self):
        row = {'id': 1, 'status': 'run', 'answer_supported': True, 'evidence': 'test-evidence'}
        result = self.run_score({'mode': 'baseline', 'cases': [row]})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['score'], 1.0)
