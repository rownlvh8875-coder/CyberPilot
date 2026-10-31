"""The native demonstration must be explicit and inert during pure CI."""

import importlib
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

from v1_helpers import ROOT


class OwnedNativeModeTests(unittest.TestCase):
    def demo(self):
        self.assertTrue((ROOT / 'native_qualification/owned_demo.py').is_file(), 'Missing closed owned-message demo')
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        return importlib.import_module('native_qualification.owned_demo')

    def test_demo_import_has_no_native_or_original_imports(self):
        before = set(sys.modules)
        self.demo()
        loaded = set(sys.modules) - before
        self.assertFalse(any(n.split('.')[0] in {'capnp', 'openpilot', 'opendbc', 'cereal'} for n in loaded))

    def test_non_boolean_mode_rejects_before_dependency_or_spawn(self):
        self.demo()
        runner = importlib.import_module('native_qualification.run')
        worker = importlib.import_module('native_qualification.worker')
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            invalid_modes: list[Any] = [None, 1, 'r20']  # Intentional malformed runtime input, not a valid typed call.
            for value in invalid_modes:
                with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'EXPLICIT_BOOLEAN_MODE'):
                    runner.qualify(root / 'missing-python', root / 'missing-wheel', root / 'output', owned_boundary=value)
                with self.subTest(worker=value), self.assertRaisesRegex(ValueError, 'EXPLICIT_BOOLEAN_MODE'):
                    worker.observe(root / 'missing-wheel', root / 'missing-schema', owned_boundary=value)
            self.assertFalse((root / 'output').exists())

    def test_opt_in_still_rejects_existing_output_before_spawn(self):
        self.demo()
        runner = importlib.import_module('native_qualification.run')
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            with self.assertRaisesRegex(FileExistsError, 'OUTPUT_EXISTS'):
                runner.qualify(root / 'missing-python', root / 'missing-wheel', root, owned_boundary=True)


if __name__ == '__main__':
    unittest.main()
