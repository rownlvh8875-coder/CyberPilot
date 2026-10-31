"""Explicit R24 mode and real pre-publication rejection with external I/O doubled."""

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


def fault_observations():
    from integration_tools import fault_reference as reference
    rows = [{'index': index, 'accepted': True, 'model_steps': 1, 'model_expected_match': True,
             'prepared': reference.expected_input(index), 'model_output': reference.expected_output(index)} for index in range(96)]
    return complete_claims({'cases': rows, 'model_execution': 96, 'F61_execution': 0, 'actual_activation': 'NOT_ALLOWED',
                            'R_BUDGET': 'UNRESOLVED', 'STATIC_EVIDENCE_GATE': 'FAIL'}, 'R24')


class FaultModeTests(unittest.TestCase):
    def modules(self):
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        runner = importlib.import_module('native_qualification.run')
        worker = importlib.import_module('native_qualification.worker')
        self.assertIn('fault_boundaries', inspect.signature(runner.qualify).parameters, 'Missing explicit fault mode')
        return runner, worker

    def test_explicit_boolean_conflicts_and_missing_public_wheel_reject_before_native(self):
        runner, worker = self.modules()
        cases: list[tuple[dict[str, Any], str]] = [({'fault_boundaries': True}, 'PUBLIC_WHEEL_REQUIRED'),
                                                 ({'fault_boundaries': 1}, 'EXPLICIT_BOOLEAN_MODE')]
        cases.extend(({'fault_boundaries': True, mode: True}, 'EXPERIMENT_MODE_CONFLICT')
                     for mode in ['owned_boundary', 'semantic_bridge', 'model_consumption', 'model_sequence'])
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
                runner.qualify(root / 'python', root / 'native', root / 'output', fault_boundaries=True, package_wheel=wheel)
            with self.assertRaisesRegex(FileExistsError, 'OUTPUT_EXISTS'):
                runner.qualify(root / 'python', root / 'native', root, fault_boundaries=True)
            self.assertEqual(wheel.read_bytes(), b'wrong')

    def run_workers(self, runner, root, data):
        completed = subprocess.CompletedProcess([], 0, runner.canonical({'observations': data, 'receipt': {}}), b'')
        with patch.object(runner, 'verify_experiment'), patch.object(runner, 'verify_inputs'), \
                patch.object(runner.subprocess, 'run', return_value=completed) as worker_io:
            result = runner.qualify(root / 'python', root / 'native', root / 'output', fault_boundaries=True, package_wheel=root / 'public')
            self.assertIn('--fault-boundaries', worker_io.call_args.args[0])
            return result

    def test_validated96_counts_are_derived_not_fixed_or_coerced(self):
        runner, _ = self.modules()
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            result = self.run_workers(runner, root, fault_observations())
            self.assertEqual((result['model_execution'], result['model_execution_per_worker']), (192, 96))
            self.assertTrue((root / 'output/SUMMARY.json').is_file())

    def test_equal_missing_rows_wrong_counter_and_bool_counts_never_publish(self):
        runner, _ = self.modules()
        for problem in ['missing', 'counter', 'count']:
            with tempfile.TemporaryDirectory() as scratch:
                root = Path(scratch)
                data = fault_observations()
                if problem == 'missing':
                    data['cases'].pop()
                elif problem == 'counter':
                    data['cases'][90]['model_output']['next_state']['angle_counter'] = 91
                else:
                    data['cases'][0]['model_steps'] = True
                with self.assertRaisesRegex(ValueError, 'OBSERVATION_COVERAGE'):
                    self.run_workers(runner, root, data)
                self.assertFalse((root / 'output').exists())

    def test_auxiliary_claims_are_required_even_when_all_numeric_rows_match(self):
        runner, _ = self.modules()
        for problem in ['oracle', 'stamp', 'identity']:
            with tempfile.TemporaryDirectory() as scratch:
                root = Path(scratch)
                data = fault_observations()
                if problem == 'oracle':
                    data['cases'][90]['oracle_parity'] = False
                elif problem == 'stamp':
                    data['cases'][90]['stamp']['invocation_index'] = 89
                else:
                    data['identity'] = {}
                with self.assertRaisesRegex(ValueError, 'OBSERVATION_CLAIMS'):
                    self.run_workers(runner, root, data)
                self.assertFalse((root / 'output').exists())


if __name__ == '__main__':
    unittest.main()
