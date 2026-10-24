"""Frozen E2 release: joint three-arm suppression, never raw private decisions."""

from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e_publication as prior
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_decision as decision

ARMS = ('D0', 'D1', 'D2')
SUPPORT = prior.SUPPORT


def group(jobs, accessor):
  out = {}
  for fold in ('FOLD_A', 'FOLD_B'):
    rows = [r for r in jobs if r['fold'] == fold]
    decision.need(len(rows) == 16)
    out[fold] = {arm: prior.summary([accessor(r, arm) for r in rows]) for arm in ARMS}
  return out


def safe_change_proof(lower_bound):
  # None is unknown, not zero. Nonzero lower bounds prove >=201 changed rows.
  return type(lower_bound) is int and (lower_bound == 0 or lower_bound >= SUPPORT)


def safe_three_counts(counts, n):
  if not all(prior.safe_cell(k, n) for k in counts):
    return False
  for first in range(3):
    for second in range(first + 1, 3):
      a, b = counts[first], counts[second]
      if a == b:
        if a not in (0, n):
          return False  # Equal non-extreme counts do not prove row equality.
      elif abs(a - b) < SUPPORT:
        return False
  return True


def complement_safe(jobs, *, horizon=None):
  """Joint release guards also cover subtraction with historical subset metrics."""
  for row in jobs:
    arms = row['arms']
    if horizon is None:
      total = [arms[a].get('one_step') for a in ARMS]
      subset = [arms[a].get('true_move') for a in ARMS]
      keys = (('projected_rows', 'true_move_projected_rows'), ('continuous_rows', 'true_move_continuous_rows'))
      changes = [arms[a].get('paired_changes') for a in ('D1', 'D2')]
      lower = arms['D2'].get('D1_changed_lower_bounds')
    else:
      rolls = [arms[a]['rollout'][str(horizon)] for a in ARMS]
      total = [r.get('overall') for r in rolls]
      subset = [r.get('path_moved') for r in rolls]
      keys = (('paired_changed_endpoint_rows', 'paired_changed_path_moved_endpoint_rows'),)
      changes = rolls[1:]
      lower = {
        'paired_changed_endpoint_rows': rolls[2].get('D1_changed_endpoint_lower_bound'),
        'paired_changed_path_moved_endpoint_rows': rolls[2].get('D1_changed_path_moved_endpoint_lower_bound'),
      }
    if any(v is None for v in (*total, *subset, *changes, lower)):
      return False
    if any(t['count'] != total[0]['count'] or sub['count'] != subset[0]['count'] for t, sub in zip(total, subset, strict=True)):
      return False
    support = total[0]['count'] - subset[0]['count']
    if support < 0 or 0 < support < SUPPORT:
      return False
    for full_key, subset_key in keys:
      values = [change.get(full_key) for change in changes] + [change.get(subset_key) for change in changes]
      if any(type(v) is not int for v in values):
        return False
      counts = [change[full_key] - change[subset_key] for change in changes]
      if any(k < 0 or k > support or not prior.safe_cell(k, support) for k in counts):
        return False
      if lower.get(full_key) == lower.get(subset_key) == 0:
        bound = 0  # Both whole and subset row equality already proven.
      elif counts[0] == counts[1]:
        bound = 0 if counts[0] == 0 else None
      else:
        bound = abs(counts[0] - counts[1])
      if not safe_change_proof(bound):
        return False
  return True


def project(payload):
  jobs = payload['jobs']
  decision.need(tuple((r['candidate_id'], r['fold']) for r in jobs) == decision.JOBS)
  decision.need(all(set(r['arms']) == set(ARMS) for r in jobs))
  families = {}
  for name in ('one_step', 'true_move'):
    keys = ('projected_rows', 'continuous_rows') if name == 'one_step' else ('true_move_projected_rows', 'true_move_continuous_rows')
    safe = all(
      all(r['arms'][a].get(name) is not None and r['arms'][a][name]['count'] >= SUPPORT for a in ARMS)
      and r['arms']['D2'].get('D1_changed_lower_bounds') is not None
      and all(
        prior.safe_changes(r['arms']['D1']['paired_changes'][k])
        and prior.safe_changes(r['arms']['D2']['paired_changes'][k])
        and safe_change_proof(r['arms']['D2']['D1_changed_lower_bounds'][k])
        for k in keys
      )
      for r in jobs
    )
    families[name] = (
      {'status': 'JOINTLY_SUPPRESSED_OR_NONPASS'}
      if not safe
      else {
        'status': 'RELEASED_JOB_MEDIANS_AND_RANGES',
        'metrics': {m: group(jobs, lambda r, a, n=name, metric=m: r['arms'][a][n]['candidate'][metric]) for m in prior.METRICS},
      }
    )
  for h in (25, 50, 100, 200):
    for name in ('overall', 'path_moved'):
      key = 'paired_changed_endpoint_rows' if name == 'overall' else 'paired_changed_path_moved_endpoint_rows'
      lb = 'D1_changed_endpoint_lower_bound' if name == 'overall' else 'D1_changed_path_moved_endpoint_lower_bound'
      safe = all(
        all(r['arms'][a]['rollout'][str(h)].get(name) is not None and r['arms'][a]['rollout'][str(h)][name]['count'] >= SUPPORT for a in ARMS)
        and prior.safe_changes(r['arms']['D1']['rollout'][str(h)].get(key))
        and prior.safe_changes(r['arms']['D2']['rollout'][str(h)].get(key))
        and safe_change_proof(r['arms']['D2']['rollout'][str(h)].get(lb))
        for r in jobs
      )
      families[f'H{h}_{name.upper()}'] = (
        {'status': 'JOINTLY_SUPPRESSED_OR_NONPASS'}
        if not safe
        else {
          'status': 'RELEASED_JOB_MEDIANS_AND_RANGES',
          'metrics': {
            m: group(jobs, lambda r, a, horizon=str(h), n=name, metric=m: r['arms'][a]['rollout'][horizon][n]['candidate'][metric]) for m in prior.METRICS
          },
        }
      )
  transitions = {}
  for state in ('STATIC_HOLD', 'MOVE_ONSET', 'MOVE_TERMINATION', 'MOVE_CONTINUATION'):
    safe = state not in prior.INHERITED_SUPPRESSED and all(
      all(r['arms'][a].get('tick_diagnostics') is not None for a in ARMS)
      and all(
        prior.safe_cell(r['arms'][a]['tick_diagnostics']['transitions'][state]['move_gate'], r['arms'][a]['tick_diagnostics']['transitions'][state]['n'])
        for a in ARMS
      )
      and prior.safe_changes(r['arms']['D1']['tick_diagnostics']['transitions'][state]['paired_changed_gate_rows'])
      and prior.safe_changes(r['arms']['D2']['tick_diagnostics']['transitions'][state]['paired_changed_gate_rows'])
      and safe_change_proof(r['arms']['D2']['tick_diagnostics']['transitions'][state]['D1_changed_gate_lower_bound'])
      for r in jobs
    )
    transitions[state] = (
      {'status': 'SUPPRESSED_C_E_COMPATIBLE_JOINT_POLICY'}
      if not safe
      else {
        'status': 'RELEASED_JOB_MEDIANS_AND_RANGES',
        'MOVE_gate_rate': group(jobs, lambda r, a, st=state: r['arms'][a]['tick_diagnostics']['transitions'][st]['move_gate_rate']),
      }
    )
  families['HARMFUL_NEXT_STATIC_REALIZATION'] = {'status': 'WITHHELD_GATE_TO_HOLD_COMPLEMENT_C_E_PROTECTION'}
  if not complement_safe(jobs) or any(families[n]['status'] != 'RELEASED_JOB_MEDIANS_AND_RANGES' for n in ('one_step', 'true_move')):
    for name in ('one_step', 'true_move'):
      families[name] = {'status': 'JOINTLY_SUPPRESSED_OR_NONPASS'}
  for h in (25, 50, 100, 200):
    pair = (f'H{h}_OVERALL', f'H{h}_PATH_MOVED')
    if not complement_safe(jobs, horizon=h) or any(families[n]['status'] != 'RELEASED_JOB_MEDIANS_AND_RANGES' for n in pair):
      for name in pair:
        families[name] = {'status': 'JOINTLY_SUPPRESSED_OR_NONPASS'}
  passing = [candidate for candidate, _ in decision.JOBS[::2] if all(r['arms']['D2']['gate']['pass'] for r in jobs if r['candidate_id'] == candidate)]
  return {
    'schema': 'V4_E2_PUBLIC_PROJECTION_V1',
    'protocol_sha256': payload['protocol_sha256'],
    'status': 'E2_EXECUTION_COMPLETE_RETROSPECTIVE_GATE_PASS_ONLY' if passing else 'E2_EXECUTION_COMPLETE_D2_NOT_ADMISSIBLE',
    'processed_jobs': 32,
    'policy_arms': list(ARMS),
    'metric_families': families,
    'transitions': transitions,
    'acceptance_by_job': [
      {
        'candidate_id': r['candidate_id'],
        'fold': r['fold'],
        **{a: {'pass': r['arms'][a]['gate']['pass'], 'failures': r['arms'][a]['gate']['failures']} for a in ARMS},
      }
      for r in jobs
    ],
    'retrospective_both_fold_qualifying_candidates': passing,
    'selected_candidate': None,
    'selected_policy': None,
    'policy_adopted': False,
    'scientific_counts_bins_exact_hit_details': 'WITHHELD',
    'onset_continuation_details': 'INHERITED_C_E_SUPPRESSION',
    'inference_and_row_telemetry': 'PRIVATE_ONLY_NOT_RELEASED',
    'holdout': 'CLOSED',
    'vehicle_authority': 'NONE',
    'interpretation': 'OVERLAPPING_JOB_MEDIANS_RANGES_NOT_INDEPENDENT_DRIVES; EXPLORATORY_RETROSPECTIVE_NOT_BLINDED',
    'original_V4_result': 'HURDLE_STAGE1_V4_NO_ADMISSIBLE_CANDIDATE',
    'D1_result': 'E_EXECUTION_COMPLETE_D1_NOT_ADMISSIBLE',
    'Hugging_Face': 'NOT_REQUIRED / NOT_USED',
  }
