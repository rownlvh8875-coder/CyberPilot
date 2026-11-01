"""Reject broken synthetic handoffs, hidden repair and poisoned whole-chain traces."""

import contextlib
import hashlib
import importlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from dataclasses import asdict, replace
from pathlib import Path
from unittest.mock import patch

from v1_helpers import ROOT, package_feature


class MessageHandoffTests(unittest.TestCase):
    def module(self):
        self.assertTrue((ROOT / 'integration_tools/message_handoff.py').is_file(), 'Missing planned fixed synthetic handoff')
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        package_feature()
        return importlib.import_module('integration_tools.message_handoff')

    def verifier(self):
        self.module()
        m = importlib.import_module('integration_tools.verify')
        self.assertTrue(callable(getattr(m, 'handoff_pair_summary', None)), 'Missing whole handoff acceptance')
        self.assertTrue(callable(getattr(m, 'verify_installed_handoff', None)), 'Missing installed handoff gate')
        return m

    def test_fixed_chain_full_golden_and_owned_trace(self):
        m, p = self.module(), package_feature()
        with patch.object(p, 'simulate', side_effect=AssertionError('NO_PREFIX_OR_BATCH_REPLACEMENT')):
            result = m.run_handoff_chain()
        self.assertEqual(result['status'], 'F70UGZ_R15_SYNTHETIC_HANDOFF_CHAIN_PASS')
        self.assertEqual((result['scenario_count'], result['extractor_calls'], result['model_steps'], result['prefix_validation_steps']), (7, 112, 112, 0))
        golden = json.loads((ROOT / 'reference/synthetic_harness_expected_v1.json').read_bytes())
        for row, expected in zip(result['scenarios'], golden['scenarios'], strict=True):
            self.assertEqual((row['id'], row['steps'], row['result_sha256']), (expected['id'], expected['steps'], expected['result_sha256']))
            self.assertEqual(hashlib.sha256(m.canonical(row['result'])).hexdigest(), expected['result_sha256'])
            for offset, prepared in enumerate(row['prepared']):
                previous = row['initial_state'] if offset == 0 else row['result']['outputs'][offset - 1]['next_state']
                self.assertEqual(prepared['state'], previous)
                self.assertEqual(prepared['sample'], row['source_samples'][offset])
                self.assertEqual(row['frames'][offset]['previous']['model_state'], previous)
                self.assertEqual(prepared['custody_claim'], 'SYNTHETIC_DECLARATION_ONLY')
        ramp = next(r for r in result['scenarios'] if r['id'] == 'ramp')
        inactive = next(r for r in result['scenarios'] if r['id'] == 'inactive')
        history = next(r for r in result['scenarios'] if r['id'] == 'history-scale')
        self.assertEqual([o['projection']['integer_command'] for o in ramp['result']['outputs']], [2, 4, 6])
        self.assertEqual([o['projection']['integer_command'] for o in inactive['result']['outputs']], [2, 0, 0, 2])
        self.assertEqual(history['seed_origin'], 'REGISTERED_SYNTHETIC_SEED_NOT_OBSERVED_PREHISTORY')
        self.assertEqual((history['result']['outputs'][0]['projection']['integer_command'],
                          history['result']['outputs'][0]['projection']['normalized_expression']), (95, 19.0))
        self.assertEqual(result['gates'], golden['required_gates'])

    def test_catalog_or_version_drift_before_work(self):
        m, p = self.module(), package_feature()
        catalog = package_feature('cyberlateral_dev.synthetic_catalog')
        with patch.object(p, 'step', side_effect=AssertionError('NO_MODEL')):
            with patch.object(p, '__version__', '0.3.1'), self.assertRaisesRegex(m.HandoffError, 'HANDOFF_IDENTITY'):
                m.run_handoff_chain()
            with patch.object(catalog, 'fixed_catalog', return_value=()), self.assertRaisesRegex(m.HandoffError, 'HANDOFF_IDENTITY'):
                m.run_handoff_chain()

    def test_source_encoding_mismatch_before_model(self):
        m, p = self.module(), package_feature()
        encode = m._encode

        def wrong_request(sample, state, sequence):
            frame = encode(sample, state, sequence)
            return replace(frame, cc=replace(frame.cc, actuators=replace(frame.cc.actuators, torque=0.2)))

        with patch.object(m, '_encode', side_effect=wrong_request), patch.object(p, 'step', side_effect=AssertionError('NO_MODEL')):
            with self.assertRaisesRegex(m.HandoffError, 'HANDOFF_PREPARED_MISMATCH'):
                m.run_handoff_chain()

    def test_wrong_owned_state_is_not_repaired(self):
        m, p = self.module(), package_feature()
        boundary = importlib.import_module('integration_tools.message_boundary')
        extract = boundary.extract_synthetic_message

        def wrong_candidate(frame):
            prepared = extract(frame)
            if prepared.state.index == 1:
                return replace(prepared, state=replace(prepared.state, previous_requested=1))
            return prepared

        with patch.object(boundary, 'extract_synthetic_message', side_effect=wrong_candidate), patch.object(p, 'step', wraps=p.step) as step:
            with self.assertRaisesRegex(m.HandoffError, 'HANDOFF_PREPARED_MISMATCH'):
                m.run_handoff_chain()
            self.assertEqual(step.call_count, 1, 'Invalid resumed state reached a new model step')

    def test_model_error_and_output_corruption_reject(self):
        m, p = self.module(), package_feature()
        error = ValueError('SYNTHETIC_MODEL_FAILURE')
        with patch.object(p, 'step', side_effect=error), self.assertRaises(m.HandoffError) as raised:
            m.run_handoff_chain()
        self.assertEqual(str(raised.exception), 'HANDOFF_MODEL_REJECTED')
        self.assertIs(raised.exception.__cause__, error)
        with patch.object(p, 'step', return_value=None), self.assertRaisesRegex(m.HandoffError, 'HANDOFF_MODEL_OUTPUT'):
            m.run_handoff_chain()
        step = p.step

        def wrong_output(sample, state):
            output = step(sample, state)
            return replace(output, projection=replace(output.projection, integer_command=output.projection.integer_command + 1))

        with patch.object(p, 'step', side_effect=wrong_output), self.assertRaisesRegex(m.HandoffError, 'HANDOFF_GOLDEN_MISMATCH'):
            m.run_handoff_chain()
        boundary = importlib.import_module('integration_tools.message_boundary')
        with patch.object(boundary, 'extract_synthetic_message', side_effect=error), self.assertRaises(m.HandoffError) as raised:
            m.run_handoff_chain()
        self.assertEqual(str(raised.exception), 'HANDOFF_EXTRACTION_REJECTED')
        self.assertIs(raised.exception.__cause__, error)

    def test_trace_and_gate_tampering_rejected(self):
        m, v = self.module(), self.verifier()
        original = m.run_handoff_chain()
        original['execution_environment'] = {'isolated': True, 'installed_package': True, 'numpy_available': False, 'forbidden_modules_loaded': []}
        with tempfile.TemporaryDirectory() as scratch:
            roots = [Path(scratch) / name for name in ['one', 'two']]
            for root in roots:
                root.mkdir()
            with self.assertRaisesRegex(ValueError, 'HANDOFF_ARTIFACT'):
                v.handoff_pair_summary(*roots)
            for mutation in ['empty', 'status', 'counts', 'extra', 'missing', 'result', 'source', 'frame', 'prepared', 'seed', 'gate', 'environment']:
                bad = deepcopy(original)
                if mutation == 'empty':
                    bad = {}
                elif mutation == 'status':
                    bad['status'] = 'NOT_PASS'
                elif mutation == 'counts':
                    bad['model_steps'] = 1
                elif mutation == 'extra':
                    bad['native_approved'] = True
                elif mutation == 'missing':
                    bad['scenarios'].pop()
                elif mutation == 'result':
                    row = bad['scenarios'][0]
                    row['result']['outputs'][0]['projection']['integer_command'] = 999
                    row['result_sha256'] = hashlib.sha256(m.canonical(row['result'])).hexdigest()
                elif mutation == 'source':
                    bad['scenarios'][-2]['source_samples'][0]['request'] = 0.0  # Negative-zero loss changes frozen catalog identity.
                elif mutation == 'frame':
                    bad['scenarios'][0]['frames'][0]['cc']['actuators']['torque'] = 0.2
                elif mutation == 'prepared':
                    bad['scenarios'][0]['prepared'][1]['state']['previous_requested'] = 1
                elif mutation == 'seed':
                    bad['scenarios'][-1]['seed_origin'] = 'OBSERVED_NATIVE_PREHISTORY'
                elif mutation == 'gate':
                    bad['gates']['STATIC_EVIDENCE_GATE'] = 'PASS'
                else:
                    bad['execution_environment']['numpy_available'] = True
                raw = m.canonical(bad)
                for root in roots:
                    (root / 'RESULTS.json').write_bytes(raw)
                    (root / 'SHA256SUMS.txt').write_text(hashlib.sha256(raw).hexdigest() + '  RESULTS.json\n')
                with self.subTest(mutation=mutation), self.assertRaisesRegex(ValueError, 'HANDOFF_CONTRACT'):
                    v.handoff_pair_summary(*roots)

    def test_existing_outputs_and_failed_publication(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            targets = [root / 'file', root / 'directory', root / 'dangling']
            targets[0].write_bytes(b'KEEP')
            targets[1].mkdir()
            targets[2].symlink_to(root / 'absent', target_is_directory=True)
            with patch.object(m, 'run_handoff_chain', side_effect=AssertionError('NO_WORK')):
                for target in targets:
                    with contextlib.redirect_stderr(io.StringIO()):
                        self.assertEqual(m.main(['--output', str(target)]), 2)
                for option in ['--data', '--native', '--source-root', '--seed', '--r', '--dt']:
                    with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
                        m.main(['--output', str(root / 'new'), option, 'UNSUPPORTED'])
                    self.assertEqual(raised.exception.code, 2)
            self.assertEqual(targets[0].read_bytes(), b'KEEP')
            self.assertEqual(list(targets[1].iterdir()), [])
            self.assertTrue(targets[2].is_symlink())
            self.assertFalse((root / 'new').exists())
            original = Path.open

            def fail_manifest(path, *args, **kwargs):
                if path.name == 'SHA256SUMS.txt':
                    raise OSError('SYNTHETIC_MANIFEST_FAILURE')
                return original(path, *args, **kwargs)

            with patch.object(Path, 'open', fail_manifest), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(m.main(['--output', str(root / 'failed')]), 2)
            self.assertFalse((root / 'failed/RESULTS.json').exists())

    def test_isolated_installed_pair(self):
        v = self.verifier()
        backend = importlib.import_module('build_backend')
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            name = backend.build_wheel(str(root / 'dist'))
            subprocess.run([sys.executable, '-B', '-m', 'venv', '--without-pip', str(root / 'env')], check=True, capture_output=True)
            py = root / 'env/bin/python'
            subprocess.run(['uv', 'pip', 'install', '--offline', '--no-deps', '--link-mode=copy', '--python', str(py), str(root / 'dist' / name)], check=True, capture_output=True)
            output = root / 'artifacts'
            output.mkdir()
            summary = v.verify_installed_handoff(ROOT, py, output, root)
            self.assertTrue(summary['byte_identical'])
            self.assertEqual((summary['scenario_count'], summary['model_steps']), (7, 112))
            record = json.loads((output / 'handoff_one/RESULTS.json').read_bytes())
            self.assertEqual(record['execution_environment'], {'isolated': True, 'installed_package': True, 'numpy_available': False, 'forbidden_modules_loaded': []})
            (output / 'handoff_two/RESULTS.json').write_bytes(b'{}\n')
            with self.assertRaisesRegex(ValueError, 'HANDOFF_ARTIFACT'):
                v.handoff_pair_summary(output / 'handoff_one', output / 'handoff_two')
            self.assertEqual(record['fixture_catalog_sha256'], '74095144882ff3977679ce92ec7dad0e7bf3f532a0cacae2cfa26f4aab0fd287')

    def test_repeat_has_no_hidden_state(self):
        m = self.module()
        self.assertEqual(m.canonical(m.run_handoff_chain()), m.canonical(m.run_handoff_chain()))
        p = package_feature()
        self.assertEqual(asdict(p.initial_state()), {'index': 0, 'previous_requested': None, 'previous_applied': 0, 'angle_counter': 0})


if __name__ == '__main__':
    unittest.main()
