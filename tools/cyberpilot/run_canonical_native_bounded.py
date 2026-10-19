#!/usr/bin/env python3
"""Fixed public synthetic A/B/C lab; no input reader or production integration."""

import argparse
from contextlib import contextmanager, nullcontext
import json
import os
from pathlib import Path
import resource
import signal
import stat
import statistics
import subprocess
import sys
import time
import unittest
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_native_bounded as q
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_caller_profile as profile
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_runtime_model as runtime
from tools.cyberpilot import canonical_bounded_fixture as fixtures
from tools.cyberpilot.canonical_readiness_fixture import models

CONTRACT = ROOT / 'docs/cyberpilot/changes/empirical-hurdle-stage1-v4-e2-canonical-native-bounded-contract-v1.json'
SUITES = (
  'openpilot.tools.cyber_autotune.tests.test_empirical_hurdle_v4_e2_canonical_native_bounded',
  'openpilot.tools.cyber_autotune.tests.test_empirical_hurdle_v4_e2_canonical_caller_profile',
)


def public_check():
  value = q.out.decode(CONTRACT.read_bytes())
  q.need(
    value['scope'] == 'PUBLIC_SYNTHETIC_NATIVE_BOUNDED_INTEGRATION_ONLY' and value['future_private_authority'] is False, 'NATIVE_BOUNDED_CONTRACT_CONFLICT'
  )
  for path, digest in value['frozen_source_sha256'].items():
    q.need(q.out.sha((ROOT / path).read_bytes()) == digest, 'NATIVE_BOUNDED_FROZEN_SOURCE_DRIFT')
  lock_path = CONTRACT.with_name('empirical-hurdle-stage1-v4-e2-canonical-native-bounded-lock.json')
  if lock_path.is_file():
    lock = q.out.checked(q.out.decode(lock_path.read_bytes()))
    for path, digest in {**lock['source_sha256'], **lock['artifact_sha256']}.items():
      q.need(q.out.sha((ROOT / path).read_bytes()) == digest, 'NATIVE_BOUNDED_IMPLEMENTATION_DRIFT')
  return value


def harness_identity():
  paths = [
    'openpilot/tools/cyber_autotune/empirical_hurdle_v4_e2_canonical_native_bounded.py',
    'openpilot/tools/cyber_autotune/empirical_hurdle_v4_e2_canonical_caller_profile.py',
    'openpilot/tools/cyber_autotune/tests/test_empirical_hurdle_v4_e2_canonical_native_bounded.py',
    'openpilot/tools/cyber_autotune/tests/test_empirical_hurdle_v4_e2_canonical_caller_profile.py',
    'tools/cyberpilot/run_canonical_native_bounded.py',
    '.github/workflows/cyberpilot-canonical-native-bounded.yaml',
    str(CONTRACT.relative_to(ROOT)),
  ]
  return {path: q.out.sha((ROOT / path).read_bytes()) for path in paths}


def caps():
  for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    q.need(os.environ.get(key) == '1', 'NATIVE_BOUNDED_SINGLE_THREAD_REQUIRED')
  resource.setrlimit(resource.RLIMIT_AS, (8 * 1024**3, 8 * 1024**3))
  resource.setrlimit(resource.RLIMIT_CPU, (1800, 1800))


def times():
  usage = resource.getrusage(resource.RUSAGE_SELF)
  return {'wall': time.perf_counter(), 'user': usage.ru_utime, 'system': usage.ru_stime}


def delta(before):
  after = times()
  return {
    'wall_seconds': after['wall'] - before['wall'],
    'user_CPU_seconds': after['user'] - before['user'],
    'system_CPU_seconds': after['system'] - before['system'],
  }


def cpu(value):
  return value['user_CPU_seconds'] + value['system_CPU_seconds']


def scientific_output_digests(path, completion_digest):
  # Every read follows the externally held completion->member digest chain.
  with q.out.Store(path, create=False) as store:
    complete = store.read('complete.json', completion_digest)
    result = {'complete.json': completion_digest}
    for name, key in (('train.json', 'train_raw_sha256'), ('result.json', 'result_raw_sha256')):
      digest = complete[key]
      record = store.read(name, digest)
      q.need(q.out.sha(q.out.canonical(record)) == digest, 'NATIVE_BOUNDED_NONCANONICAL_RESULT')
      result[name] = digest
    return result


def validate_witness(envelope):
  q.need(envelope.get('scientific_audit_enabled') is True, 'NATIVE_BOUNDED_MISSING_SCIENTIFIC_WITNESS')
  observed = envelope.get('profile')
  if envelope.get('profile_enabled') is True:
    q.need(type(observed) is dict, 'NATIVE_BOUNDED_MISSING_SCIENTIFIC_WITNESS')
    observed = observed.get('scientific_witness')
  expected = {'primary': {'potential_cache': 32, 'recursive': 384, 'infer': 36096}, 'segmented': {'potential_cache': 32, 'recursive': 672, 'infer': 52896}}
  q.need(envelope.get('fixture') in expected and type(observed) is dict, 'NATIVE_BOUNDED_MISSING_SCIENTIFIC_WITNESS')
  counts = expected[envelope['fixture']]
  q.need(set(observed) == set(counts), 'NATIVE_BOUNDED_INCOMPLETE_SCIENTIFIC_WITNESS')
  for name, count in counts.items():
    entry = observed[name]
    q.need(
      type(entry) is dict
      and set(entry) == {'calls', 'ordered_raw_array_witness_sha256'}
      and type(entry['calls']) is int
      and entry['calls'] == count
      and q.inputs.hash64(entry['ordered_raw_array_witness_sha256']),
      'NATIVE_BOUNDED_INCOMPLETE_SCIENTIFIC_WITNESS',
    )
  return observed


def child_environment():
  return {
    'PATH': '/usr/bin:/bin',
    'LC_ALL': 'C.UTF-8',
    'PYTHONNOUSERSITE': '1',
    'PYTHONDONTWRITEBYTECODE': '1',
    'OPENBLAS_NUM_THREADS': '1',
    'OMP_NUM_THREADS': '1',
    'MKL_NUM_THREADS': '1',
    'NUMEXPR_NUM_THREADS': '1',
    'TMPDIR': '/tmp',
  }


@contextmanager
def wall_guard(seconds):
  def exceeded(*unused):
    raise TimeoutError('NATIVE_BOUNDED_LAB_WALL_CAP')

  previous = signal.getsignal(signal.SIGALRM)
  previous_timer = signal.getitimer(signal.ITIMER_REAL)
  q.need(previous_timer == (0.0, 0.0), 'NATIVE_BOUNDED_WALL_TIMER_ALREADY_ACTIVE')
  signal.signal(signal.SIGALRM, exceeded)
  signal.setitimer(signal.ITIMER_REAL, seconds)
  try:
    yield
  finally:
    signal.setitimer(signal.ITIMER_REAL, 0)
    signal.signal(signal.SIGALRM, previous)


def child(args):
  public_check()
  before = times()
  native = None if args.mode == q.MODES[0] else q.VerifiedNativeBackend(args.receipt, args.receipt_sha256)
  observation = profile.CallerProfile() if args.profile else profile.ScientificAudit() if args.audit else None
  with observation if observation is not None else nullcontext():
    source = fixtures.provider() if args.fixture == 'primary' else fixtures.segmented_provider()
    binding = q.old.synthetic_binding(args.head)
    result = (
      q.reference.run_synthetic(source, args.destination, binding)
      if native is None
      else q.run_synthetic(source, args.destination, binding, native, optimized=args.mode == q.MODES[2])
    )
  granular_validation = profile.validate_granularity(observation.snapshot(), args.fixture) if args.profile else None
  measured = delta(before)
  files = scientific_output_digests(args.destination, result['completion_digest'])
  envelope = {
    'mode': args.mode,
    'harness_source_sha256': harness_identity(),
    'fixture': args.fixture,
    'measurement': measured,
    'resources': runtime.resources(),
    'scientific_files': files,
    'binding': binding,
    'completion_digest': result['completion_digest'],
    'coverage': result['coverage'],
    'native': None if native is None else native.envelope(),
    'profile': observation.snapshot() if observation is not None else None,
    'profile_enabled': args.profile,
    'granularity_validation': granular_validation,
    'scientific_audit_enabled': args.audit or args.profile,
    'phase_timings': result['phase_timings'],
    'lifetime': result['lifetime'],
    'materialization_counters': result['materialization_counters'],
    'source_integrity_optimization': 'SOURCE_INTEGRITY_OPTIMIZATION_UNPROVEN',
    'private_reads': 0,
    'source_writes': 0,
    'scope': 'PUBLIC_SYNTHETIC_NATIVE_BOUNDED_INTEGRATION_ONLY',
  }
  with q.out.Store(args.destination, create=False) as store:
    digest = store.write('execution.json', envelope)
  print(
    json.dumps(
      {
        'envelope_sha256': digest,
        'mode': args.mode,
        'fixture': args.fixture,
        'measurement': measured,
        'native_calls': 0 if native is None else native.envelope()['native_calls'],
        'end_to_end_measurement': delta(before),
      }
    )
  )


def read_envelope(path, expected_sha256):
  with q.out.Store(path, create=False) as store:
    return store.read('execution.json', expected_sha256)


def verify_output(path, expected_sha256):
  # Only sealed lab outputs; no source checks/provider/model/inference calls.
  envelope = read_envelope(path, expected_sha256)
  result = q.old.verify_synthetic(path, envelope['binding'], envelope['completion_digest'])
  q.need(
    all(result[key] == 0 for key in ('scientific_recomputations', 'inference_calls', 'source_rereads', 'source_writes')), 'NATIVE_BOUNDED_VERIFY_RECOMPUTE'
  )
  return result


def compare_paths(paths, *, witness):
  expected_files = expected_witness = None
  for path, expected_sha256 in paths:
    envelope = read_envelope(path, expected_sha256)
    current = {}
    with q.out.Store(path, create=False) as store:
      for name in ('train.json', 'result.json', 'complete.json'):
        expected = envelope['scientific_files'][name]
        raw = q.out.canonical(store.read(name, expected))
        q.need(q.out.sha(raw) == expected, 'NATIVE_BOUNDED_NONCANONICAL_RESULT')
        current[name] = raw
    observed = validate_witness(envelope) if witness else None
    if expected_files is None:
      expected_files, expected_witness = current, observed
    else:
      q.need(current == expected_files, 'NATIVE_BOUNDED_SCIENTIFIC_BYTE_PARITY_FAILED')
      if witness:
        q.need(observed == expected_witness, 'NATIVE_BOUNDED_SCIENTIFIC_BYTE_PARITY_FAILED')
    verify_output(path, expected_sha256)
  return {
    'files': {name: q.out.sha(raw) for name, raw in expected_files.items()},
    'scientific_witness': expected_witness if witness else None,
    'runs': len(paths),
    'status': 'BYTE_EXACT_PASS',
    'verify_only': {'source_rereads': 0, 'scientific_inference': 0, 'scientific_recomputations': 0, 'source_writes': 0},
  }


def launch(args, root, label, mode, fixture, *, audit=False, profiling=False):
  destination = root / label
  cmd = [
    sys.executable,
    '-B',
    str(Path(__file__).resolve()),
    '--child',
    '--receipt',
    str(args.receipt),
    '--receipt-sha256',
    args.receipt_sha256,
    '--mode',
    mode,
    '--fixture',
    fixture,
    '--head',
    args.head,
    '--destination',
    str(destination),
  ]
  if audit:
    cmd.append('--audit')
  if profiling:
    cmd.append('--profile')
  log = root / (label + '.log')
  fd = os.open(log, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
  before = time.perf_counter()
  with os.fdopen(fd, 'w+b') as stream:
    process = subprocess.run(cmd, cwd=ROOT, env=child_environment(), stdout=stream, stderr=subprocess.STDOUT, timeout=2400)
    stream.flush()
    st = os.fstat(stream.fileno())
    q.need(
      stat.S_ISREG(st.st_mode) and st.st_uid == os.getuid() and st.st_nlink == 1 and stat.S_IMODE(st.st_mode) == 0o600 and st.st_size <= 65536,
      'NATIVE_BOUNDED_CHILD_LOG_CONFLICT',
    )
    stamp = (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns)
    stream.seek(0)
    raw = stream.read(65537)
    after = os.fstat(stream.fileno())
    q.need(stamp == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns), 'NATIVE_BOUNDED_CHILD_LOG_CHANGED')
  q.need(process.returncode == 0, 'NATIVE_BOUNDED_FRESH_CHILD_FAILED_' + str(process.returncode))
  completion = q.out.decode(raw.decode().splitlines()[-1])
  q.need(completion['mode'] == mode and completion['fixture'] == fixture, 'NATIVE_BOUNDED_CHILD_LOG_BINDING')
  digest = completion['envelope_sha256']
  envelope = read_envelope(destination, digest)
  envelope['execution_envelope_sha256'] = digest
  envelope['end_to_end_measurement'] = completion['end_to_end_measurement']
  q.need(envelope['harness_source_sha256'] == harness_identity(), 'NATIVE_BOUNDED_CALLER_SOURCE_DRIFT')
  envelope['parent_observed_wall_seconds_with_process_startup'] = time.perf_counter() - before
  print(
    json.dumps(
      {
        'completed': label,
        'mode': mode,
        'CPU_seconds': cpu(envelope['end_to_end_measurement']),
        'wall_seconds': envelope['end_to_end_measurement']['wall_seconds'],
      }
    ),
    flush=True,
  )
  return destination, envelope


def recursive_case(arm, horizon, routing):
  n, length = 512, 45
  stage1, stage2 = models(length)
  initial = np.zeros((n, length + 1), np.int64)
  command = np.resize(np.array([-0.75, 0.75, -0.25, 0.25]), (n, length + horizon - 1))
  speed = np.full((n, horizon), 10.0)
  threshold = {'ALL_STATIC': 1.0, 'ALL_MOVE': 0.0, 'MIXED': 0.5, 'HIGH_SWITCH': 0.0}[routing]
  decisions = (threshold,) if arm == 'D0' else (threshold, threshold)
  return initial, command, speed, stage1, stage2, decisions, np.full(n, 200, np.int64)


def recursive_matrix(native):
  records = []
  for arm in q.b.ARMS:
    for routing in ('ALL_STATIC', 'ALL_MOVE', 'MIXED', 'HIGH_SWITCH'):
      for horizon in q.b.HORIZONS:
        initial, command, speed, stage1, stage2, decisions, available = recursive_case(arm, horizon, routing)
        expected = None
        modes = {}
        for mode in q.MODES:
          before_calls = native.envelope()['native_calls']
          values = []
          output = None
          for repeat in range(4):
            before = times()
            if mode == q.MODES[0]:
              output = q.b.recursive(initial, command, speed, 'HRI_D00_L45', stage1, stage2, decisions, arm, horizon, available, {}, scope=q.b.SCOPE)
            else:
              output = q.recursive(
                initial,
                command,
                speed,
                'HRI_D00_L45',
                stage1,
                stage2,
                decisions,
                arm,
                horizon,
                available,
                {},
                scope=q.b.SCOPE,
                backend=native,
                optimized=mode == q.MODES[2],
              )
            if repeat:
              values.append(delta(before))
            current = {key: (value.dtype.str, value.shape, value.tobytes()) for key, value in output.items()}
            if expected is None:
              expected = current
            else:
              q.need(current == expected, 'NATIVE_BOUNDED_SCIENTIFIC_BYTE_PARITY_FAILED')
          calls = native.envelope()['native_calls'] - before_calls
          if routing == 'ALL_STATIC':
            q.need(calls == 0 and not output['gate'].any(), 'NATIVE_BOUNDED_EMPTY_GATE_CALL')
          if routing == 'ALL_MOVE':
            q.need(output['gate'].all(), 'NATIVE_BOUNDED_ALL_MOVE_FIXTURE')
          if routing == 'HIGH_SWITCH':
            q.need(
              output['context'].any()
              and (~output['context']).any()
              and np.diff(output['path'], axis=1).any()
              and np.any(output['context'][:, 1:] != output['context'][:, :-1]),
              'NATIVE_BOUNDED_SWITCH_FIXTURE',
            )
          modes[mode] = {
            'samples': values,
            'CPU_median_seconds': statistics.median(cpu(v) for v in values),
            'wall_median_seconds': statistics.median(v['wall_seconds'] for v in values),
            'native_calls_including_warmup': calls,
            'gate_MOVE_rows': int(output['gate'].sum()),
            'realized_nonzero_deltas': int(np.count_nonzero(np.diff(output['path'], axis=1))),
            'context_transitions': int(np.count_nonzero(output['context'][:, 1:] != output['context'][:, :-1])),
            'context_transition_opportunities': 512 * (horizon - 1),
          }
        records.append({'arm': arm, 'routing': routing, 'horizon': horizon, 'anchors': 512, 'modes': modes, 'raw_trace_parity': True})
  return records


def benchmark(args):
  public_check()
  root = args.output_root
  q.need(root.is_absolute() and root.resolve() == root and not root.is_relative_to(ROOT), 'NATIVE_BOUNDED_OUTPUT_ROOT')
  root.mkdir(mode=0o700)
  measured_sources = harness_identity()
  timing, scientific, profiles = {}, {}, {}
  for mode in q.MODES:
    launch(args, root, 'warm-' + mode, mode, 'primary')
    samples = []
    for repeat in range(3):
      path, env = launch(args, root, 'timing-' + mode + '-' + str(repeat), mode, 'primary')
      samples.append(env)
    timing[mode] = {
      'samples': samples,
      'CPU_median_seconds': statistics.median(cpu(s['end_to_end_measurement']) for s in samples),
      'wall_median_seconds': statistics.median(s['end_to_end_measurement']['wall_seconds'] for s in samples),
    }
  timing_paths = [(root / ('timing-' + mode + '-' + str(i)), timing[mode]['samples'][i]['execution_envelope_sha256']) for mode in q.MODES for i in range(3)]
  scientific['primary_timing_files'] = compare_paths(timing_paths, witness=False)
  for fixture in ('primary', 'segmented'):
    paths = []
    for mode in q.MODES:
      for repeat in range(2):
        path, env = launch(args, root, 'scientific-' + fixture + '-' + mode + '-' + str(repeat), mode, fixture, audit=True)
        paths.append((path, env['execution_envelope_sha256']))
    scientific[fixture] = compare_paths(paths, witness=True)
  for mode in q.MODES:
    path, env = launch(args, root, 'profile-' + mode, mode, 'primary', profiling=True)
    profiles[mode] = env
  scientific['profile'] = compare_paths([(root / ('profile-' + mode), profiles[mode]['execution_envelope_sha256']) for mode in q.MODES], witness=True)
  native = q.VerifiedNativeBackend(args.receipt, args.receipt_sha256)
  with wall_guard(2400):
    recursive = recursive_matrix(native)
    from tools.cyberpilot.run_canonical_runtime_feasibility import d2_bench

    d2 = d2_bench()
  result = {
    'schema': 'V4_NATIVE_BOUNDED_SYNTHETIC_MEASUREMENTS_V1',
    'measured_source_sha256': measured_sources,
    'contract_raw_sha256': q.out.sha(CONTRACT.read_bytes()),
    'head': args.head,
    'timing': timing,
    'scientific_parity': scientific,
    'profiles': profiles,
    'recursive512': recursive,
    'recursive_control_count': 48,
    'unique_recursive_input_policy_conditions': 36,
    'HIGH_SWITCH_control_duplicates_ALL_MOVE': True,
    'D2_fixed_equal_unique': d2,
    'native_recursive_matrix_envelope': native.envelope(),
    'capacity': profile.capacity_assessment(timing),
    'process_cumulative_high_water_not_per_case_peak': runtime.resources(),
    'limitations': [
      'Fixed ABC order and three timing samples are not worst-case guarantees.',
      (
        'Timings include pipeline/artifact/provider/seal work but exclude import/public-source qualification '
        + 'and parent process startup. Parent-observed wall is separate.'
      ),
      (
        'Scientific witness/profile children are separate from unprofiled timings. '
        + 'Two-segment full original population has two fresh scientific observations per mode, '
        + 'not three-sample performance qualification.'
      ),
      'Every original SourceBlock check is retained; no hashing-removal proof is claimed.',
      'No actual source/model/I/O/host-capacity private evidence was accessed.',
    ],
    'private_reads': 0,
    'python_fallback_calls': 0,
    'source_hash_checks_removed': 0,
  }
  q.need(harness_identity() == measured_sources, 'NATIVE_BOUNDED_CALLER_SOURCE_DRIFT')
  with q.out.Store(root, create=False) as store:
    digest = store.write('measurements.json', result)
  print(
    json.dumps(
      {'measurement_raw_sha256': digest, 'scientific_parity': 'A_B_C_BYTE_EXACT_PASS', 'private_execution_authorized': False, 'capacity': result['capacity']}
    ),
    flush=True,
  )


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('--receipt', type=Path)
  parser.add_argument('--receipt-sha256')
  parser.add_argument('--tests', action='store_true')
  parser.add_argument('--benchmark', action='store_true')
  parser.add_argument('--child', action='store_true')
  parser.add_argument('--mode', choices=q.MODES)
  parser.add_argument('--fixture', choices=('primary', 'segmented'), default='primary')
  parser.add_argument('--head', default='7cf1630773918dd560153517f45bfc75663c6f97')
  parser.add_argument('--destination', type=Path)
  parser.add_argument('--output-root', type=Path)
  parser.add_argument('--audit', action='store_true')
  parser.add_argument('--profile', action='store_true')
  parser.add_argument('--verify', type=Path)
  parser.add_argument('--execution-sha256')
  args = parser.parse_args()
  if args.verify:
    q.need(args.execution_sha256 is not None, 'NATIVE_BOUNDED_VERIFY_DIGEST_REQUIRED')
    print(json.dumps(verify_output(args.verify, args.execution_sha256)))
    return
  caps()
  public_check()
  q.need(args.receipt is not None and args.receipt_sha256 is not None, 'NATIVE_BOUNDED_EXPLICIT_ARTIFACT_REQUIRED')
  if args.child:
    q.need(args.mode is not None and args.destination is not None, 'NATIVE_BOUNDED_CHILD_ARGUMENTS')
    child(args)
  elif args.tests:
    os.environ['CYBERPILOT_PUBLIC_NATIVE_RECEIPT'] = str(args.receipt)
    os.environ['CYBERPILOT_PUBLIC_NATIVE_RECEIPT_SHA256'] = args.receipt_sha256
    suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(name) for name in SUITES)
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    q.need(result.wasSuccessful(), 'NATIVE_BOUNDED_TEST_FAILURE')
    print(json.dumps({'tests': result.testsRun, 'status': 'PASS', 'private_reads': 0}))
  elif args.benchmark:
    q.need(args.output_root is not None, 'NATIVE_BOUNDED_OUTPUT_ROOT_REQUIRED')
    benchmark(args)
  else:
    raise ValueError('NATIVE_BOUNDED_EXPLICIT_MODE_REQUIRED')


if __name__ == '__main__':
  main()
