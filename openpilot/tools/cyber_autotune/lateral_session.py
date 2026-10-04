"""Blocking Linux PC session, never an active-control-thread or vehicle API.

Fixed synthetic input only. One child preserves native state across sequential
jobs. Use a context manager or close() in finally; no automatic retry/resume.
Abandoning an unclosed object is not confirmed cleanup.
Trusted local source, not a hostile-code sandbox or real-time latency guarantee.
"""
from contextlib import contextmanager
import copy
from dataclasses import dataclass
import os
from pathlib import Path
import secrets
import selectors
import subprocess
import sys
import threading
import time

from openpilot.tools.cyber_autotune import a1_experiment as a1, lateral_continuity as continuity
from openpilot.tools.cyber_autotune import lateral_session_protocol as protocol
from openpilot.tools.cyber_autotune.native_protocol import canonical, finite
from openpilot.tools.cyber_autotune.native_runner import (
  CLEANUP_TIMEOUT_S, MAX_RESPONSE_BYTES, MAX_TIMEOUT_S, _kill_owned_group, _wait_owned_group_exit,
)


# Transfer granularity only, not a control/vehicle tolerance.
PIPE_CHUNK_BYTES = 64 * 1024
build_epoch = protocol.build_epoch


@dataclass(frozen=True)
class EpochHandle:
  session_id: str
  epoch_id: int
  epoch_sha256: str


class SessionError(RuntimeError):
  def __init__(self, receipt):
    self.receipt = copy.deepcopy(receipt)
    super().__init__(receipt['status'])


class LateralSession:
  """Synchronous, single-owner session; OPEN/ADVANCE/FINISH/ABORT/CLOSE only."""
  # Private built-in protocol/entry hooks; no caller-supplied commands.
  _protocol = protocol
  _worker_name = 'lateral_session_worker.py'

  def __init__(self, *, timeout_s):
    if not finite(timeout_s) or not 0 < timeout_s <= MAX_TIMEOUT_S:
      raise ValueError('INVALID_TIMEOUT')
    self._timeout = timeout_s
    self._owner_thread = threading.get_ident()
    self._process = None
    self._expires = None
    self._session_id = secrets.token_hex(16)
    self._sequence = self._epoch_id = self._index = 0
    self._epoch = self._handle = None
    self._checkpoints = []
    self.closed = False
    self._last_receipt = None

  def _receipt(self, status, cleanup):
    return {'status': status, 'worker_returncode': None if self._process is None else self._process.returncode,
            'cleanup_confirmed': cleanup, **dict.fromkeys(a1.AUTHORITIES, False)}

  def _shutdown(self):
    self.closed = True
    cleanup = True
    process = self._process
    if process is not None:
      # Each bounded operation is independent: a second interruption must not
      # replace the pending caller exception or skip subsequent cleanup attempts.
      operations = (lambda: _kill_owned_group(process),
                    lambda: process.wait(timeout=CLEANUP_TIMEOUT_S),
                    lambda: _wait_owned_group_exit(process.pid),
                    process.poll)
      for operation in operations:
        try:
          operation()
        except BaseException:
          cleanup = False
      for stream in (process.stdin, process.stdout):
        if stream is not None:
          try:
            stream.close()
          except BaseException:
            cleanup = False
    return cleanup

  def _failure(self, status):
    cleanup = self._shutdown()
    self._last_receipt = self._receipt(status, cleanup)
    return SessionError(self._last_receipt)

  def _assert_owner(self):
    # Refuse cross-thread access without touching the owner's running process.
    if threading.get_ident() != self._owner_thread:
      raise SessionError(self._receipt('WRONG_OWNER_THREAD', False))

  def _interrupted(self, exception):
    self._last_receipt = self._receipt('INTERRUPTED', self._shutdown())
    if not self._last_receipt['cleanup_confirmed']:
      # Preserve the caller's exception/type while publicly exposing fixed,
      # structured cleanup status, not private child output or exception text.
      BaseException.add_note(exception, canonical(self._last_receipt).decode('utf-8'))

  @contextmanager
  def _guard(self):
    self._assert_owner()
    if self.closed:
      raise SessionError(self._last_receipt or self._receipt('SESSION_CLOSED', False))
    try:
      if sys.platform != 'linux':
        raise self._failure('UNSUPPORTED_PLATFORM')
      yield
    except SessionError:
      raise
    except (TimeoutError, subprocess.TimeoutExpired):
      raise self._failure('TIMEOUT') from None
    except (OSError, EOFError):
      raise self._failure('WORKER_UNAVAILABLE' if self._process is None else 'WORKER_FAILED') from None
    except Exception:
      raise self._failure('INVALID_OR_FAILED_SESSION') from None
    except BaseException as exc:
      self._interrupted(exc)
      raise

  def _spawn(self):
    self._expires = time.monotonic() + MAX_TIMEOUT_S
    worker = Path(__file__).resolve().with_name(self._worker_name)
    self._process = subprocess.Popen([sys.executable, '-I', str(worker), str(int(self._expires * 1e9))], stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                     start_new_session=True, close_fds=True, bufsize=0)
    os.set_blocking(self._process.stdin.fileno(), False)
    os.set_blocking(self._process.stdout.fileno(), False)

  def _exchange(self, payload):
    deadline = min(time.monotonic() + self._timeout, self._expires)
    process = self._process
    pending = memoryview(payload + b'\n')
    received = bytearray()
    with selectors.DefaultSelector() as selector:
      selector.register(process.stdin, selectors.EVENT_WRITE)
      selector.register(process.stdout, selectors.EVENT_READ)
      while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
          raise TimeoutError('SESSION_EXCHANGE_TIMEOUT')
        for key, _ in selector.select(remaining):
          if key.fileobj is process.stdin:
            try:
              count = os.write(key.fd, pending[:PIPE_CHUNK_BYTES])
            except BlockingIOError:
              continue
            if count <= 0:
              raise EOFError('SESSION_INPUT_CLOSED')
            pending = pending[count:]
            if not pending:
              selector.unregister(process.stdin)
          else:
            try:
              part = os.read(key.fd, min(PIPE_CHUNK_BYTES, MAX_RESPONSE_BYTES + 2 - len(received)))
            except BlockingIOError:
              continue
            if not part:
              raise EOFError('SESSION_OUTPUT_CLOSED')
            received.extend(part)
            if len(received) > MAX_RESPONSE_BYTES + 1:
              raise ValueError('SESSION_REPLY_TOO_LARGE')
            if b'\n' in received:
              if pending or received[-1:] != b'\n' or received.count(b'\n') != 1:
                raise ValueError('EXTRA_OR_PREMATURE_REPLY')
              return self._protocol.decode_json(bytes(received[:-1]))

  def _request(self, operation, epoch_id, body):
    request = self._protocol.make_message(self._session_id, self._sequence, epoch_id, operation, body)
    payload = self._protocol.encode_message(request)
    if self._epoch is not None:
      self._protocol.verify_epoch(self._epoch)
    if self._process is None:
      self._spawn()
    if self._process.poll() is not None:
      raise EOFError('WORKER_ALREADY_EXITED')
    result = self._exchange(payload)
    self._protocol.validate_reply(request, result)
    if self._epoch is not None:
      self._protocol.verify_epoch(self._epoch)
    if operation != 'CLOSE' and self._process.poll() is not None:
      raise EOFError('WORKER_EXITED_DURING_JOB')
    self._sequence += 1
    return copy.deepcopy(result['data'])

  def _require_handle(self, handle):
    if (type(handle) is not EpochHandle or type(handle.epoch_id) is not int or
        self._handle is None or handle != self._handle):
      raise ValueError('STALE_OR_FOREIGN_HANDLE')

  def open_epoch(self, epoch):
    with self._guard():
      snapshot = self._protocol.decode_json(self._protocol.encode_epoch(epoch))
      self._protocol.verify_epoch(snapshot)
      if self._handle is not None:
        raise ValueError('ACTIVE_EPOCH_NOT_CLOSED')
      if self._epoch is not None and self._protocol.encode_epoch(snapshot) != self._protocol.encode_epoch(self._epoch):
        raise ValueError('CHANGED_EPOCH_REQUIRES_FRESH_PROCESS')
      self._epoch = snapshot
      next_id = self._epoch_id + 1
      data = self._request('OPEN', next_id, snapshot)
      self._handle = EpochHandle(self._session_id, next_id, data['epoch_sha256'])
      self._epoch_id, self._index, self._checkpoints = next_id, 0, []
      return self._handle

  def advance(self, handle, *, start_index, count):
    with self._guard():
      self._require_handle(handle)
      if type(start_index) is not int or start_index != self._index:
        raise ValueError('NONCONTIGUOUS_ADVANCE')
      data = self._request('ADVANCE', handle.epoch_id,
                           {'epoch_sha256': handle.epoch_sha256, 'start_index': start_index, 'count': count})
      self._checkpoints.append(copy.deepcopy(data))
      self._index = data['end_index_exclusive']
      return data

  def finish(self, handle):
    with self._guard():
      self._require_handle(handle)
      if self._index != a1.FRAME_COUNT:
        raise ValueError('INCOMPLETE_EPOCH')
      data = self._request('FINISH', handle.epoch_id, {'epoch_sha256': handle.epoch_sha256})
      request = copy.deepcopy(self._epoch['continuity'])
      request['chunk_sizes'] = [row['end_index_exclusive'] - row['start_index'] for row in self._checkpoints]
      continuity.validate_response(request, data)
      if canonical(data['chunks']) != canonical(self._checkpoints):
        raise ValueError('CHECKPOINT_HISTORY_MISMATCH')
      self._protocol.verify_epoch(self._epoch)
      self._handle = None
      return data

  def abort(self, handle):
    with self._guard():
      self._require_handle(handle)
      data = self._request('ABORT', handle.epoch_id, {'epoch_sha256': handle.epoch_sha256})
      if data['processed_frames'] != self._index:
        raise ValueError('ABORT_ACCOUNTING_MISMATCH')
      self._handle = None
      return data

  def close(self):
    self._assert_owner()
    if self.closed:
      return copy.deepcopy(self._last_receipt)
    with self._guard():
      if self._process is not None:
        self._request('CLOSE', 0, {})
        self._process.stdin.close()
        self._process.wait(timeout=CLEANUP_TIMEOUT_S)
        _wait_owned_group_exit(self._process.pid)
        if self._process.returncode != 0:
          raise EOFError('UNCLEAN_SESSION_CLOSE')
        self._process.stdout.close()
      self.closed = True
      self._last_receipt = self._receipt('CLOSED', True)
      return copy.deepcopy(self._last_receipt)

  def __enter__(self):
    self._assert_owner()
    return self

  def __exit__(self, exc_type, exc, _traceback):
    self._assert_owner()
    if exc_type is not None and not self.closed:
      self._interrupted(exc)
    else:
      self.close()
