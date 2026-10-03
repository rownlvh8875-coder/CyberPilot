import importlib
import math
import unittest
from dataclasses import replace

from openpilot.tools.cyber_autotune.contracts import compute_metrics_v2
from openpilot.tools.cyber_autotune.tests.test_contracts import binding, contracts_module, metric_input


def preflight_module():
  try:
    return importlib.import_module('openpilot.tools.cyber_autotune.preflight')
  except ModuleNotFoundError as exc:
    raise AssertionError('STEP 8.2 fail-closed preflight API is not implemented') from exc


def change_metric(batch, name, **changes):
  return replace(batch, metrics=tuple(replace(item, **changes) if item.name == name else item for item in batch.metrics))


def policy_and_coverage(p):
  # Synthetic counts ONLY: no claim that this single window supplies corpus coverage.
  names = ('straight', 'left_curve', 'right_curve', 'gentle_curve', 'tight_curve',
           'low_speed', 'medium_speed', 'high_speed', 'entry', 'apex', 'exit',
           'lane_change', 'driver_override', 'steering_release', 'reengagement', 'saturation')
  policy = p.CoveragePolicy('1' * 64, tuple((name, 1) for name in names))
  return policy, dict.fromkeys(names, 1)


class TestMetricGate(unittest.TestCase):
  def setUp(self):
    self.p = preflight_module()
    self.baseline = compute_metrics_v2(metric_input(), binding(contracts_module()))
    self.policy, self.coverage = policy_and_coverage(self.p)

  def gate(self, candidate, baseline=None, baseline_coverage=None, candidate_coverage=None):
    return self.p.check_metric_pair(
      self.baseline if baseline is None else baseline, candidate, self.policy,
      self.coverage if baseline_coverage is None else baseline_coverage,
      self.coverage if candidate_coverage is None else candidate_coverage,
    )

  def test_identical_synthetic_metrics_pass_local_gate_without_promotion(self):
    result = self.gate(self.baseline)
    self.assertEqual(result.status, 'LOCAL_NONREGRESSION_PASS')
    self.assertTrue(result.metric_gate_pass)
    self.assertFalse(result.development_gate_pass)
    self.assertFalse(result.runtime_accepted)
    self.assertIn('torque_saturation_ratio:signed_mean', result.exact_zero_pairs)

  def test_path_only_regression_cannot_be_offset_by_smoothness(self):
    candidate = change_metric(self.baseline, 'lateral_path_error', rmse=.2)
    candidate = change_metric(candidate, 'steering_command_derivative', rmse=.9)
    result = self.gate(candidate)
    self.assertEqual(result.status, 'REJECTED')
    self.assertIn('REGRESSION:lateral_path_error:rmse', result.reasons)

  def test_missing_primary_reference_blocks_even_identical_arms(self):
    data = replace(metric_input(), lane_center_offset_m=None)
    batch = compute_metrics_v2(data, self.baseline.contract)
    self.assertEqual(self.gate(batch, baseline=batch).status, 'BLOCKED')
    self.assertIn('PRIMARY_METRIC_UNAVAILABLE', self.gate(batch, baseline=batch).reasons)

  def test_dependent_lane_source_cannot_be_relabelled_as_center_truth(self):
    data = metric_input()
    data = replace(data, lane_center_offset_m=replace(data.lane_center_offset_m, source='plant_path'))
    batch = compute_metrics_v2(data, self.baseline.contract)
    self.assertIn('PRIMARY_METRIC_UNAVAILABLE', self.gate(batch, baseline=batch).reasons)

  def test_missing_empty_and_noninteger_coverage_block(self):
    for counts in ({}, dict.fromkeys(self.coverage, 0), {**self.coverage, 'right_curve': True},
                   {**self.coverage, 'right_curve': 1.5}, {**self.coverage, 'high_speed': math.nan}):
      with self.subTest(counts=counts):
        self.assertEqual(self.gate(self.baseline, candidate_coverage=counts).status, 'BLOCKED')

  def test_coverage_policy_cannot_omit_regression_conditions(self):
    for requirements in ((), (('straight', 1),), tuple((name, 0) for name in self.coverage)):
      with self.subTest(requirements=requirements), self.assertRaises(ValueError):
        replace(self.policy, minimum_counts=requirements)

  def test_mask_counts_must_match_between_arms(self):
    result = self.gate(self.baseline, candidate_coverage={**self.coverage, 'right_curve': 2})
    self.assertEqual(result.status, 'BLOCKED')

  def test_nonfinite_and_bool_metric_values_block(self):
    for value in (math.nan, math.inf, -math.inf, True, None):
      with self.subTest(value=value):
        candidate = change_metric(self.baseline, 'lateral_path_error', rmse=value)
        self.assertEqual(self.gate(candidate).status, 'BLOCKED')

  def test_missing_wrong_unit_invalid_or_empty_metric_blocks(self):
    for name in ('lateral_path_error', 'steering_jerk', 'lane_edge_minimum_margin'):
      without = replace(self.baseline, metrics=tuple(item for item in self.baseline.metrics if item.name != name))
      self.assertEqual(self.gate(without).status, 'BLOCKED')
      for changes in ({'unit': 'Nm'}, {'count': 0}, {'count': True}, {'valid': False}, {'valid': 1}):
        with self.subTest(name=name, changes=changes):
          self.assertEqual(self.gate(change_metric(self.baseline, name, **changes)).status, 'BLOCKED')

  def test_right_curve_worsening_cannot_be_hidden_by_left_improvement(self):
    candidate = change_metric(self.baseline, 'left_curve_lane_center_error', rmse=.05)
    candidate = change_metric(candidate, 'right_curve_lane_center_error', rmse=.15)
    self.assertEqual(self.gate(candidate).status, 'REJECTED')

  def test_edge_and_saturation_have_correct_directions(self):
    for name, value in (('lane_edge_minimum_margin', .9), ('lane_edge_minimum_margin', -.1), ('torque_saturation_ratio', .1)):
      with self.subTest(name=name, value=value):
        candidate = change_metric(self.baseline, name, signed_mean=value)
        self.assertEqual(self.gate(candidate).status, 'REJECTED')

  def test_zero_to_positive_has_no_implicit_tolerance(self):
    candidate = change_metric(self.baseline, 'torque_saturation_ratio', signed_mean=1e-15)
    self.assertEqual(self.gate(candidate).status, 'REJECTED')

  def test_contract_identity_or_alignment_mismatch_blocks(self):
    for changes in ({'configuration_sha256': '9' * 64}, {'alignment_delay_s': .01},
                    {'mask_sha256': '8' * 64}, {'reset_policy_sha256': '7' * 64},
                    {'reversal_deadband_ratio_per_s': .1},
                    {'command': replace(self.baseline.contract.command, steer_max=409)}):
      with self.subTest(changes=changes):
        candidate = replace(self.baseline, contract=replace(self.baseline.contract, **changes))
        self.assertEqual(self.gate(candidate).status, 'BLOCKED')

  def test_entry_regression_cannot_hide_behind_exit_improvement(self):
    data = metric_input()
    baseline = compute_metrics_v2(replace(data, actual_curvature_1pm=replace(
      data.actual_curvature_1pm, values=(0., 0., 0., 0., .01, 0., 0., 0.),
    )), self.baseline.contract)
    candidate = compute_metrics_v2(replace(data, actual_curvature_1pm=replace(
      data.actual_curvature_1pm, values=(0., -.01, 0., 0., 0., 0., 0., 0.),
    )), self.baseline.contract)
    b_metrics, c_metrics = ({item.name: item for item in batch.metrics} for batch in (baseline, candidate))
    self.assertEqual(b_metrics['declared_delay_phase_residual'].rmse, c_metrics['declared_delay_phase_residual'].rmse)
    self.assertEqual(b_metrics['declared_delay_phase_residual_entry'].maximum_abs, .01)
    self.assertEqual(c_metrics['declared_delay_phase_residual_entry'].maximum_abs, .02)
    result = self.gate(candidate, baseline=baseline)
    self.assertEqual(result.status, 'REJECTED')
    self.assertIn('REGRESSION:declared_delay_phase_residual_entry:maximum_abs', result.reasons)

  def test_required_phase_absence_is_blocked(self):
    for phase in ('straight', 'entry', 'apex', 'exit'):
      name = f'declared_delay_phase_residual_{phase}'
      for batch in (
        replace(self.baseline, metrics=tuple(item for item in self.baseline.metrics if item.name != name)),
        change_metric(self.baseline, name, count=0),
      ):
        with self.subTest(phase=phase):
          self.assertEqual(self.gate(batch, baseline=batch).status, 'BLOCKED')

  def test_uncompared_numeric_fields_and_impossible_ratios_block(self):
    for name, changes in (
      ('lane_center_offset', {'signed_mean': math.nan}),
      ('torque_saturation_ratio', {'signed_mean': 2.}),
      ('steering_jerk', {'signed_mean': math.inf}),
      ('lane_edge_minimum_margin', {'rmse': -1.}),
      ('driver_intervention_count', {'signed_mean': .5}),
    ):
      with self.subTest(name=name, changes=changes):
        batch = change_metric(self.baseline, name, **changes)
        self.assertEqual(self.gate(batch, baseline=batch).status, 'BLOCKED')

  def test_huge_metric_integer_returns_blocked_not_exception(self):
    candidate = change_metric(self.baseline, 'lateral_path_error', rmse=10 ** 1000)
    self.assertEqual(self.gate(candidate).status, 'BLOCKED')


class TestReadiness(unittest.TestCase):
  def setUp(self):
    self.p = preflight_module()
    self.review = self.p.ParameterReview(
      name='lat_accel_factor', unit='m/s^2/normalized_command', owner='torqued',
      stage='torque_from_lateral_accel', source_sha256='a' * 64, configuration_sha256='b' * 64,
      baseline_value=2., minimum=1., maximum=3., step=.1, max_rate_per_s=.1,
      minimum_confidence=.95, review_sha256='c' * 64,
    )

  def ready(self, review):
    return self.p.check_readiness(review, expected_source_sha256='a' * 64, expected_configuration_sha256='b' * 64)

  def test_local_review_checks_never_enable_search_or_runtime(self):
    result = self.ready(self.review)
    self.assertTrue(result.contracts_ready)
    self.assertFalse(result.offline_evaluable)
    self.assertFalse(result.candidate_generation_allowed)
    self.assertFalse(result.runtime_accepted)
    self.assertIn('EVIDENCE_VALIDATION_PENDING', result.blockers)

  def test_unreviewed_bounds_rate_or_confidence_block(self):
    for name in ('minimum', 'maximum', 'step', 'max_rate_per_s', 'minimum_confidence', 'review_sha256'):
      with self.subTest(name=name):
        result = self.ready(replace(self.review, **{name: None}))
        self.assertFalse(result.contracts_ready)
        self.assertIn('NO_REVIEWED_SEARCH_SPACE', result.blockers)

  def test_invalid_numeric_review_blocks(self):
    for change in ({'minimum': math.nan}, {'maximum': math.inf}, {'step': True}, {'step': 0.},
                   {'max_rate_per_s': 0.}, {'minimum_confidence': False}, {'minimum_confidence': 1.1},
                   {'minimum': 4.}, {'baseline_value': 4.}, {'step': 5.}, {'minimum': 0.}):
      with self.subTest(change=change):
        self.assertFalse(self.ready(replace(self.review, **change)).contracts_ready)

  def test_source_and_configuration_epoch_mismatch_block(self):
    for change in ({'source_sha256': 'd' * 64}, {'configuration_sha256': 'e' * 64}, {'owner': 'user_preference'},
                   {'stage': 'actuator'}, {'review_sha256': ''}):
      with self.subTest(change=change):
        self.assertFalse(self.ready(replace(self.review, **change)).contracts_ready)

  def test_legacy_units_unknown_and_safety_parameters_block(self):
    for change in ({'unit': 'm/s^2/Nm'}, {'name': 'STEER_MAX'}, {'name': 'lane_offset'},
                   {'name': 'longitudinal_gain'}, {'name': 'driver_override'}):
      with self.subTest(change=change):
        self.assertFalse(self.ready(replace(self.review, **change)).contracts_ready)

  def test_huge_review_integer_returns_blocked_not_exception(self):
    self.assertFalse(self.ready(replace(self.review, maximum=10 ** 1000)).contracts_ready)


if __name__ == '__main__':
  unittest.main()
