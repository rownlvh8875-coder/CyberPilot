"""Fail-closed structural contract for external lateral closed-loop evidence.

This module does not implement a plant, controller callback, metric gate, file IO,
profile write, CAN transport, runtime scheduler, or promotion path. It validates
immutable producer receipts before they may enter an offline comparison pipeline.
"""
from dataclasses import asdict, dataclass, field
import hashlib
import json

from openpilot.tools.cyber_autotune.contracts import finite_number, is_sha256


ARMS = frozenset({'UPSTREAM_BASELINE', 'CYBER_CURRENT', 'CYBER_CANDIDATE'})
MAX_FRAMES = 60_000
STRUCTURAL_BLOCKERS = (
  'PLANT_CALIBRATION_AUTHENTICITY_UNVERIFIED',
  'INDEPENDENT_REFERENCE_UNVERIFIED',
  'PERFORMANCE_GATE_NOT_EVALUATED',
)


@dataclass(frozen=True)
class ClosedLoopDomain:
  identity_sha256: str
  dt_s: float
  min_speed_mps: float
  max_speed_mps: float
  physical_actuator_delay_s: float
  physical_delay_owner: str
  normalized_command_limit: float
  version: int = 1


@dataclass(frozen=True)
class ClosedLoopBinding:
  software_sha256: str
  controller_sha256: str
  adapter_sha256: str
  plant_sha256: str
  domain_sha256: str
  inputs_sha256: str
  reset_sha256: str
  metric_sha256: str
  environment_sha256: str
  timebase_sha256: str


@dataclass(frozen=True)
class ClosedLoopFrame:
  step_index: int
  time_s: float
  speed_mps: float
  accel_mps2: float
  roll_rad: float
  desired_curvature: float
  active: bool
  steering_pressed: bool
  controller_prediction_delay_s: float


@dataclass(frozen=True)
class ClosedLoopSample:
  step_index: int
  time_s: float
  requested_torque: float
  applied_normalized_torque: float
  lateral_accel_mps2: float
  yaw_rate_rps: float
  pose_y_m: float


@dataclass(frozen=True)
class ClosedLoopReceipt:
  arm: str
  binding: ClosedLoopBinding
  outcome: str
  samples: tuple[ClosedLoopSample, ...]
  trace_sha256: str | None
  physical_delay_owners: tuple[str, ...]
  controller_delay_queue_present: bool
  sendcan_forwarded: bool
  live_can: bool
  vehicle_write: bool
  parameter_write: bool
  runtime_accepted: bool
  promotable: bool


@dataclass(frozen=True)
class ClosedLoopAdmission:
  status: str
  blockers: tuple[str, ...]
  sample_count: int = 0
  inputs_sha256: str | None = None
  trace_sha256: str | None = None
  structural_admission_pass: bool = False
  qualified_closed_loop: bool = field(default=False, init=False)
  runtime_accepted: bool = field(default=False, init=False)
  promotable: bool = field(default=False, init=False)


def _canonical(value) -> bytes:
  return json.dumps(
    value, sort_keys=True, separators=(',', ':'), allow_nan=False,
  ).encode()


def _digest(value) -> str:
  return hashlib.sha256(_canonical(value)).hexdigest()


def frames_sha256(frames: tuple[ClosedLoopFrame, ...]) -> str:
  return _digest([asdict(frame) for frame in frames])


def timebase_sha256(frames: tuple[ClosedLoopFrame, ...]) -> str:
  return _digest([
    {'step_index': frame.step_index, 'time_s': frame.time_s}
    for frame in frames
  ])


def trace_sha256(samples: tuple[ClosedLoopSample, ...]) -> str:
  return _digest([asdict(sample) for sample in samples])


def _blocked(reason: str) -> ClosedLoopAdmission:
  return ClosedLoopAdmission('BLOCKED', (reason,))


def _domain_valid(domain) -> bool:
  return (
    type(domain) is ClosedLoopDomain
    and type(domain.version) is int and domain.version == 1
    and is_sha256(domain.identity_sha256)
    and all(finite_number(value) for value in (
      domain.dt_s, domain.min_speed_mps, domain.max_speed_mps,
      domain.physical_actuator_delay_s, domain.normalized_command_limit,
    ))
    and 0.0 < domain.dt_s <= 0.1
    and 0.0 <= domain.min_speed_mps < domain.max_speed_mps
    and 0.0 < domain.physical_actuator_delay_s <= 1.0
    and domain.physical_delay_owner == 'PLANT'
    and 0.0 < domain.normalized_command_limit <= 1.0
  )


def _binding_valid(binding) -> bool:
  if type(binding) is not ClosedLoopBinding:
    return False
  return all(is_sha256(value) for value in asdict(binding).values())


def _frame_valid(frame, domain: ClosedLoopDomain) -> bool:
  return (
    type(frame) is ClosedLoopFrame
    and type(frame.step_index) is int and frame.step_index >= 0
    and all(finite_number(value) for value in (
      frame.time_s, frame.speed_mps, frame.accel_mps2, frame.roll_rad,
      frame.desired_curvature, frame.controller_prediction_delay_s,
    ))
    and type(frame.active) is bool
    and type(frame.steering_pressed) is bool
    and domain.min_speed_mps <= frame.speed_mps <= domain.max_speed_mps
    and 0.0 <= frame.controller_prediction_delay_s <= 1.0
  )


def _sample_valid(sample, domain: ClosedLoopDomain) -> bool:
  return (
    type(sample) is ClosedLoopSample
    and type(sample.step_index) is int and sample.step_index >= 0
    and all(finite_number(value) for value in (
      sample.time_s, sample.requested_torque, sample.applied_normalized_torque,
      sample.lateral_accel_mps2, sample.yaw_rate_rps, sample.pose_y_m,
    ))
    and abs(sample.requested_torque) <= domain.normalized_command_limit
    and abs(sample.applied_normalized_torque) <= domain.normalized_command_limit
  )


def _frame_timebase_valid(
  frames: tuple[ClosedLoopFrame, ...], domain: ClosedLoopDomain,
) -> bool:
  if not 0 < len(frames) <= MAX_FRAMES:
    return False
  for index, frame in enumerate(frames):
    if not _frame_valid(frame, domain):
      return False
    if frame.step_index != index:
      return False
    if abs(frame.time_s - index * domain.dt_s) > 1e-9:
      return False
  return True


def _receipt_valid(receipt) -> bool:
  return (
    type(receipt) is ClosedLoopReceipt
    and type(receipt.arm) is str and receipt.arm in ARMS
    and _binding_valid(receipt.binding)
    and type(receipt.outcome) is str
    and type(receipt.samples) is tuple
    and (receipt.trace_sha256 is None or is_sha256(receipt.trace_sha256))
    and type(receipt.physical_delay_owners) is tuple
    and all(type(owner) is str for owner in receipt.physical_delay_owners)
    and type(receipt.controller_delay_queue_present) is bool
    and all(type(value) is bool for value in (
      receipt.sendcan_forwarded, receipt.live_can, receipt.vehicle_write,
      receipt.parameter_write, receipt.runtime_accepted, receipt.promotable,
    ))
  )


def admit_closed_loop_receipt(
  domain: ClosedLoopDomain,
  frames: tuple[ClosedLoopFrame, ...],
  receipt: ClosedLoopReceipt,
) -> ClosedLoopAdmission:
  """Admit one immutable external receipt to structural offline comparison only."""
  if not _domain_valid(domain):
    return _blocked('INVALID_DOMAIN')
  if type(frames) is not tuple or not frames:
    return _blocked('INVALID_FRAMES')
  if not all(type(frame) is ClosedLoopFrame for frame in frames):
    return _blocked('INVALID_FRAMES')
  if any(not _frame_valid(frame, domain) for frame in frames):
    return _blocked('FRAME_OUTSIDE_DOMAIN')
  if not _frame_timebase_valid(frames, domain):
    return _blocked('INVALID_FRAME_TIMEBASE')
  if not _receipt_valid(receipt):
    return _blocked('INVALID_RECEIPT')
  if receipt.outcome != 'COMPLETED':
    return _blocked('RUN_NOT_COMPLETED')
  if receipt.physical_delay_owners != ('PLANT',):
    return _blocked('INVALID_PHYSICAL_DELAY_OWNERSHIP')
  if receipt.controller_delay_queue_present:
    return _blocked('DUPLICATE_ACTUATOR_DELAY_QUEUE')
  if any((
    receipt.sendcan_forwarded,
    receipt.live_can,
    receipt.vehicle_write,
    receipt.parameter_write,
    receipt.runtime_accepted,
    receipt.promotable,
  )):
    return _blocked('FORBIDDEN_AUTHORITY')

  inputs_digest = frames_sha256(frames)
  if receipt.binding.domain_sha256 != domain.identity_sha256:
    return _blocked('DOMAIN_BINDING_MISMATCH')
  if receipt.binding.inputs_sha256 != inputs_digest:
    return _blocked('INPUT_BINDING_MISMATCH')
  if receipt.binding.timebase_sha256 != timebase_sha256(frames):
    return _blocked('TIMEBASE_BINDING_MISMATCH')
  if len(receipt.samples) != len(frames):
    return _blocked('TRACE_CARDINALITY_MISMATCH')
  if any(not _sample_valid(sample, domain) for sample in receipt.samples):
    return _blocked('INVALID_TRACE_SAMPLE')
  for frame, sample in zip(frames, receipt.samples, strict=True):
    if sample.step_index != frame.step_index or abs(sample.time_s - frame.time_s) > 1e-9:
      return _blocked('TRACE_TIMEBASE_MISMATCH')

  trace_digest = trace_sha256(receipt.samples)
  if receipt.trace_sha256 != trace_digest:
    return _blocked('TRACE_DIGEST_MISMATCH')
  return ClosedLoopAdmission(
    status='STRUCTURAL_ADMISSION',
    blockers=STRUCTURAL_BLOCKERS,
    sample_count=len(receipt.samples),
    inputs_sha256=inputs_digest,
    trace_sha256=trace_digest,
    structural_admission_pass=True,
  )
