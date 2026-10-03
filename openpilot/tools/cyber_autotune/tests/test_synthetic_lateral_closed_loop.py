import math
import unittest
from dataclasses import replace

from opendbc.car.hyundai.interface import CarInterface
from opendbc.car.hyundai.values import CAR


def car_params_bytes():
  return CarInterface.get_non_essential_params(
    CAR.HYUNDAI_SANTA_FE_2022,
  ).to_bytes()


def short(scenario, duration_s=0.30):
  return replace(scenario, duration_s=duration_s)


class TestSyntheticLateralClosedLoop(unittest.TestCase):
  def scenarios(self):
    from openpilot.tools.cyber_autotune.synthetic_lateral_scenarios import (
      build_default_matrix,
    )
    return {item.scenario_id: item for item in build_default_matrix()}

  def test_fault_scenario_rejects_before_car_params_decode(self):
    from openpilot.tools.cyber_autotune.synthetic_lateral_closed_loop import (
      run_synthetic_scenario,
    )

    scenario = short(self.scenarios()['sensor_dropout'])
    result = run_synthetic_scenario(scenario, b'not car params')
    self.assertEqual(result.status, 'REJECTED_INPUT')
    self.assertFalse(result.controller_executed)
    self.assertFalse(result.plant_executed)
    self.assertIsNone(result.trace_sha256)
    self.assertFalse(result.runtime_accepted)
    self.assertFalse(result.promotable)

  def test_nominal_scenario_runs_native_controller_and_generic_plant(self):
    from openpilot.tools.cyber_autotune.synthetic_lateral_closed_loop import (
      run_synthetic_scenario,
    )

    scenario = short(self.scenarios()['gentle_left'])
    result = run_synthetic_scenario(scenario, car_params_bytes())
    self.assertEqual(result.status, 'COMPLETED_DIAGNOSTIC')
    self.assertEqual(result.sample_count, 30)
    self.assertTrue(result.controller_executed)
    self.assertTrue(result.plant_executed)
    self.assertEqual(result.physical_delay_owner, 'PLANT')
    self.assertFalse(result.controller_delay_queue_present)
    self.assertIsNotNone(result.trace_sha256)
    self.assertTrue(all(math.isfinite(value) for value in (
      result.lateral_error_rmse_m,
      result.maximum_abs_lateral_error_m,
      result.steering_jerk_rmse_deg_s3,
      result.saturation_ratio,
    )))
    self.assertFalse(result.performance_qualified)
    self.assertFalse(result.vehicle_or_can_write)
    self.assertFalse(result.runtime_accepted)
    self.assertFalse(result.promotable)

  def test_invalid_car_params_blocks_nominal_scenario(self):
    from openpilot.tools.cyber_autotune.synthetic_lateral_closed_loop import (
      run_synthetic_scenario,
    )

    result = run_synthetic_scenario(
      short(self.scenarios()['straight_low']), b'invalid',
    )
    self.assertEqual(result.status, 'BLOCKED')
    self.assertIn('INVALID_CAR_PARAMS', result.blockers)
    self.assertFalse(result.controller_executed)
    self.assertFalse(result.plant_executed)

  def test_left_right_closed_loop_direction_is_symmetric(self):
    from openpilot.tools.cyber_autotune.synthetic_lateral_closed_loop import (
      run_synthetic_scenario,
    )

    scenarios = self.scenarios()
    left = run_synthetic_scenario(short(scenarios['gentle_left']), car_params_bytes())
    right = run_synthetic_scenario(short(scenarios['gentle_right']), car_params_bytes())
    self.assertEqual(left.status, 'COMPLETED_DIAGNOSTIC')
    self.assertEqual(right.status, 'COMPLETED_DIAGNOSTIC')
    self.assertGreater(left.signed_mean_desired_curvature_1pm, 0.0)
    self.assertLess(right.signed_mean_desired_curvature_1pm, 0.0)
    self.assertGreater(left.signed_mean_actual_curvature_1pm, 0.0)
    self.assertLess(right.signed_mean_actual_curvature_1pm, 0.0)
    self.assertAlmostEqual(
      left.signed_mean_actual_curvature_1pm,
      -right.signed_mean_actual_curvature_1pm,
      places=12,
    )
    self.assertAlmostEqual(
      left.lateral_error_rmse_m, right.lateral_error_rmse_m, places=12,
    )

  def test_fresh_state_makes_scenario_result_order_independent(self):
    from openpilot.tools.cyber_autotune.synthetic_lateral_closed_loop import (
      run_synthetic_matrix,
    )

    scenarios = self.scenarios()
    left = short(scenarios['gentle_left'])
    right = short(scenarios['gentle_right'])
    forward = run_synthetic_matrix((left, right), car_params_bytes())
    reverse = run_synthetic_matrix((right, left), car_params_bytes())
    a = {row.scenario_id: row.trace_sha256 for row in forward.scenarios}
    b = {row.scenario_id: row.trace_sha256 for row in reverse.scenarios}
    self.assertEqual(a, b)

  def test_driver_override_keeps_requested_torque_zero_while_inactive(self):
    from openpilot.tools.cyber_autotune.synthetic_lateral_closed_loop import (
      run_synthetic_scenario,
    )

    result = run_synthetic_scenario(
      short(self.scenarios()['driver_override'], 1.0), car_params_bytes(),
    )
    self.assertEqual(result.status, 'COMPLETED_DIAGNOSTIC')
    self.assertGreater(result.driver_intervention_frames, 0)
    self.assertEqual(result.inactive_requested_torque_max_abs, 0.0)
    self.assertGreaterEqual(result.inactive_applied_command_max_abs, 0.0)

  def test_matrix_classifies_nominal_and_fault_scenarios_without_authority(self):
    from openpilot.tools.cyber_autotune.synthetic_lateral_closed_loop import (
      run_synthetic_matrix,
    )

    scenarios = self.scenarios()
    matrix = (
      short(scenarios['straight_low']),
      short(scenarios['gentle_left']),
      short(scenarios['sensor_dropout']),
      short(scenarios['timebase_gap']),
    )
    result = run_synthetic_matrix(matrix, car_params_bytes())
    self.assertEqual(result.status, 'SYNTHETIC_CLOSED_LOOP_DIAGNOSTIC')
    self.assertEqual(result.completed_count, 2)
    self.assertEqual(result.rejected_input_count, 2)
    self.assertEqual(result.blocked_count, 0)
    self.assertTrue(result.all_nominal_completed)
    self.assertTrue(result.fault_inputs_rejected)
    self.assertFalse(result.qualified_closed_loop)
    self.assertFalse(result.performance_qualified)
    self.assertFalse(result.candidate_generation_allowed)
    self.assertFalse(result.runtime_accepted)
    self.assertFalse(result.promotable)

  def test_closed_loop_results_repeat_exactly(self):
    from openpilot.tools.cyber_autotune.synthetic_lateral_closed_loop import (
      run_synthetic_matrix,
    )

    scenarios = self.scenarios()
    matrix = (
      short(scenarios['straight_high']),
      short(scenarios['tight_left']),
      short(scenarios['friction_high']),
    )
    first = run_synthetic_matrix(matrix, car_params_bytes())
    second = run_synthetic_matrix(matrix, car_params_bytes())
    self.assertEqual(first, second)
    self.assertEqual(first.result_sha256, second.result_sha256)

  def test_requested_torque_and_plant_command_remain_bounded(self):
    from openpilot.tools.cyber_autotune.synthetic_lateral_closed_loop import (
      run_synthetic_scenario,
    )

    result = run_synthetic_scenario(
      short(self.scenarios()['tight_left'], 1.0), car_params_bytes(),
    )
    self.assertEqual(result.status, 'COMPLETED_DIAGNOSTIC')
    self.assertLessEqual(result.maximum_abs_requested_torque, 1.0)
    self.assertGreaterEqual(result.saturation_ratio, 0.0)
    self.assertLessEqual(result.saturation_ratio, 1.0)
    self.assertEqual(result.native_to_plant_sign, -1.0)

  def test_invalid_scenario_and_matrix_fail_closed(self):
    from openpilot.tools.cyber_autotune.synthetic_lateral_closed_loop import (
      run_synthetic_matrix,
      run_synthetic_scenario,
    )

    invalid = replace(
      short(self.scenarios()['straight_low']),
      stress_axes=('timebase_gap',),
      expected_outcome='COMPLETED',
    )
    result = run_synthetic_scenario(invalid, car_params_bytes())
    self.assertEqual(result.status, 'BLOCKED')
    self.assertIn('INVALID_SCENARIO', result.blockers)
    for matrix in ([], (), (invalid, invalid)):
      report = run_synthetic_matrix(matrix, car_params_bytes())
      self.assertEqual(report.status, 'BLOCKED')
      self.assertFalse(report.qualified_closed_loop)
      self.assertFalse(report.runtime_accepted)
      self.assertFalse(report.promotable)
