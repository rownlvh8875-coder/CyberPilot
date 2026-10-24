"""Frozen offline-only schemas. No candidate behavior or runtime integration."""
from dataclasses import dataclass, fields
import math
import re


def scalar(value):
  if type(value) not in (int, float) or not math.isfinite(value):
    raise ValueError('FINITE_SCALAR_REQUIRED')


def sha(value):
  if type(value) is not str or not re.fullmatch('[0-9a-f]{64}', value):
    raise ValueError('SHA256_REQUIRED')


def torque(value):
  scalar(value)
  if abs(value) > 1:
    raise ValueError('NORMALIZED_TORQUE_REQUIRED')


class ExactInput:
  @classmethod
  def parse(cls, row):
    if type(row) is not dict or set(row) != {f.name for f in fields(cls)}:
      raise ValueError('EXACT_ROLE_INPUT_WHITELIST_REQUIRED')
    return cls(**row)


@dataclass(frozen=True)
class TrajectoryInput(ExactInput):
  desired_curvature_1pm: float
  actual_curvature_1pm: float
  speed_mps: float
  roll_rad: float
  time_s: float
  dt_s: float
  active: bool
  steering_pressed: bool
  safety_limited: bool
  curvature_limited: bool

  def __post_init__(self):
    for name in ('desired_curvature_1pm', 'actual_curvature_1pm', 'speed_mps', 'roll_rad', 'time_s', 'dt_s'):
      scalar(getattr(self, name))
    if self.speed_mps < 0 or self.time_s < 0 or self.dt_s != .01:
      raise ValueError('OFFLINE_100HZ_TIMEBASE_REQUIRED')
    for name in ('active', 'steering_pressed', 'safety_limited', 'curvature_limited'):
      if type(getattr(self, name)) is not bool:
        raise ValueError('BOOLEAN_REQUIRED')


@dataclass(frozen=True)
class InterventionInput(ExactInput):
  time_s: float
  dt_s: float
  active: bool
  steering_pressed: bool
  release: bool
  reengagement: bool

  def __post_init__(self):
    scalar(self.time_s)
    scalar(self.dt_s)
    if self.time_s < 0 or self.dt_s != .01:
      raise ValueError('OFFLINE_100HZ_TIMEBASE_REQUIRED')
    for name in ('active', 'steering_pressed', 'release', 'reengagement'):
      if type(getattr(self, name)) is not bool:
        raise ValueError('BOOLEAN_REQUIRED')


@dataclass(frozen=True)
class GovernorCommand(ExactInput):
  """Deliberately excludes curvature, targets, tracking error and component observations."""
  normalized_torque: float
  core_source_sha256: str
  core_config_sha256: str

  def __post_init__(self):
    torque(self.normalized_torque)
    sha(self.core_source_sha256)
    sha(self.core_config_sha256)


@dataclass(frozen=True)
class TrajectoryAuthorityOutput:
  raw_requested_torque: float  # post-controller limit; normalized, upstream return sign
  tracking_error: float | None  # curvature 1/m, if explicitly available in future prototype
  feedforward_component: float | None  # normalized torque equivalent, if explicitly observed
  feedback_component: float | None
  friction_component: float | None
  saturation_intent: bool | None
  pre_limit_intent: float | None  # normalized equivalent, may exceed [-1,1]
  observation_status: str
  source_sha256: str
  config_sha256: str

  def __post_init__(self):
    torque(self.raw_requested_torque)
    sha(self.source_sha256)
    sha(self.config_sha256)
    values = (self.tracking_error, self.feedforward_component, self.feedback_component,
              self.friction_component, self.pre_limit_intent)
    if self.observation_status not in ('UNAVAILABLE', 'OFFLINE_PROTOTYPE_OBSERVED'):
      raise ValueError('OBSERVATION_STATUS_REQUIRED')
    if self.observation_status == 'UNAVAILABLE' and (any(v is not None for v in values) or self.saturation_intent is not None):
      raise ValueError('NO_FABRICATED_OBSERVABILITY')
    for value in values:
      if value is not None:
        scalar(value)
    if self.saturation_intent is not None and type(self.saturation_intent) is not bool:
      raise ValueError('BOOLEAN_OR_UNAVAILABLE_REQUIRED')

  def for_governor(self):
    return GovernorCommand(self.raw_requested_torque, self.source_sha256, self.config_sha256)


@dataclass(frozen=True)
class FinalOfflineTorqueCommand:
  pre_governor: float
  post_governor: float
  final_requested_torque: float
  governor_state: tuple
  saturation_reason: str
  core_source_sha256: str
  core_config_sha256: str
  governor_identity_sha256: str

  def __post_init__(self):
    for value in (self.pre_governor, self.post_governor, self.final_requested_torque):
      torque(value)
    for value in (self.core_source_sha256, self.core_config_sha256, self.governor_identity_sha256):
      sha(value)
    if self.governor_state != () or self.saturation_reason != 'DISABLED_EXACT_PASSTHROUGH':
      raise ValueError('ENABLED_GOVERNOR_NOT_AUTHORIZED')
    if not self.pre_governor == self.post_governor == self.final_requested_torque:
      raise ValueError('DISABLED_GOVERNOR_MUST_BE_EXACT')
