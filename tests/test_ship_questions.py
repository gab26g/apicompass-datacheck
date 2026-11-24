import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from uuid import uuid4

from scripts import ship_questions as ship


def event(**changes):
    return {'event': 'question_attempt', 'schema_version': 1,
            'request_id': str(uuid4()), 'app_version': 'apicompass-runtime-v2',
            'librechat_version': '0.8.8', 'outcome': 'succeeded', 'reason': 'success',
            'duration_ms': 45.5, 'timestamp': '2026-11-23T12:00:00.000Z',
            'http_status': 200, **changes}


class QuestionShippingTests(unittest.TestCase):
    def test_actual_attempt_durations_are_metrics_once_without_idle_samples(self):
        items = [event(duration_ms=1200.5), event(duration_ms=3400, outcome='failed', reason='provider_error')]
        logs, metrics = Mock(), Mock()
        logs.put_log_events.return_value = {}
        with tempfile.TemporaryDirectory() as directory:
            ship.deliver(logs, metrics, [*items, items[0]], {'seen': {}},
                         Path(directory) / 'state.json', '2026-11-23T12:00:01Z')
        samples = [m for m in metrics.put_metric_data.call_args.kwargs['MetricData']
                   if m['MetricName'] == 'AnswerLatencyMs']
        self.assertEqual([m['Value'] for m in samples], [1200.5, 3400])
        self.assertTrue(all(m['Unit'] == 'Milliseconds' and m['Timestamp'] == ship.instant(items[0]['timestamp']) for m in samples))

    def test_frozen_hook_version_accepts_leading_dot_underscore_or_hyphen(self):
        for version in ['.release', '_release', '-release', 'apicompass-runtime-v2']:
            with self.subTest(version=version):
                parsed = ship.parse_line(json.dumps(event(app_version=version)))
                self.assertEqual(parsed['app_version'], version)

    def test_parser_strips_extra_sensitive_fields_and_docker_timestamp(self):
        raw = event(prompt='DO NOT SHIP', authorization='Bearer SECRET', error='PRIVATE')
        parsed = ship.parse_line('2026-11-23T12:00:00.123456789Z ' + json.dumps(raw))
        self.assertEqual(set(parsed), ship.FIELDS)
        self.assertNotIn('SECRET', json.dumps(parsed))
        self.assertNotIn('PRIVATE', json.dumps(parsed))

    def test_non_events_are_ignored_and_malformed_candidates_fail(self):
        for line in ['ordinary diagnostic PRIVATE', '{broken', json.dumps({'event': 'other', 'prompt': 'PRIVATE'})]:
            self.assertIsNone(ship.parse_line(line))
        for changes in [{'duration_ms': float('nan')}, {'duration_ms': -1},
                        {'duration_ms': 300001}, {'reason': 'provider_error', 'outcome': 'succeeded'},
                        {'request_id': 'sensitive text'}, {'http_status': True},
                        {'timestamp': 'yesterday'}, {'app_version': 'secret with whitespace'},
                        {'schema_version': 2}, {'librechat_version': 'other'}]:
            with self.subTest(changes=changes), self.assertRaises(ship.ShippingError):
                ship.parse_line(json.dumps(event(**changes)))

    def test_large_line_rejected_without_echoing_it(self):
        with self.assertRaises(ship.ShippingError) as caught:
            ship.parse_line('SECRET' * ship.MAX_LINE_BYTES)
        self.assertNotIn('SECRET', str(caught.exception))

    def test_duplicates_within_and_between_scans_do_not_increment_again(self):
        item = event()
        state = {'cursor': '2026-11-23T11:59:00Z', 'seen': {}}
        selected = ship.select_events([item, item], state)
        self.assertEqual(len(selected), 1)
        state['seen'][item['request_id']] = item['timestamp']
        self.assertEqual(ship.select_events([item], state), [])

    def test_heartbeat_publishes_both_zero_counts_without_question_log(self):
        logs, metrics = Mock(), Mock()
        state = {'cursor': '2026-11-23T11:59:00Z', 'seen': {}}
        with tempfile.TemporaryDirectory() as directory:
            ship.deliver(logs, metrics, [], state, Path(directory) / 'state.json',
                         '2026-11-23T12:00:01Z')
        data = metrics.put_metric_data.call_args.kwargs
        self.assertEqual(data['Namespace'], 'APICompass')
        self.assertEqual([(x['MetricName'], x['Value']) for x in data['MetricData']],
                         [('AnswerSuccess', 0), ('AnswerFailure', 0)])
        self.assertEqual(data['MetricData'][0]['Dimensions'], [{'Name': 'Project', 'Value': 'APICompass'}])
        logs.put_log_events.assert_not_called()

    def test_metric_partial_failure_does_not_advance_state_then_retry_delivers(self):
        item = event(outcome='failed', reason='provider_error')
        state = {'cursor': '2026-11-23T11:59:00Z', 'seen': {}}
        logs, metrics = Mock(), Mock()
        logs.put_log_events.return_value = {}
        metrics.put_metric_data.side_effect = [RuntimeError('PRIVATE SDK ERROR'), {}]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'state.json'
            with self.assertRaises(RuntimeError):
                ship.deliver(logs, metrics, [item], state, path, '2026-11-23T12:00:01Z')
            self.assertFalse(path.exists())
            self.assertEqual(state['seen'], {})
            ship.deliver(logs, metrics, [item], state, path, '2026-11-23T12:00:01Z')
            saved = json.loads(path.read_text())
        self.assertIn(item['request_id'], saved['seen'])
        self.assertEqual(logs.put_log_events.call_count, 2)
        self.assertEqual(metrics.put_metric_data.call_args.kwargs['MetricData'][1]['Value'], 1)

    def test_cloudwatch_partial_log_rejection_does_not_publish_metrics_or_state(self):
        logs, metrics = Mock(), Mock()
        logs.put_log_events.return_value = {'rejectedLogEventsInfo': {'tooOldLogEventEndIndex': 0}}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'state.json'
            with self.assertRaises(ship.ShippingError):
                ship.deliver(logs, metrics, [event()], {'cursor': '2026-11-23T11:59:00Z', 'seen': {}},
                             path, '2026-11-23T12:00:01Z')
            self.assertFalse(path.exists())
        metrics.put_metric_data.assert_not_called()

    def test_batch_bound_fails_instead_of_silently_dropping_events(self):
        with self.assertRaises(ship.ShippingError):
            ship.select_events([event() for _ in range(ship.MAX_EVENTS + 1)], {'seen': {}})

    def test_failed_cli_never_echoes_exception_or_raw_logs(self):
        import io
        with patch.object(ship, 'run', side_effect=RuntimeError('PRIVATE PROMPT')), \
                patch('sys.stdout', new_callable=io.StringIO) as output:
            self.assertEqual(ship.main(), 1)
        self.assertNotIn('PRIVATE', output.getvalue())
        self.assertEqual(json.loads(output.getvalue())['status'], 'failed')

    def test_successful_delivery_commits_dedup_and_sends_clean_fields(self):
        item = ship.parse_line(json.dumps(event(outcome='aborted', reason='disconnected',
                                                prompt='PRIVATE', error='SECRET')))
        logs, metrics = Mock(), Mock()
        logs.put_log_events.return_value = {}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'state.json'
            state = {'cursor': '2026-11-23T11:59:00Z', 'seen': {}}
            self.assertEqual(ship.deliver(logs, metrics, [item, item], state, path,
                                         '2026-11-23T12:00:01Z'), 1)
            saved = ship.load_state(path, ship.instant('2026-11-23T12:00:02Z'))
            self.assertEqual(ship.select_events([item], saved), [])
        message = logs.put_log_events.call_args.kwargs['logEvents'][0]['message']
        self.assertEqual(set(json.loads(message)), ship.FIELDS)
        self.assertNotIn('PRIVATE', message)
        self.assertNotIn('SECRET', message)
        self.assertEqual(metrics.put_metric_data.call_args.kwargs['MetricData'][1]['Value'], 1)

    def test_unavailable_log_delivery_does_not_publish_heartbeat_or_advance(self):
        logs, metrics = Mock(), Mock()
        logs.create_log_stream.side_effect = RuntimeError('PRIVATE SDK FAILURE')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'state.json'
            with self.assertRaises(RuntimeError):
                ship.deliver(logs, metrics, [event()], {'seen': {}}, path,
                             '2026-11-23T12:00:01Z')
            self.assertFalse(path.exists())
        metrics.put_metric_data.assert_not_called()


class SanitizedQuestionShippingTests(unittest.TestCase):
    def test_optional_question_survives_validation_and_actual_delivery(self):
        parsed = ship.parse_line(json.dumps(event(question='Inspect shipments.', question_status='captured')))
        self.assertEqual(parsed['question'], 'Inspect shipments.')
        logs, metrics = Mock(), Mock()
        logs.put_log_events.return_value = {}
        with tempfile.TemporaryDirectory() as directory:
            ship.deliver(logs, metrics, [parsed], {'seen': {}}, Path(directory) / 'state.json',
                         '2026-11-23T12:00:01Z')
        sent = json.loads(logs.put_log_events.call_args.kwargs['logEvents'][0]['message'])
        self.assertEqual(sent['question'], 'Inspect shipments.')
        self.assertEqual(sent['question_status'], 'captured')

    def test_omitted_question_status_is_preserved_and_schema_v1_metadata_remains_valid(self):
        self.assertEqual(set(ship.parse_line(json.dumps(event()))), ship.FIELDS)
        for status in ['redacted', 'omitted_missing', 'omitted_over_limit', 'omitted_unavailable']:
            parsed = ship.parse_line(json.dumps(event(question_status=status)))
            self.assertEqual(parsed['question_status'], status)
            self.assertNotIn('question', parsed)

    def test_question_schema_rejects_unsafe_or_inconsistent_candidates_instead_of_dropping_text(self):
        for changes in [{'question': 'Inspect shipments.'}, {'question_status': 'captured'},
                        {'question_status': 'invented'}, {'question_status': 'redacted', 'question': 'secret'},
                        *({'question_status': 'captured', 'question': value} for value in [
                            '', '  ', ' x ', 5, 'x ' * 251, '🙂' * 501,
                            'student@example.invalid', 'https://user:pass@example.invalid',
                            'Bearer short-secret', 'api_key=short-secret', 'password: short-secret',
                            'AIza' + 'a' * 35, 'sk-' + 'a' * 20, 'AKIA' + 'A' * 16,
                            '-----BEGIN PRIVATE KEY-----', 'a' * 32, '+63 912 345 6789',
                            'Inspect\u0000shipments', 'Inspect\nshipments', 'bad \ud800'])]:
            with self.subTest(changes=changes), self.assertRaises(ship.ShippingError):
                ship.parse_line(json.dumps(event(**changes)))

    def test_multibyte_question_batch_is_bounded_before_any_cloud_side_effect(self):
        items = [ship.parse_line(json.dumps(event(question='🙂' * 500, question_status='captured'),
                                           ensure_ascii=False)) for _ in range(500)]
        logs, metrics = Mock(), Mock()
        logs.put_log_events.return_value = {}
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ship.ShippingError):
                ship.deliver(logs, metrics, items, {'seen': {}}, Path(directory) / 'state.json',
                             '2026-11-23T12:00:01Z')
        logs.create_log_stream.assert_not_called()
        logs.put_log_events.assert_not_called()
        metrics.put_metric_data.assert_not_called()
