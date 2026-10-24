"""Offline requested-acceleration shadow windows; no actuator/profile authority.

Fresh native LongControl state per window, not continuous or on-device shadow.
Uses the existing bounded scheduler; never call its API on an active-control thread.
"""
import json
import math

from openpilot.tools.cyber_autotune.native_long_protocol import EXPECTED_ACCEL_LIMITS, decode_request, encode_request
from openpilot.tools.cyber_autotune.native_long_runner import run_native, validate_response
from openpilot.tools.cyber_autotune.native_protocol import _invalid_constant, _unique_pairs, canonical, digest
from openpilot.tools.cyber_autotune.native_runner import MAX_RESPONSE_BYTES
from openpilot.tools.cyber_autotune.shadow import ShadowJob, ShadowSession, _identity


SCOPE = 'OFFLINE_LONGITUDINAL_SHADOW_WINDOW_ONLY'
COMPARISON_FIELDS = frozenset({'requested_accel_rmse_difference_mps2', 'requested_accel_max_difference_mps2',
                              'requested_accel_pid_bound_ratio', 'long_state_mismatch_ratio'})


def _inputs(request):
  return digest(canonical({key: request[key] for key in ('frames', 'fingerprint', 'openpilot_longitudinal_control')}))


def _prepare(job, identity):
  if type(job) is not ShadowJob or type(job.sequence) is not int or not 0 <= job.sequence < 2**63:
    raise ValueError('INVALID_JOB')
  candidate = decode_request(job.candidate_request)
  active = decode_request(job.active_request)
  if _identity(candidate) != identity or _inputs(candidate) != _inputs(active):
    raise ValueError('JOB_BINDING_MISMATCH')
  if type(job.active_response) is not bytes or not 0 < len(job.active_response) <= MAX_RESPONSE_BYTES:
    raise ValueError('INVALID_ACTIVE_RESPONSE')
  response = json.loads(job.active_response, object_pairs_hook=_unique_pairs, parse_constant=_invalid_constant)
  validate_response(active, response)
  return ShadowJob(job.sequence, encode_request(candidate), encode_request(active), canonical(response))


def _diagnostic(job, timeout_s):
  request = decode_request(job.candidate_request)
  active = decode_request(job.active_request)
  result = {'sequence': job.sequence, 'status': 'INVALID_RESPONSE', 'scope': SCOPE,
            'candidate_request_sha256': digest(job.candidate_request), 'active_request_sha256': digest(job.active_request),
            'candidate_source_head': request['source']['head'], 'active_source_head': active['source']['head'],
            'candidate_car_params_sha256': request['car_params_sha256'], 'active_car_params_sha256': active['car_params_sha256'],
            'inputs_sha256': _inputs(request), 'first_time_ns': request['frames'][0]['time_ns'],
            'last_time_ns': request['frames'][-1]['time_ns'], 'runtime_accepted': False, 'promotable': False}
  try:
    observed = run_native(request, timeout_s=timeout_s)
    if type(observed) is not dict:
      return result
    if observed.get('status') != 'COMPLETED':
      if (set(observed) == {'status', 'request_sha256', 'runtime_accepted', 'promotable'} and
          type(observed['status']) is str and observed['status'] in
          {'TIMEOUT', 'WORKER_FAILED', 'WORKER_UNAVAILABLE', 'INVALID_RESPONSE', 'UNSUPPORTED_PLATFORM'} and
          observed['request_sha256'] == digest(job.candidate_request) and
          observed['runtime_accepted'] is False and observed['promotable'] is False):
        result['status'] = observed['status']
      return result
    validate_response(request, observed)
    reference = json.loads(job.active_response)
    pairs = tuple(zip(observed['samples'], reference['samples'], strict=True))
    differences = tuple(row['requested_accel_mps2'] - old['requested_accel_mps2'] for row, old in pairs)
    count = len(differences)
    result.update(status='COMPLETED_DIAGNOSTIC', candidate_trace_sha256=observed['ordered_trace_sha256'],
                  active_trace_sha256=reference['ordered_trace_sha256'], sample_count=count,
                  requested_accel_rmse_difference_mps2=math.sqrt(math.fsum(value * value for value in differences) / count),
                  requested_accel_max_difference_mps2=max(abs(value) for value in differences),
                  requested_accel_pid_bound_ratio=sum(row['requested_accel_mps2'] in EXPECTED_ACCEL_LIMITS for row, _ in pairs) / count,
                  long_state_mismatch_ratio=sum(row['state_after'] != old['state_after'] for row, old in pairs) / count)
  except ValueError:
    result['status'] = 'INVALID_RESPONSE'
  except Exception:
    result['status'] = 'EXECUTION_EXCEPTION'
  return result


def _expired(result):
  return {key: ('EXPIRED' if key == 'status' else value) for key, value in result.items() if key not in COMPARISON_FIELDS}


class LongShadowSession(ShadowSession):
  """Built-in long-axis hooks only; same bounded lifecycle as offline lateral windows."""
  _decode = staticmethod(decode_request)
  _prepare_job = staticmethod(_prepare)
  _diagnose_job = staticmethod(_diagnostic)
  _expire_result = staticmethod(_expired)
  _scope = SCOPE
