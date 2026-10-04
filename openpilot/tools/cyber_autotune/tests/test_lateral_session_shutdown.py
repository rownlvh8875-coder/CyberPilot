"""Second independent review reproductions: blocked output and close failures."""
import json
import os
import signal
import subprocess
import time
import unittest
from unittest.mock import patch

from openpilot.tools.cyber_autotune import lateral_session as api, lateral_session_protocol as protocol
from openpilot.tools.cyber_autotune.native_runner import _owned_group_running


class ClosingProxy:
  def __init__(self, stream, name, failing, calls):
    self.stream, self.name, self.failing, self.calls = stream, name, failing, calls

  def __getattr__(self, name):
    return getattr(self.stream, name)

  def close(self):
    self.calls.append(self.name)
    self.stream.close()
    if self.name == self.failing:
      raise OSError('PRIVATE_CLOSE_DETAIL')


class TestSessionShutdown(unittest.TestCase):
  def test_blocked_stdout_cannot_outlive_absolute_worker_deadline(self):
    real = subprocess.Popen
    epoch = api.build_epoch()

    def shorter_deadline(argv, *args, **kwargs):
      argv = list(argv)
      if any('lateral_session_worker.py' in str(item) for item in argv):
        argv[-1] = str(time.monotonic_ns() + 3_000_000_000)
      return real(argv, *args, **kwargs)

    session = api.LateralSession(timeout_s=10.)
    try:
      with patch.object(api.subprocess, 'Popen', side_effect=shorter_deadline):
        handle = session.open_epoch(epoch)
      session.advance(handle, start_index=0, count=601)
      request = protocol.make_message(handle.session_id, session._sequence, handle.epoch_id, 'FINISH',
                                      {'epoch_sha256': handle.epoch_sha256})
      payload = protocol.encode_message(request) + b'\n'
      self.assertEqual(os.write(session._process.stdin.fileno(), payload), len(payload))
      # Intentionally do not drain FINISH; its large trace fills the output pipe.
      try:
        code = session._process.wait(timeout=5.)
      except subprocess.TimeoutExpired:
        self.fail('Worker survived its deadline while output remained blocked')
      self.assertEqual(code, -signal.SIGALRM)
      fragment = os.read(session._process.stdout.fileno(), 1024)
      self.assertTrue(fragment.startswith(b'{'), 'No output was produced; blocked-output condition not established')
      self.assertLess(len(fragment), api.MAX_RESPONSE_BYTES)
    finally:
      session._shutdown()
      if session._process is not None:
        self.assertIsNotNone(session._process.returncode)
        self.assertFalse(_owned_group_running(session._process.pid))

  def install_proxies(self, session, failing):
    calls = []
    process = session._process
    process.stdin = ClosingProxy(process.stdin, 'stdin', failing, calls)
    process.stdout = ClosingProxy(process.stdout, 'stdout', failing, calls)
    return calls

  def check_original_and_cleanup(self, session, original, observed, calls):
    self.assertIs(observed, original)
    notes = getattr(observed, '__notes__', [])
    self.assertTrue(notes, 'Cleanup failure was not exposed through the original exception')
    self.assertIs(json.loads(notes[-1])['cleanup_confirmed'], False)
    self.assertNotIn('PRIVATE', notes[-1])
    self.assertEqual(calls, ['stdin', 'stdout'])
    self.assertIsNotNone(session._process.returncode)
    self.assertFalse(_owned_group_running(session._process.pid))

  def test_each_close_failure_preserves_context_exception_and_closes_both(self):
    for failing in ('stdin', 'stdout'):
      with self.subTest(stream=failing):
        session = api.LateralSession(timeout_s=10.)
        session.open_epoch(api.build_epoch())
        calls = self.install_proxies(session, failing)
        original = ValueError('CALLER_PRIVATE_TEXT')
        with self.assertRaises(ValueError) as caught:
          with session:
            raise original
        self.check_original_and_cleanup(session, original, caught.exception, calls)

  def test_each_close_failure_preserves_keyboard_interrupt_and_closes_both(self):
    for failing in ('stdin', 'stdout'):
      with self.subTest(stream=failing), api.LateralSession(timeout_s=10.) as session:
        handle = session.open_epoch(api.build_epoch())
        calls = self.install_proxies(session, failing)
        original = KeyboardInterrupt('CALLER_PRIVATE_TEXT')
        with patch.object(session, '_exchange', side_effect=original), self.assertRaises(KeyboardInterrupt) as caught:
          session.advance(handle, start_index=0, count=1)
        self.check_original_and_cleanup(session, original, caught.exception, calls)


if __name__ == '__main__':
  unittest.main()
