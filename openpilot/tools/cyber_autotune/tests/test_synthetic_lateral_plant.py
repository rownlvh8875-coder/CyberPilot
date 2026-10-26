import math
import unittest
from dataclasses import replace


class TestSyntheticLateralPlant(unittest.TestCase):
  def config(self):
    from openpilot.tools.cyber_autotune.synthetic_lateral_plant import PlantConfig
    return PlantConfig(
      dt_s=0.01,
      actuator_delay_s=0.03,
      response_tau_s=0.20,
      lateral_accel_per_command_mps2=3.0,
      command_friction=0.05,
      wheelbase_m=2.8,
      steer_ratio=16.0,
      command_limit=1.0,
    )

  def plant(self):
    from openpilot.tools.cyber_autotune.synthetic_lateral_plant import SyntheticLateralPlant
    return SyntheticLateralPlant(self.config())

  def test_zero_command_on_straight_remains_zero(self):
    plant = self.plant()
    for _ in range(100):
      sample = plant.step(0.0, speed_mps=20.0, desired_curvature_1pm=0.0)
    self.assertEqual(sample.requested_command, 0.0)
    self.assertEqual(sample.applied_command, 0.0)
    self.assertEqual(sample.lateral_accel_mps2, 0.0)
    self.assertEqual(sample.yaw_rate_rps, 0.0)
    self.assertEqual(sample.heading_error_rad, 0.0)
    self.assertEqual(sample.lateral_error_m, 0.0)

  def test_actuator_delay_is_owned_once_by_plant(self):
    plant = self.plant()
    outputs = [
      plant.step(0.5, speed_mps=20.0, desired_curvature_1pm=0.0)
      for _ in range(5)
    ]
    self.assertEqual([row.applied_command for row in outputs[:3]], [0.0, 0.0, 0.0])
    self.assertEqual(outputs[3].applied_command, 0.5)
    self.assertEqual(outputs[4].applied_command, 0.5)
    self.assertEqual(outputs[-1].physical_delay_owner, 'PLANT')
    self.assertFalse(outputs[-1].controller_delay_queue_present)

  def test_command_is_clamped_and_saturation_is_reported(self):
    plant = self.plant()
    sample = plant.step(2.0, speed_mps=20.0, desired_curvature_1pm=0.0)
    self.assertEqual(sample.requested_command, 1.0)
    self.assertTrue(sample.saturated)
    for _ in range(3):
      sample = plant.step(-3.0, speed_mps=20.0, desired_curvature_1pm=0.0)
    self.assertEqual(sample.requested_command, -1.0)
    self.assertTrue(sample.saturated)

  def test_friction_deadzone_blocks_small_command(self):
    plant = self.plant()
    for _ in range(10):
      sample = plant.step(0.04, speed_mps=20.0, desired_curvature_1pm=0.0)
    self.assertEqual(sample.effective_command, 0.0)
    self.assertEqual(sample.lateral_accel_mps2, 0.0)
    self.assertEqual(sample.yaw_rate_rps, 0.0)

  def test_left_right_response_is_sign_symmetric(self):
    left = self.plant()
    right = self.plant()
    for _ in range(100):
      a = left.step(0.4, speed_mps=18.0, desired_curvature_1pm=0.006)
      b = right.step(-0.4, speed_mps=18.0, desired_curvature_1pm=-0.006)
    self.assertAlmostEqual(a.applied_command, -b.applied_command)
    self.assertAlmostEqual(a.lateral_accel_mps2, -b.lateral_accel_mps2)
    self.assertAlmostEqual(a.yaw_rate_rps, -b.yaw_rate_rps)
    self.assertAlmostEqual(a.heading_error_rad, -b.heading_error_rad)
    self.assertAlmostEqual(a.lateral_error_m, -b.lateral_error_m)
    self.assertAlmostEqual(a.steering_angle_deg, -b.steering_angle_deg)
    self.assertAlmostEqual(a.steering_rate_deg_s, -b.steering_rate_deg_s)

  def test_reset_restores_deterministic_initial_state(self):
    plant = self.plant()
    first = [plant.step(0.3, speed_mps=17.0, desired_curvature_1pm=0.004) for _ in range(20)]
    plant.reset()
    second = [plant.step(0.3, speed_mps=17.0, desired_curvature_1pm=0.004) for _ in range(20)]
    self.assertEqual(first, second)
    self.assertEqual(plant.snapshot(), second[-1].state)

  def test_friction_scale_changes_effective_command_only_within_bounds(self):
    low = self.plant()
    high = self.plant()
    for _ in range(10):
      a = low.step(0.3, speed_mps=20.0, desired_curvature_1pm=0.0, friction_scale=0.5)
      b = high.step(0.3, speed_mps=20.0, desired_curvature_1pm=0.0, friction_scale=1.5)
    self.assertGreater(a.effective_command, b.effective_command)
    self.assertGreater(abs(a.lateral_accel_mps2), abs(b.lateral_accel_mps2))

  def test_invalid_config_and_inputs_fail_closed(self):
    from openpilot.tools.cyber_autotune.synthetic_lateral_plant import SyntheticLateralPlant

    for mutation in (
      replace(self.config(), dt_s=0.0),
      replace(self.config(), actuator_delay_s=-0.1),
      replace(self.config(), response_tau_s=0.0),
      replace(self.config(), lateral_accel_per_command_mps2=math.nan),
      replace(self.config(), command_friction=-0.1),
      replace(self.config(), wheelbase_m=0.0),
      replace(self.config(), steer_ratio=0.0),
      replace(self.config(), command_limit=1.1),
    ):
      with self.subTest(mutation=mutation), self.assertRaises(ValueError):
        SyntheticLateralPlant(mutation)

    plant = self.plant()
    for kwargs in (
      {'command': math.nan, 'speed_mps': 20.0, 'desired_curvature_1pm': 0.0},
      {'command': 0.0, 'speed_mps': 0.0, 'desired_curvature_1pm': 0.0},
      {'command': 0.0, 'speed_mps': 20.0, 'desired_curvature_1pm': math.inf},
      {'command': 0.0, 'speed_mps': 20.0, 'desired_curvature_1pm': 0.0, 'friction_scale': 0.0},
    ):
      with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
        plant.step(**kwargs)

  def test_samples_never_grant_vehicle_or_runtime_authority(self):
    sample = self.plant().step(0.2, speed_mps=20.0, desired_curvature_1pm=0.001)
    self.assertFalse(sample.vehicle_or_can_write)
    self.assertFalse(sample.runtime_accepted)
    self.assertFalse(sample.promotable)


if __name__ == '__main__':
  unittest.main()
