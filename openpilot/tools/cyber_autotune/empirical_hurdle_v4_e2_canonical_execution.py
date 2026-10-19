"""Additive readiness executor. Private entry is blocked before any I/O."""

from enum import StrEnum
import math
from pathlib import Path
import re
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_bridge as b
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_inputs as inputs
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_output as output
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_evaluation as evaluation

need = b.need
ROOT = Path(__file__).resolve().parents[3]
PUBLIC = ROOT / 'docs/cyberpilot/changes'
PROTOCOL = 'empirical-hurdle-stage1-v4-e2-canonical-private-readiness-protocol.json'
LOCK = 'empirical-hurdle-stage1-v4-e2-canonical-readiness-lock.json'


class Phase(StrEnum):
  PREFLIGHT = 'A_PREFLIGHT'
  D0 = 'B_ALL32_D0'
  CACHE = 'C_ALL32_POTENTIALS'
  Q1 = 'D_ALL32_Q1'
  D1 = 'E_ALL64_D1'
  D2 = 'F_ALL64_D2'
  Q3 = 'G_ALL32_Q3'
  SEAL = 'H_DURABLE_TRAIN'
  DEV = 'I_DEV_UNLOCK'
  EVALUATE = 'J_THREE_ARM_DEV'
  ACCEPTANCE = 'K_FROZEN32_22'
  COMPLETE = 'COMPLETE_SYNTHETIC_REPEAT'
  FAILED = 'FAILED_TERMINAL'


def execute_private(*args, **kwargs):
  # Do not inspect supplied paths, grants, old controls or model metadata.
  raise ValueError('CANONICAL_E2_PRIVATE_EXECUTION_NOT_AUTHORIZED')


def validate_future_authority(binding):
  need(type(binding) is dict and binding.get('schema') == 'FRESH_CANONICAL_E2_GRANT_V1', 'CANONICAL_FRESH_GRANT_REQUIRED')
  need(
    binding.get('scope') == 'CANONICAL_E2_EXPLICIT_FUTURE_EXECUTION'
    and binding.get('F_AUTHORIZED') is False
    and binding.get('HOLDOUT') == 'CLOSED'
    and binding.get('vehicle_authority') == 'NONE',
    'CANONICAL_FUTURE_AUTHORITY_CONFLICT',
  )
  ci = binding.get('FULL_CI', {})
  need(
    ci.get('scope') == 'FULL_CI' and ci.get('head') == binding.get('head') and ci.get('status') == 'completed' and ci.get('conclusion') == 'success',
    'CANONICAL_FULL_CI_ELIGIBILITY_REQUIRED',
  )
  need(
    binding.get('resource_status') == 'CANONICAL_E2_RESOURCE_PREFLIGHT_PROVEN_STATIC_ONLY' and binding.get('input_status') == 'EXACT_INPUT_BINDING_VERIFIED',
    'CANONICAL_FUTURE_PREFLIGHT_REQUIRED',
  )
  need(
    set(binding.get('reviews', {})) == {'SCIENCE', 'AUTHORITY'}
    and all(v.get('approval') == 'APPROVED' and v.get('head') == binding['head'] for v in binding['reviews'].values()),
    'CANONICAL_FRESH_REVIEWS_REQUIRED',
  )
  execute_private()  # This HEAD has no trusted private capability issuer.


def resource_plan(n=336941, p=93, source_rows=916535, segments=154):
  need(
    type(n) is type(p) is type(source_rows) is type(segments) is int
    and 0 < n <= 336941
    and p in (5, 13, 33, 93)
    and 0 < source_rows <= 916535
    and 0 < segments <= 154,
    'CANONICAL_RESOURCE_CAP',
  )
  x = n * p * 8
  components = {
    'retained_64_train_dev_provider_features': 64 * x,
    'retained_32_pipeline_features': 32 * x,
    'retained_cache_and_one_step_vectors_upper': 32 * n * 160,
    'one_job_index_transform_hash_workspace': 8 * x,
    'finite_boolean_temporary': n * p,
    'source_vectors': 50 * source_rows,
    'retained_prebuilt_paths_max_scenario': 32 * n * 8 * (8 * 45 + 3 * 375 + 8),
    'chunk512_recursive_history': 512 * 200 * 45 * 8,
    'loss_tree_and_sort_upper': 256 * (1 << (n - 1).bit_length()),
    'serialization_and_outputs': 384 * 1024**2,
    'Python_native_reserve': 2 * 1024**3,
  }
  total = sum(components.values())
  return {
    'status': 'CANONICAL_E2_RESOURCE_PREFLIGHT_UNPROVEN',
    'known_buffer_scenario_bytes': total,
    'total_peak_proven': False,
    'components': components,
    'address_space_cap': 8 * 1024**3,
    'cpu_cap_seconds': 21600,
    'wall_cap_seconds': 43200,
    'all_row_calls_max': 32 * (math.ceil(n / 512) + segments - 1),
    'note': 'Known buffers exceed capacity; full peak/runtime unproven. No limit increased.',
    'private_execution_ready': False,
  }


def public_check():
  protocol_raw = (PUBLIC / PROTOCOL).read_bytes()
  protocol = output.checked(output.decode(protocol_raw))
  lock = output.checked(output.decode((PUBLIC / LOCK).read_bytes()))
  for name, digest in {**protocol['frozen_numerics'], **protocol['source_sha256'], **lock['source_sha256']}.items():
    need(output.sha((ROOT / name).read_bytes()) == digest, 'CANONICAL_PUBLIC_SOURCE_DRIFT')
  for name, digest in lock['frozen_source_sha256'].items():
    need(output.sha((ROOT / name).read_bytes()) == digest, 'CANONICAL_FROZEN_SOURCE_DRIFT')
  return protocol, output.sha(protocol_raw)


def synthetic_binding(head):
  need(re.fullmatch('[0-9a-f]{40}', head) is not None, 'CANONICAL_HEAD_BINDING')
  protocol, raw = public_check()
  return {
    'scope': 'SYNTHETIC_ONLY',
    'head': head,
    'protocol_sha256': raw,
    'protocol_receipt': protocol['receipt_sha256'],
    'source_sha256': protocol['source_sha256'],
    'implementation_lock_raw_sha256': output.sha((PUBLIC / LOCK).read_bytes()),
    'private_authority': False,
    'HOLDOUT': 'CLOSED',
    'vehicle_authority': 'NONE',
  }


def validate_train(record, binding):
  need(
    record.get('schema') == 'CANONICAL_SYNTHETIC_TRAIN_V1' and record.get('binding') == binding and record.get('guard_reference') == b.REFERENCE,
    'CANONICAL_TRAIN_BINDING_CONFLICT',
  )
  need(tuple(tuple(j['job']) for j in record['jobs']) == b.d1.JOBS, 'CANONICAL_TRAIN_COMPLETENESS')
  for row in record['jobs']:
    need(set(row['decisions']) == set(b.ARMS) and re.fullmatch('[0-9a-f]{64}', row['identity']) is not None, 'CANONICAL_TRAIN_SCHEMA')
    for arm, size in (('D0', 1), ('D1', 2), ('D2', 2)):
      ds = row['decisions'][arm]
      need(type(ds) is list and len(ds) == size and all(type(v) is float and math.isfinite(v) and 0 <= v <= 1 for v in ds), 'CANONICAL_TRAIN_DECISION_CONFLICT')
    for kind in ('Q1', 'Q3'):
      proof = row[kind]
      need(set(proof) == {'status', 'mode', 'selected_stage2_calls'} and proof['status'] == 'PASS', 'CANONICAL_TRAIN_QUALIFICATION_CONFLICT')
      need(
        (proof['mode'], proof['selected_stage2_calls']) in (('WHOLE_JOB_SELECTED_ROWS', 1), ('EXPLICIT_EMPTY_GATE_NOOP', 0)),
        'CANONICAL_TRAIN_QUALIFICATION_CONFLICT',
      )
    need(row['details']['D0']['value'] == row['decisions']['D0'][0], 'CANONICAL_D0_SEAL_CONTRADICTION')
    for i, name in enumerate(b.d2.CONTEXTS):
      need(row['details']['D1'][name]['decision'] == row['decisions']['D1'][i], 'CANONICAL_D1_SEAL_CONTRADICTION')
    contexts = row['details']['D2']
    need(set(contexts) == set(b.d2.CONTEXTS), 'CANONICAL_TRAIN_CONTEXT_CONFLICT')
    for index, name in enumerate(b.d2.CONTEXTS):
      c = contexts[name]
      old = c['D0_reference']
      need(type(old['TP']) is int and type(old['harmful_static']) is int and type(old['net_exact_hit_gain']) is int, 'CANONICAL_D0_COUNTER_TYPE')
      need(all(type(old[k]) is float and math.isfinite(old[k]) and old[k] >= 0 for k in ('TRUE_MOVE_SSE', 'TRUE_MOVE_SAE')), 'CANONICAL_D0_LOSS_TYPE')
      need(
        all(type(c[k]) is int for k in ('count', 'positive', 'negative', 'TRUE_MOVE_TP', 'harmful_static', 'net_exact_hit_gain')),
        'CANONICAL_TRAIN_COUNTER_TYPE',
      )
      need(c['positive'] > 0 and c['negative'] > 0 and c['count'] == c['positive'] + c['negative'], 'CANONICAL_TRAIN_SUPPORT')
      need(
        0 <= old['TP'] <= c['TRUE_MOVE_TP'] <= c['positive'] and 0 <= c['harmful_static'] <= old['harmful_static'] <= c['negative'],
        'CANONICAL_TRAIN_COUNTER_BOUNDS',
      )
      need(-c['negative'] <= old['net_exact_hit_gain'] <= c['net_exact_hit_gain'] <= c['positive'], 'CANONICAL_TRAIN_GAIN_BOUNDS')
      need(
        all(type(c[k]) is float and math.isfinite(c[k]) and c[k] >= 0 for k in ('continuous_sse', 'continuous_sae', 'TRUE_MOVE_SSE', 'TRUE_MOVE_SAE')),
        'CANONICAL_TRAIN_LOSS_TYPE',
      )
      need(
        c['TRUE_MOVE_TP'] >= old['TP']
        and c['TRUE_MOVE_SSE'] <= old['TRUE_MOVE_SSE']
        and c['TRUE_MOVE_SAE'] <= old['TRUE_MOVE_SAE']
        and c['harmful_static'] <= old['harmful_static'],
        'CANONICAL_TRAIN_NUMERIC_GUARD_CONTRADICTION',
      )
      need(
        c['decision'] == row['decisions']['D2'][index]
        and c['witness_verified'] is True
        and set(c['guards']) == {'TRUE_MOVE_TP', 'TRUE_MOVE_SSE', 'TRUE_MOVE_SAE', 'HARMFUL_STATIC'}
        and all(v is True for v in c['guards'].values()),
        'CANONICAL_TRAIN_GUARD_CONFLICT',
      )


class TrainPipeline:
  """TRAIN saved-score selection; Stage1 heads are intentionally absent here."""

  def __init__(self, jobs):
    need(tuple((j['candidate'], j['fold']) for j in jobs) == b.d1.JOBS, 'CANONICAL_EXACT32_MANIFEST_CONFLICT')
    self.jobs = jobs
    self.counters = {}
    self.caches = []
    self.policies = []
    self.details = []
    self.q1 = []
    self.q3 = []
    self.seals = {}
    self.details_seal = None
    for j in jobs:
      b._bound(j)
      need(j['stage1'] is None, 'CANONICAL_TRAIN_STAGE1_PAYLOAD_NOT_AUTHORIZED')
      b.canonical.canonical_predict_delta(j['x'][:0], j['stage2'])

  def _check_proofs(self):
    for j in self.jobs:
      b._bound(j)
    if self.caches:
      need(len(self.caches) == 32, 'CANONICAL_CACHE_COMPLETENESS')
      for j, cache in zip(self.jobs, self.caches, strict=True):
        b._cache_bound(j, cache)
    for arm, digest in self.seals.items():
      need(b._hash([p[arm] for p in self.policies]) == digest, 'CANONICAL_FINAL_WINNER_BINDING_CONFLICT')
    if self.details_seal is not None:
      need(b._hash(self.details) == self.details_seal, 'CANONICAL_SELECTION_DETAILS_CONFLICT')

  def seal(self, arm):
    self.seals[arm] = b._hash([p[arm] for p in self.policies])
    self.details_seal = b._hash(self.details)

  def reconstruct_d0(self):
    self._check_proofs()
    rows = [b.reconstruct_d0(j['p'], j['y'], self.counters) for j in self.jobs]
    self.policies = [{'D0': (r['value'],)} for r in rows]
    self.details = [{'D0': r, 'guard_reference': b.REFERENCE} for r in rows]
    self.seal('D0')

  def cache_potentials(self):
    self._check_proofs()
    self.caches = [b.potential_cache(j, self.counters) for j in self.jobs]

  def qualify_q1(self):
    self._check_proofs()
    self.q1 = [
      b.qualify_selected(j, cache, b.apply_gate(j['p'], j['prior'], p['D0'], 'D0'), 'Q1', self.counters)
      for j, cache, p in zip(self.jobs, self.caches, self.policies, strict=True)
    ]
    need(len(self.q1) == 32, 'CANONICAL_Q1_COMPLETENESS')

  def select_d1(self):
    self._check_proofs()
    need(len(self.q1) == 32, 'CANONICAL_Q1_BEFORE_D1')
    for j, p, detail in zip(self.jobs, self.policies, self.details, strict=True):
      selected = b.d1.select_job(j['p'], j['y'], j['prior'], candidate=j['candidate'], fold=j['fold'], anchor=j['anchor'], role='TRAIN')
      detail['D1'] = selected['contexts']
      p['D1'] = tuple(selected['contexts'][name]['decision'] for name in b.d2.CONTEXTS)
      b.d2.count(self.counters, 'D1_context_decision_selection_calls', 0)
      b.d2.count(self.counters, 'D1_context_decision_selection_calls', 0)
    self.seal('D1')

  def select_d2(self):
    self._check_proofs()
    need(len(self.q1) == 32 and all('D1' in p for p in self.policies), 'CANONICAL_Q1_BEFORE_D2')
    for j, cache, p, detail in zip(self.jobs, self.caches, self.policies, self.details, strict=True):
      contexts = {}
      for state, name in enumerate(b.d2.CONTEXTS):
        mask = (j['prior'] != 0) == state
        contexts[name] = b.d2.select_context(
          j['p'][mask], j['y'][mask], j['current'][mask], j['target'][mask], cache['u'][mask], cache['move_tick'][mask], p['D0'][0], role='TRAIN'
        )
        b.d2.count(self.counters, 'D2_context_decision_selection_calls')
      detail['D2'] = contexts
      p['D2'] = tuple(contexts[name]['decision'] for name in b.d2.CONTEXTS)
    need(self.counters['D2_context_decision_selection_calls'] == 64, 'CANONICAL_ALL64_REQUIRED')
    self.seal('D2')

  def qualify_q3(self):
    self._check_proofs()
    need(self.counters.get('D2_context_decision_selection_calls') == 64, 'CANONICAL_ALL64_BEFORE_Q3')
    self.q3 = [
      b.qualify_selected(j, cache, b.apply_gate(j['p'], j['prior'], p['D2'], 'D2'), 'Q3', self.counters)
      for j, cache, p in zip(self.jobs, self.caches, self.policies, strict=True)
    ]
    need(len(self.q3) == 32, 'CANONICAL_Q3_COMPLETENESS')


class Run:
  def __init__(self, provider, store, binding):
    need(
      type(provider) is inputs.SyntheticProvider and binding['scope'] == 'SYNTHETIC_ONLY' and binding['private_authority'] is False,
      'CANONICAL_SYNTHETIC_PROVIDER_REQUIRED',
    )
    self.provider, self.store, self.binding = provider, store, binding
    self.phase = Phase.PREFLIGHT
    self.trace = [self.phase.value]
    self.train_digest = None
    self.train_record = None

  def advance(self, expected, completed, action):
    try:
      need(self.phase == expected, 'CANONICAL_GLOBAL_PHASE_BARRIER')
      action()
      self.phase = completed
      self.trace.append(completed.value)
    except Exception:
      self.phase = Phase.FAILED
      self.trace.append(self.phase.value)
      raise

  def train(self):
    try:
      need(self.phase == Phase.PREFLIGHT, 'CANONICAL_TERMINAL_NO_RETRY')
      self.pipeline = TrainPipeline(self.provider.train())
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
        validate_train(self.train_record, self.binding)
        self.train_digest = self.store.write('train.json', self.train_record)
        loaded = self.store.read('train.json', self.train_digest)
        validate_train(loaded, self.binding)
        need({k: v for k, v in loaded.items() if k != 'receipt_sha256'} == self.train_record, 'CANONICAL_TRAIN_READBACK_MISMATCH')

      self.advance(Phase.Q3, Phase.SEAL, seal_train)
    except Exception:
      self.phase = Phase.FAILED
      raise

  def evaluate(self, clauses):
    jobs = []

    def unlock():
      self.pipeline._check_proofs()
      loaded = self.store.read('train.json', self.train_digest)
      validate_train(loaded, self.binding)
      need(output.canonical({k: v for k, v in loaded.items() if k != 'receipt_sha256'}) == output.canonical(self.train_record), 'CANONICAL_CHANGED_TRAIN_SEAL')
      self.provider.unlock(self.train_digest)

    self.advance(Phase.SEAL, Phase.DEV, unlock)

    def compute():
      for i in range(32):
        data, paths, identity = self.provider.dev(i, self.train_digest)
        need(b._hash(data) == identity, 'CANONICAL_DEV_IDENTITY_CONFLICT')
        policies = {arm: tuple(self.train_record['jobs'][i]['decisions'][arm]) for arm in b.ARMS}
        result = evaluation.evaluate(data, paths, policies, clauses, self.pipeline.counters)
        train = self.pipeline.jobs[i]
        train_score = evaluation.e1.score_diagnostics(train['p'], train['y'], train['prior'])
        for arm in b.ARMS:
          result['arms'][arm]['train_dev_transfer'] = evaluation.e1.score_transfer(train_score, result['arms'][arm]['score_diagnostics'])
        jobs.append(result)

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
      'validation_domains': domain_receipt(jobs),
      'synthetic_counters': dict(self.pipeline.counters),
      'source_writes': 0,
      'private_reads': 0,
      'HOLDOUT': 'CLOSED',
      'vehicle_authority': 'NONE',
      'train_raw_sha256': self.train_digest,
    }


def run_synthetic(provider, path, binding):
  protocol, _ = public_check()
  need(binding == synthetic_binding(binding['head']), 'CANONICAL_CURRENT_BINDING_CONFLICT')
  with output.Store(path) as store:
    run = Run(provider, store, binding)
    try:
      run.train()
      result = run.evaluate(protocol['acceptance']['clauses'])
      digest = store.write('result.json', result)
      completion_digest = store.write(
        'complete.json', {'schema': 'CANONICAL_SYNTHETIC_COMPLETE_V1', 'binding': binding, 'result_raw_sha256': digest, 'train_raw_sha256': run.train_digest}
      )
      return {**result, 'completion_digest': completion_digest, 'synthetic_output_bytes': store.total}
    except Exception as exc:
      store.write(
        'abort.json', {'schema': 'CANONICAL_SYNTHETIC_ABORT_V1', 'binding': binding, 'phase': run.phase.value, 'reason': type(exc).__name__, 'private_reads': 0}
      )
      raise


def verify_synthetic(path, binding, completion_digest):
  # This branch intentionally does not call public_check, providers or math.
  with output.Store(path, create=False) as store:
    complete = store.read('complete.json', completion_digest)
    need(complete['binding'] == binding and complete['schema'] == 'CANONICAL_SYNTHETIC_COMPLETE_V1', 'CANONICAL_VERIFY_BINDING')
    train = store.read('train.json', complete['train_raw_sha256'])
    validate_train(train, binding)
    result = store.read('result.json', complete['result_raw_sha256'])
    validate_result(result, binding)
    need(
      result['binding'] == binding
      and result['train_raw_sha256'] == complete['train_raw_sha256']
      and result['coverage'] == {'D0': 32, 'D1': 64, 'D2': 64, 'Q1': 32, 'Q3': 32, 'DEV_jobs': 32},
      'CANONICAL_VERIFY_COMPLETENESS',
    )
    need(
      tuple((j['candidate_id'], j['fold']) for j in result['jobs']) == b.d1.JOBS
      and result['evidence_scope'] == 'SYNTHETIC_ONLY'
      and result['empirical_acceptance'] is False,
      'CANONICAL_VERIFY_RESULT_SCOPE',
    )
    need(
      result['selected_candidate'] is result['selected_policy'] is None and result['HOLDOUT'] == 'CLOSED' and result['vehicle_authority'] == 'NONE',
      'CANONICAL_VERIFY_AUTHORITY',
    )
  return {'source_rereads': 0, 'inference_calls': 0, 'scientific_recomputations': 0, 'source_writes': 0, 'status': 'VERIFIED_SYNTHETIC_ONLY'}


def domain_receipt(jobs):
  statuses = {
    1: 'VERIFIED_PUBLIC_SOURCE',
    2: 'EXECUTED_SYNTHETIC_ONLY',
    3: 'EXECUTED',
    4: 'EXECUTED',
    5: 'EXECUTED',
    6: 'EXECUTED',
    7: 'EXECUTED',
    8: 'EXECUTED',
    9: 'EXECUTED',
    10: 'EXECUTED',
    11: 'EXECUTED',
    12: 'EXECUTED_DESCRIPTIVE_SYNTHETIC_TRANSFER',
    13: 'VERIFIED_BOTH_FOLDS',
    14: 'NOT_IDENTIFIABLE',
    15: 'NOT_IDENTIFIABLE',
    16: 'VERIFIED_SYNTHETIC',
    17: 'EXECUTED',
    18: 'NOT_IDENTIFIABLE',
    19: 'NOT_IDENTIFIABLE',
    20: 'PENDING_ORCHESTRATOR_REPEAT_VERIFICATION',
    21: 'AUTHORITY_BLOCKED_CLOSED',
    22: 'AUTHORITY_BLOCKED_NONE',
  }
  need(len(jobs) == 32, 'CANONICAL_DOMAINS_COMPLETENESS')
  return [
    {'order': i, 'status': statuses[i], 'evidence_scope': 'SYNTHETIC_ONLY', 'empirical_pass': False, 'source_pointer': f'/validation_domains/{i - 1}'}
    for i in range(1, 23)
  ]


def validate_result(result, binding):
  need(
    result['schema'] == 'CANONICAL_SYNTHETIC_RESULT_V1'
    and result['binding'] == binding
    and result['trace'] == [p.value for p in Phase if p is not Phase.FAILED],
    'CANONICAL_RESULT_PHASE_CONFLICT',
  )
  need(result['validation_domains'] == domain_receipt(result['jobs']), 'CANONICAL_RESULT_DOMAIN_CONFLICT')
  ids = (
    'ONE_STEP_RMSE',
    'ONE_STEP_MAE',
    'ONE_STEP_P95',
    'ONE_STEP_EXACT_HIT',
    'ONE_STEP_WITHIN_ONE_TICK',
    'MOVE_RMSE',
    'MOVE_MAE',
    'MOVE_P95',
    *(f'{pop}_{h}_{metric}' for pop in ('OVERALL', 'PATH_MOVED') for h in b.HORIZONS for metric in ('RMSE', 'MAE', 'P95')),
  )
  for row, job in zip(result['jobs'], b.d1.JOBS, strict=True):
    need((row['candidate_id'], row['fold']) == job and set(row['arms']) == set(b.ARMS), 'CANONICAL_RESULT_ARM_CONFLICT')
    for arm in row['arms'].values():
      checks = arm['gate']['clauses']
      need(
        tuple(c['id'] for c in checks) == ids
        and all(type(c['pass']) is bool and type(c['evaluated']) is bool and (not c['pass'] or c['evaluated']) for c in checks),
        'CANONICAL_RESULT_CLAUSE_CONFLICT',
      )
      failed = [c['id'] for c in checks if not c['pass']]
      need(arm['gate']['failures'] == failed and arm['gate']['pass'] == (arm['status'] == 'EXECUTED_COMPLETE' and not failed), 'CANONICAL_RESULT_GATE_CONFLICT')
      need(set(map(int, arm['rollout'])) == set(b.HORIZONS), 'CANONICAL_RESULT_HORIZON_CONFLICT')
      pairs = [arm['one_step'], arm['true_move'], *(roll[group] for roll in arm['rollout'].values() for group in ('overall', 'path_moved'))]
      for pair in pairs:
        if pair is None:
          continue
        need(type(pair['count']) is int and pair['count'] >= 201 and pair['anchor_sha256'] == pair['comparator_anchor_sha256'], 'CANONICAL_STORED_PAIR_ANCHOR')
        need(re.fullmatch('[0-9a-f]{64}', pair['anchor_sha256']) is not None, 'CANONICAL_STORED_ANCHOR_FORMAT')
        for side in ('candidate', 'comparator'):
          need(
            all(type(v) is float and math.isfinite(v) and v >= 0 and (k not in ('exact_hit', 'within_one_tick') or v <= 1) for k, v in pair[side].items()),
            'CANONICAL_STORED_METRIC',
          )
      for i, check in enumerate(checks):
        if i < 5:
          pair = arm['one_step']
        elif i < 8:
          pair = arm['true_move']
        else:
          pop, h, _ = check['id'].rsplit('_', 2)
          pair = arm['rollout'][h]['overall' if pop == 'OVERALL' else 'path_moved']
        need(check['evaluated'] == (pair is not None), 'CANONICAL_STORED_SUPPORT_CONFLICT')


def public_projection(result):
  need(result.get('evidence_scope') == 'SYNTHETIC_ONLY' and result.get('private_reads') == 0, 'CANONICAL_PRIVATE_PUBLICATION_NOT_IMPLEMENTED')
  return {
    'evidence_scope': 'SYNTHETIC_ONLY',
    'coverage': result['coverage'],
    'empirical_acceptance': False,
    'private_execution_authorized': False,
    'vehicle_authority': 'NONE',
  }


def compare_repeats(first, second, first_complete, second_complete):
  need(first_complete is True and second_complete is True, 'CANONICAL_REPEAT_PARTIAL')
  need(type(first) is bytes and type(second) is bytes and first == second, 'CANONICAL_REPEATABILITY_FAILED')
  return 'BYTE_EXACT_SYNTHETIC_REPEATS'
