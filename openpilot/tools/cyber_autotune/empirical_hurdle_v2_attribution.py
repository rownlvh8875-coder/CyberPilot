"""Read-only residual attribution of successful immutable V1/V2 evidence."""

import argparse
from contextlib import contextmanager, ExitStack
import gzip
import json
from pathlib import Path
from unittest.mock import patch

import numpy as np
from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_hurdle_attribution_io as io
from openpilot.tools.cyber_autotune import empirical_hurdle_attribution_math as old
from openpilot.tools.cyber_autotune import empirical_hurdle_v2_attribution_math as a

BASELINE = '6176dbef998e7957f9ef1a605c081ced0857cb7b'
V2_SHA = '7d28c7d07c72a1080e6769165af8539f3568e14688b82f782d0d29aed8d84b9b'
V2_REPEAT = 'a6c3e3852d585d089b14ce36b853429afefeb1646aeb8d8008042c092ebe6aae'
SUCCESS = 'HURDLE_STAGE1_V2_FAILURE_ATTRIBUTION_V1_COMPLETE'
PREFIX = 'empirical-hurdle-stage1-v2-'
LABELS = (
  'failure-attribution-policy',
  'exact-hit-decomposition',
  'move-miss-decomposition',
  'score-ranking',
  'score-transfer',
  'decision-conservatism',
  'feasibility-slack',
  'fold-asymmetry',
  'rollout-attribution',
  'long-horizon-attribution',
  'mechanism-summary',
  'next-design-trigger',
  'failure-attribution-repeatability',
  'failure-attribution-readiness',
  'failure-attribution-validation',
)
ZERO = dict.fromkeys(
  (
    'model_refit_calls',
    'normalizer_refit_calls',
    'threshold_reselection_calls',
    'prediction_replay_calls',
    'rollout_regeneration_calls',
    'selection_calls',
    'raw_log_openings',
    'qlog_openings',
    'holdout_openings',
    'holdout_discovery',
    'source_write_count',
    'causal_derived_openings',
  ),
  0,
)
EXPECTED = dict(
  zip(
    ('ONE_STEP_RMSE', 'ONE_STEP_MAE', 'ONE_STEP_P95', 'ONE_STEP_EXACT_HIT', 'ONE_STEP_WITHIN_ONE_TICK', 'MOVE_RMSE', 'MOVE_MAE', 'MOVE_P95'),
    (1, 1, 0, 18, 10, 0, 0, 0),
    strict=True,
  )
)
for _name, _values in (
  ('OVERALL', ((1, 6, 0), (0, 0, 0), (0, 0, 1), (5, 5, 1))),
  ('PATH_MOVED', ((0, 4, 2), (0, 0, 1), (0, 0, 1), (5, 5, 0))),
):
  for _h, _counts in zip(io.HORIZONS, _values, strict=True):
    EXPECTED.update({f'{_name}_{_h}_{k}': v for k, v in zip(('RMSE', 'MAE', 'P95'), _counts, strict=True)})


def sources():
  paths = [Path(__file__), Path(a.__file__), Path(old.__file__), Path(io.__file__), Path(__file__).with_name('empirical_hurdle_v2_attribution_publication.py')]
  return {v.name: io.digest(v) for v in paths}


def policy():
  return p.seal(
    {
      'schema': 'HURDLE_STAGE1_V2_ATTRIBUTION_POLICY',
      'baseline': BASELINE,
      'v1_manifest_sha256': io.SOURCE_SHA,
      'v2_manifest_sha256': V2_SHA,
      'job_order': [list(j) for j in io.JOBS],
      'horizons': list(io.HORIZONS),
      'auc': 'SORTED_EXACT_SCORE_GROUPS_PYTHON_INT_2_CONCORDANT_PLUS_TIED_OVER_2PN',
      'rank_comparison': 'EXACT_INTEGER_FRACTIONS_NO_EPSILON',
      'reductions': 'CONTIGUOUS_FLOAT64_ORIGINAL_ROW_ORDER_NUMPY_LINEAR_P95',
      'extreme_move_suppression': 'DEVELOPMENT_MISSED_MOVE_RATE_STRICTLY_GREATER_THAN_0.95',
      'classifier_review_trigger': 'ANY_JOB_TRAIN_AUC_STRICTLY_ABOVE_HALF_AND_DEV_AUC_AT_OR_BELOW_HALF',
      'threshold_review_trigger': 'ALL_32_EXACT_HIT_IMPROVE_VS_V1_AND_NO_ADMISSIBLE_AND_ALL_32_EXTREME_SUPPRESSION',
      'stage2_review': 'NO_AUTOMATIC_TRIGGER_REPORT_SUPPORT_GE_201_LONG_HORIZON_REGRESSIONS',
      'small_support': 'NONEMPTY_BELOW_201_SMALL_SUPPORT_DESCRIPTIVE_ONLY; ZERO_EMPTY',
      'train_truth': 'EXACT_ANCHOR_MATCH_OPPOSITE_FOLD_V1_DEVELOPMENT_TRUTH_ONLY',
      'train_continuous_error': 'SAVED_SELECTED_AGGREGATES_ONLY_NO_PER_ROW_RECONSTRUCTION',
      'first_event': 'ONE_BASED_STEP_ZERO_MEANS_NONE',
      'output': 'D_ONLY_AGGREGATES_NO_ARRAY_DUPLICATION',
      'review_authority': 'DESIGN_REVIEW_ONLY',
      'redesign_authorized': False,
      'counterfactual_thresholds': False,
      'candidate_ranking': False,
      'counterfactual_admission': False,
      'expected_failure_counts': EXPECTED,
      'execution_calls': ZERO,
    }
  )


@contextmanager
def firewall():
  from openpilot.tools.cyber_autotune import empirical_hurdle_v2_execution as execution
  from openpilot.tools.cyber_autotune import empirical_hurdle_v2_threshold as threshold
  from openpilot.tools.cyber_autotune import empirical_hurdle_v2_io as replay

  with io.firewall(), ExitStack() as stack:
    for module, names in (
      (execution, ('run', '_execute_job', 'selection', 'train_report')),
      (threshold, ('sweep', 'canonical')),
      (replay, ('load_model', 'load_route', 'verify_inputs', 'metadata')),
    ):
      for name in names:
        stack.enter_context(patch.object(module, name, io.forbidden))
    yield


def require_jobs(jobs):
  io.require([(j['candidate_id'], j['fold']) for j in jobs] == list(io.JOBS), 'V2_ATTRIBUTION_JOB_SET_CONFLICT')


def counts(jobs):
  result = dict.fromkeys(EXPECTED, 0)
  for job in jobs:
    clauses = job['gate']['clauses']
    io.require({v['id'] for v in clauses} == set(EXPECTED) and len(clauses) == 32)
    for clause in clauses:
      io.require(clause['evaluated'])
      result[clause['id']] += not clause['pass']
  io.require(result == EXPECTED, 'V2_ATTRIBUTION_HISTORICAL_RECONCILIATION_FAILURE')
  return result


PUBLIC_PINS = {
  'empirical-hurdle-stage1-v2-candidate-gates.json': '154e73dae6961745f5b2071f1fd29599314b7da049c2d143b8a419d9e0844564',
  'empirical-hurdle-stage1-v2-job-manifest.json': '85b31a2b20a543ab4cf542982c085a6e36a9ebe95a7615ed4896288051ce56ae',
  'empirical-hurdle-stage1-v2-retrospective-execution-readiness.json': '00434b084fb2b0617a6e540281db406e620482a6a1453a39de16d53dbe0736ba',
}


def metadata(v1, v2):
  for name, sha in PUBLIC_PINS.items():
    io.read_json(p.PUBLIC / name, sha)
  first = io.read_json(v1 / 'repeat-1/manifest.json', io.SOURCE_SHA)
  second = io.read_json(v2 / 'repeat-1/manifest.json', V2_SHA)
  repeated = io.read_json(v2 / 'repeatability.json', V2_REPEAT)
  io.require(repeated['all_file_content_decoded_hashes_equal'] and repeated['run1_manifest_sha256'] == V2_SHA)
  one = io.read_json(v1 / 'repeat-1/results.json', first['results_sha256'])
  two = io.read_json(v2 / 'repeat-1/results.json', second['results_sha256'])
  require_jobs(one['jobs'])
  require_jobs(two['jobs'])
  counts(two['jobs'])
  public = io.read_json(p.PUBLIC / (PREFIX + 'candidate-gates.json'))
  io.require(public['failure_counts'] == EXPECTED)
  published_jobs = io.read_json(p.PUBLIC / (PREFIX + 'job-manifest.json'))
  io.require(published_jobs['private_manifest_sha256'] == V2_SHA)
  for j, historical, published in zip(two['jobs'], one['jobs'], published_jobs['jobs'], strict=True):
    io.require(j['status'] == historical['status'] == 'EXECUTED_COMPLETE' and not j['failures'])
    io.require(j['receipt_sha256'] == published['receipt_sha256'])
    io.require(j['train_anchor_sha256'] == historical['train_anchor_sha256'])
  io.require([sum(j['gate']['pass'] for j in two['jobs'] if j['fold'] == f) for f in ('FOLD_A', 'FOLD_B')] == [0, 14])
  selected = io.read_json(v2 / 'repeat-1/selection.json', second['selection_sha256'])
  io.require(selected['selected_candidate'] is None and selected['admissible_count'] == 0)
  return first, second, one['jobs'], two['jobs']


def snapshot(v1, v2, manifests):
  return [io.verify_files(root / 'repeat-1', m['files']) for root, m in zip((v1, v2), manifests, strict=True)]


def population(root, job, name, v2=False):
  local = root / 'repeat-1/candidates' / job['candidate_id'] / job['fold']
  manifest = io.read_json(root / 'repeat-1/manifest.json', V2_SHA if v2 else io.SOURCE_SHA)
  key = 'populations' if v2 else 'population_receipts'
  receipt = io.read_json(local / name / 'receipt.json', job[key][name])
  rel = (local / name / 'receipt.json').relative_to(root / 'repeat-1').as_posix()
  io.require(manifest['files'][rel] == io.digest(local / name / 'receipt.json'))
  required = {
    'train': ('predicted_gate', 'projected_next_tick') if v2 else ('actual_delta_tick',),
    'one-step': ('predicted_gate', 'projected_next_tick', 'integrated_delta', 'candidate_error', 'p_move')
    if v2
    else ('current_tick', 'target_next_tick', 'comparator_error', 'projected_next_tick', 'p_move'),
  }
  required_fields = required.get(
    name,
    ('projected_path', 'predicted_gate_path', 'candidate_error')
    if v2
    else ('observed_path', 'hold_last_path', 'projected_path', 'predicted_gate_path', 'comparator_error'),
  )
  io.require(set(required_fields) <= set(receipt['arrays']), 'HURDLE_ATTRIBUTION_INPUT_INSUFFICIENT')
  for b in receipt['arrays'].values():
    member = io.member(local / name, b['filename'])
    io.require(manifest['files'][member.relative_to(root / 'repeat-1').as_posix()] == b['file_sha256'])
  return local / name, receipt


def reference(v2_receipt, v1_receipt):
  ref = v2_receipt['source_reference']
  io.require(ref['manifest_sha256'] == io.SOURCE_SHA and ref['receipt_sha256'] == v1_receipt['receipt_sha256'])
  io.require(ref['arrays'] == v1_receipt['arrays'] and v2_receipt['anchor_sha256'] == v1_receipt['anchor_sha256'])


def reconcile(actual, expected):
  io.require(all(actual[k] == value for k, value in expected.items()), 'V2_ATTRIBUTION_HISTORICAL_RECONCILIATION_FAILURE')


def analyze_train(v1, v2, historical, job, opposite):
  tr, receipt = population(v2, job, 'train', True)
  prior, original = population(v1, historical, 'train')
  reference(receipt, original)
  truthroot, truthreceipt = population(v1, opposite, 'one-step')
  io.require(receipt['anchor_sha256'] == truthreceipt['anchor_sha256'] == job['train_anchor_sha256'])
  for k in ('anchor_index', 'anchor_order_index', 'anchor_route_id', 'anchor_segment_sha', 's2_ri_run_id', 'within_run_index'):
    io.require(original['arrays'][k]['array_sha256'] == truthreceipt['arrays'][k]['array_sha256'])
  current, target = (io.load_array(truthroot, truthreceipt, k) for k in ('current_tick', 'target_next_tick'))
  actual = io.load_array(prior, original, 'actual_delta_tick')
  io.require(np.array_equal(actual, target - current) and len(actual) == job['train_count'])
  thresholdroot = prior.parent / 'threshold'
  v1threshold = io.read_json(thresholdroot / 'receipt.json', historical['threshold']['receipt_sha256'])
  probability = io.load_array(thresholdroot, v1threshold, 'train_probability')
  from openpilot.tools.cyber_autotune.empirical_hurdle_fit_cv_store import array_digest

  io.require(array_digest(probability) == receipt['probability_sha256'] == job['threshold']['probability_sha256'])
  gate, projected = (io.load_array(tr, receipt, k) for k in ('predicted_gate', 'projected_next_tick'))
  selected = io.read_json(tr.parent / 'threshold/receipt.json', receipt['threshold_sha256'])
  io.require(selected['probability_sha256'] == receipt['probability_sha256'] and selected['train_anchor_sha256'] == job['train_anchor_sha256'])
  io.require(np.array_equal(probability > selected['threshold'], gate))  # Only validate the already stored decision.
  move = actual != 0
  decision = a.decisions(move, gate, projected != current)
  reconcile(decision['counts'], {k: job['train_metrics']['stage1'][k] for k in ('TN', 'FP', 'FN', 'TP')})
  hit = a.hit_counts(current, target, projected)
  objective = job['threshold']['objective']
  io.require(hit['candidate_exact_hit_count'] == objective['exact_hit_count'] and hit['static_hit_loss'] == objective['static_projected_false_move_count'])
  within = a.count(np.abs(projected.astype(np.int64) - target) <= 1)
  io.require(within == objective['within_one_tick_count'])
  comparator_all, comparator_move = old.metrics(-actual), old.metrics(-actual[move])
  saved = job['train_metrics']
  slack = {f'move_{k}_slack': comparator_move[k] - saved['true_move'][k] for k in ('rmse', 'mae', 'p95')}
  slack['all_rmse_improvement'] = comparator_all['rmse'] - saved['all']['rmse']
  io.require(all(slack[k] >= 0 for k in slack if k != 'all_rmse_improvement') and slack['all_rmse_improvement'] > 0)
  return {
    'ranking': a.ranking(probability, move),
    'decision': decision,
    'exact_hit': hit,
    'feasibility_slack': slack,
    'selected_objective': {
      'predicted_move_count': a.count(gate),
      'projected_move_count': a.count(projected != current),
      'exact_move_hit_count': hit['move_hit_gain'],
      'static_projected_false_move_count': hit['static_hit_loss'],
      'exact_hit_count': hit['candidate_exact_hit_count'],
      'within_one_tick_count': within,
    },
    'lineage': {
      'anchor_sha256': receipt['anchor_sha256'],
      'truth_receipt_sha256': truthreceipt['receipt_sha256'],
      'probability_sha256': receipt['probability_sha256'],
      'threshold_receipt_sha256': receipt['threshold_sha256'],
    },
    'continuous_train_metrics': 'SAVED_SELECTED_AGGREGATES_ONLY',
  }, selected['threshold']


def analyze_one(v1, v2, historical, job, selected):
  original_root, original = population(v1, historical, 'one-step')
  root, receipt = population(v2, job, 'one-step', True)
  reference(receipt, original)
  current, target, hold, v1projected = (
    io.load_array(original_root, original, k) for k in ('current_tick', 'target_next_tick', 'comparator_error', 'projected_next_tick')
  )
  gate, projected, delta, error, probability = (
    io.load_array(root, receipt, k) for k in ('predicted_gate', 'projected_next_tick', 'integrated_delta', 'candidate_error', 'p_move')
  )
  io.require(np.array_equal(probability > selected, gate))
  v1probability = io.load_array(original_root, original, 'p_move')
  io.require(probability.dtype == v1probability.dtype and probability.tobytes() == v1probability.tobytes())
  result = a.one_step(current, target, gate, projected, delta, error, hold)
  for label, historical_key in (('ALL', 'one_step'), ('MOVE', 'true_move')):
    for side, prior in (('candidate', 'candidate'), ('hold_last', 'comparator')):
      reconcile(result['classes'][label][side], job[historical_key][prior])
  reconcile(result['confusion']['counts'], {k: job['stage1_diagnostics'][k] for k in ('TN', 'FP', 'FN', 'TP')})
  v1hits = a.hit_counts(current, target, v1projected)
  result['v1_exact_hit'] = v1hits
  result['v1_to_v2'] = {k: result['exact_hit'][k] - v1hits[k] for k in ('static_hit_loss', 'move_hit_gain', 'net_hit_delta', 'candidate_exact_hit_count')}
  result['ranking'] = a.ranking(probability, target != current)
  return result


def analyze_path(v1, v2, historical, job, horizon):
  name = f'rollout-{horizon}'
  original_root, original = population(v1, historical, name)
  root, receipt = population(v2, job, name, True)
  reference(receipt, original)
  readers = []
  for local, rec, key in (
    (original_root, original, 'observed_path'),
    (original_root, original, 'hold_last_path'),
    (original_root, original, 'projected_path'),
    (original_root, original, 'predicted_gate_path'),
    (root, receipt, 'projected_path'),
    (root, receipt, 'predicted_gate_path'),
  ):
    io.require(key in rec['arrays'], 'HURDLE_ATTRIBUTION_INPUT_INSUFFICIENT')
    binding = rec['arrays'][key]
    readers.append(io.array_chunks(io.member(local, binding['filename']), binding))
  error, hold = io.load_array(root, receipt, 'candidate_error'), io.load_array(original_root, original, 'comparator_error')
  collected, v1counts, start = {}, {'predicted_move_count': 0, 'projected_move_count': 0, 'hold_last_identical_count': 0}, 0
  for observed, baseline, projected1, gate1, projected2, gate2 in zip(*readers, strict=True):
    end = start + len(observed)
    io.require(np.all(baseline == observed[:, :1]))
    io.require((projected2[:, -1].astype(np.int64) - observed[:, -1]).astype(float).tobytes() == error[start:end].tobytes())
    io.require((baseline[:, -1] - observed[:, -1]).astype(float).tobytes() == hold[start:end].tobytes())
    rows = a.path_rows(observed, projected2, gate2)
    for k, values in rows.items():
      collected.setdefault(k, []).append(values)
    v1counts['predicted_move_count'] += a.count(gate1)
    v1counts['projected_move_count'] += a.count(np.diff(projected1, axis=1) != 0)
    v1counts['hold_last_identical_count'] += a.count(np.all(projected1 == baseline, axis=1))
    start = end
  io.require(start == len(error) == job['rollout'][str(horizon)]['overall']['count'])
  rows = {k: np.concatenate(v) for k, v in collected.items()}
  result = a.rollout(rows, error, hold)
  for label, previous in (('ALL', 'overall'), ('PATH_MOVED', 'path_moved')):
    for side, prior in (('candidate', 'candidate'), ('hold_last', 'comparator')):
      reconcile(result['classes'][label][side], job['rollout'][str(horizon)][previous][prior])
  v1counts['hold_last_identical_fraction'] = v1counts['hold_last_identical_count'] / len(error)
  result['v1_event_comparison'] = {
    'authority': 'REPORT_ONLY',
    'v1': v1counts,
    'v2': {
      **result['event_totals'],
      'hold_last_identical_count': result['hold_last_identical_count'],
      'hold_last_identical_fraction': result['hold_last_identical_fraction'],
    },
  }
  return result


def summarize(jobs):
  require_jobs(jobs)
  folds = {}
  for fold in ('FOLD_A', 'FOLD_B'):
    subset = [j for j in jobs if j['fold'] == fold]
    value = {
      'jobs': 16,
      'exact_hit_fail_count': sum(j['one']['exact_hit']['net_hit_delta'] < 0 for j in subset),
      'within_one_tick_fail_count': sum(not j['historical_clauses']['ONE_STEP_WITHIN_ONE_TICK'] for j in subset),
      'complete_gate_pass_count': sum(j['historical_gate_pass'] for j in subset),
      'rank_transfer_counts': {
        s: sum(j['ranking_transfer']['transfer_state'] == s for j in subset)
        for s in ('RANK_TRANSFER_INCREASED', 'RANK_TRANSFER_EQUAL', 'RANK_TRANSFER_DECREASED')
      },
    }
    extract = {
      'train_auc': lambda j: j['train']['ranking']['auc'],
      'dev_auc': lambda j: j['one']['ranking']['auc'],
      'train_brier': lambda j: j['train']['ranking']['brier'],
      'dev_brier': lambda j: j['one']['ranking']['brier'],
      'missed_move_rate': lambda j: j['one']['confusion']['missed_move_rate'],
      'predicted_move_fraction': lambda j: j['one']['confusion']['predicted_move_fraction'],
    }
    extract.update(
      {k: (lambda j, key=k: j['one']['exact_hit'][key]) for k in ('move_hit_gain', 'static_hit_loss', 'exact_hit_deficit_count', 'exact_hit_surplus_count')}
    )
    value['ranges'] = {k: {'min': min(fn(j) for j in subset), 'max': max(fn(j) for j in subset)} for k, fn in extract.items()}
    folds[fold] = value
  rank_count = sum(j['ranking_transfer']['rank_state'] == 'RANK_ABOVE_CHANCE' for j in jobs)
  reduced = sum(j['ranking_transfer']['transfer_state'] == 'RANK_TRANSFER_DECREASED' for j in jobs)
  suppressed = sum(j['one']['confusion']['extreme_move_suppression'] for j in jobs)
  improved = sum(j['one']['v1_to_v2']['candidate_exact_hit_count'] > 0 for j in jobs)
  classifier = sum(j['ranking_transfer']['classifier_review_evidence'] for j in jobs)
  sufficient_support = {str(h): sum(j['rollout'][str(h)]['classes']['GATE_PERFECT_PATH_MOVED']['count'] >= 201 for j in jobs) for h in (50, 100, 200)}
  long_support = {
    str(h): sum(
      j['rollout'][str(h)]['classes']['GATE_PERFECT_PATH_MOVED']['count'] >= 201 and j['rollout'][str(h)]['classes']['GATE_PERFECT_PATH_MOVED']['delta_sse'] > 0
      for j in jobs
    )
    for h in (50, 100, 200)
  }
  return p.seal(
    {
      'schema': 'HURDLE_STAGE1_V2_ATTRIBUTION_SUMMARY',
      'folds': folds,
      'rank_above_chance_jobs': rank_count,
      'rank_transfer_decreased_jobs': reduced,
      'extreme_move_suppression_jobs': suppressed,
      'exact_hit_improved_jobs': improved,
      'rank_state': 'STAGE1_DEV_RANK_ABOVE_CHANCE_ALL_JOBS' if rank_count == 32 else 'STAGE1_DEV_RANK_NOT_ABOVE_CHANCE_ALL_JOBS',
      'rank_transfer_state': 'STAGE1_RANK_TRANSFER_DECREASED_ALL_JOBS' if reduced == 32 else 'MIXED',
      'decision_state': 'V2_EXTREME_MOVE_SUPPRESSION_ALL_JOBS' if suppressed == 32 else 'V2_EXTREME_MOVE_SUPPRESSION_MIXED',
      'threshold_review': 'THRESHOLD_POLICY_REDESIGN_REVIEW_SUPPORTED' if improved == suppressed == 32 else 'NOT_FULLY_SUPPORTED',
      'classifier_review': 'STAGE1_CLASSIFIER_REDESIGN_REVIEW_SUPPORTED' if classifier else 'PREDECLARED_RANK_COLLAPSE_CONDITION_NOT_MET',
      'classifier_review_evidence_jobs': classifier,
      'supported_gate_perfect_long_regression_jobs': long_support,
      'sufficient_gate_perfect_support_jobs': sufficient_support,
      'stage2_review': 'SUFFICIENT_GATE_PERFECT_REGRESSION_EVIDENCE_REQUIRES_SEPARATE_REVIEW'
      if any(long_support.values())
      else ('SUFFICIENT_SUPPORT_NO_REGRESSION' if any(sufficient_support.values()) else 'INSUFFICIENT_GATE_PERFECT_SUPPORT'),
      'stage2_redesign_authorized': False,
      'redesign_authorized': False,
      'review_authority': 'DESIGN_REVIEW_ONLY',
      'historical_selection': 'HURDLE_STAGE1_V2_NO_ADMISSIBLE_CANDIDATE',
      'selected_candidate': None,
    }
  )


def readiness(summary):
  original = io.read_json(p.PUBLIC / (PREFIX + 'retrospective-execution-readiness.json'))
  return p.seal(
    {
      'schema': 'HURDLE_STAGE1_V2_ATTRIBUTION_READINESS',
      'status': SUCCESS,
      'states': [
        'READ_ONLY_ATTRIBUTION_COMPLETE',
        'NO_MODEL_REFIT',
        'NO_NORMALIZER_REFIT',
        'NO_THRESHOLD_RESELECTION',
        'NO_MODEL_REPLAY',
        'NO_ROLLOUT_REGENERATION',
        'NO_MODEL_SELECTION',
        'NO_POLICY_CHANGE',
        'HURDLE_STAGE1_V2_NO_ADMISSIBLE_CANDIDATE_PRESERVED',
        'MODEL_SELECTION_FAILED_CLOSED',
      ],
      'execution_calls': ZERO,
      'summary_sha256': summary['receipt_sha256'],
      'preserved_authority': original['preserved_authority'],
      'historical_v1': original['historical_v1'],
      'holdout': 'CLOSED',
      'opening_count': 0,
      'vehicle_authority': 'NONE',
      'next_execution_authorized': False,
    }
  )


def authorize(v1, v2, output):
  import shutil

  io.output_root(output, v1)
  io.output_root(output, v2)
  io.require(shutil.disk_usage('/mnt/d').free >= 128 * 1024**2, 'ATTRIBUTION_AGGREGATE_STORAGE_CAPACITY_REQUIRED')
  first, second, _, _ = metadata(v1, v2)
  value = p.seal(
    {
      'schema': 'HURDLE_STAGE1_V2_ATTRIBUTION_AUTHORIZATION',
      'policy_sha256': policy()['receipt_sha256'],
      'v1_manifest_sha256': first['receipt_sha256'],
      'v2_manifest_sha256': second['receipt_sha256'],
      'source_root_identities': [p.sha(str(io.safe(r)).encode()) for r in (v1, v2)],
      'output_identity': p.sha(str(io.safe(output)).encode()),
      'executor_sources': sources(),
      'execution_calls': ZERO,
    }
  )
  io.write_json(output / 'policy.json', policy())
  io.write_json(output / 'authorization.json', value)
  return value


def run(v1, v2, output, replica):
  io.require(replica in ('repeat-1', 'repeat-2'))
  auth = io.read_json(output / 'authorization.json')
  io.require(auth['executor_sources'] == sources() and auth['policy_sha256'] == policy()['receipt_sha256'])
  io.require(
    auth['source_root_identities'] == [p.sha(str(io.safe(r)).encode()) for r in (v1, v2)] and auth['output_identity'] == p.sha(str(io.safe(output)).encode())
  )
  root = output / replica
  io.require(not root.exists(), 'ATTRIBUTION_NO_PARTIAL_REUSE')
  with firewall():
    m1, m2, originals, saved = metadata(v1, v2)
    before = snapshot(v1, v2, (m1, m2))
    jobs = []
    for i, (historical, current) in enumerate(zip(originals, saved, strict=True)):
      train, selected = analyze_train(v1, v2, historical, current, originals[i ^ 1])
      one = analyze_one(v1, v2, historical, current, selected)
      io.require((one['exact_hit']['net_hit_delta'] >= 0) == next(c['pass'] for c in current['gate']['clauses'] if c['id'] == 'ONE_STEP_EXACT_HIT'))
      job = p.seal(
        {
          'schema': 'HURDLE_STAGE1_V2_ATTRIBUTION_JOB',
          'candidate_id': current['candidate_id'],
          'fold': current['fold'],
          'authorization_sha256': auth['receipt_sha256'],
          'v1_job_sha256': historical['receipt_sha256'],
          'v2_job_sha256': current['receipt_sha256'],
          'train': train,
          'one': one,
          'ranking_transfer': a.transfer(train['ranking'], one['ranking']),
          'rollout': {str(h): analyze_path(v1, v2, historical, current, h) for h in io.HORIZONS},
          'historical_gate_pass': current['gate']['pass'],
          'historical_clauses': {c['id']: c['pass'] for c in current['gate']['clauses']},
        }
      )
      io.write_json(root / f'jobs/{current["candidate_id"]}/{current["fold"]}/receipt.json', job)
      jobs.append(job)
      print(json.dumps({'candidate': job['candidate_id'], 'fold': job['fold'], 'complete': len(jobs)}), flush=True)
    summary = summarize(jobs)
    io.require(summary['exact_hit_improved_jobs'] == 32, 'V2_ATTRIBUTION_HISTORICAL_RECONCILIATION_FAILURE')
    ready = readiness(summary)
    io.write_json(root / 'summary.json', summary)
    io.write_json(root / 'readiness.json', ready)
    io.require(before == snapshot(v1, v2, (m1, m2)), 'ATTRIBUTION_SOURCE_MUTATION')
    names = [f'jobs/{c}/{f}/receipt.json' for c, f in io.JOBS] + ['summary.json', 'readiness.json']
    return io.finish(
      root,
      names,
      {
        'schema': 'HURDLE_STAGE1_V2_ATTRIBUTION_MANIFEST',
        'status': SUCCESS,
        'authorization_sha256': auth['receipt_sha256'],
        'source_hashes': before,
        'policy_sha256': policy()['receipt_sha256'],
        'v1_manifest_sha256': io.SOURCE_SHA,
        'v2_manifest_sha256': V2_SHA,
        'job_order': [list(j) for j in io.JOBS],
        'summary_sha256': summary['receipt_sha256'],
        'readiness_sha256': ready['receipt_sha256'],
        'source_bytes_unchanged': True,
      },
    )


def validate_job(job):
  from openpilot.tools.cyber_autotune import empirical_hurdle_attribution_schema as schema

  fields = schema.fields
  fields(
    job,
    (
      'schema',
      'candidate_id',
      'fold',
      'authorization_sha256',
      'v1_job_sha256',
      'v2_job_sha256',
      'train',
      'one',
      'ranking_transfer',
      'rollout',
      'historical_gate_pass',
      'historical_clauses',
    ),
  )
  io.require(job['schema'] == 'HURDLE_STAGE1_V2_ATTRIBUTION_JOB')
  for key in ('authorization_sha256', 'v1_job_sha256', 'v2_job_sha256'):
    schema.sha(job[key])
  fields(job['train'], ('ranking', 'decision', 'exact_hit', 'feasibility_slack', 'selected_objective', 'lineage', 'continuous_train_metrics'))
  fields(job['one'], ('ranking', 'confusion', 'exact_hit', 'v1_exact_hit', 'v1_to_v2', 'move', 'fn', 'tp', 'within', 'classes', 'sae_sse_partition'))
  for rank in (job['train']['ranking'], job['one']['ranking']):
    fields(
      rank,
      (
        'count',
        'positive_count',
        'negative_count',
        'auc_num2',
        'auc_den2',
        'auc',
        'brier',
        'true_move_prevalence',
        'mean_probability',
        'calibration_bias',
        'static_score_mean',
        'move_score_mean',
        'score_mean_gap',
      ),
    )
    io.require(rank['count'] == rank['positive_count'] + rank['negative_count'] and rank['positive_count'] > 0 and rank['negative_count'] > 0)
    io.require(type(rank['auc_num2']) is int and 0 <= rank['auc_num2'] <= rank['auc_den2'] == 2 * rank['positive_count'] * rank['negative_count'])
    io.require(rank['auc'] == rank['auc_num2'] / rank['auc_den2'])
  fields(job['ranking_transfer'], ('train', 'development', 'dev_minus_train_auc', 'rank_state', 'transfer_state', 'classifier_review_evidence'))
  io.require(job['ranking_transfer']['train'] == job['train']['ranking'] and job['ranking_transfer']['development'] == job['one']['ranking'])
  for hit in (job['train']['exact_hit'], job['one']['exact_hit'], job['one']['v1_exact_hit']):
    fields(
      hit,
      (
        'static_hit_loss',
        'move_hit_gain',
        'net_hit_delta',
        'candidate_exact_hit_count',
        'hold_exact_hit_count',
        'exact_hit_deficit_count',
        'exact_hit_surplus_count',
        'integer_identity_exact',
      ),
    )
    io.require(hit['net_hit_delta'] == hit['move_hit_gain'] - hit['static_hit_loss'] == hit['candidate_exact_hit_count'] - hit['hold_exact_hit_count'])
    io.require(hit['exact_hit_deficit_count'] == max(-hit['net_hit_delta'], 0) and hit['exact_hit_surplus_count'] == max(hit['net_hit_delta'], 0))
  for decision in (job['train']['decision'], job['one']['confusion']):
    schema.confusion(decision, decision['count'])
    fields(decision, ('move_coverage_ratio', 'projected_move_fraction', 'extreme_move_suppression'))
    io.require(decision['extreme_move_suppression'] == (decision['missed_move_rate'] > 0.95))
  for item in job['one']['classes'].values():
    schema.pair(item, grid=True)
  io.require(set(job['one']['classes']) == {'ALL', 'STATIC', 'MOVE'})
  fields(job['one']['fn'], ('count', 'one_tick_fraction', 'multi_tick_fraction', 'hold_identity_exact', 'metrics'))
  fields(job['one']['tp'], ('count', 'exact_count', 'exact_rate', 'within_one_tick_rate', 'sign_accuracy', 'metrics'))
  io.require(job['one']['fn']['hold_identity_exact'])
  schema.pair(job['one']['tp']['metrics'], grid=True)
  io.require(set(job['historical_clauses']) == set(EXPECTED) and all(type(v) is bool for v in job['historical_clauses'].values()))
  io.require(job['historical_gate_pass'] == all(job['historical_clauses'].values()))
  io.require(set(job['rollout']) == {str(h) for h in io.HORIZONS})
  for h, result in job['rollout'].items():
    fields(result, ('hold_last_identical_count', 'hold_last_identical_fraction', 'first_departure_from_hold_last', 'event_totals', 'v1_event_comparison'))
    base = dict(
      result,
      classes={k: result['classes'][k] for k in schema.PATH_CLASSES},
      count_distributions={k: result['count_distributions'][k] for k in ('gate_fp_count', 'gate_fn_count', 'projected_move_count', 'observed_move_count')},
      historical_metric_reconciliation='EXACT',
    )
    schema.rollout(base, int(h))
    for name in ('NO_PREDICTED_MOVE', 'ANY_PREDICTED_MOVE', 'PATH_MOVED_NO_PREDICTED_MOVE', 'PATH_MOVED_ANY_PREDICTED_MOVE'):
      schema.pair(result['classes'][name])
    io.require(result['hold_last_identical_fraction'] == result['hold_last_identical_count'] / result['count'])
    schema.event(result['first_departure_from_hold_last'], result['count'])
  # Fail closed on arbitrary nonfinite aggregate leaves and private payload fields.
  from openpilot.tools.cyber_autotune.empirical_hurdle_v2_publication import privacy

  privacy(job)
  json.dumps(job, allow_nan=False)


def validate_summary(value):
  from openpilot.tools.cyber_autotune.empirical_hurdle_attribution_schema import fields

  fields(
    value,
    (
      'schema',
      'folds',
      'rank_above_chance_jobs',
      'rank_transfer_decreased_jobs',
      'extreme_move_suppression_jobs',
      'exact_hit_improved_jobs',
      'rank_state',
      'rank_transfer_state',
      'decision_state',
      'threshold_review',
      'classifier_review',
      'classifier_review_evidence_jobs',
      'supported_gate_perfect_long_regression_jobs',
      'sufficient_gate_perfect_support_jobs',
      'stage2_review',
      'redesign_authorized',
      'historical_selection',
      'selected_candidate',
    ),
  )
  fields(value, ('stage2_redesign_authorized', 'review_authority'))
  io.require(value['stage2_redesign_authorized'] is False and value['review_authority'] == 'DESIGN_REVIEW_ONLY')
  io.require(value['historical_selection'] == 'HURDLE_STAGE1_V2_NO_ADMISSIBLE_CANDIDATE')
  io.require(set(value['folds']) == {'FOLD_A', 'FOLD_B'} and not value['redesign_authorized'] and value['selected_candidate'] is None)
  for fold in value['folds'].values():
    fields(fold, ('jobs', 'exact_hit_fail_count', 'within_one_tick_fail_count', 'complete_gate_pass_count', 'rank_transfer_counts', 'ranges'))
    io.require(fold['jobs'] == 16 and sum(fold['rank_transfer_counts'].values()) == 16)


def resume(root):
  manifest = io.read_json(root / 'manifest.json')
  auth = io.read_json(root.parent / 'authorization.json', manifest['authorization_sha256'])
  io.require(auth['executor_sources'] == sources() and auth['output_identity'] == p.sha(str(io.safe(root.parent)).encode()))
  io.require(manifest['status'] == SUCCESS and manifest['schema'] == 'HURDLE_STAGE1_V2_ATTRIBUTION_MANIFEST')
  io.require(manifest['v1_manifest_sha256'] == io.SOURCE_SHA and manifest['v2_manifest_sha256'] == V2_SHA)
  io.require(manifest['policy_sha256'] == auth['policy_sha256'] == policy()['receipt_sha256'])
  io.read_json(root.parent / 'policy.json', manifest['policy_sha256'])
  expected = {f'jobs/{c}/{f}/receipt.json' for c, f in io.JOBS} | {'summary.json', 'readiness.json'}
  io.require(set(manifest['files']) == expected and manifest['job_order'] == [list(j) for j in io.JOBS])
  io.verify_files(root, manifest['files'])
  jobs = [io.read_json(root / f'jobs/{c}/{f}/receipt.json') for c, f in io.JOBS]
  require_jobs(jobs)
  for job in jobs:
    validate_job(job)
  io.require(all(j['authorization_sha256'] == auth['receipt_sha256'] for j in jobs))
  summary = io.read_json(root / 'summary.json', manifest['summary_sha256'])
  ready = io.read_json(root / 'readiness.json', manifest['readiness_sha256'])
  validate_summary(summary)
  io.require(ready == readiness(summary), 'ATTRIBUTION_READINESS_CONFLICT')
  io.require(ready['status'] == SUCCESS and ready['summary_sha256'] == summary['receipt_sha256'] and ready['execution_calls'] == ZERO)
  return manifest


def trapped_resume(root):
  import sys

  with firewall(), ExitStack() as stack:
    for module, names in (
      (sys.modules[__name__], ('metadata', 'snapshot', 'analyze_train', 'analyze_one', 'analyze_path', 'summarize')),
      (io, ('load_array', 'array_chunks')),
      (gzip, ('open',)),
      (a, ('ranking', 'one_step', 'rollout', 'path_rows', 'transfer')),
    ):
      for name in names:
        stack.enter_context(patch.object(module, name, io.forbidden))
    return resume(root)


def verify(output):
  first, second = (trapped_resume(output / r) for r in ('repeat-1', 'repeat-2'))
  io.require(first == second, 'V2_ATTRIBUTION_REPEATABILITY_FAILURE')
  value = p.seal(
    {
      'schema': 'HURDLE_STAGE1_V2_ATTRIBUTION_REPEATABILITY',
      'status': 'BYTE_EXACT_PASS',
      'run1_manifest_sha256': first['receipt_sha256'],
      'run2_manifest_sha256': second['receipt_sha256'],
      'file_count': len(first['files']),
      'resume': 'VERIFY_ONLY_RESUME_PASS',
      'execution_calls': ZERO,
    }
  )
  io.write_json(output / 'repeatability.json', value)
  return value


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--v1', type=Path)
  parser.add_argument('--v2', type=Path)
  parser.add_argument('--output', type=Path, required=True)
  parser.add_argument('--action', choices=('authorize', 'repeat-1', 'repeat-2', 'verify'), required=True)
  args = parser.parse_args()
  if args.action == 'verify':
    value = verify(args.output)
  elif args.action == 'authorize':
    value = authorize(args.v1, args.v2, args.output)
  else:
    value = run(args.v1, args.v2, args.output, args.action)
  print(json.dumps({'receipt_sha256': value['receipt_sha256'], 'status': value.get('status', 'AUTHORIZED')}))


if __name__ == '__main__':
  main()
