import io
import json
import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch

from scripts import ops_jobs as ops


class OpsTests(unittest.TestCase):
    def test_backup_keys_unique_and_scoped(self):
        a, b = ops.backup_key(), ops.backup_key()
        self.assertNotEqual(a, b)
        self.assertTrue(a.startswith('backups/mongodb/'))
        self.assertTrue(a.endswith('.archive.gz'))

    def test_actual_health_requires_known_issues_and_private_s3(self):
        ready = {'status': 'ready', 'checked_datasets': ['inventory', 'shipments', 'equipment']}
        report = {'request_id': 'trace-1', 'dataset_version': 'shipments-v2',
                  'row_count': 60, 'issue_count': 7, 'affected_row_count': 7,
                  'issue_signature': [[1, 'shipment_id', 'duplicate_id'], [2, 'shipment_id', 'duplicate_id'],
                                      [3, 'weight_kg', 'range'], [4, 'weight_kg', 'type'],
                                      [5, 'shipment_id', 'required'], [6, 'status', 'category'], [7, 'weight_kg', 'range']],
                  'truncated': False, 'source': {'storage': 's3', 'object_version': 'v1'}}
        self.assertTrue(ops.valid_health(ready, report))
        report['issue_count'] = 0
        self.assertFalse(ops.valid_health(ready, report))
        report['issue_count'] = 7
        report['source']['storage'] = 'local'
        self.assertFalse(ops.valid_health(ready, report))

    def test_missing_backup_is_failure_not_zero_age(self):
        s3 = Mock()
        s3.get_paginator.return_value.paginate.return_value = [{'Contents': []}]
        with self.assertRaises(ops.JobError):
            ops.backup_age(s3, 'bucket')

    def test_backup_age_uses_newest_nonempty_archive(self):
        now = datetime.now(timezone.utc)
        s3 = Mock()
        s3.get_paginator.return_value.paginate.return_value = [{'Contents': [
            {'Key': 'backups/mongodb/a.archive.gz', 'Size': 3, 'LastModified': now - timedelta(hours=2)},
            {'Key': 'backups/mongodb/empty.archive.gz', 'Size': 0, 'LastModified': now}]}]
        self.assertAlmostEqual(ops.backup_age(s3, 'bucket', now), 2)

    def test_failure_output_never_contains_exception_secret(self):
        with patch.object(ops, 'run_job', side_effect=RuntimeError('PRIVATE_ERROR_MARKER_FOR_TEST_ONLY')), \
                patch.object(ops, 'ship_job_event'), \
                patch('sys.stdout', new_callable=io.StringIO) as output:
            self.assertEqual(ops.main(['health']), 1)
        body = json.loads(output.getvalue())
        self.assertNotIn('PRIVATE_ERROR_MARKER_FOR_TEST_ONLY', output.getvalue())
        self.assertEqual(body['status'], 'failed')
        self.assertIn('request_id', body)

    def test_restore_refuses_production_names_and_unscoped_key(self):
        for name, key in [('apicompass-prod', 'backups/mongodb/x.archive.gz'),
                          ('apicompass-restore-test', 'datasets/v2/x')]:
            with self.assertRaises(ops.JobError):
                ops.restore_preflight(name, key, 'confirmed-fresh-target')

    def test_backup_command_uses_tmpfs_config(self):
        self.assertNotIn('--oplog', ops.DUMP_COMMAND)
        self.assertIn('--config /run/apicompass-backup.yml', ops.DUMP_COMMAND)
        self.assertIn('trap', ops.DUMP_COMMAND)
        self.assertNotIn('--password', ops.DUMP_COMMAND)

    def test_dump_failure_restarts_only_previously_running_chat(self):
        seen = []
        def fake(argv, **kwargs):
            seen.append(argv)
            if argv[1] == 'ps':
                return b'abcdef123456\n'
            if argv[1] == 'exec':
                raise ops.JobError('dump_failed')
            return b''
        with patch.object(ops, 'command', side_effect=fake):
            with self.assertRaises(ops.JobError):
                ops.dump_with_quiescence('mongo', 'secret', io.BytesIO())
        self.assertEqual([argv[1] for argv in seen], ['ps', 'stop', 'exec', 'start'])
        self.assertNotIn('secret', repr(seen))

    def test_originally_stopped_chat_is_never_started(self):
        with patch.object(ops, 'command', return_value=b'') as execute:
            ops.dump_with_quiescence('mongo', 'secret', io.BytesIO())
        self.assertEqual([call.args[0][1] for call in execute.call_args_list], ['ps', 'exec'])

    def test_upload_failure_removes_local_archive(self):
        paths = []
        def dump(target, password, output):
            paths.append(ops.Path(output.name))
            output.write(b'compressed-archive')
        s3 = Mock()
        s3.put_object.side_effect = RuntimeError('SDK error containing secret')
        with patch.object(ops, 'container', return_value='mongo'), \
                patch.object(ops, 'command', return_value=b'[{"HostConfig":{"Tmpfs":{"/run":""}}}]'), \
                patch.object(ops, 'dump_with_quiescence', side_effect=dump):
            with self.assertRaises(RuntimeError):
                ops.locked_backup(s3, 'bucket', {'MONGO_ROOT_PASSWORD': 'secret'})
        self.assertFalse(paths[0].exists())
        self.assertEqual(s3.put_object.call_args.kwargs['ServerSideEncryption'], 'AES256')

    def test_bad_known_answer_and_missing_backup_publish_failure(self):
        aws = {name: Mock() for name in ('ssm', 's3', 'cloudwatch', 'logs')}
        aws['ssm'].get_parameter.return_value = {'Parameter': {'Value': '{"DATACHECK_API_TOKEN":"secret"}'}}
        aws['s3'].get_paginator.return_value.paginate.return_value = [{'Contents': []}]
        args = ops.argparse.Namespace(job='health')
        with patch.object(ops, 'clients', return_value=aws), \
                patch.dict(ops.os.environ, {'DATACHECK_S3_BUCKET': 'bucket'}), \
                patch.object(ops, 'container', return_value='data'), \
                patch.object(ops, 'command', return_value=b'{"ready":{},"report":{}}'), \
                patch.object(ops.shutil, 'disk_usage', return_value=ops.shutil._ntuple_diskusage(100, 20, 80)):
            with self.assertRaises(ops.JobError):
                ops.run_job(args)
        metrics = aws['cloudwatch'].put_metric_data.call_args.kwargs['MetricData']
        by_name = {item['MetricName']: item['Value'] for item in metrics}
        self.assertEqual(by_name['HealthFailure'], 1)
        self.assertNotIn('BackupAgeHours', by_name)
        self.assertNotIn('secret', repr(metrics))

    def test_dump_timeout_still_restarts_chat_and_has_a_remote_deadline(self):
        events = []
        def execute(argv, **kwargs):
            events.append(argv[1])
            if argv[1] == 'exec':
                self.assertIn('timeout', argv)
                self.assertGreater(kwargs['timeout'], 25 * 60 + 5)
                raise ops.subprocess.TimeoutExpired(argv, kwargs['timeout'])
            return b'abcdef123456\n' if argv[1] == 'ps' else b''
        with patch.object(ops, 'command', side_effect=execute):
            with self.assertRaises(ops.subprocess.TimeoutExpired):
                ops.dump_with_quiescence('mongo', 'secret', io.BytesIO())
        self.assertEqual(events, ['ps', 'stop', 'exec', 'start'])

    def test_backup_cannot_leave_a_late_database_write_lock(self):
        def execute(argv, **kwargs):
            return b'abcdef123456\n' if argv[1] == 'ps' else b''
        with patch.object(ops, 'command', side_effect=execute), \
                patch.object(ops, 'mongo_control', create=True) as control:
            ops.dump_with_quiescence('mongo', 'secret', io.BytesIO())
        control.assert_not_called()

    def test_restore_never_reuses_a_named_volume_even_if_target_appears_after_download(self):
        s3 = Mock()
        content = b'archive'
        s3.get_object.return_value = {'Body': io.BytesIO(content), 'Metadata': {
            'sha256': ops.hashlib.sha256(content).hexdigest()}}
        args = ops.argparse.Namespace(target='apicompass-restore-fresh1234',
                                      key='backups/mongodb/x.archive.gz',
                                      version='version-1', confirm='confirmed-fresh-target')
        seen = []
        def execute(argv, **kwargs):
            seen.append(argv)
            if argv[1:3] == ['volume', 'create']:
                raise AssertionError('Named volume create could reuse an existing target')
            return b'created-container'
        def run(argv, **kwargs):
            return Mock(returncode=1 if 'inspect' in argv else 0)
        with patch.object(ops, 'command', side_effect=execute), \
                patch.object(ops.subprocess, 'run', side_effect=run):
            ops.restore(s3, 'bucket', args)
        create = next(argv for argv in seen if argv[1] == 'create')
        self.assertEqual(create[create.index('--mount') + 1], 'type=volume,target=/data/db')


class JobLogTests(unittest.TestCase):
    def event(self, **changes):
        value = {'job': 'backup', 'request_id': '253b7dde-5339-419e-bbd8-9514fc5c1fd1',
                 'status': 'succeeded', 'duration_ms': 1828.32,
                 'timestamp': '2026-11-24T00:15:22.123Z'}
        value.update(changes)
        return value

    def test_cloud_event_is_bounded_allowlist_with_exact_utc_timestamp(self):
        logs = Mock()
        logs.put_log_events.return_value = {}
        event = self.event(backup_key='PRIVATE_ARCHIVE_PATH', archive_sha256='PRIVATE_DIGEST',
                           error='PRIVATE_ERROR', api_request_id='9a4d3ffc-1673-48af-8dec-c0d4b50a80ae')
        ops.ship_job_event(event, logs=logs)
        logs.create_log_stream.assert_called_once_with(
            logGroupName='/apicompass/prod/jobs', logStreamName='job-runs-2026-11-24')
        payload = logs.put_log_events.call_args.kwargs
        self.assertEqual(payload['logGroupName'], '/apicompass/prod/jobs')
        self.assertEqual(payload['logStreamName'], 'job-runs-2026-11-24')
        self.assertEqual(payload['logEvents'][0]['timestamp'], 1795479322123)
        body = json.loads(payload['logEvents'][0]['message'])
        self.assertEqual(set(body), {'job', 'request_id', 'status', 'duration_ms',
                                     'timestamp', 'api_request_id'})
        self.assertNotIn('PRIVATE', repr(payload))
        self.assertLess(len(payload['logEvents'][0]['message'].encode()), 1024)

    def test_existing_stream_only_is_tolerated(self):
        from botocore.exceptions import ClientError
        logs = Mock()
        logs.create_log_stream.side_effect = ClientError(
            {'Error': {'Code': 'ResourceAlreadyExistsException', 'Message': 'PRIVATE_ERROR'}},
            'CreateLogStream')
        logs.put_log_events.return_value = {}
        ops.ship_job_event(self.event(status='failed', job='restore'), logs=logs)
        self.assertEqual(json.loads(logs.put_log_events.call_args.kwargs['logEvents'][0]['message'])['status'], 'failed')
        logs.create_log_group.assert_not_called()

    def test_denied_stream_is_not_treated_as_existing(self):
        from botocore.exceptions import ClientError
        logs = Mock()
        logs.create_log_stream.side_effect = ClientError(
            {'Error': {'Code': 'AccessDeniedException', 'Message': 'PRIVATE_ERROR'}}, 'CreateLogStream')
        with self.assertRaises(ClientError):
            ops.ship_job_event(self.event(), logs=logs)
        logs.put_log_events.assert_not_called()

    def test_rejected_events_or_transport_fail_delivery(self):
        for response in [{'rejectedLogEventsInfo': {'tooOldLogEventEndIndex': 0}},
                         {'rejectedLogEventsInfo': {'tooNewLogEventStartIndex': 0}},
                         {'rejectedLogEventsInfo': {'expiredLogEventEndIndex': 0}}]:
            with self.subTest(response=response):
                logs = Mock()
                logs.put_log_events.return_value = response
                with self.assertRaises(ops.JobError):
                    ops.ship_job_event(self.event(), logs=logs)
        logs = Mock()
        logs.put_log_events.side_effect = RuntimeError('PRIVATE_SDK_EXCEPTION')
        with self.assertRaises(RuntimeError):
            ops.ship_job_event(self.event(), logs=logs)

    def test_invalid_metadata_never_reaches_aws(self):
        for changes in [{'job': 'PRIVATE'}, {'request_id': 'PRIVATE'}, {'status': 'PRIVATE'},
                        {'duration_ms': float('nan')}, {'duration_ms': float('inf')},
                        {'duration_ms': -1}, {'duration_ms': True}, {'duration_ms': 86400001},
                        {'timestamp': '2026-11-24T00:15:22+08:00'},
                        {'timestamp': '2026-11-99T00:15:22.123Z'},
                        {'api_request_id': 'PRIVATE_TOKEN_VALUE'}]:
            with self.subTest(changes=changes):
                logs = Mock()
                with self.assertRaises(ops.JobError):
                    ops.ship_job_event(self.event(**changes), logs=logs)
                logs.create_log_stream.assert_not_called()
                logs.put_log_events.assert_not_called()

    def test_main_success_logs_once_and_preserves_journal_result(self):
        with patch.object(ops, 'run_job', return_value={'backup_key': 'PRIVATE_ARCHIVE_PATH'}) as run, \
                patch.object(ops, 'ship_job_event') as ship, \
                patch('sys.stdout', new_callable=io.StringIO) as output:
            self.assertEqual(ops.main(['backup']), 0)
        run.assert_called_once()
        ship.assert_called_once()
        body = json.loads(output.getvalue())
        self.assertEqual(body['backup_key'], 'PRIVATE_ARCHIVE_PATH')
        self.assertEqual(body['status'], 'succeeded')
        self.assertEqual(body['log_delivery'], 'succeeded')
        self.assertTrue(body['timestamp'].endswith('Z'))

    def test_log_failure_never_reruns_or_relabels_original_success(self):
        with patch.object(ops, 'run_job', return_value={}) as run, \
                patch.object(ops, 'ship_job_event',
                             side_effect=RuntimeError('PRIVATE_SDK_EXCEPTION')) as ship, \
                patch('sys.stdout', new_callable=io.StringIO) as output:
            self.assertEqual(ops.main(['backup']), 1)
        run.assert_called_once()
        ship.assert_called_once()
        body = json.loads(output.getvalue())
        self.assertEqual(body['status'], 'succeeded')
        self.assertEqual(body['log_delivery'], 'failed')
        self.assertNotIn('PRIVATE_SDK_EXCEPTION', output.getvalue())

    def test_original_failure_is_logged_and_not_masked_by_delivery_failure(self):
        for delivery_failure in [False, True]:
            with self.subTest(delivery_failure=delivery_failure), \
                    patch.object(ops, 'run_job', side_effect=RuntimeError('PRIVATE_JOB_ERROR')) as run, \
                    patch.object(ops, 'ship_job_event',
                                 side_effect=RuntimeError('PRIVATE_SDK_ERROR') if delivery_failure else None) as ship, \
                    patch('sys.stdout', new_callable=io.StringIO) as output:
                self.assertEqual(ops.main(['health']), 1)
                run.assert_called_once()
                self.assertEqual(ship.call_args.args[0]['status'], 'failed')
                body = json.loads(output.getvalue())
                self.assertEqual(body['status'], 'failed')
                self.assertEqual(body['log_delivery'], 'failed' if delivery_failure else 'succeeded')
                self.assertNotIn('PRIVATE', output.getvalue())

