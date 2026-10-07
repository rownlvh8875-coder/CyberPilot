from dataclasses import FrozenInstanceError
import importlib
import importlib.util
import math
import unittest


class TestCurvatureYawPlant(unittest.TestCase):
  def api(self):
    name = 'openpilot.tools.cyber_autotune.curvature_yaw_plant'
    self.assertIsNotNone(importlib.util.find_spec(name), 'curvature/yaw plant primitive not implemented')
    return importlib.import_module(name)

  def config(self, **changes):
    api = self.api()
    values = {
      'dt_s': 0.01,
      'delay_steps': 2,
      'min_speed_mps': 2.5,
      'max_speed_mps': 8.0,
      'command_limit': 1.0,
      'curvature_intercept_1pm': 0.0001,
      'curvature_ar': 0.9,
      'command_gain_1pm': 0.02,
      'command_speed_gain_s_per_m2': 0.001,
      'command_inv_speed_gain_per_s': 0.03,
      'roll_gain_1pm_per_rad': 0.004,
      'yaw_ar': 0.8,
      'yaw_bias_rad_s': 0.0002,
    }
    values.update(changes)
    return api.CurvatureYawPlantConfig(**values)

  def state(self, **changes):
    api = self.api()
    values = {'curvature_1pm': 0.01, 'yaw_rate_rad_s': -0.05, 'command_history': (0.2, 0.3)}
    values.update(changes)
    return api.CurvatureYawPlantState(**values)

  def test_exact_step_formula_and_fifo_delay(self):
    api = self.api()
    config = self.config()
    state = self.state()
    result = api.observe_curvature_yaw_step(config, state, command=0.4, speed_mps=5.0, roll_rad=0.02)
    self.assertEqual(result.status, 'DESCRIPTIVE_ONLY')
    self.assertEqual(result.reason, 'ok')
    self.assertAlmostEqual(result.delayed_command, 0.2)
    expected_k = 0.0001 + 0.9 * 0.01 + 0.02 * 0.2 + 0.001 * 0.2 * 5.0 + 0.03 * 0.2 / 5.0 + 0.004 * 0.02
    self.assertAlmostEqual(result.next_state.curvature_1pm, expected_k)
    current_target = -0.01 * 5.0
    next_target = -expected_k * 5.0
    expected_yaw = next_target + 0.8 * (-0.05 - current_target) + 0.0002
    self.assertAlmostEqual(result.next_state.yaw_rate_rad_s, expected_yaw)
    self.assertEqual(result.next_state.command_history, (0.3, 0.4))
    self.assertFalse(result.vehicle_activation_allowed)

  def test_zero_delay_uses_current_command_and_keeps_empty_history(self):
    api = self.api()
    config = self.config(delay_steps=0)
    state = self.state(command_history=())
    result = api.observe_curvature_yaw_step(config, state, command=-0.25, speed_mps=4.0, roll_rad=0.0)
    self.assertEqual(result.status, 'DESCRIPTIVE_ONLY')
    self.assertAlmostEqual(result.delayed_command, -0.25)
    self.assertEqual(result.next_state.command_history, ())

  def test_mirrored_zero_bias_case_is_antisymmetric(self):
    api = self.api()
    config = self.config(
      curvature_intercept_1pm=0.0,
      yaw_bias_rad_s=0.0,
      roll_gain_1pm_per_rad=0.0,
    )
    pos = api.observe_curvature_yaw_step(
      config, self.state(curvature_1pm=0.01, yaw_rate_rad_s=-0.04, command_history=(0.1, 0.2)),
      command=0.3, speed_mps=5.0, roll_rad=0.0,
    )
    neg = api.observe_curvature_yaw_step(
      config, self.state(curvature_1pm=-0.01, yaw_rate_rad_s=0.04, command_history=(-0.1, -0.2)),
      command=-0.3, speed_mps=5.0, roll_rad=0.0,
    )
    self.assertAlmostEqual(pos.next_state.curvature_1pm, -neg.next_state.curvature_1pm)
    self.assertAlmostEqual(pos.next_state.yaw_rate_rad_s, -neg.next_state.yaw_rate_rad_s)

  def test_invalid_or_unstable_config_fails_closed(self):
    api = self.api()
    cases = (
      self.config(dt_s=0.0),
      self.config(delay_steps=-1),
      self.config(min_speed_mps=8.0, max_speed_mps=2.5),
      self.config(command_limit=0.0),
      self.config(curvature_ar=1.0),
      self.config(curvature_ar=-1.0),
      self.config(yaw_ar=-0.01),
      self.config(yaw_ar=1.0),
      self.config(command_gain_1pm=math.nan),
    )
    for config in cases:
      with self.subTest(config=config):
        result = api.observe_curvature_yaw_step(config, self.state(), command=0.0, speed_mps=5.0, roll_rad=0.0)
        self.assertEqual(result.status, 'BLOCKED')
        self.assertEqual(result.reason, 'INVALID_CONFIG')
        self.assertIsNone(result.next_state)

  def test_invalid_state_or_history_fails_closed(self):
    api = self.api()
    cases = (
      self.state(curvature_1pm=math.nan),
      self.state(yaw_rate_rad_s=math.inf),
      self.state(command_history=(0.1,)),
      self.state(command_history=(0.1, 2.0)),
    )
    for state in cases:
      with self.subTest(state=state):
        result = api.observe_curvature_yaw_step(self.config(), state, command=0.0, speed_mps=5.0, roll_rad=0.0)
        self.assertEqual(result.status, 'BLOCKED')
        self.assertEqual(result.reason, 'INVALID_STATE')

  def test_input_domain_fails_closed(self):
    api = self.api()
    cases = (
      {'command': 1.1, 'speed_mps': 5.0, 'roll_rad': 0.0},
      {'command': 0.0, 'speed_mps': 2.49, 'roll_rad': 0.0},
      {'command': 0.0, 'speed_mps': 8.01, 'roll_rad': 0.0},
      {'command': 0.0, 'speed_mps': 5.0, 'roll_rad': math.nan},
    )
    for kwargs in cases:
      with self.subTest(kwargs=kwargs):
        result = api.observe_curvature_yaw_step(self.config(), self.state(), **kwargs)
        self.assertEqual(result.status, 'BLOCKED')
        self.assertEqual(result.reason, 'INPUT_OUTSIDE_DOMAIN')

  def test_result_is_frozen_and_has_no_authority_surface(self):
    api = self.api()
    result = api.observe_curvature_yaw_step(self.config(), self.state(), command=0.0, speed_mps=5.0, roll_rad=0.0)
    with self.assertRaises(FrozenInstanceError):
      result.status = 'READY'
    with self.assertRaises(FrozenInstanceError):
      result.next_state.curvature_1pm = 0.0
    self.assertIsNone(getattr(result, 'accepted', None))
    self.assertIsNone(getattr(result, 'controller_command', None))
    self.assertIsNone(getattr(result, 'profile', None))
    self.assertIsNone(getattr(result, 'tune', None))


if __name__ == '__main__':
  unittest.main()
