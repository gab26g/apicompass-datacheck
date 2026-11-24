import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from scripts import ship_database as ship


def line(**changes):
    value = {'t': {'$date': '2026-11-23T12:00:00.123+00:00'}, 's': 'I',
             'c': 'NETWORK', 'id': 22943, 'ctx': 'conn123',
             'msg': 'PRIVATE_USER mongodb://PRIVATE_URI',
             'attr': {'namespace': 'PRIVATE_DB', 'document': 'PRIVATE_DATA'}}
    value.update(changes)
    return json.dumps(value)


class DatabaseShippingTests(unittest.TestCase):
    def test_only_safe_envelope_and_fixed_classification_leave_parser(self):
        event = ship.parse_line('2026-11-23T12:00:00.123456789Z ' + line())
        self.assertEqual(set(event), {'t', 's', 'c', 'id', 'ctx', 'classification'})
        self.assertEqual(event['classification'], 'database_connection')
        self.assertEqual(event['ctx'], 'connection')
        self.assertNotIn('PRIVATE', json.dumps(event))

    def test_unknown_context_is_normalized_not_forwarded(self):
        self.assertEqual(ship.parse_line(line(ctx='PRIVATE_CUSTOM_CONTEXT'))['ctx'], 'other')

    def test_invalid_envelopes_and_non_json_are_not_forwarded(self):
        for raw in ['PRIVATE', '{broken', line(s='PRIVATE'), line(c='PRIVATE'),
                    line(id=True), line(id='PRIVATE'), line(t={'$date': 'PRIVATE'})]:
            self.assertIsNone(ship.parse_line(raw))

    def test_line_and_collection_limits_are_small(self):
        with self.assertRaises(ship.ShippingError):
            ship.parse_line('X' * (ship.MAX_LINE_BYTES + 1))
        self.assertLessEqual(ship.MAX_SCAN_BYTES, 4 * 1024**2)
        self.assertLessEqual(ship.MAX_EVENTS, 2000)
        self.assertLess(ship.MAX_BATCH_BYTES, 1024**2)

    def test_rejected_batch_does_not_advance_cursor(self):
        logs = Mock()
        logs.put_log_events.return_value = {'rejectedLogEventsInfo': {'tooOldLogEventEndIndex': 0}}
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'state.json'
            with self.assertRaises(ship.ShippingError):
                ship.deliver(logs, [ship.parse_line(line())], {'seen': {}}, path,
                             '2026-11-23T12:00:01.000Z')
            self.assertFalse(path.exists())

    def test_success_uses_runtime_database_stream_and_replay_is_deduplicated(self):
        logs = Mock()
        logs.put_log_events.return_value = {}
        event = ship.parse_line(line())
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'state.json'
            self.assertEqual(ship.deliver(logs, [event, event], {'seen': {}}, path,
                                          '2026-11-23T12:00:01.000Z'), 1)
            state = json.loads(path.read_text())
            self.assertEqual(ship.deliver(logs, [event], state, path,
                                          '2026-11-23T12:00:02.000Z'), 0)
        call = logs.put_log_events.call_args.kwargs
        self.assertEqual(call['logGroupName'], '/apicompass/prod/runtime')
        self.assertTrue(call['logStreamName'].startswith('database-'))
        self.assertNotIn('PRIVATE', repr(call))
        self.assertEqual(logs.put_log_events.call_count, 1)

    def test_normal_startup_volume_above_500_envelopes_delivers_without_losing_cursor(self):
        from datetime import datetime, timedelta, timezone
        start = datetime(2026, 11, 23, 12, tzinfo=timezone.utc)
        events = [ship.parse_line(line(t={'$date': (start + timedelta(milliseconds=i)).isoformat()}))
                  for i in range(1000)]
        logs = Mock()
        logs.put_log_events.return_value = {}
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'state.json'
            self.assertEqual(ship.deliver(logs, events, {'seen': {}}, path,
                                          '2026-11-23T12:05:00.000Z'), 1000)
            self.assertTrue(path.exists())
        batch = logs.put_log_events.call_args.kwargs['logEvents']
        self.assertLess(sum(len(v['message'].encode()) + 26 for v in batch), 1024**2)

    def test_error_output_never_prints_raw_exception(self):
        with patch.object(ship, 'run', side_effect=RuntimeError('PRIVATE')), \
                patch('sys.stdout', new_callable=io.StringIO) as output:
            self.assertEqual(ship.main(), 1)
        self.assertNotIn('PRIVATE', output.getvalue())

    def test_container_selection_uses_only_fixed_production_mongo_labels(self):
        with patch.object(ship.subprocess, 'run', return_value=Mock(returncode=0, stdout=b'abcdef123456\n')) as run:
            self.assertEqual(ship.mongo_container(), 'abcdef123456')
        argv = run.call_args.args[0]
        self.assertIn('label=com.docker.compose.project=apicompass-prod', argv)
        self.assertIn('label=com.docker.compose.service=mongodb', argv)
        self.assertNotIn('inspect', argv)

    def test_malformed_and_oversized_state_refused(self):
        from datetime import datetime, timezone
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'state.json'
            path.write_text(json.dumps({'cursor': '2026-11-23T12:00:00Z', 'seen': {'PRIVATE': 'PRIVATE'}}))
            with self.assertRaises(ship.ShippingError):
                ship.load_state(path, datetime.now(timezone.utc))


if __name__ == '__main__':
    unittest.main()
