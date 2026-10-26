"""Strict request contract for isolated native curvature/yaw transcript production."""
import json
import math

from openpilot.tools.cyber_autotune.native_protocol import (
  MAX_REQUEST_BYTES,
  _invalid_constant,
  _keys,
  _unique_pairs,
  canonical,
  digest,
  finite,
  validate_request as validate_native_request,
)


PLANT_PATH = 'openpilot/tools/cyber_autotune/curvature_yaw_plant.py'
ADAPTER_PATH = 'openpilot/tools/cyber_autotune/curvature_yaw_closed_loop.py'
SUPPORT_FILES = (
  PLANT_PATH,
  ADAPTER_PATH,
  'openpilot/tools/cyber_autotune/curvature_yaw_native_protocol.py',
  'openpilot/tools/cyber_autotune/curvature_yaw_native_worker.py',
  'openpilot/tools/cyber_autotune/native_worker.py',
  'openpilot/tools/cyber_autotune/source_imports.py',
  'openpilot/tools/cyber_autotune/worker_resources.py',
)
CANDIDATE_FILES = (
  'openpilot/tools/cyber_autotune/curvature_yaw_candidate.py',
  'openpilot/tools/cyber_autotune/a1_schedule.py',
  'openpilot/selfdrive/controls/lib/cyber_lateral/speed_aware_tune.py',
)


def support_paths(request):
  return SUPPORT_FILES + (CANDIDATE_FILES if request.get('version') == 2 else ())


PLANT_KEYS = (
  'dt_s', 'delay_steps', 'min_speed_mps', 'max_speed_mps', 'command_limit',
  'curvature_intercept_1pm', 'curvature_ar', 'command_gain_1pm',
  'command_speed_gain_s_per_m2', 'command_inv_speed_gain_per_s',
  'roll_gain_1pm_per_rad', 'yaw_ar', 'yaw_bias_rad_s',
)
STATE_KEYS = ('curvature_1pm', 'yaw_rate_rad_s', 'command_history', 'heading_rad', 'pose_y_m')


def _sha256(value) -> bool:
  return type(value) is str and len(value) == 64 and all(char in '0123456789abcdef' for char in value)


def _validate_plant(config):
  _keys(config, PLANT_KEYS)
  if type(config['delay_steps']) is not int or not 0 <= config['delay_steps'] <= 10_000:
    raise ValueError('INVALID_PLANT_DELAY')
  numbers = tuple(config[key] for key in PLANT_KEYS if key != 'delay_steps')
  if not all(finite(value) for value in numbers):
    raise ValueError('INVALID_PLANT_VALUE')
  if not 0.0 < config['dt_s'] <= 0.1:
    raise ValueError('INVALID_PLANT_DT')
  if not 0.0 < config['min_speed_mps'] < config['max_speed_mps']:
    raise ValueError('INVALID_PLANT_SPEED_DOMAIN')
  if not 0.0 < config['command_limit'] <= 1.0:
    raise ValueError('INVALID_PLANT_COMMAND_DOMAIN')
  if not abs(config['curvature_ar']) < 1.0 or not 0.0 <= config['yaw_ar'] < 1.0:
    raise ValueError('INVALID_PLANT_STABILITY')


def _validate_state(state, config):
  _keys(state, STATE_KEYS)
  if not all(finite(state[key]) for key in ('curvature_1pm', 'yaw_rate_rad_s', 'heading_rad', 'pose_y_m')):
    raise ValueError('INVALID_INITIAL_STATE')
  history = state['command_history']
  if type(history) is not list or len(history) != config['delay_steps']:
    raise ValueError('INVALID_INITIAL_HISTORY')
  if not all(finite(value) and abs(value) <= config['command_limit'] for value in history):
    raise ValueError('INVALID_INITIAL_HISTORY')


def validate_request(request):
  if type(request) is not dict or type(request.get('version')) is not int or request['version'] not in (1, 2):
    raise ValueError('UNSUPPORTED_CONTRACT')
  fields = ('version', 'native', 'support_files', 'plant_config', 'initial_state', 'controller_to_plant_sign')
  _keys(request, fields + (('controller',) if request['version'] == 2 else ()))
  if request['version'] == 2:
    from openpilot.tools.cyber_autotune.curvature_yaw_candidate import validate_controller
    validate_controller(request['controller'])
  validate_native_request(request['native'])
  frames = request['native']['frames']
  if frames[0]['time_ns'] != 0:
    raise ValueError('NONZERO_TIME_ORIGIN')
  if any(frame['angle_deg'] != 0.0 or frame['rate_deg_s'] != 0.0 for frame in frames):
    raise ValueError('RECORDED_STEERING_INPUT_FORBIDDEN')

  support = request['support_files']
  _keys(support, support_paths(request))
  if not all(_sha256(value) for value in support.values()):
    raise ValueError('INVALID_SUPPORT_FILE_BINDING')

  _validate_plant(request['plant_config'])
  _validate_state(request['initial_state'], request['plant_config'])
  if not math.isclose(
    request['plant_config']['dt_s'],
    10_000_000 * 1e-9,
    rel_tol=0.0,
    abs_tol=1e-12,
  ):
    raise ValueError('PLANT_NATIVE_TIMESTEP_MISMATCH')
  sign = request['controller_to_plant_sign']
  if type(sign) not in (int, float) or float(sign) not in (-1.0, 1.0):
    raise ValueError('INVALID_SIGN_CONVENTION')


def controller_identity_sha256(request) -> str:
  validate_request(request)
  native = request['native']
  identity = {
    'source_head': native['source']['head'],
    'opendbc_head': native['source']['opendbc_head'],
    'source_files': native['source']['files'],
    'car_params_sha256': native['car_params_sha256'],
    'fingerprint': native['fingerprint'],
  }
  if request['version'] == 2:
    identity['controller'] = request['controller']
    identity['candidate_sources'] = {name: request['support_files'][name] for name in CANDIDATE_FILES}
  return digest(canonical(identity))


def producer_identity_sha256(request) -> str:
  validate_request(request)
  return digest(canonical({
    'support_files': request['support_files'],
    'controller_identity_sha256': controller_identity_sha256(request),
  }))


def encode_request(request) -> bytes:
  validate_request(request)
  payload = canonical(request)
  if not 0 < len(payload) <= MAX_REQUEST_BYTES:
    raise ValueError('INVALID_REQUEST_SIZE')
  return payload


def decode_request(payload: bytes) -> dict:
  if type(payload) is not bytes or not 0 < len(payload) <= MAX_REQUEST_BYTES:
    raise ValueError('INVALID_REQUEST_SIZE')
  try:
    request = json.loads(
      payload.decode('utf-8'),
      object_pairs_hook=_unique_pairs,
      parse_constant=_invalid_constant,
    )
    validate_request(request)
  except (UnicodeError, RecursionError) as exc:
    raise ValueError('INVALID_JSON') from exc
  return request
