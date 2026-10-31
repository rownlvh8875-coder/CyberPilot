"""R23 explicit mode and real parent publication gates with worker I/O doubled."""

import importlib
import inspect
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

from test_native_coverage import observations
from v1_helpers import ROOT


class SequenceModeTests(unittest.TestCase):
    def modules(self):
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        runner = importlib.import_module('native_qualification.run')
        worker = importlib.import_module('native_qualification.worker')
        self.assertIn('model_sequence', inspect.signature(runner.qualify).parameters, 'Missing explicit R23 mode')
        return runner, worker

    def test_types_wheel_and_every_conflicting_mode_reject_before_native(self):
        runner, worker = self.modules()
        invalid: list[tuple[dict[str, Any], str]] = [({'model_sequence': True}, 'PUBLIC_WHEEL_REQUIRED'),
                                                  ({'model_sequence': 1}, 'EXPLICIT_BOOLEAN_MODE')]
        invalid.extend(({'model_sequence': True, mode: True}, 'EXPERIMENT_MODE_CONFLICT')
                       for mode in ['owned_boundary', 'semantic_bridge', 'model_consumption'])
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            for kwargs, code in invalid:
                with self.assertRaisesRegex(ValueError, code):
                    runner.qualify(root / 'python', root / 'missing', root / 'output', **kwargs)
                with self.assertRaisesRegex(ValueError, code):
                    worker.observe(root / 'missing', root / 'schema', **kwargs)
            self.assertFalse((root / 'output').exists())

    def test_wrong_public_wheel_and_existing_output_reject(self):
        runner, _ = self.modules()
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            wheel = root / 'package.whl'
            wheel.write_bytes(b'not the pinned wheel')
            with self.assertRaisesRegex(ValueError, 'PUBLIC_WHEEL_IDENTITY'):
                runner.qualify(root / 'python', root / 'missing', root / 'output', model_sequence=True, package_wheel=wheel)
            with self.assertRaisesRegex(FileExistsError, 'OUTPUT_EXISTS'):
                runner.qualify(root / 'python', root / 'missing', root, model_sequence=True)
            self.assertEqual(wheel.read_bytes(), b'not the pinned wheel')

    def run_workers(self, runner, root, mode, record):
        # Only external process/file identity I/O is doubled. Canonical decoding,
        # equality, coverage, count derivation and filesystem publication are real.
        completed = subprocess.CompletedProcess([], 0, runner.canonical({'observations': record, 'receipt': {}}), b'')
        flag = 'model_consumption' if mode == 'R22' else 'model_sequence'
        with patch.object(runner, 'verify_experiment'), patch.object(runner, 'verify_inputs'), \
                patch.object(runner.subprocess, 'run', return_value=completed) as worker_io:
            result = runner.qualify(root / 'python', root / 'wheel', root / 'output', **{flag: True, 'package_wheel': root / 'package'})
            self.assertIn('--model-consumption' if mode == 'R22' else '--model-sequence', worker_io.call_args.args[0])
            return result

    def test_identical_reduced_coverage_workers_cannot_publish_pass_for_either_mode(self):
        runner, _ = self.modules()
        for mode in ['R22', 'R23']:
            with tempfile.TemporaryDirectory() as scratch:
                root = Path(scratch)
                record = observations(mode)
                record['cases'].pop()
                with self.assertRaisesRegex(ValueError, 'OBSERVATION_COVERAGE'):
                    self.run_workers(runner, root, mode, record)
                self.assertFalse((root / 'output').exists())

    def test_wrong_counts_and_lying_match_flags_do_not_create_output(self):
        runner, _ = self.modules()
        for mode in ['R22', 'R23']:
            for key, value in [('model_steps', True), ('model_steps', 0), ('model_expected_match', False)]:
                with tempfile.TemporaryDirectory() as scratch:
                    root = Path(scratch)
                    record = observations(mode)
                    record['cases'][0][key] = value
                    with self.assertRaisesRegex(ValueError, 'OBSERVATION_COVERAGE'):
                        self.run_workers(runner, root, mode, record)
                    self.assertFalse((root / 'output').exists())

    def test_validated_counts_and_source_mode_are_published(self):
        runner, _ = self.modules()
        for mode, count in [('R22', 5), ('R23', 4)]:
            with tempfile.TemporaryDirectory() as scratch:
                root = Path(scratch)
                result = self.run_workers(runner, root, mode, observations(mode))
                self.assertEqual(result['model_execution_per_worker'], count)
                self.assertEqual(result['model_execution'], 2 * count)
                self.assertTrue((root / 'output/SUMMARY.json').is_file())
                self.assertIn('NOT_UNIT_TEST_OR_STAGE_TOTAL', result['model_execution_scope'])

    def test_import_remains_native_free(self):
        before = set(sys.modules)
        self.modules()
        self.assertFalse(any(name.split('.')[0] in {'capnp', 'openpilot', 'opendbc', 'cereal'} for name in set(sys.modules) - before))


if __name__ == '__main__':
    unittest.main()
