"""Predeclared minimal E release. Never publish decisions, cells, rows or paths."""

import math
import statistics

from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e_decision as decision

SUPPORT = 201  # Publication floor inherited from C, not a new performance gate.
INHERITED_SUPPRESSED = {'MOVE_ONSET', 'MOVE_CONTINUATION'}
METRICS = ('rmse', 'mae', 'p95')


def safe_cell(event, n):
  return type(event) is int and type(n) is int and 0 <= event <= n and n >= SUPPORT and all(v == 0 or v >= SUPPORT for v in (event, n - event))


def safe_changes(changed):
  return type(changed) is int and (changed == 0 or changed >= SUPPORT)


def summary(values):
  decision.need(bool(values) and all(type(v) in (int, float) and math.isfinite(v) for v in values), 'E_PUBLIC_NONFINITE')
  return {'valid_jobs': len(values), 'median': statistics.median(values), 'minimum': min(values), 'maximum': max(values)}


def grouped(jobs, accessor):
  result = {}
  for fold in ('FOLD_A', 'FOLD_B'):
    rows = [r for r in jobs if r['fold'] == fold]
    decision.need(len(rows) == 16)
    result[fold] = {arm: summary([accessor(r, arm) for r in rows]) for arm in ('D0', 'D1')}
  return result


def project(payload):
  """Co-suppress a whole family across both folds/arms if any cell is unsafe.

  No release contains scientific counts, job-specific metric values, histogram
  cells, state-conditioned scores hidden by C, or paired changes on rare rows.
  Onset/continuation details remain withheld regardless of new D1 support.
  """
  jobs = payload['jobs']
  decision.need(tuple((r['candidate_id'], r['fold']) for r in jobs) == decision.JOBS, 'E_PUBLIC_JOB_IDENTITY')
  decision.need(all(set(r['arms']) == {'D0', 'D1'} for r in jobs))
  families = {}
  for group in ('one_step', 'true_move'):
    change_key = 'projected_rows' if group == 'one_step' else 'true_move_projected_rows'
    continuous_key = 'continuous_rows' if group == 'one_step' else 'true_move_continuous_rows'
    allowed = all(
      r['arms']['D1'].get('paired_changes') is not None
      and safe_changes(r['arms']['D1']['paired_changes'][change_key])
      and safe_changes(r['arms']['D1']['paired_changes'][continuous_key])
      and all(r['arms'][a][group] is not None and r['arms'][a][group]['count'] >= SUPPORT for a in ('D0', 'D1'))
      for r in jobs
    )
    if not allowed:
      families[group] = {'status': 'JOINTLY_SUPPRESSED_OR_NUMERICAL_NONPASS'}
      continue
    # Exact/within tick percentages are withheld: exposing them can recover
    # rare cells through historical same-anchor counts and cross-arm deltas.
    metrics = METRICS
    families[group] = {
      'status': 'RELEASED_JOB_MEDIANS_AND_RANGES',
      'metrics': {m: grouped(jobs, lambda r, a, metric=m, g=group: r['arms'][a][g]['candidate'][metric]) for m in metrics},
    }
  for horizon in (25, 50, 100, 200):
    for group in ('overall', 'path_moved'):
      key = f'H{horizon}_{group.upper()}'
      change_key = 'paired_changed_endpoint_rows' if group == 'overall' else 'paired_changed_path_moved_endpoint_rows'
      allowed = all(
        r['arms']['D1']['rollout'][str(horizon)].get(group) is not None
        and safe_changes(r['arms']['D1']['rollout'][str(horizon)].get(change_key))
        and all(
          r['arms'][a]['rollout'][str(horizon)][group] is not None and r['arms'][a]['rollout'][str(horizon)][group]['count'] >= SUPPORT for a in ('D0', 'D1')
        )
        for r in jobs
      )
      families[key] = (
        {'status': 'JOINTLY_SUPPRESSED_OR_NUMERICAL_NONPASS'}
        if not allowed
        else {
          'status': 'RELEASED_JOB_MEDIANS_AND_RANGES',
          'metrics': {m: grouped(jobs, lambda r, a, metric=m, h=str(horizon), g=group: r['arms'][a]['rollout'][h][g]['candidate'][metric]) for m in METRICS},
        }
      )
  transitions = {}
  for state in ('STATIC_HOLD', 'MOVE_ONSET', 'MOVE_TERMINATION', 'MOVE_CONTINUATION'):
    allowed = state not in INHERITED_SUPPRESSED and all(
      r['arms']['D1'].get('tick_diagnostics') is not None
      and safe_changes(r['arms']['D1']['tick_diagnostics']['transitions'][state]['paired_changed_gate_rows'])
      and all(
        safe_cell(r['arms'][a]['tick_diagnostics']['transitions'][state]['move_gate'], r['arms'][a]['tick_diagnostics']['transitions'][state]['n'])
        for a in ('D0', 'D1')
      )
      for r in jobs
    )
    transitions[state] = (
      {'status': 'SUPPRESSED_C_COMPATIBLE_JOINT_POLICY'}
      if not allowed
      else {
        'status': 'RELEASED_JOB_MEDIANS_AND_RANGES',
        'MOVE_gate_rate': grouped(jobs, lambda r, a, s=state: r['arms'][a]['tick_diagnostics']['transitions'][s]['move_gate_rate']),
      }
    )
  gate_rows = [
    {
      'candidate_id': r['candidate_id'],
      'fold': r['fold'],
      **{a: {'pass': r['arms'][a]['gate']['pass'], 'failures': r['arms'][a]['gate']['failures']} for a in ('D0', 'D1')},
    }
    for r in jobs
  ]
  passing = [c for c, _ in decision.JOBS[::2] if all(r['arms']['D1']['gate']['pass'] for r in jobs if r['candidate_id'] == c)]
  return {
    'schema': 'V4_E_PUBLIC_PROJECTION_V1',
    'protocol_sha256': payload['protocol_sha256'],
    'status': 'E_EXECUTION_COMPLETE_RETROSPECTIVE_GATE_PASS_ONLY' if passing else 'E_EXECUTION_COMPLETE_D1_NOT_ADMISSIBLE',
    'processed_jobs': len(jobs),
    'policy_arms': ['D0', 'D1'],
    'metric_families': families,
    'transitions': transitions,
    'acceptance_by_job': gate_rows,
    'retrospective_both_fold_gate_qualifying_candidates': passing,
    'selected_candidate': None,
    'selected_policy': None,
    'policy_adopted': False,
    'scientific_counts_and_bins': 'WITHHELD',
    'onset_continuation_details': 'WITHHELD_TO_PRESERVE_C_SUPPRESSION',
    'state_conditioned_score_and_calibration': 'TEACHER_FORCED_DEV_SCORE_BYTE_EQUIVALENCE_VERIFIED_USE_PINNED_C_PUBLIC_RESULTS',
    'interpretation': 'OVERLAPPING_JOB_MEDIANS_NOT_INDEPENDENT_DRIVING_TRIALS; RETROSPECTIVE_NOT_BLINDED; NO_CAUSAL_SHARE_IDENTIFIED',
    'holdout': 'CLOSED',
    'vehicle_authority': 'NONE',
    'Hugging_Face': 'NOT_REQUIRED / NOT_USED',
    'original_V4_result': 'HURDLE_STAGE1_V4_NO_ADMISSIBLE_CANDIDATE',
    'original_selection': 'MODEL_SELECTION_FAILED_CLOSED',
    'original_TRAIN_rowwise_gate': 'NOT_SAVED',
    'original_replica': 'REPLICA_PAYLOAD_EQUALITY_NOT_FULLY_REVERIFIED',
  }
