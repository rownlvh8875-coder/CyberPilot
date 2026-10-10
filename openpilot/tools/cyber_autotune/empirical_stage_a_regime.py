"""Paired attribution only: no model execution, fitting, quantization or selector."""

import numpy as np
from openpilot.tools.cyber_autotune import empirical_plant_model as metrics
from openpilot.tools.cyber_autotune import empirical_plant_policy as p

PARTITION = ('TARGET_UNCHANGED', 'TARGET_ONE_QUANTUM_CHANGE', 'TARGET_MULTI_QUANTUM_CHANGE')
CAUSAL_BOUNDARY = 'SOURCE_HALF_QUANTUM_PREDICTION_MOVEMENT'
MINIMUM_SUPPORT = 201


def require_quantization(rows):
  if not rows or len({(x['step_deg'], x['offset_deg'], x['sign']) for x in rows}) != 1:
    raise ValueError('QUANTIZATION_CONFLICT')
  row = rows[0]
  if row['step_deg'] <= 0 or row['sign'] not in (-1, 1):
    raise ValueError('QUANTIZATION_CONFLICT')
  return row


def grid_arrays(values, step, offset):
  values = np.asarray(values, dtype=np.float64)
  if not np.isfinite(values).all() or step <= 0:
    raise ValueError('INVALID_GRID_INPUT')
  # Nearest grid is used only to measure residuals/label outcomes, never to
  # replace a target or a prediction. Half ULP is representation tolerance.
  ordinal = np.rint((values - offset) / step)
  nearest = ordinal * step + offset
  f32 = nearest.astype(np.float32)
  upper = np.nextafter(f32, np.float32(np.inf)).astype(float)
  lower = np.nextafter(f32, np.float32(-np.inf)).astype(float)
  tolerance = np.maximum(upper - f32, f32 - lower) / 2
  residual = np.abs(values - nearest)
  compliant = (values == f32.astype(float)) | (residual <= tolerance)
  return ordinal, residual, compliant


def distribution(values):
  if not len(values):
    return {'median': None, 'p95': None, 'max': None}
  return {'median': float(np.median(values)), 'p95': float(np.percentile(values, 95)), 'max': float(np.max(values))}


def grid(values, step, offset):
  _, residual, compliant = grid_arrays(values, step, offset)
  return {
    'total': len(values),
    'exact_grid_count': int(np.sum(residual == 0)),
    'float32_tolerant_grid_count': int(compliant.sum()),
    'off_grid_count': int((~compliant).sum()),
    'residual': distribution(residual),
  }


def availability():
  reason = 'NOT_PRESERVED_IN_V3_SELECTED_DERIVATIVES_NO_RUN_BOUNDARY_MAP_NO_RAW_REOPENING'
  return {
    **{
      k: {'status': 'UNAVAILABLE', 'reason': reason}
      for k in (
        'RAW_COMMAND_CHANGED',
        'RAW_COMMAND_REVERSAL',
        'NORMALIZED_COMMAND_CHANGED',
        'CURRENT_MEASURED_ANGLE_CHANGED',
        'CURRENT_STEERING_RATE_NONZERO',
        'ACTIVE_STEADY',
        'INTERVENTION_BOUNDARY',
        'SATURATION_OR_RAIL_CONTEXT',
      )
    },
    CAUSAL_BOUNDARY: {'status': 'AVAILABLE', 'scope': 'ARCHITECTURE_DIAGNOSTIC_ONLY_ARX_PREDICTION_MINUS_PAST_MEASUREMENT'},
  }


def authorize_gate(name):
  if isinstance(name, str) and name.startswith('TARGET_'):
    raise ValueError('OUTCOME_GATE_FORBIDDEN')
  if name != CAUSAL_BOUNDARY:
    raise ValueError('NO_UNKNOWN_OR_COMBINED_CAUSAL_RULE')
  return 'DIAGNOSTIC_ONLY_NOT_IMPLEMENTATION_AUTHORIZATION'


def causal_masks(array, quantum):
  # Model prediction is the frozen causal ARX value; col 3 is y[k-1].
  # No future target (col 0) participates.
  return np.abs(array[:, 1] - array[:, 3]) >= quantum / 2


def paired(array):
  target, arx, hold = array[:, 0], array[:, 1], array[:, 3]
  ae_a, ae_h = np.abs(arx - target), np.abs(hold - target)
  se_a, se_h = ae_a**2, ae_h**2
  return np.column_stack([ae_a, se_a, ae_h, se_h, ae_a - ae_h, se_a - se_h, target - hold])


def summarize(array, data, mask, total, denominator):
  a = metrics.statistics(array[mask, 1] - array[mask, 0], array[mask, 0])
  h = metrics.statistics(array[mask, 3] - array[mask, 0], array[mask, 0])
  aa, sa, ah, sh, da, ds, _ = data[mask].T
  return {
    'count': int(mask.sum()),
    'fraction': float(mask.sum() / total) if total else None,
    'arx': a,
    'hold_last': h,
    'win_tie_loss': {'win': int((da < 0).sum()), 'tie': int((da == 0).sum()), 'loss': int((da > 0).sum())},
    'absolute_error_total': {'arx': float(aa.sum()), 'hold_last': float(ah.sum())},
    'metric_direction': {
      k: ('UNAVAILABLE' if not mask.any() else 'ARX_LOWER' if a[k] < h[k] else 'ARX_HIGHER' if a[k] > h[k] else 'EXACT_TIE') for k in ('MAE', 'RMSE', 'P95_ABS')
    },
    'squared_error_total': {'arx': float(sa.sum()), 'hold_last': float(sh.sum())},
    'mae_difference_contribution': float(da.sum() / total) if total else None,
    'mse_difference_contribution': float(ds.sum() / total) if total else None,
    'rmse_difference_contribution': float(ds.sum() / total / denominator) if total and denominator else (0.0 if total else None),
  }


def analyze(array, quantum, offset):
  array = np.asarray(array)
  if array.ndim != 2 or array.shape[1] != 5 or not len(array) or not np.isfinite(array).all():
    raise ValueError('EXACT_FINITE_V3_FIVE_COLUMN_PAIRED_SUPPORT_REQUIRED')
  target, arx, hold = array[:, 0], array[:, 1], array[:, 3]
  ti, _, tc = grid_arrays(target, quantum, offset)
  hi, _, hc = grid_arrays(hold, quantum, offset)
  valid_grid = tc & hc
  delta = np.abs(ti - hi)
  unchanged = target == hold
  # Off-grid changes are never silently forced into quantum labels.
  outcome = {
    'TARGET_UNCHANGED': unchanged,
    'TARGET_ONE_QUANTUM_CHANGE': ~unchanged & valid_grid & (delta == 1),
    'TARGET_MULTI_QUANTUM_CHANGE': ~unchanged & valid_grid & (delta >= 2),
    'TARGET_OFF_GRID_OR_SUBQUANTUM_CHANGE': ~unchanged & (~valid_grid | (delta == 0)),
    'TARGET_SIGN_REVERSAL': target * hold < 0,
    'TARGET_LARGE_TRANSITION': ~unchanged & valid_grid & (delta >= 2),
  }
  part = (*PARTITION, 'TARGET_OFF_GRID_OR_SUBQUANTUM_CHANGE')
  if not np.all(np.sum([outcome[k] for k in part], axis=0) == 1):
    raise ValueError('OUTCOME_PARTITION_ERROR')
  data = paired(array)
  denominator = float(np.sqrt(np.mean(data[:, 1])) + np.sqrt(np.mean(data[:, 3])))

  def summarize_mask(mask):
    return summarize(array, data, mask, len(array), denominator)

  movement = causal_masks(array, quantum)
  result = {
    'all': summarize_mask(np.ones(len(array), dtype=bool)),
    'outcome': {k: summarize_mask(mask) for k, mask in outcome.items()},
    'causal': {k: summarize_mask(mask) for k, mask in {'MOVEMENT_AT_LEAST_HALF_QUANTUM': movement, 'MOVEMENT_BELOW_HALF_QUANTUM': ~movement}.items()},
    'target_grid': grid(target, quantum, offset),
    'past_measurement_grid': grid(hold, quantum, offset),
    'arx_prediction_grid': grid(arx, quantum, offset),
    'quantization': {
      'hold_last_exact_hit_count': int((target == hold).sum()),
      'arx_exact_hit_count': int((target == arx).sum()),
      'arx_error_below_half_quantum_count': int((data[:, 0] < quantum / 2).sum()),
      'arx_error_half_through_one_quantum_count': int(((data[:, 0] >= quantum / 2) & (data[:, 0] <= quantum)).sum()),
      'arx_error_above_one_quantum_count': int((data[:, 0] > quantum).sum()),
      'unchanged_small_error_absolute_contribution': float(data[unchanged & (data[:, 0] < quantum / 2), 0].sum() / len(array)),
      'unchanged_other_error_absolute_contribution': float(data[unchanged & (data[:, 0] >= quantum / 2), 0].sum() / len(array)),
    },
    'causal_availability': availability(),
    'unavailable_paired_fields': {
      'current_raw_command_delta': None,
      'current_normalized_command_delta': None,
      'current_measured_angle_delta': None,
      'current_source_steering_rate': None,
      'active_intervention_state': None,
    },
    'quantization_fractions': {
      'hold_last_exact_hit': float(np.mean(target == hold)),
      'arx_exact_hit': float(np.mean(target == arx)),
      'arx_off_grid': float(grid(arx, quantum, offset)['off_grid_count'] / len(array)),
      'arx_error_below_half_quantum': float(np.mean(data[:, 0] < quantum / 2)),
      'arx_error_half_through_one_quantum': float(np.mean((data[:, 0] >= quantum / 2) & (data[:, 0] <= quantum))),
      'arx_error_above_one_quantum': float(np.mean(data[:, 0] > quantum)),
    },
    'partition': list(part),
    'overlapping_diagnostics': ['TARGET_SIGN_REVERSAL', 'TARGET_LARGE_TRANSITION'],
  }
  # Local columns also bind outcome masks and the sole available causal label.
  private = np.column_stack([data, *[outcome[k] for k in outcome], movement])
  return result, private


def aggregate(rows):
  fields = ('mae_difference_contribution', 'mse_difference_contribution', 'rmse_difference_contribution')
  counts = np.array([x['all']['count'] for x in rows])
  return {
    'primary': 'EQUAL_ROUTE',
    'equal_route': {k: float(np.mean([x['all'][k] for x in rows])) for k in fields},
    'sample_weighted_supporting': {k: float(np.average([x['all'][k] for x in rows], weights=counts)) for k in fields},
    'equal_route_fraction': {k: float(np.mean([x['outcome'][k]['fraction'] for x in rows])) for k in rows[0].get('partition', [])},
    'rmse_aggregation': 'MEAN_OF_ROUTE_RMSE_DIFFERENCES_NOT_RMSE_OF_POOLED_ERRORS',
    'regimes': {scope: {name: aggregate_regime([x[scope][name] for x in rows]) for name in rows[0].get(scope, {})} for scope in ('outcome', 'causal')},
  }


def aggregate_regime(groups):
  supported = [g for g in groups if g['count']]
  fields = ('mae_difference_contribution', 'mse_difference_contribution', 'rmse_difference_contribution')
  return {
    'count': sum(g['count'] for g in groups),
    'equal_route_fraction': float(np.mean([g['fraction'] for g in groups])),
    'routes_with_support': len(supported),
    'total_routes': len(groups),
    'equal_route_metrics': {
      name: {metric: float(np.mean([g[name][metric] for g in supported])) if supported else None for metric in ('MAE', 'RMSE', 'P95_ABS')}
      for name in ('arx', 'hold_last')
    },
    'equal_route_contributions': {key: float(np.mean([g[key] for g in groups])) for key in fields},
    'equal_route_win_fraction': float(np.mean([g['win_tie_loss']['win'] / g['count'] for g in supported])) if supported else None,
    'interpretation': 'ARITHMETIC_MEAN_ROUTE_METRICS_P95_NOT_POOLED_QUANTILE_EMPTY_ROUTES_DISCLOSED',
  }


def causal_gate_supported(rows):
  """No condition combination and no searching. Each route/bin must agree."""
  if len(rows) != 6:
    return False
  for row in rows:
    good = row['causal']['MOVEMENT_AT_LEAST_HALF_QUANTUM']
    other = row['causal']['MOVEMENT_BELOW_HALF_QUANTUM']
    if min(good['count'], other['count']) < MINIMUM_SUPPORT:
      return False
    if not all(good['arx'][k] < good['hold_last'][k] for k in ('MAE', 'RMSE', 'P95_ABS')):
      return False
    if not all(other['arx'][k] >= other['hold_last'][k] for k in ('MAE', 'RMSE', 'P95_ABS')):
      return False
  return True


def adjudicate(rows):
  if any(x['target_grid']['off_grid_count'] or x['past_measurement_grid']['off_grid_count'] for x in rows):
    return {'verdict': 'STAGE_A_ATTRIBUTION_BLOCKED_SOURCE_CONFLICT', 'hypotheses': {}, 'family_closed': True}
  consistent = len(rows) == 6 and all(
    x['outcome']['TARGET_UNCHANGED']['mae_difference_contribution'] > 0
    and x['outcome']['TARGET_MULTI_QUANTUM_CHANGE']['mse_difference_contribution'] < 0
    and x['outcome']['TARGET_UNCHANGED']['count'] >= MINIMUM_SUPPORT
    and x['outcome']['TARGET_MULTI_QUANTUM_CHANGE']['count'] >= MINIMUM_SUPPORT
    for x in rows
  )
  # Dominance means greater contribution than the sum of other positive
  # contributions, not an effect-size acceptance threshold.
  h1 = consistent and all(
    x['outcome']['TARGET_UNCHANGED']['mae_difference_contribution']
    > sum(max(0, x['outcome'][k]['mae_difference_contribution']) for k in x['partition'] if k != 'TARGET_UNCHANGED')
    and x['quantization']['unchanged_small_error_absolute_contribution'] > x['quantization']['unchanged_other_error_absolute_contribution']
    for x in rows
  )
  h2 = consistent and all(
    -x['outcome']['TARGET_MULTI_QUANTUM_CHANGE']['mse_difference_contribution']
    > sum(max(0, -x['outcome'][k]['mse_difference_contribution']) for k in x['partition'] if k != 'TARGET_MULTI_QUANTUM_CHANGE')
    for x in rows
  )
  support_complete = len(rows) == 6 and all(
    min(x['outcome']['TARGET_UNCHANGED']['count'], x['outcome']['TARGET_MULTI_QUANTUM_CHANGE']['count']) >= MINIMUM_SUPPORT for x in rows
  )

  def contradictory(scope, metric):
    values = [x['outcome'][scope][metric] for x in rows if x['outcome'][scope]['count']]
    return any(v > 0 for v in values) and any(v < 0 for v in values)

  conflict = contradictory('TARGET_UNCHANGED', 'mae_difference_contribution') or contradictory('TARGET_MULTI_QUANTUM_CHANGE', 'mse_difference_contribution')
  h3 = causal_gate_supported(rows)
  quant_review = h1 and h2 and all(x['arx_prediction_grid']['off_grid_count'] > 0 for x in rows)
  verdict = (
    'QUANTIZATION_AWARE_OBSERVATION_REVIEW_POSSIBLE' if quant_review else 'CAUSAL_HYBRID_REVIEW_POSSIBLE' if h3 else 'STAGE_A_ATTRIBUTION_MIXED_OR_UNRESOLVED'
  )
  return {
    'verdict': verdict,
    'causal_hybrid_review_possible': h3,
    'hypotheses': {'H1': h1, 'H2': h2, 'H3': h3, 'H4': 'UNRESOLVED_MISSING_CAUSAL_FIELDS', 'H5': False if h1 else 'UNRESOLVED_NOT_ESTABLISHED', 'H6': conflict},
    'regime_support_complete': support_complete,
    'family_closed': False,
    'family_status': 'NO_ADMISSIBLE_MODEL_REVIEW_ONLY',
    'limitation': 'A_THROUGH_E_UNAVAILABLE_ABSENCE_OF_CAUSAL_SEPARATOR_NOT_PROVEN',
  }


def architecture_contract(verdict, policy_sha):
  if verdict not in ('QUANTIZATION_AWARE_OBSERVATION_REVIEW_POSSIBLE', 'CAUSAL_HYBRID_REVIEW_POSSIBLE'):
    raise ValueError('NO_SUPPORTED_ARCHITECTURE_REVIEW')
  return p.seal(
    {
      'schema': 'EMPIRICAL_STAGE_A_V4_ARCHITECTURE_CONTRACT_V1',
      'rationale_verdict': verdict,
      'policy_sha256': policy_sha,
      'roles': ['LATENT_DYNAMIC_STATE', 'SOURCE_BOUND_MEASUREMENT_EMISSION', 'EXACT_HOLD_LAST_BASELINE_PATH', 'OPTIONAL_CAUSAL_SELECTOR_REQUIRES_NEW_POLICY'],
      'allowed_inputs': ['CURRENT_AND_PAST_SOURCE_BOUND_COMMAND', 'PAST_MEASURED_STEERING', 'SOURCE_PROFILE', 'TIMEBASE', 'INTERVENTION'],
      'forbidden_inputs': ['NEXT_TARGET', 'FUTURE_COMMAND', 'FUTURE_STEERING_RATE', 'RESIDUAL', 'FOLD_LABEL', 'LANE_MODEL_PATH'],
      'state_ownership': {'latent_state': 'FUTURE_DYNAMIC_CORE', 'emission_state': 'FUTURE_OBSERVATION_LAYER', 'physical_delay': 'FUTURE_PLANT_ONLY'},
      'reset': 'NEW_INSTANCE_AT_ROUTE_SEGMENT_MASK_SPEED_BIN_INTERVENTION_CONFIG_BOUNDARY',
      'quantization_semantics': 'SOURCE_DBC_GRID_AND_FLOAT32_STORAGE_ONLY_NO_PREDICTION_ROUNDING_SELECTED',
      'rounding_rule': 'NOT_SELECTED',
      'half_lsb_hold_rule': 'NOT_SELECTED',
      'latent_update_rule': 'NOT_SELECTED',
      'hybrid_switch': 'NOT_SELECTED',
      'parameter_values': None,
      'actual_algorithm_implemented': False,
      'model_fitted': False,
      'execution_allowed': False,
      'search_allowed': False,
      'future_holdout': 'FUTURE_UNTOUCHED_HOLDOUT_REQUIRED',
      'holdout_opening': 'CLOSED_MISSING_ADMISSIBLE_MODEL',
    }
  )
