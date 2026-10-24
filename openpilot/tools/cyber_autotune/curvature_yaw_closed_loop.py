"""Evidence-bound transcript adapter for the curvature/yaw offline plant.

This module never executes a controller callback. It verifies an immutable
controller transcript whose feedback hashes must match the adapter-computed plant
state at every step, then emits the existing structural ClosedLoopReceipt. It has
no CAN, Params, profile, runtime, device, network, subprocess, or vehicle-write
API. Producer authenticity and producer-side non-actuation remain separate
external evidence requirements.
"""
from dataclasses import asdict, dataclass, field
import hashlib
import json
import math

from openpilot.tools.cyber_autotune.contracts import finite_number, is_sha256
from openpilot.tools.cyber_autotune.curvature_yaw_plant import (
  CurvatureYawPlantConfig,
  CurvatureYawPlantState,
  observe_curvature_yaw_step,
)
from openpilot.tools.cyber_autotune.lateral_closed_loop import (
  ClosedLoopBinding,
  ClosedLoopDomain,
  ClosedLoopFrame,
  ClosedLoopReceipt,
  ClosedLoopSample,
  admit_closed_loop_receipt,
  frames_sha256,
  timebase_sha256,
  trace_sha256,
)


@dataclass(frozen=True)
class CurvatureYawClosedLoopState:
  plant_state: CurvatureYawPlantState
  heading_rad: float
  pose_y_m: float


@dataclass(frozen=True)
class CurvatureYawControllerFeedback:
  step_index: int
  time_s: float
  curvature_1pm: float
  yaw_rate_rad_s: float
  lateral_accel_mps2: float
  heading_rad: float
  pose_y_m: float


@dataclass(frozen=True)
class CurvatureYawControllerStep:
  step_index: int
  time_s: float
  feedback_sha256: str
  requested_normalized_torque: float


@dataclass(frozen=True)
class CurvatureYawRunContract:
  controller_identity_sha256: str
  expected_plant_config_sha256: str
  expected_initial_state_sha256: str
  expected_controller_transcript_sha256: str
  controller_to_plant_sign: float
  version: int = 1


@dataclass(frozen=True)
class CurvatureYawRunResult:
  status: str
  blockers: tuple[str, ...]
  receipt: ClosedLoopReceipt | None = None
  plant_config_sha256: str | None = None
  initial_state_sha256: str | None = None
  controller_transcript_sha256: str | None = None
  final_state_sha256: str | None = None
  envelope_sha256: str | None = None
  structural_admission_pass: bool = False
  qualified_closed_loop: bool = field(default=False, init=False)
  performance_qualified: bool = field(default=False, init=False)
  vehicle_or_can_write: bool = field(default=False, init=False)
  parameter_write: bool = field(default=False, init=False)
  runtime_accepted: bool = field(default=False, init=False)
  promotable: bool = field(default=False, init=False)


def _canonical(value) -> bytes:
  return json.dumps(
    value, sort_keys=True, separators=(',', ':'), allow_nan=False,
  ).encode()


def _digest(value) -> str:
  return hashlib.sha256(_canonical(value)).hexdigest()


def plant_config_sha256(config: CurvatureYawPlantConfig) -> str:
  if type(config) is not CurvatureYawPlantConfig:
    raise ValueError('INVALID_PLANT_CONFIG')
  return _digest(asdict(config))


def closed_loop_state_sha256(state: CurvatureYawClosedLoopState) -> str:
  if type(state) is not CurvatureYawClosedLoopState:
    raise ValueError('INVALID_INITIAL_STATE')
  return _digest(asdict(state))


def controller_feedback_sha256(feedback: CurvatureYawControllerFeedback) -> str:
  if type(feedback) is not CurvatureYawControllerFeedback:
    raise ValueError('INVALID_CONTROLLER_FEEDBACK')
  return _digest(asdict(feedback))


def controller_transcript_sha256(
  transcript: tuple[CurvatureYawControllerStep, ...],
) -> str:
  if (
    type(transcript) is not tuple
    or not transcript
    or not all(type(step) is CurvatureYawControllerStep for step in transcript)
  ):
    raise ValueError('INVALID_CONTROLLER_TRANSCRIPT')
  return _digest([asdict(step) for step in transcript])


def _blocked(
  reason: str,
  *,
  plant_hash: str | None = None,
  state_hash: str | None = None,
  transcript_hash: str | None = None,
) -> CurvatureYawRunResult:
  return CurvatureYawRunResult(
    status='BLOCKED',
    blockers=(reason,),
    plant_config_sha256=plant_hash,
    initial_state_sha256=state_hash,
    controller_transcript_sha256=transcript_hash,
  )


def _contract_valid(contract) -> bool:
  return (
    type(contract) is CurvatureYawRunContract
    and type(contract.version) is int and contract.version == 1
    and is_sha256(contract.controller_identity_sha256)
    and is_sha256(contract.expected_plant_config_sha256)
    and is_sha256(contract.expected_initial_state_sha256)
    and is_sha256(contract.expected_controller_transcript_sha256)
    and type(contract.controller_to_plant_sign) in (int, float)
    and float(contract.controller_to_plant_sign) in (-1.0, 1.0)
  )


def _initial_state_valid(state) -> bool:
  return (
    type(state) is CurvatureYawClosedLoopState
    and type(state.plant_state) is CurvatureYawPlantState
    and finite_number(state.plant_state.curvature_1pm)
    and finite_number(state.plant_state.yaw_rate_rad_s)
    and type(state.plant_state.command_history) is tuple
    and all(finite_number(value) for value in state.plant_state.command_history)
    and finite_number(state.heading_rad)
    and finite_number(state.pose_y_m)
  )


def _transcript_shape_valid(
  transcript: tuple[CurvatureYawControllerStep, ...],
  frames: tuple[ClosedLoopFrame, ...],
) -> bool:
  if (
    type(transcript) is not tuple
    or len(transcript) != len(frames)
    or not transcript
  ):
    return False
  return all(
    type(step) is CurvatureYawControllerStep
    and type(step.step_index) is int
    and finite_number(step.time_s)
    and is_sha256(step.feedback_sha256)
    and finite_number(step.requested_normalized_torque)
    for step in transcript
  )


def _domain_matches_plant(
  domain: ClosedLoopDomain,
  config: CurvatureYawPlantConfig,
) -> bool:
  if type(domain) is not ClosedLoopDomain or type(config) is not CurvatureYawPlantConfig:
    return False
  try:
    physical_delay_s = config.delay_steps * config.dt_s
    return (
      math.isclose(domain.dt_s, config.dt_s, rel_tol=0.0, abs_tol=1e-12)
      and math.isclose(
        domain.physical_actuator_delay_s, physical_delay_s,
        rel_tol=0.0, abs_tol=1e-12,
      )
      and config.min_speed_mps <= domain.min_speed_mps
      and domain.max_speed_mps <= config.max_speed_mps
      and domain.normalized_command_limit <= config.command_limit
    )
  except (OverflowError, TypeError, ValueError):
    return False


def _feedback(
  state: CurvatureYawClosedLoopState,
  frame: ClosedLoopFrame,
) -> CurvatureYawControllerFeedback:
  return CurvatureYawControllerFeedback(
    step_index=frame.step_index,
    time_s=frame.time_s,
    curvature_1pm=float(state.plant_state.curvature_1pm),
    yaw_rate_rad_s=float(state.plant_state.yaw_rate_rad_s),
    lateral_accel_mps2=float(state.plant_state.yaw_rate_rad_s) * float(frame.speed_mps),
    heading_rad=float(state.heading_rad),
    pose_y_m=float(state.pose_y_m),
  )


def run_curvature_yaw_closed_loop(
  domain: ClosedLoopDomain,
  frames: tuple[ClosedLoopFrame, ...],
  binding: ClosedLoopBinding,
  plant_config: CurvatureYawPlantConfig,
  initial_state: CurvatureYawClosedLoopState,
  contract: CurvatureYawRunContract,
  controller_transcript: tuple[CurvatureYawControllerStep, ...],
  *,
  arm: str = 'CYBER_CANDIDATE',
  plant_calibration_status: str = 'DESCRIPTIVE_CALIBRATION_EVIDENCE',
) -> CurvatureYawRunResult:
  """Verify one immutable controller/plant transcript without executing a controller.

  Each transcript row is bound to the exact feedback state observed immediately
  before that row's command. A mismatch fails closed before the plant step. This
  verifies transcript/plant causal consistency only; it does not authenticate
  the external producer or establish that producer-side execution was non-actuating.
  """
  if not _contract_valid(contract):
    return _blocked('INVALID_CONTRACT')
  if type(binding) is not ClosedLoopBinding:
    return _blocked('INVALID_BINDING')
  if type(frames) is not tuple or not frames or not all(type(frame) is ClosedLoopFrame for frame in frames):
    return _blocked('INVALID_FRAMES')
  if not _initial_state_valid(initial_state):
    return _blocked('INVALID_INITIAL_STATE')
  if not _transcript_shape_valid(controller_transcript, frames):
    return _blocked('INVALID_CONTROLLER_TRANSCRIPT')

  try:
    plant_hash = plant_config_sha256(plant_config)
    state_hash = closed_loop_state_sha256(initial_state)
    transcript_hash = controller_transcript_sha256(controller_transcript)
  except (TypeError, ValueError, OverflowError):
    return _blocked('INVALID_EVIDENCE_INPUT')

  if contract.expected_plant_config_sha256 != plant_hash:
    return _blocked(
      'PLANT_CONFIG_BINDING_MISMATCH',
      plant_hash=plant_hash, state_hash=state_hash, transcript_hash=transcript_hash,
    )
  if contract.expected_initial_state_sha256 != state_hash:
    return _blocked(
      'INITIAL_STATE_BINDING_MISMATCH',
      plant_hash=plant_hash, state_hash=state_hash, transcript_hash=transcript_hash,
    )
  if contract.expected_controller_transcript_sha256 != transcript_hash:
    return _blocked(
      'CONTROLLER_TRANSCRIPT_BINDING_MISMATCH',
      plant_hash=plant_hash, state_hash=state_hash, transcript_hash=transcript_hash,
    )
  if binding.controller_sha256 != contract.controller_identity_sha256:
    return _blocked(
      'CONTROLLER_BINDING_MISMATCH',
      plant_hash=plant_hash, state_hash=state_hash, transcript_hash=transcript_hash,
    )
  if binding.reset_sha256 != state_hash:
    return _blocked(
      'RESET_BINDING_MISMATCH',
      plant_hash=plant_hash, state_hash=state_hash, transcript_hash=transcript_hash,
    )
  if not _domain_matches_plant(domain, plant_config):
    return _blocked(
      'PLANT_DOMAIN_MISMATCH',
      plant_hash=plant_hash, state_hash=state_hash, transcript_hash=transcript_hash,
    )

  try:
    input_hash = frames_sha256(frames)
    clock_hash = timebase_sha256(frames)
  except (TypeError, ValueError, OverflowError):
    return _blocked(
      'INVALID_FRAMES',
      plant_hash=plant_hash, state_hash=state_hash, transcript_hash=transcript_hash,
    )

  if binding.domain_sha256 != domain.identity_sha256:
    return _blocked(
      'DOMAIN_BINDING_MISMATCH',
      plant_hash=plant_hash, state_hash=state_hash, transcript_hash=transcript_hash,
    )
  if binding.inputs_sha256 != input_hash:
    return _blocked(
      'INPUT_BINDING_MISMATCH',
      plant_hash=plant_hash, state_hash=state_hash, transcript_hash=transcript_hash,
    )
  if binding.timebase_sha256 != clock_hash:
    return _blocked(
      'TIMEBASE_BINDING_MISMATCH',
      plant_hash=plant_hash, state_hash=state_hash, transcript_hash=transcript_hash,
    )

  state = initial_state
  samples = []
  limit = min(float(domain.normalized_command_limit), float(plant_config.command_limit))
  sign = float(contract.controller_to_plant_sign)

  for frame, controller_step in zip(frames, controller_transcript, strict=True):
    feedback = _feedback(state, frame)
    if (
      controller_step.step_index != frame.step_index
      or not math.isclose(controller_step.time_s, frame.time_s, rel_tol=0.0, abs_tol=1e-12)
    ):
      return _blocked(
        'CONTROLLER_TRANSCRIPT_TIMEBASE_MISMATCH',
        plant_hash=plant_hash, state_hash=state_hash, transcript_hash=transcript_hash,
      )
    if controller_step.feedback_sha256 != controller_feedback_sha256(feedback):
      return _blocked(
        'CONTROLLER_FEEDBACK_BINDING_MISMATCH',
        plant_hash=plant_hash, state_hash=state_hash, transcript_hash=transcript_hash,
      )

    requested = float(controller_step.requested_normalized_torque)
    if abs(requested) > limit:
      return _blocked(
        'CONTROLLER_COMMAND_OUTSIDE_DOMAIN',
        plant_hash=plant_hash, state_hash=state_hash, transcript_hash=transcript_hash,
      )

    observation = observe_curvature_yaw_step(
      plant_config,
      state.plant_state,
      command=sign * requested,
      speed_mps=frame.speed_mps,
      roll_rad=frame.roll_rad,
    )
    if observation.status != 'DESCRIPTIVE_ONLY' or observation.next_state is None:
      return _blocked(
        f'PLANT_{observation.reason}',
        plant_hash=plant_hash, state_hash=state_hash, transcript_hash=transcript_hash,
      )

    next_plant = observation.next_state
    next_heading = float(state.heading_rad) + float(next_plant.yaw_rate_rad_s) * float(domain.dt_s)
    next_pose_y = float(state.pose_y_m) + float(frame.speed_mps) * math.sin(next_heading) * float(domain.dt_s)
    if not all(math.isfinite(value) for value in (next_heading, next_pose_y)):
      return _blocked(
        'POSE_OBSERVER_INVALID',
        plant_hash=plant_hash, state_hash=state_hash, transcript_hash=transcript_hash,
      )

    applied_controller_command = sign * float(observation.delayed_command)
    samples.append(ClosedLoopSample(
      step_index=frame.step_index,
      time_s=frame.time_s,
      requested_torque=requested,
      applied_normalized_torque=applied_controller_command,
      lateral_accel_mps2=float(next_plant.yaw_rate_rad_s) * float(frame.speed_mps),
      yaw_rate_rps=float(next_plant.yaw_rate_rad_s),
      pose_y_m=next_pose_y,
    ))
    state = CurvatureYawClosedLoopState(
      plant_state=next_plant,
      heading_rad=next_heading,
      pose_y_m=next_pose_y,
    )

  samples_t = tuple(samples)
  receipt = ClosedLoopReceipt(
    arm=arm,
    binding=binding,
    outcome='COMPLETED',
    samples=samples_t,
    trace_sha256=trace_sha256(samples_t),
    plant_calibration_status=plant_calibration_status,
    plant_calibration_qualified=False,
    physical_delay_owners=('PLANT',),
    controller_delay_queue_present=False,
    sendcan_forwarded=False,
    live_can=False,
    vehicle_write=False,
    parameter_write=False,
    runtime_accepted=False,
    promotable=False,
  )
  admission = admit_closed_loop_receipt(domain, frames, receipt)
  if admission.status != 'STRUCTURAL_ADMISSION' or not admission.structural_admission_pass:
    reason = admission.blockers[0] if admission.blockers else 'UNKNOWN'
    return _blocked(
      f'RECEIPT_{reason}',
      plant_hash=plant_hash, state_hash=state_hash, transcript_hash=transcript_hash,
    )

  final_state_hash = closed_loop_state_sha256(state)
  envelope = {
    'version': contract.version,
    'controller_identity_sha256': contract.controller_identity_sha256,
    'controller_to_plant_sign': sign,
    'plant_config_sha256': plant_hash,
    'initial_state_sha256': state_hash,
    'final_state_sha256': final_state_hash,
    'domain_sha256': domain.identity_sha256,
    'inputs_sha256': input_hash,
    'timebase_sha256': clock_hash,
    'controller_transcript_sha256': transcript_hash,
    'receipt_trace_sha256': receipt.trace_sha256,
  }
  return CurvatureYawRunResult(
    status='STRUCTURAL_ADMISSION',
    blockers=admission.blockers + (
      'CONTROLLER_PRODUCER_AUTHENTICITY_UNVERIFIED',
      'CONTROLLER_PRODUCER_NONACTUATION_UNVERIFIED',
      'CURVATURE_YAW_ADAPTER_OFFLINE_ONLY',
    ),
    receipt=receipt,
    plant_config_sha256=plant_hash,
    initial_state_sha256=state_hash,
    controller_transcript_sha256=transcript_hash,
    final_state_sha256=final_state_hash,
    envelope_sha256=_digest(envelope),
    structural_admission_pass=True,
  )
