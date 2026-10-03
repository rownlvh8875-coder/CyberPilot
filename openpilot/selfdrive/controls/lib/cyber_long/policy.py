"""Non-actuating stock observer; state and fault reasons stay in memory only."""
import math

from openpilot.selfdrive.controls.lib.cyber_long.types import CyberLongConfig, CyberLongMode, LongContext, LongObservation


class CyberLongPolicy:
  def __init__(self, config: CyberLongConfig):
    self.config = config
    self.reset('initialization')

  def reset(self, reason: str) -> None:
    """Explicit session reset clears diagnostics, input watermarks and binding."""
    self.last_observation: LongObservation | None = None
    self.last_reset_reason = reason
    self._times: tuple[int, int, int] | None = None
    self._binding = None

  def invalidate(self, reason: str, context: LongContext | None = None) -> None:
    """Clear diagnostics on fault, not session freshness. Consume known frame ID."""
    self.last_observation = None
    self.last_reset_reason = reason
    if context is not None:
      timestamps = (context.model_mono_time_ns, context.car_state_mono_time_ns, context.radar_mono_time_ns)
      if all(type(t) is int and t > 0 for t in timestamps):
        self._times = timestamps if self._times is None else tuple(max(a, b) for a, b in zip(self._times, timestamps, strict=True))

  def observe(self, context: LongContext) -> None:
    """Return no candidate. Rejected frames clear diagnostics, never hold them.

    Within a session input watermarks survive rejection (not controller state):
    otherwise a third copy of a rejected duplicate could be labeled fresh.
    Explicit reset is reserved for a new session; faults retain input identity.
    Equal asynchronous radar/carState times are allowed; model must advance.
    """
    if self.config.mode == CyberLongMode.DISABLED:
      return

    self.last_observation = None
    timestamps = (context.model_mono_time_ns, context.car_state_mono_time_ns, context.radar_mono_time_ns)
    if any(type(t) is not int or t <= 0 for t in timestamps):
      self.last_reset_reason = 'invalid_timestamp'
      return
    previous_times = self._times
    self._times = timestamps if previous_times is None else tuple(max(a, b) for a, b in zip(previous_times, timestamps, strict=True))
    previous_binding = self._binding
    self._binding = context.binding

    if context.binding.configuration_epoch != self.config.configuration_epoch:
      self.last_reset_reason = 'configuration_mismatch'
    elif previous_binding is not None and previous_binding != context.binding:
      self.last_reset_reason = 'binding_changed'
    elif previous_times is not None and (timestamps[0] <= previous_times[0] or
                                        timestamps[1] < previous_times[1] or timestamps[2] < previous_times[2]):
      self.last_reset_reason = 'input_replay_or_reversal'
    elif not context.input_valid:
      self.last_reset_reason = 'upstream_input_invalid'
    elif context.reset_state or context.brake_pressed or context.gas_pressed or not context.long_active:
      self.last_reset_reason = 'driver_or_stock_reset'
    elif not context.candidates or not all(math.isfinite(c.accel_mps2) for c in context.candidates) or not all(
      math.isfinite(v) for v in (context.v_ego_mps, context.a_ego_mps2, context.v_cruise_mps)
    ):
      self.last_reset_reason = 'invalid_numeric_input'
    else:
      winner = min(context.candidates, key=lambda c: c.accel_mps2)
      self.last_observation = LongObservation(
        context=context, winner_source=winner.source, winner_accel_mps2=winner.accel_mps2,
        stock_should_stop=any(c.should_stop for c in context.candidates), mode=self.config.mode,
        reason='stock_observation_only', provenance_complete=context.binding.complete,
      )
