"""Paired OFFLINE windows using existing schedulers/workers, never live control.

Axes run sequentially on preadmitted exogenous inputs, not a coupled plant or
continuous two-axis session. Matching declared bytes does not authenticate clocks,
configuration history, physical truth or vehicle qualification. No actuator writer.
"""
import json
from time import monotonic

from openpilot.tools.cyber_autotune import shadow, long_shadow
from openpilot.tools.cyber_autotune import native_protocol as lat, native_long_protocol as lng
from openpilot.tools.cyber_autotune.native_runner import MAX_RESPONSE_BYTES, MAX_TIMEOUT_S


AXES = ('lateral', 'longitudinal')
SHARED_FRAME_FIELDS = ('time_ns', 'speed_mps', 'accel_mps2')
SCOPE = 'OFFLINE_PAIRED_SHADOW_WINDOW_ONLY'
ALIGNMENT = 'STRUCTURAL_WINDOW_MATCH_ONLY'
MODULES = (shadow, long_shadow)
PROTOCOLS = (lat, lng)
METRICS = (('requested_torque_rmse_difference', 'requested_torque_max_difference'),
           ('requested_accel_rmse_difference_mps2', 'requested_accel_max_difference_mps2',
            'requested_accel_pid_bound_ratio', 'long_state_mismatch_ratio'))
FAILURES = frozenset(('TIMEOUT', 'WORKER_FAILED', 'WORKER_UNAVAILABLE', 'UNSUPPORTED_PLATFORM',
                      'INVALID_RESPONSE', 'EXECUTION_EXCEPTION'))


def _split(envelope):
  return tuple(dict(envelope[axis], frames=envelope['frames'][axis]) for axis in AXES)


def encode_request(envelope):
  lat._keys(envelope, ('version', *AXES, 'frames'))
  if type(envelope['version']) is not int or envelope['version'] != 1:
    raise ValueError('INVALID_PAIRED_VERSION')
  lat._keys(envelope['frames'], AXES)
  for axis in AXES:
    if type(envelope[axis]) is not dict or 'frames' in envelope[axis]:
      raise ValueError('INVALID_AXIS_HEADER')
  first, second = _split(envelope)
  lat.validate_request(first)
  lng.validate_request(second)
  for field in ('fingerprint', 'car_params_base64', 'car_params_sha256'):
    if first[field] != second[field]:
      raise ValueError('CROSS_AXIS_CP_MISMATCH')
  for field in ('root', 'head', 'opendbc_head'):
    if first['source'][field] != second['source'][field]:
      raise ValueError('CROSS_AXIS_SOURCE_MISMATCH')
  shared = first['source']['files'].keys() & second['source']['files'].keys()
  if any(first['source']['files'][name] != second['source']['files'][name] for name in shared):
    raise ValueError('CROSS_AXIS_SHARED_SOURCE_MISMATCH')
  if len(first['frames']) != len(second['frames']):
    raise ValueError('CROSS_AXIS_FRAME_COUNT_MISMATCH')
  for left, right in zip(first['frames'], second['frames'], strict=True):
    if lat.canonical({key: left[key] for key in SHARED_FRAME_FIELDS}) != lat.canonical({key: right[key] for key in SHARED_FRAME_FIELDS}):
      raise ValueError('CROSS_AXIS_FRAME_MISMATCH')
  payload = lat.canonical(envelope)
  # Keep the existing cap for the whole pair, not twice the admission limit.
  if len(payload) > lat.MAX_REQUEST_BYTES:
    raise ValueError('PAIRED_REQUEST_TOO_LARGE')
  return payload


def _read_json(payload, limit):
  if type(payload) is not bytes or not 0 < len(payload) <= limit:
    raise ValueError('INVALID_PAIRED_BYTES')
  try:
    return json.loads(payload, object_pairs_hook=lat._unique_pairs, parse_constant=lat._invalid_constant)
  except (UnicodeError, RecursionError) as error:
    raise ValueError('INVALID_PAIRED_JSON') from error


def decode_request(payload):
  envelope = _read_json(payload, lat.MAX_REQUEST_BYTES)
  encode_request(envelope)
  return envelope


def pack_requests(lateral, longitudinal):
  requests = (lat.decode_request(lateral), lng.decode_request(longitudinal))
  envelope = {'version': 1, 'frames': {}}
  for axis, request in zip(AXES, requests, strict=True):
    envelope[axis] = {key: value for key, value in request.items() if key != 'frames'}
    envelope['frames'][axis] = request['frames']
  return encode_request(envelope)


def _responses(request, payload):
  envelope = decode_request(request)
  response = _read_json(payload, MAX_RESPONSE_BYTES)
  lat._keys(response, ('version', *AXES))
  if type(response['version']) is not int or response['version'] != 1:
    raise ValueError('INVALID_PAIRED_RESPONSE_VERSION')
  for axis, module, native in zip(AXES, MODULES, _split(envelope), strict=True):
    module.validate_response(native, response[axis])
  return response


def pack_responses(request, lateral, longitudinal):
  payload = lat.canonical({'version': 1, 'lateral': _read_json(lateral, MAX_RESPONSE_BYTES),
                           'longitudinal': _read_json(longitudinal, MAX_RESPONSE_BYTES)})
  _responses(request, payload)
  return payload


def _jobs(job):
  candidate, active = decode_request(job.candidate_request), decode_request(job.active_request)
  response = _responses(job.active_request, job.active_response)
  jobs = []
  for axis, protocol, module, current, observed in zip(AXES, PROTOCOLS, MODULES, _split(candidate), _split(active), strict=True):
    item = shadow.ShadowJob(job.sequence, protocol.encode_request(current), protocol.encode_request(observed),
                            lat.canonical(response[axis]))
    jobs.append(module._prepare(item, shadow._identity(current)))
  return tuple(jobs)


def _prepare(job, identity):
  if type(job) is not shadow.ShadowJob or type(job.sequence) is not int or not 0 <= job.sequence < 2**63:
    raise ValueError('INVALID_JOB')
  candidate = decode_request(job.candidate_request)
  active = decode_request(job.active_request)
  if shadow._identity(candidate) != identity:
    raise ValueError('PAIRED_TEMPLATE_CHANGED')
  _jobs(job)  # Both active observations and each axis' inputs admit before any run.
  return shadow.ShadowJob(job.sequence, encode_request(candidate), encode_request(active),
                          lat.canonical(_responses(job.active_request, job.active_response)))


def _checked_axis(item, module, protocol, metrics, result):
  current, active = protocol.decode_request(item.candidate_request), protocol.decode_request(item.active_request)
  expected = {'sequence': item.sequence, 'scope': module.SCOPE if module is long_shadow else 'OFFLINE_SHADOW_WINDOW_ONLY',
              'candidate_request_sha256': lat.digest(item.candidate_request), 'active_request_sha256': lat.digest(item.active_request),
              'candidate_source_head': current['source']['head'], 'active_source_head': active['source']['head'],
              'candidate_car_params_sha256': current['car_params_sha256'], 'active_car_params_sha256': active['car_params_sha256'],
              'inputs_sha256': module._inputs(current), 'first_time_ns': current['frames'][0]['time_ns'],
              'last_time_ns': current['frames'][-1]['time_ns'], 'runtime_accepted': False, 'promotable': False}
  if type(result) is not dict or type(result.get('status')) is not str:
    raise ValueError('INVALID_AXIS_DIAGNOSTIC')
  complete = result['status'] == 'COMPLETED_DIAGNOSTIC'
  keys = (*expected, 'status', *(('candidate_trace_sha256', 'active_trace_sha256', 'sample_count', *metrics) if complete else ()))
  lat._keys(result, keys)
  if any(type(result[key]) is not type(value) or result[key] != value for key, value in expected.items()):
    raise ValueError('AXIS_DIAGNOSTIC_REBINDING')
  if complete:
    if (type(result['sample_count']) is not int or result['sample_count'] != len(current['frames']) or
        not lat._hex(result['candidate_trace_sha256'], 64) or
        result['active_trace_sha256'] != json.loads(item.active_response)['ordered_trace_sha256'] or
        any(not lat.finite(result[key]) or result[key] < 0 for key in metrics)):
      raise ValueError('INVALID_AXIS_DIAGNOSTIC_VALUES')
    if any(result[key] > 1 for key in metrics if key.endswith('_ratio')):
      raise ValueError('INVALID_AXIS_DIAGNOSTIC_RATIO')
  elif result['status'] not in FAILURES:
    raise ValueError('UNKNOWN_AXIS_FAILURE')
  return result['status']


def _diagnostic(job, timeout_s):
  if not lat.finite(timeout_s) or not 0 < timeout_s <= MAX_TIMEOUT_S:
    raise ValueError('INVALID_TIMEOUT')
  started = monotonic()
  items = _jobs(job)
  result = {'sequence': job.sequence, 'status': 'PAIR_INCOMPLETE', 'scope': SCOPE, 'input_alignment': ALIGNMENT,
            'candidate_request_sha256': lat.digest(job.candidate_request), 'active_request_sha256': lat.digest(job.active_request),
            'axis_status': dict.fromkeys(AXES, 'NOT_RUN'), 'runtime_accepted': False, 'promotable': False}
  diagnostics = {}
  for axis, module, protocol, metrics, item in zip(AXES, MODULES, PROTOCOLS, METRICS, items, strict=True):
    remaining = timeout_s - (monotonic() - started)
    if remaining <= 0:
      result['status'] = 'TIMEOUT'
      return result
    try:
      observed = module._diagnostic(item, remaining)
      status = _checked_axis(item, module, protocol, metrics, observed)
    except Exception:
      status = 'INVALID_RESPONSE'
    result['axis_status'][axis] = status
    if monotonic() - started >= timeout_s:
      result['status'] = 'TIMEOUT'
      return result
    if status != 'COMPLETED_DIAGNOSTIC':
      return result
    diagnostics[axis] = observed
  result.update(status='COMPLETED_DIAGNOSTIC', axes=diagnostics)
  return result


def _expired(result):
  # No partial pair survives execution/admission/poll expiry.
  return {key: ('EXPIRED' if key == 'status' else value) for key, value in result.items() if key != 'axes'}


class PairedShadowSession(shadow.ShadowSession):
  """Existing one-running/one-pending/one-result queue; shared sequential budget.

  Each native axis resets per window. No continuous state, real-time simultaneity,
  runtime parameter attestation or active-loop noninterference qualification.
  """
  _decode = staticmethod(decode_request)
  _prepare_job = staticmethod(_prepare)
  _diagnose_job = staticmethod(_diagnostic)
  _expire_result = staticmethod(_expired)
  _scope = SCOPE
