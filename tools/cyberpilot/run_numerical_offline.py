#!/usr/bin/env python3
"""Exact public synthetic suite; Python-level I/O guard, not an OS air gap.

Package installation/checkout use network before this process. This runner has
no input-path arguments, scientific readers, grants or execution/resume API.
Public legacy helpers import reader/executor definitions transitively; no such
entry point is invoked. Private adapters and model-payload reads are rejected.
"""

import importlib.abc
import json
import os
from pathlib import Path
import sys
import stat
import unittest

ROOT = Path(__file__).resolve().parents[2]
READ_ROOTS = (ROOT, Path(sys.base_prefix).resolve(), Path(sys.prefix).resolve())
SUITES = (
  'openpilot.tools.cyber_autotune.tests.test_empirical_hurdle_v4_e2_canonical_stage2',
  'openpilot.tools.cyber_autotune.tests.test_empirical_hurdle_v4_e2_deterministic_numerics_design',
  'openpilot.tools.cyber_autotune.tests.test_empirical_hurdle_v4_e2_numerical_diagnostic.TestNumericalDiagnostic',
)


class PublicImports(importlib.abc.MetaPathFinder):
  def find_spec(self, fullname, path=None, target=None):
    if (fullname.startswith('openpilot.tools.cyber_autotune.') and '_private' in fullname) or fullname.startswith(
      ('openpilot.selfdrive', 'openpilot.system', 'opendbc', 'panda', 'cereal', 'huggingface_hub', 'requests')
    ):
      raise ImportError('OFFLINE_FORBIDDEN_IMPORT')
    return None


def public_boundary(event, args):
  if event.startswith('socket.') or event in (
    'os.system',
    'os.exec',
    'os.posix_spawn',
    'os.remove',
    'os.rename',
    'os.rmdir',
    'os.mkdir',
    'os.symlink',
    'os.link',
  ):
    raise PermissionError('OFFLINE_OPERATION_DENIED')
  if event == 'subprocess.Popen':
    executable, argv, cwd, _ = args
    if executable != 'git' or type(argv) not in (list, tuple) or len(argv) != 3 or argv[1] != 'show' or not isinstance(argv[2], str):
      raise PermissionError('OFFLINE_SUBPROCESS_DENIED')
    revision, separator, member = argv[2].partition(':')
    if (
      len(revision) != 40
      or any(c not in '0123456789abcdef' for c in revision)
      or separator != ':'
      or not member
      or member.startswith('/')
      or '..' in Path(member).parts
      or Path(cwd).resolve() != ROOT
    ):
      raise PermissionError('OFFLINE_GIT_OBJECT_DENIED')
  if event == 'open':
    path, mode, flags = args
    if type(path) is int and (mode in ('r', 'rb')) and not (flags & (os.O_WRONLY | os.O_RDWR)):
      if stat.S_ISFIFO(os.fstat(path).st_mode):
        return  # Read end of the bounded, read-only git-show stdout pipe.
    if not isinstance(path, (str, bytes, os.PathLike)):
      raise PermissionError('OFFLINE_SOURCE_DENIED')
    p = Path(os.fsdecode(path)).resolve()
    writing = (isinstance(mode, str) and any(c in mode for c in 'wax+')) or (
      isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)
    )
    if writing or p.name.endswith(('.npy', '.npy.gz', '.npz', '.onnx', '.pkl', '.rlog', '.qlog')) or not any(p.is_relative_to(root) for root in READ_ROOTS):
      raise PermissionError('OFFLINE_SOURCE_DENIED')


def main():
  os.chdir(ROOT)
  sys.path.insert(0, str(ROOT))
  sys.dont_write_bytecode = True
  sys.meta_path.insert(0, PublicImports())
  sys.addaudithook(public_boundary)
  suite = unittest.TestLoader().loadTestsFromNames(SUITES)
  result = unittest.TextTestRunner(verbosity=1).run(suite)
  forbidden = [
    name
    for name in sys.modules
    if (name.startswith('openpilot.tools.cyber_autotune.') and '_private' in name) or name.startswith(('openpilot.selfdrive', 'openpilot.system'))
  ]
  if forbidden:
    raise RuntimeError('OFFLINE_FORBIDDEN_IMPORT')
  print(
    json.dumps(
      {
        'validation_scope': 'OFFLINE_STATIC_NUMERICAL_CI',
        'tests': result.testsRun,
        'success': result.wasSuccessful(),
        'private_adapters_imported': 0,
        'full_CI_certified': False,
        'E2_integration_authorized': False,
      }
    )
  )
  raise SystemExit(0 if result.wasSuccessful() else 1)


if __name__ == '__main__':
  main()
