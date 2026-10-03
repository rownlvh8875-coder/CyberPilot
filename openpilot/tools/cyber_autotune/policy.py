"""Authoritative offline classification, never a runtime permission registry.

Names are Cyber policy identifiers, not Params keys. Source symbols identify
owners/consumers, not empirically reviewed values. No setters or apply path.
"""
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType

from openpilot.tools.cyber_autotune.contracts import PARAMETER_UNITS


class ParameterClass(StrEnum):
  AUTO_ALLOWED = 'AUTO_ALLOWED'
  ONLINE_ONLY = 'ONLINE_ONLY'
  OFFLINE_ONLY = 'OFFLINE_ONLY'
  USER_PREFERENCE = 'USER_PREFERENCE'
  SAFETY_LOCKED = 'SAFETY_LOCKED'
  STATIC = 'STATIC'


@dataclass(frozen=True)
class ParameterPolicy:
  name: str
  unit: str
  classification: ParameterClass
  owner: str
  source_symbol: str


def _policies() -> tuple[ParameterPolicy, ...]:
  pc = ParameterClass
  torque = 'openpilot/selfdrive/locationd/torqued.py:TorqueEstimator'
  vehicle = 'openpilot/selfdrive/locationd/paramsd.py:ParamsLearner'
  controller = 'openpilot/selfdrive/controls/lib/latcontrol_torque.py:LatControlTorque'
  long_params = 'openpilot/selfdrive/controls/lib/cyber_long/params.py:PARAMETER_METADATA'
  hkg = 'opendbc_repo/opendbc/car/hyundai/values.py:CarControllerParams'
  # Aliases below are deliberately locked policy concepts, not tunable keys.
  locked = (
    ('steering_limit', 'normalized_command', controller), ('torque_limit', 'normalized_command', controller),
    ('curvature_limit', '1/m', 'openpilot/selfdrive/controls/controlsd.py:Controls.state_control'),
    ('lateral_jerk_limit', 'm/s^3', 'openpilot/selfdrive/controls/controlsd.py:Controls.state_control'),
    ('can_driver_allowance', 'native_command', hkg), ('driver_override_gate', 'bool', 'openpilot/selfdrive/controls/controlsd.py:Controls'),
    ('engagement_gate', 'bool', 'openpilot/selfdrive/selfdrived/selfdrived.py:SelfdriveD'),
    ('safety.accel_min', 'm/s^2', long_params), ('safety.accel_max', 'm/s^2', long_params),
    ('safety_flags', 'bitmask', 'opendbc_repo/opendbc/car/structs.py:CarParams'),
    ('can_authority', 'permission', 'opendbc_repo/opendbc/safety/safety.h:safety_tx_hook'),
    ('steer_max', 'native_command', hkg), ('steer_delta_up', 'native_command/frame', hkg),
    ('steer_delta_down', 'native_command/frame', hkg),
  )
  return (
    *(ParameterPolicy(name, unit, pc.AUTO_ALLOWED, 'torqued', torque) for name, unit in PARAMETER_UNITS.items()),
    ParameterPolicy('lateral_delay_s', 's', pc.ONLINE_ONLY, 'lagd', 'openpilot/selfdrive/locationd/lagd.py:LateralLagEstimator'),
    *(ParameterPolicy(name, unit, pc.ONLINE_ONLY, 'paramsd', vehicle) for name, unit in (
      ('steer_ratio', 'ratio'), ('stiffness_factor', 'ratio'), ('angle_offset_deg', 'deg'), ('roll_rad', 'rad'))),
    *(ParameterPolicy(name, unit, pc.OFFLINE_ONLY, 'latcontrol_torque', controller) for name, unit in (
      ('torque_kp', 'normalized_command/(m/s^2)'), ('torque_ki', 'normalized_command/(m/s)'))),
    ParameterPolicy('vehicle.longitudinal_actuator_delay', 's', pc.OFFLINE_ONLY, 'vehicle_interface', long_params),
    ParameterPolicy('controller.acceleration_integral_gain', '1/s', pc.OFFLINE_ONLY, 'longcontrol', long_params),
    ParameterPolicy('user.personality', 'enum', pc.USER_PREFERENCE, 'user', long_params),
    ParameterPolicy('user_lane_offset', 'm', pc.USER_PREFERENCE, 'user', 'docs/STEP7_ZOOMPILOT_LATERAL_REVIEW.md'),
    *(ParameterPolicy(name, unit, pc.STATIC, 'configuration', source) for name, unit, source in (
      ('vehicle_fingerprint', 'identity', 'opendbc_repo/opendbc/car/structs.py:CarParams'),
      ('software_revision', 'identity', 'Git HEAD and dirty-overlay digest'),
      ('model_revision', 'identity', 'openpilot/selfdrive/modeld/modeld.py'),
      ('configuration_revision', 'identity', 'openpilot/tools/cyber_autotune/contracts.py:MetricContract'),
      ('wheelbase', 'm', 'opendbc_repo/opendbc/car/vehicle_model.py:VehicleModel'))),
    *(ParameterPolicy(name, unit, pc.SAFETY_LOCKED, 'safety', source) for name, unit, source in locked),
  )


PARAMETER_POLICIES = MappingProxyType({policy.name: policy for policy in _policies()})


def lookup_policy(name: str) -> ParameterPolicy | None:
  return PARAMETER_POLICIES.get(name) if type(name) is str else None


def offline_proposal_permitted(name: str) -> bool:
  """Local representation only. Evidence and runtime authority are never granted."""
  policy = lookup_policy(name)
  return policy is not None and name in PARAMETER_UNITS and policy.classification is ParameterClass.AUTO_ALLOWED
