"""Explicit R22 mode gates fail before native input, output writes or step."""

import importlib
import inspect
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

from v1_helpers import ROOT, package_feature


class ModelModeTests(unittest.TestCase):
    def modules(self):
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        package_feature()
        runner = importlib.import_module('native_qualification.run')
        worker = importlib.import_module('native_qualification.worker')
        demo = importlib.import_module('native_qualification.semantic_demo')
        self.assertIn('model_consumption', inspect.signature(runner.qualify).parameters, 'Missing explicit R22 mode')
        self.assertIn('consume_model', inspect.signature(demo.demonstrate).parameters, 'Missing closed native consumption')
        return runner, worker, demo

    def test_import_is_native_and_original_application_free(self):
        before = set(sys.modules)
        self.modules()
        self.assertFalse(any(n.split('.')[0] in {'capnp', 'openpilot', 'opendbc', 'cereal'} for n in set(sys.modules) - before))

    def test_mode_conflicts_types_and_missing_wheel_before_input_or_spawn(self):
        runner, worker, _ = self.modules()
        invalid: list[tuple[dict[str, Any], str]] = [
            ({'model_consumption': True}, 'PUBLIC_WHEEL_REQUIRED'),
            ({'model_consumption': 1}, 'EXPLICIT_BOOLEAN_MODE'),
            ({'model_consumption': True, 'semantic_bridge': True}, 'EXPERIMENT_MODE_CONFLICT'),
            ({'model_consumption': True, 'owned_boundary': True}, 'EXPERIMENT_MODE_CONFLICT'),
        ]
        with tempfile.TemporaryDirectory() as scratch, patch.object(runner.subprocess, 'run') as spawn:
            root = Path(scratch)
            for kwargs, code in invalid:
                with self.subTest(kwargs=kwargs), self.assertRaisesRegex(ValueError, code):
                    runner.qualify(root / 'python', root / 'absent-native', root / 'output', **kwargs)
                with self.assertRaisesRegex(ValueError, code):
                    worker.observe(root / 'absent-native', root / 'absent-schema', **kwargs)
            self.assertFalse((root / 'output').exists())
            spawn.assert_not_called()

    def test_bad_public_wheel_and_symlink_reject_before_native(self):
        runner, _, _ = self.modules()
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            wheel = root / 'wrong.whl'
            wheel.write_bytes(b'not the sealed wheel')
            alias = root / 'alias.whl'
            alias.symlink_to(wheel)
            for candidate in (wheel, alias):
                with self.assertRaisesRegex(ValueError, 'PUBLIC_WHEEL_IDENTITY'):
                    runner.qualify(root / 'python', root / 'absent-native', root / 'output',
                                   model_consumption=True, package_wheel=candidate)
            self.assertFalse((root / 'output').exists())

    def test_existing_output_is_never_overwritten(self):
        runner, _, _ = self.modules()
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            marker = root / 'preserve'
            marker.write_bytes(b'unchanged')
            with self.assertRaisesRegex(FileExistsError, 'OUTPUT_EXISTS'):
                runner.qualify(root / 'python', root / 'absent-native', root, model_consumption=True)
            self.assertEqual(marker.read_bytes(), b'unchanged')

    def test_demo_requires_explicit_builtin_boolean_before_touching_native(self):
        _, _, demo = self.modules()
        for value in [1, 'yes', None]:
            with self.assertRaisesRegex(ValueError, 'EXPLICIT_BOOLEAN_MODE'):
                demo.demonstrate(None, consume_model=value)

    def test_empty_legacy_demo_performs_no_model_work(self):
        # The real native path is exercised separately; no fake native objects.
        _, _, demo = self.modules()
        with patch.object(demo, '_make', side_effect=RuntimeError('stop-before-native')), patch.object(demo.p, 'step') as step:
            with self.assertRaisesRegex(RuntimeError, 'stop-before-native'):
                demo.demonstrate(None)
            step.assert_not_called()


if __name__ == '__main__':
    unittest.main()
