"""Joint IPC over preadmitted synthetic epochs; no vehicle qualification."""
import copy
from dataclasses import replace
import importlib
import importlib.util
import json
import os
import signal
import subprocess
import sys
import threading
import time
import unittest
from unittest.mock import patch

from openpilot.tools.cyber_autotune import joint_continuity as joint, lateral_session as lateral
from openpilot.tools.cyber_autotune.native_protocol import digest
from openpilot.tools.cyber_autotune.native_runner import _owned_group_running, _run_process
from openpilot.tools.cyber_autotune.tests.test_joint_continuity import pair_fixture


class TestJointSession(unittest.TestCase):
  def setUp(self):
    name = 'openpilot.tools.cyber_autotune.joint_session'
    self.assertIsNotNone(importlib.util.find_spec(name), 'Persistent joint IPC is not implemented')
    self.api = importlib.import_module(name)
    self.proto = importlib.import_module(name + '_protocol')
    self.epoch = self.api.build_epoch(pair_fixture(), [2, 3, 6])

  def complete(self, session, handle, sizes=(2, 3, 6)):
    start = 0
    for index, count in enumerate(sizes):
      reply = session.advance(handle, start_index=start, count=count)
      self.assertEqual(reply['start_index'], start)
      self.assertEqual(reply['end_index_exclusive'], start + count)
      self.assertEqual(reply['checkpoint']['chunk_index'], index)
      start += count
    return session.finish(handle)

  def reaped(self, session):
    self.assertTrue(session.closed)
    if session._process is not None:
      self.assertIsNotNone(session._process.poll())
      self.assertFalse(_owned_group_running(session._process.pid))

  def test_real_separate_jobs_keep_one_child_and_match_existing_joint_result(self):
    reference = joint.execute_experiment(self.epoch['joint'])
    popen = subprocess.Popen
    with patch.object(lateral.subprocess, 'Popen', wraps=popen) as spawn:
      with self.api.JointSession(timeout_s=10.) as session:
        handle = session.open_epoch(self.epoch)
        child = session._process
        result = self.complete(session, handle)
        self.assertIs(session._process, child)
        self.assertIsNone(child.poll())
        self.assertEqual(result, reference)
      selected = [call for call in spawn.call_args_list if 'joint_session_worker.py' in str(call.args[0])]
      self.assertEqual(len(selected), 1)
    self.reaped(session)
    self.assertEqual(child.returncode, 0)

  def test_completed_and_aborted_epochs_reset_both_in_same_child(self):
    before = copy.deepcopy(self.epoch)
    with self.api.JointSession(timeout_s=10.) as session:
      first = session.open_epoch(self.epoch)
      child = session._process
      result = self.complete(session, first)
      aborted = session.open_epoch(self.epoch)
      session.advance(aborted, start_index=0, count=2)
      self.assertEqual(session.abort(aborted), {'processed_frames': 2, 'completed': False})
      third = session.open_epoch(self.epoch)
      self.assertEqual(third.epoch_id, 3)
      self.assertIs(session._process, child)
      self.assertEqual(self.complete(session, third), result)
    self.assertEqual(self.epoch, before)
    self.reaped(session)

  def test_nonzero_integrator_retained_across_real_ipc(self):
    epoch = self.api.build_epoch(pair_fixture(True), [7, 5, 8])
    with self.api.JointSession(timeout_s=10.) as session:
      handle = session.open_epoch(epoch)
      result = self.complete(session, handle, (7, 5, 8))
    self.assertEqual(result, joint.execute_experiment(epoch['joint']))
    states = result['axes']['longitudinal']['candidate']['continuity']['states']
    self.assertGreater(states[-1]['snapshot']['pid']['i'], states[0]['snapshot']['pid']['i'])

  def test_machine_advances_are_lazy_and_use_both_controllers(self):
    from openpilot.selfdrive.controls.lib.latcontrol_torque import LatControlTorque
    from openpilot.selfdrive.controls.lib.longcontrol import LongControl
    calls = [0, 0]
    first, second = LatControlTorque.update, LongControl.update
    def left(controller, *args, **kwargs):
      calls[0] += 1
      return first(controller, *args, **kwargs)
    def right(controller, *args, **kwargs):
      calls[1] += 1
      return second(controller, *args, **kwargs)
    before = list(sys.path)
    with patch.object(LatControlTorque, 'update', left), patch.object(LongControl, 'update', right), self.proto.EpochMachine() as machine:
      machine.dispatch(self.proto.make_message('1' * 32, 0, 1, 'OPEN', self.epoch))
      self.assertEqual(calls, [0, 0])
      identity = digest(self.proto.encode_epoch(self.epoch))
      reply = machine.dispatch(self.proto.make_message('1' * 32, 1, 1, 'ADVANCE',
                               {'epoch_sha256': identity, 'start_index': 0, 'count': 2}))
      self.assertEqual(calls, [2, 2])
      reply['data']['checkpoint']['axes']['longitudinal']['end_state_sha256'] = '0' * 64
      machine.dispatch(self.proto.make_message('1' * 32, 2, 1, 'ABORT', {'epoch_sha256': identity}))
      self.assertEqual(calls, [2, 2])
    self.assertEqual(sys.path, before)

  def test_wrong_partition_missing_index_or_partial_finish_terminates_both(self):
    for operation, start, count in (('ADVANCE', 1, 2), ('ADVANCE', 0, 1), ('ADVANCE', 0, True), ('FINISH', 0, 0)):
      with self.subTest(operation=operation, start=start, count=count), self.api.JointSession(timeout_s=10.) as session:
        handle = session.open_epoch(self.epoch)
        with self.assertRaises(lateral.SessionError):
          if operation == 'FINISH':
            session.finish(handle)
          else:
            session.advance(handle, start_index=start, count=count)
        self.reaped(session)

  def test_stale_foreign_handle_and_configuration_change_are_not_reused(self):
    for field, value in (('session_id', '0' * 32), ('epoch_id', 99), ('epoch_sha256', '0' * 64)):
      with self.subTest(field=field), self.api.JointSession(timeout_s=10.) as session:
        handle = session.open_epoch(self.epoch)
        with self.assertRaises(lateral.SessionError):
          session.advance(replace(handle, **{field: value}), start_index=0, count=2)
        self.reaped(session)
    with self.api.JointSession(timeout_s=10.) as session:
      handle = session.open_epoch(self.epoch)
      session.abort(handle)
      changed = self.api.build_epoch(pair_fixture(True), [7, 5, 8])
      with self.assertRaises(lateral.SessionError):
        session.open_epoch(changed)
      self.reaped(session)

  def test_caller_input_and_checkpoint_copies_do_not_rebind_active_epoch(self):
    supplied = copy.deepcopy(self.epoch)
    reference = joint.execute_experiment(supplied['joint'])
    with self.api.JointSession(timeout_s=10.) as session:
      handle = session.open_epoch(supplied)
      first = session.advance(handle, start_index=0, count=2)
      supplied['joint']['pair']['frames']['longitudinal'][3]['a_target_mps2'] = 1e100
      first['checkpoint']['axes']['lateral']['end_state_sha256'] = '0' * 64
      session.advance(handle, start_index=2, count=3)
      session.advance(handle, start_index=5, count=6)
      self.assertEqual(session.finish(handle), reference)

  def test_invalid_source_or_pair_blocks_before_launch(self):
    for mode in ('overlay', 'pair', 'extra'):
      supplied = copy.deepcopy(self.epoch)
      if mode == 'overlay':
        supplied['overlay'][next(iter(supplied['overlay']))] = '0' * 64
      elif mode == 'pair':
        supplied['joint']['pair']['frames']['longitudinal'][0]['time_ns'] += 1
      else:
        supplied['command'] = 'PRIVATE_SENTINEL'
      with self.subTest(mode=mode), patch.object(lateral.subprocess, 'Popen') as spawn:
        with self.api.JointSession(timeout_s=5.) as session, self.assertRaises(lateral.SessionError) as caught:
          session.open_epoch(supplied)
        spawn.assert_not_called()
        self.assertNotIn('PRIVATE_SENTINEL', str(caught.exception.receipt))

  def test_source_drift_between_jobs_kills_session_without_partial_result(self):
    with self.api.JointSession(timeout_s=10.) as session:
      handle = session.open_epoch(self.epoch)
      session.advance(handle, start_index=0, count=2)
      with patch.object(self.proto, 'verify_epoch', side_effect=ValueError('PRIVATE_SOURCE')):
        with self.assertRaises(lateral.SessionError) as caught:
          session.advance(handle, start_index=2, count=3)
      self.reaped(session)
      self.assertNotIn('axes', caught.exception.receipt)
      self.assertNotIn('PRIVATE_SOURCE', str(caught.exception.receipt))

  def test_wrong_reply_sequence_and_checkpoint_never_complete(self):
    for field in ('sequence', 'checkpoint'):
      with self.subTest(field=field), self.api.JointSession(timeout_s=10.) as session:
        handle = session.open_epoch(self.epoch)
        exchange = session._exchange
        def corrupt(payload, field=field, exchange=exchange):
          reply = exchange(payload)
          if field == 'sequence':
            reply['sequence'] += 1
          else:
            reply['data']['checkpoint']['axes']['longitudinal']['end_state_sha256'] = '0' * 64
          return reply
        if field == 'sequence':
          with patch.object(session, '_exchange', side_effect=corrupt), self.assertRaises(lateral.SessionError):
            session.advance(handle, start_index=0, count=2)
        else:
          with patch.object(session, '_exchange', side_effect=corrupt):
            session.advance(handle, start_index=0, count=2)
          session.advance(handle, start_index=2, count=3)
          session.advance(handle, start_index=5, count=6)
          with self.assertRaises(lateral.SessionError):
            session.finish(handle)
        self.reaped(session)

  def test_machine_rejects_duplicate_or_foreign_request_terminally(self):
    for change in ({'sequence': 0}, {'session_id': '2' * 32}, {'epoch_id': 2}):
      with self.subTest(change=change), self.proto.EpochMachine() as machine:
        machine.dispatch(self.proto.make_message('1' * 32, 0, 1, 'OPEN', self.epoch))
        advance = self.proto.make_message('1' * 32, 1, 1, 'ADVANCE',
                                         {'epoch_sha256': digest(self.proto.encode_epoch(self.epoch)), 'start_index': 0, 'count': 2})
        with self.assertRaises(ValueError):
          machine.dispatch(advance | change)
        self.assertTrue(machine.closed)
        with self.assertRaises(ValueError):
          machine.dispatch(advance)

  def test_failure_in_either_native_axis_never_returns_completed_data(self):
    for axis, field in (('lateral', 'desired_curvature_1pm'), ('longitudinal', 'a_target_mps2')):
      supplied = copy.deepcopy(self.epoch)
      supplied['joint']['pair']['frames'][axis][3][field] = 1e308
      with self.subTest(axis=axis), self.api.JointSession(timeout_s=10.) as session:
        handle = session.open_epoch(supplied)
        session.advance(handle, start_index=0, count=2)
        with self.assertRaises(lateral.SessionError) as caught:
          session.advance(handle, start_index=2, count=3)
        self.reaped(session)
        self.assertNotIn('axes', caught.exception.receipt)
        self.assertTrue(caught.exception.receipt['cleanup_confirmed'])

  def test_timeout_and_child_signal_have_no_automatic_restart(self):
    with self.api.JointSession(timeout_s=.001) as session:
      with self.assertRaises(lateral.SessionError) as caught:
        session.open_epoch(self.epoch)
      self.assertEqual(caught.exception.receipt['status'], 'TIMEOUT')
      self.reaped(session)
    with self.api.JointSession(timeout_s=10.) as session:
      handle = session.open_epoch(self.epoch)
      os.killpg(session._process.pid, signal.SIGKILL)
      session._process.wait(timeout=5.)
      with self.assertRaises(lateral.SessionError) as caught:
        session.advance(handle, start_index=0, count=2)
      self.assertEqual(caught.exception.receipt['worker_returncode'], -signal.SIGKILL)
      with patch.object(lateral.subprocess, 'Popen') as spawn, self.assertRaises(lateral.SessionError):
        session.open_epoch(self.epoch)
      spawn.assert_not_called()
      self.reaped(session)

  def test_foreign_thread_and_repeated_cleanup_interrupt_preserve_owner(self):
    failures = []
    with self.api.JointSession(timeout_s=10.) as session:
      handle = session.open_epoch(self.epoch)
      def other():
        try:
          session.close()
        except lateral.SessionError as exc:
          failures.append(exc.receipt['status'])
      thread = threading.Thread(target=other)
      thread.start()
      thread.join(timeout=3.)
      self.assertEqual(failures, ['WRONG_OWNER_THREAD'])
      self.assertIsNone(session._process.poll())
      original = KeyboardInterrupt('CALLER_PRIVATE')
      with patch.object(session, '_exchange', side_effect=original), patch.object(lateral, '_wait_owned_group_exit', side_effect=KeyboardInterrupt):
        with self.assertRaises(KeyboardInterrupt) as caught:
          session.advance(handle, start_index=0, count=2)
      self.assertIs(caught.exception, original)
      self.assertIs(json.loads(original.__notes__[-1])['cleanup_confirmed'], False)
      self.assertNotIn('PRIVATE', original.__notes__[-1])
      self.reaped(session)

  def test_raw_worker_rejects_malformed_or_wrong_protocol_without_reflection(self):
    worker = self.api.WORKER_PATH
    for payload in (b'{"PRIVATE_SENTINEL":"route"}\n', b'{"version":1,"version":1}\n', b'[]\n'):
      outcome = _run_process([sys.executable, '-I', str(worker)], payload, 10.)
      self.assertEqual(outcome.returncode, 1)
      self.assertEqual(json.loads(outcome.stdout), {'status': 'REJECTED', 'code': 'INVALID_OR_FAILED_SESSION'})

  def test_partial_eof_and_expired_deadline_reap_child(self):
    identity = digest(self.proto.encode_epoch(self.epoch))
    rows = [self.proto.make_message('1' * 32, 0, 1, 'OPEN', self.epoch),
            self.proto.make_message('1' * 32, 1, 1, 'ADVANCE', {'epoch_sha256': identity, 'start_index': 0, 'count': 2})]
    payload = b''.join(self.proto.encode_message(row) + b'\n' for row in rows)
    outcome = _run_process([sys.executable, '-I', str(self.api.WORKER_PATH)], payload, 10.)
    self.assertEqual(outcome.returncode, 1)
    replies = [json.loads(line) for line in outcome.stdout.splitlines()]
    self.assertEqual([row['status'] for row in replies], ['OPENED', 'ADVANCED', 'REJECTED'])
    with self.api.JointSession(timeout_s=10.) as session:
      handle = session.open_epoch(self.epoch)
      session._expires = time.monotonic() - 1.
      with patch.object(lateral.os, 'write') as write, self.assertRaises(lateral.SessionError):
        session.advance(handle, start_index=0, count=2)
      write.assert_not_called()
      self.reaped(session)


if __name__ == '__main__':
  unittest.main()
