import math
import unittest
from dataclasses import FrozenInstanceError

from openpilot.selfdrive.controls.lib.cyber_lateral.coordinator import CyberLateralCoordinator
from openpilot.selfdrive.controls.lib.cyber_lateral.types import (
  CyberLateralConfig, CyberLateralMode, LateralBinding, LateralContext,
  NativeLateralResult,
)


def make_binding(*, vehicle='synthetic-car', firmware='eps-v1', model='model-v1', controller_type='torque', epoch=0):
  return LateralBinding(vehicle=vehicle, firmware=firmware, model=model,
                        controller_type=controller_type, configuration_epoch=epoch)


def make_context(*, model_time=100, car_time=90, params_time=80, delay_time=70,
                 input_valid=True, lat_active=True, steering_pressed=False,
                 steer_limited=False, curvature_limited=False, v_ego=15.,
                 desired_curvature=0.01, current_curvature=0.009, roll=0.02,
                 lateral_delay=0.2, native_result=None, binding=None):
  return LateralContext(
    model_mono_time_ns=model_time,
    car_state_mono_time_ns=car_time,
    vehicle_parameters_mono_time_ns=params_time,
    lateral_delay_mono_time_ns=delay_time,
    input_valid=input_valid,
    lat_active=lat_active,
    steering_pressed=steering_pressed,
    steer_limited_by_safety=steer_limited,
    curvature_limited=curvature_limited,
    v_ego_mps=v_ego,
    desired_curvature_1pm=desired_curvature,
    current_curvature_1pm=current_curvature,
    roll_rad=roll,
    lateral_delay_s=lateral_delay,
    native_result=native_result or NativeLateralResult(0.1, 1.2, 'torque'),
    binding=binding or make_binding(),
  )


class TestCyberLateralCoordinator(unittest.TestCase):
  def test_disabled_invokes_native_once_and_never_builds_context(self):
    coordinator = CyberLateralCoordinator(CyberLateralConfig(), make_binding())
    native_result = (0.1, 1.2, object())
    counts = {'native': 0, 'context': 0}

    def native_update():
      counts['native'] += 1
      return native_result

    def context_factory(_):
      counts['context'] += 1
      raise AssertionError('disabled mode read optional observation input')

    result = coordinator.run_native(native_update, context_factory)
    self.assertIs(result, native_result)
    self.assertEqual(counts, {'native': 1, 'context': 0})
    self.assertIsNone(coordinator.last_observation)

  def test_observe_only_invokes_native_once_and_records_current_frame(self):
    config = CyberLateralConfig(mode=CyberLateralMode.OBSERVE_ONLY)
    coordinator = CyberLateralCoordinator(config, make_binding())
    native_result = (0.1, 1.2, object())
    seen = []

    result = coordinator.run_native(lambda: native_result, lambda value: seen.append(value) or make_context())

    self.assertIs(result, native_result)
    self.assertEqual(seen, [native_result])
    observation = coordinator.last_observation
    self.assertEqual(observation.context.native_result, NativeLateralResult(0.1, 1.2, 'torque'))
    self.assertEqual(observation.reason, 'native_observation_only')
    self.assertTrue(observation.provenance_complete)

  def test_native_exception_propagates_without_observation(self):
    coordinator = CyberLateralCoordinator(CyberLateralConfig(mode=CyberLateralMode.OBSERVE_ONLY), make_binding())
    error = RuntimeError('native failure')

    with self.assertRaises(RuntimeError) as raised:
      coordinator.run_native(lambda: (_ for _ in ()).throw(error), lambda _: make_context())

    self.assertIs(raised.exception, error)
    self.assertIsNone(coordinator.last_observation)
    self.assertIsNone(coordinator.last_fault)

  def test_context_exception_returns_native_result_and_invalidates_observation(self):
    coordinator = CyberLateralCoordinator(CyberLateralConfig(mode=CyberLateralMode.OBSERVE_ONLY), make_binding())
    native_result = (0.1, 1.2, object())
    coordinator.run_native(lambda: native_result, lambda _: make_context())

    result = coordinator.run_native(lambda: native_result, lambda _: (_ for _ in ()).throw(RuntimeError('bad context')))

    self.assertIs(result, native_result)
    self.assertIsNone(coordinator.last_observation)
    self.assertEqual(coordinator.last_fault, 'RuntimeError')
    self.assertEqual(coordinator.last_reset_reason, 'observer_fault')

  def test_duplicate_or_reversed_model_time_is_not_fresh(self):
    coordinator = CyberLateralCoordinator(CyberLateralConfig(mode=CyberLateralMode.OBSERVE_ONLY), make_binding())
    native_result = (0.1, 1.2, object())
    def run(context):
      return coordinator.run_native(lambda: native_result, lambda _: context)
    run(make_context(model_time=100))
    self.assertIsNotNone(coordinator.last_observation)
    for timestamp in (100, 99):
      run(make_context(model_time=timestamp))
      self.assertIsNone(coordinator.last_observation)
      self.assertEqual(coordinator.last_reset_reason, 'input_replay_or_reversal')
    run(make_context(model_time=101))
    self.assertEqual(coordinator.last_observation.context.model_mono_time_ns, 101)

  def test_async_reuse_of_other_service_timestamps_is_allowed(self):
    coordinator = CyberLateralCoordinator(CyberLateralConfig(mode=CyberLateralMode.OBSERVE_ONLY), make_binding())
    native_result = (0.1, 1.2, object())
    coordinator.run_native(lambda: native_result, lambda _: make_context(model_time=100))
    coordinator.run_native(lambda: native_result, lambda _: make_context(model_time=101))
    self.assertEqual(coordinator.last_observation.context.car_state_mono_time_ns, 90)
    self.assertEqual(coordinator.last_observation.context.vehicle_parameters_mono_time_ns, 80)

  def test_inactive_override_binding_change_and_nonfinite_input_clear_current_observation(self):
    coordinator = CyberLateralCoordinator(CyberLateralConfig(mode=CyberLateralMode.OBSERVE_ONLY), make_binding())
    native_result = (0.1, 1.2, object())
    contexts = (
      make_context(model_time=101, lat_active=False),
      make_context(model_time=102, steering_pressed=True),
      make_context(model_time=103, binding=make_binding(firmware='eps-v2')),
      make_context(model_time=104, v_ego=math.nan),
      make_context(model_time=105, input_valid=False),
    )
    coordinator.run_native(lambda: native_result, lambda _: make_context(model_time=100))
    for context in contexts:
      with self.subTest(model_time=context.model_mono_time_ns):
        coordinator.run_native(lambda: native_result, lambda _, context=context: context)
        self.assertIsNone(coordinator.last_observation)

  def test_config_context_and_result_are_immutable(self):
    config = CyberLateralConfig()
    context = make_context()
    result = NativeLateralResult(0.1, 1.2, 'torque')
    for owner, field, value in ((config, 'configuration_epoch', 1), (context, 'v_ego_mps', 1.), (result, 'steer', 0.2)):
      with self.subTest(owner=type(owner).__name__), self.assertRaises(FrozenInstanceError):
        setattr(owner, field, value)
    with self.assertRaises(ValueError):
      CyberLateralConfig(mode='active')
    with self.assertRaises(ValueError):
      CyberLateralConfig(configuration_epoch=-1)


if __name__ == '__main__':
  unittest.main()
