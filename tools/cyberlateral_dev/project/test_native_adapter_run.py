"""R28 runner preflight cannot overwrite artifacts or launch on wrong identity."""

import importlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from v1_helpers import ROOT


class AdapterRunnerTests(unittest.TestCase):
    def module(self):
        self.assertTrue((ROOT / 'native_qualification/adapter_run.py').is_file(), 'Missing R28 runner')
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        return importlib.import_module('native_qualification.adapter_run')

    def test_existing_output_preserved_before_work(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            output = root / 'existing'
            output.write_bytes(b'preserve')
            with self.assertRaisesRegex(FileExistsError, 'OUTPUT_EXISTS'):
                m.qualify(root / 'no-python', root / 'no-wheel', root / 'no-public', output, enabled=True)
            self.assertEqual(output.read_bytes(), b'preserve')

    def test_opt_in_bool_and_missing_parent_reject_before_work(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            for enabled, code in [(False, 'ADAPTER_OPT_IN_REQUIRED'), (1, 'ADAPTER_EXPLICIT_BOOL')]:
                with self.assertRaisesRegex(ValueError, code):
                    m.qualify(root / 'p', root / 'w', root / 'pub', root / 'out', enabled=enabled)
            with self.assertRaisesRegex(ValueError, 'ADAPTER_PARENT_REQUIRED'):
                m.qualify(root / 'p', root / 'w', root / 'pub', root / 'missing/out', enabled=True)

    def test_wrong_public_artifact_rejects_without_output(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            wrong = root / 'wrong.whl'
            wrong.write_bytes(b'wrong')
            with self.assertRaisesRegex(ValueError, 'PUBLIC_WHEEL_IDENTITY'):
                m.qualify(root / 'no-python', wrong, wrong, root / 'out', enabled=True)
            self.assertFalse((root / 'out').exists())

    def test_parent_import_is_inert(self):
        self.module()
        script = ('import sys;sys.path.insert(0,' + repr(str(ROOT)) + ');import native_qualification.adapter_run;'
                  'import native_qualification.adapter_runtime;'
                  'assert not any(n.split(".")[0] in {"capnp","cyberlateral_dev","numpy","openpilot","opendbc","cereal"} for n in sys.modules)')
        result = subprocess.run([sys.executable, '-I', '-B', '-c', script], capture_output=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
