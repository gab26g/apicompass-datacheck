import copy
import io
import json
import unittest
from unittest.mock import patch

from scripts import verify_restore as verify


class RestoreVerificationTests(unittest.TestCase):
    def target(self):
        return {'Name': '/apicompass-restore-test1234', 'State': {'Running': True},
                'Config': {'Labels': {'apicompass.purpose': 'isolated-restore'}},
                'HostConfig': {'NetworkMode': 'none', 'PortBindings': {}},
                'NetworkSettings': {'Networks': {'none': {}}},
                'Mounts': [{'Type': 'volume', 'Destination': '/data/db', 'Name': 'fresh-volume'}]}

    def test_isolation_rejects_network_ports_labels_and_shared_data(self):
        target = self.target()
        verify.validate_target(target, {'production-volume'})
        for section, key, value in [('HostConfig', 'NetworkMode', 'bridge'),
                                    ('HostConfig', 'PortBindings', {'27017/tcp': [{}]}),
                                    ('Config', 'Labels', {})]:
            bad = copy.deepcopy(target)
            bad[section][key] = value
            with self.assertRaises(verify.VerificationError):
                verify.validate_target(bad, {'production-volume'})
        with self.assertRaises(verify.VerificationError):
            verify.validate_target(target, {'fresh-volume'})

    def snapshot(self):
        return {'counts': {key: 1 for key in verify.COLLECTIONS},
                'known': {'conversation': 1, 'messages': 2, 'agent': 1, 'actions': 1},
                'ttl_indexes': {key: 0 for key in verify.COLLECTIONS}}

    def test_known_records_and_counts_must_match(self):
        baseline = self.snapshot()
        verify.compare(baseline, baseline)
        bad = copy.deepcopy(baseline)
        bad['counts']['messages'] += 1
        with self.assertRaises(verify.VerificationError):
            verify.compare(baseline, bad)
        bad = copy.deepcopy(baseline)
        bad['known']['actions'] = 0
        with self.assertRaises(verify.VerificationError):
            verify.compare(bad, bad)

    def test_untrusted_probe_output_is_not_accepted(self):
        bad = self.snapshot()
        bad['credential'] = 'PRIVATE_MARKER'
        with self.assertRaises(verify.VerificationError):
            verify.validate_snapshot(bad)
        bad = self.snapshot()
        bad['counts']['users'] = True
        with self.assertRaises(verify.VerificationError):
            verify.validate_snapshot(bad)

    def test_failed_output_never_contains_child_error(self):
        with patch.object(verify, 'run', side_effect=RuntimeError('PRIVATE_MARKER')), \
                patch('sys.stdout', new_callable=io.StringIO) as output:
            self.assertEqual(verify.main(['baseline', '--conversation-id', 'conv-123',
                                          '--agent-id', 'agent-123']), 1)
        self.assertNotIn('PRIVATE_MARKER', output.getvalue())
        self.assertEqual(json.loads(output.getvalue())['status'], 'failed')

    def test_probe_keeps_ids_in_stdin_and_does_not_read_documents(self):
        with patch.object(verify, 'command', return_value=json.dumps(self.snapshot()).encode()) as cmd:
            verify.probe('abcdef123456', 'conv-123', 'agent-123', authenticated=True)
        argv = cmd.call_args.args[0]
        self.assertNotIn('conv-123', repr(argv))
        self.assertNotIn('agent-123', repr(argv))
        self.assertNotIn('.find(', verify.PROBE)
        self.assertNotIn('metadata.api_key', verify.PROBE)


if __name__ == '__main__':
    unittest.main()
