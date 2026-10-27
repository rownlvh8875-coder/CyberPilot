"""Reproduce the two original compatibility checks with repository-relative paths."""
import importlib.util
import json
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / 'tools/cyberpilot/f70s'
FILES = ['f70_synthetic_exact_reference.py', 'f70_synthetic_exact_audit.py',
         'test_f70_synthetic_exact_reference.py', 'run_f70_synthetic_exact_reference.py']


class CompatibilityTests(unittest.TestCase):
  def test_repository_native_lint(self):
    program = shutil.which('ruff')
    self.assertIsNotNone(program, 'locked Ruff must be restored before this compatibility check')
    done = subprocess.run([str(program), 'check', '--no-cache', '--config', str(ROOT / 'pyproject.toml'),
                           '--output-format', 'json', *(str(SOURCE / name) for name in FILES)], capture_output=True, check=False)
    self.assertEqual(done.returncode, 0, done.stdout.decode())
    self.assertEqual(json.loads(done.stdout), [])

  def test_diagnostic_exception_preserves_ValueError_and_code(self):
    spec = importlib.util.spec_from_file_location('f70u_compatibility_primary', SOURCE / FILES[0])
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    exception = getattr(module, 'SyntheticReferenceError', None)
    assert isinstance(exception, type)
    self.assertTrue(issubclass(exception, ValueError))
    with self.assertRaises(exception) as raised:
      module.evaluate(None)
    self.assertEqual(str(raised.exception), 'F70S_REQUEST_TYPE')
