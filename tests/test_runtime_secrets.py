"""Offline runtime security tests; no AWS calls, Docker mutations or real secrets."""
import io
import json
import subprocess
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import Mock, patch

from scripts import runtime_secrets as runtime


def fixture():
    return {
        'JWT_SECRET': '1' * 64, 'JWT_REFRESH_SECRET': '2' * 64,
        'CREDS_KEY': '3' * 64, 'CREDS_IV': '4' * 32,
        'MONGO_ROOT_PASSWORD': '5' * 40,
        'MONGO_APP_PASSWORD': '6' * 40,
        'DATACHECK_API_TOKEN': '7' * 64, 'GOOGLE_KEY': 'test-provider-key-never-real',
    }


HOST = {'APICOMPASS_HOSTNAME': 'test.example.com',
        'DATACHECK_S3_BUCKET': 'test-fixtures-only', 'AWS_REGION': 'ap-southeast-1'}


class RuntimeSecretTests(unittest.TestCase):
    def client(self, value=None, kind='SecureString'):
        client = Mock()
        client.get_parameter.return_value = {'Parameter': {
            'Name': runtime.PARAMETER, 'Type': kind,
            'Value': json.dumps(fixture() if value is None else value)}}
        return client

    def test_one_exact_decrypted_securestring_read(self):
        client = self.client()
        env = runtime.load_environment(HOST, client)
        client.get_parameter.assert_called_once_with(Name='/apicompass/prod/runtime', WithDecryption=True)
        self.assertEqual(env['GOOGLE_KEY'], fixture()['GOOGLE_KEY'])
        self.assertIn('@mongodb:27017/APICompass?authSource=APICompass', env['MONGO_URI'])

    def test_missing_unknown_duplicate_and_nonobject_json_fail_closed(self):
        missing = fixture()
        missing.pop('GOOGLE_KEY')
        for raw in [json.dumps(missing), json.dumps({**fixture(), 'EXTRA': 'hidden'}),
                    '[]', 'null', '{broken', '{"JWT_SECRET":"a","JWT_SECRET":"b"}']:
            with self.subTest(raw_type=type(raw).__name__), self.assertRaises(runtime.RuntimeConfigurationError):
                runtime.validate_runtime(raw)

    def test_invalid_or_placeholder_fields_fail_closed(self):
        cases = [('JWT_SECRET', 123), ('DATACHECK_API_TOKEN', ''),
                 ('GOOGLE_KEY', 'user_provided'), ('CREDS_KEY', 'g' * 64),
                 ('CREDS_IV', 'a' * 31), ('MONGO_APP_PASSWORD', 'short'),
                 ('MONGO_ROOT_PASSWORD', 'long\n' * 10),
                 ('JWT_REFRESH_SECRET', 'a' * 4097)]
        for name, value in cases:
            with self.subTest(field=name), self.assertRaises(runtime.RuntimeConfigurationError):
                runtime.validate_runtime(json.dumps({**fixture(), name: value}))

    def test_security_keys_cannot_be_reused(self):
        with self.assertRaises(runtime.RuntimeConfigurationError):
            runtime.validate_runtime(json.dumps({**fixture(), 'JWT_REFRESH_SECRET': fixture()['JWT_SECRET']}))

    def test_plain_string_wrong_parameter_or_aws_failure_is_safe(self):
        client = self.client(kind='String')
        with self.assertRaises(runtime.RuntimeConfigurationError):
            runtime.load_runtime(HOST['AWS_REGION'], client)
        client = self.client()
        client.get_parameter.return_value['Parameter']['Name'] = '/wrong'
        with self.assertRaises(runtime.RuntimeConfigurationError):
            runtime.load_runtime(HOST['AWS_REGION'], client)
        client.get_parameter.side_effect = RuntimeError('secret-provider-response')
        with self.assertRaises(runtime.RuntimeConfigurationError) as caught:
            runtime.load_runtime(HOST['AWS_REGION'], client)
        self.assertNotIn('secret-provider-response', str(caught.exception))

    def test_invalid_host_fails_before_reading_secrets(self):
        for name, value in [('APICOMPASS_HOSTNAME', 'https://test.example.com'),
                            ('APICOMPASS_HOSTNAME', 'example.com:443'),
                            ('APICOMPASS_HOSTNAME', '*.example.com'),
                            ('DATACHECK_S3_BUCKET', ''), ('AWS_REGION', 'bad/region')]:
            client = self.client()
            with self.subTest(field=name), self.assertRaises(runtime.RuntimeConfigurationError):
                runtime.load_environment({**HOST, name: value}, client)
            client.get_parameter.assert_not_called()

    def test_uri_encodes_password_and_overrides_ambient_compose(self):
        secrets = {**fixture(), 'MONGO_APP_PASSWORD': 'a' * 32 + ':/$@?%#'}
        base = {**HOST, 'COMPOSE_FILE': 'evil.yaml', 'COMPOSE_PROJECT_NAME': 'local',
                'MONGO_URI': 'wrong', 'GOOGLE_KEY': 'ambient-wrong'}
        env = runtime.build_environment(secrets, base)
        self.assertIn('%3A%2F%24%40%3F%25%23@mongodb', env['MONGO_URI'])
        self.assertNotIn('COMPOSE_FILE', env)
        self.assertNotIn('COMPOSE_PROJECT_NAME', env)
        self.assertEqual(env['COMPOSE_DISABLE_ENV_FILE'], '1')
        self.assertEqual(base['MONGO_URI'], 'wrong')

    def test_compose_uses_env_and_never_secret_argv_or_child_error_output(self):
        runner = Mock(return_value=subprocess.CompletedProcess([], 1, b'secret-stdout', b'secret-stderr'))
        env = runtime.build_environment(fixture(), HOST)
        with self.assertRaises(runtime.RuntimeConfigurationError) as caught:
            runtime.run_compose(['up', '--detach'], env, runner)
        args, kwargs = runner.call_args
        self.assertEqual(kwargs['env'], env)
        self.assertTrue(kwargs['capture_output'])
        self.assertIn('apicompass-prod', args[0])
        self.assertNotIn(fixture()['GOOGLE_KEY'], ' '.join(args[0]))
        self.assertNotIn('secret-', str(caught.exception))

    def test_cli_does_not_echo_secrets_or_tracebacks_on_aws_error(self):
        output = io.StringIO()
        with patch.dict('os.environ', HOST, clear=True), patch.object(runtime, 'load_runtime',
                side_effect=runtime.RuntimeConfigurationError('Cannot read the production SecureString using the host role.')):
            with redirect_stderr(output), redirect_stdout(output):
                self.assertEqual(runtime.main(['up']), 1)
        self.assertNotIn('Traceback', output.getvalue())
        self.assertNotIn(fixture()['GOOGLE_KEY'], output.getvalue())

    def test_start_uses_wait_and_brand_before_compose(self):
        order = []
        with patch.object(runtime, 'load_environment', return_value={}), \
                patch.object(runtime, 'prepare_brand', side_effect=lambda: order.append('brand')), \
                patch.object(runtime, 'run_compose', side_effect=lambda args, env: order.append(args)), \
                redirect_stdout(io.StringIO()):
            self.assertEqual(runtime.main(['up']), 0)
        self.assertEqual(order[0], 'brand')
        self.assertIn('--wait', order[1])


if __name__ == '__main__':
    unittest.main()
