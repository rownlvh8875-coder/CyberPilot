"""Catch partial evidence publication and weak installed DEV bridge acceptance."""

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
from pathlib import Path
from unittest.mock import patch

from v1_helpers import ROOT, package_feature


class DevBridgeProbeTests(unittest.TestCase):
    def module(self):
        self.assertTrue((ROOT / 'integration_tools/dev_bridge_probe.py').is_file(), 'Missing planned DEV bridge probe')
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        package_feature()
        return importlib.import_module('integration_tools.dev_bridge_probe')

    def verifier(self):
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        m = importlib.import_module('integration_tools.verify')
        self.assertTrue(callable(getattr(m, 'bridge_pair_summary', None)), 'Missing DEV bridge artifact acceptance')
        self.assertTrue(callable(getattr(m, 'verify_installed_bridge', None)), 'Missing installed DEV bridge gate')
        return m

    def valid_record(self):
        result = self.module().run_bridge_probe()
        result['execution_environment'] = {
            'isolated': True, 'installed_package': True, 'numpy_available': False, 'forbidden_modules_loaded': [],
        }
        return result

    def write_pair(self, roots, data):
        raw = (json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode()
        for directory in roots:
            (directory / 'RESULTS.json').write_bytes(raw)
            (directory / 'SHA256SUMS.txt').write_text(hashlib.sha256(raw).hexdigest() + '  RESULTS.json\n')

    def test_probe_contains_full_fixed_outputs_final_sessions_and_closed_gates(self):
        record = self.module().run_bridge_probe()
        self.assertEqual(record['status'], 'F70UGZ_R12_FIXED_SYNTHETIC_DEV_BRIDGE_PASS')
        self.assertEqual((record['scenario_count'], record['total_steps']), (7, 112))
        golden = json.loads((ROOT / 'reference/synthetic_harness_expected_v1.json').read_bytes())
        for row, expected in zip(record['scenarios'], golden['scenarios'], strict=True):
            self.assertEqual((row['id'], row['steps'], row['result_sha256']), (expected['id'], expected['steps'], expected['result_sha256']))
            raw = (json.dumps(row['result'], sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), expected['result_sha256'])
            self.assertEqual(row['final_session']['model_state'], row['result']['next_state'])
            self.assertEqual(row['final_session']['next_offset'], expected['steps'])
        self.assertEqual(record['gates'], golden['required_gates'])
        self.assertEqual(record, self.module().run_bridge_probe())

    def test_existing_paths_and_unknown_modes_reject_before_probe_work(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            targets = [root / 'file', root / 'directory', root / 'dangling']
            targets[0].write_bytes(b'KEEP')
            targets[1].mkdir()
            targets[2].symlink_to(root / 'absent', target_is_directory=True)
            with patch.object(m, 'run_bridge_probe', side_effect=AssertionError('NO_PROBE')):
                for target in targets:
                    with contextlib.redirect_stderr(io.StringIO()):
                        self.assertEqual(m.main(['--output', str(target)]), 2)
                for option in ['--data', '--log', '--source-root', '--rate-budget-per-s', '--dt']:
                    with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
                        m.main(['--output', str(root / 'new'), option, 'UNSUPPORTED'])
                    self.assertEqual(raised.exception.code, 2)
            self.assertEqual(targets[0].read_bytes(), b'KEEP')
            self.assertEqual(list(targets[1].iterdir()), [])
            self.assertTrue(targets[2].is_symlink())
            self.assertFalse((root / 'new').exists())

    def test_manifest_failure_never_publishes_designated_pass_result(self):
        m = self.module()
        original = Path.open

        def fail_manifest(path, *args, **kwargs):
            if path.name == 'SHA256SUMS.txt':
                raise OSError('SYNTHETIC_MANIFEST_FAILURE')
            return original(path, *args, **kwargs)

        with tempfile.TemporaryDirectory() as scratch:
            output = Path(scratch) / 'out'
            with patch.object(Path, 'open', fail_manifest), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(m.main(['--output', str(output)]), 2)
            self.assertFalse((output / 'RESULTS.json').exists())

    def test_missing_package_location_rejects_without_pass_publication(self):
        m, p = self.module(), package_feature()
        with tempfile.TemporaryDirectory() as scratch:
            output = Path(scratch) / 'out'
            with patch.object(p, '__file__', None), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(m.main(['--output', str(output)]), 2)
            self.assertFalse((output / 'RESULTS.json').exists())

    def test_missing_or_identically_malformed_artifacts_are_not_success(self):
        m = self.verifier()
        with tempfile.TemporaryDirectory() as scratch:
            roots = [Path(scratch) / name for name in ['one', 'two']]
            for root in roots:
                root.mkdir()
            with self.assertRaisesRegex(ValueError, 'MISSING_BRIDGE_ARTIFACTS'):
                m.bridge_pair_summary(*roots)
            for data in [{}, [], None]:
                self.write_pair(roots, data)
                with self.assertRaisesRegex(ValueError, 'BRIDGE_CONTRACT'):
                    m.bridge_pair_summary(*roots)

    def test_identical_tampering_with_valid_checksums_cannot_bypass_full_contract(self):
        m, original = self.verifier(), self.valid_record()
        with tempfile.TemporaryDirectory() as scratch:
            roots = [Path(scratch) / name for name in ['one', 'two']]
            for root in roots:
                root.mkdir()
            mutations = ['status', 'count', 'profile', 'source', 'fixture', 'missing-scenarios', 'reorder',
                         'result', 'final-state', 'session-sequence', 'session-scope', 'gate', 'extra-claim', 'environment']
            for mutation in mutations:
                bad = deepcopy(original)
                if mutation == 'status':
                    bad['status'] = 'NOT_PASS'
                elif mutation == 'count':
                    bad['total_steps'] = True
                elif mutation == 'profile':
                    bad['profile_id'] = 'UNKNOWN'
                elif mutation == 'source':
                    bad['source_set_id'] = 'OLD_AJOUATOM'
                elif mutation == 'fixture':
                    bad['fixture_catalog_sha256'] = '0' * 64
                elif mutation == 'missing-scenarios':
                    del bad['scenarios']
                elif mutation == 'reorder':
                    bad['scenarios'].reverse()
                elif mutation == 'result':
                    row = bad['scenarios'][0]
                    row['result']['outputs'][0]['projection']['integer_command'] = 999
                    row['result_sha256'] = hashlib.sha256(m.canonical(row['result'])).hexdigest()
                elif mutation == 'final-state':
                    bad['scenarios'][0]['final_session']['model_state']['previous_applied'] = 999
                elif mutation == 'session-sequence':
                    bad['scenarios'][0]['final_session']['sequence_id'] = 'OTHER'
                elif mutation == 'session-scope':
                    bad['scenarios'][0]['final_session']['scope'] = 'PRODUCTION'
                elif mutation == 'gate':
                    bad['gates']['STATIC_EVIDENCE_GATE'] = 'PASS'
                elif mutation == 'extra-claim':
                    bad['production_approved'] = True
                else:
                    bad['execution_environment']['forbidden_modules_loaded'] = ['numpy']
                self.write_pair(roots, bad)
                with self.subTest(mutation=mutation), self.assertRaisesRegex(ValueError, 'BRIDGE_CONTRACT'):
                    m.bridge_pair_summary(*roots)

    def test_pair_mismatch_or_bad_manifest_rejects(self):
        m, record = self.verifier(), self.valid_record()
        with tempfile.TemporaryDirectory() as scratch:
            roots = [Path(scratch) / name for name in ['one', 'two']]
            for root in roots:
                root.mkdir()
            self.write_pair(roots, record)
            (roots[1] / 'RESULTS.json').write_bytes(b'{}\n')
            with self.assertRaisesRegex(ValueError, 'REPRODUCTION_BYTE_MISMATCH'):
                m.bridge_pair_summary(*roots)
            self.write_pair(roots, record)
            for root in roots:
                (root / 'SHA256SUMS.txt').write_bytes(b'WRONG\n')
            with self.assertRaisesRegex(ValueError, 'BRIDGE_MANIFEST_MISMATCH'):
                m.bridge_pair_summary(*roots)

    def test_real_isolated_installed_wheel_probe_pair(self):
        self.module()
        m = self.verifier()
        backend = importlib.import_module('build_backend')
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            name = backend.build_wheel(str(root / 'dist'))
            subprocess.run([sys.executable, '-B', '-m', 'venv', '--without-pip', str(root / 'env')], check=True, capture_output=True)
            python = root / 'env/bin/python'
            subprocess.run(['uv', 'pip', 'install', '--offline', '--no-deps', '--link-mode=copy', '--python', str(python),
                            str(root / 'dist' / name)], check=True, capture_output=True)
            output = root / 'artifacts'
            output.mkdir()
            result = m.verify_installed_bridge(ROOT, python, output, root)
            self.assertTrue(result['byte_identical'])
            self.assertEqual((result['scenario_count'], result['total_steps']), (7, 112))
            record = json.loads((output / 'bridge_one/RESULTS.json').read_bytes())
            self.assertEqual(record['execution_environment'], {
                'isolated': True, 'installed_package': True, 'numpy_available': False, 'forbidden_modules_loaded': [],
            })
            (output / 'bridge_one/RESULTS.json').unlink()
            with self.assertRaisesRegex(ValueError, 'REPRODUCTION_BYTE_MISMATCH'):
                m.bridge_pair_summary(output / 'bridge_one', output / 'bridge_two')


if __name__ == '__main__':
    unittest.main()
