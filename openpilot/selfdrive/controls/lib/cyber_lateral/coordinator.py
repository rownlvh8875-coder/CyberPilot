"""Exactly-once native-controller seam and read-only observation lifecycle."""
from collections.abc import Callable
import math
from typing import TypeVar

from openpilot.selfdrive.controls.lib.cyber_lateral.path_tracking import observe_path_tracking
from openpilot.selfdrive.controls.lib.cyber_lateral.types import (
  CyberLateralConfig, CyberLateralMode, LateralBinding, LateralContext,
  LateralObservation,
)

T = TypeVar('T')


class CyberLateralCoordinator:
  def __init__(self, config: CyberLateralConfig, binding: LateralBinding):
    if not isinstance(config, CyberLateralConfig):
      raise ValueError('config must be CyberLateralConfig')
    if not isinstance(binding, LateralBinding):
      raise ValueError('binding must be LateralBinding')
    self.config = config
    self.binding = binding
    self.reset('initialization')

  def reset(self, reason: str) -> None:
    self.last_observation: LateralObservation | None = None
    self.last_reset_reason = reason
    self.last_fault: str | None = None
    self._times: tuple[int, int, int, int] | None = None

  @staticmethod
  def _timestamps(context: LateralContext) -> tuple[int, int, int, int]:
    return (context.model_mono_time_ns, context.car_state_mono_time_ns,
            context.vehicle_parameters_mono_time_ns, context.lateral_delay_mono_time_ns)

  def invalidate(self, reason: str, context: LateralContext | None = None) -> None:
    self.last_observation = None
    self.last_reset_reason = reason
    if context is not None:
      timestamps = self._timestamps(context)
      if all(type(value) is int and value > 0 for value in timestamps):
        self._times = timestamps if self._times is None else tuple(
          max(old, new) for old, new in zip(self._times, timestamps, strict=True)
        )

  def observe(self, context: LateralContext) -> None:
    if self.config.mode == CyberLateralMode.DISABLED:
      return

    self.last_observation = None
    self.last_fault = None
    timestamps = self._timestamps(context)
    if any(type(value) is not int or value <= 0 for value in timestamps):
      self.last_reset_reason = 'invalid_timestamp'
      return

    previous_times = self._times
    self._times = timestamps if previous_times is None else tuple(
      max(old, new) for old, new in zip(previous_times, timestamps, strict=True)
    )
    numeric = (
      context.v_ego_mps, context.desired_curvature_1pm, context.current_curvature_1pm,
      context.roll_rad, context.lateral_delay_s, context.native_result.steer,
      context.native_result.lateral_output,
    )

    if context.binding.configuration_epoch != self.config.configuration_epoch:
      self.last_reset_reason = 'configuration_mismatch'
    elif context.binding != self.binding:
      self.last_reset_reason = 'binding_mismatch'
    elif previous_times is not None and (timestamps[0] <= previous_times[0] or any(
      new < old for old, new in zip(previous_times[1:], timestamps[1:], strict=True)
    )):
      self.last_reset_reason = 'input_replay_or_reversal'
    elif not context.input_valid:
      self.last_reset_reason = 'upstream_input_invalid'
    elif not context.lat_active or context.steering_pressed:
      self.last_reset_reason = 'native_reset_or_override'
    elif not isinstance(context.native_result.state_kind, str) or not context.native_result.state_kind:
      self.last_reset_reason = 'invalid_controller_identity'
    elif not all(type(value) in (int, float) and math.isfinite(value) for value in numeric):
      self.last_reset_reason = 'invalid_numeric_input'
    else:
      self.last_observation = LateralObservation(
        context=context,
        mode=self.config.mode,
        reason='native_observation_only',
        provenance_complete=context.binding.complete,
        path_tracking_observation=observe_path_tracking(
          model_mono_time_ns=context.model_mono_time_ns,
          car_state_mono_time_ns=context.car_state_mono_time_ns,
          desired_curvature_1pm=context.desired_curvature_1pm,
          current_curvature_1pm=context.current_curvature_1pm,
          path_quality=context.path_quality_observation,
        ),
      )
      self.last_reset_reason = 'observed'

  def run_native(self, native_update: Callable[[], T],
                 context_factory: Callable[[T], LateralContext] | None = None) -> T:
    """Invoke native control exactly once; optional diagnostics cannot replace its result."""
    result = self.invoke_native(native_update)
    self.observe_native_result(result, context_factory)
    return result

  @staticmethod
  def invoke_native(native_update: Callable[[], T]) -> T:
    """Invoke the native controller exactly once without running diagnostics."""
    return native_update()

  def observe_native_result(self, result: T,
                            context_factory: Callable[[T], LateralContext] | None = None) -> None:
    """Run contained diagnostics after the native command has left the publish path."""
    if self.config.mode == CyberLateralMode.DISABLED:
      return
    if context_factory is None:
      self.invalidate('missing_context_factory')
      return
    try:
      self.observe(context_factory(result))
    except Exception as error:
      self.last_fault = type(error).__name__
      self.invalidate('observer_fault')
