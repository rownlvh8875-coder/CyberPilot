#!/usr/bin/env python3
"""Separate synthetic durable/process CI, not FULL_CI or a private-data runner."""

import argparse
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_execution as ex
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_output as out


def boundary(output_root):
  from tools.cyberpilot.run_numerical_offline import PublicImports

  sys.meta_path.insert(0, PublicImports())
  read_roots = (ROOT, Path(sys.prefix).resolve(), Path(sys.base_prefix).resolve(), output_root)
  ancestors = {output_root, *output_root.parents}

  def audit(event, args):
    if event.startswith('socket.') or event in (
      'os.system',
      'os.exec',
      'os.posix_spawn',
      'subprocess.Popen',
      'os.remove',
      'os.rename',
      'os.rmdir',
      'os.link',
      'os.symlink',
      'os.chmod',
      'os.chown',
      'os.truncate',
      'os.chdir',
      'os.utime',
    ):
      raise PermissionError('READINESS_WORKER_OPERATION_DENIED')
    if event in ('open', 'os.mkdir'):
      name = args[0]
      cap = out.IO_PERMISSION.get()
      if cap is not None:
        expected, name_expected, flags, target, fd, stamp = cap
        if event != expected or str(name) != name_expected:
          raise PermissionError('READINESS_IO_CAPABILITY_CONFLICT')
        if fd is not None:
          st = os.fstat(fd)
          if (st.st_dev, st.st_ino) != stamp:
            raise PermissionError('READINESS_IO_FD_CONFLICT')
        target = Path(target)
        if event == 'os.mkdir':
          if not target.is_relative_to(output_root) or args[1] != 0o700:
            raise PermissionError('READINESS_MKDIR_DENIED')
          return
        if (args[2] & ~os.O_CLOEXEC) != (flags & ~os.O_CLOEXEC):
          raise PermissionError('READINESS_IO_FLAGS_CONFLICT')
        directory = bool(flags & os.O_DIRECTORY)
        if not directory and target.name.endswith(('.npy', '.npy.gz', '.npz', '.onnx', '.pkl', '.rlog', '.qlog')):
          raise PermissionError('READINESS_MODEL_OR_LOG_DENIED')
        if directory and target in ancestors and not flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT):
          return
        if target.is_relative_to(output_root) and flags & os.O_NOFOLLOW:
          return
        raise PermissionError('READINESS_IO_TARGET_DENIED')
      if event == 'os.mkdir':
        raise PermissionError('READINESS_MKDIR_DENIED')
      _, mode, flags = args
      if type(name) is int:
        target = Path(os.readlink(f'/proc/self/fd/{name}'))
      else:
        target = Path(os.fsdecode(name))
        if not target.is_absolute():
          target = Path.cwd() / target
      resolved = target.resolve()
      writing = bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC))
      if writing and not resolved.is_relative_to(output_root):
        raise PermissionError('READINESS_WORKER_WRITE_DENIED')
      if (
        not writing
        and resolved not in (Path('/proc/self/status').resolve(), Path('/proc/self/statm').resolve())
        and not any(resolved.is_relative_to(r) for r in read_roots)
      ):
        raise PermissionError('READINESS_WORKER_READ_DENIED')
      if resolved.name.endswith(('.npy', '.npy.gz', '.npz', '.onnx', '.pkl', '.rlog', '.qlog')):
        raise PermissionError('READINESS_MODEL_OR_LOG_DENIED')
    if event in ('os.listdir', 'os.scandir'):
      name = args[0]
      path = Path(os.readlink(f'/proc/self/fd/{name}')) if type(name) is int else Path(name or '.')
      if not any(path.resolve().is_relative_to(r) for r in read_roots):
        raise PermissionError('READINESS_DISCOVERY_DENIED')

  sys.addaudithook(audit)


def measure():
  usage = resource.getrusage(resource.RUSAGE_SELF)
  status = Path('/proc/self/status').read_text()
  return {
    'Linux_peak_RSS_KiB': usage.ru_maxrss,
    'CPU_user_seconds': usage.ru_utime,
    'CPU_system_seconds': usage.ru_stime,
    'VmPeak_KiB': int(next(line.split()[1] for line in status.splitlines() if line.startswith('VmPeak:'))),
  }


def worker(args):
  path = Path(args.output)
  out.need(path.is_absolute() and path.is_relative_to('/tmp') and '..' not in path.parts, 'READINESS_SYNTHETIC_TMP_REQUIRED')
  resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))
  resource.setrlimit(resource.RLIMIT_CPU, (120, 120))
  boundary(path)
  started = time.perf_counter()
  if args.worker == 'repeat':
    from tools.cyberpilot.canonical_readiness_fixture import provider

    result = ex.run_synthetic(provider(), path, ex.synthetic_binding(args.head))
    envelope = {
      'completion_digest': result['completion_digest'],
      'binding': result['binding'],
      'resources': measure(),
      'output_file_count': 3,
      'output_bytes': result['synthetic_output_bytes'],
      'wall_seconds': time.perf_counter() - started,
    }
    print(json.dumps(envelope, sort_keys=True))
  elif args.worker == 'verify':
    # Binding comes from parent-owned expected public envelope, no source reads.
    binding = out.decode(args.binding.encode())
    print(json.dumps(ex.verify_synthetic(path, binding, args.digest), sort_keys=True))
  elif args.worker == 'audit':
    denied = 0
    with out.Store(path) as store:
      digest = store.write('sample.json', {'scope': 'SYNTHETIC_ONLY'})
      store.read('sample.json', digest)
      checks = (
        lambda: os.open('train.json', os.O_WRONLY | os.O_CREAT, 0o600),
        lambda: Path('/proc/version').read_text(),
        lambda: os.mkdir('/tmp/denied-readiness'),
        lambda: os.listdir('/'),
        lambda: os.symlink('x', path / 'link'),
      )
      for action in checks:
        try:
          action()
        except PermissionError:
          denied += 1
        else:
          raise AssertionError('READINESS_AUDIT_BYPASS')
      fd = os.open(ROOT / 'README.md', os.O_RDONLY)
      try:
        try:
          os.fdopen(fd, 'wb', closefd=False)
        except PermissionError:
          denied += 1
        else:
          raise AssertionError('READINESS_FD_WRITE_BYPASS')
      finally:
        os.close(fd)
    print(json.dumps({'denied': denied, 'resource_stats': measure()}))
  elif args.worker == 'stress':
    import numpy as np
    from tools.cyberpilot.canonical_readiness_fixture import models
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_stage2 as kernel

    n, p = 336941, 93
    x = np.full((n, p), 0.25, np.float64)
    x[:, 0] = 1.0
    model = models(45)[1]
    cache = np.empty(n, np.float64)
    for first in range(0, n, 512):
      cache[first : first + 512] = kernel.canonical_predict_delta(x[first : first + 512], model)
    mask = np.arange(n) % 2 == 0
    selected = np.ascontiguousarray(x[mask])
    actual = kernel.canonical_predict_delta(selected, model)
    ex.b.require_bytes(actual, cache[mask], 'CANONICAL_STRESS_PARITY_FAILED')
    result = {
      'scope': 'MAX_SHAPE_SYNTHETIC_KERNEL_ONLY',
      'N': n,
      'P': p,
      'input_bytes': x.nbytes,
      'selected_copy_bytes': selected.nbytes,
      'finite_boolean_bytes_upper': n * p,
      'output_bytes': cache.nbytes + actual.nbytes,
      'fixed512_calls': (n + 511) // 512,
      'whole_selected_calls': 1,
      'byte_exact': True,
      'resources': measure(),
      'wall_seconds': time.perf_counter() - started,
      'full_private_capacity_certified': False,
    }
    with out.Store(path) as store:
      store.write('result.json', result)
    print(json.dumps(result, sort_keys=True))


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('--worker', choices=('repeat', 'verify', 'stress', 'audit'))
  parser.add_argument('--output')
  parser.add_argument('--head')
  parser.add_argument('--binding')
  parser.add_argument('--digest')
  parser.add_argument('--check-public', action='store_true')
  parser.add_argument('--dry-run-synthetic', action='store_true')
  parser.add_argument('--verify-synthetic', action='store_true')
  parser.add_argument('--execute-private', action='store_true')
  args = parser.parse_args()
  if args.execute_private:
    ex.execute_private()
  if args.check_public:
    _, digest = ex.public_check()
    print(json.dumps({'public_check': 'PASS', 'protocol_raw_sha256': digest, 'private_execution_authorized': False}))
    return
  if args.dry_run_synthetic:
    args.worker = 'repeat'
  if args.verify_synthetic:
    args.worker = 'verify'
  if args.worker:
    if args.head is None and args.worker != 'verify':
      args.head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    worker(args)
    return
  head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
  ex.public_check()
  suite = unittest.defaultTestLoader.loadTestsFromName('openpilot.tools.cyber_autotune.tests.test_empirical_hurdle_v4_e2_canonical_readiness')
  tests = unittest.TextTestRunner(verbosity=1).run(suite)
  if not tests.wasSuccessful():
    raise SystemExit(1)
  env = {k: os.environ[k] for k in ('PATH', 'LANG') if k in os.environ}
  env.update(dict.fromkeys(('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS', 'PYTHONDONTWRITEBYTECODE'), '1'))
  script = str(Path(__file__).resolve())

  def child(mode, path, *extra):
    value = subprocess.run(
      [sys.executable, '-I', '-B', script, '--worker', mode, '--output', str(path), '--head', head, *extra],
      cwd=ROOT,
      env=env,
      capture_output=True,
      text=True,
      timeout=180,
    )
    if value.returncode:
      print(value.stderr, file=sys.stderr)
      raise RuntimeError('READINESS_FRESH_PROCESS_FAILED_NO_RETRY')
    return json.loads(value.stdout)

  with tempfile.TemporaryDirectory(prefix='canonical-readiness-') as folder:
    work = Path(folder)
    audit_result = child('audit', work / 'audit')
    out.need(audit_result['denied'] == 6, 'READINESS_AUDIT_COVERAGE')
    first = child('repeat', work / 'repeat-1')  # failure raises; repeat2 never starts.
    second = child('repeat', work / 'repeat-2')
    a = (work / 'repeat-1/result.json').read_bytes()
    bb = (work / 'repeat-2/result.json').read_bytes()
    comparison = ex.compare_repeats(a, bb, True, True)
    verifies = [
      child('verify', work / f'repeat-{i}', '--binding', json.dumps(row['binding'], sort_keys=True), '--digest', row['completion_digest'])
      for i, row in enumerate((first, second), 1)
    ]
    stress = child('stress', work / 'stress')
  print(
    json.dumps(
      {
        'scope': 'CANONICAL_SYNTHETIC_READINESS_CI',
        'tests': tests.testsRun,
        'success': True,
        'two_fresh_processes': True,
        'audit': audit_result,
        'comparison': comparison,
        'repeat_validation_domain20': 'VERIFIED_TWO_FRESH_PROCESSES',
        'verify_only': verifies,
        'repeat_envelopes': [first, second],
        'stress': stress,
        'FULL_CI_certified': False,
        'private_execution_authorized': False,
      },
      sort_keys=True,
    )
  )


if __name__ == '__main__':
  main()
