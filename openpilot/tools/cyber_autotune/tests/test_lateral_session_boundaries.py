"""Additional state ownership and transport boundaries; original20tests unchanged."""
import copy
import os
import subprocess
import sys
import threading
import time
import unittest
from unittest.mock import patch

from openpilot.tools.cyber_autotune import lateral_session as api, lateral_session_protocol as protocol
from openpilot.tools.cyber_autotune.native_protocol import canonical, digest
from openpilot.tools.cyber_autotune.native_runner import _owned_group_running, MAX_RESPONSE_BYTES


class TestSessionBoundaries(unittest.TestCase):
  def setUp(self):
    self.epoch = api.build_epoch()

  def test_direct_reply_mutation_cannot_corrupt_machine_checkpoint_history(self):
    identity = digest(protocol.encode_epoch(self.epoch))
    with protocol.EpochMachine() as machine:
      machine.dispatch(protocol.make_message('1' * 32, 0, 1, 'OPEN', self.epoch))
      first = machine.dispatch(protocol.make_message('1' * 32, 1, 1, 'ADVANCE',
                               {'epoch_sha256': identity, 'start_index': 0, 'count': 150}))
      preserved = copy.deepcopy(first['data'])
      first['data']['end_state_sha256'] = '0' * 64
      machine.dispatch(protocol.make_message('1' * 32, 2, 1, 'ADVANCE',
                       {'epoch_sha256': identity, 'start_index': 150, 'count': 451}))
      completed = machine.dispatch(protocol.make_message('1' * 32, 3, 1, 'FINISH', {'epoch_sha256': identity}))
      self.assertEqual(completed['data']['chunks'][0], preserved)

  def test_other_thread_cannot_close_owned_session(self):
    results = []
    with api.LateralSession(timeout_s=10.) as session:
      handle = session.open_epoch(self.epoch)
      process = session._process

      def other_thread():
        try:
          session.close()
        except api.SessionError as exc:
          results.append(exc.receipt['status'])

      thread = threading.Thread(target=other_thread)
      thread.start()
      thread.join(timeout=10.)
      self.assertFalse(thread.is_alive())
      self.assertEqual(results, ['WRONG_OWNER_THREAD'])
      self.assertFalse(session.closed)
      self.assertIsNone(process.poll())
      session.advance(handle, start_index=0, count=601)
      session.finish(handle)

  def test_abort_reply_must_match_observed_progress(self):
    with api.LateralSession(timeout_s=10.) as session:
      handle = session.open_epoch(self.epoch)
      session.advance(handle, start_index=0, count=20)
      exchange = session._exchange

      def corrupt(payload):
        result = exchange(payload)
        result['data']['processed_frames'] = 21
        return result

      with patch.object(session, '_exchange', side_effect=corrupt), self.assertRaises(api.SessionError):
        session.abort(handle)
      self.assertTrue(session.closed)
      self.assertFalse(_owned_group_running(session._process.pid))

  def test_expired_parent_session_cannot_send_another_job(self):
    with api.LateralSession(timeout_s=10.) as session:
      handle = session.open_epoch(self.epoch)
      session._expires = time.monotonic() - 1.
      with patch.object(api.os, 'write') as write, self.assertRaises(api.SessionError) as caught:
        session.advance(handle, start_index=0, count=1)
      write.assert_not_called()
      self.assertEqual(caught.exception.receipt['status'], 'TIMEOUT')
      self.assertTrue(caught.exception.receipt['cleanup_confirmed'])

  def test_pipe_initialization_failure_reaps_started_worker(self):
    with api.LateralSession(timeout_s=10.) as session:
      with patch.object(api.os, 'set_blocking', side_effect=OSError('PRIVATE_SENTINEL')), self.assertRaises(api.SessionError) as caught:
        session.open_epoch(self.epoch)
      self.assertIsNotNone(session._process.returncode)
      self.assertFalse(_owned_group_running(session._process.pid))
      self.assertNotIn('PRIVATE_SENTINEL', canonical(caught.exception.receipt).decode())

  def transport(self, body, payload=b'{}', timeout=2.):
    session = api.LateralSession(timeout_s=timeout)
    session._process = subprocess.Popen([sys.executable, '-c', body], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                       stderr=subprocess.DEVNULL, start_new_session=True, close_fds=True, bufsize=0)
    session._expires = time.monotonic() + 10.
    for stream in (session._process.stdin, session._process.stdout):
      os.set_blocking(stream.fileno(), False)
    try:
      with session._guard():
        return session._exchange(payload)
    finally:
      session._shutdown()
      self.assertIsNotNone(session._process.returncode)
      self.assertFalse(_owned_group_running(session._process.pid))

  def test_partial_write_and_fragmented_read_are_reassembled(self):
    body = 'import sys,os,time;sys.stdin.buffer.readline();os.write(1,b"{\\\"okay\\\":");time.sleep(.01);os.write(1,b"true}\\n")'
    self.assertEqual(self.transport(body, b'X' * (api.PIPE_CHUNK_BYTES * 3)), {'okay': True})

  def test_extra_response_line_is_rejected(self):
    body = 'import sys,os;sys.stdin.buffer.readline();os.write(1,b"{}\\n{}\\n")'
    with self.assertRaises(api.SessionError):
      self.transport(body)

  def test_unterminated_reply_times_out_without_returning_partial_data(self):
    body = 'import sys,os,time;sys.stdin.buffer.readline();os.write(1,b"{\\\"private\\\":");time.sleep(5)'
    with self.assertRaises(api.SessionError) as caught:
      self.transport(body, timeout=.1)
    self.assertEqual(caught.exception.receipt['status'], 'TIMEOUT')
    self.assertTrue(caught.exception.receipt['cleanup_confirmed'])

  def test_oversized_reply_is_not_returned_or_unboundedly_captured(self):
    body = f'import sys;sys.stdin.buffer.readline();sys.stdout.buffer.write(b"X"*{MAX_RESPONSE_BYTES + 2});sys.stdout.buffer.flush()'
    with self.assertRaises(api.SessionError) as caught:
      self.transport(body)
    self.assertEqual(caught.exception.receipt['status'], 'INVALID_OR_FAILED_SESSION')
    self.assertNotIn('data', caught.exception.receipt)


if __name__ == '__main__':
  unittest.main()
