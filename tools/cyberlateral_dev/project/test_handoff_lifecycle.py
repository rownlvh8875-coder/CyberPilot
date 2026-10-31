"""Pin real split/resume and independent-stream behavior through message extraction."""

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
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from v1_helpers import ROOT, package_feature


class HandoffLifecycleTests(unittest.TestCase):
    def module(self):
        self.assertTrue((ROOT / 'integration_tools/handoff_lifecycle.py').is_file(), 'Missing planned synthetic message lifecycle')
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        package_feature()
        return importlib.import_module('integration_tools.handoff_lifecycle')

    def verifier(self):
        self.module()
        v = importlib.import_module('integration_tools.verify')
        self.assertTrue(callable(getattr(v, 'verify_installed_lifecycle', None)), 'Missing installed lifecycle verification')
        return v

    def test_all_splits_and_interleaved_full_trace(self):
        m, p = self.module(), package_feature()
        with patch.object(p, 'simulate', side_effect=AssertionError('NO_BATCH_OR_PREFIX_REPLACEMENT')), patch.object(p, 'step', wraps=p.step) as step:
            result = m.run_lifecycle()
        self.assertEqual((result['scenario_count'], result['total_source_samples'], result['two_chunk_splits']), (7, 112, 105))
        self.assertEqual((result['extractor_calls'], result['model_steps'], result['prefix_validation_steps']), (9010, 9010, 0))
        self.assertEqual(step.call_count, 9010)
        baseline = result['baseline']
        golden = json.loads((ROOT / 'reference/synthetic_harness_expected_v1.json').read_bytes())
        for row, expected, splits in zip(baseline['scenarios'], golden['scenarios'], result['split_runs'], strict=True):
            self.assertEqual((row['id'], row['result_sha256']), (expected['id'], expected['result_sha256']))
            self.assertEqual(hashlib.sha256(m.canonical(row['result'])).hexdigest(), expected['result_sha256'])
            self.assertEqual(splits['id'], row['id'])
            self.assertEqual([cut['cut'] for cut in splits['cuts']], list(range(1, expected['steps'])))
            for cut in splits['cuts']:
                state = row['result']['outputs'][cut['cut'] - 1]['next_state']
                self.assertEqual(cut['prefix_final_state'], state)
                self.assertEqual(cut['resumed_prepared_state'], state)
                self.assertEqual(cut['result_sha256'], expected['result_sha256'])
                self.assertEqual(cut['frames_sha256'], hashlib.sha256(m.canonical(row['frames'])).hexdigest())
                self.assertEqual(cut['prepared_sha256'], hashlib.sha256(m.canonical(row['prepared'])).hexdigest())
        expected_events = []
        for offset in range(94):
            for row in baseline['scenarios']:
                if offset < row['steps']:
                    expected_events.append({'id': row['id'], 'offset': offset, 'frame': row['frames'][offset],
                                            'prepared': row['prepared'][offset], 'output': row['result']['outputs'][offset]})
        self.assertEqual(m.canonical(result['interleaved_events']), m.canonical(expected_events))
        rows = {row['id']: row for row in baseline['scenarios']}
        self.assertEqual([o['projection']['integer_command'] for o in rows['ramp']['result']['outputs']], [2, 4, 6])
        self.assertEqual([o['projection']['integer_command'] for o in rows['inactive']['result']['outputs']], [2, 0, 0, 2])
        self.assertEqual(rows['history-scale']['seed_origin'], 'REGISTERED_SYNTHETIC_SEED_NOT_OBSERVED_PREHISTORY')
        self.assertEqual(rows['history-scale']['result']['outputs'][0]['projection']['normalized_expression'], 19.0)
        self.assertEqual(result['gates'], golden['required_gates'])

    def test_second_catalog_drift_before_lifecycle_work(self):
        m, p = self.module(), package_feature()
        catalog = package_feature('cyberlateral_dev.synthetic_catalog')
        original = catalog.fixed_catalog()
        with patch.object(catalog, 'fixed_catalog', side_effect=[original, ()]), patch.object(p, 'step', wraps=p.step) as step:
            with self.assertRaisesRegex(m.LifecycleError, 'LIFECYCLE_CATALOG_DRIFT'):
                m.run_lifecycle()
            self.assertEqual(step.call_count, 112, 'A drifted second catalog reached lifecycle model work')

    def test_resumed_state_fault_rejected(self):
        m = self.module()
        chunk = m._chunk

        def broken_resume(samples, state, sequence):
            result = chunk(samples, state, sequence)
            if sequence == 'handoff_ramp' and state.index == 0 and len(samples) == 1:
                result['next_state'] = replace(result['next_state'], previous_requested=1)
            return result

        with patch.object(m, '_chunk', side_effect=broken_resume), self.assertRaisesRegex(m.LifecycleError, 'LIFECYCLE_SPLIT_MISMATCH:ramp:1'):
            m.run_lifecycle()

    def test_interleaved_fault_rejected(self):
        m = self.module()
        handoff = importlib.import_module('integration_tools.message_handoff')
        advance, calls = handoff._advance_owned, 0

        def foreign_stream_state(sample, state, sequence):
            nonlocal calls
            calls += 1
            if calls > 8898 and sequence == 'handoff_ramp' and state.index > 0:
                state = replace(state, previous_applied=state.previous_applied + 1)
            return advance(sample, state, sequence)

        with patch.object(handoff, '_advance_owned', side_effect=foreign_stream_state), self.assertRaisesRegex(m.LifecycleError, 'LIFECYCLE_INTERLEAVED_MISMATCH'):
            m.run_lifecycle()

    def test_complete_trace_tampering(self):
        m, v = self.module(), self.verifier()
        original = m.run_lifecycle()
        original['execution_environment'] = {'isolated': True, 'installed_package': True, 'numpy_available': False, 'forbidden_modules_loaded': []}
        mutations = [
            lambda r: r['split_runs'][0]['cuts'].pop(),
            lambda r: r['split_runs'][0]['cuts'].append(deepcopy(r['split_runs'][0]['cuts'][0])),
            lambda r: r['split_runs'][0]['cuts'][0].update(cut=4),
            lambda r: r['split_runs'][0]['cuts'].reverse(),
            lambda r: r['split_runs'][1]['cuts'][0]['prefix_final_state'].update(previous_requested=1),
            lambda r: r['split_runs'][1]['cuts'][0]['resumed_prepared_state'].update(previous_requested=1),
            lambda r: r['split_runs'][0]['cuts'][0].update(frames_sha256='0' * 64),
            lambda r: r['split_runs'][0]['cuts'][0].update(prepared_sha256='0' * 64),
            lambda r: r['split_runs'][0]['cuts'][0].update(result_sha256='0' * 64),
            lambda r: r['interleaved_events'].reverse(),
            lambda r: r['interleaved_events'].pop(),
            lambda r: r['interleaved_events'][0]['prepared']['state'].update(previous_applied=99),
            lambda r: r['interleaved_events'][0]['output']['next_state'].update(previous_applied=99),
            lambda r: r['baseline']['scenarios'][-1].update(seed_origin='OBSERVED_NATIVE_PREHISTORY'),
            lambda r: r['baseline']['scenarios'][-2]['source_samples'][0].update(request=0.0),
            lambda r: r.update(model_steps=112),
            lambda r: r['gates'].update(STATIC_EVIDENCE_GATE='PASS'),
            lambda r: r.update(native_approved=True),
            lambda r: r['execution_environment'].update(numpy_available=True),
        ]
        with tempfile.TemporaryDirectory() as scratch:
            roots = [Path(scratch) / name for name in ['one', 'two']]
            for root in roots:
                root.mkdir()
            with self.assertRaisesRegex(ValueError, 'LIFECYCLE_ARTIFACT'):
                v.lifecycle_pair_summary(*roots)
            for index, mutate in enumerate(mutations):
                bad = deepcopy(original)
                mutate(bad)
                raw = m.canonical(bad)
                for root in roots:
                    (root / 'RESULTS.json').write_bytes(raw)
                    (root / 'SHA256SUMS.txt').write_text(hashlib.sha256(raw).hexdigest() + '  RESULTS.json\n')
                with self.subTest(index=index), self.assertRaisesRegex(ValueError, 'LIFECYCLE_CONTRACT|HANDOFF_CONTRACT'):
                    v.lifecycle_pair_summary(*roots)
            raw = json.dumps(original, indent=2).encode()
            for root in roots:
                (root / 'RESULTS.json').write_bytes(raw)
                (root / 'SHA256SUMS.txt').write_text(hashlib.sha256(raw).hexdigest() + '  RESULTS.json\n')
            with self.assertRaisesRegex(ValueError, 'LIFECYCLE_CONTRACT_CANONICAL'):
                v.lifecycle_pair_summary(*roots)

    def test_existing_outputs_and_failed_publication(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            targets = [root / 'file', root / 'directory', root / 'dangling']
            targets[0].write_bytes(b'KEEP')
            targets[1].mkdir()
            targets[2].symlink_to(root / 'absent', target_is_directory=True)
            with patch.object(m, 'run_lifecycle', side_effect=AssertionError('NO_WORK')):
                for target in targets:
                    with contextlib.redirect_stderr(io.StringIO()):
                        self.assertEqual(m.main(['--output', str(target)]), 2)
                for option in ['--data', '--native', '--source-root', '--seed', '--r', '--dt']:
                    with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
                        m.main(['--output', str(root / 'new'), option, 'UNSUPPORTED'])
                    self.assertEqual(raised.exception.code, 2)
            self.assertEqual(targets[0].read_bytes(), b'KEEP')
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
        self.module()
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
            summary = v.verify_installed_lifecycle(ROOT, py, output, root)
            self.assertTrue(summary['byte_identical'])
            self.assertEqual((summary['scenario_count'], summary['two_chunk_splits'], summary['model_steps']), (7, 105, 9010))
            record = json.loads((output / 'lifecycle_one/RESULTS.json').read_bytes())
            self.assertEqual(record['execution_environment'], {'isolated': True, 'installed_package': True, 'numpy_available': False, 'forbidden_modules_loaded': []})
            (output / 'lifecycle_two/RESULTS.json').write_bytes(b'{}\n')
            with self.assertRaisesRegex(ValueError, 'LIFECYCLE_ARTIFACT'):
                v.lifecycle_pair_summary(output / 'lifecycle_one', output / 'lifecycle_two')

    def test_repeat_has_no_hidden_state(self):
        m = self.module()
        self.assertEqual(m.canonical(m.run_lifecycle()), m.canonical(m.run_lifecycle()))


if __name__ == '__main__':
    unittest.main()
