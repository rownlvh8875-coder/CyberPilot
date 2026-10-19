#!/usr/bin/env python3
"""Separate public bounded numerical CI; no private E2 authorization."""

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
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_bounded as q
from tools.cyberpilot.run_canonical_readiness import boundary, measure

SUITES = (
  'openpilot.tools.cyber_autotune.tests.test_empirical_hurdle_v4_e2_canonical_bounded',
  'openpilot.tools.cyber_autotune.tests.test_empirical_hurdle_v4_e2_canonical_capability',
)


def max_shape():
  from tools.cyberpilot.canonical_bounded_fixture import spec

  n, p = 336941, 93
  started = time.perf_counter()
  cpu = time.process_time()
  # Frozen public unit: periodic command vector, deterministic fixture SEED20261020;
  # no reduction in candidate grid or rows, but this is not uniqueN-score timing.
  s = spec(6, 'TRAIN', n=n, periodic=True)
  life = q.resources.Lifetime()
  life.add('source', s['parts'][0][0].arrays)
  life.add('train_vectors', s['train_meta'])
  x = q.inputs.assemble(s['parts'], s['candidate'])
  token = life.add('feature', x)
  j = {**s['train_meta'], 'x': x}
  counters = {}
  d0 = q.b.reconstruct_d0(j['p'], j['y'], counters)['value']
  cache = q.b.potential_cache(j, counters)
  life.add('cache', cache)
  q1 = q.qualify(j, cache, q.b.apply_gate(j['p'], j['prior'], (float(d0),), 'D0'), 'Q1', counters, life)
  decisions = []
  for state in (0, 1):
    mask = (j['prior'] != 0) == state
    result = q.b.d2.select_context(
      j['p'][mask], j['y'][mask], j['current'][mask], j['target'][mask], cache['u'][mask], cache['move_tick'][mask], float(d0), role='TRAIN'
    )
    decisions.append(result['decision'])
  q3 = q.qualify(j, cache, q.b.apply_gate(j['p'], j['prior'], tuple(decisions), 'D2'), 'Q3', counters, life)
  j.pop('x')
  x = None
  life.release(token)
  return {
    'scope': 'MAX_SHAPE_SINGLE_JOB_UNIT_NOT_GLOBAL_E2',
    'N': n,
    'P': p,
    'Q1': q1,
    'Q3': q3,
    'counter': counters,
    'lifetime': life.snapshot(),
    'resources': measure(),
    'wall_seconds': time.perf_counter() - started,
    'CPU_seconds': time.process_time() - cpu,
    'runtime_worst_case_certified': False,
    'private_execution_authorized': False,
  }


def worker(args):
  path = Path(args.output)
  q.need(path.is_absolute() and path.is_relative_to('/tmp') and '..' not in path.parts, 'CANONICAL_BOUNDED_SYNTHETIC_TMP')
  resource.setrlimit(resource.RLIMIT_AS, (8 * 1024**3, 8 * 1024**3))
  resource.setrlimit(resource.RLIMIT_CPU, (900, 900))
  boundary(path)
  started = time.perf_counter()
  if args.worker == 'repeat':
    from tools.cyberpilot.canonical_bounded_fixture import provider

    binding = q.implementation_binding(args.head)
    result = q.run_synthetic(provider(), path, binding['reference_binding'])
    execution = q.seal_execution(path, binding, result)
    print(
      json.dumps(
        {
          'binding': binding,
          'completion_digest': result['completion_digest'],
          'execution_digest': execution,
          'lifetime': result['lifetime'],
          'phase_timings': result['phase_timings'],
          'materialization_counters': result['materialization_counters'],
          'resources': measure(),
          'wall_seconds': time.perf_counter() - started,
          'output_bytes': sum((path / name).stat().st_size for name in ('train.json', 'result.json', 'complete.json', 'execution.json')),
        },
        sort_keys=True,
      )
    )
  elif args.worker == 'verify':
    binding = q.out.decode(args.binding.encode())
    print(json.dumps(q.verify_bounded(path, binding, args.digest), sort_keys=True))
  elif args.worker == 'stress':
    result = max_shape()
    with q.out.Store(path) as store:
      store.write('stress.json', result)
    print(json.dumps(result, sort_keys=True))


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('--worker', choices=('repeat', 'verify', 'stress'))
  parser.add_argument('--output')
  parser.add_argument('--head')
  parser.add_argument('--binding')
  parser.add_argument('--digest')
  parser.add_argument('--check-public', action='store_true')
  parser.add_argument('--stress-max', action='store_true')
  parser.add_argument('--execute-private', action='store_true')
  args = parser.parse_args()
  if args.execute_private:
    q.execute_private()
  if args.worker:
    worker(args)
    return
  if args.check_public:
    q.public_check()
    print(json.dumps({'public_check': 'PASS', 'private_execution_authorized': False}))
    return
  q.public_check()
  env = {k: v for k, v in os.environ.items() if k in ('PATH', 'LANG', 'LC_ALL')}
  env.update(OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', MKL_NUM_THREADS='1', NUMEXPR_NUM_THREADS='1', PYTHONDONTWRITEBYTECODE='1')
  head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()

  def launch(kind, path, **fields):
    argv = [sys.executable, '-B', str(Path(__file__).resolve()), '--worker', kind, '--output', str(path), '--head', head]
    for key, value in fields.items():
      argv += ['--' + key, value]
    result = subprocess.run(argv, cwd=ROOT, env=env, text=True, capture_output=True, timeout=1800, check=True)
    return json.loads(result.stdout)

  with tempfile.TemporaryDirectory(prefix='cyberpilot-bounded-synthetic-') as tmp:
    root = Path(tmp)
    if args.stress_max:
      print(json.dumps(launch('stress', root / 'stress'), sort_keys=True))
      return
    suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(name) for name in SUITES)
    tests = unittest.TextTestRunner(verbosity=1).run(suite)
    q.need(tests.wasSuccessful(), 'CANONICAL_BOUNDED_FOCUSED_FAILURE')
    first = launch('repeat', root / 'repeat1')
    second = launch('repeat', root / 'repeat2')  # Only after successful complete first process.
    for name in ('train.json', 'result.json', 'complete.json'):
      q.old.compare_repeats((root / 'repeat1' / name).read_bytes(), (root / 'repeat2' / name).read_bytes(), True, True)
    verify = [
      launch('verify', root / ('repeat' + str(i + 1)), binding=json.dumps(item['binding'], sort_keys=True), digest=item['execution_digest'])
      for i, item in enumerate((first, second))
    ]
    print(
      json.dumps(
        {
          'scope': 'OFFLINE_STATIC_NUMERICAL_CI_BOUNDED',
          'tests': tests.testsRun,
          'success': True,
          'reference_parity': 'TRAIN_RESULT_COMPLETE_BYTE_EXACT',
          'two_fresh_processes': True,
          'repeatability': 'BYTE_EXACT',
          'repeat_envelopes': [first, second],
          'verify_only': verify,
          'FULL_CI_certified': False,
          'private_execution_authorized': False,
        },
        sort_keys=True,
      )
    )


if __name__ == '__main__':
  main()
