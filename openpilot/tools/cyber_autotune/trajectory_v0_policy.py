"""Pre-execution source/design freeze. No candidate implementation or result input."""
import json

from openpilot.tools.cyber_autotune import candidate_architecture as a
from openpilot.tools.cyber_autotune import candidate_architecture_publication as prior
from openpilot.tools.cyber_autotune.native_protocol import digest
from openpilot.tools.cyber_autotune.resolution_candidate_evidence import immutable_public

BASELINE = 'c2d3923d9a13e3e9942352d8a8114cd3203188e2'
PUBLIC = a.ROOT / 'docs/cyberpilot/changes'
FILES = {
  'policy': 'trajectory-family-selection-policy-v1.json',
  'selection': 'trajectory-family-selection-v1.json',
  'metrics': 'trajectory-metric-execution-policy-v1.json',
  'config': 'trajectory-v0-config-v1.json',
  'scenarios': 'trajectory-development-scenarios-v1.json',
  'matrix': 'candidate-experiment-matrix-ta-v1.json',
}
SOURCES = (
  'openpilot/selfdrive/controls/lib/latcontrol_torque.py',
  'openpilot/common/pid.py',
  'openpilot/selfdrive/controls/lib/latcontrol.py',
  'opendbc_repo/opendbc/car/interfaces.py',
  'opendbc_repo/opendbc/car/vehicle_model.py',
  'opendbc_repo/opendbc/car/lateral.py',
  'opendbc_repo/opendbc/car/hyundai/interface.py',
  'opendbc_repo/opendbc/car/car.capnp',
  'openpilot/tools/cyber_autotune/curvature_yaw_plant.py',
  'openpilot/tools/cyber_autotune/candidate_role_contracts.py',
  'openpilot/tools/cyber_autotune/candidate_architecture.py',
  'openpilot/tools/cyber_autotune/trajectory_v0_policy.py',
)
CRITERIA = (
  'current_past_inputs_only', 'nonduplicate_native_mechanism', 'no_second_physical_delay',
  'causal_phase_tracking_mechanism', 'single_state_reset_owner', 'observable_before_limits',
  'minimal_parameter_state_complexity', 'production_transfer_risk_disclosed',
  'source_injection_feasible', 'not_arbitrary_scale_bias', 'no_lane_model_path_truth',
  'canonical_config_justified_without_results',
)


def seal(row):
  body = {**row, 'source_baseline_sha': BASELINE, 'qualification_allowed': False,
          'reference_promotable': False, 'sealed_reference_allowed': False,
          'vehicle_activation_allowed': False, 'production_authority': False}
  return {**body, 'receipt_sha256': a.hash_object(body)}


def build():
  old = prior.load()
  prior.validate_sources(old)
  sources = {path: digest((a.ROOT / path).read_bytes()) for path in SOURCES}
  policy = seal({'schema': 'TRAJECTORY_FAMILY_SELECTION_POLICY_V1', 'status': 'FROZEN_BEFORE_IMPLEMENTATION',
                 'criteria': CRITERIA, 'families': ['TA-A', 'TA-B', 'TA-C'],
                 'selection_input': 'SOURCE_ONLY_AND_EXISTING_ARCHITECTURE_CONTRACT',
                 'result_input_allowed': False, 'historical_70_input_allowed': False,
                 'one_family_required': True, 'config_justification_required': True,
                 'unjustified_outcome': 'TA_IMPLEMENTATION_BLOCKED', 'source_bindings': sources,
                 'architecture_receipts': {k: v['receipt_sha256'] for k, v in old.items()}})
  selection = seal({'schema': 'TRAJECTORY_FAMILY_SELECTION_V1', 'status': 'TA_B_SELECTED',
                    'selected_family': 'TA-B', 'policy_sha256': policy['receipt_sha256'],
                    'historical_70_used': False, 'candidate_results_used': False,
                    'mechanism': 'ONE_STEP_CLIPPED_ERROR_INNOVATION',
                    'reason': 'Native PID D=0/no error_rate; desired-only jerk lacks measured-error innovation',
                    'counterevidence': ['desired component partly overlaps native jerk', 'feedback noise amplification',
                                        'clipped error loses information', 'saturation and smoothness tradeoffs',
                                        'one-step prediction is a design definition, not identified optimum'],
                    'alternatives': [
                      {'family': 'TA-A', 'status': 'NOT_SELECTED',
                       'reason': 'Native current FF, delayed-demand alignment, desired jerk/friction already present; no specified nonduplicate predictor'},
                      {'family': 'TA-C', 'status': 'NOT_SELECTED',
                       'reason': 'Native P already speed scheduled; no source-canonical new blend; needless attribution/state complexity'}],
                    'injection': 'Instance-local PID subclass; additive acceleration correction inside native update BEFORE antiwindup and total clip',
                    'source_evidence': {
                      'latcontrol_torque.py': 'KP/KI; delayed setpoint error; desired-only jerk; pid.update no error_rate; negative converted return',
                      'pid.py': 'D defaults 0; native p+i+d+f controls antiwindup and clipping',
                      'interfaces.py': 'Existing linear acceleration/torque conversion; factor applied once'},
                    'pre_implementation_independent_review': 'Source-only reviewer supports clipped-error variant; no .02/.15 feedback gain inference'})
  config = seal({'schema': 'TRAJECTORY_V0_CONFIG_V1', 'family': 'TA-B', 'horizon_samples': 1,
                 'dt_s': .01, 'history_length': 1, 'state_fields': ['previous_clipped_error_mps2'],
                 'state_owner': 'TA', 'state_units': 'm/s^2', 'physical_delay_owner': 'PLANT',
                 'state_projection': 'clip(native_delayed_accel_error, native_PID_neg_limit, native_PID_pos_limit)',
                 'correction': 'clip(current_clipped_error - previous_clipped_error, native_PID_neg_limit, native_PID_pos_limit)',
                 'first_sample_correction_mps2': 0., 'bound_semantics': 'INHERITED_OUTPUT_AUTHORITY_PROJECTION_NOT_PHYSICAL_ERROR_BOUND',
                 'horizon_justification': 'Minimal one-step discrete predictor dt*backward_difference; dt cancels exactly',
                 'native_parameters_changed': False, 'native_ff_friction_unchanged': True,
                 'allowed_configs': ['DISABLED', 'CANONICAL_V0', 'TEST_ONLY_SAME_MECHANISM'],
                 'search_allowed': False, 'in_run_mutation_allowed': False,
                 'steering_pressed': 'FRESH_RESET_ON_PRESS; ZERO_INNOVATION_WHILE_PRESSED; NATIVE_OUTPUT_NOT_FORCED_ZERO',
                 'inactive': 'ZERO_NATIVE_OUTPUT; CLEAR_INNOVATION_HISTORY',
                 'reset_events': a.EVENTS, 'reset_policy': a.RESETS,
                 'selection_sha256': selection['receipt_sha256']})
  metrics = seal({'schema': 'TRAJECTORY_METRIC_EXECUTION_POLICY_V1', 'status': 'FROZEN_BEFORE_EXECUTION',
                  'dt_s': .01, 'floating_tolerance': {'repeatability': 'EXACT_CANONICAL_JSON_BYTES', 'time_abs_s': 1e-12},
                  'valid_mask': 'active AND NOT steering_pressed AND finite; event/saturation metrics disclose separate masks',
                  'contiguous': 'adjacent indices and dt=.01; gaps/reset segments never joined for lag/derivative/spectrum',
                  'minimum_support': {'distribution': 1, 'derivative': 2, 'lag_pairs': 3, 'spectrum': 4},
                  'small_sample': 'Always disclose n; n<3 marked SMALL_SUPPORT; empty=null',
                  'lag': {'estimator': 'demeaned_normalized_cross_correlation',
                          'search_samples_inclusive': [-100, 100], 'search_source': 'native 1s demand history / .01s',
                          'sign': 'positive means actual follows desired',
                          'tie_break': 'max correlation then minimum absolute lag then signed lag',
                          'ambiguity': 'exact tied maxima -> ambiguous descriptive value; flat/insufficient=null',
                          'cross_phase_or_reset': False},
                  'phases': 'Use frozen exogenous scenario labels ENTRY/APEX/EXIT/REVERSAL/STRAIGHT; never infer from outputs',
                  'event_windows': {'offset_samples_inclusive': [0, 99], 'overlap': 'events reported separately',
                                    'source': 'native one-second history; never posthoc window selection'},
                  'derivative': 'backward difference / .01 on adjacent eligible samples only',
                  'zero_crossings': 'nonzero sign reversal after removing exact zeros within contiguous eligible segment',
                  'spectrum': {'window': 'Hann on each contiguous eligible segment', 'detrend': 'subtract mean',
                               'band_hz': [1.2, 50.], 'band_source': 'native jerk cutoff to 100Hz Nyquist',
                               'energy': 'sum squared rFFT magnitudes in inclusive band / N^2'},
                  'saturation': 'explicit abs(pre_limit_accel)>native_authority; separate upstream sat timer bool',
                  'distance': {'queries_m': [5., 10., 15., 20., 25., 30.],
                               'coordinate': 'observed pose_x_m, updated-heading Euler plant integration',
                               'interpolation': 'piecewise linear on strictly increasing observed x; no extrapolation',
                               'secondary': 'full observed distance descriptive only; no meter envelope classification'},
                  'coverage': 'valid/total/unavailable for every metric and phase; never zero fill',
                  'aggregation': 'numpy linear quantiles p50/p90/p95/max; separate trajectory/smoothness, no weighted score',
                  'performance_threshold': None, 'threshold_status': 'THRESHOLD_UNJUSTIFIED'})
  # New synthetic design stimuli, not historical70/search data or vehicle geometry.
  rows = []
  for name, speed, magnitude, profile in (
    ('straight', 15., 0., 'STRAIGHT'),
    ('gentle_left', 15., .001, 'TURN'), ('gentle_right', 15., -.001, 'TURN'),
    ('sharp_left', 15., .003, 'TURN'), ('sharp_right', 15., -.003, 'TURN'),
    ('low_speed', 5., .001, 'TURN'), ('medium_speed', 15., .001, 'TURN'),
    ('high_speed', 30., .001, 'TURN'), ('s_reversal', 15., .001, 'REVERSAL'),
    ('driver_events', 15., .001, 'DRIVER'), ('limit_flags', 15., .001, 'LIMITS'),
  ):
    rows.append({'id': name, 'speed_mps': speed, 'curvature_amplitude_1pm': magnitude,
                 'profile': profile, 'samples': 800, 'duration_s': 8., 'dt_s': .01,
                 'feedback': 'NEW_DESCRIPTIVE_CLOSED_LOOP_ACTUAL_CURVATURE_ONLY',
                 'initial_state': 'ZERO_ALL_NATIVE_AND_PLANT_STATE', 'reset': 'FRESH_NATIVE_ON_EACH_FROZEN_TA_EVENT'})
  scenarios = seal({'schema': 'TA_ARCHITECTURE_DEVELOPMENT_SCENARIOS_V1', 'status': 'FROZEN_BEFORE_EXECUTION',
                    'rows': rows, 'input_source': 'NEW_SYNTHETIC_DESIGN_STIMULI_NOT_HISTORICAL70',
                    'rationale': '5/15/30mps cover low/medium/high; .001/.003 1/m are gentle/sharp diagnostic inputs, not calibrated road bounds',
                    'profile': 'zero t<1; linear entry1..2; apex2..4; linear exit4..5; zero after5',
                    'reversal': 'triangle left1..3; triangle right3..5; REVERSAL at3',
                    'driver': 'steeringPressed2<=t<3; release3; inactive5<=t<6; reengagement6',
                    'limits': 'safety_limited2<=t<3; curvature_limited3<=t<4',
                    'forbidden_roles': ['FROZEN_EVALUATION', 'STRESS_DIAGNOSTIC', 'SEARCH'],
                    'result_driven_changes_allowed': False})
  matrix = seal({'schema': 'CANDIDATE_EXPERIMENT_MATRIX_TA_V1',
                 'arms': ['UPSTREAM_BASELINE', 'CYBER_CURRENT_ALIAS', 'TA_V0_CANDIDATE'],
                 'current_is_exact_baseline_alias': True, 'allowed_roles': ['ARCHITECTURE_PROBE', 'DEVELOPMENT_SCREEN'],
                 'repeats': 2, 'sg_enabled': False, 'composition_authorized': False, 'search_authorized': False,
                 'frozen_evaluation_authorized': False, 'candidate_acceptance_authorized': False,
                 'config_sha256': config['receipt_sha256'], 'metric_policy_sha256': metrics['receipt_sha256'],
                 'scenario_policy_sha256': scenarios['receipt_sha256'],
                 'historical_verdicts': dict(a.HISTORY), 'historical_roles': list(a.HISTORICAL_ROLES)})
  return {"policy": policy, "selection": selection, "config": config, "metrics": metrics, "scenarios": scenarios, "matrix": matrix}


def validate(rows):
  if type(rows) is not dict or a.hash_object(rows) != a.hash_object(build()):
    raise ValueError('EXACT_PRE_EXECUTION_POLICY_REQUIRED')
  return rows


def write_new():
  for key, row in build().items():
    immutable_public(PUBLIC / FILES[key], (json.dumps(row, indent=2, sort_keys=True) + '\n').encode())


if __name__ == '__main__':
  write_new()
