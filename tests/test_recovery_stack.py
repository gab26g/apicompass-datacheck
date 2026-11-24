import io
import json
import unittest
from unittest.mock import patch

from scripts import recovery_stack as recovery


class RecoveryStackTests(unittest.TestCase):
    def test_scope_rejects_production_and_shell_syntax(self):
        for name in ['apicompass-prod', 'apicompass-recovery-x;id', '../test']:
            with self.assertRaises(recovery.RecoveryError):
                recovery.validate_name(name)
        recovery.validate_name('apicompass-recovery-test1234')

    def test_environment_preserves_encryption_but_replaces_mongo(self):
        keys = {k: 'SENSITIVE_' + k for k in recovery.runtime_secrets.REQUIRED}
        env = recovery.chat_environment(keys, 'temporary-root')
        self.assertEqual(env['CREDS_KEY'], keys['CREDS_KEY'])
        self.assertEqual(env['CREDS_IV'], keys['CREDS_IV'])
        self.assertNotIn(keys['MONGO_APP_PASSWORD'], env['MONGO_URI'])
        self.assertIn('@mongodb:27017/APICompass?authSource=admin', env['MONGO_URI'])
        self.assertEqual(env['DOMAIN_SERVER'], 'http://127.0.0.1:3081')
        self.assertEqual(env['ALLOW_REGISTRATION'], 'false')
        self.assertEqual(env['SCHEDULES_DISABLED'], 'true')

    def test_environment_values_never_enter_docker_arguments(self):
        with patch.object(recovery, 'command', return_value=b'id') as cmd:
            recovery.create_container('apicompass-recovery-test1234', 'chat', 'image',
                                      {'CREDS_KEY': 'PRIVATE_MARKER'}, [])
        self.assertNotIn('PRIVATE_MARKER', repr(cmd.call_args.args))
        self.assertEqual(cmd.call_args.kwargs['env']['CREDS_KEY'], 'PRIVATE_MARKER')

    def test_teardown_requires_exact_scoped_label_and_no_production_project(self):
        name = 'apicompass-recovery-test1234'
        labels = {'apicompass.purpose': 'assessment-recovery', 'apicompass.recovery': name}
        recovery.check_labels(labels, name)
        with self.assertRaises(recovery.RecoveryError):
            recovery.check_labels({**labels, 'com.docker.compose.project': 'apicompass-prod'}, name)
        with self.assertRaises(recovery.RecoveryError):
            recovery.check_labels({**labels, 'apicompass.recovery': 'other'}, name)

    def test_failed_output_suppresses_all_exception_values(self):
        with patch.object(recovery, 'execute', side_effect=RuntimeError('PRIVATE_MARKER')), \
                patch('sys.stdout', new_callable=io.StringIO) as out:
            self.assertEqual(recovery.main(['status', '--name', 'apicompass-recovery-test1234']), 1)
        self.assertNotIn('PRIVATE_MARKER', out.getvalue())
        self.assertEqual(json.loads(out.getvalue())['status'], 'failed')

    def test_login_script_only_emits_boolean_proof_and_no_session(self):
        self.assertNotIn('console.log(token)', recovery.LOGIN_CODE)
        self.assertIn('/api/auth/login', recovery.LOGIN_CODE)
        self.assertIn('/api/convos/', recovery.LOGIN_CODE)
        self.assertIn('conversation_present', recovery.LOGIN_CODE)

    def test_private_login_requires_restored_tool_proof_and_keeps_credentials_off_argv(self):
        args = recovery.argparse.Namespace(name='apicompass-recovery-test1234',
            conversation_id='saved-convo', agent_id='agent_saved')
        result = {'login': True, 'conversation_present': True, 'action_present': True,
                  'tool_answer_verified': True, 'row_count': 60, 'issue_count': 7, 'affected_row_count': 7,
                  'request_id': 'a0418fb3-ba8e-420c-bcc6-92c4ce6f7762',
                  'dataset_version': 'shipments-v2', 'ruleset_version': 'shipments-rules-v2'}
        with patch.object(recovery.sys.stdin, 'isatty', return_value=True), \
                patch.object(recovery.sys.stdout, 'isatty', return_value=True), \
                patch.object(recovery, 'resource_labels', return_value={'apicompass.purpose': 'assessment-recovery',
                    'apicompass.recovery': args.name}), \
                patch.object(recovery.getpass, 'getpass', side_effect=['PRIVATE_EMAIL', 'PRIVATE_PASSWORD']), \
                patch.object(recovery, 'command', return_value=json.dumps(result).encode()) as command:
            proof = recovery.login(args)
        self.assertTrue(proof['tool_answer_verified'])
        self.assertNotIn('PRIVATE_PASSWORD', repr(command.call_args.args))
        self.assertIn(b'PRIVATE_PASSWORD', command.call_args.kwargs['data'])

    def test_restore_excludes_admin_and_keeps_auth_file_in_tmpfs(self):
        self.assertIn('--nsInclude "APICompass.*"', recovery.RESTORE_COMMAND)
        self.assertIn('--authenticationDatabase admin', recovery.RESTORE_COMMAND)
        self.assertIn('trap', recovery.RESTORE_COMMAND)
        self.assertIn('/run/recovery-auth.yml', recovery.RESTORE_COMMAND)
        self.assertNotIn('--drop', recovery.RESTORE_COMMAND)
        self.assertIn('/proc/1/comm', recovery.MONGO_PING)

    def test_teardown_refuses_unowned_resource_before_any_removal(self):
        args = recovery.argparse.Namespace(name='apicompass-recovery-test1234', action='stop',
                                           confirm='remove-only-assessment-resources')
        with patch.object(recovery, 'owned_resources', side_effect=recovery.RecoveryError), \
                patch.object(recovery, 'command') as command:
            with self.assertRaises(recovery.RecoveryError):
                recovery.execute(args)
        command.assert_not_called()

    def test_inventory_includes_stopped_containers_for_partial_failure_cleanup(self):
        with patch.object(recovery, 'command', return_value=b'') as command:
            recovery.owned_resources('apicompass-recovery-test1234')
        container_call = next(c.args[0] for c in command.call_args_list if c.args[0][1] == 'container')
        self.assertIn('--all', container_call)

    def test_mongo_can_reach_final_pid_one_guard_without_docker_init(self):
        with patch.object(recovery, 'command', return_value=b'id') as command:
            recovery.create_container('apicompass-recovery-test1234', 'mongodb', 'mongo:8.0.20', {}, [])
        self.assertNotIn('--init', command.call_args.args[0])
        with patch.object(recovery, 'command', return_value=b'id') as command:
            recovery.create_container('apicompass-recovery-test1234', 'chat', 'image', {}, [])
        self.assertIn('--init', command.call_args.args[0])

    def test_recovery_container_overrides_inherited_production_image_labels(self):
        with patch.object(recovery, 'command', return_value=b'id') as command:
            recovery.create_container('apicompass-recovery-test1234', 'datacheck', 'image', {}, [])
        args = command.call_args.args[0]
        self.assertIn('com.docker.compose.project=', args)
        self.assertIn('com.docker.compose.service=', args)

    def test_datacheck_waits_through_cold_start_then_checks_known_answer(self):
        valid = json.dumps({'ready': {}, 'report': {}}).encode()
        with patch.object(recovery, 'command', side_effect=[recovery.RecoveryError(), valid]) as command, \
                patch.object(recovery.ops_jobs, 'valid_health', return_value=True) as health, \
                patch.object(recovery.time, 'sleep'):
            recovery.wait_datacheck('recovery-data', 'PRIVATE_TOKEN')
        self.assertEqual(command.call_count, 2)
        self.assertNotIn('PRIVATE_TOKEN', repr(command.call_args.args))
        health.assert_called_once()

    def test_datacheck_wait_has_bounded_failure(self):
        with patch.object(recovery, 'command', side_effect=recovery.RecoveryError()), \
                patch.object(recovery.time, 'monotonic', side_effect=[0, 1, 2, 121]), \
                patch.object(recovery.time, 'sleep'):
            with self.assertRaises(recovery.RecoveryError):
                recovery.wait_datacheck('recovery-data', 'PRIVATE_TOKEN')


if __name__ == '__main__':
    unittest.main()
