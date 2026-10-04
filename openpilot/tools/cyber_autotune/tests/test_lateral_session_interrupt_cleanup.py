"""Retain original exceptions when owned cleanup itself is interrupted."""
import json
import unittest
from unittest.mock import patch

from openpilot.tools.cyber_autotune import lateral_session as api
from openpilot.tools.cyber_autotune.native_runner import _owned_group_running


class InterruptedClose:
  def __init__(self, stream, name, fail_name, calls):
    self.stream, self.name, self.fail_name, self.calls = stream, name, fail_name, calls

  def __getattr__(self, name):
    return getattr(self.stream, name)

  def close(self):
    self.calls.append(self.name)
    self.stream.close()
    if self.name == self.fail_name:
      raise KeyboardInterrupt('SECOND_PRIVATE_INTERRUPT')


class TestInterruptedCleanup(unittest.TestCase):
  def session(self, failing=None):
    session = api.LateralSession(timeout_s=10.)
    session.open_epoch(api.build_epoch())
    calls = []
    for name in ('stdin', 'stdout'):
      setattr(session._process, name, InterruptedClose(getattr(session._process, name), name, failing, calls))
    return session, calls

  def verify(self, session, calls, original, actual):
    self.assertIs(actual, original)
    notes = getattr(actual, '__notes__', [])
    self.assertTrue(notes, 'Cleanup interruption lost its public receipt')
    receipt = json.loads(notes[-1])
    self.assertEqual(receipt['status'], 'INTERRUPTED')
    self.assertIs(receipt['cleanup_confirmed'], False)
    self.assertNotIn('PRIVATE', notes[-1])
    self.assertEqual(calls, ['stdin', 'stdout'])
    self.assertIsNotNone(session._process.poll())
    self.assertFalse(_owned_group_running(session._process.pid))

  def test_wait_interruption_preserves_original_and_attempts_both_closes(self):
    session, calls = self.session()
    original = ValueError('ORIGINAL_PRIVATE_TEXT')
    with patch.object(session._process, 'wait', side_effect=KeyboardInterrupt('SECOND_PRIVATE_INTERRUPT')):
      try:
        with session:
          raise original
      except BaseException as observed:
        actual = observed
    self.verify(session, calls, original, actual)

  def test_each_close_interruption_preserves_original_and_attempts_other_close(self):
    for failing in ('stdin', 'stdout'):
      with self.subTest(stream=failing):
        session, calls = self.session(failing)
        original = ValueError('ORIGINAL_PRIVATE_TEXT')
        try:
          with session:
            raise original
        except BaseException as observed:
          actual = observed
        self.verify(session, calls, original, actual)

  def test_repeated_interrupt_keeps_first_exception_and_public_cleanup_receipt(self):
    session, calls = self.session('stdin')
    original = KeyboardInterrupt('ORIGINAL_PRIVATE_TEXT')
    try:
      with session:
        raise original
    except BaseException as observed:
      actual = observed
    self.verify(session, calls, original, actual)


if __name__ == '__main__':
  unittest.main()
