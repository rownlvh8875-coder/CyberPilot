"""Source containment and descriptive feedback interaction; not a stability proof."""

import math

from openpilot.tools.cyber_autotune import trajectory_v0_metrics as base
from openpilot.tools.cyber_autotune.smoothness_closed_loop_policy import load as policy
from openpilot.tools.cyber_autotune.trajectory_v0_screen import PLANT

EXOGENOUS = ('desired_curvature_1pm', 'speed_mps', 'roll_rad', 'active', 'steering_pressed', 'safety_limited', 'curvature_limited')


def delta(current, reference):
  return None if current is None or reference is None else current - reference


def up(x):
  return math.nextafter(x, math.inf)


def containment(rows):
  k = w = heading = path = 0.
  margins = []
  for r in rows:
    if any(not math.isfinite(r[key]) for key in ('requested', 'applied', 'curvature', 'yaw_rate', 'heading', 'pose_x', 'pose_y')):
      raise ValueError('NONFINITE_FINITE_HORIZON_RESULT')
    v, roll = r['input']['speed_mps'], r['input']['roll_rad']
    old_k = k
    forcing = up(abs(PLANT.curvature_intercept_1pm) + up(abs(PLANT.command_gain_1pm) * PLANT.command_limit)
                 + up(abs(PLANT.command_speed_gain_s_per_m2) * PLANT.command_limit * abs(v))
                 + up(abs(PLANT.command_inv_speed_gain_per_s) * PLANT.command_limit / abs(v))
                 + up(abs(PLANT.roll_gain_1pm_per_rad) * abs(roll)))
    k = up(up(abs(PLANT.curvature_ar) * old_k) + forcing)
    w = up(up(abs(v) * k) + up(abs(PLANT.yaw_ar) * up(w + up(abs(v) * old_k))) + abs(PLANT.yaw_bias_rad_s))
    heading = up(heading + up(w * PLANT.dt_s))
    path = up(path + up(abs(v) * PLANT.dt_s))
    observed = [abs(r[key]) for key in ('curvature', 'yaw_rate', 'heading', 'pose_x', 'pose_y')]
    bounds = [k, w, heading, path, path]
    if any(x > b for x, b in zip(observed, bounds, strict=True)):
      raise ValueError('SOURCE_DERIVED_CONTAINMENT_VIOLATION')
    margins.append(min(b - x for x, b in zip(observed, bounds, strict=True)))
  return {'all_within_source_envelope': True, 'valid': len(rows), 'total': len(rows), 'unavailable': 0,
          'last_bounds': {'curvature_1pm': k, 'yaw_rate_rad_s': w, 'heading_rad': heading, 'abs_pose_coordinate_m': path},
          'minimum_containment_margin': min(margins) if margins else None,
          'scope': 'INPUT_BOUNDED_PLANT_CONTAINMENT_ONLY_NOT_CLOSED_LOOP_CONVERGENCE', 'stability_proof': False}


def stat(values):
  return {'rms': math.sqrt(math.fsum(v * v for v in values) / len(values)) if values else None,
          'absolute_peak': max(map(abs, values)) if values else None, 'support': len(values)}


def equivalent_growth(parts, key):
  if len(parts) < 2 or any(not p for p in parts):
    return None
  signatures = [[tuple(r['input'][k] for k in EXOGENOUS) for r in p] for p in parts]
  if any(s != signatures[0] for s in signatures[1:]):
    return None
  values = [stat([r[key] for r in p]) for p in parts]
  return all(b['rms'] > a['rms'] and b['absolute_peak'] > a['absolute_peak'] for a, b in zip(values, values[1:], strict=False))


def compact_block(part):
  result = {'support': len(part), 'first_index': part[0]['index'] if part else None,
            'last_index': part[-1]['index'] if part else None}
  for key in ('pre', 'requested', 'applied', 'curvature'):
    result[key] = stat([r[key] for r in part])
  errors = [abs(r['input']['desired_curvature_1pm'] - r['input']['actual_curvature_1pm']) for r in part]
  signs = [r['requested'] > 0. for r in part if r['requested'] != 0.]
  result.update({'tracking': {**base.distribution(errors, len(part)), **stat(errors)},
                 'nonzero_reversals': sum(a != b for a, b in zip(signs, signs[1:], strict=False)),
                 'output_rail_occupancy': sum(abs(r['requested']) == 1. for r in part) / len(part) if part else None,
                 'native_state_first': part[0]['native_state_before'] if part else None,
                 'native_state_last': part[-1]['native_state_after'] if part else None})
  return result


def blocks(rows):
  block_policy = policy()['policy']['blocks']
  parts = [rows[start:stop] for start, stop in block_policy['quarter_ranges_half_open']]
  # Exact last 300 predeclared samples only, never choose a response-dependent tail.
  n = block_policy['constant_tail_block_samples']
  tail = [rows[len(rows) - 3 * n + i * n:len(rows) - 3 * n + (i + 1) * n] for i in range(3)] if len(rows) >= 3 * n else []
  same_demand = bool(tail) and len({tuple(r['input'][k] for k in EXOGENOUS) for p in tail for r in p}) == 1
  return {'quarters': [compact_block(p) for p in parts],
          'quarter_growth': {k: equivalent_growth(parts, k) for k in ('pre', 'requested', 'applied', 'curvature')},
          'constant_demand_tail': [compact_block(p) for p in tail] if same_demand else [],
          'tail_support': {'valid': 3 * n if same_demand else 0, 'total': 3 * n, 'unavailable': 0 if same_demand else 3 * n},
          'tail_growth': {k: equivalent_growth(tail, k) if same_demand else None for k in ('pre', 'requested', 'applied', 'curvature')},
          'interpretation': 'STRICT_INCREASE_FLAG_ONLY; unequal-demand blocks unavailable; bounded oscillations not a stability proof'}


def diagnostics(rows):
  from openpilot.tools.cyber_autotune.smoothness_closed_loop import finite_tree
  finite_tree(rows)
  return {'scope': 'FINITE_HORIZON_CLOSED_LOOP_STABILITY_DIAGNOSTIC', 'stability_proof': False,
          'native_state_all_finite': True, 'plant_containment': containment(rows), 'blocks': blocks(rows),
          'no_asymptotic_convergence_claim': True, 'limit_cycles_may_remain': True}


def pose_alignment(baseline, candidate):
  monotone = all(b['pose_x'] > a['pose_x'] for rows in (baseline, candidate) for a, b in zip(rows, rows[1:], strict=False))
  queries = {}
  for d in (5, 10, 15, 20, 25, 30):
    b, c = base.distance_value(baseline, d, 'pose_y'), base.distance_value(candidate, d, 'pose_y')
    reason = 'NONMONOTONE_FORWARD_COORDINATE' if not monotone else 'DISTANCE_NOT_REACHED' if b is None or c is None else 'AVAILABLE'
    queries[str(d)] = {'delta_pose_y_m': delta(c, b), 'reason': reason, 'valid': int(b is not None and c is not None), 'total': 1}
  # Full common observed x support, no extrapolation, independent of meter-envelope.
  lower = max(rows[0]['pose_x'] for rows in (baseline, candidate))
  upper = min(rows[-1]['pose_x'] for rows in (baseline, candidate))
  support = sorted({r['pose_x'] for rows in (baseline, candidate) for r in rows if lower <= r['pose_x'] <= upper}) if monotone else []
  differences = [base.distance_value(candidate, d, 'pose_y') - base.distance_value(baseline, d, 'pose_y') for d in support]
  return {'queries': queries, 'full_observed_common_x_peak_delta_m': max(map(abs, differences)) if differences else None,
          'full_observed_common_x_support': len(support), 'monotone_forward_coordinate': monotone,
          'meter_envelope_classification': False, 'scope': 'DESCRIPTIVE_PLANT_COUNTERFACTUAL_ONLY'}


def markers(baseline, candidate):
  if len(baseline) != len(candidate):
    raise ValueError('PAIRED_HORIZON_REQUIRED')
  getters = {
    'shaping_first': lambda r: r['requested'] != r['pre'],
    'plant_curvature_pre': lambda r: r['input']['actual_curvature_1pm'],
    'core_requested_torque': lambda r: r['pre'], 'post_governor_torque': lambda r: r['requested'],
    'applied_torque': lambda r: r['applied'], 'plant_curvature_post': lambda r: r['curvature'],
    'tracking_residual_pre': lambda r: r['input']['desired_curvature_1pm'] - r['input']['actual_curvature_1pm'],
    'output_saturation': lambda r: abs(r['requested']) == 1.,
    'pose_y_post': lambda r: r['pose_y'],
  }
  result = {}
  for key, get in getters.items():
    index = next((i for i, (b, c) in enumerate(zip(baseline, candidate, strict=True)) if get(b) != get(c)), None)
    is_pre = key.endswith('_pre')
    is_post = key in ('plant_curvature_post', 'pose_y_post')
    result[key] = None if index is None else {
      'index': index, 'sample_time_s': candidate[index]['input']['time_s'],
      'observed_state_time_s': (index + int(is_post)) * .01 if is_pre or is_post else None,
      'timing': 'PRE_STEP_STATE' if is_pre else 'POST_STEP_STATE' if is_post else 'COMMAND_STEP',
    }
  return result


def scalar_metrics(metrics):
  smooth, trajectory = metrics['smoothness_primary'], metrics['trajectory']
  return {'requested_derivative_p95': smooth['requested']['derivative_abs']['p95'],
          'requested_derivative_rms': smooth['requested']['derivative_rms'],
          'applied_derivative_p95': smooth['applied']['derivative_abs']['p95'],
          'applied_derivative_rms': smooth['applied']['derivative_rms'],
          'curvature_tracking_p95': trajectory['tracking']['p95'],
          'output_saturation_occupancy': smooth['requested']['saturation']['occupancy'],
          'core_input_saturation_occupancy': smooth['pre_governor']['saturation']['occupancy'],
          'governor_limit_occupancy': smooth['governor_limit']['occupancy'],
          'reversals': smooth['requested']['nonzero_sign_reversals'],
          'high_frequency_energy': smooth['requested']['high_frequency_energy'],
          'total_variation': smooth['requested']['total_variation'],
          'heading_absolute_peak_rad': trajectory['heading_abs']['maximum'],
          'pose_y_absolute_peak_m': trajectory['pose_y_abs']['maximum']}


def phase_comparison(closed, replay):
  result = {}
  for phase, c in closed['trajectory']['phases'].items():
    r = replay['trajectory']['phases'][phase]
    result[phase] = {'closed_loop_lag_segments': c['lag_segments'], 'replay_lag_segments': r['lag_segments'],
                    'closed_coverage': c['coverage'], 'replay_coverage': r['coverage'],
                    'tracking_p95_delta': delta(c['tracking']['p95'], r['tracking']['p95'])}
  return result


def compare(baseline, closed, replay, historical_row):
  from openpilot.tools.cyber_autotune.smoothness_v0_metrics import evaluate
  # Only NEW closed-loop traces are evaluated. Historical metric receipt is the input.
  bm, cm = evaluate(baseline), evaluate(closed)
  rm = historical_row['arms']['SG_V0_CANDIDATE']['metrics']
  b, c, r = scalar_metrics(bm), scalar_metrics(cm), scalar_metrics(rm)
  table = {k: {'baseline_closed_loop': b[k], 'sg_frozen_replay': r[k], 'sg_closed_loop': c[k],
               'closed_minus_baseline': delta(c[k], b[k]), 'closed_minus_replay': delta(c[k], r[k])} for k in c}
  return {'metric_table': table, 'first_divergence_vs_baseline': markers(baseline, closed),
          'first_divergence_vs_replay': markers(replay, closed),
          'phase_lag_vs_replay': phase_comparison(cm, rm), 'phase_lag_vs_baseline': phase_comparison(cm, bm),
          'coverage': {'baseline_closed_loop': bm['coverage'], 'sg_frozen_replay': rm['coverage'], 'sg_closed_loop': cm['coverage']},
          'event_transients': {'baseline_closed_loop': bm['smoothness_primary']['event_transients'],
                               'sg_frozen_replay': rm['smoothness_primary']['event_transients'],
                               'sg_closed_loop': cm['smoothness_primary']['event_transients']},
          'same_time_peak_pose_difference_m': {'frozen_replay_vs_baseline':
                                                 historical_row['arms']['SG_V0_CANDIDATE']['effect_vs_baseline']['same_time_peak_absolute_delta']['pose_y'],
                                               'closed_loop_vs_baseline': max(abs(c['pose_y'] - b['pose_y']) for b, c in zip(baseline, closed, strict=True)),
                                               'closed_loop_vs_replay': max(abs(c['pose_y'] - r['pose_y']) for r, c in zip(replay, closed, strict=True))},
          'distance_aligned_pose': {'closed_loop_vs_baseline': pose_alignment(baseline, closed),
                                    'closed_loop_vs_replay': pose_alignment(replay, closed)},
          'closed_signal_chain_exact_baseline': all(
            all(b[k] == c[k] for k in ('pre', 'requested', 'applied', 'curvature', 'yaw_rate', 'heading', 'pose_x', 'pose_y',
                                       'input', 'native_state_after'))
            for b, c in zip(baseline, closed, strict=True)),
          'replay_feedback_to_native': 'NOT_USED_FROZEN_BASELINE_COMMANDS',
          'closed_feedback_to_native': 'OWN_ARM_PRE_STEP_PLANT',
          'phase_lag_divergence': {'timing': 'AGGREGATE_PHASE_ESTIMATOR_NOT_SAMPLE_LOCAL',
                                   'vs_baseline': lag_costs(phase_comparison(cm, bm)),
                                   'vs_replay': lag_costs(phase_comparison(cm, rm))},
          'historical_metric_recalculated': False, 'semantics': ['FROZEN_COMMAND_REPLAY', 'CLOSED_LOOP_FEEDBACK'],
          'physical_performance_claim': False}


def lag_costs(phases):
  costs = []
  unavailable = 0
  for row in phases.values():
    closed, reference = row['closed_loop_lag_segments'], row['replay_lag_segments']
    for i in range(max(len(closed), len(reference))):
      if i >= len(closed) or i >= len(reference):
        unavailable += 1
        continue
      c, r = closed[i], reference[i]
      if c['status'] != 'IDENTIFIED_DESCRIPTIVE' or r['status'] != 'IDENTIFIED_DESCRIPTIVE' or c['pairs'] != r['pairs']:
        unavailable += 1
        continue
      costs.append(abs(c['lag_s']) - abs(r['lag_s']))
  return {'identified_equal_support_deltas_s': costs, 'valid': len(costs), 'unavailable_segments': unavailable,
          'aggregate_not_sample_local': True}


def classify_interaction(row):
  t = row['metric_table']['curvature_tracking_p95']
  baseline, replay, closed = (t[k] for k in ('baseline_closed_loop', 'sg_frozen_replay', 'sg_closed_loop'))
  if any(v is None for v in (baseline, replay, closed)):
    return 'MIXED_OR_UNRESOLVED'
  if row.get('closed_signal_chain_exact_baseline') is True and row['same_time_peak_pose_difference_m']['frozen_replay_vs_baseline'] > 0.:
    return 'FROZEN_REPLAY_ARTIFACT_DOMINANT'
  cb = lag_costs(row['phase_lag_vs_baseline'])['identified_equal_support_deltas_s']
  cr = lag_costs(row['phase_lag_vs_replay'])['identified_equal_support_deltas_s']
  if closed <= baseline and cb and all(v <= 0. for v in cb):
    return 'FEEDBACK_COMPENSATES_GOVERNOR_LAG'
  if closed > replay and cr and all(v >= 0. for v in cr):
    return 'FEEDBACK_AMPLIFIES_GOVERNOR_TRADEOFF'
  if baseline < closed <= replay:
    return 'FEEDBACK_PRESERVES_GOVERNOR_TRADEOFF'
  return 'MIXED_OR_UNRESOLVED'


def standalone_verdict(records):
  affected = []
  contradictory = False
  benefit = False
  smooth_keys = ('requested_derivative_p95', 'requested_derivative_rms', 'applied_derivative_p95', 'applied_derivative_rms',
                 'reversals', 'high_frequency_energy', 'total_variation', 'output_saturation_occupancy')
  for row in records:
    interaction = row['interaction']
    table = interaction['metric_table']
    changed = any(t['closed_minus_baseline'] != 0. for t in table.values() if t['closed_minus_baseline'] is not None)
    affected.append(changed)
    if not changed:
      continue
    for key in (*smooth_keys, 'curvature_tracking_p95'):
      value = table[key]['closed_minus_baseline']
      if value is None or value > 0.:
        contradictory = True
      if key in smooth_keys and value is not None and value < 0.:
        benefit = True
    lag = lag_costs(interaction['phase_lag_vs_baseline'])
    if not lag['valid'] or lag['unavailable_segments'] or any(v > 0. for v in lag['identified_equal_support_deltas_s']):
      contradictory = True
    coverage = interaction['coverage']
    if coverage['sg_closed_loop']['eligible'] < coverage['baseline_closed_loop']['eligible']:
      contradictory = True
  if not any(affected):
    return 'SG_CLOSED_LOOP_STRUCTURAL_PASS'
  return 'SG_CLOSED_LOOP_SCREENING_IMPROVED' if benefit and not contradictory else 'SG_CLOSED_LOOP_TRADEOFF_ONLY'
