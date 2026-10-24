"""Read-only Hurdle failure attribution CLI. Never executes a fitted model."""

import argparse
from contextlib import ExitStack
import gzip
import os
from pathlib import Path
import platform
from unittest.mock import patch

import numpy as np
from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_hurdle_attribution_io as io
from openpilot.tools.cyber_autotune import empirical_hurdle_attribution_math as a

SUCCESS = 'HURDLE_FAILURE_ATTRIBUTION_V1_COMPLETE'
EXPECTED_FAILURES = dict(
  zip(
    ('ONE_STEP_RMSE', 'ONE_STEP_MAE', 'ONE_STEP_P95', 'ONE_STEP_EXACT_HIT', 'ONE_STEP_WITHIN_ONE_TICK', 'MOVE_RMSE', 'MOVE_MAE', 'MOVE_P95'),
    (4, 20, 16, 32, 8, 0, 0, 0),
    strict=True,
  )
)
for _h, _overall, _moved in (
  (25, (15, 23, 21), (14, 23, 21)),
  (50, (16, 22, 24), (16, 22, 23)),
  (100, (20, 23, 25), (19, 23, 25)),
  (200, (21, 22, 18), (21, 22, 17)),
):
  for _label, _counts in (('OVERALL', _overall), ('PATH_MOVED', _moved)):
    EXPECTED_FAILURES.update({f'{_label}_{_h}_{m}': v for m, v in zip(('RMSE', 'MAE', 'P95'), _counts, strict=True)})

ZERO_CALLS = dict.fromkeys(
  (
    'model_refit_calls',
    'normalizer_refit_calls',
    'threshold_reselection_calls',
    'model_replay_calls',
    'selection_calls',
    'raw_log_openings',
    'qlog_openings',
    'holdout_openings',
    'causal_source_openings',
  ),
  0,
)
CONTEXT = (
  'anchor_index',
  'anchor_order_index',
  'anchor_route_id',
  'anchor_segment_sha',
  'speed_mps',
  'speed_bin_code',
  'rail',
  'prior_delta_tick',
  's2_ri_run_id',
  'within_run_index',
  'model_eligible',
  'command_current',
  'command_feature_newest',
  'command_history',
)
ONE_FIELDS = (
  'current_tick',
  'target_next_tick',
  'actual_delta_tick',
  'p_move',
  'predicted_gate',
  'integrated_delta',
  'projected_next_tick',
  'candidate_error',
  'comparator_error',
  'true_move',
  'hold_last_next_tick',
  'stage2_oracle_move_prediction',
)
PATH_FIELDS = (
  'initial_tick',
  'target_endpoint_tick',
  'observed_path',
  'projected_path',
  'hold_last_path',
  'predicted_gate_path',
  'candidate_error',
  'comparator_error',
  'path_moved',
)


def policy():
  return p.seal(
    {
      'schema': 'EMPIRICAL_HURDLE_FAILURE_ATTRIBUTION_POLICY_V1',
      'baseline': io.BASELINE,
      'source_manifest_sha256': io.SOURCE_SHA,
      'source_repeatability_sha256': io.REPEAT_SHA,
      'public_input_receipts': io.PUBLIC_PINS,
      'job_order': [list(j) for j in io.JOBS],
      'purpose': 'PURE_READ_ONLY_FAILURE_ATTRIBUTION',
      'chunk_rows': a.CHUNK,
      'metrics': 'CONTIGUOUS_FLOAT64_ORIGINAL_ANCHOR_ORDER_NUMPY_MEAN_SUM_LINEAR_P95',
      'canonical_one_step_error': 'STORED_INTEGRATED_DELTA_MINUS_ACTUAL_DELTA',
      'partition_reconciliation': 'EXACT_ROW_CONTRIBUTIONS_WITH_REDUCTION_ORDER_RESIDUAL_NO_TOLERANCE_GATE',
      'empty_subset': 'NULL_METRICS',
      'small_subset': 'NONEMPTY_BELOW_201_DESCRIPTIVE_ONLY_MARKED',
      'oracle': 'STORED_DELTA_CONTINUOUS_DIAGNOSTIC_AND_HISTORICAL_GRID_METRICS_NO_REPROJECTION',
      'first_event': 'ONE_BASED_STEP_ZERO_MEANS_NO_EVENT',
      'horizons': list(io.HORIZONS),
      'path_truth': 'STORED_OBSERVED_ADJACENT_TICKS_DIFFER',
      'gate_perfect': 'ALL_STORED_GATE_STEPS_EQUAL_TRUE_STEPS',
      'exact_hit_state': 'ALL_32_STATIC_HIT_LOSS_GT_MOVE_HIT_GAIN_AND_HISTORICAL_EXACT_HIT_FAIL',
      'stage1_review_trigger': 'ALL_32_TRUE_MOVE_PASS_AND_EXACT_HIT_FAIL_AND_STATIC_LOSS_GT_GAIN_AND_STATIC_PROJECTED_FALSE_MOVE',
      'review_authority': 'DESIGN_REVIEW_ONLY',
      'redesign_implementation_authorized': False,
      'threshold_policy_change': False,
      'alternative_thresholds': False,
      'candidate_ranking': False,
      'counterfactual_admission': False,
      'array_or_path_output': False,
      'output_volume': 'D',
      'expected_historical_failure_counts': EXPECTED_FAILURES,
      'execution_calls': ZERO_CALLS,
      'holdout': 'CLOSED',
      'opening_count': 0,
      'vehicle_authority': 'NONE',
    }
  )


def reconcile_metrics(actual, expected):
  a.require(actual is not None)
  a.require(all(actual[k] == v for k, v in expected.items()), 'HURDLE_ATTRIBUTION_HISTORICAL_RECONCILIATION_FAILURE')


def population_schema(receipt, fields, count, horizon=None, move_count=None):
  a.require(set(fields) | set(CONTEXT) <= set(receipt['arrays']), 'HURDLE_ATTRIBUTION_INPUT_INSUFFICIENT')
  for key, binding in receipt['arrays'].items():
    shape = binding['shape']
    expected = move_count if key == 'stage2_oracle_move_prediction' else count
    a.require(shape and shape[0] == expected, 'HURDLE_ATTRIBUTION_INPUT_CONFLICT')
    if key in ('observed_path', 'projected_path', 'hold_last_path', 'predicted_gate_path'):
      a.require(shape == [count, horizon if key == 'predicted_gate_path' else horizon + 1])
    elif key == 'command_history':
      a.require(len(shape) == 2 and shape[1] > 0)
    else:
      a.require(shape == [expected])
    a.require(binding['order'] == 'C' and binding['storage_format'] == 'NPY_GZIP_V1')
    if key in ('predicted_gate', 'true_move', 'predicted_gate_path', 'path_moved'):
      a.require(binding['dtype'] == '|b1')
    if key in (
      'current_tick',
      'target_next_tick',
      'actual_delta_tick',
      'projected_next_tick',
      'hold_last_next_tick',
      'initial_tick',
      'target_endpoint_tick',
      'observed_path',
      'projected_path',
      'hold_last_path',
    ):
      a.require(binding['dtype'] == '<i8')
    if key in ('p_move', 'integrated_delta', 'candidate_error', 'comparator_error', 'stage2_oracle_move_prediction'):
      a.require(binding['dtype'] == '<f8')


def analyze_one(root, job, receipt, threshold):
  n, moved = job['one_step']['count'], job['true_move']['count']
  population_schema(receipt, ONE_FIELDS, n, move_count=moved)
  a.require(receipt['anchor_sha256'] == job['one_step']['anchor_sha256'] == job['one_step']['comparator_anchor_sha256'])
  a.require(receipt['model_lineage'] == [job['stage1']['model_receipt_sha256'], job['threshold']['receipt_sha256'], job['stage2']['model_receipt_sha256']])
  arrays = {k: io.load_array(root, receipt, k) for k in ONE_FIELDS}
  probability = arrays['p_move']
  a.require(bool(np.isfinite(probability).all()) and bool(np.all((probability >= 0) & (probability <= 1))))
  # Validate the stored decision at its single historical threshold; no threshold search.
  a.require(np.array_equal(probability > threshold['selection']['value'], arrays['predicted_gate']))
  result = a.one_step(arrays)
  for label, previous in (('ALL', 'one_step'), ('MOVE', 'true_move')):
    for side, prior in (('candidate', 'candidate'), ('hold_last', 'comparator')):
      reconcile_metrics(result['classes'][label][side], job[previous][prior])
  diagnostic = result['confusion']
  a.require(diagnostic['counts'] == {k: job['stage1_diagnostics'][k] for k in ('TN', 'FP', 'FN', 'TP')}, 'HURDLE_ATTRIBUTION_HISTORICAL_RECONCILIATION_FAILURE')
  reconcile_metrics(
    diagnostic, {k: job['stage1_diagnostics'][k] for k in ('false_move_rate', 'missed_move_rate', 'precision', 'recall', 'specificity', 'balanced_accuracy')}
  )
  oracle = result['oracle']
  reconcile_metrics(oracle['metrics'], {k: job['stage2_oracle']['metrics'][k] for k in ('rmse', 'mae', 'p95')})
  a.require(oracle['sign_accuracy'] == job['stage2_oracle']['metrics']['sign_accuracy'])
  oracle['historical_grid_metrics'] = {k: job['stage2_oracle']['metrics'][k] for k in ('exact_hit', 'within_one_tick')}
  oracle['grid_provenance'] = 'PINNED_ORIGINAL_JOB_AGGREGATE_NO_PROJECTION_EXECUTION'
  train = a.confusion_counts({k: threshold['selection'][k] for k in ('TN', 'FP', 'FN', 'TP')})
  t = threshold['selection']
  a.require(
    t['P'] == t['TP'] + t['FN'] == job['train_move_count']
    and t['N'] == t['TN'] + t['FP'] == job['train_static_count']
    and t['BA_NUM'] == int(t['TP']) * int(t['N']) + int(t['TN']) * int(t['P'])
    and t['decision'] == '>'
    and t['population'] == 'TRAIN_ONLY'
  )
  result['transfer'] = {**a.transfer(train, diagnostic), 'threshold_receipt_sha256': threshold['receipt_sha256']}
  result['historical_metric_reconciliation'] = 'EXACT'
  return result


def analyze_rollout(root, job, receipt, horizon):
  historical = job['rollout'][str(horizon)]
  n = historical['overall']['count']
  population_schema(receipt, PATH_FIELDS, n, horizon=horizon)
  a.require(
    receipt['horizon'] == horizon
    and receipt['anchor_sha256']
    == receipt['comparator_anchor_sha256']
    == historical['overall']['anchor_sha256']
    == historical['overall']['comparator_anchor_sha256']
  )
  keys = ('observed_path', 'projected_path', 'hold_last_path', 'predicted_gate_path')
  readers = [io.array_chunks(io.member(root, receipt['arrays'][k]['filename']), receipt['arrays'][k]) for k in keys]
  vectors = {k: io.load_array(root, receipt, k) for k in ('initial_tick', 'target_endpoint_tick', 'candidate_error', 'comparator_error', 'path_moved')}
  collected, start = {}, 0
  for observed, projected, hold_path, gates in zip(*readers, strict=True):
    stop = start + len(observed)
    section = slice(start, stop)
    a.require(np.array_equal(observed[:, 0], vectors['initial_tick'][section]) and np.array_equal(observed[:, -1], vectors['target_endpoint_tick'][section]))
    a.require(bool(np.all(hold_path == observed[:, :1])))
    a.require(bool(np.all((np.diff(projected, axis=1) == 0) | gates)))
    a.require(
      (projected[:, -1] - observed[:, -1]).astype(np.float64).tobytes() == vectors['candidate_error'][section].tobytes()
      and (hold_path[:, -1] - observed[:, -1]).astype(np.float64).tobytes() == vectors['comparator_error'][section].tobytes()
    )
    rows = a.path_rows(observed, projected, gates)
    a.require(np.array_equal(rows['path_moved'], vectors['path_moved'][section]))
    for k, v in rows.items():
      collected.setdefault(k, []).append(v)
    start = stop
  a.require(start == n)
  rows = {k: np.concatenate(v) for k, v in collected.items()}
  result = a.rollout(rows, vectors['candidate_error'], vectors['comparator_error'])
  a.require(sum(result['gate_confusion']['counts'].values()) == n * horizon)
  for label, previous in (('ALL', 'overall'), ('PATH_MOVED', 'path_moved')):
    a.require(result['classes'][label]['count'] == historical[previous]['count'])
    for side, prior in (('candidate', 'candidate'), ('hold_last', 'comparator')):
      reconcile_metrics(result['classes'][label][side], historical[previous][prior])
  result['historical_metric_reconciliation'] = 'EXACT'
  return result


def mechanism(facts):
  a.require(len(facts) == 32, 'HURDLE_ATTRIBUTION_JOB_SET_CONFLICT')
  counts = {k: sum(bool(f[k]) for f in facts) for k in ('move_protection_pass', 'exact_hit_fail', 'static_loss_exceeds_gain', 'projected_false_move')}
  exact = counts['exact_hit_fail'] == counts['static_loss_exceeds_gain'] == 32
  supported = all(v == 32 for v in counts.values())
  return {
    'job_counts': counts,
    'exact_hit_state': 'HURDLE_EXACT_HIT_STATIC_LOSS_ALL_JOBS' if exact else 'HURDLE_EXACT_HIT_MECHANISM_MIXED',
    'stage1_design_review': 'STAGE1_GATE_REDESIGN_REVIEW_SUPPORTED' if supported else 'STAGE1_GATE_REDESIGN_REVIEW_NOT_FULLY_SUPPORTED',
    'authority': 'DESIGN_REVIEW_ONLY',
    'implementation_authorized': False,
    'fitting_authorized': False,
    'stage2_implementation_authorized': False,
  }


def gate_counts(jobs):
  return {k: sum(k in j['historical_gate']['failures'] for j in jobs) for k in EXPECTED_FAILURES}


def summarize(jobs):
  a.require([(j['candidate_id'], j['fold']) for j in jobs] == list(io.JOBS), 'HURDLE_ATTRIBUTION_JOB_SET_CONFLICT')
  a.require(gate_counts(jobs) == EXPECTED_FAILURES, 'HURDLE_ATTRIBUTION_HISTORICAL_RECONCILIATION_FAILURE')
  facts = []
  for j in jobs:
    failure = j['historical_gate']['failures']
    facts.append(
      {
        'move_protection_pass': not any(f'MOVE_{m}' in failure for m in ('RMSE', 'MAE', 'P95')),
        'exact_hit_fail': 'ONE_STEP_EXACT_HIT' in failure,
        'static_loss_exceeds_gain': j['one_step']['exact_hit']['static_loss_exceeds_move_gain'],
        'projected_false_move': j['one_step']['fp']['projected_moved_count'] > 0,
      }
    )
  folds = {}
  for fold in ('FOLD_A', 'FOLD_B'):
    selected = [j for j in jobs if j['fold'] == fold]
    values = {
      'false_move_rate': [j['one_step']['confusion']['false_move_rate'] for j in selected],
      'missed_move_rate': [j['one_step']['confusion']['missed_move_rate'] for j in selected],
      'balanced_accuracy': [j['one_step']['confusion']['balanced_accuracy'] for j in selected],
      'static_hit_loss': [j['one_step']['exact_hit']['static_hit_loss'] for j in selected],
      'move_hit_gain': [j['one_step']['exact_hit']['move_hit_gain'] for j in selected],
    }
    folds[fold] = {
      'job_count': len(selected),
      'historical_failure_counts': gate_counts(selected),
      'ranges': {k: {'min': min(v), 'max': max(v)} for k, v in values.items()},
    }
  horizons = {}
  for h in io.HORIZONS:
    subsets = [j['rollout'][str(h)]['classes']['GATE_PERFECT_PATH_MOVED'] for j in jobs]
    populated = [s for s in subsets if s['count']]
    horizons[str(h)] = {
      'gate_perfect_path_moved_support_jobs': len(populated),
      'small_support_jobs': sum(s['count'] < a.SUPPORT for s in populated),
      'candidate_sse_less_hold_jobs': sum(s['delta_sse'] < 0 for s in populated),
      'candidate_sse_greater_hold_jobs': sum(s['delta_sse'] > 0 for s in populated),
      'candidate_p95_nonworse_jobs': sum(s['candidate']['p95'] <= s['hold_last']['p95'] for s in populated),
      'candidate_p95_worse_jobs': sum(s['candidate']['p95'] > s['hold_last']['p95'] for s in populated),
      'gate_mismatch_relations': {
        key: sum(j['rollout'][str(h)]['first_event_relation'][key] for j in jobs) for key in jobs[0]['rollout'][str(h)]['first_event_relation']
      },
      'interpretation': 'DESCRIPTIVE_ASSOCIATION_NOT_CAUSAL; POPULATIONS_OVERLAP_ACROSS_STRUCTURES',
    }
  return p.seal(
    {
      'schema': 'EMPIRICAL_HURDLE_FAILURE_MECHANISM_SUMMARY_V1',
      'status': SUCCESS,
      'one_step': mechanism(facts),
      'folds': folds,
      'rollout': horizons,
      'historical_failure_counts': gate_counts(jobs),
      'historical_selection': 'HURDLE_NO_ADMISSIBLE_CANDIDATE',
      'model_selection': 'MODEL_SELECTION_FAILED_CLOSED',
      'execution_calls': ZERO_CALLS,
    }
  )


def source_code():
  return {
    name: io.digest(Path(__file__).with_name(name))
    for name in (
      'empirical_hurdle_attribution.py',
      'empirical_hurdle_attribution_io.py',
      'empirical_hurdle_attribution_math.py',
      'empirical_hurdle_attribution_schema.py',
    )
  }


def run(source, output, repeat):
  output = io.output_root(output, source)
  root = output / repeat
  a.require(repeat in ('repeat-1', 'repeat-2'))
  if (root / 'manifest.json').exists():
    return io.resume(root)
  a.require(not root.exists(), 'HURDLE_ATTRIBUTION_INCOMPLETE_NO_PARTIAL_REUSE')
  a.require(
    platform.python_version() == '3.12.13' and np.__version__ == '2.5.3' and all(os.environ.get(k) == '1' for k in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS')),
    'HURDLE_ATTRIBUTION_FROZEN_ENVIRONMENT_REQUIRED',
  )
  with io.firewall():
    manifest, inputs, public, identity = io.admit(source)
    policy_value = policy()
    io.write_json(output / 'policy.json', policy_value)
    authorization = p.seal(
      {
        'schema': 'EMPIRICAL_HURDLE_ATTRIBUTION_AUTHORIZATION_V1',
        'policy_sha256': policy_value['receipt_sha256'],
        'source_identity': identity,
        'executor_sources': source_code(),
        'output_identity_sha256': p.sha(str(output).encode()),
        'numeric_access': 'STORED_EVIDENCE_READ_ONLY',
        'execution_calls': ZERO_CALLS,
      }
    )
    io.write_json(output / 'authorization.json', authorization)
    jobs, names = [], []
    for local, historical, populations, threshold in inputs:
      job = {
        'schema': 'EMPIRICAL_HURDLE_FAILURE_ATTRIBUTION_JOB_V1',
        'candidate_id': historical['candidate_id'],
        'fold': historical['fold'],
        'original_job_receipt_sha256': historical['receipt_sha256'],
        'population_receipts': historical['population_receipts'],
        'authorization_sha256': authorization['receipt_sha256'],
        'historical_gate': historical['gate'],
        'one_step': analyze_one(local / 'one-step', historical, populations['one-step'], threshold),
        'rollout': {},
      }
      for h in io.HORIZONS:
        job['rollout'][str(h)] = analyze_rollout(local / f'rollout-{h}', historical, populations[f'rollout-{h}'], h)
      job = p.seal(job)
      name = f'jobs/{job["candidate_id"]}/{job["fold"]}/receipt.json'
      io.write_json(root / name, job)
      jobs.append(job)
      names.append(name)
      print(job['candidate_id'], job['fold'], 'READ_ONLY_ATTRIBUTION_COMPLETE', flush=True)
    summary = summarize(jobs)
    a.require(summary['historical_failure_counts'] == public['candidate-gates']['failure_counts'])
    io.verify_files(source / 'repeat-1', manifest['files'])
    a.require(
      io.digest(source / 'authorization.json') == identity['authorization_file_sha256']
      and io.digest(source / 'repeatability.json') == identity['repeatability_file_sha256']
      and io.digest(source / 'repeat-1/manifest.json') == identity['manifest_file_sha256']
    )
    io.write_json(root / 'summary.json', summary)
    names.append('summary.json')
    readiness = p.seal(
      {
        'schema': 'EMPIRICAL_HURDLE_ATTRIBUTION_READINESS_V1',
        'status': SUCCESS,
        'states': [
          'READ_ONLY_ATTRIBUTION_COMPLETE',
          'NO_NEW_MODEL_FIT',
          'NO_THRESHOLD_RESELECTION',
          'NO_MODEL_REPLAY',
          'NO_MODEL_SELECTION',
          'NO_POLICY_CHANGE',
          'HURDLE_NO_ADMISSIBLE_CANDIDATE_PRESERVED',
        ],
        'job_count': 32,
        'one_step_populations': 32,
        'rollout_populations': 128,
        'summary_sha256': summary['receipt_sha256'],
        'execution_calls': ZERO_CALLS,
        'source_manifest_sha256': io.SOURCE_SHA,
        'source_manifest_listed_bytes_unchanged': True,
        'source_write_count': 0,
        'source_fallback': False,
        'holdout': 'CLOSED',
        'opening_count': 0,
        'vehicle_authority': 'NONE',
      }
    )
    io.write_json(root / 'readiness.json', readiness)
    names.append('readiness.json')
    return io.finish(
      root,
      names,
      {
        'schema': 'EMPIRICAL_HURDLE_ATTRIBUTION_MANIFEST_V1',
        'source_manifest_sha256': io.SOURCE_SHA,
        'authorization_sha256': authorization['receipt_sha256'],
        'policy_sha256': policy_value['receipt_sha256'],
        'job_order': [list(j) for j in io.JOBS],
        'summary_sha256': summary['receipt_sha256'],
        'readiness_sha256': readiness['receipt_sha256'],
        'status': SUCCESS,
      },
    )


def repeatability(root, source):
  root = io.output_root(root, source)
  first, second = io.resume(root / 'repeat-1'), io.resume(root / 'repeat-2')
  a.require(first == second, 'HURDLE_ATTRIBUTION_REPEATABILITY_FAILURE')
  with io.firewall(), ExitStack() as traps:
    for module, names in (
      (io, ('load_array', 'array_chunks', 'admit')),
      (gzip, ('open',)),
      (a, ('metrics', 'pair', 'summary', 'confusion', 'confusion_counts', 'first', 'one_step', 'path_rows', 'rollout', 'transfer', 'partition_accounting')),
    ):
      for name in names:
        traps.enter_context(patch.object(module, name, io.forbidden))
    for name in ('analyze_one', 'analyze_rollout', 'summarize', 'mechanism'):
      traps.enter_context(patch(__name__ + '.' + name, io.forbidden))
    resumed = io.resume(root / 'repeat-1')
  a.require(resumed == first)
  receipt = p.seal(
    {
      'schema': 'EMPIRICAL_HURDLE_ATTRIBUTION_REPEATABILITY_V1',
      'status': 'PASS',
      'independent_runs': 2,
      'manifest_sha256': first['receipt_sha256'],
      'all_file_hashes_exact': True,
      'receipts_exact': True,
      'trapped_resume_exact': True,
      'source_manifest_sha256': io.SOURCE_SHA,
    }
  )
  io.write_json(root / 'repeatability.json', receipt)
  return receipt


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--source', type=Path, required=True)
  parser.add_argument('--output', type=Path, required=True)
  parser.add_argument('--repeat', choices=('repeat-1', 'repeat-2'))
  parser.add_argument('--verify-repeatability', action='store_true')
  args = parser.parse_args()
  result = repeatability(args.output, args.source) if args.verify_repeatability else run(args.source, args.output, args.repeat)
  print(result['receipt_sha256'])


if __name__ == '__main__':
  main()
