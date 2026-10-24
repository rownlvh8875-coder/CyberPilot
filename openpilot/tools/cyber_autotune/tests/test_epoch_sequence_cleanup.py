"""Real inherited cleanup interruption must not disappear inside sequence handling."""
from contextlib import ExitStack
import unittest
from unittest.mock import patch

from openpilot.tools.cyber_autotune import joint_epoch_sequence as api, joint_session_protocol as protocol
from openpilot.tools.cyber_autotune import lateral_session as transport
from openpilot.tools.cyber_autotune.native_runner import _owned_group_running
from openpilot.tools.cyber_autotune.tests.test_joint_epoch_sequence import sequence_epochs


class TestSequenceInternalCleanup(unittest.TestCase):
  def check_cleanup(self, location, pending_interrupt):
    plan = api.build_sequence(sequence_epochs())
    original = KeyboardInterrupt('ORIGINAL_PRIVATE') if pending_interrupt else ValueError('ORIGINAL_PRIVATE')
    cleanup_interrupt = KeyboardInterrupt('CLEANUP_PRIVATE')
    exchange = transport.LateralSession._exchange
    sessions = []
    with ExitStack() as stack:
      def fail(session, payload):
        if protocol.decode_message(payload)['operation'] != 'ADVANCE':
          return exchange(session, payload)
        sessions.append(session)
        if location == 'wait':
          target, name = session._process, 'wait'
        elif location == 'group':
          target, name = transport, '_wait_owned_group_exit'
        else:
          target, name = getattr(session._process, location), 'close'
        underlying = getattr(target, name)
        def interrupted(*args, **kwargs):
          underlying(*args, **kwargs)
          raise cleanup_interrupt
        stack.enter_context(patch.object(target, name, side_effect=interrupted))
        raise original
      stack.enter_context(patch.object(transport.LateralSession, '_exchange', fail))
      with self.assertRaises(KeyboardInterrupt) as caught:
        api.run_sequence(plan, timeout_s=15.)
      self.assertIs(caught.exception, original if pending_interrupt else cleanup_interrupt)
      self.assertTrue(getattr(caught.exception, '__notes__', []))
      self.assertNotIn('PRIVATE', str(caught.exception.__notes__))
    self.assertEqual(len(sessions), 1)
    self.assertTrue(sessions[0].closed)
    self.assertIsNotNone(sessions[0]._process.poll())
    self.assertFalse(_owned_group_running(sessions[0]._process.pid))
    self.assertTrue(sessions[0]._process.stdin.closed)
    self.assertTrue(sessions[0]._process.stdout.closed)

  def test_new_interrupt_inside_each_cleanup_operation_propagates(self):
    for location in ('wait', 'group', 'stdin', 'stdout'):
      with self.subTest(location=location):
        self.check_cleanup(location, False)

  def test_pending_original_interrupt_survives_each_internal_cleanup_interrupt(self):
    for location in ('wait', 'group', 'stdin', 'stdout'):
      with self.subTest(location=location):
        self.check_cleanup(location, True)


if __name__ == '__main__':
  unittest.main()
