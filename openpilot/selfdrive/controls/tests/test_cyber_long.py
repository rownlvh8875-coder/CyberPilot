"""Synthetic, hand-derived contract cases; no vehicle/native solver qualification."""
import unittest
from dataclasses import FrozenInstanceError, replace

from openpilot.selfdrive.controls.lib.cyber_long.types import (
  CyberLongConfig, CyberLongMode, LongContext, ParameterBinding, StockCandidate,
)
from openpilot.selfdrive.controls.lib.cyber_long.policy import CyberLongPolicy


def context(**changes):
  # Nanoseconds identify synthetic messages, not physical freshness thresholds.
  stock = LongContext(
    candidates=(StockCandidate(-0.4, 'lead0', False), StockCandidate(0.2, 'cruise', True)),
    input_valid=True, reset_state=False, brake_pressed=False, gas_pressed=False, long_active=True,
    model_mono_time_ns=100, car_state_mono_time_ns=90, radar_mono_time_ns=80,
    v_ego_mps=10., a_ego_mps2=0., v_cruise_mps=12., force_decel=False, personality='standard',
    binding=ParameterBinding(vehicle='synthetic-car', firmware='synthetic-fw', model='synthetic-model', configuration_epoch=0),
  )
  return replace(stock, **changes)


class TestCyberLongPolicy(unittest.TestCase):
  def setUp(self):
    self.policy = CyberLongPolicy(CyberLongConfig(mode=CyberLongMode.OBSERVE_ONLY))

  def test_disabled_bypasses_observation(self):
    policy = CyberLongPolicy(CyberLongConfig())
    ctx = context()
    self.assertIsNone(policy.observe(ctx))
    self.assertIsNone(policy.last_observation)
    self.assertEqual(ctx.candidates, (StockCandidate(-0.4, 'lead0', False), StockCandidate(0.2, 'cruise', True)))

  def test_observation_has_no_actuator_authority(self):
    ctx = context()
    self.assertIsNone(self.policy.observe(ctx))
    observation = self.policy.last_observation
    self.assertEqual(observation.winner_source, 'lead0')
    self.assertEqual(observation.winner_accel_mps2, -0.4)
    self.assertTrue(observation.stock_should_stop)
    self.assertEqual(observation.context, ctx)

  def test_tie_retains_first_source(self):
    self.policy.observe(context(candidates=(StockCandidate(-0.4, 'lead0', False), StockCandidate(-0.4, 'cruise', True))))
    self.assertEqual(self.policy.last_observation.winner_source, 'lead0')
    self.assertTrue(self.policy.last_observation.stock_should_stop)

  def test_invalid_context_clears_previous_observation(self):
    cases = [{'input_valid': False}, {'candidates': ()}, {'v_ego_mps': float('nan')},
             {'a_ego_mps2': float('inf')}, {'v_cruise_mps': float('-inf')},
             {'model_mono_time_ns': 0}, {'car_state_mono_time_ns': -1}, {'radar_mono_time_ns': 0}]
    cases += [{'candidates': (StockCandidate(x, 'lead0', False),)} for x in (float('nan'), float('inf'), float('-inf'))]
    for changes in cases:
      with self.subTest(changes=changes):
        self.policy.reset('test setup')
        self.policy.observe(context())
        self.assertIsNotNone(self.policy.last_observation)
        self.assertIsNone(self.policy.observe(context(model_mono_time_ns=110, **changes) if 'model_mono_time_ns' not in changes else context(**changes)))
        self.assertIsNone(self.policy.last_observation)

  def test_driver_or_stock_reset_clears_observation(self):
    for changes in ({'brake_pressed': True}, {'gas_pressed': True}, {'long_active': False}, {'reset_state': True}):
      with self.subTest(changes=changes):
        self.policy.reset('test setup')
        self.policy.observe(context())
        self.policy.observe(context(model_mono_time_ns=110, **changes))
        self.assertIsNone(self.policy.last_observation)

  def test_replayed_or_reversed_model_time_resets(self):
    self.policy.observe(context())
    for timestamp in (100, 100, 99, 100):
      self.policy.observe(context(model_mono_time_ns=timestamp))
      self.assertIsNone(self.policy.last_observation)
    self.policy.observe(context(model_mono_time_ns=101))
    self.assertEqual(self.policy.last_observation.context.model_mono_time_ns, 101)

  def test_asynchronous_radar_reuse_is_not_model_replay(self):
    self.policy.observe(context())
    self.policy.observe(context(model_mono_time_ns=110))
    self.assertIsNotNone(self.policy.last_observation)
    self.assertEqual(self.policy.last_observation.context.radar_mono_time_ns, 80)

  def test_reversed_asynchronous_time_clears_observation(self):
    for changes in ({'car_state_mono_time_ns': 89}, {'radar_mono_time_ns': 79}):
      with self.subTest(changes=changes):
        self.policy.reset('test setup')
        self.policy.observe(context())
        self.policy.observe(context(model_mono_time_ns=110, **changes))
        self.assertIsNone(self.policy.last_observation)

  def test_binding_change_resets_observation(self):
    for changes in ({'vehicle': 'other'}, {'firmware': 'other'}, {'model': 'other'}, {'configuration_epoch': 1}):
      with self.subTest(changes=changes):
        self.policy.reset('test setup')
        self.policy.observe(context())
        binding = replace(context().binding, **changes)
        self.policy.observe(context(model_mono_time_ns=110, binding=binding))
        self.assertIsNone(self.policy.last_observation)
        # Configuration epoch must match the immutable observer configuration.
        if binding.configuration_epoch == 0:
          self.policy.observe(context(model_mono_time_ns=120, binding=binding))
          self.assertEqual(self.policy.last_observation.context.binding, binding)

  def test_unknown_provenance_is_not_qualified_evidence(self):
    self.policy.observe(context(binding=ParameterBinding(vehicle='car', configuration_epoch=0)))
    self.assertIsNotNone(self.policy.last_observation)
    self.assertFalse(self.policy.last_observation.provenance_complete)

  def test_explicit_reset_clears_session(self):
    self.policy.observe(context())
    self.policy.reset('new synthetic session')
    self.assertIsNone(self.policy.last_observation)
    self.assertEqual(self.policy.last_reset_reason, 'new synthetic session')
    self.policy.observe(context(model_mono_time_ns=1, car_state_mono_time_ns=1, radar_mono_time_ns=1))
    self.assertIsNotNone(self.policy.last_observation)

  def test_context_and_config_are_immutable(self):
    ctx = context()
    config = CyberLongConfig()
    with self.assertRaises(FrozenInstanceError):
      ctx.v_ego_mps = 100.
    with self.assertRaises(FrozenInstanceError):
      config.mode = CyberLongMode.OBSERVE_ONLY
    with self.assertRaises(FrozenInstanceError):
      ctx.candidates[0].accel_mps2 = 100.
    self.policy.observe(ctx)
    with self.assertRaises(FrozenInstanceError):
      self.policy.last_observation.winner_accel_mps2 = 100.

  def test_configuration_rejects_unavailable_active_mode(self):
    with self.assertRaises(ValueError):
      CyberLongConfig(mode='active')
    with self.assertRaises(ValueError):
      CyberLongConfig(configuration_epoch=-1)


if __name__ == '__main__':
  unittest.main()
