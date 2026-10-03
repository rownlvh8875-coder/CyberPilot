"""Regression for timestamp/size-valid bytecode hiding a reviewed source edit."""
import importlib.util
import os
from pathlib import Path
import py_compile
import subprocess
import sys
import tempfile
import unittest

from openpilot.tools.cyber_autotune.source_imports import source_only_imports


def load_value(path):
  spec = importlib.util.spec_from_file_location('synthetic_source_binding_probe', path)
  module = importlib.util.module_from_spec(spec)
  spec.loader.exec_module(module)
  return module.VALUE


class TestSourceImports(unittest.TestCase):
  def test_same_size_same_second_stale_cache_cannot_override_current_source(self):
    previous_prefix, previous_write = sys.pycache_prefix, sys.dont_write_bytecode
    with tempfile.TemporaryDirectory() as directory:
      path = Path(directory) / 'synthetic.py'
      path.write_text('VALUE = 1\n')
      timestamp = 1_700_000_000
      os.utime(path, (timestamp, timestamp))
      cached = Path(py_compile.compile(str(path), doraise=True))
      cached_before = cached.read_bytes()
      path.write_text('VALUE = 2\n')
      os.utime(path, (timestamp, timestamp))
      self.assertEqual(load_value(path), 1)  # prove the concrete stale-cache precondition
      with source_only_imports():
        self.assertEqual(load_value(path), 2)
        prefix = Path(sys.pycache_prefix)
        self.assertTrue(prefix.is_dir())
        self.assertEqual(list(prefix.iterdir()), [])
        self.assertTrue(sys.dont_write_bytecode)
        self.assertEqual(list(prefix.iterdir()), [])
      self.assertFalse(prefix.exists())
      self.assertEqual(cached.read_bytes(), cached_before)
      self.assertEqual(sys.pycache_prefix, previous_prefix)
      self.assertEqual(sys.dont_write_bytecode, previous_write)

  def test_nested_and_exception_contexts_restore_and_clean_owned_directories(self):
    previous = (sys.pycache_prefix, sys.dont_write_bytecode)
    with self.assertRaisesRegex(RuntimeError, 'synthetic'):
      with source_only_imports():
        outer = Path(sys.pycache_prefix)
        with source_only_imports():
          inner = Path(sys.pycache_prefix)
          self.assertNotEqual(inner, outer)
        self.assertFalse(inner.exists())
        self.assertEqual(Path(sys.pycache_prefix), outer)
        raise RuntimeError('synthetic')
    self.assertFalse(outer.exists())
    self.assertEqual((sys.pycache_prefix, sys.dont_write_bytecode), previous)

  def test_both_fixed_worker_entrypoints_own_source_only_context(self):
    # Inspect wrappers in fresh children: importing worker into this process is forbidden.
    code = '''import pathlib, runpy, sys
ns = runpy.run_path(sys.argv[1], run_name='test_worker_entry')
def probe(request):
  prefix = pathlib.Path(sys.pycache_prefix)
  assert prefix.is_dir() and not list(prefix.iterdir()) and sys.dont_write_bytecode
  return str(prefix)
entry = ns['execute_request']
entry.__globals__['_execute_request'] = probe
owned = entry({})
assert not pathlib.Path(owned).exists()
'''
    for worker in ('native_worker.py', 'native_long_worker.py'):
      with self.subTest(worker=worker):
        result = subprocess.run([sys.executable, '-I', '-c', code, str(Path(__file__).parents[1] / worker)],
                                capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
  unittest.main()
