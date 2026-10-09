"""Frozen future evaluation catalog. No thresholds, parameter values or execution authority."""

TRAJECTORY_METRICS = (
  ('curvature_tracking_residual', '1/m', 'LOWER_ABSOLUTE', 'median_p95_max', 'active_with_feedback'),
  ('phase_aligned_curvature_response', 's', 'DESCRIPTIVE_LAG', 'per_phase', 'unique_identifiable_lag'),
  ('heading_response', 'rad', 'DESCRIPTIVE_SIGNED', 'distance_and_phase', 'observed_distance_only'),
  ('descriptive_pose_response', 'm', 'DESCRIPTIVE_SIGNED', 'distance_and_phase', 'monotonic_observed_x_only'),
  ('saturation_tracking_loss', '1/m', 'LOWER_ABSOLUTE', 'median_p95_max', 'saturated_and_active'),
  ('sign_consistency', 'count', 'DESCRIPTIVE', 'per_speed_sign_phase', 'causal_response_available'),
)
SMOOTHNESS_METRICS = (
  ('requested_torque_derivative', 'normalized/s', 'LOWER_ABSOLUTE', 'rms_p95_max', 'adjacent_active_samples'),
  ('applied_torque_derivative', 'normalized/s', 'LOWER_ABSOLUTE', 'rms_p95_max', 'adjacent_applied_samples'),
  ('zero_crossing', 'count', 'DESCRIPTIVE', 'per_phase', 'active_nonzero_signs'),
  ('sign_reversal', 'count', 'DESCRIPTIVE', 'per_phase', 'active_nonzero_signs'),
  ('high_frequency_content', 'normalized^2', 'DESCRIPTIVE', 'spectral_band_energy', 'uniform_contiguous_timebase'),
  ('saturation_occupancy', 'fraction', 'DESCRIPTIVE', 'count_over_valid', 'explicit_saturation_observation'),
  ('saturation_transition', 'count', 'DESCRIPTIVE', 'per_phase', 'adjacent_saturation_observations'),
  ('release_reengagement_transient', 'normalized', 'LOWER_ABSOLUTE', 'peak_and_signed_response', 'frozen_event_window'),
  ('steering_pressed_transient', 'normalized', 'LOWER_ABSOLUTE', 'peak_and_signed_response', 'frozen_event_window'),
)
VERDICTS = {
  'TA': ('TRAJECTORY_STRUCTURALLY_VALID', 'TRAJECTORY_EFFECT_PRESENT', 'TRAJECTORY_TRADEOFF_ONLY', 'TRAJECTORY_REJECTED', 'TRAJECTORY_BLOCKED'),
  'SG': ('SMOOTHNESS_STRUCTURALLY_VALID', 'SMOOTHNESS_SCREENING_IMPROVED', 'SMOOTHNESS_TRADEOFF_ONLY', 'SMOOTHNESS_REJECTED', 'SMOOTHNESS_BLOCKED'),
  'COMPOSED': ('COMPOSITION_NOT_AUTHORIZED', 'COMPOSITION_STRUCTURALLY_VALID', 'COMPOSITION_TRADEOFF_ONLY', 'COMPOSITION_REJECTED'),
}


def metrics(role):
  rows = TRAJECTORY_METRICS if role == 'TA' else SMOOTHNESS_METRICS if role == 'SG' else None
  if rows is None:
    raise ValueError('ROLE_REQUIRED')
  return [{**dict(zip(('name', 'unit', 'direction', 'aggregation', 'mask'), row, strict=True)),
           'availability': 'NULL_IF_MISSING_SIGNAL_OR_INSUFFICIENT_SUPPORT; NEVER_ZERO_FILL',
           'phase_handling': 'ENTRY_APEX_EXIT_REVERSAL_RELEASE_REENGAGEMENT_SEPARATE',
           'coverage': 'VALID_TOTAL_UNAVAILABLE_SEPARATE_PER_SCENARIO_AND_PHASE',
           'no_worse': 'PAIRED_BASELINE_COMPARISON_WITH_COVERAGE; NO_CROSS_OBJECTIVE_COMPENSATION',
           'threshold': None, 'threshold_status': 'THRESHOLD_UNJUSTIFIED',
           'execution_definition_status': 'CATALOG_FROZEN_EXECUTION_POLICY_PENDING',
           'pending_before_execution': 'Freeze exact lag estimator, spectral band/window, event window, tolerances and masks before results'}
          for row in rows]


def families():
  # No algorithm selected; parameter names/count/ranges remain explicitly undetermined.
  return [
    {'family': name, 'causal_inputs': inputs, 'state': state, 'reset': 'EXPLICIT_FRESH_INSTANCE_POLICY',
     'expected_mechanism': mechanism, 'potential_failure': failure, 'observability': observation,
     'parameter_count': None, 'search_complexity': 'UNDETERMINED_NO_SEARCH',
     'parameter_ranges': None, 'algorithm_selected': False, 'production_transfer_risk': risk}
    for name, inputs, state, mechanism, failure, observation, risk in (
      ('TA-A', 'present/past desired curvature, speed, roll, feedback', 'causal demand history',
       'delay-aware curvature feedforward', 'causal predictor phase overshoot; duplicate physical delay prohibited',
       'FF intent/limited torque/curvature phase', 'delay estimate and torque conversion mismatch'),
      ('TA-B', 'present/past desired/actual curvature, speed, intervention', 'bounded tracking error state',
       'error dynamics and entry/apex/exit response', 'windup/state leak/incorrect reset',
       'error state/feedback/limits/phase', 'feedback reconstruction and saturation'),
      ('TA-C', 'present/past demand, feedback, speed, roll', 'blend/history state',
       'speed-conditioned feedforward-feedback blend', 'schedule discontinuity/sign inconsistency',
       'FF/FB components and speed transitions', 'profile-specific scheduling and extrapolation'),
    )]
