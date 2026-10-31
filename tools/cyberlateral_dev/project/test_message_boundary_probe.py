"""B25-B28: actual isolated copy-only probing and complete literal evidence gates."""

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


class MessageBoundaryProbeTests(unittest.TestCase):
    def module(self):
        self.assertTrue((ROOT / 'integration_tools/message_boundary_probe.py').is_file(), 'Missing planned message boundary probe')
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        package_feature()
        return importlib.import_module('integration_tools.message_boundary_probe')

    def verifier(self):
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        m = importlib.import_module('integration_tools.verify')
        self.assertTrue(callable(getattr(m, 'message_boundary_pair_summary', None)), 'Missing complete message boundary gate')
        self.assertTrue(callable(getattr(m, 'verify_installed_message_boundary', None)), 'Missing installed message boundary gate')
        return m

    def golden(self):
        return json.loads((ROOT / 'reference/message_boundary_expected_v1.json').read_bytes())

    def write_pair(self, roots, data):
        raw = (json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode()
        for root in roots:
            (root / 'RESULTS.json').write_bytes(raw)
            (root / 'SHA256SUMS.txt').write_text(hashlib.sha256(raw).hexdigest() + '  RESULTS.json\n')

    def test_empty_installed_environment_probe(self):
        self.module()
        m = self.verifier()
        backend = importlib.import_module('build_backend')
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            name = backend.build_wheel(str(root / 'dist'))
            self.assertEqual(hashlib.sha256((root / 'dist' / name).read_bytes()).hexdigest(),
                             '3f3db36f62aa79ba97e4536a183b7e685a9d06c4e264d1fec9dd3bbda7c4d73c')
            subprocess.run([sys.executable, '-B', '-m', 'venv', '--without-pip', str(root / 'env')], check=True, capture_output=True)
            py = root / 'env/bin/python'
            subprocess.run(['uv', 'pip', 'install', '--offline', '--no-deps', '--link-mode=copy', '--python', str(py),
                            str(root / 'dist' / name)], check=True, capture_output=True)
            artifacts = root / 'artifacts'
            artifacts.mkdir()
            summary = m.verify_installed_message_boundary(ROOT, py, artifacts, root)
            self.assertEqual(summary['scenario_count'], 4)
            self.assertTrue(summary['byte_identical'])
            record = json.loads((artifacts / 'message_boundary_one/RESULTS.json').read_bytes())
            self.assertEqual(record['records'], self.golden()['records'])
            self.assertEqual(record['execution_environment'], {
                'isolated': True, 'installed_package': True, 'numpy_available': False, 'forbidden_modules_loaded': [],
            })
            self.assertEqual((record['model_transitions'], record['native_qualification']), (0, 'NOT_RUN_NOT_AUTHORIZED'))

    def test_new_output_only_and_last_publication(self):
        m, p = self.module(), package_feature()
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            targets = [root / 'file', root / 'dir', root / 'dangling']
            targets[0].write_bytes(b'KEEP')
            targets[1].mkdir()
            targets[2].symlink_to(root / 'absent', target_is_directory=True)
            with patch.object(m, 'run_message_boundary_probe', side_effect=AssertionError('NO_WORK')):
                for target in targets:
                    with contextlib.redirect_stderr(io.StringIO()):
                        self.assertEqual(m.main(['--output', str(target)]), 2)
                for option in ['--data', '--log', '--native', '--source-root', '--r', '--dt']:
                    with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
                        m.main(['--output', str(root / 'new'), option, 'UNSUPPORTED'])
                    self.assertEqual(raised.exception.code, 2)
            self.assertEqual(targets[0].read_bytes(), b'KEEP')
            self.assertEqual(list(targets[1].iterdir()), [])
            self.assertTrue(targets[2].is_symlink())
            self.assertFalse((root / 'new').exists())
            original_open = Path.open

            def fail_manifest(path, *args, **kwargs):
                if path.name == 'SHA256SUMS.txt':
                    raise OSError('SYNTHETIC_MANIFEST_FAILURE')
                return original_open(path, *args, **kwargs)

            with patch.object(Path, 'open', fail_manifest), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(m.main(['--output', str(root / 'write-failure')]), 2)
            self.assertFalse((root / 'write-failure/RESULTS.json').exists())
            with patch.object(p, '__file__', None), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(m.main(['--output', str(root / 'location-failure')]), 2)
            self.assertFalse((root / 'location-failure/RESULTS.json').exists())

    def test_full_artifact_and_gate_acceptance(self):
        probe, m = self.module(), self.verifier()
        original = probe.run_message_boundary_probe()
        original['execution_environment'] = {
            'isolated': True, 'installed_package': True, 'numpy_available': False, 'forbidden_modules_loaded': [],
        }
        self.assertEqual(original['records'], self.golden()['records'])
        with tempfile.TemporaryDirectory() as scratch:
            roots = [Path(scratch) / name for name in ['one', 'two']]
            for root in roots:
                root.mkdir()
            with self.assertRaisesRegex(ValueError, 'MISSING_MESSAGE_BOUNDARY_ARTIFACTS'):
                m.message_boundary_pair_summary(*roots)
            for mutation in ['empty', 'list', 'status', 'profile', 'source', 'count', 'model-work', 'native-claim',
                             'missing-records', 'reorder', 'numeric', 'state', 'hex', 'custody', 'scope', 'gate', 'extra', 'environment']:
                bad = deepcopy(original)
                if mutation == 'empty':
                    bad = {}
                elif mutation == 'list':
                    bad = []
                elif mutation == 'status':
                    bad['status'] = 'NOT_PASS'
                elif mutation in ['profile', 'source']:
                    bad['profile_id' if mutation == 'profile' else 'source_set_id'] = 'UNKNOWN'
                elif mutation == 'count':
                    bad['scenario_count'] = True
                elif mutation == 'model-work':
                    bad['model_transitions'] = 1
                elif mutation == 'native-claim':
                    bad['native_qualification'] = 'PASS'
                elif mutation == 'missing-records':
                    del bad['records']
                elif mutation == 'reorder':
                    bad['records'].reverse()
                elif mutation in ['numeric', 'state', 'hex', 'custody', 'scope']:
                    row = bad['records'][-1]
                    payload = row['payload']
                    if mutation == 'numeric':
                        payload['prepared']['sample']['request'] = 0.0  # -0.0 and0.0 compare numerically equal.
                    elif mutation == 'state':
                        payload['prepared']['state']['previous_applied'] = 999
                    elif mutation == 'hex':
                        payload['float_hex']['request'] = '0x0.0p+0'
                    elif mutation == 'custody':
                        payload['prepared']['custody_claim'] = 'NATIVE_HISTORY_VERIFIED'
                    else:
                        payload['prepared']['sample']['provenance'] = 'PRODUCTION'
                    row['sha256'] = hashlib.sha256(m.canonical(payload)).hexdigest()
                elif mutation == 'gate':
                    bad['gates']['STATIC_EVIDENCE_GATE'] = 'PASS'
                elif mutation == 'extra':
                    bad['approved_r'] = 1
                else:
                    bad['execution_environment']['numpy_available'] = True
                self.write_pair(roots, bad)
                with self.subTest(mutation=mutation), self.assertRaisesRegex(ValueError, 'MESSAGE_BOUNDARY_CONTRACT'):
                    m.message_boundary_pair_summary(*roots)

    def test_pair_reproduction_and_unchanged_wheel(self):
        probe, m = self.module(), self.verifier()
        record = probe.run_message_boundary_probe()
        self.assertEqual(record, probe.run_message_boundary_probe())
        for row in self.golden()['records']:
            self.assertEqual(hashlib.sha256(m.canonical(row['payload'])).hexdigest(), row['sha256'])
        with tempfile.TemporaryDirectory() as scratch:
            roots = [Path(scratch) / name for name in ['one', 'two']]
            for root in roots:
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(probe.main(['--output', str(root)]), 0)
            files = {p.name: p.read_bytes() for p in roots[0].iterdir()}
            self.assertEqual(set(files), {'RESULTS.json', 'SHA256SUMS.txt'})
            self.assertEqual(files, {p.name: p.read_bytes() for p in roots[1].iterdir()})
            self.assertEqual(files['RESULTS.json'], m.canonical(json.loads(files['RESULTS.json'])))
            self.assertEqual(files['SHA256SUMS.txt'], (hashlib.sha256(files['RESULTS.json']).hexdigest() + '  RESULTS.json\n').encode())
            (roots[1] / 'RESULTS.json').write_bytes(b'{}\n')
            with self.assertRaisesRegex(ValueError, 'REPRODUCTION_BYTE_MISMATCH'):
                m.message_boundary_pair_summary(*roots)
            record['execution_environment'] = {
                'isolated': True, 'installed_package': True, 'numpy_available': False, 'forbidden_modules_loaded': [],
            }
            self.write_pair(roots, record)
            for root in roots:
                (root / 'SHA256SUMS.txt').write_bytes(b'WRONG\n')
            with self.assertRaisesRegex(ValueError, 'MESSAGE_BOUNDARY_MANIFEST_MISMATCH'):
                m.message_boundary_pair_summary(*roots)


if __name__ == '__main__':
    unittest.main()
