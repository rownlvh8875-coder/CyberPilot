"""Read-only explanation of frozen v2 experiments, not a new acceptance gate.

Only structurally valid, repeatable evidence with a matching recomputed verdict
is summarized. Digests do not authenticate producers. No search, candidate
selection, control invocation, parameter update or vehicle authority exists here.
"""
import argparse
from collections import Counter
import json
from pathlib import Path

from openpilot.tools.cyber_autotune.contracts import finite_number
from openpilot.tools.cyber_autotune.native_protocol import _unique_pairs, canonical, digest
from openpilot.tools.cyber_autotune.synthetic_native_v2 import frozen_policy
from openpilot.tools.cyber_autotune.synthetic_pipeline import ARMS, AUTHORITY, MAX_OUTPUT, evaluate


# At most the existing bounded worker output for each declared arm/repetition.
MAX_REPORT_BYTES = MAX_OUTPUT * len(ARMS) * 2


def metric_delta(baseline, candidate, direction: str) -> dict:
  """Positive oriented delta is worse; relative improvement needs positive base.

  Null is missing coverage, never zero. Negative/zero signed margins have no
  meaningful percentage denominator. Different units are never summed/ranked.
  """
  if direction not in ('lower', 'higher') or any(value is not None and not finite_number(value)
                                               for value in (baseline, candidate)):
    raise ValueError('INVALID_DIAGNOSTIC_METRIC')
  result = {'baseline': baseline, 'candidate': candidate, 'oriented_delta': None, 'relative_improvement': None}
  if baseline is None or candidate is None:
    return {**result, 'status': 'UNAVAILABLE' if baseline is candidate else 'AVAILABILITY_CHANGED'}
  delta = candidate - baseline if direction == 'lower' else baseline - candidate
  relative = -delta / baseline if baseline > 0 else None
  if not finite_number(delta) or (relative is not None and not finite_number(relative)):
    raise ValueError('NONFINITE_DIAGNOSTIC_DELTA')
  allowance = frozen_policy()['absolute_numeric_allowance']
  status = 'REGRESSION' if delta > allowance else ('IMPROVEMENT' if delta < -allowance else 'UNCHANGED')
  return {**result, 'oriented_delta': delta, 'relative_improvement': relative, 'status': status}


def _candidate(base, candidate, verdict, policy):
  variants = []
  axes = {axis: {'completed_variants': 0, 'rejected_input_variants': 0, 'changed_trace_variants': 0,
                 'changed_car_params_variants': 0, 'regression_count': 0, 'regressions_by_metric': Counter()}
          for axis in ('lateral', 'longitudinal')}
  for before, after in zip(base['results'], candidate['results'], strict=True):
    axis = axes[before['axis']]
    row = {'case_id': before['case_id'], 'axis': before['axis'], 'physical_delay_s': before['physical_delay_s'],
           'input_status': before['input_status'], 'status': before['status'], 'metrics': None,
           'trace_changed': None, 'car_params_changed': None}
    if before['metrics'] is None:
      axis['rejected_input_variants'] += 1
    else:
      axis['completed_variants'] += 1
      row['trace_changed'] = before['metrics']['trace_sha256'] != after['metrics']['trace_sha256']
      row['car_params_changed'] = before['candidate_car_params_sha256'] != after['candidate_car_params_sha256']
      axis['changed_trace_variants'] += int(row['trace_changed'])
      axis['changed_car_params_variants'] += int(row['car_params_changed'])
      row['metrics'] = {}
      for direction, key in (('lower', 'lower_is_better'), ('higher', 'higher_is_better')):
        for metric in policy[key]:
          if metric not in before['metrics']:
            continue
          detail = metric_delta(before['metrics'][metric], after['metrics'][metric], direction)
          row['metrics'][metric] = {**detail, 'direction': direction, 'primary': metric in policy['primary_metrics']}
          if detail['status'] == 'REGRESSION':
            axis['regression_count'] += 1
            axis['regressions_by_metric'][metric] += 1
    variants.append(row)
  for axis in axes.values():
    axis['effect_status'] = 'OBSERVED_TRACE_CHANGE' if axis['changed_trace_variants'] else 'NO_OBSERVED_TRACE_CHANGE'
    axis['regressions_by_metric'] = dict(sorted(axis['regressions_by_metric'].items()))
  # Existing gate reasons collapse equal case/metric failures across delays.
  # Preserve that verdict while retaining every delay in diagnostic rows.
  return {'gate_status': verdict['status'], 'gate_reasons': list(verdict['reasons']), 'axes': axes, 'variants': variants}


def diagnose(report: dict) -> dict:
  failure = {'status': 'BLOCKED', 'reason': 'INVALID_SYNTHETIC_EVIDENCE', 'vehicle_activation_allowed': False}
  try:
    if type(report) is not dict or set(report) != {'evaluation', 'arms'}:
      return failure
    evaluation = evaluate(report['arms'])
    if evaluation['status'] != 'COMPLETED_SYNTHETIC_ONLY' or canonical(evaluation) != canonical(report['evaluation']):
      return failure
    # A completed evaluator may have rejected incomparable plant/reset/CP data.
    # Never derive performance deltas for comparisons it deliberately skipped.
    for verdict in evaluation['comparisons'].values():
      if any(reason != 'NO_REQUIRED_PRIMARY_IMPROVEMENT' and
             not reason.endswith((':REGRESSION', ':AVAILABILITY_CHANGED')) for reason in verdict['reasons']):
        return failure
    policy = frozen_policy()
    base = report['arms']['baseline'][0]
    result = {
      'schema': 'synthetic-diagnostics-v1', 'status': 'DIAGNOSTIC_ONLY',
      'scope': evaluation['scope'], 'readiness': 'NOT_READY',
      'producer_authentication': 'NOT_ESTABLISHED', 'causal_attribution': 'NOT_ESTABLISHED',
      'count_semantics': 'PER_METRIC_PER_DELAY_VARIANT_NOT_UNIQUE_GATE_REASON_COUNT',
      'report_sha256': digest(canonical(report)), 'evidence_sha256': evaluation['evidence_sha256'],
      'policy_sha256': evaluation['policy_sha256'],
      'source_files_sha256': evaluation['binding']['files_sha256'],
      'candidates': {name: _candidate(base, report['arms'][name][0], evaluation['comparisons'][name], policy)
                     for name in ('gentle', 'firm')},
      **dict.fromkeys(AUTHORITY, False), 'vehicle_activation_allowed': False,
    }
    canonical(result)
    return result
  except (ValueError, TypeError, KeyError, IndexError, OverflowError, RecursionError, OSError):
    return failure


def main(argv=None) -> int:
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('report', type=Path)
  args = parser.parse_args(argv)
  result = {'status': 'BLOCKED', 'reason': 'UNREADABLE_OR_INVALID_REPORT', 'vehicle_activation_allowed': False}
  try:
    if args.report.is_file() and not args.report.is_symlink():
      with args.report.open('rb') as stream:
        raw = stream.read(MAX_REPORT_BYTES + 1)
      if 0 < len(raw) <= MAX_REPORT_BYTES:
        result = diagnose(json.loads(raw, object_pairs_hook=_unique_pairs))
  except (OSError, ValueError, TypeError, UnicodeError, RecursionError):
    pass  # Never reflect caller filenames, payloads or exception strings.
  print(canonical(result).decode())
  return 0 if result['status'] == 'DIAGNOSTIC_ONLY' else 1


if __name__ == '__main__':
  raise SystemExit(main())
