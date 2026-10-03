"""Strict requested-acceleration diagnostic protocol, never actuation authority."""
import base64
import json
from pathlib import Path

if __package__:
  from .native_protocol import (MAX_CP_BYTES, MAX_FRAMES, MAX_REQUEST_BYTES, TIMESTEP_NS, FINGERPRINT,
                                _hex, _invalid_constant, _keys, _unique_pairs, canonical, digest, finite)
else:  # standalone isolated worker: only its fixed trusted sibling directory
  from native_protocol import (MAX_CP_BYTES, MAX_FRAMES, MAX_REQUEST_BYTES, TIMESTEP_NS, FINGERPRINT,
                               _hex, _invalid_constant, _keys, _unique_pairs, canonical, digest, finite)


# Frozen observation of opendbc4134c0d1 interfaces.py's PID envelope (m/s^2).
# NOT panda safety, a tuning parameter, or permission to enlarge native limits.
EXPECTED_ACCEL_LIMITS = (-3.5, 2.0)
SOURCE_FILES = (
  'openpilot/selfdrive/controls/controlsd.py',
  'openpilot/selfdrive/controls/lib/longcontrol.py',
  'openpilot/selfdrive/controls/lib/drive_helpers.py',
  'openpilot/selfdrive/modeld/constants.py',
  'openpilot/common/pid.py', 'openpilot/common/realtime.py', 'openpilot/common/constants.py',
  'openpilot/cereal/__init__.py', 'openpilot/cereal/log.capnp', 'openpilot/cereal/custom.capnp',
  'opendbc_repo/opendbc/car/__init__.py', 'opendbc_repo/opendbc/car/structs.py',
  'opendbc_repo/opendbc/car/car.capnp', 'opendbc_repo/opendbc/car/interfaces.py',
  'opendbc_repo/opendbc/car/hyundai/interface.py',
)
FLAGS = ('enabled', 'override_longitudinal', 'brake_pressed', 'cruise_standstill', 'should_stop')
NUMBERS = ('speed_mps', 'accel_mps2', 'cruise_speed_kph', 'a_target_mps2')


def validate_request(request: dict) -> None:
  _keys(request, ('version', 'kind', 'source', 'car_params_base64', 'car_params_sha256', 'fingerprint',
                  'openpilot_longitudinal_control', 'frames'))
  if (type(request['version']) is not int or request['version'] != 1 or
      type(request['kind']) is not str or request['kind'] != 'longcontrol' or
      type(request['fingerprint']) is not str or request['fingerprint'] != FINGERPRINT or
      type(request['openpilot_longitudinal_control']) is not bool):
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
  encoded = request['car_params_base64']
  if type(encoded) is not str or not _hex(request['car_params_sha256'], 64):
    raise ValueError('INVALID_CP_BINDING')
  if len(encoded) > 4 * ((MAX_CP_BYTES + 2) // 3):
    raise ValueError('CP_TOO_LARGE')
  try:
    raw = base64.b64decode(encoded, validate=True)
  except (ValueError, UnicodeError) as error:
    raise ValueError('INVALID_CP_ENCODING') from error
  if (not 0 < len(raw) <= MAX_CP_BYTES or base64.b64encode(raw).decode() != encoded or
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
    if frame['speed_mps'] < 0 or frame['cruise_speed_kph'] < 0:
      raise ValueError('INVALID_FRAME_DOMAIN')


def encode_request(request: dict) -> bytes:
  validate_request(request)
  payload = canonical(request)
  if len(payload) > MAX_REQUEST_BYTES:
    raise ValueError('INVALID_REQUEST_SIZE')
  return payload


def decode_request(payload: bytes) -> dict:
  if type(payload) is not bytes or not 0 < len(payload) <= MAX_REQUEST_BYTES:
    raise ValueError('INVALID_REQUEST_SIZE')
  try:
    request = json.loads(payload.decode('utf-8'), object_pairs_hook=_unique_pairs, parse_constant=_invalid_constant)
    validate_request(request)
  except (UnicodeError, RecursionError) as error:
    raise ValueError('INVALID_JSON') from error
  return request
