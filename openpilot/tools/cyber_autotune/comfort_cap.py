"""Synthetic-only 95% positive-acceleration experiment. NOT a runtime policy.

No production consumer imports this module. The native planner subclass is an
in-process experimental seam, not an active CyberLong mode or a vehicle adapter.
No Carrot code/constants copied. Existing stock speed envelope supplies units;
0.95 is the single approved research hypothesis, NOT a calibrated vehicle value.
"""
import hashlib
import inspect
from pathlib import Path

from openpilot.selfdrive.controls.lib.cyber_long.types import CyberLongConfig, CyberLongMode, LongContext
from openpilot.selfdrive.controls.lib.drive_helpers import should_stop
from openpilot.selfdrive.controls.lib.longitudinal_mpc_lib.long_mpc import LongitudinalPlanSource
from openpilot.selfdrive.controls.lib.longitudinal_planner import LongitudinalPlanner, get_max_accel
from openpilot.tools.cyber_autotune.contracts import finite_number


CAP_FRACTION = .95  # Dimensionless, fixed before experiment; no search/default vehicle tune.
PLANNER_SHA256 = '9e155c5a38d4c383a8f49827cbbc52e89dd87abf6ca9b911e842e1862ff1c959'


def positive_accel_cap(context: LongContext) -> float | None:
  """Stateless proposal; temporal admission belongs to the native observer seam.

None always means use current stock candidates, never retain an older cap.
Unknown vehicle provenance is permitted ONLY in this synthetic fixture scope.
"""
  if not isinstance(context, LongContext):
    return None
  flags = (context.input_valid, context.reset_state, context.brake_pressed, context.gas_pressed,
           context.long_active, context.force_decel)
  if (any(type(value) is not bool for value in flags) or not context.input_valid or context.reset_state or
      context.brake_pressed or context.gas_pressed or not context.long_active or context.force_decel):
    return None
  if (context.binding.vehicle != 'SYNTHETIC_PARITY_ONLY' or
      not all(finite_number(value) for value in (context.v_ego_mps, context.a_ego_mps2, context.v_cruise_mps)) or
      context.v_ego_mps < 0 or context.v_cruise_mps < 0 or not context.candidates or
      any(not finite_number(c.accel_mps2) or type(c.should_stop) is not bool for c in context.candidates)):
    return None
  if any(c.should_stop for c in context.candidates) or should_stop(context.v_ego_mps, 0.):
    return None  # Never alter the near-standstill launch/stop policy.
  stock = min(c.accel_mps2 for c in context.candidates)
  cap = float(get_max_accel(context.v_ego_mps)) * CAP_FRACTION
  if not finite_number(cap) or not 0 < cap < stock or should_stop(context.v_ego_mps, cap):
    return None
  return cap


class OfflineComfortPlanner(LongitudinalPlanner):
  """Uses the existing pre-arbitration observer hook ONLY in synthetic tools.

The pinned planner consumes appended cruise-cap candidates with its own min,
original stop OR, global clip and same-tick feedback. No copied update method,
post-control filter, new physical delay or runtime constructor option is added.
The CP label is a misuse guard, not authentication or an arbitrary-code sandbox.
"""
  def __init__(self, CP, *args, experiment_enabled=False, **kwargs):
    if type(experiment_enabled) is not bool or CP.carFingerprint != 'SYNTHETIC_PARITY_ONLY':
      raise ValueError('SYNTHETIC_COMFORT_ONLY')
    source = Path(inspect.getfile(LongitudinalPlanner)).read_bytes()
    if hashlib.sha256(source).hexdigest() != PLANNER_SHA256:
      raise ValueError('UNREVIEWED_PLANNER_SEAM')
    if 'cyber_long_config' in kwargs:
      raise ValueError('EXPERIMENT_OWNS_DIAGNOSTIC_MODE')
    self.last_cap = None
    self.pre_feedback_speed = None
    self.experiment_enabled = experiment_enabled
    super().__init__(CP, *args, cyber_long_config=CyberLongConfig(
      mode=CyberLongMode.OBSERVE_ONLY if experiment_enabled else CyberLongMode.DISABLED), **kwargs)

  def _observe_stock(self, sm, candidates, reset_state, v_ego, v_cruise):
    self.last_cap = None
    self.pre_feedback_speed = float(self.v_desired_filter.x)
    super()._observe_stock(sm, candidates, reset_state, v_ego, v_cruise)
    observation = self.cyber_long_policy.last_observation
    if observation is None or not self.experiment_enabled:
      return
    self.last_cap = positive_accel_cap(observation.context)
    if self.last_cap is not None:
      candidates.append((self.last_cap, LongitudinalPlanSource.cruise, False))
