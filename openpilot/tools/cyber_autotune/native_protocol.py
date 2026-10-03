"""Strict local worker protocol. Identity bindings are not qualification tokens."""
import base64
import hashlib
import json
import math
from pathlib import Path
import re


MAX_REQUEST_BYTES = 4 * 1024 * 1024
MAX_CP_BYTES = 1024 * 1024
MAX_FRAMES = 10000
TIMESTEP_NS = 10_000_000
FINGERPRINT = 'HYUNDAI_SANTA_FE_2022'
SOURCE_FILES = (
  'openpilot/selfdrive/controls/lib/latcontrol_torque.py',
  'openpilot/selfdrive/controls/lib/latcontrol.py',
  'openpilot/common/pid.py', 'openpilot/common/filter_simple.py',
  'opendbc_repo/opendbc/car/interfaces.py', 'opendbc_repo/opendbc/car/vehicle_model.py',
  'opendbc_repo/opendbc/car/hyundai/interface.py', 'opendbc_repo/opendbc/car/lateral.py',
  'opendbc_repo/opendbc/car/car.capnp',
)
FLAGS = ('active', 'safety_limited', 'curvature_limited', 'steering_pressed')
NUMBERS = ('speed_mps', 'accel_mps2', 'angle_deg', 'rate_deg_s', 'driver_torque',
           'roll_rad', 'angle_offset_deg', 'stiffness_factor', 'steer_ratio',
           'desired_curvature_1pm', 'lateral_delay_s')


def finite(value):
  try:
    return type(value) in (int, float) and math.isfinite(value)
  except OverflowError:
    return False


def digest(value):
  return hashlib.sha256(value).hexdigest()


def canonical(value):
  return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def _keys(value, expected):
  if type(value) is not dict or set(value) != set(expected):
    raise ValueError('INVALID_FIELDS')


def _hex(value, length):
  return type(value) is str and re.fullmatch('[0-9a-f]{' + str(length) + '}', value) is not None


def validate_request(request):
  _keys(request, ('version', 'source', 'car_params_base64', 'car_params_sha256', 'fingerprint', 'frames'))
  if type(request['version']) is not int or request['version'] != 1 or request['fingerprint'] != FINGERPRINT:
    raise ValueError('UNSUPPORTED_CONTRACT')
  source = request['source']
  _keys(source, ('root', 'head', 'opendbc_head', 'files'))
  if type(source['root']) is not str or not Path(source['root']).is_absolute():
    raise ValueError('INVALID_SOURCE_ROOT')
  if not _hex(source['head'], 40) or not _hex(source['opendbc_head'], 40):
    raise ValueError('INVALID_SOURCE_REVISION')
  _keys(source['files'], SOURCE_FILES)
  if not all(_hex(value, 64) for value in source['files'].values()):
    raise ValueError('INVALID_SOURCE_DIGEST')
  if type(request['car_params_base64']) is not str or not _hex(request['car_params_sha256'], 64):
    raise ValueError('INVALID_CP_BINDING')
  if len(request['car_params_base64']) > 4 * ((MAX_CP_BYTES + 2) // 3):
    raise ValueError('CP_TOO_LARGE')
  try:
    raw = base64.b64decode(request['car_params_base64'], validate=True)
  except (ValueError, UnicodeEncodeError) as exc:
    raise ValueError('INVALID_CP_ENCODING') from exc
  if (not 0 < len(raw) <= MAX_CP_BYTES or base64.b64encode(raw).decode() != request['car_params_base64'] or
      digest(raw) != request['car_params_sha256']):
    raise ValueError('CP_DIGEST_MISMATCH')
  frames = request['frames']
  if type(frames) is not list or not 2 <= len(frames) <= MAX_FRAMES:
    raise ValueError('INVALID_FRAME_COUNT')
  previous = None
  for frame in frames:
    _keys(frame, ('time_ns', *FLAGS, *NUMBERS))
    timestamp = frame['time_ns']
    if type(timestamp) is not int or not 0 <= timestamp < 2 ** 63:
      raise ValueError('INVALID_TIMESTAMP')
    if previous is not None and timestamp - previous != TIMESTEP_NS:
      raise ValueError('NONUNIFORM_TIME')
    previous = timestamp
    if any(type(frame[name]) is not bool for name in FLAGS) or any(not finite(frame[name]) for name in NUMBERS):
      raise ValueError('INVALID_FRAME_VALUE')
    if (frame['speed_mps'] < 0 or frame['lateral_delay_s'] < 0 or
        frame['stiffness_factor'] <= 0 or frame['steer_ratio'] <= 0):
      raise ValueError('INVALID_FRAME_DOMAIN')


def _unique_pairs(pairs):
  result = {}
  for key, value in pairs:
    if key in result:
      raise ValueError('DUPLICATE_JSON_KEY')
    result[key] = value
  return result


def _invalid_constant(_value):
  raise ValueError('NONFINITE_JSON')


def decode_request(payload: bytes) -> dict:
  if type(payload) is not bytes or not 0 < len(payload) <= MAX_REQUEST_BYTES:
    raise ValueError('INVALID_REQUEST_SIZE')
  try:
    request = json.loads(payload.decode('utf-8'), object_pairs_hook=_unique_pairs, parse_constant=_invalid_constant)
    validate_request(request)
  except (UnicodeError, RecursionError) as exc:
    raise ValueError('INVALID_JSON') from exc
  return request


def encode_request(request: dict) -> bytes:
  validate_request(request)
  payload = canonical(request)
  if len(payload) > MAX_REQUEST_BYTES:
    raise ValueError('INVALID_REQUEST_SIZE')
  return payload
