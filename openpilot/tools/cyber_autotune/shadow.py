"""Bounded OFFLINE shadow windows, never an active-control-thread API.

Fresh native controller state per window. Active output is immutable observation,
not a callback or writable channel. No vehicle transport or profile update exists.
Validation/locks/OS scheduling are not real-time or a hostile-source sandbox.
"""
from dataclasses import dataclass
import json
import math
import threading
from time import monotonic

from openpilot.tools.cyber_autotune.native_protocol import _unique_pairs, canonical, decode_request, digest, encode_request, finite
from openpilot.tools.cyber_autotune.native_runner import MAX_RESPONSE_BYTES, MAX_TIMEOUT_S, run_native, validate_response


@dataclass(frozen=True)
class ShadowJob:
  sequence: int
  candidate_request: bytes
  active_request: bytes
  active_response: bytes


def _identity(request):
  return digest(canonical({key: value for key, value in request.items() if key != 'frames'}))


def _inputs(request):
  return digest(canonical({'frames': request['frames'], 'fingerprint': request['fingerprint']}))


def _prepare(job, identity):
  if type(job) is not ShadowJob or type(job.sequence) is not int or not 0 <= job.sequence < 2**63:
    raise ValueError('INVALID_JOB')
  candidate = decode_request(job.candidate_request)
  active = decode_request(job.active_request)
  if _identity(candidate) != identity or _inputs(candidate) != _inputs(active):
    raise ValueError('JOB_BINDING_MISMATCH')
  if type(job.active_response) is not bytes or not 0 < len(job.active_response) <= MAX_RESPONSE_BYTES:
    raise ValueError('INVALID_ACTIVE_RESPONSE')
  response = json.loads(job.active_response, object_pairs_hook=_unique_pairs)
  validate_response(active, response)
  return ShadowJob(job.sequence, encode_request(candidate), encode_request(active), canonical(response))


def _diagnostic(job, timeout_s):
  request = decode_request(job.candidate_request)
  active = decode_request(job.active_request)
  result = {'sequence': job.sequence, 'status': 'INVALID_RESPONSE', 'scope': 'OFFLINE_SHADOW_WINDOW_ONLY',
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
    differences = tuple(row['requested_torque'] - old['requested_torque']
                        for row, old in zip(observed['samples'], reference['samples'], strict=True))
    result.update(status='COMPLETED_DIAGNOSTIC', candidate_trace_sha256=observed['ordered_trace_sha256'],
                  active_trace_sha256=reference['ordered_trace_sha256'], sample_count=len(differences),
                  requested_torque_rmse_difference=math.sqrt(math.fsum(value * value for value in differences) / len(differences)),
                  requested_torque_max_difference=max(abs(value) for value in differences))
  except ValueError:
    result['status'] = 'INVALID_RESPONSE'
  except Exception:
    result['status'] = 'EXECUTION_EXCEPTION'
  return result


def _expired(result):
  return {key: ('EXPIRED' if key == 'status' else value) for key, value in result.items()
          if not key.startswith('requested_torque_')}


class ShadowSession:
  """One running job, one pending job and one result; full queues drop NEW items.

close() waits outside any active loop for the owned native supervisor timeout and
cleanup. It never kills unrelated workers or retries. OS/process creation itself
has no hard real-time guarantee. Use as a context manager or explicitly close.
"""
  # Private built-in axis hooks; no user-supplied worker/transport callback API.
  _decode = staticmethod(decode_request)
  _prepare_job = staticmethod(_prepare)
  _diagnose_job = staticmethod(_diagnostic)
  _expire_result = staticmethod(_expired)
  _scope = 'OFFLINE_SHADOW_WINDOW_ONLY'

  def __init__(self, candidate_template: bytes, *, timeout_s: float, deadline_s: float):
    if any(not finite(value) or not 0 < value <= MAX_TIMEOUT_S for value in (timeout_s, deadline_s)):
      raise ValueError('INVALID_TIME_POLICY')
    self._identity = _identity(self._decode(candidate_template))
    self._timeout_s = timeout_s
    self._deadline_s = deadline_s
    self._condition = threading.Condition()
    self._pending = None
    self._result = None
    self._last_sequence = -1
    self._running = False
    self._closed = False
    self._terminal_fault = False
    self._counts = {'accepted': 0, 'invalid': 0, 'busy_drops': 0, 'result_drops': 0, 'cancelled': 0, 'processed': 0, 'expired': 0}
    self._thread = threading.Thread(target=self._work, name='cyber-offline-shadow', daemon=True)
    self._thread.start()

  def try_submit(self, job: ShadowJob) -> str:
    with self._condition:
      if self._closed:
        return 'CLOSED'
    try:
      prepared = self._prepare_job(job, self._identity)
    except Exception:
      with self._condition:
        if self._closed:
          return 'CLOSED'
        self._counts['invalid'] += 1
      return 'INVALID'
    with self._condition:
      if self._closed:
        return 'CLOSED'
      if prepared.sequence <= self._last_sequence:
        self._counts['invalid'] += 1
        return 'INVALID'
      if self._pending is not None:
        self._counts['busy_drops'] += 1
        return 'BUSY'
      self._pending = (prepared, monotonic())
      self._last_sequence = prepared.sequence
      self._counts['accepted'] += 1
      self._condition.notify()
      return 'ACCEPTED'

  def poll(self) -> bytes | None:
    with self._condition:
      if self._result is None or self._closed:
        return None
      payload, admitted = self._result
      self._result = None
      result = json.loads(payload)
      if monotonic() - admitted >= self._deadline_s and result['status'] != 'EXPIRED':
        self._counts['expired'] += 1
        result = self._expire_result(result)
      return canonical(result)

  def snapshot(self) -> dict:
    with self._condition:
      return dict(self._counts, closed=self._closed, running=self._running,
                  pending=self._pending is not None, terminal_fault=self._terminal_fault)

  def close(self) -> None:
    with self._condition:
      self._closed = True
      if self._pending is not None:
        self._counts['cancelled'] += 1
        self._pending = None
      if self._result is not None:
        self._counts['result_drops'] += 1
        self._result = None
      self._condition.notify_all()
    self._thread.join()

  def __enter__(self):
    return self

  def __exit__(self, *_):
    self.close()

  def _work(self):
    try:
      while True:
        with self._condition:
          self._condition.wait_for(lambda: self._closed or self._pending is not None)
          if self._closed:
            return
          job, admitted = self._pending
          self._pending = None
          self._running = True
        started = monotonic()
        if started - admitted >= self._deadline_s:
          result = {'sequence': job.sequence, 'status': 'EXPIRED', 'scope': self._scope,
                    'candidate_request_sha256': digest(job.candidate_request), 'active_request_sha256': digest(job.active_request),
                    'runtime_accepted': False, 'promotable': False}
        else:
          result = self._diagnose_job(job, self._timeout_s)
        finished = monotonic()
        result.update(queue_duration_s=started - admitted, processing_duration_s=finished - started,
                      admission_to_finish_s=finished - admitted)
        if finished - admitted >= self._deadline_s:
          result = self._expire_result(result)
        payload = canonical(result)
        with self._condition:
          self._running = False
          if self._closed:
            self._counts['cancelled'] += 1
            return
          self._counts['processed'] += 1
          if result['status'] == 'EXPIRED':
            self._counts['expired'] += 1
          if self._result is not None:
            self._counts['result_drops'] += 1
          else:
            self._result = (payload, admitted)
    except BaseException:
      # Thread death must not leave a seemingly live scheduler accepting jobs.
      with self._condition:
        self._terminal_fault = True
        self._closed = True
        self._counts['cancelled'] += int(self._running) + int(self._pending is not None)
        self._running = False
        self._pending = None
        self._counts['result_drops'] += int(self._result is not None)
        self._result = None
        self._condition.notify_all()
