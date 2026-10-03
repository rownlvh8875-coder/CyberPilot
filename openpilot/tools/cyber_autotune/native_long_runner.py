"""Blocking offline LongControl supervisor, never an active-loop component."""
import json
from pathlib import Path
import sys

from openpilot.tools.cyber_autotune.native_long_protocol import EXPECTED_ACCEL_LIMITS, encode_request
from openpilot.tools.cyber_autotune.native_protocol import _invalid_constant, _keys, _unique_pairs, canonical, digest, finite
from openpilot.tools.cyber_autotune.native_runner import MAX_RESPONSE_BYTES, MAX_TIMEOUT_S, _run_process


def validate_response(request: dict, result: dict) -> None:
  _keys(result, ('status', 'scope', 'request_sha256', 'source_head', 'opendbc_head', 'car_params_sha256',
                 'samples', 'ordered_trace_sha256', 'runtime_accepted', 'promotable'))
  bindings = {'status': 'COMPLETED', 'scope': 'OFFLINE_NATIVE_REQUESTED_ACCEL',
              'request_sha256': digest(encode_request(request)), 'source_head': request['source']['head'],
              'opendbc_head': request['source']['opendbc_head'], 'car_params_sha256': request['car_params_sha256']}
  if any(type(result[key]) is not str or result[key] != value for key, value in bindings.items()):
    raise ValueError('RESPONSE_BINDING_MISMATCH')
  if result['runtime_accepted'] is not False or result['promotable'] is not False:
    raise ValueError('INVALID_RESPONSE_AUTHORITY')
  samples = result['samples']
  if type(samples) is not list or len(samples) != len(request['frames']):
    raise ValueError('INVALID_SAMPLE_COUNT')
  previous = 'off'
  for frame, row in zip(request['frames'], samples, strict=True):
    _keys(row, ('time_ns', 'requested_accel_mps2', 'long_active', 'state_before', 'state_after'))
    active = frame['enabled'] and not frame['override_longitudinal'] and request['openpilot_longitudinal_control']
    if (type(row['time_ns']) is not int or row['time_ns'] != frame['time_ns'] or
        type(row['long_active']) is not bool or row['long_active'] != active):
      raise ValueError('OUTPUT_TIME_OR_MODE_MISMATCH')
    accel = row['requested_accel_mps2']
    if not finite(accel) or not EXPECTED_ACCEL_LIMITS[0] <= accel <= EXPECTED_ACCEL_LIMITS[1]:
      raise ValueError('INVALID_NATIVE_SAMPLE')
    if (type(row['state_before']) is not str or row['state_before'] != previous or
        type(row['state_after']) is not str or row['state_after'] not in ('off', 'stopping', 'pid')):
      raise ValueError('INVALID_STATE_SEQUENCE')
    if (not active and (accel != 0 or row['state_after'] != 'off')) or (active and row['state_after'] == 'off'):
      raise ValueError('INVALID_INACTIVE_OUTPUT')
    previous = row['state_after']
  if result['ordered_trace_sha256'] != digest(canonical(samples)):
    raise ValueError('TRACE_DIGEST_MISMATCH')


def run_native(request: dict, *, timeout_s: float) -> dict:
  if not finite(timeout_s) or not 0 < timeout_s <= MAX_TIMEOUT_S:
    raise ValueError('INVALID_TIMEOUT')
  payload = encode_request(request)
  request = json.loads(payload)

  def failure(status):
    return {'status': status, 'request_sha256': digest(payload), 'runtime_accepted': False, 'promotable': False}

  if sys.platform != 'linux':
    return failure('UNSUPPORTED_PLATFORM')
  worker = Path(__file__).resolve().with_name('native_long_worker.py')
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
    result = json.loads(outcome.stdout, object_pairs_hook=_unique_pairs, parse_constant=_invalid_constant)
    validate_response(request, result)
  except (ValueError, UnicodeError, RecursionError):
    return failure('INVALID_RESPONSE')
  return result
