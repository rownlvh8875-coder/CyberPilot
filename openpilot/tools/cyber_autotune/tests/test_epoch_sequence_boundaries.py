"""Independent-review reproductions; preserve all original assertions and limits."""
import unittest
from unittest.mock import patch

from openpilot.tools.cyber_autotune import joint_epoch_sequence as api, joint_session as ipc
from openpilot.tools.cyber_autotune import joint_session_protocol as protocol, lateral_session as transport, native_protocol as native
from openpilot.tools.cyber_autotune.tests.test_joint_epoch_sequence import sequence_epochs


class TestEpochSequenceBoundaries(unittest.TestCase):
  def setUp(self):
    self.epochs = sequence_epochs()
    self.plan = api.build_sequence(self.epochs)

  def test_aggregate_bytes_are_rejected_before_any_json_allocation(self):
    size = native.MAX_REQUEST_BYTES // 2 + 1
    padded = [epoch + b' ' * (size - len(epoch)) for epoch in self.epochs]
    read = api.joint.paired_shadow._read_json
    with patch.object(api.joint.paired_shadow, '_read_json', wraps=read) as decode:
      with self.assertRaises(ValueError):
        api.build_sequence(padded)
      decode.assert_not_called()

  def test_open_validation_expiry_does_not_spawn_native_worker(self):
    clock, sessions = [100.], []
    create, verify, popen = api.JointSession, protocol.verify_epoch, transport.subprocess.Popen
    def new(**kwargs):
      session = create(**kwargs)
      sessions.append(session)
      return session
    def slow(epoch):
      verify(epoch)
      if sessions and sessions[-1]._process is None:
        clock[0] = 103.
    with patch.object(api, 'monotonic', lambda: clock[0]), patch.object(api, 'JointSession', side_effect=new), \
         patch.object(protocol, 'verify_epoch', side_effect=slow), patch.object(transport.subprocess, 'Popen', wraps=popen) as spawn:
      result = api.run_sequence(self.plan, timeout_s=2.)
    self.assertEqual(result['status'], 'TIMEOUT')
    workers = [call for call in spawn.call_args_list if 'joint_session_worker.py' in str(call.args[0])]
    self.assertEqual(workers, [], 'Source validation consumed budget but native child still launched')
    self.assertEqual(len(sessions), 1)
    self.assertIsNone(sessions[0]._process)

  def test_advance_validation_expiry_does_not_send_stale_budget_request(self):
    clock, sessions, operations = [100.], [], []
    create, verify, exchange = api.JointSession, protocol.verify_epoch, transport.LateralSession._exchange
    def new(**kwargs):
      session = create(**kwargs)
      sessions.append(session)
      return session
    def slow(epoch):
      verify(epoch)
      if sessions and sessions[-1]._handle is not None:
        clock[0] = 103.
    def observed(session, payload):
      operations.append(protocol.decode_message(payload)['operation'])
      return exchange(session, payload)
    with patch.object(api, 'monotonic', lambda: clock[0]), patch.object(api, 'JointSession', side_effect=new), \
         patch.object(protocol, 'verify_epoch', side_effect=slow), patch.object(transport.LateralSession, '_exchange', observed):
      result = api.run_sequence(self.plan, timeout_s=2.)
    self.assertEqual(result['status'], 'TIMEOUT')
    self.assertNotIn('ADVANCE', operations, 'Stale remaining budget permitted an IPC advance')
    self.assertTrue(sessions[0].closed)
    self.assertIsNotNone(sessions[0]._process.poll())

  def test_new_cleanup_interrupt_propagates_instead_of_becoming_failure_metadata(self):
    close = ipc.JointSession.close
    original = KeyboardInterrupt('NEW_PRIVATE_INTERRUPT')
    def interrupted(session):
      close(session)
      raise original
    with patch.object(ipc.JointSession, 'advance', side_effect=ValueError('INITIAL_PRIVATE_FAILURE')), \
         patch.object(ipc.JointSession, 'close', interrupted), self.assertRaises(KeyboardInterrupt) as caught:
      api.run_sequence(self.plan, timeout_s=10.)
    self.assertIs(caught.exception, original)
    self.assertNotIn('PRIVATE', str(getattr(original, '__notes__', [])))

  def test_cleanup_interruption_does_not_replace_pending_original_interruption(self):
    close = ipc.JointSession.close
    original = KeyboardInterrupt('ORIGINAL_PRIVATE_INTERRUPT')
    def interrupted(session):
      close(session)
      raise KeyboardInterrupt('SECOND_PRIVATE_INTERRUPT')
    with patch.object(ipc.JointSession, 'advance', side_effect=original), patch.object(ipc.JointSession, 'close', interrupted):
      with self.assertRaises(KeyboardInterrupt) as caught:
        api.run_sequence(self.plan, timeout_s=10.)
    self.assertIs(caught.exception, original)
    self.assertIn('SEQUENCE_CLEANUP_UNCONFIRMED', original.__notes__)


if __name__ == '__main__':
  unittest.main()
