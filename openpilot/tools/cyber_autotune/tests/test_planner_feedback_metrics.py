"""Hand-calculated metrics and actual native feedback measurement alignment."""
import copy
import importlib.util
import math
import unittest


MODULE = 'openpilot.tools.cyber_autotune.planner_feedback_metrics'


def rows():
  return [{'time_s': i * .1, 'active': True, 'stop_demand': False, 'lead_present': True, 'cut_in_event': False,
           'speed_mps': 1., 'accel_mps2': 0., 'position_m': i * .1, 'lead_gap_m': 5., 'lead_speed_mps': 0.,
           'planner_accel_mps2': 1., 'requested_accel_mps2': i * .1, 'applied_accel_mps2': 0.,
           'response_speed_mps': 1., 'response_accel_mps2': 0.} for i in range(4)]


class TestPlannerFeedbackMetrics(unittest.TestCase):
  def metrics(self, trace, dt=.1):
    # A missing feature is an explicit assertion failure, not an import typo.
    self.assertIsNotNone(importlib.util.find_spec(MODULE), 'planner feedback metric implementation is absent')
    from openpilot.tools.cyber_autotune.planner_feedback_metrics import summarize
    return summarize(trace, dt)

  def test_hand_calculated_tracking_jerk_and_missing_coverage(self):
    result = self.metrics(rows())
    self.assertEqual(result['status'], 'DESCRIPTIVE_ONLY')
    self.assertEqual(result['readiness'], 'NOT_READY')
    self.assertFalse(result['vehicle_activation_allowed'])
    self.assertEqual(result['planner_tracking_rms_mps2'], 1.)
    self.assertAlmostEqual(result['command_jerk_rms_mps3'], 1.)
    self.assertEqual(result['actual_jerk_rms_mps3'], 0.)
    self.assertEqual(result['minimum_lead_gap_m'], 5.)
    self.assertEqual(result['minimum_ttc_s'], 5.)
    self.assertIsNone(result['stopping_error_m'])
    self.assertIsNone(result['restart_delay_s'])
    self.assertIsNone(result['cut_in_response_s'])

  def test_explicit_cut_in_is_not_lost_when_lead_stays_present(self):
    trace = rows()
    trace[1]['cut_in_event'] = True
    trace[1]['lead_gap_m'] = -1.
    trace[2]['requested_accel_mps2'] = -.2
    result = self.metrics(trace)
    self.assertEqual(result['cut_in_event_count'], 1)
    self.assertAlmostEqual(result['cut_in_response_s'], .1)
    self.assertEqual(result['minimum_lead_gap_m'], -1.)
    self.assertEqual(result['minimum_ttc_s'], 0.)
    self.assertEqual(result['nonpositive_gap_frames'], 1)

  def test_stop_and_restart_use_response_end_time_and_keep_unresolved_null(self):
    trace = rows()
    for row in trace:
      row.update(speed_mps=0., response_speed_mps=0.)
    trace[0]['stop_demand'] = trace[1]['stop_demand'] = True
    trace[3]['response_speed_mps'] = .5
    result = self.metrics(trace)
    self.assertEqual(result['stop_episode_count'], 1)
    self.assertEqual(result['stopped_episode_count'], 1)
    self.assertAlmostEqual(result['restart_delay_s'], .2)  # release .2, response end .4
    trace[3]['response_speed_mps'] = .4
    self.assertIsNone(self.metrics(trace)['restart_delay_s'])
    self.assertEqual(self.metrics(trace)['unresolved_restarts'], 1)

  def test_gap_and_response_metrics_do_not_fabricate_coverage(self):
    trace = rows()
    for row in trace:
      row['lead_present'] = False
    result = self.metrics(trace)
    self.assertIsNone(result['minimum_lead_gap_m'])
    self.assertIsNone(result['minimum_ttc_s'])
    self.assertIsNone(result['inactive_max_abs_request_mps2'])
    trace[1]['active'] = False
    self.assertEqual(self.metrics(trace)['inactive_max_abs_request_mps2'], .1)

  def test_releasing_stop_demand_while_still_moving_is_not_a_restart(self):
    trace = rows()
    trace[0]['stop_demand'] = trace[1]['stop_demand'] = True
    result = self.metrics(trace)
    self.assertEqual(result['unresolved_stops'], 1)
    self.assertIsNone(result['restart_delay_s'])
    self.assertEqual(result['release_without_standstill_count'], 1)

  def test_invalid_timebase_state_and_values_are_rejected_without_mutation(self):
    valid = rows()
    original = copy.deepcopy(valid)
    self.metrics(valid)
    self.assertEqual(valid, original)
    for key, value in [('time_s', .5), ('active', 1), ('speed_mps', -1.), ('requested_accel_mps2', math.inf),
                       ('response_speed_mps', True), ('accel_mps2', 1.)]:
      invalid = copy.deepcopy(valid)
      invalid[2][key] = value
      with self.subTest(key=key), self.assertRaises(ValueError):
        self.metrics(invalid)
    with self.assertRaises(ValueError):
      self.metrics(valid, float('nan'))
    with self.assertRaises(ValueError):
      self.metrics(valid[:1])

  def test_native_measurements_align_input_output_and_delay_without_changing_parity(self):
    from openpilot.selfdrive.controls.tests.test_cyber_long_feedback import simulate
    result = simulate('lead_transition')
    self.assertIn('measurements', result)
    measurements = result['measurements']
    self.assertEqual(len(measurements), len(result['trace']))
    for i, (sample, legacy) in enumerate(zip(measurements, result['trace'], strict=True)):
      self.assertEqual(sample['requested_accel_mps2'], legacy[2])
      self.assertEqual(sample['response_speed_mps'], legacy[3])
      self.assertEqual(sample['response_accel_mps2'], legacy[4])
      self.assertEqual(sample['planner_accel_mps2'], legacy[0])
      if i:
        self.assertEqual(sample['speed_mps'], measurements[i - 1]['response_speed_mps'])
      self.assertEqual(sample['applied_accel_mps2'], 0. if i < 3 else measurements[i - 3]['requested_accel_mps2'])
    metrics = self.metrics(measurements, .01)
    self.assertEqual(metrics['cut_in_event_count'], 1)
    self.assertEqual(sum(row['cut_in_event'] for row in measurements), 1)
    self.assertTrue(measurements[199]['lead_present'] and measurements[200]['lead_present'])
    self.assertEqual(metrics, self.metrics(simulate('lead_transition')['measurements'], .01))
