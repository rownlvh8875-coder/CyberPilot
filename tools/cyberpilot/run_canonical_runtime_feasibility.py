#!/usr/bin/env python3
"""Public synthetic runtime lab. Compilation is a separate explicit build mode.

No private readers or original-runtime patching; only this lab accepts a native
callable for controlled in-memory recursion. Never activates a private grant.
"""

import argparse
import cProfile
import hashlib
from functools import partial
import json
import os
from pathlib import Path
import pstats
import re
import resource
import statistics
import subprocess
import sys
import tempfile
import time
import unittest
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_runtime_model as m
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_native_candidate as native
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_stage2 as scalar

SUITES = (
  'openpilot.tools.cyber_autotune.tests.test_empirical_hurdle_v4_e2_canonical_native_candidate',
  'openpilot.tools.cyber_autotune.tests.test_empirical_hurdle_v4_e2_canonical_runtime_feasibility',
)


def build(directory):
  m.public_check()
  directory = Path(directory)
  m.need(not directory.is_relative_to(ROOT), 'NATIVE_BUILD_MUST_BE_OUTSIDE_GIT')
  m.need(directory.is_absolute() and directory.resolve() == directory, 'NATIVE_EXACT_BUILD_PATH_REQUIRED')
  directory.mkdir(mode=0o700)  # Exclusive, no overwrite or preexisting library.
  compiler = Path('/usr/bin/gcc-13').resolve(strict=True)
  build_env = {'PATH': '/usr/bin:/bin', 'LC_ALL': 'C'}
  source_bytes = native.SOURCE.read_bytes()
  source_hash = hashlib.sha256(source_bytes).hexdigest()
  snapshot = directory / 'candidate.c'
  fd = os.open(snapshot, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o400)
  with os.fdopen(fd, 'wb') as stream:
    stream.write(source_bytes)
    stream.flush()
    os.fsync(stream.fileno())
  version = subprocess.check_output([str(compiler), '-dumpfullversion'], text=True, env=build_env).strip()
  m.need(version == '13.3.0', 'CANONICAL_NATIVE_TOOLCHAIN_NOT_QUALIFIED')
  compiler_text = subprocess.check_output([str(compiler), '--version'], text=True, env=build_env).splitlines()[0]
  library = directory / 'canonical_candidate.so'
  before = m.resources()
  started = time.perf_counter()
  subprocess.run([str(compiler), *native.FLAGS, str(snapshot), '-o', str(library), '-lm'], check=True, timeout=60, env=build_env)
  m.need(
    hashlib.sha256(snapshot.read_bytes()).hexdigest() == source_hash == hashlib.sha256(native.SOURCE.read_bytes()).hexdigest(), 'NATIVE_COMPILE_INPUT_DRIFT'
  )
  assembly = subprocess.check_output(['/usr/bin/objdump', '-d', library.name], cwd=directory, text=True)
  m.need(not re.search(r'\b(?:v?fmadd|v?fmsub|v?fnmadd|v?fnmsub)', assembly), 'CANONICAL_NATIVE_FUSED_OPERATION_FOUND')
  ops = {op: bool(re.search(r'\b' + op + r'\b', assembly)) for op in ('subsd', 'divsd', 'mulsd', 'addsd')}
  m.need(all(ops.values()), 'CANONICAL_NATIVE_SCALAR_OPERATIONS_NOT_OBSERVED')
  receipt = {
    'schema': 'PUBLIC_CANONICAL_NATIVE_BUILD_V1',
    'ABI': native.ABI,
    'source_sha256': source_hash,
    'compile_snapshot_sha256': source_hash,
    'source_checked_before_after_compile': True,
    'compiler_version': version,
    'compiler_description': compiler_text,
    'compiler_binary_sha256': hashlib.sha256(compiler.read_bytes()).hexdigest(),
    'flags': list(native.FLAGS),
    'library': library.name,
    'binary_sha256': hashlib.sha256(library.read_bytes()).hexdigest(),
    'machine_code': {'no_fused_multiply_add': True, 'observed_scalar_operations': ops, 'objdump_sha256': hashlib.sha256(assembly.encode()).hexdigest()},
    'private_execution_authorized': False,
    'runtime_integration_authorized': False,
  }
  raw = native.canonical(receipt) + b'\n'
  path = directory / 'build.json'
  fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
  with os.fdopen(fd, 'wb') as stream:
    stream.write(raw)
    stream.flush()
    os.fsync(stream.fileno())
  library.chmod(0o500)
  with library.open('rb') as binary:
    os.fsync(binary.fileno())
  (directory / 'disassembly.txt').write_text(assembly)
  directory_fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
  try:
    os.fsync(directory_fd)
  finally:
    os.close(directory_fd)
  return {
    'receipt_file': str(path),
    'receipt_sha256': hashlib.sha256(raw).hexdigest(),
    'build_wall_seconds': time.perf_counter() - started,
    'build_process_resources_before': before,
    'build_process_resources_after': m.resources(),
    'build': receipt,
  }


def load(path, digest):
  return native.NativeCandidate(Path(path), digest)


def median_cpu(records):
  return statistics.median(x['user_CPU_seconds'] + x['system_CPU_seconds'] for x in records)


def kernels(q):
  records = []
  for n in (8192, 65536, 336941):
    for p in (5, 13, 33, 93):
      x, model = m.fixture(n, p)
      expected = None
      pair = {}
      for label, fn in (('python', scalar.canonical_predict_delta), ('native', q.predict)):
        output, timings = m.timed(partial(fn, x, model))
        if expected is None:
          expected = output
        else:
          m.need(output.tobytes() == expected.tobytes(), 'CANONICAL_NATIVE_BYTE_PARITY_FAILED')
        cpu = median_cpu(timings)
        pair[label] = {
          'measurements': timings,
          'CPU_median_seconds': cpu,
          'rows_per_CPU_second': n / cpu,
          'effective_terms_per_CPU_second': n * p / cpu,
          'wall_median_seconds': statistics.median(v['wall_seconds'] for v in timings),
        }
      records.append(
        {
          'N': n,
          'P': p,
          'effective_columns': p,
          'selected_ratio': 1.0,
          'input_bytes': x.nbytes,
          'output_bytes': expected.nbytes,
          'timing': pair,
          'CPU_speedup': pair['python']['CPU_median_seconds'] / pair['native']['CPU_median_seconds'],
          'process_cumulative_high_water_not_case_peak': m.resources(),
        }
      )
  return records


def overhead(q):
  records = []
  for n in (0, 1, 8, 64, 512, 336941):
    x, model = m.fixture(n, 93)
    args = q.arguments(x, model)
    pair = {}
    inner = 1 if n == 336941 else 100
    for label, fn in (
      ('Python', partial(scalar.canonical_predict_delta, x, model)),
      ('Native_wrapper', partial(q.predict, x, model)),
      ('checked_ABI_reuse_only', partial(q.library.cp_stage2, *args)),
      ('ctypes_noop', q.noop),
    ):
      result, times = m.timed(fn, inner=inner)
      if label in ('checked_ABI_reuse_only', 'ctypes_noop'):
        m.need(result == 0, 'NATIVE_ABI_TIMING_STATUS_FAILURE')
      pair[label] = {'measurements': times, 'median_CPU_seconds': median_cpu(times)}
    records.append({'N': n, 'P': 93, 'effective_columns': 93, 'inner_calls': inner, 'results': pair, 'ABI_reuse_is_diagnostic_not_authorized_runtime': True})
  return records


def stage1_bench():
  from tools.cyberpilot.canonical_readiness_fixture import models
  from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_bridge as b

  rows = []
  for n in (1, 8, 64, 512):
    for p in (5, 13, 33, 93):
      x, _ = m.fixture(n, p)
      stage1, _ = models((p - 3) // 2)
      for mode in ('STATIC', 'MOVE', 'ALTERNATING'):
        x[:, -3] = 0 if mode == 'STATIC' else 1 if mode == 'MOVE' else np.arange(n) % 2
        _, times = m.timed(partial(b.original.probability, x, stage1), inner=100)
        rows.append(
          {'N': n, 'P': p, 'prior_context': mode, 'measurements': times, 'CPU_seconds_per_original_probability_call': median_cpu(times), 'head_calls_upper': 2}
        )
  return rows


def recursive_probe(kernel, n=64, horizon=25, arm='D0', routing='MIXED'):
  """Lab-only DI, no reference truth argument or original executor alteration."""
  from tools.cyberpilot.canonical_readiness_fixture import models
  from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_bridge as b

  length = 45
  stage1, stage2 = models(length)
  stage2['coefficients'] *= 0.125  # Predeclared public lab model; no model fitting.
  initial = np.zeros((n, length + 1), np.int64)
  # Supplied synthetic exogenous command alternates both state probabilities.
  command = np.resize(np.array([-0.75, 0.75, -0.25, 0.25]), (n, length + horizon - 1))
  speed = np.full((n, horizon), 10.0)
  threshold = {'STATIC': 1.0, 'MOVE': 0.0, 'MIXED': 0.5}[routing]
  policy = (threshold,) if arm == 'D0' else (threshold, threshold)
  current, past = initial[:, -1].copy(), np.diff(initial, axis=1)
  path = np.empty((n, horizon + 1), np.int64)
  path[:, 0] = current
  deltas = np.empty((n, horizon), np.float64)
  timings = dict.fromkeys(('feature_assembly', 'Stage1', 'gate_validation', 'Stage2', 'projection', 'history_loop'), 0.0)
  move_rows = 0
  for step in range(horizon):
    start = time.process_time()
    x = np.ascontiguousarray(np.column_stack((np.ones(n), command[:, step : step + length], past, current, speed[:, step])), dtype=np.float64)
    timings['feature_assembly'] += time.process_time() - start
    start = time.process_time()
    p = b.original.probability(x, stage1)
    timings['Stage1'] += time.process_time() - start
    start = time.process_time()
    gate = b.apply_gate(p, past[:, -1], policy, arm)
    timings['gate_validation'] += time.process_time() - start
    start = time.process_time()
    delta = np.zeros(n, np.float64)
    if np.any(gate):
      delta[gate] = kernel(np.ascontiguousarray(x[gate]), stage2)
    timings['Stage2'] += time.process_time() - start
    move_rows += int(np.count_nonzero(gate))
    start = time.process_time()
    new = current.copy()
    if np.any(gate):
      new[gate] = b.original.m.project(current[gate].astype(np.float64) + delta[gate])
    timings['projection'] += time.process_time() - start
    start = time.process_time()
    path[:, step + 1], deltas[:, step] = new, delta
    past[:, :-1] = past[:, 1:]
    past[:, -1] = new - current
    current = new
    timings['history_loop'] += time.process_time() - start
  return {
    'path': path,
    'delta': deltas,
    'component_CPU_seconds': timings,
    'MOVE_rows': move_rows,
    'row_steps': n * horizon,
    'future_truth_inputs': 0,
    'DI_scope': 'PUBLIC_SYNTHETIC_ONLY_NOT_FULL_EXECUTOR',
  }


def recursive_bench(q):
  rows = []
  for arm in ('D0', 'D1', 'D2'):
    for routing in ('STATIC', 'MOVE', 'MIXED'):
      for horizon in (25, 50, 100, 200):
        values = {}
        expected = None
        for label, fn in (('python', scalar.canonical_predict_delta), ('native', q.predict)):
          output, times = m.timed(partial(recursive_probe, fn, horizon=horizon, arm=arm, routing=routing))
          if expected is None:
            expected = output
          else:
            m.need(all(output[key].tobytes() == expected[key].tobytes() for key in ('path', 'delta')), 'NATIVE_RECURSIVE_PARITY_FAILED')
          values[label] = {'timings': times, 'last_component_CPU_seconds': output['component_CPU_seconds'], 'MOVE_rows': output['MOVE_rows']}
        rows.append({'arm': arm, 'routing': routing, 'horizon': horizon, 'anchors': 64, 'timings': values, 'raw_byte_parity': True})
  return rows


def d2_bench():
  from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_bridge as b

  results = []
  for n in (8192, 65536):
    current = np.zeros(n, np.int64)
    target = (np.arange(n) % 2).astype(np.int64)
    y = target != current
    u = np.full(n, 0.75)
    move = b.original.m.project(u)
    for kind in ('equal', 'unique'):
      p = np.full(n, 0.5) if kind == 'equal' else (np.arange(n, dtype=np.float64) + 1) / (n + 1)
      output, times = m.timed(partial(b.d2.select_context, p, y, current, target, u, move, 0.5, role='TRAIN'))
      results.append(
        {
          'N': n,
          'score_groups': kind,
          'timings': times,
          'decision_selected_synthetic_only': True,
          'witness_verified': output['witness_verified'],
        }
      )
  return results


def full_caller():
  from tools.cyberpilot.canonical_bounded_fixture import provider
  from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_bounded as bounded

  binding = bounded.old.synthetic_binding('1' * 40)
  hashes = []

  def run():
    with tempfile.TemporaryDirectory(prefix='public-runtime-caller-') as tmp:
      result = bounded.run_synthetic(provider(), Path(tmp) / 'run', binding)
      hashes.append({name: hashlib.sha256((Path(tmp) / 'run' / name).read_bytes()).hexdigest() for name in ('train.json', 'result.json', 'complete.json')})
      return result

  result, times = m.timed(run)
  profiler = cProfile.Profile(time.process_time)
  profiler.runcall(run)
  stats = pstats.Stats(profiler)
  rows = [
    {
      'file': Path(key[0]).name,
      'function': key[2],
      'primitive_calls': value[0],
      'calls': value[1],
      'exclusive_CPU_seconds': value[2],
      'cumulative_CPU_seconds_not_additive': value[3],
    }
    for key, value in stats.stats.items()
    if 'cyber' in key[0] or key[2] in ('canonical_predict_delta', 'probability')
  ]
  rows.sort(key=lambda x: (-x['exclusive_CPU_seconds'], x['file'], x['function']))
  m.need(all(h == hashes[0] for h in hashes), 'FROZEN_PYTHON_PAYLOAD_DRIFT')
  stage2 = sum(v[3] for k, v in stats.stats.items() if k[2] == 'canonical_predict_delta')
  total = sum(v[2] for v in stats.stats.values())
  return {
    'jobs': 32,
    'timings_unprofiled': times,
    'phase_timings_last_unprofiled': result['phase_timings'],
    'profile': rows,
    'profile_total_CPU_seconds': total,
    'profile_Stage2_cumulative_CPU_seconds': stage2,
    'profile_is_instrumented_not_throughput_certificate': True,
    'Stage2_infinite_speedup_floor': m.amdahl(total, min(stage2, total), 1e100),
    'scientific_payload_hashes': hashes[0],
    'all_5_warmup_measured_profile_payloads_byte_exact': True,
    'coverage': result['coverage'],
    'lifetime': result['lifetime'],
    'synthetic_counters': result['synthetic_counters'],
    'native_calls_in_frozen_executor': 0,
    'resources_process_high_water': m.resources(),
  }


def benchmark(q):
  scalar.qualify_environment()
  m.public_check()
  data = {
    'scope': 'OFFLINE_CANONICAL_NATIVE_AND_RUNTIME_CI',
    'kernel': kernels(q),
    'boundary': overhead(q),
    'Stage1': stage1_bench(),
    'recursive': recursive_bench(q),
    'D2': d2_bench(),
    'full_frozen_Python_caller': full_caller(),
    'workload_upper': m.workload(),
    'call_graph': m.CALL_GRAPH,
    'resources_process_high_water': m.resources(),
    'statuses': {
      'NATIVE_NUMERICAL_PARITY': 'TESTS_REQUIRED_SEPARATELY',
      'NATIVE_PERFORMANCE': 'CANONICAL_NATIVE_PERFORMANCE_MEASURED',
      'FULL_CALLER_RUNTIME': 'CANONICAL_E2_RUNTIME_BOUND_UNPROVEN',
      'MEMORY_CAPACITY': 'CANONICAL_E2_RESOURCE_PREFLIGHT_UNPROVEN',
      'PRIVATE_EXECUTION_AUTHORITY': 'CANONICAL_E2_PRIVATE_EXECUTION_NOT_AUTHORIZED',
      'NATIVE_INTEGRATION': 'CANONICAL_NATIVE_RUNTIME_INTEGRATION_NOT_AUTHORIZED',
    },
  }
  return data


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('--build', type=Path)
  parser.add_argument('--receipt', type=Path)
  parser.add_argument('--receipt-sha256')
  parser.add_argument('--benchmark-output', type=Path)
  parser.add_argument('--tests', action='store_true')
  args = parser.parse_args()
  if args.build:
    print(json.dumps(build(args.build), sort_keys=True))
    return
  m.public_check()
  m.need(args.receipt is not None and args.receipt_sha256 is not None, 'EXPLICIT_NATIVE_BUILD_RECEIPT_REQUIRED')
  resource.setrlimit(resource.RLIMIT_AS, (8 * 1024**3, 8 * 1024**3))
  resource.setrlimit(resource.RLIMIT_CPU, (1800, 1800))
  q = load(args.receipt, args.receipt_sha256)
  if args.tests:
    os.environ['CYBERPILOT_PUBLIC_NATIVE_RECEIPT'] = str(args.receipt)
    os.environ['CYBERPILOT_PUBLIC_NATIVE_RECEIPT_SHA256'] = args.receipt_sha256
    suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(name) for name in SUITES)
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    m.need(result.wasSuccessful(), 'CANONICAL_RUNTIME_TEST_FAILURE')
    print(json.dumps({'tests': result.testsRun, 'status': 'CANONICAL_NATIVE_BYTE_EXACT_QUALIFIED', 'private_execution_authorized': False}))
  if args.benchmark_output:
    data = benchmark(q)
    raw = native.canonical(data) + b'\n'
    fd = os.open(args.benchmark_output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as stream:
      stream.write(raw)
      stream.flush()
      os.fsync(stream.fileno())
    print(json.dumps({'benchmark_raw_sha256': hashlib.sha256(raw).hexdigest(), 'status': data['statuses'], 'resources': m.resources()}))


if __name__ == '__main__':
  main()
