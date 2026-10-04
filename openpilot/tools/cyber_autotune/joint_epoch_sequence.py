"""Finite changing-input sequence with explicit fresh-process epoch boundaries.

All inputs are predeclared. Exact contiguous time is structural, not runtime-clock
or settings attestation. Never carry state between epochs or qualify a vehicle.
Existing JointSession restrictions, workers, controller math and limits are intact.
"""
from time import monotonic

from openpilot.tools.cyber_autotune import joint_continuity as joint, joint_session_protocol as protocol
from openpilot.tools.cyber_autotune.joint_session import JointSession as _NativeJointSession
from openpilot.tools.cyber_autotune.lateral_session import SessionError
from openpilot.tools.cyber_autotune import lateral_session as transport
from openpilot.tools.cyber_autotune import native_protocol as native
from openpilot.tools.cyber_autotune.native_runner import MAX_TIMEOUT_S


# Whole sequence shares existing native input caps; not a physical tolerance.
MAX_TOTAL_FRAMES = native.MAX_FRAMES
OVERLAY_FILE = 'openpilot/tools/cyber_autotune/joint_epoch_sequence.py'
PASS = 'SOFTWARE_ORDERED_EPOCH_RESETS_ONLY'
SCOPE = 'OFFLINE_PREDECLARED_CHANGING_INPUT_SEQUENCE'
BOUNDARY = 'FRESH_PROCESS_RESET'


class JointSession(_NativeJointSession):
  """Private sequence-owned specialization; no shared transport source changes.

  Recheck the absolute sequence budget at transport entry after source validation,
  not only before OPEN/ADVANCE. Startup/cleanup retain native bounded semantics.
  """
  def _shutdown(self):
    # Same owned operations/order/bounds as the inherited cleanup, but retain
    # interruption identity locally instead of reducing it to a boolean alone.
    self.closed = True
    self._cleanup_interrupt = None
    cleanup = True
    process = self._process
    if process is not None:
      operations = [lambda: transport._kill_owned_group(process),
                    lambda: process.wait(timeout=transport.CLEANUP_TIMEOUT_S),
                    lambda: transport._wait_owned_group_exit(process.pid), process.poll]
      operations.extend(stream.close for stream in (process.stdin, process.stdout) if stream is not None)
      for operation in operations:
        try:
          operation()
        except BaseException as exc:
          cleanup = False
          if not isinstance(exc, Exception) and self._cleanup_interrupt is None:
            self._cleanup_interrupt = exc
    return cleanup

  def _failure(self, status):
    failure = super()._failure(status)
    if self._cleanup_interrupt is not None:
      BaseException.add_note(self._cleanup_interrupt, 'SEQUENCE_CLEANUP_UNCONFIRMED')
      raise self._cleanup_interrupt
    return failure

  def _interrupted(self, exception):
    super()._interrupted(exception)
    if isinstance(exception, Exception) and self._cleanup_interrupt is not None:
      BaseException.add_note(self._cleanup_interrupt, 'SEQUENCE_CLEANUP_UNCONFIRMED')
      raise self._cleanup_interrupt

  def _refresh_budget(self):
    budget = self._sequence_deadline - monotonic()
    if budget <= 0:
      raise TimeoutError('SEQUENCE_DEADLINE')
    self._timeout = budget

  def _spawn(self):
    self._refresh_budget()
    super()._spawn()

  def _exchange(self, payload):
    self._refresh_budget()
    return super()._exchange(payload)


def _configuration(epoch):
  request = epoch['joint']
  return native.canonical({'version': request['version'], 'joint_overlay': request['overlay'],
                           'session_overlay': epoch['overlay'],
                           'pair_headers': {name: value for name, value in request['pair'].items() if name != 'frames'}})


def encode_sequence(plan):
  native._keys(plan, ('version', 'epochs', 'overlay'))
  if type(plan['version']) is not int or plan['version'] != 1:
    raise ValueError('INVALID_SEQUENCE_VERSION')
  native._keys(plan['overlay'], (OVERLAY_FILE,))
  if not native._hex(plan['overlay'][OVERLAY_FILE], 64):
    raise ValueError('INVALID_SEQUENCE_OVERLAY')
  epochs = plan['epochs']
  if type(epochs) is not list or not 1 <= len(epochs) <= MAX_TOTAL_FRAMES:
    raise ValueError('INVALID_SEQUENCE_LENGTH')
  signature, previous_end, count = None, None, 0
  for epoch in epochs:
    protocol.encode_epoch(epoch)
    config = _configuration(epoch)
    if signature is not None and config != signature:
      raise ValueError('CROSS_EPOCH_CONFIGURATION_CHANGED')
    signature = config
    frames = epoch['joint']['pair']['frames']['lateral']
    if previous_end is not None and frames[0]['time_ns'] != previous_end + native.TIMESTEP_NS:
      raise ValueError('NONCONTIGUOUS_EPOCH_TIMES')
    previous_end = frames[-1]['time_ns']
    count += len(frames)
    if count > MAX_TOTAL_FRAMES:
      raise ValueError('SEQUENCE_FRAME_LIMIT')
  payload = native.canonical(plan)
  if len(payload) > native.MAX_REQUEST_BYTES:
    raise ValueError('SEQUENCE_BYTE_LIMIT')
  return payload


def decode_sequence(payload):
  plan = joint.paired_shadow._read_json(payload, native.MAX_REQUEST_BYTES)
  encode_sequence(plan)
  return plan


def build_sequence(epochs):
  if type(epochs) is not list or not 1 <= len(epochs) <= MAX_TOTAL_FRAMES:
    raise ValueError('INVALID_SEQUENCE_LENGTH')
  # Reject the aggregate raw byte budget BEFORE constructing JSON objects.
  # Whitespace does not allow unbounded admission allocations.
  total_bytes = 0
  for epoch in epochs:
    if type(epoch) is not bytes or not epoch:
      raise ValueError('INVALID_EPOCH_BYTES')
    total_bytes += len(epoch)
    if total_bytes > native.MAX_REQUEST_BYTES:
      raise ValueError('SEQUENCE_BYTE_LIMIT')
  decoded = [joint.paired_shadow._read_json(epoch, native.MAX_REQUEST_BYTES) for epoch in epochs]
  return encode_sequence({'version': 1, 'epochs': decoded,
                          'overlay': {OVERLAY_FILE: native.digest((joint.ROOT / OVERLAY_FILE).read_bytes())}})


def _verify_sequence(plan):
  path = (joint.ROOT / OVERLAY_FILE).resolve(strict=True)
  if not path.is_relative_to(joint.ROOT) or native.digest(path.read_bytes()) != plan['overlay'][OVERLAY_FILE]:
    raise ValueError('SEQUENCE_SOURCE_CHANGED')
  # Admit every future source/configuration before launching the first child.
  for epoch in plan['epochs']:
    protocol.verify_epoch(epoch)


def _close_info(session, *, pending_interrupt=None):
  if session is None:
    return {'code': None, 'cleanup': True, 'normal': False}
  try:
    try:
      receipt = session.close()
    except SessionError as exc:
      receipt = exc.receipt
    native._keys(receipt, ('status', 'worker_returncode', 'cleanup_confirmed', *joint.AUTHORITIES))
    code = receipt['worker_returncode']
    if (type(receipt['status']) is not str or (code is not None and type(code) is not int) or
        type(receipt['cleanup_confirmed']) is not bool or any(receipt[name] is not False for name in joint.AUTHORITIES)):
      raise ValueError('INVALID_CLEANUP_RECEIPT')
    return {'code': code, 'cleanup': receipt['cleanup_confirmed'],
            'normal': receipt['status'] == 'CLOSED' and type(code) is int and code == 0 and receipt['cleanup_confirmed']}
  except Exception:
    return {'code': None, 'cleanup': False, 'normal': False}
  except BaseException as exc:
    if pending_interrupt is None:
      BaseException.add_note(exc, 'SEQUENCE_CLEANUP_UNCONFIRMED')
      raise
    # Keep an already pending original interruption; do not replace it with this one.
    return {'code': None, 'cleanup': False, 'normal': False}


def run_sequence(payload, *, timeout_s):
  """Blocking PC-only batch. Each successor requires confirmed previous teardown.

  Invalid plans raise before execution. Runtime failures return fixed metadata and
  no earlier success rows. The complete sequence uses one inherited timeout budget;
  native cleanup remains separately bounded. This is not hard-real-time execution.
  """
  if not native.finite(timeout_s) or not 0 < timeout_s <= MAX_TIMEOUT_S:
    raise ValueError('INVALID_SEQUENCE_TIMEOUT')
  deadline = monotonic() + timeout_s
  plan = decode_sequence(payload)
  plan_sha = native.digest(encode_sequence(plan))
  completed, session, index = [], None, None
  stage = 'BINDING_REJECTED'

  def remaining():
    budget = deadline - monotonic()
    if budget <= 0:
      raise TimeoutError('SEQUENCE_DEADLINE')
    return budget

  def failure(status, info=None):
    info = _close_info(session) if info is None else info
    return {'status': status, 'scope': SCOPE, 'plan_sha256': plan_sha,
            'failed_index': index, 'completed_count': len(completed),
            'worker_returncode': info['code'], 'cleanup_confirmed': info['cleanup'],
            'state_carried_between_epochs': False, **dict.fromkeys(joint.AUTHORITIES, False)}

  try:
    _verify_sequence(plan)
    remaining()
    for index, epoch in enumerate(plan['epochs']):
      session = None
      stage = 'BINDING_REJECTED'
      _verify_sequence(plan)
      remaining()
      stage = 'SESSION_FAILED'
      session = JointSession(timeout_s=remaining())
      session._sequence_deadline = deadline
      with session:
        handle = session.open_epoch(epoch)
        start = 0
        for count in epoch['joint']['chunk_sizes']:
          session._timeout = remaining()
          session.advance(handle, start_index=start, count=count)
          start += count
        session._timeout = remaining()
        result = session.finish(handle)
        stage = 'INVALID_RESULT'
        joint.validate_response(epoch['joint'], result)
        stage = 'BINDING_REJECTED'
        _verify_sequence(plan)
        session._timeout = remaining()
      info = _close_info(session)
      if not info['cleanup']:
        return failure('CLEANUP_UNCONFIRMED', info)
      if not info['normal']:
        return failure('SESSION_FAILED', info)
      remaining()
      completed.append({'index': index, 'epoch_sha256': native.digest(protocol.encode_epoch(epoch)),
                        'result_sha256': native.digest(native.canonical(result)), 'boundary': BOUNDARY,
                        'worker_returncode': info['code'], 'cleanup_confirmed': True})
    stage = 'BINDING_REJECTED'
    _verify_sequence(plan)
    remaining()
    return {'status': PASS, 'scope': SCOPE, 'plan_sha256': plan_sha, 'epochs': completed,
            'completed_count': len(completed), 'input_alignment': joint.paired_shadow.ALIGNMENT,
            'state_carried_between_epochs': False, **dict.fromkeys(joint.AUTHORITIES, False)}
  except TimeoutError:
    return failure('TIMEOUT')
  except SessionError as exc:
    return failure('TIMEOUT' if exc.receipt.get('status') == 'TIMEOUT' else 'SESSION_FAILED')
  except Exception:
    return failure(stage)
  except BaseException as exc:
    info = _close_info(session, pending_interrupt=exc)
    if not info['cleanup']:
      BaseException.add_note(exc, 'SEQUENCE_CLEANUP_UNCONFIRMED')
    raise
