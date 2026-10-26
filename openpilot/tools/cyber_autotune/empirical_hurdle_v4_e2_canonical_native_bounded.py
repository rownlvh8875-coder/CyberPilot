"""Isolated native bounded PUBLIC SYNTHETIC caller, never a private executor.

Adapted MIT CyberPilot reference at7cf163077, bounded SHA11e94639... and
bridge SHA5add917e...; original scientific sources remain untouched. Only
Stage2 dispatch and optional recursive feature-buffer reuse differ. Backend
identity/timing live outside the unchanged scientific train/result payloads.
"""

import time
import numpy as np
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_bounded as reference
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_native_candidate as native

old, inputs, metrics, resources = reference.old, reference.inputs, reference.metrics, reference.resources
b, out, Phase, need = reference.b, reference.out, reference.Phase, reference.need
canonical, original, d1, d2 = b.canonical, b.original, b.d1, b.d2
_scope, _history_domain = b._scope, b._history_domain
HORIZONS, apply_gate = b.HORIZONS, b.apply_gate
MODES = ('PYTHON_REFERENCE', 'NATIVE_BOUNDED', 'NATIVE_BOUNDED_OPTIMIZED')
STATUS = 'EXPERIMENTAL_PUBLIC_SYNTHETIC_NATIVE_BOUNDED_NON_WIRED'
SITES = frozenset(('MODEL_VALIDATE', 'TRAIN_CACHE', 'Q1', 'Q3', 'DEV_ONE_STEP', 'DEV_RECURSIVE', 'ABI_TEST'))


def execute_private(*args, **kwargs):
  raise ValueError('CANONICAL_E2_PRIVATE_EXECUTION_NOT_AUTHORIZED')


def integrity_optimization_status(optimized):
  need(type(optimized) is bool, 'NATIVE_BOUNDED_MODE_INVALID')
  return 'SOURCE_INTEGRITY_OPTIMIZATION_UNPROVEN'


class FrozenPythonBackend:
  def predict(self, x, model, *, site, trace=False):
    need(site in SITES and not trace, 'NATIVE_BOUNDED_BACKEND_SCOPE')
    return canonical.canonical_predict_delta(x, model)


class VerifiedNativeBackend:
  """Keep every prepared input/model owner strongly reachable through C return.

  The frozen wrapper owns its output/trace locals until the C call returns.
  This adapter pins aligned C input/model arrays, so its np.require calls in
  the wrapper reuse those exact owners. No cached raw pointer/argument reuse.
  Single worker, no reentrant calls; no fallback or artifact auto-discovery.
  Caller provenance is synthetic-only, not authenticated by ndarray contents.
  """

  def __init__(self, receipt_path, receipt_sha256):
    self.candidate = native.NativeCandidate(receipt_path, receipt_sha256)
    self.receipt_sha256 = receipt_sha256
    self._owners = None
    self._counts = {
      'native_calls': 0,
      'native_attempts': 0,
      'native_rows': 0,
      'python_fallback_calls': 0,
      'input_x_copy_bytes': 0,
      'model_array_copy_bytes': 0,
      'coefficient_copy_bytes': 0,
      'successful_output_array_bytes': 0,
      'successful_trace_array_bytes': 0,
      'peak_strong_reference_entries': 0,
      'site_calls': {},
      'site_rows': {},
      'CPU_seconds': 0.0,
      'wall_seconds': 0.0,
    }

  def predict(self, x, model, *, site, trace=False):
    need(site in SITES and self._owners is None, 'NATIVE_BOUNDED_ABI_LIFETIME_UNPROVEN')
    need(type(x) is np.ndarray and x.dtype == np.float64 and x.ndim == 2, 'NATIVE_BOUNDED_INPUT_INVALID')
    need(type(model) is dict and type(model.get('normalizer')) is dict, 'NATIVE_BOUNDED_INPUT_INVALID')
    norm = model['normalizer']
    need(
      set(norm) == canonical.NORMALIZER_FIELDS and all(type(v) is np.ndarray for v in norm.values()) and type(model.get('coefficients')) is np.ndarray,
      'NATIVE_BOUNDED_INPUT_INVALID',
    )
    x_owned = np.require(x, requirements=['C', 'A'])
    owned_norm = {key: np.require(value, requirements=['C', 'A']) for key, value in norm.items()}
    coefficients = np.require(model['coefficients'], requirements=['C', 'A'])
    prepared = {**model, 'normalizer': owned_norm, 'coefficients': coefficients}
    self._owners = (x_owned, *owned_norm.values(), coefficients, prepared, model, x)
    self._counts['peak_strong_reference_entries'] = max(self._counts['peak_strong_reference_entries'], len(self._owners))
    self._counts['input_x_copy_bytes'] += x_owned.nbytes if x_owned is not x else 0
    self._counts['model_array_copy_bytes'] += sum(value.nbytes for key, value in owned_norm.items() if value is not norm[key])
    self._counts['coefficient_copy_bytes'] += coefficients.nbytes if coefficients is not model['coefficients'] else 0
    self._counts['native_attempts'] += 1
    wall, cpu = time.perf_counter(), time.process_time()
    try:
      result = self.candidate.predict(x_owned, prepared, trace=trace)
      self._counts['native_calls'] += 1
      self._counts['successful_output_array_bytes'] += result[0].nbytes if trace else result.nbytes
      self._counts['successful_trace_array_bytes'] += result[1].nbytes if trace else 0
      self._counts['native_rows'] += len(x_owned)
      self._counts['site_calls'][site] = self._counts['site_calls'].get(site, 0) + 1
      self._counts['site_rows'][site] = self._counts['site_rows'].get(site, 0) + len(x_owned)
      return result
    except ValueError as error:
      if str(error).startswith('CANONICAL_NATIVE_NUMERICAL_STATUS_'):
        self._counts['native_calls'] += 1  # C executed and returned a failure status.
      raise
    finally:
      self._counts['CPU_seconds'] += time.process_time() - cpu
      self._counts['wall_seconds'] += time.perf_counter() - wall
      self._owners = None

  def envelope(self):
    return {
      **self._counts,
      'site_calls': dict(self._counts['site_calls']),
      'site_rows': dict(self._counts['site_rows']),
      'active_strong_reference_entries': 0 if self._owners is None else len(self._owners),
      'receipt_sha256': self.receipt_sha256,
      'native_binary_sha256': self.candidate.receipt['binary_sha256'],
      'native_source_sha256': self.candidate.receipt['source_sha256'],
      'ownership_accounting': 'STRONG_REFERENCE_ENTRIES_NOT_UNIQUE_OWNER_OR_PROCESS_BYTE_CENSUS',
      'scope': 'PUBLIC_SYNTHETIC_NATIVE_BOUNDED_INTEGRATION_ONLY',
      'private_execution_authorized': False,
      'production_runtime_integration_authorized': False,
    }


def require_backend(backend):
  need(type(backend) in (FrozenPythonBackend, VerifiedNativeBackend), 'NATIVE_BOUNDED_EXACT_BACKEND_REQUIRED')


def potential_cache(job, counters, backend):
  b._bound(job)
  x, current = job['x'], job['current']
  u = np.empty(len(x), np.float64)
  start = 0
  for stop in job['segment_stops']:
    for first in range(start, stop, original.m.CHUNK):
      last = min(first + original.m.CHUNK, stop)
      u[first:last] = backend.predict(np.ascontiguousarray(x[first:last]), job['stage2'], site='TRAIN_CACHE')
      d2.count(counters, 'canonical_all_row_calls', last - first)
    start = stop
  move = original.m.project(current.astype(np.float64) + u)
  d2.count(counters, 'canonical_all_row_projection_calls', len(current))
  return {'binding': job['binding'], 'semantics': canonical.SEMANTICS, 'u': u, 'move_tick': move, 'cache_sha256': b._hash((u, move))}


def qualify(job, cache, gate, kind, counters, lifetime, backend):
  # Same whole-job arithmetic and proof shape as frozen qualify_selected.
  b._cache_bound(job, cache)
  need(kind in ('Q1', 'Q3') and gate.dtype == np.bool_ and gate.shape == job['p'].shape, 'CANONICAL_BOUNDED_QUALIFICATION')
  selected = np.ascontiguousarray(job['x'][gate])
  token = lifetime.add('selected', selected)
  try:
    expected = cache['u'][gate]
    status = 'CANONICAL_' + kind + '_QUALIFICATION_FAILED'
    if np.any(gate):
      actual = backend.predict(selected, job['stage2'], site=kind)
      b.d2.count(counters, kind + '_selected_calls', len(selected))
      b.require_bytes(actual, expected, status)
      return {'status': 'PASS', 'mode': 'WHOLE_JOB_SELECTED_ROWS', 'selected_stage2_calls': 1}
    need(selected.dtype == np.float64 and selected.shape == (0, job['x'].shape[1]), status)
    b.require_bytes(expected, np.empty(0, np.float64), status)
    delta = np.zeros(len(gate), np.float64)
    projected = job['current'].copy()
    need(np.all(delta.view(np.uint64) == 0) and np.array_equal(projected, job['current']), status)
    b.d2.count(counters, kind + '_empty_noop_proofs')
    return {'status': 'PASS', 'mode': 'EXPLICIT_EMPTY_GATE_NOOP', 'selected_stage2_calls': 0}
  finally:
    selected = None
    lifetime.release(token)


class NativeTrainPipeline(reference.BoundedTrainPipeline):
  def __init__(self, provider, backend):
    need(type(provider) is inputs.BoundedSyntheticProvider and type(backend) is VerifiedNativeBackend, 'NATIVE_BOUNDED_EXACT_PROVIDER_BACKEND')
    self.provider, self.backend = provider, backend
    self.jobs = tuple(provider.train_meta(i) for i in range(32))
    self.counters, self.caches, self.policies, self.details, self.q1, self.q3 = {}, [], [], [], [], []
    self.seals, self.details_seal, self.cache_tokens = {}, None, []
    for job in self.jobs:
      dimension = 2 * b.original.m.parameters(job['candidate'])[1] + 3
      backend.predict(np.empty((0, dimension), np.float64), job['stage2'], site='MODEL_VALIDATE')

  def cache_potentials(self):
    self._check_proofs()
    for i in range(32):
      with self.provider.features(i) as job:
        cache = potential_cache(job, self.counters, self.backend)
      self.caches.append(cache)
      self.cache_tokens.append(self.provider.lifetime.add('cache', cache))

  def _qualification(self, kind, arm, proofs):
    self._check_proofs()
    for i, (cache, policy) in enumerate(zip(self.caches, self.policies, strict=True)):
      with self.provider.features(i) as job:
        gate = b.apply_gate(job['p'], job['prior'], policy[arm], arm)
        proofs.append(qualify(job, cache, gate, kind, self.counters, self.provider.lifetime, self.backend))
    need(len(proofs) == 32, 'CANONICAL_BOUNDED_ALL32_QUALIFICATION')


def infer(x, current, stage1, stage2, decisions, arm, counters, *, scope, backend, p_move=None, site='DEV_ONE_STEP'):
  """No target/reference truth argument; one shared Stage1 score definition."""
  require_backend(backend)
  _scope(scope)
  need(type(x) is np.ndarray and x.dtype == np.float64 and x.ndim == 2 and x.shape[1] in canonical.FEATURE_DIMENSIONS, 'CANONICAL_INFERENCE_FEATURE_CONFLICT')
  need(type(current) is np.ndarray and current.dtype == np.int64 and current.shape == (len(x),), 'CANONICAL_INFERENCE_CURRENT_CONFLICT')
  original.m.finite(x)
  need(np.array_equal(x[:, -2], current) and bool(np.all(x[:, 0] == 1.0)), 'CANONICAL_INFERENCE_ROW_CONFLICT')
  need(bool(np.all((current >= -32768) & (current <= 32767))), 'CANONICAL_INFERENCE_TICK_RANGE')
  _history_domain(x)
  prior = x[:, -3].astype(np.int64)
  need(np.array_equal(prior, x[:, -3]), 'CANONICAL_INFERENCE_PRIOR_CONFLICT')
  if p_move is None:
    p = original.probability(np.ascontiguousarray(x), stage1)
    d2.count(counters, 'canonical_branch_stage1_calls', len(x))
  else:
    d1.probability(p_move)
    need(p_move.shape == current.shape, 'CANONICAL_SCORE_ORDER_CONFLICT')
    p = p_move
  gate = apply_gate(p, prior, decisions, arm)
  delta, projected = np.zeros(len(x), np.float64), current.copy()
  if np.any(gate):
    delta[gate] = backend.predict(np.ascontiguousarray(x[gate]), stage2, site=site)
    d2.count(counters, 'canonical_branch_stage2_calls', int(np.count_nonzero(gate)))
    projected[gate] = original.m.project(current[gate].astype(np.float64) + delta[gate])
    d2.count(counters, 'canonical_branch_projection_calls', int(np.count_nonzero(gate)))
  return {'policy': arm, 'context': prior != 0, 'gate': gate, 'delta': delta, 'projected': projected, 'realized_movement': projected != current, 'p_move': p}


def recursive(initial, command, speed, candidate, stage1, stage2, decisions, arm, horizon, available_steps, counters, *, scope, backend, optimized=False):
  """Supplied delayed commands; projected full history only, reset each call."""
  require_backend(backend)
  need(type(optimized) is bool, 'NATIVE_BOUNDED_MODE_INVALID')
  _scope(scope)
  _, length = original.m.parameters(candidate)
  need(
    horizon in HORIZONS and type(initial) is np.ndarray and initial.dtype == np.int64 and initial.ndim == 2 and initial.shape[1] == length + 1,
    'CANONICAL_RECURSIVE_HISTORY_CONFLICT',
  )
  n = len(initial)
  need(n > 0 and bool(np.all((initial >= -32768) & (initial <= 32767))), 'CANONICAL_RECURSIVE_HISTORY_CONFLICT')
  need(type(command) is np.ndarray and command.dtype == np.float64 and command.shape == (n, length + horizon - 1), 'CANONICAL_RECURSIVE_EXOGENOUS_CONFLICT')
  need(type(speed) is np.ndarray and speed.dtype == np.float64 and speed.shape == (n, horizon), 'CANONICAL_RECURSIVE_EXOGENOUS_CONFLICT')
  need(
    type(available_steps) is np.ndarray and available_steps.dtype == np.int64 and available_steps.shape == (n,) and bool(np.all(available_steps >= horizon)),
    'CANONICAL_SEGMENT_BOUNDARY_CONFLICT',
  )
  original.m.finite(command, speed)
  current, past = initial[:, -1].copy(), np.diff(initial, axis=1)
  path = np.empty((n, horizon + 1), np.int64)
  gates, contexts = np.empty((n, horizon), bool), np.empty((n, horizon), bool)
  history = np.empty((n, horizon, length), np.int64)
  probability, delta = np.empty((n, horizon), np.float64), np.empty((n, horizon), np.float64)
  workspace = np.empty((n, 2 * length + 3), np.float64) if optimized else None
  if optimized:
    workspace[:, 0] = 1.0
  path[:, 0] = current
  for step in range(horizon):
    history[:, step] = past
    if optimized:
      workspace[:, 1 : length + 1] = command[:, step : step + length]
      workspace[:, length + 1 : 2 * length + 1] = past
      workspace[:, -2] = current
      workspace[:, -1] = speed[:, step]
      x = workspace
    else:
      x = np.ascontiguousarray(np.column_stack((np.ones(n), command[:, step : step + length], past, current, speed[:, step])), dtype=np.float64)
    result = infer(x, current, stage1, stage2, decisions, arm, counters, scope=scope, backend=backend, site='DEV_RECURSIVE')
    new = result['projected']
    path[:, step + 1], gates[:, step], contexts[:, step] = new, result['gate'], result['context']
    probability[:, step], delta[:, step] = result['p_move'], result['delta']
    past[:, :-1] = past[:, 1:]
    past[:, -1] = new - current
    current = new
  d2.count(counters, 'synthetic_recursive_path_calls', n)
  return {'path': path, 'gate': gates, 'context': contexts, 'history_before': history, 'p_move': probability, 'delta': delta}


def one_step(data, policies, counters, backend):
  current, target, prior, p = (data[k] for k in ('current', 'target', 'prior', 'p'))
  truth = target != current
  actual = (target - current).astype(np.float64)
  hold = -actual
  results = {}
  for arm in b.ARMS:
    row = infer(data['x'], current, data['stage1'], data['stage2'], policies[arm], arm, counters, scope=b.SCOPE, p_move=p, backend=backend)
    error = row['delta'] - actual
    predicted = row['projected']
    pair = metrics.pair(error, hold, data['anchor'])
    if pair is not None:
      pair['candidate'].update({'exact_hit': float(np.mean(predicted == target)), 'within_one_tick': float(np.mean(np.abs(predicted - target) <= 1))})
      pair['comparator'].update({'exact_hit': float(np.mean(current == target)), 'within_one_tick': float(np.mean(np.abs(current - target) <= 1))})
    results[arm] = {
      'status': 'EXECUTED_COMPLETE',
      'one_step': pair,
      'true_move': metrics.pair(error[truth], hold[truth], metrics.subset_anchor(data['anchor'], truth)),
      'tick_diagnostics': metrics.e1.tick_diagnostics(current, target, prior, row),
      'score_diagnostics': metrics.e1.score_diagnostics(p, truth, prior),
      'rollout': {},
    }
  return results


def _recursive_chunk(chunk, candidate, stage1, stage2, policy, arm, h, counters, lifetime, backend, optimized):
  prediction = recursive(
    chunk['initial'],
    chunk['command'],
    chunk['speed'],
    candidate,
    stage1,
    stage2,
    policy,
    arm,
    h,
    chunk['available_steps'],
    counters,
    scope=b.SCOPE,
    backend=backend,
    optimized=optimized,
  )
  token = lifetime.add('trace', prediction)
  try:
    reference = chunk['observed']  # Used after prediction, never an inference argument.
    error = (prediction['path'][:, -1] - reference[:, -1]).astype(np.float64)
    baseline = (reference[:, 0] - reference[:, -1]).astype(np.float64)
    moved = b.path_moved(reference)
    drift, _, _ = metrics.e1.drift_chunk(
      chunk['initial'], reference, prediction['path'], prediction['gate'], prediction['context'], b.original.m.parameters(candidate)[1]
    )
    return error, baseline, moved, drift
  finally:
    prediction.clear()
    lifetime.release(token)


def rollout(provider, index, data, policy, arm, h, counters, backend, optimized):
  count, anchor = provider.horizon_metadata(index, h)
  error, baseline, moved = np.empty(count, np.float64), np.empty(count, np.float64), np.empty(count, bool)
  drift = {}
  for first in range(0, count, resources.CHUNK):
    with provider.horizon_chunk(index, h, first) as chunk:
      e, v, m, part = _recursive_chunk(
        chunk, data['candidate'], data['stage1'], data['stage2'], policy, arm, h, counters, provider.lifetime, backend, optimized
      )
      last = first + len(e)
      error[first:last], baseline[first:last], moved[first:last] = e, v, m
      for key, value in part.items():
        drift[key] = drift.get(key, np.zeros_like(value)) + value
  return {
    'overall': metrics.pair(error, baseline, anchor),
    'path_moved': metrics.pair(error[moved], baseline[moved], metrics.subset_anchor(anchor, moved)),
    'status': 'COMPLETE' if count >= 201 and int(np.count_nonzero(moved)) >= 201 else 'V4_ROLLOUT_SUPPORT_FAILURE',
    'full_state_drift': {key: value.tolist() for key, value in drift.items()},
  }


class NativeRun(old.Run):
  def __init__(self, provider, store, binding, backend, optimized=False):
    need(
      type(provider) is inputs.BoundedSyntheticProvider and binding['scope'] == 'SYNTHETIC_ONLY' and binding['private_authority'] is False,
      'CANONICAL_BOUNDED_EXACT_PROVIDER',
    )
    self.provider, self.store, self.binding = provider, store, binding
    self.phase, self.trace = Phase.PREFLIGHT, [Phase.PREFLIGHT.value]
    self.train_digest, self.train_record = None, None
    need(type(backend) is VerifiedNativeBackend and type(optimized) is bool, 'NATIVE_BOUNDED_EXACT_BACKEND_REQUIRED')
    self.backend, self.optimized = backend, optimized
    self.phase_timings = {}

  def advance(self, expected, completed, action):
    wall, cpu = time.perf_counter(), time.process_time()
    try:
      return super().advance(expected, completed, action)
    finally:
      self.phase_timings[completed.value] = {'wall_seconds': time.perf_counter() - wall, 'CPU_seconds': time.process_time() - cpu}

  def train(self):
    try:
      need(self.phase == Phase.PREFLIGHT, 'CANONICAL_TERMINAL_NO_RETRY')
      self.pipeline = NativeTrainPipeline(self.provider, self.backend)
      for before, after, action in (
        (Phase.PREFLIGHT, Phase.D0, self.pipeline.reconstruct_d0),
        (Phase.D0, Phase.CACHE, self.pipeline.cache_potentials),
        (Phase.CACHE, Phase.Q1, self.pipeline.qualify_q1),
        (Phase.Q1, Phase.D1, self.pipeline.select_d1),
        (Phase.D1, Phase.D2, self.pipeline.select_d2),
        (Phase.D2, Phase.Q3, self.pipeline.qualify_q3),
      ):
        self.advance(before, after, action)
      self.pipeline._check_proofs()
      self.train_record = {
        'schema': 'CANONICAL_SYNTHETIC_TRAIN_V1',
        'binding': self.binding,
        'guard_reference': b.REFERENCE,
        'jobs': [
          {
            'job': list(b.d1.JOBS[i]),
            'identity': j['binding'],
            'decisions': {arm: list(policies[arm]) for arm in b.ARMS},
            'Q1': self.pipeline.q1[i],
            'Q3': self.pipeline.q3[i],
            'details': self.pipeline.details[i],
            'cache_sha256': self.pipeline.caches[i]['cache_sha256'],
          }
          for i, (j, policies) in enumerate(zip(self.pipeline.jobs, self.pipeline.policies, strict=True))
        ],
      }

      def seal_train():
        old.validate_train(self.train_record, self.binding)
        self.train_digest = self.store.write('train.json', self.train_record)
        loaded = self.store.read('train.json', self.train_digest)
        old.validate_train(loaded, self.binding)
        need({k: v for k, v in loaded.items() if k != 'receipt_sha256'} == self.train_record, 'CANONICAL_TRAIN_READBACK_MISMATCH')

      self.advance(Phase.Q3, Phase.SEAL, seal_train)
    except Exception:
      self.phase = Phase.FAILED
      self.provider.failed = True
      raise

  def evaluate(self, clauses):
    jobs = []

    def unlock():
      self.pipeline._check_proofs()
      loaded = self.store.read('train.json', self.train_digest)
      old.validate_train(loaded, self.binding)
      need(out.canonical({k: v for k, v in loaded.items() if k != 'receipt_sha256'}) == out.canonical(self.train_record), 'CANONICAL_CHANGED_TRAIN_SEAL')
      self.train_scores = [metrics.e1.score_diagnostics(j['p'], j['y'], j['prior']) for j in self.pipeline.jobs]
      self.provider.unlock(self.train_digest, loaded)
      self.pipeline.caches.clear()
      for token in self.pipeline.cache_tokens:
        self.provider.lifetime.release(token)
      self.pipeline.cache_tokens.clear()
      self.provider.retire_train()

    self.advance(Phase.SEAL, Phase.DEV, unlock)

    def compute():
      for i in range(32):
        policies = {arm: tuple(self.train_record['jobs'][i]['decisions'][arm]) for arm in b.ARMS}
        with self.provider.dev_job(i, self.train_digest) as data:
          with self.provider.features(i, 'DEV') as active:
            arms = one_step(active, policies, self.pipeline.counters, self.backend)
          for arm in b.ARMS:
            for h in b.HORIZONS:
              arms[arm]['rollout'][str(h)] = rollout(self.provider, i, data, policies[arm], arm, h, self.pipeline.counters, self.backend, self.optimized)
            arms[arm]['gate'] = metrics.e1.gates.fold_gate(arms[arm], clauses)
          train_score = self.train_scores[i]
          for arm in b.ARMS:
            arms[arm]['train_dev_transfer'] = metrics.e1.score_transfer(train_score, arms[arm]['score_diagnostics'])
          jobs.append({'candidate_id': data['candidate'], 'fold': data['fold'], 'anchor': data['anchor'], 'arms': arms, 'evidence_scope': 'SYNTHETIC_ONLY'})

    self.advance(Phase.DEV, Phase.EVALUATE, compute)
    self.advance(Phase.EVALUATE, Phase.ACCEPTANCE, lambda: need(len(jobs) == 32, 'CANONICAL_DEV_COMPLETENESS'))
    self.advance(Phase.ACCEPTANCE, Phase.COMPLETE, lambda: None)
    qualifying = {arm: sum(all(jobs[2 * i + f]['arms'][arm]['gate']['pass'] for f in (0, 1)) for i in range(16)) for arm in b.ARMS}
    return {
      'schema': 'CANONICAL_SYNTHETIC_RESULT_V1',
      'binding': self.binding,
      'evidence_scope': 'SYNTHETIC_ONLY',
      'empirical_acceptance': False,
      'coverage': {'D0': 32, 'D1': 64, 'D2': 64, 'Q1': 32, 'Q3': 32, 'DEV_jobs': 32},
      'trace': self.trace,
      'jobs': jobs,
      'synthetic_qualifying_both_fold_counts': qualifying,
      'selected_candidate': None,
      'selected_policy': None,
      'validation_domains': old.domain_receipt(jobs),
      'synthetic_counters': dict(self.pipeline.counters),
      'source_writes': 0,
      'private_reads': 0,
      'HOLDOUT': 'CLOSED',
      'vehicle_authority': 'NONE',
      'train_raw_sha256': self.train_digest,
    }


def run_synthetic(provider, path, binding, backend, *, optimized=False):
  protocol, _ = old.public_check()
  need(binding == old.synthetic_binding(binding['head']), 'CANONICAL_CURRENT_BINDING_CONFLICT')
  with out.Store(path) as store:
    run = NativeRun(provider, store, binding, backend, optimized)
    try:
      run.train()
      result = run.evaluate(protocol['acceptance']['clauses'])
      digest = store.write('result.json', result)
      completion = store.write(
        'complete.json', {'schema': 'CANONICAL_SYNTHETIC_COMPLETE_V1', 'binding': binding, 'result_raw_sha256': digest, 'train_raw_sha256': run.train_digest}
      )
      return {
        **result,
        'completion_digest': completion,
        'synthetic_output_bytes': store.total,
        'lifetime': provider.lifetime.snapshot(),
        'materialization_counters': dict(provider.counters),
        'phase_timings': dict(run.phase_timings),
        'native_envelope': backend.envelope(),
        'caller_optimization': 'REUSED_RECURSIVE_FEATURE_BUFFER' if optimized else 'NONE',
        'source_integrity_optimization': integrity_optimization_status(optimized),
      }
    except Exception as exc:
      provider.failed = True
      store.write(
        'abort.json', {'schema': 'CANONICAL_SYNTHETIC_ABORT_V1', 'binding': binding, 'phase': run.phase.value, 'reason': type(exc).__name__, 'private_reads': 0}
      )
      raise
