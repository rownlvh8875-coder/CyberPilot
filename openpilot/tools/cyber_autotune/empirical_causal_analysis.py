"""Six independent, frozen causal conditions; no fitted or sequential selector."""
import numpy as np
from openpilot.tools.cyber_autotune import empirical_plant_model as m
from openpilot.tools.cyber_autotune import empirical_stage_a_regime as paired

MINIMUM = 201
CONDITIONS = {
  'C1': 'LATEST_PRIOR_COMMAND_CHANGED',
  'C2': 'DELAYED_MODEL_INPUT_CHANGED',
  'C3': 'LATEST_PRIOR_COMMAND_REVERSAL',
  'C4': 'PAST_MEASURED_ANGLE_CHANGED',
  'C5': 'PAST_COMMAND_AT_RAIL',
  'C6': 'SOURCE_HALF_QUANTUM_ARX_MOVEMENT',
}
DEFINITIONS = {
  'C1': 'u[k-1] != u[k-2]', 'C2': 'u[k-5] != u[k-6]',
  'C3': 'u[k-1] != 0 and u[k-2] != 0 and sign(u[k-1]) != sign(u[k-2])',
  'C4': 'y[k-1] != y[k-2]', 'C5': 'abs(u[k-1]) == 409',
  'C6': 'abs(frozen_ARX_prediction - y[k-1]) >= source_half_quantum_0.05_deg',
}


def conditions(context, prediction):
  context, prediction = np.asarray(context), np.asarray(prediction)
  if context.ndim != 2 or context.shape[1] != 6 or prediction.shape != (len(context),):
    raise ValueError('SIX_PRIOR_FIELDS_ONLY_NO_TARGET_OR_UNKNOWN_FIELD')
  if not np.isfinite(context).all() or not np.isfinite(prediction).all():
    raise ValueError('FINITE_CAUSAL_INPUT_REQUIRED')
  u1, u2, u5, u6, y1, y2 = context.T
  return {
    'C1': u1 != u2, 'C2': u5 != u6,
    'C3': (u1 != 0) & (u2 != 0) & (np.sign(u1) != np.sign(u2)),
    'C4': y1 != y2, 'C5': abs(u1) == 409,
    'C6': abs(prediction - y1) >= .05,
  }


def command_equivalence(raw):
  raw = np.asarray(raw, dtype=np.float64)
  if not np.isfinite(raw).all() or np.any(raw != np.rint(raw)) or np.any(abs(raw) > 409):
    raise ValueError('SOURCE_CONFIRMED_INTEGER_RAW_DOMAIN_REQUIRED')
  normalized = (raw / 409).astype(np.float32)
  return bool(len(np.unique(raw)) == len(np.unique(normalized)))


def scope_gate(true, false):
  if any(x['count'] < MINIMUM for x in (true, false)):
    return {'passed': False, 'status': 'INSUFFICIENT_BRANCH_SUPPORT'}
  if any(x[side][key] is None or not np.isfinite(x[side][key])
         for x in (true, false) for side in ('arx', 'hold_last') for key in ('RMSE', 'MAE', 'P95_ABS')):
    return {'passed': False, 'status': 'NONFINITE_METRIC'}
  a, h = true['arx'], true['hold_last']
  dynamic = a['RMSE'] < h['RMSE'] and a['MAE'] <= h['MAE'] and a['P95_ABS'] <= h['P95_ABS']
  a, h = false['arx'], false['hold_last']
  steady = all(h[k] <= a[k] for k in ('RMSE', 'MAE', 'P95_ABS'))
  return {'passed': bool(dynamic and steady), 'status': 'PASS' if dynamic and steady else 'DIRECTIONAL_CRITERION_FAILED',
          'true_branch_pass': bool(dynamic), 'false_branch_pass': bool(steady)}


def audit(one, context):
  if one.ndim != 2 or one.shape[1] != 5 or len(one) != len(context) or not np.isfinite(one).all():
    raise ValueError('EXACT_FINITE_SHARED_PREDICTION_SUPPORT_REQUIRED')
  data = paired.paired(one)
  denominator = float(np.sqrt(np.mean(data[:, 1])) + np.sqrt(np.mean(data[:, 3])))
  output = {}
  for name, mask in conditions(context, one[:, 1]).items():
    branches = {key: paired.summarize(one, data, selected, len(one), denominator)
                for key, selected in (('TRUE', mask), ('FALSE', ~mask))}
    output[name] = {'branches': branches, 'gate': scope_gate(branches['TRUE'], branches['FALSE']),
                    'coverage': {'valid': len(one), 'total': len(one), 'unavailable': 0}}
  return output


def selector(one, mask, admitted):
  if admitted is not True:
    raise ValueError('STRICT_ALL_SCOPE_SEPARATOR_REQUIRED_BEFORE_SELECTOR')
  return m.statistics(np.where(mask, one[:, 1], one[:, 3]) - one[:, 0], one[:, 0])


def adjudicate(rows):
  route_ids = {x['route_id'] for x in rows}
  expected = {(rid,b) for rid in route_ids for b in ('LOW','MEDIUM','HIGH')}
  if len(rows) != 6 or len(route_ids) != 2 or {(x['route_id'], x['speed_bin']) for x in rows} != expected:
    raise ValueError('EXACT_SIX_ROUTE_BIN_SCOPES_REQUIRED')
  states = {}
  for name in CONDITIONS:
    gates = [x['conditions'][name]['gate'] for x in rows]
    supported = all(x['passed'] for x in gates)
    insufficient = any(x['status'] == 'INSUFFICIENT_BRANCH_SUPPORT' for x in gates)
    invalid = any(x['status'] == 'NONFINITE_METRIC' for x in gates)
    states[name] = {'status': 'CAUSAL_SEPARATOR_SUPPORTED' if supported else
                    'INSUFFICIENT_BRANCH_SUPPORT' if insufficient else
                    'NONFINITE_METRIC' if invalid else
                    'CAUSAL_SEPARATOR_PARTIAL_ROUTE_OR_SPEED_DEPENDENT' if any(x['passed'] for x in gates) else
                    'NO_STRICT_SEPARATOR',
                    'passing_scopes': sum(x['passed'] for x in gates), 'total_scopes': 6}
  admitted = [k for k, x in states.items() if x['status'] == 'CAUSAL_SEPARATOR_SUPPORTED']
  incomplete = ('INSUFFICIENT_BRANCH_SUPPORT', 'NONFINITE_METRIC', 'CAUSAL_SEPARATOR_PARTIAL_ROUTE_OR_SPEED_DEPENDENT')
  partial = any(x['status'] in incomplete for x in states.values())
  return {
    'context': 'CAUSAL_CONTEXT_RECOVERED_PARTIAL' if partial and not admitted else 'CAUSAL_CONTEXT_RECOVERED',
    'verdict': 'CAUSAL_HYBRID_REVIEW_POSSIBLE' if admitted else
               'CAUSAL_CONTEXT_RECOVERED_PARTIAL' if partial else 'NO_PREDECLARED_SINGLE_CONDITION_SEPARATOR',
    'conditions': states, 'strict_pass_conditions': admitted,
    'track': 'REVIEW_ONLY' if admitted else 'NOT_CLOSED_PARTIAL_OR_UNAVAILABLE_EVIDENCE' if partial else
             'CURRENT_ARX1_FIR25_PLUS_PREDECLARED_SINGLE_CONDITION_TRACK_CLOSED',
    'model_admission': 'NO_MODEL_ADMITTED_FOR_FUTURE_HOLDOUT',
  }


def aggregate(rows, name, branch):
  tables = [x['conditions'][name]['branches'][branch] for x in rows]
  if len(tables) != 2:
    raise ValueError('EXACT_TWO_ROUTE_EQUAL_AGGREGATION')
  result = {'route_count': 2, 'equal_route_fraction': sum(x['fraction'] for x in tables) / 2,
            'support_by_route': [x['count'] for x in tables], 'interpretation': 'EQUAL_ROUTE_METRIC_MEANS_NOT_POOLED_QUANTILES'}
  for side in ('arx', 'hold_last'):
    result[side] = {k: sum(x[side][k] for x in tables) / 2 if all(x[side][k] is not None for x in tables) else None
                    for k in ('RMSE', 'MAE', 'MEDIAN_ABS', 'P95_ABS', 'BIAS', 'CORRELATION')}
  return result
