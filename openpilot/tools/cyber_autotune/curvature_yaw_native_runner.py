"""Bounded parent supervisor for isolated native curvature/yaw transcripts."""
import json
from pathlib import Path
import sys

from openpilot.tools.cyber_autotune.curvature_yaw_closed_loop import (
  CurvatureYawClosedLoopState,
  CurvatureYawControllerStep,
  CurvatureYawRunContract,
  closed_loop_state_sha256,
  controller_transcript_sha256,
  plant_config_sha256,
  run_curvature_yaw_closed_loop,
)
from openpilot.tools.cyber_autotune.curvature_yaw_native_protocol import (
  ADAPTER_PATH,
  PLANT_PATH,
  controller_identity_sha256,
  decode_request,
  encode_request,
  producer_identity_sha256,
)
from openpilot.tools.cyber_autotune.curvature_yaw_plant import (
  CurvatureYawPlantConfig,
  CurvatureYawPlantState,
)
from openpilot.tools.cyber_autotune.lateral_closed_loop import (
  ClosedLoopBinding,
  ClosedLoopDomain,
  ClosedLoopFrame,
)
from openpilot.tools.cyber_autotune.native_protocol import (
  _invalid_constant,
  _keys,
  _unique_pairs,
  canonical,
  digest,
  finite,
)
from openpilot.tools.cyber_autotune.native_runner import MAX_RESPONSE_BYTES, MAX_TIMEOUT_S, _run_process


def _sha256(value) -> bool:
  return type(value) is str and len(value) == 64 and all(char in '0123456789abcdef' for char in value)


def plant_config(request: dict) -> CurvatureYawPlantConfig:
  decode_request(encode_request(request))
  return CurvatureYawPlantConfig(**request['plant_config'])


def initial_state(request: dict) -> CurvatureYawClosedLoopState:
  decode_request(encode_request(request))
  raw = request['initial_state']
  return CurvatureYawClosedLoopState(
    CurvatureYawPlantState(
      raw['curvature_1pm'],
      raw['yaw_rate_rad_s'],
      tuple(raw['command_history']),
    ),
    raw['heading_rad'],
    raw['pose_y_m'],
  )


def closed_loop_frames(request: dict) -> tuple[ClosedLoopFrame, ...]:
  decode_request(encode_request(request))
  return tuple(
    ClosedLoopFrame(
      step_index=index,
      time_s=frame['time_ns'] * 1e-9,
      speed_mps=frame['speed_mps'],
      accel_mps2=frame['accel_mps2'],
      roll_rad=frame['roll_rad'],
      desired_curvature=frame['desired_curvature_1pm'],
      active=frame['active'],
      steering_pressed=frame['steering_pressed'],
      controller_prediction_delay_s=frame['lateral_delay_s'],
    )
    for index, frame in enumerate(request['native']['frames'])
  )


def typed_transcript(result: dict) -> tuple[CurvatureYawControllerStep, ...]:
  rows = result['controller_transcript']
  return tuple(CurvatureYawControllerStep(**row) for row in rows)


def validate_response(request: dict, result: dict) -> None:
  expected = (
    'status', 'scope', 'request_sha256', 'source_head', 'opendbc_head',
    'car_params_sha256', 'controller_identity_sha256',
    'plant_config_sha256', 'initial_state_sha256', 'support_files_sha256',
    'controller_transcript', 'controller_transcript_sha256',
    'final_state_sha256', 'runtime_accepted', 'promotable',
  )
  _keys(result, expected)
  native = request['native']
  bindings = {
    'status': 'COMPLETED',
    'scope': 'OFFLINE_NATIVE_CURVATURE_YAW_TRANSCRIPT',
    'request_sha256': digest(encode_request(request)),
    'source_head': native['source']['head'],
    'opendbc_head': native['source']['opendbc_head'],
    'car_params_sha256': native['car_params_sha256'],
    'controller_identity_sha256': controller_identity_sha256(request),
    'plant_config_sha256': plant_config_sha256(plant_config(request)),
    'initial_state_sha256': closed_loop_state_sha256(initial_state(request)),
    'support_files_sha256': digest(canonical(request['support_files'])),
  }
  if any(type(result[key]) is not str or result[key] != value for key, value in bindings.items()):
    raise ValueError('RESPONSE_BINDING_MISMATCH')
  if not _sha256(result['final_state_sha256']):
    raise ValueError('INVALID_FINAL_STATE_DIGEST')
  if result['runtime_accepted'] is not False or result['promotable'] is not False:
    raise ValueError('INVALID_RESPONSE_AUTHORITY')

  rows = result['controller_transcript']
  frames = request['native']['frames']
  if type(rows) is not list or len(rows) != len(frames):
    raise ValueError('INVALID_TRANSCRIPT_COUNT')
  for index, (frame, row) in enumerate(zip(frames, rows, strict=True)):
    _keys(row, (
      'step_index', 'time_s', 'feedback_sha256', 'requested_normalized_torque',
    ))
    if (
      type(row['step_index']) is not int
      or row['step_index'] != index
      or not finite(row['time_s'])
      or row['time_s'] != frame['time_ns'] * 1e-9
      or not _sha256(row['feedback_sha256'])
      or not finite(row['requested_normalized_torque'])
      or abs(row['requested_normalized_torque']) > request['plant_config']['command_limit']
    ):
      raise ValueError('INVALID_TRANSCRIPT_ROW')
  transcript = typed_transcript(result)
  if result['controller_transcript_sha256'] != controller_transcript_sha256(transcript):
    raise ValueError('TRANSCRIPT_DIGEST_MISMATCH')


def run_native_transcript(request: dict, *, timeout_s: float) -> dict:
  if not finite(timeout_s) or not 0 < timeout_s <= MAX_TIMEOUT_S:
    raise ValueError('INVALID_TIMEOUT')
  payload = encode_request(request)
  request = json.loads(payload)

  def failure(status):
    return {
      'status': status,
      'request_sha256': digest(payload),
      'runtime_accepted': False,
      'promotable': False,
    }

  if sys.platform != 'linux':
    return failure('UNSUPPORTED_PLATFORM')
  worker = Path(__file__).resolve().with_name('curvature_yaw_native_worker.py')
  try:
    outcome = _run_process([sys.executable, '-I', str(worker)], payload, timeout_s)
  except OSError:
    return failure('WORKER_UNAVAILABLE')
  if outcome.status == 'TIMEOUT':
    return failure('TIMEOUT')
  if outcome.status != 'EXITED' or outcome.returncode != 0:
    return failure('WORKER_FAILED')
  if not 0 < len(outcome.stdout) <= MAX_RESPONSE_BYTES:
    return failure('INVALID_RESPONSE')
  try:
    result = json.loads(
      outcome.stdout,
      object_pairs_hook=_unique_pairs,
      parse_constant=_invalid_constant,
    )
    validate_response(request, result)
  except (ValueError, UnicodeError, RecursionError):
    return failure('INVALID_RESPONSE')
  return result


def admit_native_transcript(
  request: dict,
  result: dict,
  domain: ClosedLoopDomain,
  binding: ClosedLoopBinding,
  *,
  arm: str = 'CYBER_CANDIDATE',
  plant_calibration_status: str = 'DESCRIPTIVE_CALIBRATION_EVIDENCE',
):
  """Replay a completed isolated native transcript through the public adapter."""
  validate_response(request, result)
  if type(domain) is not ClosedLoopDomain or type(binding) is not ClosedLoopBinding:
    raise ValueError('INVALID_ADMISSION_BINDING')
  if binding.software_sha256 != producer_identity_sha256(request):
    raise ValueError('PRODUCER_BINDING_MISMATCH')
  if binding.controller_sha256 != result['controller_identity_sha256']:
    raise ValueError('CONTROLLER_BINDING_MISMATCH')
  if binding.plant_sha256 != request['support_files'][PLANT_PATH]:
    raise ValueError('PLANT_IMPLEMENTATION_BINDING_MISMATCH')
  if binding.adapter_sha256 != request['support_files'][ADAPTER_PATH]:
    raise ValueError('ADAPTER_IMPLEMENTATION_BINDING_MISMATCH')

  config = plant_config(request)
  state = initial_state(request)
  contract = CurvatureYawRunContract(
    controller_identity_sha256=result['controller_identity_sha256'],
    expected_plant_config_sha256=result['plant_config_sha256'],
    expected_initial_state_sha256=result['initial_state_sha256'],
    expected_controller_transcript_sha256=result['controller_transcript_sha256'],
    controller_to_plant_sign=request['controller_to_plant_sign'],
  )
  admitted = run_curvature_yaw_closed_loop(
    domain,
    closed_loop_frames(request),
    binding,
    config,
    state,
    contract,
    typed_transcript(result),
    arm=arm,
    plant_calibration_status=plant_calibration_status,
  )
  if admitted.status == 'STRUCTURAL_ADMISSION' and admitted.final_state_sha256 != result['final_state_sha256']:
    raise ValueError('PRODUCER_ADAPTER_FINAL_STATE_MISMATCH')
  return admitted
