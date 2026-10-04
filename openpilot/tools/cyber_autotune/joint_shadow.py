"""Whole identical joint epochs through existing bounded offline Shadow queues.

Only chunks INSIDE an admitted epoch share state. Epoch boundaries reset both
controllers. This is not live streaming, vehicle shadow qualification or tuning.
"""
from time import monotonic

from openpilot.tools.cyber_autotune import joint_continuity as joint, shadow
from openpilot.tools.cyber_autotune.joint_session import JointSession, build_epoch
from openpilot.tools.cyber_autotune.lateral_session import SessionError
from openpilot.tools.cyber_autotune.native_protocol import canonical, digest
from openpilot.tools.cyber_autotune.native_runner import MAX_RESPONSE_BYTES


SCOPE = 'OFFLINE_QUEUED_JOINT_EPOCH_ONLY'


def _prepare(job, identity):
  if type(job) is not shadow.ShadowJob or type(job.sequence) is not int or not 0 <= job.sequence < 2**63:
    raise ValueError('INVALID_JOINT_JOB')
  candidate = joint.decode_request(job.candidate_request)
  active = joint.decode_request(job.active_request)
  payload = joint.encode_request(candidate)
  # The inherited identity covers the complete joint input (frames are nested).
  # This interface is deliberately A/A only, not an approved parameter optimizer.
  if shadow._identity(candidate) != identity or payload != joint.encode_request(active):
    raise ValueError('JOINT_JOB_TEMPLATE_MISMATCH')
  reference = joint.paired_shadow._read_json(job.active_response, MAX_RESPONSE_BYTES)
  joint.validate_response(active, reference)
  return shadow.ShadowJob(job.sequence, payload, payload, canonical(reference))


def _expired(result):
  return {key: ('EXPIRED' if key == 'status' else value) for key, value in result.items()
          if key not in ('axes', 'completed_result_sha256')}


class JointShadowSession(shadow.ShadowSession):
  """Same bounded queue, one thread-owned IPC child, complete-epoch admission.

  Queued/result drops never skip chunks in a running epoch. Child faults and its
  inherited lifetime expiry are terminal: no automatic restart or partial result.
  close() joins the owner thread and explicitly reports unconfirmed cleanup.
  """
  _decode = staticmethod(joint.decode_request)
  _prepare_job = staticmethod(_prepare)
  _expire_result = staticmethod(_expired)
  _scope = SCOPE

  def __init__(self, candidate_template, *, timeout_s, deadline_s):
    self._session = None
    self._worker_cleanup_confirmed = False
    super().__init__(candidate_template, timeout_s=timeout_s, deadline_s=deadline_s)

  def _diagnose_job(self, job, timeout_s):
    started = monotonic()
    request = joint.decode_request(job.candidate_request)
    joint._verify_bindings(request)
    epoch = build_epoch(joint.paired_shadow.encode_request(request['pair']), request['chunk_sizes'])
    if canonical(epoch['joint']) != canonical(request):
      raise ValueError('JOINT_SOURCE_CHANGED')
    if self._session is None:
      self._session = JointSession(timeout_s=timeout_s)

    def remaining():
      budget = timeout_s - (monotonic() - started)
      if budget <= 0:
        raise TimeoutError('JOINT_EPOCH_BUDGET_EXHAUSTED')
      self._session._timeout = budget

    remaining()
    handle = self._session.open_epoch(epoch)
    start = 0
    for count in request['chunk_sizes']:
      remaining()
      self._session.advance(handle, start_index=start, count=count)
      start += count
    remaining()
    observed = self._session.finish(handle)
    remaining()
    joint.validate_response(request, observed)
    if canonical(observed) != job.active_response:
      raise ValueError('JOINT_REFERENCE_MISMATCH')
    joint._verify_bindings(request)
    remaining()
    axes = {}
    for axis in joint.paired_shadow.AXES:
      arm = observed['axes'][axis]['candidate']
      extension = 'a1' if axis == 'lateral' else 'continuity'
      axes[axis] = {'ordered_trace_sha256': arm['ordered_trace_sha256'], 'states_sha256': arm[extension]['states_sha256']}
    return {'sequence': job.sequence, 'status': 'COMPLETED_DIAGNOSTIC', 'scope': SCOPE,
            'candidate_request_sha256': digest(job.candidate_request), 'active_request_sha256': digest(job.active_request),
            'completed_result_sha256': digest(canonical(observed)), 'sample_count': start, 'axes': axes,
            'input_alignment': joint.paired_shadow.ALIGNMENT, **dict.fromkeys(joint.AUTHORITIES, False)}

  def _work(self):
    try:
      super()._work()
    finally:
      confirmed = self._session is None
      if self._session is not None:
        try:
          receipt = self._session.close()
          confirmed = type(receipt) is dict and receipt.get('cleanup_confirmed') is True
        except BaseException:
          confirmed = False
      with self._condition:
        self._worker_cleanup_confirmed = confirmed
        self._condition.notify_all()

  def snapshot(self):
    with self._condition:
      return dict(super().snapshot(), worker_cleanup_confirmed=self._worker_cleanup_confirmed)

  def close(self):
    super().close()
    if not self._worker_cleanup_confirmed:
      raise SessionError({'status': 'JOINT_SHADOW_CLEANUP_UNCONFIRMED', 'cleanup_confirmed': False,
                          **dict.fromkeys(joint.AUTHORITIES, False)})

  def __exit__(self, exc_type, exc, _traceback):
    try:
      self.close()
    except BaseException:
      if exc_type is None:
        raise
      BaseException.add_note(exc, 'JOINT_SHADOW_CLEANUP_UNCONFIRMED')
