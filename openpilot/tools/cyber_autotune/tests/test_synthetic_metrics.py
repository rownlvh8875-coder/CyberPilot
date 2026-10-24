import math
import unittest
from copy import deepcopy


def lateral_trace():
  return tuple({'time_s': i * .1, 'lateral_error_m': e, 'heading_error_rad': e * .1,
                'desired_curvature_1pm': e * .2, 'actual_curvature_1pm': e * .1,
                'speed_mps': 10., 'requested_command': c, 'applied_command': c / 2,
                'steering_angle_deg': float(i ** 3), 'saturated': i == 1, 'rate_limited': i in (1, 2),
                'desired_steering_angle_deg': 0.,
                'active': True, 'steering_pressed': False, 'lane_half_width_m': 1.8, 'vehicle_half_width_m': .9}
               for i, (e, c) in enumerate(zip((0., 1., -1., 0.), (0., 1., 0., -1.), strict=True)))


def long_trace():
  return tuple({'time_s': i * .1, 'speed_mps': 2., 'accel_mps2': -1. + i * .5,
                'target_accel_mps2': -1., 'requested_accel_mps2': -1.,
                'lead_available': True, 'lead_distance_m': 10. - i, 'lead_speed_mps': 1.,
                'desired_distance_m': 10., 'position_m': float(i), 'stop_target_m': 2.,
                'should_stop': True, 'stop_required': True, 'target_speed_mps': 0., 'active': True, 'saturated': False}
               for i in range(4))


class TestSyntheticMetrics(unittest.TestCase):
  def test_lateral_hand_calculated_metrics_and_units(self):
    from openpilot.tools.cyber_autotune.synthetic_metrics import lateral_metrics
    result = lateral_metrics(lateral_trace(), .1)
    self.assertAlmostEqual(result['center_rms_m'], math.sqrt(.5))
    self.assertEqual(result['center_p95_abs_m'], 1.)
    self.assertEqual(result['center_max_abs_m'], 1.)
    self.assertAlmostEqual(result['lane_edge_minimum_margin_m'], -.1)
    self.assertAlmostEqual(result['steering_jerk_rms_deg_s3'], 6000.)
    self.assertEqual(result['command_derivative_rms_per_s'], 10.)
    self.assertEqual(result['saturation_ratio'], .25)
    self.assertAlmostEqual(result['rate_limited_duration_s'], .2)
    self.assertEqual(result['command_zero_crossings'], 1)
    self.assertEqual(result['command_oscillation_pair_count'], 0)
    self.assertIsNone(result['lane_loss_recovery_s'])
    self.assertEqual(result['curve_inside_bias_m'], 1.)
    self.assertAlmostEqual(result['steering_tracking_rms_deg'], math.sqrt(794. / 4))
    self.assertEqual(result['left_right_rms_asymmetry_m'], 0.)
    self.assertIsNone(result['override_recovery_s'])
    self.assertEqual(result['truth_scope'], 'GENERIC_SYNTHETIC_ONLY')
    self.assertFalse(result['real_vehicle_verified'])

  def test_longitudinal_hand_calculated_metrics(self):
    from openpilot.tools.cyber_autotune.synthetic_metrics import longitudinal_metrics
    result = longitudinal_metrics(long_trace(), .1)
    self.assertEqual(result['minimum_ttc_s'], 7.)
    self.assertEqual(result['maximum_deceleration_mps2'], 1.)
    self.assertAlmostEqual(result['acceleration_tracking_rms_mps2'], math.sqrt(.875))
    self.assertAlmostEqual(result['actual_jerk_rms_mps3'], 5.)
    self.assertEqual(result['command_jerk_rms_mps3'], 0.)
    self.assertAlmostEqual(result['actual_jerk_p95_abs_mps3'], 5.)
    self.assertAlmostEqual(result['actual_jerk_max_abs_mps3'], 5.)
    self.assertEqual(result['false_stop_duration_s'], 0.)
    self.assertIsNone(result['cut_in_peak_deceleration_mps2'])
    self.assertEqual(result['braking_overshoot_mps2'], 0.)
    self.assertEqual(result['stopping_overshoot_m'], 1.)
    self.assertIsNone(result['stopping_error_m'], 'not stopped; missing measurement is not zero')
    self.assertIsNone(result['restart_delay_s'])
    self.assertFalse(result['vehicle_activation_allowed'])

  def test_no_lead_or_curve_produces_null_not_perfect_scores(self):
    from openpilot.tools.cyber_autotune.synthetic_metrics import lateral_metrics, longitudinal_metrics
    rows = deepcopy(lateral_trace())
    for row in rows:
      row['desired_curvature_1pm'] = 0.
    lateral = lateral_metrics(rows, .1)
    self.assertIsNone(lateral['left_curve_rms_m'])
    self.assertIsNone(lateral['right_curve_rms_m'])
    rows = deepcopy(long_trace())
    for row in rows:
      row['lead_available'] = False
    self.assertIsNone(longitudinal_metrics(rows, .1)['minimum_ttc_s'])

  def test_time_and_value_faults_reject_without_partial_metrics(self):
    from openpilot.tools.cyber_autotune.synthetic_metrics import lateral_metrics, longitudinal_metrics
    for function, make_trace, field in ((lateral_metrics, lateral_trace, 'lateral_error_m'),
                                       (longitudinal_metrics, long_trace, 'accel_mps2')):
      for value in (float('nan'), float('inf'), True, None):
        rows = deepcopy(make_trace())
        rows[2][field] = value
        with self.subTest(function=function.__name__, value=value), self.assertRaises(ValueError):
          function(rows, .1)
      for time in (.1, .4, float('nan')):
        rows = deepcopy(make_trace())
        rows[2]['time_s'] = time
        with self.assertRaises(ValueError):
          function(rows, .1)
      for rows in ((), make_trace()[:3]):
        with self.assertRaises(ValueError):
          function(rows, .1)
      with self.assertRaises(ValueError):
        function(make_trace(), 0.)

  def test_aggregate_bytes_repeat_and_inputs_are_immutable(self):
    from openpilot.tools.cyber_autotune.native_protocol import canonical
    from openpilot.tools.cyber_autotune.synthetic_metrics import lateral_metrics, longitudinal_metrics
    for function, rows in ((lateral_metrics, lateral_trace()), (longitudinal_metrics, long_trace())):
      before = deepcopy(rows)
      a = canonical(function(rows, .1))
      b = canonical(function(rows, .1))
      self.assertEqual(a, b)
      self.assertEqual(rows, before)

  def test_recovery_does_not_cross_new_override_or_stop_episode(self):
    from openpilot.tools.cyber_autotune.synthetic_metrics import lateral_metrics, longitudinal_metrics
    rows = deepcopy(lateral_trace())
    rows[0]['steering_pressed'] = rows[2]['steering_pressed'] = True
    # First release never recovered before next intervention. Final zero-error
    # frame belongs to a different episode and cannot rescue the earlier one.
    result = lateral_metrics(rows, .1)
    self.assertIsNone(result['override_recovery_s'])
    self.assertEqual(result['unresolved_recoveries'], 1)
    rows = deepcopy(long_trace())
    for i, row in enumerate(rows):
      row['should_stop'] = i in (0, 2)
      row['speed_mps'] = 1. if i == 3 else 0.
    result = longitudinal_metrics(rows, .1)
    self.assertIsNone(result['restart_delay_s'])
    self.assertEqual(result['unresolved_restarts'], 1)

  def test_cut_in_response_latency_and_absence_are_distinct(self):
    from openpilot.tools.cyber_autotune.synthetic_metrics import longitudinal_metrics
    rows = deepcopy(long_trace())
    for i, row in enumerate(rows):
      row['lead_available'] = i >= 1
      row['requested_accel_mps2'] = -1. if i >= 2 else 0.
    self.assertAlmostEqual(longitudinal_metrics(rows, .1)['cut_in_response_s'], .1)
    for row in rows:
      row['requested_accel_mps2'] = 0.
    result = longitudinal_metrics(rows, .1)
    self.assertIsNone(result['cut_in_response_s'])
    self.assertEqual(result['unresolved_cut_ins'], 1)

  def test_false_stop_truth_is_independent_of_supplied_stop_demand(self):
    from openpilot.tools.cyber_autotune.synthetic_metrics import longitudinal_metrics
    rows = deepcopy(long_trace())
    for row in rows:
      row.update(stop_required=False, speed_mps=0., target_speed_mps=2.)
    result = longitudinal_metrics(rows, .1)
    self.assertEqual(result['false_stop_frames'], 4)
    self.assertEqual(result['false_braking_frames'], 4)

  def test_unresolved_later_stop_cannot_inherit_earlier_success(self):
    from openpilot.tools.cyber_autotune.synthetic_metrics import longitudinal_metrics
    rows = deepcopy(long_trace())
    rows[0].update(speed_mps=0., position_m=2.)
    rows[1].update(should_stop=False, stop_required=False)
    result = longitudinal_metrics(rows, .1)
    self.assertEqual(result['stop_episode_count'], 2)
    self.assertEqual(result['unresolved_stops'], 1)
    self.assertIsNone(result['stopping_error_m'])

  def test_negative_physical_domains_reject_but_contact_gap_is_supported(self):
    from openpilot.tools.cyber_autotune.synthetic_metrics import longitudinal_metrics
    for field in ('lead_speed_mps', 'desired_distance_m', 'target_speed_mps'):
      rows = deepcopy(long_trace())
      rows[1][field] = -1.
      with self.subTest(field=field), self.assertRaises(ValueError):
        longitudinal_metrics(rows, .1)
    rows = deepcopy(long_trace())
    rows[1]['lead_distance_m'] = -1.
    self.assertEqual(longitudinal_metrics(rows, .1)['minimum_ttc_s'], 0.)

  def test_required_stop_cannot_disappear_when_demand_or_target_is_missing(self):
    from openpilot.tools.cyber_autotune.synthetic_metrics import longitudinal_metrics
    rows = deepcopy(long_trace())
    for row in rows:
      row['should_stop'] = False
    result = longitudinal_metrics(rows, .1)
    self.assertEqual(result['stop_episode_count'], 1)
    self.assertEqual(result['unresolved_stops'], 1)
    rows[1]['should_stop'] = True
    self.assertEqual(longitudinal_metrics(rows, .1)['stop_episode_count'], 1)
    rows[1]['stop_target_m'] = None
    with self.assertRaises(ValueError):
      longitudinal_metrics(rows, .1)
