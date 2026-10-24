"""In-memory public synthetic canonical research, never a private E2 executor.

Historical BLAS outputs remain immutable. No readers, fitting, controller APIs,
filesystem/network access, global replacement, or empirical acceptance execution.
"""

import copy
import hashlib
import json
import re
import numpy as np
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_stage2 as canonical
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_decision as d2
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e_decision as d1
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_execution as original

STATUS = 'EXPERIMENTAL_CANONICAL_RESEARCH_NON_WIRED'
SCOPE = 'PUBLIC_SYNTHETIC_CANONICAL_RESEARCH_ONLY'
REFERENCE = 'NEW_CANONICAL_D0_TRAIN_REFERENCE'
ARMS = ('D0', 'D1', 'D2')
HORIZONS = (25, 50, 100, 200)
JOB_FIELDS = frozenset(
  ('candidate', 'fold', 'scope', 'role', 'source_id', 'anchor', 'row_ids', 'segment_stops', 'x', 'p', 'prior', 'current', 'target', 'y', 'stage1', 'stage2')
)
need = d1.need


def _scope(value):
  need(value == SCOPE, 'CANONICAL_RESEARCH_SCOPE_REQUIRED')


def _hash(value):
  def encode(v):
    if type(v) is np.ndarray:
      need(v.dtype.kind in 'bifu', 'CANONICAL_BINDING_ARRAY_DTYPE_CONFLICT')
      return {'dtype': v.dtype.str, 'shape': list(v.shape), 'C_bytes_sha256': hashlib.sha256(v.tobytes(order='C')).hexdigest()}
    if type(v) is dict:
      need(all(type(k) in (str, int) for k in v), 'CANONICAL_BINDING_KEY_TYPE_CONFLICT')
      return [[type(k).__name__, str(k), encode(v[k])] for k in sorted(v, key=lambda k: (type(k).__name__, str(k)))]
    if type(v) in (tuple, list):
      return [encode(item) for item in v]
    if type(v) is float:
      return ['float', v.hex()]
    need(type(v) in (str, int, bool, type(None)), 'CANONICAL_BINDING_TYPE_CONFLICT')
    return [type(v).__name__, v]

  return hashlib.sha256(json.dumps(encode(value), separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def _history_domain(x):
  length = (x.shape[1] - 3) // 2
  history = x[:, length + 1 : 2 * length + 1]
  code = 'CANONICAL_SIGNED16_HISTORY_DOMAIN_CONFLICT'
  need(bool(np.all((history >= -65535) & (history <= 65535))) and np.array_equal(history, np.rint(history)), code)
  # Validation of observed/projected signed16 history, not a new projection.
  previous = x[:, -2, None] - np.cumsum(history[:, ::-1].astype(np.int64), axis=1)
  need(bool(np.all((previous >= -32768) & (previous <= 32767))), code)


def _validate_rows(job):
  need(type(job) is dict and JOB_FIELDS <= set(job), 'CANONICAL_JOB_SCHEMA_CONFLICT')
  _scope(job['scope'])
  need(job['role'] == 'TRAIN' and (job['candidate'], job['fold']) in d1.JOBS, 'CANONICAL_JOB_ROLE_CONFLICT')
  for key in ('source_id', 'anchor'):
    need(type(job[key]) is str and re.fullmatch('[0-9a-f]{64}', job[key]) is not None, 'CANONICAL_SOURCE_IDENTITY_CONFLICT')
  need(type(job['candidate']) is str and type(job['fold']) is str, 'CANONICAL_JOB_ID_TYPE_CONFLICT')
  need(all(type(job[k]) is np.ndarray for k in ('p', 'y', 'prior', 'x', 'current', 'target', 'row_ids')), 'CANONICAL_PLAIN_ARRAY_REQUIRED')
  p, y, prior, x = (job[k] for k in ('p', 'y', 'prior', 'x'))
  d2.validate(p, y, prior)
  n = len(p)
  _, length = original.m.parameters(job['candidate'])
  need(type(x) is np.ndarray and x.dtype == np.float64 and x.shape == (n, 2 * length + 3), 'CANONICAL_FEATURE_SHAPE_CONFLICT')
  need(bool(np.all(np.isfinite(x))) and bool(np.all(x[:, 0] == 1.0)), 'CANONICAL_FEATURE_DOMAIN_CONFLICT')
  need(bool(np.all((prior >= -65535) & (prior <= 65535))), 'CANONICAL_SIGNED16_HISTORY_DOMAIN_CONFLICT')
  _history_domain(x)
  for name in ('current', 'target', 'row_ids'):
    a = job[name]
    need(type(a) is np.ndarray and a.dtype == np.int64 and a.shape == (n,), 'CANONICAL_TICK_ORDER_DTYPE_CONFLICT')
  c, t = job['current'], job['target']
  need(bool(np.all((c >= -32768) & (c <= 32767) & (t >= -32768) & (t <= 32767))), 'CANONICAL_TICK_RANGE_CONFLICT')
  need(np.array_equal(job['row_ids'], np.arange(n)) and np.array_equal(x[:, -3], prior) and np.array_equal(x[:, -2], c), 'CANONICAL_ROW_ORDER_CONFLICT')
  need(np.array_equal(y, t != c), 'CANONICAL_TRUTH_LABEL_CONFLICT')
  stops = job['segment_stops']
  need(type(stops) is tuple and bool(stops) and all(type(v) is int for v in stops) and stops[-1] == n, 'CANONICAL_SEGMENT_BOUNDARY_CONFLICT')
  need(all(b > a for a, b in zip((0,) + stops[:-1], stops, strict=True)), 'CANONICAL_SEGMENT_BOUNDARY_CONFLICT')
  for state in (False, True):
    subset = y[(prior != 0) == state]
    need(bool(np.any(subset)) and bool(np.any(~subset)), 'CANONICAL_CONTEXT_CLASS_MISSING')


def _binding(job):
  return _hash({key: job[key] for key in JOB_FIELDS})


def make_job(data):
  """Snapshot a caller-declared synthetic job. This is no private-data grant.

  Array values alone cannot prove provenance; no private input loader exists.
  The digest detects subsequent source/model/order changes, not caller honesty.
  """
  _validate_rows(data)
  need(set(data) == JOB_FIELDS, 'CANONICAL_JOB_SCHEMA_CONFLICT')
  binding = _binding(data)  # Reject unapproved model objects before any copy hook.
  job = copy.deepcopy(data)
  job['binding'] = binding
  return job


def _bound(job):
  _validate_rows(job)
  need(type(job.get('binding')) is str and job['binding'] == _binding(job), 'CANONICAL_SOURCE_MODEL_ORDER_BINDING_CONFLICT')


def _cache_bound(job, cache):
  _bound(job)
  need(type(cache) is dict and cache.get('binding') == job['binding'], 'CANONICAL_CACHE_SOURCE_CONFLICT')
  need(cache.get('semantics') == canonical.SEMANTICS, 'CANONICAL_CACHE_NUMERICAL_SOURCE_CONFLICT')
  need(type(cache.get('u')) is np.ndarray and cache['u'].dtype == np.float64 and cache['u'].shape == job['p'].shape, 'CANONICAL_CACHE_DTYPE_CONFLICT')
  need(
    type(cache.get('move_tick')) is np.ndarray and cache['move_tick'].dtype == np.int64 and cache['move_tick'].shape == job['p'].shape,
    'CANONICAL_CACHE_DTYPE_CONFLICT',
  )
  need(cache.get('cache_sha256') == _hash((cache['u'], cache['move_tick'])), 'CANONICAL_CACHE_PAYLOAD_CONFLICT')


def require_bytes(actual, expected, status):
  need(type(actual) is np.ndarray and type(expected) is np.ndarray and actual.dtype == expected.dtype == np.float64 and d2.byte_equal(actual, expected), status)


def reconstruct_d0(p, y, counters):
  return d2.reconstruct_D0(p, y, role='TRAIN', counters=counters)


def potential_cache(job, counters):
  _bound(job)
  x, c = job['x'], job['current']
  u = np.empty(len(x), np.float64)
  start = 0
  for stop in job['segment_stops']:
    for first in range(start, stop, original.m.CHUNK):
      last = min(first + original.m.CHUNK, stop)
      u[first:last] = canonical.canonical_predict_delta(np.ascontiguousarray(x[first:last]), job['stage2'])
      d2.count(counters, 'canonical_all_row_calls', last - first)
    start = stop
  move = original.m.project(c.astype(np.float64) + u)
  d2.count(counters, 'canonical_all_row_projection_calls', len(c))
  return {'binding': job['binding'], 'semantics': canonical.SEMANTICS, 'u': u, 'move_tick': move, 'cache_sha256': _hash((u, move))}


def apply_gate(p, prior, decisions, arm):
  need(arm in ARMS and type(decisions) is tuple and len(decisions) == (1 if arm == 'D0' else 2), 'CANONICAL_EXACT_THREE_ARM_CONFLICT')
  need(all(type(v) is float and np.isfinite(v) and 0 <= v <= 1 for v in decisions), 'CANONICAL_DECISION_DOMAIN_CONFLICT')
  d1.probability(p)
  need(type(prior) is np.ndarray and prior.dtype == np.int64 and prior.shape == p.shape, 'CANONICAL_PRIOR_DTYPE_CONFLICT')
  return p > decisions[0] if arm == 'D0' else d1.gate(p, prior, decisions)


def qualify_selected(job, cache, gate, kind, counters):
  _cache_bound(job, cache)
  need(kind in ('Q1', 'Q3', 'D1_DIAGNOSTIC'), 'CANONICAL_QUALIFICATION_KIND_CONFLICT')
  n = len(job['p'])
  need(type(gate) is np.ndarray and gate.dtype == np.bool_ and gate.shape == (n,), 'CANONICAL_QUALIFICATION_GATE_CONFLICT')
  selected = np.ascontiguousarray(job['x'][gate])
  expected = cache['u'][gate]
  status = 'CANONICAL_' + kind + '_QUALIFICATION_FAILED'
  if np.any(gate):
    actual = canonical.canonical_predict_delta(selected, job['stage2'])
    d2.count(counters, kind + '_selected_calls', len(selected))
    require_bytes(actual, expected, status)
    return {'status': 'PASS', 'mode': 'WHOLE_JOB_SELECTED_ROWS', 'selected_stage2_calls': 1}
  # Match original integrated's empty-gate branch: no selected Stage2 call.
  need(not bool(np.any(gate)) and selected.dtype == np.float64 and selected.shape == (0, job['x'].shape[1]), status)
  require_bytes(expected, np.empty(0, np.float64), status)
  delta = np.zeros(n, np.float64)
  projected = job['current'].copy()
  need(bool(np.all(delta.view(np.uint64) == 0)) and np.array_equal(projected, job['current']), status)
  d2.count(counters, kind + '_empty_noop_proofs')
  return {'status': 'PASS', 'mode': 'EXPLICIT_EMPTY_GATE_NOOP', 'selected_stage2_calls': 0}


def infer(x, current, stage1, stage2, decisions, arm, counters, *, scope, p_move=None):
  """No target/reference truth argument; one shared Stage1 score definition."""
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
    delta[gate] = canonical.canonical_predict_delta(np.ascontiguousarray(x[gate]), stage2)
    d2.count(counters, 'canonical_branch_stage2_calls', int(np.count_nonzero(gate)))
    projected[gate] = original.m.project(current[gate].astype(np.float64) + delta[gate])
    d2.count(counters, 'canonical_branch_projection_calls', int(np.count_nonzero(gate)))
  return {'policy': arm, 'context': prior != 0, 'gate': gate, 'delta': delta, 'projected': projected, 'realized_movement': projected != current, 'p_move': p}


def one_step(job, cache, policies, counters):
  _cache_bound(job, cache)
  need(type(policies) is dict and tuple(policies) == ARMS, 'CANONICAL_EXACT_THREE_ARM_CONFLICT')
  results = {}
  actual = (job['target'] - job['current']).astype(np.float64)
  for arm in ARMS:
    result = infer(job['x'], job['current'], job['stage1'], job['stage2'], policies[arm], arm, counters, scope=SCOPE, p_move=job['p'])
    require_bytes(result['delta'], np.where(result['gate'], cache['u'], 0.0), 'CANONICAL_ONE_STEP_CACHE_PARITY_FAILED')
    result.update(
      {'binding': job['binding'], 'row_ids': job['row_ids'].copy(), 'exact_hit': result['projected'] == job['target'], 'residual': result['delta'] - actual}
    )
    result['loss'] = d2.LossTree(d2.leaf_losses(result['delta'], actual, job['y'])).root.copy()
    results[arm] = result
  return results


def recursive(initial, command, speed, candidate, stage1, stage2, decisions, arm, horizon, available_steps, counters, *, scope):
  """Supplied delayed commands; projected full history only, reset each call."""
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
  path[:, 0] = current
  for step in range(horizon):
    history[:, step] = past
    x = np.ascontiguousarray(np.column_stack((np.ones(n), command[:, step : step + length], past, current, speed[:, step])), dtype=np.float64)
    result = infer(x, current, stage1, stage2, decisions, arm, counters, scope=scope)
    new = result['projected']
    path[:, step + 1], gates[:, step], contexts[:, step] = new, result['gate'], result['context']
    probability[:, step], delta[:, step] = result['p_move'], result['delta']
    past[:, :-1] = past[:, 1:]
    past[:, -1] = new - current
    current = new
  d2.count(counters, 'synthetic_recursive_path_calls', n)
  return {'path': path, 'gate': gates, 'context': contexts, 'history_before': history, 'p_move': probability, 'delta': delta}


def path_moved(observed):
  need(type(observed) is np.ndarray and observed.dtype == np.int64 and observed.ndim == 2 and observed.shape[1] > 0, 'CANONICAL_REFERENCE_PATH_CONFLICT')
  return np.any(observed != observed[:, :1], axis=1)


class ResearchPipeline:
  """All-job barriers, terminal abort, no retries or private execution grant."""

  def __init__(self, jobs):
    need(type(jobs) in (list, tuple) and tuple((j['candidate'], j['fold']) for j in jobs) == d1.JOBS, 'CANONICAL_EXACT32_MANIFEST_CONFLICT')
    self.jobs = tuple(jobs)
    self.phase, self.counters = 'INPUT_QUALIFIED', {}
    self.policy_seals, self.details_seal = {}, None
    for j in self.jobs:
      _bound(j)
      # Qualification only; no fit, threshold read, or new normalization.
      canonical.canonical_predict_delta(j['x'][:0], j['stage2'])
      d2.count(self.counters, 'canonical_model_validation_calls')
      require_bytes(original.probability(np.ascontiguousarray(j['x']), j['stage1']), j['p'], 'CANONICAL_STAGE1_SOURCE_SCORE_CONFLICT')
      d2.count(self.counters, 'stage1_source_qualification_calls', len(j['p']))
    self.d0, self.caches, self.policies, self.details = [], [], [], []
    self.q1, self.q3, self.one_steps, self.recursive_results = [], [], [], []

  def _check_proofs(self):
    if self.caches:
      need(len(self.caches) == 32, 'CANONICAL_CACHE_COMPLETENESS_CONFLICT')
      for j, cache in zip(self.jobs, self.caches, strict=True):
        _cache_bound(j, cache)
    else:
      for j in self.jobs:
        _bound(j)
    for arm, seal in self.policy_seals.items():
      status = 'CANONICAL_FINAL_WINNER_BINDING_CONFLICT' if arm == 'D2' else 'CANONICAL_TRAIN_REFERENCE_BINDING_CONFLICT'
      need(_hash([p[arm] for p in self.policies]) == seal, status)
    if self.details_seal is not None:
      need(_hash(self.details) == self.details_seal, 'CANONICAL_SELECTION_DETAILS_BINDING_CONFLICT')

  def _execute(self, expected, completed, action):
    try:
      need(self.phase == expected, 'CANONICAL_RESEARCH_PHASE_BARRIER')
      self._check_proofs()
      action()
      self.phase = completed
    except Exception:
      self.phase = 'FAILED'
      raise

  def reconstruct_d0(self):
    def action():
      self.d0 = [reconstruct_d0(j['p'], j['y'], self.counters) for j in self.jobs]
      self.policies = [{'D0': (float(value['value']),)} for value in self.d0]
      self.details = [{'D0': value, 'guard_reference': REFERENCE} for value in self.d0]
      self.policy_seals['D0'] = _hash([p['D0'] for p in self.policies])
      self.details_seal = _hash(self.details)

    self._execute('INPUT_QUALIFIED', 'D0_COMPLETE', action)

  def cache_potentials(self):
    self._execute('D0_COMPLETE', 'CACHE_COMPLETE', lambda: self.caches.extend(potential_cache(j, self.counters) for j in self.jobs))

  def qualify_q1(self):
    def action():
      for j, cache, policies in zip(self.jobs, self.caches, self.policies, strict=True):
        self.q1.append(qualify_selected(j, cache, apply_gate(j['p'], j['prior'], policies['D0'], 'D0'), 'Q1', self.counters))
      need(len(self.q1) == 32, 'CANONICAL_Q1_COMPLETENESS_CONFLICT')

    self._execute('CACHE_COMPLETE', 'Q1_ALL32_PASS', action)

  def select_d1(self):
    def action():
      for j, policies, details in zip(self.jobs, self.policies, self.details, strict=True):
        result = d1.select_job(j['p'], j['y'], j['prior'], candidate=j['candidate'], fold=j['fold'], anchor=j['anchor'], role='TRAIN')
        details['D1'] = result['contexts']
        policies['D1'] = tuple(result['contexts'][name]['decision'] for name in d2.CONTEXTS)
        for _ in d2.CONTEXTS:
          d2.count(self.counters, 'D1_context_decision_selection_calls')
      self.policy_seals['D1'] = _hash([p['D1'] for p in self.policies])
      self.details_seal = _hash(self.details)

    self._execute('Q1_ALL32_PASS', 'D1_COMPLETE', action)

  def select_d2(self):
    def action():
      for j, cache, policies, details in zip(self.jobs, self.caches, self.policies, self.details, strict=True):
        _cache_bound(j, cache)
        contexts = {}
        for state, name in enumerate(d2.CONTEXTS):
          mask = (j['prior'] != 0) == state
          contexts[name] = d2.select_context(
            j['p'][mask], j['y'][mask], j['current'][mask], j['target'][mask], cache['u'][mask], cache['move_tick'][mask], policies['D0'][0], role='TRAIN'
          )
          d2.count(self.counters, 'D2_context_decision_selection_calls')
        details['D2'] = contexts
        policies['D2'] = tuple(contexts[name]['decision'] for name in d2.CONTEXTS)
      need(self.counters['D2_context_decision_selection_calls'] == 64, 'CANONICAL_D2_COMPLETENESS_CONFLICT')
      self.policy_seals['D2'] = _hash([p['D2'] for p in self.policies])
      self.details_seal = _hash(self.details)

    self._execute('D1_COMPLETE', 'D2_ALL64_PROVISIONAL', action)

  def qualify_q3(self):
    def action():
      for j, cache, policies in zip(self.jobs, self.caches, self.policies, strict=True):
        self.q3.append(qualify_selected(j, cache, apply_gate(j['p'], j['prior'], policies['D2'], 'D2'), 'Q3', self.counters))
      need(len(self.q3) == 32, 'CANONICAL_Q3_COMPLETENESS_CONFLICT')

    self._execute('D2_ALL64_PROVISIONAL', 'Q3_ALL32_PASS', action)

  def compare_one_step(self):
    def action():
      for j, cache, policies in zip(self.jobs, self.caches, self.policies, strict=True):
        qualify_selected(j, cache, apply_gate(j['p'], j['prior'], policies['D1'], 'D1'), 'D1_DIAGNOSTIC', self.counters)
        self.one_steps.append(one_step(j, cache, policies, self.counters))

    self._execute('Q3_ALL32_PASS', 'ONE_STEP_COMPLETE', action)

  def smoke_recursive(self, inputs):
    def action():
      need(type(inputs) in (list, tuple) and len(inputs) == 32, 'CANONICAL_RECURSIVE_MANIFEST_CONFLICT')
      fields = {'binding', 'initial', 'command', 'speed', 'available_steps'}
      need(
        all(type(supplied) is dict and set(supplied) == fields and supplied['binding'] == j['binding'] for j, supplied in zip(self.jobs, inputs, strict=True)),
        'CANONICAL_RECURSIVE_SOURCE_BINDING_CONFLICT',
      )
      for j, policies, supplied in zip(self.jobs, self.policies, inputs, strict=True):
        result = {}
        for arm in ARMS:
          result[arm] = {}
          for horizon in HORIZONS:
            _, length = original.m.parameters(j['candidate'])
            result[arm][horizon] = recursive(
              supplied['initial'],
              supplied['command'][:, : length + horizon - 1],
              supplied['speed'][:, :horizon],
              j['candidate'],
              j['stage1'],
              j['stage2'],
              policies[arm],
              arm,
              horizon,
              supplied['available_steps'],
              self.counters,
              scope=SCOPE,
            )
        self.recursive_results.append(result)

    self._execute('ONE_STEP_COMPLETE', 'SYNTHETIC_READY', action)

  def run(self, inputs):
    for step in (self.reconstruct_d0, self.cache_potentials, self.qualify_q1, self.select_d1, self.select_d2, self.qualify_q3, self.compare_one_step):
      step()
    self.smoke_recursive(inputs)
    return self.summary()

  def summary(self):
    try:
      need(self.phase == 'SYNTHETIC_READY', 'CANONICAL_RESEARCH_NOT_READY')
      self._check_proofs()
      need(
        len(self.q1) == len(self.q3) == len(self.one_steps) == len(self.recursive_results) == 32 and self.counters['D2_context_decision_selection_calls'] == 64,
        'CANONICAL_RESEARCH_COVERAGE_CONFLICT',
      )
    except Exception:
      self.phase = 'FAILED'
      raise
    return {
      'status': 'CANONICAL_D0_D1_D2_RESEARCH_BRIDGE_SYNTHETIC_QUALIFIED',
      'scope': SCOPE,
      'jobs': len(self.jobs),
      'Q1_jobs': len(self.q1),
      'D2_decisions': self.counters['D2_context_decision_selection_calls'],
      'Q3_jobs': len(self.q3),
      'Q2_private_calls': 0,
      'guard_reference': REFERENCE,
      'selected_candidate': None,
      'selected_policy': None,
      'empirical_acceptance_executed': False,
      'private_execution_authorized': False,
      'vehicle_authority': 'NONE',
      'synthetic_counters': self.counters.copy(),
    }
