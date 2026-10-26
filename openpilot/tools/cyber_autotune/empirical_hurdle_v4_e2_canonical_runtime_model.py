"""Public synthetic cost model; estimates never confer private execution authority."""

import hashlib
import json
import math
from pathlib import Path
import resource
import time
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
PROTOCOL = ROOT / 'docs/cyberpilot/changes/empirical-hurdle-stage1-v4-e2-canonical-runtime-qualification-v1.json'
SEED = 20261021
HORIZONS = (25, 50, 100, 200)
N_MAX = 336941
CPU_CAP = 21600
WALL_CAP = 43200


def need(ok, reason='CANONICAL_RUNTIME_CONTRACT_CONFLICT'):
  if not ok:
    raise ValueError(reason)


def workload(n=N_MAX, p=93):
  need(type(n) is int and 0 < n <= N_MAX and type(p) is int and p in (5, 13, 33, 93))
  chunks = (n + 511) // 512
  calls = 32 * 3 * sum(HORIZONS) * chunks
  steps = 32 * 3 * sum(HORIZONS) * n
  return {
    'jobs': 32,
    'arms': 3,
    'horizons': list(HORIZONS),
    'rows': n,
    'columns_upper': p,
    'recursive_bridge_calls': calls,
    'Stage1_probability_calls': calls,
    'Stage1_head_calls_upper': 2 * calls,
    'Stage2_calls_upper': calls,
    'recursive_row_steps': steps,
    'Stage2_terms_upper': steps * p,
    'TRAIN_cache_Q1_Q3_row_predictions_upper': 32 * 3 * n,
    'DEV_one_step_row_predictions_upper': 32 * 3 * n,
    'feature_materializations': 128,
    'Q1_whole_calls_upper': 32,
    'Q3_whole_calls_upper': 32,
    'fixed512_all_row_calls_single_segment': 32 * chunks,
    'fixed512_calls_with_154_segment_resets_upper': 32 * ((n // 512) + 154),
    'D2_context_calls': 64,
    'D1_context_calls': 64,
    'D2_complexity': 'O(N log N) sorted sweep plus fixed-tree replacements',
    'full_runtime_certified': False,
  }


def amdahl(total, stage2, speedup):
  need(all(type(x) in (float, int) and math.isfinite(x) for x in (total, stage2, speedup)))
  need(0 <= stage2 <= total and total > 0 and speedup > 0)
  floor = total - stage2
  return {
    'accelerated_CPU_seconds': floor + stage2 / speedup,
    'infinite_Stage2_speedup_floor_seconds': floor,
    'maximum_speedup': total / floor if floor else None,
    'full_runtime_certified': False,
  }


def public_check():
  value = json.loads(PROTOCOL.read_bytes())
  for name, sha in value['frozen_source_sha256'].items():
    need(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == sha, 'CANONICAL_RUNTIME_FROZEN_SOURCE_CONFLICT')
  need(value['acceptance']['private_execution_authorized'] is False and value['acceptance']['native_integration_authorized'] is False)
  lock_path = ROOT / 'docs/cyberpilot/changes/empirical-hurdle-stage1-v4-e2-canonical-runtime-lock.json'
  lock = json.loads(lock_path.read_bytes())
  payload = {k: v for k, v in lock.items() if k != 'receipt_sha256'}
  encoded = json.dumps(payload, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
  need(hashlib.sha256(encoded).hexdigest() == lock['receipt_sha256'], 'CANONICAL_RUNTIME_LOCK_RECEIPT_CONFLICT')
  for name, sha in {**lock['source_sha256'], **lock['artifact_sha256']}.items():
    need(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == sha, 'CANONICAL_RUNTIME_IMPLEMENTATION_DRIFT')
  need(lock['private_execution_authorized'] is False and lock['native_integration_authorized'] is False)
  return {'frozen_pins': len(value['frozen_source_sha256']), 'private_execution_authorized': False, 'native_integration_authorized': False}


def fixture(n, p):
  need(type(n) is int and 0 <= n <= N_MAX and p in (5, 13, 33, 93))
  rng = np.random.default_rng(SEED + p)
  x = rng.normal(size=(n, p)).astype(np.float64)
  x[:, 0] = 1.0
  normalizer = {
    'mean': np.linspace(-0.25, 0.25, p),
    'std': np.linspace(0.75, 1.25, p),
    'constant': np.zeros(p, bool),
    'effective': np.arange(p, dtype=np.int64),
    'constant_reference': np.zeros(p),
  }
  return x, {'normalizer': normalizer, 'coefficients': np.linspace(-0.05, 0.05, p)}


def resources():
  usage = resource.getrusage(resource.RUSAGE_SELF)
  status = {}
  for line in Path('/proc/self/status').read_text().splitlines():
    if line.startswith(('VmPeak:', 'VmRSS:')):
      key, number, unit = line.split()
      need(unit == 'kB')
      status[key[:-1] + '_KiB'] = int(number)
  return {'user_CPU_seconds': usage.ru_utime, 'system_CPU_seconds': usage.ru_stime, 'Linux_peak_RSS_KiB': usage.ru_maxrss, **status}


def timed(fn, repeats=3, warmups=1, inner=1):
  for _ in range(warmups):
    fn()
  measured = []
  result = None
  for _ in range(repeats):
    before = resource.getrusage(resource.RUSAGE_SELF)
    wall = time.perf_counter()
    for _ in range(inner):
      result = fn()
    after = resource.getrusage(resource.RUSAGE_SELF)
    measured.append(
      {
        'wall_seconds': (time.perf_counter() - wall) / inner,
        'user_CPU_seconds': (after.ru_utime - before.ru_utime) / inner,
        'system_CPU_seconds': (after.ru_stime - before.ru_stime) / inner,
      }
    )
  return result, measured


# Call-site accounting, not independent additive time estimates. Profiling joins
# these symbols to exclusive times and preserves cumulative times separately.
CALL_GRAPH = (
  (
    'admission_hash',
    'SourceBlock.__init__/check; Provider.__init__/_check',
    'source blocks/model/meta snapshots',
    'O(source bytes) plus conditional O(live original alias bytes * chunks)',
    'source admission copies/hash bytes',
  ),
  ('D0', 'reconstruct_d0', '32 combined TRAIN populations', 'O(N log N)', 'score sort/count vectors'),
  ('feature_assembly', 'assemble', '128 TRAIN/DEV materializations', 'O(NP)', 'one feature plus chunk'),
  ('TRAIN_Stage2', 'potential_cache', 'segment fixed512 all rows', 'O(NP)', '32 retained u/move caches'),
  ('Q1', 'qualify_q1', '32 whole selected calls maximum', 'O(NP)', 'full and one selected feature copy'),
  ('D1', 'select_d1', '64 TRAIN contexts', 'O(N log N)', 'one sorted context'),
  ('D2', 'select_d2', '64 TRAIN contexts', 'O(N log N)', 'original four-channel tree'),
  ('Q3', 'qualify_q3', '32 whole final-selected calls maximum', 'O(NP)', 'no winner reselection'),
  ('TRAIN_seal', 'train', 'exclusive Store fsync/readback', 'O(receipt bytes)', 'serialized TRAIN proofs'),
  ('DEV_Stage1', 'probability', 'original head routing, up to2 heads/call', 'O(NP)', 'transformed matrix/head slices'),
  ('one_step', 'one_step', '32 jobs times3 arms', 'O(NP)', 'one active arm result'),
  ('recursive_Stage1', 'probability', '23,724,000 recursive calls upper', 'O(row steps P)', 'chunk512 normalizer arrays'),
  ('recursive_Stage2', 'canonical_predict_delta', '0..one call per recursive step', 'O(MOVE row steps P)', 'selected x/output/finite mask'),
  ('projection', 'project', 'same ties-even signed16 rule', 'O(MOVE rows)', 'temporary float and int arrays'),
  ('history_loop', 'recursive', 'full-state history update', 'O(row steps L)', 'one chunk history and trace'),
  ('drift_diagnostics', 'drift_chunk', 'after predictions only', 'O(anchor H L)', 'one trace; truth evaluation only'),
  ('metrics', 'metrics', 'original RMSE/MAE/P95 order', 'O(N log N) P95 upper', 'full-horizon errors plus sort copies'),
  ('serialization_verify', 'write', 'canonical Store/verify-only', 'O(output bytes)', 'up to384MiB output plus serialization'),
)


def validate_workflow(value):
  need(type(value) is dict and value.get('permissions') == {'contents': 'read'}, 'NATIVE_CI_AUTHORITY_CONFLICT')
  job = value['jobs']['runtime']
  need(job['name'] == 'OFFLINE_CANONICAL_NATIVE_AND_RUNTIME_CI' and job['runs-on'] == 'ubuntu-24.04')
  need(job['timeout-minutes'] == 40 and set(value['jobs']) == {'runtime'})
  steps = job['steps']
  checkout = steps[0]
  need(checkout['with'] == {'fetch-depth': 0, 'lfs': False, 'submodules': False, 'persist-credentials': False}, 'NATIVE_CI_ASSET_BOUNDARY')
  commands = '\n'.join(str(s.get('run', '')) for s in steps)
  for forbidden in ('git lfs pull', 'tools/op.sh setup', '--execute-private', 'continue-on-error', 'secrets.', '/mnt/e/', '/mnt/d/'):
    need(forbidden not in commands and forbidden not in json.dumps(value), 'NATIVE_CI_FORBIDDEN_OPERATION')
  need('--build ' in commands and '--tests' in commands and '--benchmark-output' in commands)
  need('timeout 2400s' in commands and '13.3.0' in commands)
  need(value['env']['OPENBLAS_NUM_THREADS'] == '1' and value['env']['GIT_LFS_SKIP_SMUDGE'] == '1')
  return {'scope': job['name'], 'private_execution_authorized': False, 'FULL_CI_certified': False}


def estimated_runtime(measurements):
  """Measured-cost extrapolations, deliberately never a whole-caller bound.

  The raw benchmark source/timings are retained independently. This postprocess
  adds no kernel, routing, population, metric or threshold changes.
  """
  need(type(measurements) is dict and 'Stage1' in measurements and 'boundary' in measurements)
  stage1 = [r for r in measurements['Stage1'] if r['N'] == 512 and r['P'] == 93]
  stage2 = [r for r in measurements['boundary'] if r['N'] == 512]
  need(bool(stage1) and len(stage2) == 1, 'CANONICAL_RUNTIME_MEASUREMENTS_MISSING')

  def maximum_cpu(rows):
    values = [r['user_CPU_seconds'] + r['system_CPU_seconds'] for r in rows]
    need(bool(values) and all(math.isfinite(v) and v >= 0 for v in values))
    return max(values)

  s1 = maximum_cpu([r for case in stage1 for r in case['measurements']])
  s2 = maximum_cpu(stage2[0]['results']['Native_wrapper']['measurements'])
  counts = workload()
  calls = counts['recursive_bridge_calls']
  chunks = 32 * 3 * len(HORIZONS) * ((N_MAX + 511) // 512)
  return {
    'method': 'MAXIMUM_OBSERVED_SAMPLE_COST_TIMES_PUBLIC_WORK_COUNT_NOT_A_TIME_BOUND',
    'Stage1_measured_call_cost_extrapolation_CPU_seconds': calls * s1,
    'Native_all_MOVE_measured_call_cost_extrapolation_CPU_seconds': calls * s2,
    'all_STATIC_Stage2_calls': 0,
    'high_switching_Stage1_head_calls_upper': counts['Stage1_head_calls_upper'],
    'horizon_chunks_upper': chunks,
    'conditional_original_alias_fast_checks': 2 * chunks,
    'actual_live_original_alias_bytes': None,
    'conditional_hash_bytes_if_916535_rows_4x8byte_original_fields_live_per_job': 2 * chunks * 916535 * 32,
    'drift_variable_dimension_complexity': 'O(anchors * horizon * history_length)',
    'unbounded_or_unmeasured_costs': [
      'actual source/model/alias lifetimes and hashes',
      'Stage1/Stage2 distributions and cache state',
      'source assembly/proof checks',
      'D1/D2 unique-Nmax sweeps',
      'full history/drift/metrics',
      'allocator/loader/scheduling',
      'actual input/output/fsync',
    ],
    'full_CPU_upper_bound_seconds': None,
    'full_wall_upper_bound_seconds': None,
    'certified': False,
    'status': 'CANONICAL_E2_RUNTIME_BOUND_UNPROVEN',
  }
