"""Bounded synthetic executor; reference scientific bytes remain unchanged."""

import numpy as np
import time
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_execution as old
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_bounded_inputs as inputs
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_evaluation as metrics
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_resources as resources

b, out, Phase, need = old.b, old.output, old.Phase, old.need


def execute_private(*args, **kwargs):
  raise ValueError('CANONICAL_E2_PRIVATE_EXECUTION_NOT_AUTHORIZED')


def qualify(job, cache, gate, kind, counters, lifetime):
  # Same whole-job arithmetic and proof shape as frozen qualify_selected.
  b._cache_bound(job, cache)
  need(kind in ('Q1', 'Q3') and gate.dtype == np.bool_ and gate.shape == job['p'].shape, 'CANONICAL_BOUNDED_QUALIFICATION')
  selected = np.ascontiguousarray(job['x'][gate])
  token = lifetime.add('selected', selected)
  try:
    expected = cache['u'][gate]
    status = 'CANONICAL_' + kind + '_QUALIFICATION_FAILED'
    if np.any(gate):
      actual = b.canonical.canonical_predict_delta(selected, job['stage2'])
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


class BoundedTrainPipeline(old.TrainPipeline):
  def __init__(self, provider):
    need(type(provider) is inputs.BoundedSyntheticProvider, 'CANONICAL_BOUNDED_EXACT_PROVIDER')
    self.provider = provider
    self.jobs = tuple(provider.train_meta(i) for i in range(32))
    self.counters, self.caches, self.policies, self.details, self.q1, self.q3 = {}, [], [], [], [], []
    self.seals, self.details_seal = {}, None
    self.cache_tokens = []
    for j in self.jobs:
      dimension = 2 * b.original.m.parameters(j['candidate'])[1] + 3
      b.canonical.canonical_predict_delta(np.empty((0, dimension), np.float64), j['stage2'])

  def _check_proofs(self):
    for i, j in enumerate(self.jobs):
      need(self.provider._check(i, 'TRAIN')['train_meta'] is j, 'CANONICAL_BOUNDED_META_OWNER')
    if self.caches:
      need(len(self.caches) == 32, 'CANONICAL_CACHE_COMPLETENESS')
      for j, cache in zip(self.jobs, self.caches, strict=True):
        need(cache['binding'] == j['binding'] and cache['semantics'] == b.canonical.SEMANTICS, 'CANONICAL_CACHE_SOURCE_CONFLICT')
        need(
          type(cache['u']) is type(cache['move_tick']) is np.ndarray
          and cache['u'].dtype == np.float64
          and cache['move_tick'].dtype == np.int64
          and cache['u'].shape == cache['move_tick'].shape == j['p'].shape,
          'CANONICAL_CACHE_DTYPE_CONFLICT',
        )
        need(cache['cache_sha256'] == b._hash((cache['u'], cache['move_tick'])), 'CANONICAL_CACHE_PAYLOAD_CONFLICT')
    for arm, h in self.seals.items():
      need(b._hash([p[arm] for p in self.policies]) == h, 'CANONICAL_FINAL_WINNER_BINDING_CONFLICT')
    if self.details_seal is not None:
      need(b._hash(self.details) == self.details_seal, 'CANONICAL_SELECTION_DETAILS_CONFLICT')

  def cache_potentials(self):
    self._check_proofs()
    for i in range(32):
      with self.provider.features(i) as job:
        cache = b.potential_cache(job, self.counters)
      self.caches.append(cache)
      self.cache_tokens.append(self.provider.lifetime.add('cache', cache))

  def qualify_q1(self):
    self._qualification('Q1', 'D0', self.q1)

  def qualify_q3(self):
    need(self.counters.get('D2_context_decision_selection_calls') == 64, 'CANONICAL_ALL64_BEFORE_Q3')
    self._qualification('Q3', 'D2', self.q3)

  def _qualification(self, kind, arm, proofs):
    self._check_proofs()
    for i, (cache, policy) in enumerate(zip(self.caches, self.policies, strict=True)):
      with self.provider.features(i) as job:
        gate = b.apply_gate(job['p'], job['prior'], policy[arm], arm)
        proofs.append(qualify(job, cache, gate, kind, self.counters, self.provider.lifetime))
    need(len(proofs) == 32, 'CANONICAL_BOUNDED_ALL32_QUALIFICATION')


def one_step(data, policies, counters):
  current, target, prior, p = (data[k] for k in ('current', 'target', 'prior', 'p'))
  truth = target != current
  actual = (target - current).astype(np.float64)
  hold = -actual
  results = {}
  for arm in b.ARMS:
    row = b.infer(data['x'], current, data['stage1'], data['stage2'], policies[arm], arm, counters, scope=b.SCOPE, p_move=p)
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


def _recursive_chunk(chunk, candidate, stage1, stage2, policy, arm, h, counters, lifetime):
  prediction = b.recursive(
    chunk['initial'], chunk['command'], chunk['speed'], candidate, stage1, stage2, policy, arm, h, chunk['available_steps'], counters, scope=b.SCOPE
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


def rollout(provider, index, data, policy, arm, h, counters):
  count, anchor = provider.horizon_metadata(index, h)
  error, baseline, moved = np.empty(count, np.float64), np.empty(count, np.float64), np.empty(count, bool)
  drift = {}
  for first in range(0, count, resources.CHUNK):
    with provider.horizon_chunk(index, h, first) as chunk:
      e, v, m, part = _recursive_chunk(chunk, data['candidate'], data['stage1'], data['stage2'], policy, arm, h, counters, provider.lifetime)
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


class BoundedRun(old.Run):
  def __init__(self, provider, store, binding):
    need(
      type(provider) is inputs.BoundedSyntheticProvider and binding['scope'] == 'SYNTHETIC_ONLY' and binding['private_authority'] is False,
      'CANONICAL_BOUNDED_EXACT_PROVIDER',
    )
    self.provider, self.store, self.binding = provider, store, binding
    self.phase, self.trace = Phase.PREFLIGHT, [Phase.PREFLIGHT.value]
    self.train_digest, self.train_record = None, None
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
      self.pipeline = BoundedTrainPipeline(self.provider)
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
            arms = one_step(active, policies, self.pipeline.counters)
          for arm in b.ARMS:
            for h in b.HORIZONS:
              arms[arm]['rollout'][str(h)] = rollout(self.provider, i, data, policies[arm], arm, h, self.pipeline.counters)
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


def run_synthetic(provider, path, binding):
  protocol, _ = old.public_check()
  need(binding == old.synthetic_binding(binding['head']), 'CANONICAL_CURRENT_BINDING_CONFLICT')
  with out.Store(path) as store:
    run = BoundedRun(provider, store, binding)
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
      }
    except Exception as exc:
      provider.failed = True
      store.write(
        'abort.json', {'schema': 'CANONICAL_SYNTHETIC_ABORT_V1', 'binding': binding, 'phase': run.phase.value, 'reason': type(exc).__name__, 'private_reads': 0}
      )
      raise


BOUNDED_LOCK = 'empirical-hurdle-stage1-v4-e2-canonical-bounded-lock.json'


def public_check():
  old.public_check()
  lock = out.checked(out.decode((old.PUBLIC / BOUNDED_LOCK).read_bytes()))
  for name, h in {**lock['source_sha256'], **lock['frozen_source_sha256']}.items():
    need(out.sha((old.ROOT / name).read_bytes()) == h, 'CANONICAL_BOUNDED_SOURCE_DRIFT')
  return lock


def implementation_binding(head):
  lock = public_check()
  return {
    'schema': 'CANONICAL_BOUNDED_IMPLEMENTATION_ENVELOPE_V1',
    'scope': 'PUBLIC_SYNTHETIC_BOUNDED_ONLY',
    'head': head,
    'source_sha256': lock['source_sha256'],
    'lock_raw_sha256': out.sha((old.PUBLIC / BOUNDED_LOCK).read_bytes()),
    'reference_binding': old.synthetic_binding(head),
    'private_authority': False,
    'HOLDOUT': 'CLOSED',
    'vehicle_authority': 'NONE',
  }


def seal_execution(path, binding, result):
  with out.Store(path, create=False) as store:
    return store.write(
      'execution.json',
      {
        'binding': binding,
        'reference_completion_digest': result['completion_digest'],
        'lifetime': result['lifetime'],
        'materialization_counters': result['materialization_counters'],
        'phase_timings': result['phase_timings'],
      },
    )


def verify_bounded(path, binding, execution_digest):
  # No source/protocol reads, no provider, no inference or recomputation.
  with out.Store(path, create=False) as store:
    evidence = store.read('execution.json', execution_digest)
    need(evidence['binding'] == binding, 'CANONICAL_BOUNDED_VERIFY_BINDING')
  return old.verify_synthetic(path, binding['reference_binding'], evidence['reference_completion_digest'])
