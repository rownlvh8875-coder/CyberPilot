import unittest


class TestSyntheticNativeV2(unittest.TestCase):
  def run_case(self, name, **kwargs):
    from openpilot.tools.cyber_autotune.synthetic_native_v2 import run_variant
    return run_variant(name, **kwargs)

  def test_native_lateral_runs_and_reports_single_delay_owner(self):
    result = self.run_case('lat_constant_left')
    self.assertEqual(result['status'], 'COMPLETED_SYNTHETIC_ONLY')
    self.assertEqual(result['metrics']['sample_count'], 600)
    self.assertEqual(result['physical_delay_owner'], 'PLANT')
    self.assertFalse(result['controller_delay_queue_present'])
    self.assertEqual(result['controller'], 'LatControlTorque')
    self.assertGreater(result['metrics']['center_rms_m'], 0.)
    self.assertFalse(result['metrics']['runtime_accepted'])

  def test_native_longitudinal_runs_and_observes_false_stop(self):
    result = self.run_case('long_false_stop')
    self.assertEqual(result['status'], 'COMPLETED_SYNTHETIC_ONLY')
    self.assertEqual(result['controller'], 'LongControl')
    self.assertGreater(result['metrics']['false_braking_frames'], 0)
    self.assertGreater(result['metrics']['false_stop_frames'], 0)
    self.assertFalse(result['metrics']['vehicle_write_enabled'])

  def test_identity_and_candidate_have_fresh_deterministic_state(self):
    first = self.run_case('lat_constant_left')
    candidate = self.run_case('lat_constant_left', tune_id='gentle')
    second = self.run_case('lat_constant_left')
    self.assertEqual(first, second)
    self.assertNotEqual(first['metrics']['trace_sha256'], candidate['metrics']['trace_sha256'])
    self.assertNotEqual(first['tune_sha256'], candidate['tune_sha256'])
    self.assertEqual(first['input_sha256'], candidate['input_sha256'])
    self.assertEqual(first['plant_sha256'], candidate['plant_sha256'])
    self.assertEqual(first['base_car_params_sha256'], candidate['base_car_params_sha256'])

  def test_fault_inputs_are_rejected_before_controller_execution(self):
    for case in ('lat_sensor_dropout', 'lat_nonfinite', 'long_stale', 'long_plan_dropout'):
      with self.subTest(case=case):
        result = self.run_case(case)
        self.assertEqual(result['status'], 'REJECTED_INPUT')
        self.assertFalse(result['controller_executed'])
        self.assertIsNone(result['metrics'])
        self.assertFalse(result['promotable_to_vehicle'])

  def test_undeclared_tune_case_or_delay_cannot_run(self):
    for kwargs in ({'case_id': 'unknown'}, {'case_id': 'lat_straight', 'tune_id': 'vehicle_active'},
                   {'case_id': 'lat_straight', 'delay_s': 2.}):
      from openpilot.tools.cyber_autotune.synthetic_native_v2 import run_variant
      with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
        run_variant(**kwargs)

  def test_delay_variants_are_separate_and_repeatable(self):
    fast = self.run_case('long_delay_sweep', delay_s=0.)
    slow = self.run_case('long_delay_sweep', delay_s=.30)
    repeated = self.run_case('long_delay_sweep', delay_s=0.)
    self.assertEqual(fast, repeated)
    self.assertNotEqual(fast['plant_sha256'], slow['plant_sha256'])
    self.assertNotEqual(fast['metrics']['trace_sha256'], slow['metrics']['trace_sha256'])
    self.assertEqual(fast['input_sha256'], slow['input_sha256'])

  def test_changed_catalog_cannot_run_under_frozen_policy(self):
    from dataclasses import replace
    from unittest.mock import patch
    from openpilot.tools.cyber_autotune import synthetic_stress_catalog as module
    from openpilot.tools.cyber_autotune.synthetic_native_v2 import run_variant
    original = module.frames

    def changed(case):
      rows = original(case)
      return (replace(rows[0], curvature=rows[0].curvature + .001), *rows[1:])

    with patch.object(module, 'frames', side_effect=changed), self.assertRaises(ValueError):
      run_variant('lat_constant_left')

  def test_scope_explicitly_excludes_unexercised_perception_inputs(self):
    lateral = self.run_case('lat_lane_loss')
    longitudinal = self.run_case('long_radar_model_disagreement')
    self.assertIn('lane_visible', lateral['unexercised_inputs'])
    self.assertIn('radar_model_disagreement', longitudinal['unexercised_inputs'])
    self.assertFalse(lateral['perception_planner_executed'])
    self.assertFalse(longitudinal['perception_planner_executed'])

  def test_executed_frames_cannot_differ_from_frozen_input(self):
    from dataclasses import replace
    from unittest.mock import patch
    from openpilot.tools.cyber_autotune import synthetic_native_v2 as module
    original = module.frames
    def changed(case):
      rows = original(case)
      return (replace(rows[0], curvature=.009), *rows[1:])
    with patch.object(module, 'frames', side_effect=changed), self.assertRaises(ValueError):
      self.run_case('lat_constant_left')

  def test_feedback_is_inverse_of_native_vehicle_model(self):
    import math
    from opendbc.car.hyundai.interface import CarInterface
    from opendbc.car.hyundai.values import CAR
    from opendbc.car.vehicle_model import VehicleModel
    from openpilot.tools.cyber_autotune.synthetic_native_v2 import feedback_angle_deg
    cp = CarInterface.get_non_essential_params(CAR.HYUNDAI_SANTA_FE_2022)
    model = VehicleModel(cp)
    for speed in (5., 18., 30.):
      for curvature in (-.002, 0., .002):
        with self.subTest(speed=speed, curvature=curvature):
          angle = feedback_angle_deg(model, curvature, speed)
          self.assertAlmostEqual(-model.calc_curvature(math.radians(angle), speed, 0.), curvature, places=12)

  def test_longitudinal_sample_time_and_delay_onset(self):
    from dataclasses import replace
    from opendbc.car.hyundai.interface import CarInterface
    from opendbc.car.hyundai.values import CAR
    from openpilot.tools.cyber_autotune.synthetic_native_v2 import _longitudinal_trace
    from openpilot.tools.cyber_autotune.synthetic_stress_catalog import catalog, frames
    case = next(c for c in catalog() if c.case_id == 'long_delay_sweep')
    rows = tuple(replace(f, supplied_accel_mps2=1.) for f in frames(case))
    cp = CarInterface.get_non_essential_params(CAR.HYUNDAI_SANTA_FE_2022)
    cp.openpilotLongitudinalControl = True
    trace, _ = _longitudinal_trace(case, rows, cp, 1., .03)
    self.assertEqual(trace[0]['interval_start_s'], 0.)
    self.assertAlmostEqual(trace[0]['time_s'], .01)
    self.assertAlmostEqual(trace[0]['position_m'], .1)
    self.assertEqual([r['accel_mps2'] for r in trace[:3]], [0.] * 3)
    self.assertGreater(trace[3]['accel_mps2'], 0.)
    self.assertAlmostEqual(trace[3]['time_s'], .04)
