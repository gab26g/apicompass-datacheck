import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from scripts import build_release, render_observability


class ReleaseTests(unittest.TestCase):
    def test_production_payload_has_hook_shipper_units_and_host_enrollment_helper(self):
        root = Path(__file__).resolve().parents[1]
        payload = build_release.collect(root)
        required = {'scripts/question-telemetry.cjs', 'scripts/ship_questions.py',
                    'scripts/create_production_user.cjs',
                    'infra/systemd/apicompass-question-telemetry.service',
                    'infra/systemd/apicompass-question-telemetry.timer'}
        self.assertTrue(required.issubset(payload), required - set(payload))
        self.assertNotIn('scripts/prepare_runtime_secret.py', payload)

    def test_monitoring_alarms_on_failed_answers_and_retains_backup_age_graph(self):
        resources = render_observability.render()['Resources']
        alarms = {key: value['Properties'] for key, value in resources.items()
                  if value['Type'] == 'AWS::CloudWatch::Alarm'}
        self.assertEqual(len(alarms), 6)
        self.assertNotIn('BackupAgeAlarm', alarms)
        answer = alarms['AnswerFailureAlarm']
        self.assertEqual((answer['Namespace'], answer['MetricName']), ('APICompass', 'AnswerFailure'))
        self.assertEqual(answer['Dimensions'], [{'Name': 'Project', 'Value': 'APICompass'}])
        self.assertEqual((answer['Threshold'], answer['TreatMissingData']), (0, 'breaching'))
        widgets = json.loads(resources['Dashboard']['Properties']['DashboardBody']['Fn::Sub'])['widgets']
        metrics = [series for widget in widgets for series in widget['properties']['metrics']]
        self.assertIn(['APICompass', 'BackupAgeHours', 'Project', 'APICompass'], metrics)
        self.assertIn(['APICompass', 'AnswerFailure', 'Project', 'APICompass'], metrics)

    def test_only_allowlisted_payload_is_packed_and_csv_bytes_are_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payload = {name: b'public\n' for name in build_release.FILES}
            manifest = {}
            for dataset in ('inventory', 'shipments', 'equipment'):
                raw = b'id,value\r\nsynthetic,1\r\n'
                payload[f'datacheck/data/{dataset}.csv'] = raw
                manifest[dataset] = {'sha256': hashlib.sha256(raw).hexdigest()}
            payload['datacheck/data/manifest.json'] = json.dumps(manifest).encode()
            for name, content in payload.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content)
            (root / '.env').write_text('PRIVATE_MUST_NEVER_PACK=not-a-real-secret')
            archive, digest = build_release.build(root, commit='test-commit')
            self.assertEqual(hashlib.sha256(archive.read_bytes()).hexdigest(), digest)
            with zipfile.ZipFile(archive) as bundle:
                self.assertNotIn('.env', bundle.namelist())
                self.assertEqual(bundle.getinfo('librechat.production.yaml').external_attr >> 16 & 0o444, 0o444,
                                 'Public config must be readable by non-root application containers')
                self.assertEqual(set(bundle.namelist()), set(build_release.FILES) | {'RELEASE-MANIFEST.json'})
                self.assertEqual(bundle.read('datacheck/data/inventory.csv'), b'id,value\r\nsynthetic,1\r\n')

    def test_changed_dataset_cannot_be_released_with_stale_hash(self):
        root = Path(__file__).resolve().parents[1]
        original = Path.read_bytes

        def changed(path):
            if path == root / 'datacheck/data/shipments.csv':
                return b'changed-content'
            return original(path)

        with patch.object(Path, 'read_bytes', changed):
            with self.assertRaisesRegex(ValueError, 'declared content hash'):
                build_release.collect(root)

    def test_missing_allowlisted_file_fails_instead_of_silently_shipping_partial_app(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, 'missing or escapes'):
                build_release.collect(directory)


if __name__ == '__main__':
    unittest.main()
