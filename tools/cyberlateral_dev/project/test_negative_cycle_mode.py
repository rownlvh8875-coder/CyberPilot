"""R26 mode and real parent publication gates, only external worker I/O doubled."""

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


def negative_cycle_observations():
    from integration_tools import negative_cycle_reference as reference
    rows = [{'index': index, 'accepted': True, 'model_steps': 1, 'model_expected_match': True,
             'prepared': reference.expected_input(index), 'model_output': reference.expected_output(index)} for index in range(99)]
    return complete_claims({'cases': rows, 'model_execution': 99, 'F61_execution': 0, 'actual_activation': 'NOT_ALLOWED',
                            'R_BUDGET': 'UNRESOLVED', 'STATIC_EVIDENCE_GATE': 'FAIL'}, 'R26')


class NegativeCycleModeTests(unittest.TestCase):
    def modules(self):
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        runner = importlib.import_module('native_qualification.run')
        worker = importlib.import_module('native_qualification.worker')
        self.assertIn('negative_cycle', inspect.signature(runner.qualify).parameters, 'Missing explicit R26 mode')
        return runner, worker

    def test_boolean_all_six_conflicts_and_missing_wheel_reject_before_native(self):
        runner, worker = self.modules()
        cases: list[tuple[dict[str, Any], str]] = [({'negative_cycle': True}, 'PUBLIC_WHEEL_REQUIRED'),
                                                 ({'negative_cycle': 1}, 'EXPLICIT_BOOLEAN_MODE')]
        cases.extend(({'negative_cycle': True, mode: True}, 'EXPERIMENT_MODE_CONFLICT')
                     for mode in ['owned_boundary', 'semantic_bridge', 'model_consumption', 'model_sequence', 'fault_boundaries', 'driver_boundaries'])
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            for kwargs, code in cases:
                with self.assertRaisesRegex(ValueError, code):
                    runner.qualify(root / 'python', root / 'native', root / 'output', **kwargs)
                with self.assertRaisesRegex(ValueError, code):
                    worker.observe(root / 'native', root / 'schema', **kwargs)
            self.assertFalse((root / 'output').exists())

    def test_wrong_wheel_and_existing_output_are_not_consumed_or_overwritten(self):
        runner, _ = self.modules()
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            wheel = root / 'wrong.whl'
            wheel.write_bytes(b'wrong')
            with self.assertRaisesRegex(ValueError, 'PUBLIC_WHEEL_IDENTITY'):
                runner.qualify(root / 'python', root / 'native', root / 'output', negative_cycle=True, package_wheel=wheel)
            with self.assertRaisesRegex(FileExistsError, 'OUTPUT_EXISTS'):
                runner.qualify(root / 'python', root / 'native', root, negative_cycle=True)
            self.assertEqual(wheel.read_bytes(), b'wrong')

    def run_workers(self, runner, root, data):
        completed = subprocess.CompletedProcess([], 0, runner.canonical({'observations': data, 'receipt': {}}), b'')
        with patch.object(runner, 'verify_experiment'), patch.object(runner, 'verify_inputs'), \
                patch.object(runner.subprocess, 'run', return_value=completed) as worker_io:
            result = runner.qualify(root / 'python', root / 'native', root / 'output', negative_cycle=True, package_wheel=root / 'public')
            self.assertIn('--negative-cycle', worker_io.call_args.args[0])
            return result

    def test_complete99_rows_publish_derived_counts_and_validated_reference(self):
        runner, _ = self.modules()
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            result = self.run_workers(runner, root, negative_cycle_observations())
            self.assertEqual((result['model_execution'], result['model_execution_per_worker']), (198, 99))
            self.assertEqual(result['status'], 'F70UGZ_R26_FIXED_SYNTHETIC_NEGATIVE_CYCLE_PASS')
            self.assertEqual(result['model_reference_sha256'], 'f3b60afc2e3ba8b100ee9dbcb2a125f9c27c797c3d6b4af7b882cc7c069390f8')
            self.assertTrue((root / 'output/SUMMARY.json').is_file())

    def test_equal_missing_counter_state_trace_or_bool_count_never_publish(self):
        runner, _ = self.modules()
        for problem in ['missing', 'counter', 'state', 'kind', 'count']:
            with tempfile.TemporaryDirectory() as scratch:
                root = Path(scratch)
                data = negative_cycle_observations()
                if problem == 'missing':
                    data['cases'].pop()
                elif problem == 'counter':
                    data['cases'][90]['model_output']['next_state']['angle_counter'] = 91
                elif problem == 'state':
                    data['cases'][95]['prepared']['state']['previous_applied'] = -12
                elif problem == 'kind':
                    data['cases'][89]['model_output']['trace']['downstream']['rate_clip']['result']['kind'] = 'numpy.int64'
                else:
                    data['cases'][0]['model_steps'] = True
                with self.assertRaisesRegex(ValueError, 'OBSERVATION_COVERAGE'):
                    self.run_workers(runner, root, data)
                self.assertFalse((root / 'output').exists())

    def test_missing_or_false_claims_stamp_reference_and_elapsed_time_never_publish(self):
        runner, _ = self.modules()
        for problem in ['missing', 'oracle', 'stamp', 'reference', 'time']:
            with tempfile.TemporaryDirectory() as scratch:
                root = Path(scratch)
                data = negative_cycle_observations()
                if problem == 'missing':
                    del data['actual_call_custody']
                elif problem == 'oracle':
                    data['cases'][94]['oracle_parity'] = False
                elif problem == 'stamp':
                    data['cases'][94]['stamp']['invocation_index'] = 93
                elif problem == 'reference':
                    data['model_reference_sha256'] = '0' * 64
                else:
                    data['time_semantics'] = 'ACTUAL_ELAPSED_10MS'
                with self.assertRaisesRegex(ValueError, 'OBSERVATION_CLAIMS'):
                    self.run_workers(runner, root, data)
                self.assertFalse((root / 'output').exists())


if __name__ == '__main__':
    unittest.main()
