import math
import unittest

from openpilot.selfdrive.controls.lib.cyber_lateral.metrics import (
  LateralMetricInput, MetricSeries, compute_lateral_metrics,
)


def series(values, unit, source, times=(0., 1., 2., 3., 4.)):
  return MetricSeries(tuple(times), tuple(values), unit, source)


def metric_input(*, desired=(0., 0., 0., 0., 0.), actual=(0., 0., 0., 0., 0.),
                 cross=(0., 0., 0., 0., 0.), requested=(0., 0., 0., 0., 0.),
                 actual_curvature=(0., 0., 0., 0., 0.), lane=(0., 0., 0., 0., 0.),
                 steering=(0., 0., 0., 0., 0.), saturation=(0., 0., 0., 0., 0.),
                 intervention=(0., 0., 0., 0., 0.), delay=0., lane_source='independent-map',
                 phases=('straight',) * 5, command=None, applied_torque=None,
                 desired_steering=None, edge_margin=None, deadband=0.,
                 times=(0., 1., 2., 3., 4.)):
  return LateralMetricInput(
    desired_path_offset_m=series(desired, 'm', 'model-desired', times),
    actual_path_offset_m=series(actual, 'm', 'vehicle-pose', times),
    cross_track_error_m=series(cross, 'm', 'nearest-station', times),
    requested_curvature_1pm=series(requested, '1/m', 'controller-request', times),
    actual_curvature_1pm=series(actual_curvature, '1/m', 'yaw-rate', times),
    lane_center_offset_m=None if lane is None else series(lane, 'm', lane_source, times),
    steering_angle_deg=series(steering, 'deg', 'eps-angle', times),
    saturation=series(saturation, 'bool', 'controller-limit', times),
    driver_intervention=series(intervention, 'bool', 'car-state', times),
    declared_alignment_delay_s=delay,
    curve_phase_labels=phases,
    steering_command=None if command is None else series(command, 'ratio', 'controller-command', times),
    applied_steering_torque=None if applied_torque is None else series(applied_torque, 'ratio', 'car-output', times),
    desired_steering_angle_deg=None if desired_steering is None else series(desired_steering, 'deg', 'controller-desired-angle', times),
    lane_edge_margin_m=None if edge_margin is None else series(edge_margin, 'm', 'independent-road-edge', times),
    steering_zero_crossing_deadband_ratio_per_s=deadband,
  )


class TestCyberLateralMetricContracts(unittest.TestCase):
  def test_identical_baseline_candidate_has_exact_zero_metrics(self):
    result = compute_lateral_metrics(metric_input())
    for name in ('lateral_path_error', 'cross_track_error', 'curvature_tracking_error',
                 'lane_center_offset', 'inside_outside_bias', 'steering_jerk',
                 'steering_oscillation_residual', 'declared_delay_phase_residual'):
      with self.subTest(metric=name):
        self.assertTrue(result[name].valid)
        self.assertEqual(result[name].rmse, 0.0)
        self.assertEqual(result[name].maximum_abs, 0.0)

  def test_inside_bias_normalizes_left_and_right_curve_sign(self):
    left = compute_lateral_metrics(metric_input(
      requested=(0.1,) * 5, lane=(0.2,) * 5,
    ))['inside_outside_bias']
    right = compute_lateral_metrics(metric_input(
      requested=(-0.1,) * 5, lane=(-0.2,) * 5,
    ))['inside_outside_bias']
    self.assertEqual(left.signed_mean, 0.2)
    self.assertEqual(right.signed_mean, 0.2)

  def test_declared_delay_is_applied_without_searching_candidate_output(self):
    result = compute_lateral_metrics(metric_input(
      requested=(0., 1., 2., 3., 4.),
      actual_curvature=(0., 0., 1., 2., 3.),
      delay=1.,
    ))
    self.assertGreater(result['curvature_tracking_error'].rmse, 0.)
    self.assertEqual(result['declared_delay_phase_residual'].count, 4)
    self.assertEqual(result['declared_delay_phase_residual'].rmse, 0.)

  def test_declared_delay_residual_is_stratified_by_caller_frozen_curve_phase(self):
    result = compute_lateral_metrics(metric_input(
      requested=(0., 1., 2., 3., 4.),
      actual_curvature=(0., 2., 4., 6., 8.),
      phases=('straight', 'entry', 'entry', 'apex', 'exit'),
    ))
    self.assertEqual(result['declared_delay_phase_residual_straight'].count, 1)
    self.assertEqual(result['declared_delay_phase_residual_entry'].count, 2)
    self.assertEqual(result['declared_delay_phase_residual_entry'].signed_mean, 1.5)
    self.assertEqual(result['declared_delay_phase_residual_apex'].signed_mean, 3.)
    self.assertEqual(result['declared_delay_phase_residual_exit'].signed_mean, 4.)

  def test_steering_jerk_is_third_angle_derivative_in_deg_per_second_cubed(self):
    result = compute_lateral_metrics(metric_input(
      steering=(0., 1., 8., 27., 64.),
    ))['steering_jerk']
    self.assertEqual(result.unit, 'deg/s^3')
    self.assertEqual(result.count, 2)
    self.assertEqual(result.signed_mean, 6.)
    self.assertEqual(result.rmse, 6.)

  def test_saturation_duty_and_intervention_edges_are_not_conflated(self):
    result = compute_lateral_metrics(metric_input(
      saturation=(0., 1., 1., 0., 0.),
      intervention=(0., 1., 1., 0., 1.),
    ))
    self.assertEqual(result['saturation_duty'].signed_mean, 0.4)
    self.assertEqual(result['driver_intervention_count'].signed_mean, 2.)
    self.assertEqual(result['driver_intervention_count'].unit, 'events')

  def test_command_torque_derivatives_and_tracking_error_have_explicit_units(self):
    result = compute_lateral_metrics(metric_input(
      steering=(0., 1., 2., 3., 4.),
      desired_steering=(0., 0.5, 1., 1.5, 2.),
      command=(0., 0.1, 0.3, 0.6, 1.),
      applied_torque=(0., 0.05, 0.15, 0.3, 0.5),
    ))
    self.assertEqual(result['steering_command_derivative'].unit, 'ratio/s')
    self.assertEqual(result['steering_command_derivative'].count, 4)
    self.assertAlmostEqual(result['steering_command_derivative'].signed_mean, 0.25)
    self.assertEqual(result['steering_torque_derivative'].unit, 'ratio/s')
    self.assertAlmostEqual(result['steering_torque_derivative'].signed_mean, 0.125)
    self.assertEqual(result['desired_actual_steering_error'].unit, 'deg')
    self.assertEqual(result['desired_actual_steering_error'].maximum_abs, 2.)

  def test_command_reversal_frequency_uses_derivative_deadband(self):
    result = compute_lateral_metrics(metric_input(
      command=(0., 1., 0., -1., 0.),
      deadband=0.5,
    ))
    self.assertEqual(result['steering_zero_crossing_frequency'].unit, 'Hz')
    self.assertEqual(result['steering_zero_crossing_frequency'].signed_mean, 0.25)

  def test_dominant_oscillation_frequency_is_reported_for_periodic_command(self):
    times = tuple(index * 0.25 for index in range(8))
    zeros = (0.,) * len(times)
    periodic = (0., 1., 0., -1., 0., 1., 0., -1.)
    result = compute_lateral_metrics(metric_input(
      desired=zeros, actual=zeros, cross=zeros, requested=zeros,
      actual_curvature=zeros, lane=zeros, steering=zeros, saturation=zeros,
      intervention=zeros, command=periodic, phases=('straight',) * len(times),
      times=times,
    ))
    self.assertTrue(result['steering_oscillation_frequency'].valid)
    self.assertEqual(result['steering_oscillation_frequency'].unit, 'Hz')
    self.assertAlmostEqual(result['steering_oscillation_frequency'].signed_mean, 1.)

  def test_curve_errors_are_split_by_left_and_right_and_edge_margin_is_minimum(self):
    result = compute_lateral_metrics(metric_input(
      requested=(0.1, 0.1, 0., -0.1, -0.1),
      lane=(0.1, 0.3, 0., -0.2, -0.4),
      edge_margin=(1.2, 1.0, 0.9, 0.8, 0.7),
    ))
    self.assertEqual(result['left_curve_lane_center_error'].count, 2)
    self.assertAlmostEqual(result['left_curve_lane_center_error'].signed_mean, 0.2)
    self.assertEqual(result['right_curve_lane_center_error'].count, 2)
    self.assertAlmostEqual(result['right_curve_lane_center_error'].signed_mean, -0.3)
    self.assertEqual(result['lane_edge_minimum_margin'].signed_mean, 0.7)
    self.assertEqual(result['torque_saturation_ratio'].signed_mean, result['saturation_duty'].signed_mean)

  def test_extended_metrics_are_invalid_when_optional_sources_are_missing(self):
    result = compute_lateral_metrics(metric_input())
    for name in ('steering_command_derivative', 'steering_torque_derivative',
                 'desired_actual_steering_error', 'steering_zero_crossing_frequency',
                 'steering_oscillation_frequency', 'lane_edge_minimum_margin'):
      with self.subTest(metric=name):
        self.assertFalse(result[name].valid)
        self.assertEqual(result[name].reason, 'missing_source')

  def test_lane_center_requires_an_independent_reference(self):
    missing = compute_lateral_metrics(metric_input(lane=None))
    self.assertFalse(missing['lane_center_offset'].valid)
    self.assertEqual(missing['lane_center_offset'].reason, 'missing_independent_lane_reference')

    reused = compute_lateral_metrics(metric_input(lane_source='model-desired'))
    self.assertFalse(reused['lane_center_offset'].valid)
    self.assertEqual(reused['inside_outside_bias'].reason, 'missing_independent_lane_reference')

  def test_series_rejects_length_nonfinite_and_nonmonotonic_time(self):
    invalid = (
      ((0., 1.), (0.,), 'length'),
      ((0., 0.), (0., 1.), 'time'),
      ((0., 1.), (0., math.nan), 'finite'),
      ((0., math.inf), (0., 1.), 'finite'),
    )
    for times, values, _reason in invalid:
      with self.subTest(times=times, values=values), self.assertRaises(ValueError):
        MetricSeries(times, values, 'm', 'test')

  def test_input_rejects_misaligned_or_irregular_time_and_invalid_flags(self):
    base = metric_input()
    with self.assertRaises(ValueError):
      LateralMetricInput(
        **{**base.__dict__, 'actual_path_offset_m': series((0.,) * 5, 'm', 'vehicle-pose', (0., 1., 2., 3., 5.))},
      )
    with self.assertRaises(ValueError):
      LateralMetricInput(
        **{**base.__dict__, 'steering_angle_deg': series((0.,) * 5, 'deg', 'eps-angle', (0., 1., 2.1, 3., 4.))},
      )
    with self.assertRaises(ValueError):
      LateralMetricInput(
        **{**base.__dict__, 'saturation': series((0., 2., 0., 0., 0.), 'bool', 'controller-limit')},
      )
    with self.assertRaises(ValueError):
      LateralMetricInput(
        **{**base.__dict__, 'steering_command': series((0.,) * 5, 'Nm', 'wrong-unit')},
      )
    with self.assertRaises(ValueError):
      LateralMetricInput(
        **{**base.__dict__, 'steering_zero_crossing_deadband_ratio_per_s': -0.1},
      )


if __name__ == '__main__':
  unittest.main()
