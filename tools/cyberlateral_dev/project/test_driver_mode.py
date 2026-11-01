"""R25 opt-in and parent gates: process I/O doubled, real validation/publication."""

import importlib
import inspect
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

from native_claim_fixture import complete_claims
from v1_helpers import ROOT


def driver_observations():
    from integration_tools import driver_reference as reference
    rows = [{'index': index, 'accepted': True, 'model_steps': 1, 'model_expected_match': True,
             'prepared': reference.expected_input(index), 'model_output': reference.expected_output(index)} for index in range(20)]
    return complete_claims({'cases': rows, 'model_execution': 20, 'F61_execution': 0, 'actual_activation': 'NOT_ALLOWED',
                            'R_BUDGET': 'UNRESOLVED', 'STATIC_EVIDENCE_GATE': 'FAIL'}, 'R25')


class DriverModeTests(unittest.TestCase):
    def modules(self):
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        runner = importlib.import_module('native_qualification.run')
        worker = importlib.import_module('native_qualification.worker')
        self.assertIn('driver_boundaries', inspect.signature(runner.qualify).parameters, 'Missing explicit R25 mode')
        return runner, worker

    def test_boolean_conflicts_and_missing_public_wheel_reject_before_native(self):
        runner, worker = self.modules()
        cases: list[tuple[dict[str, Any], str]] = [({'driver_boundaries': True}, 'PUBLIC_WHEEL_REQUIRED'),
                                                 ({'driver_boundaries': 1}, 'EXPLICIT_BOOLEAN_MODE')]
        cases.extend(({'driver_boundaries': True, mode: True}, 'EXPERIMENT_MODE_CONFLICT')
                     for mode in ['owned_boundary', 'semantic_bridge', 'model_consumption', 'model_sequence', 'fault_boundaries'])
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            for kwargs, code in cases:
                with self.assertRaisesRegex(ValueError, code):
                    runner.qualify(root / 'python', root / 'native', root / 'output', **kwargs)
                with self.assertRaisesRegex(ValueError, code):
                    worker.observe(root / 'native', root / 'schema', **kwargs)
            self.assertFalse((root / 'output').exists())

    def test_wrong_public_wheel_and_existing_output_preserved(self):
        runner, _ = self.modules()
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            wheel = root / 'wrong.whl'
            wheel.write_bytes(b'wrong')
            with self.assertRaisesRegex(ValueError, 'PUBLIC_WHEEL_IDENTITY'):
                runner.qualify(root / 'python', root / 'native', root / 'output', driver_boundaries=True, package_wheel=wheel)
            with self.assertRaisesRegex(FileExistsError, 'OUTPUT_EXISTS'):
                runner.qualify(root / 'python', root / 'native', root, driver_boundaries=True)
            self.assertEqual(wheel.read_bytes(), b'wrong')

    def run_workers(self, runner, root, data):
        completed = subprocess.CompletedProcess([], 0, runner.canonical({'observations': data, 'receipt': {}}), b'')
        with patch.object(runner, 'verify_experiment'), patch.object(runner, 'verify_inputs'), \
                patch.object(runner.subprocess, 'run', return_value=completed) as worker_io:
            result = runner.qualify(root / 'python', root / 'native', root / 'output', driver_boundaries=True, package_wheel=root / 'public')
            self.assertIn('--driver-boundaries', worker_io.call_args.args[0])
            return result

    def test_complete20_rows_publish_validated_counts_and_active_reference(self):
        runner, _ = self.modules()
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            result = self.run_workers(runner, root, driver_observations())
            self.assertEqual((result['model_execution'], result['model_execution_per_worker']), (40, 20))
            self.assertEqual(result['status'], 'F70UGZ_R25_FIXED_SYNTHETIC_NEGATIVE_DRIVER_PASS')
            self.assertEqual(result['model_reference_sha256'], '21de9d95fa3e45dd03fe5ac8da0505a4ea94d233dc81d21ba65d741573ef1fa7')
            self.assertTrue((root / 'output/SUMMARY.json').is_file())

    def test_missing_rows_wrong_float_kind_or_bool_counts_never_publish(self):
        runner, _ = self.modules()
        for problem in ['missing', 'kind', 'count', 'state']:
            with tempfile.TemporaryDirectory() as scratch:
                root = Path(scratch)
                data = driver_observations()
                if problem == 'missing':
                    data['cases'].pop()
                elif problem == 'kind':
                    data['cases'][5]['model_output']['trace']['downstream']['rate_clip']['result']['kind'] = 'numpy.int64'
                elif problem == 'state':
                    data['cases'][17]['prepared']['state']['previous_applied'] = -12
                else:
                    data['cases'][0]['model_steps'] = True
                with self.assertRaisesRegex(ValueError, 'OBSERVATION_COVERAGE'):
                    self.run_workers(runner, root, data)
                self.assertFalse((root / 'output').exists())

    def test_false_or_missing_claims_stamp_and_reference_never_publish(self):
        runner, _ = self.modules()
        for problem in ['oracle', 'missing', 'stamp', 'reference']:
            with tempfile.TemporaryDirectory() as scratch:
                root = Path(scratch)
                data = driver_observations()
                if problem == 'oracle':
                    data['cases'][16]['oracle_parity'] = False
                elif problem == 'missing':
                    del data['actual_call_custody']
                elif problem == 'stamp':
                    data['cases'][16]['stamp']['invocation_index'] = 15
                else:
                    data['model_reference_sha256'] = '0' * 64
                with self.assertRaisesRegex(ValueError, 'OBSERVATION_CLAIMS'):
                    self.run_workers(runner, root, data)
                self.assertFalse((root / 'output').exists())


if __name__ == '__main__':
    unittest.main()
