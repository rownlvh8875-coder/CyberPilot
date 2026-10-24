"""Real PC IPC continuity; no live inputs or vehicle authority."""
import copy
from dataclasses import replace
import importlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import unittest
from unittest.mock import patch

from openpilot.tools.cyber_autotune import a1_experiment as a1, lateral_continuity as continuity
from openpilot.tools.cyber_autotune.native_protocol import canonical, digest
from openpilot.tools.cyber_autotune.native_runner import _owned_group_running, _run_process


class TestLateralSession(unittest.TestCase):
  def setUp(self):
    name = 'openpilot.tools.cyber_autotune.lateral_session'
    self.assertIsNotNone(importlib.util.find_spec(name), 'Persistent job-to-job IPC session is not implemented')
    self.api = importlib.import_module(name)
    self.protocol = importlib.import_module(name + '_protocol')
    self.epoch = self.api.build_epoch()

  def complete(self, session, handle, sizes=(150, 151, 300)):
    start = 0
    for count in sizes:
      checkpoint = session.advance(handle, start_index=start, count=count)
      self.assertEqual(checkpoint['start_index'], start)
      start += count
      self.assertEqual(checkpoint['end_index_exclusive'], start)
    return session.finish(handle)

  def assert_reaped(self, session):
    self.assertTrue(session.closed)
    if session._process is not None:
      self.assertIsNotNone(session._process.poll())
      self.assertFalse(_owned_group_running(session._process.pid))

  def test_real_jobs_reuse_one_child_and_match_existing_reference(self):
    real_popen = subprocess.Popen
    with patch.object(self.api.subprocess, 'Popen', wraps=real_popen) as spawn:
      with self.api.LateralSession(timeout_s=10.) as session:
        handle = session.open_epoch(self.epoch)
        child = session._process
        first = session.advance(handle, start_index=0, count=150)
        self.assertIsNone(child.poll())
        self.assertEqual(first['end_index_exclusive'], 150)
        session.advance(handle, start_index=150, count=151)
        session.advance(handle, start_index=301, count=300)
        result = session.finish(handle)
        self.assertIs(session._process, child)
        self.assertIsNone(child.poll())
      worker_spawns = [call for call in spawn.call_args_list if 'lateral_session_worker.py' in str(call.args[0])]
      self.assertEqual(len(worker_spawns), 1)
    reference = continuity.execute_experiment(continuity.build_request([150, 151, 300]))
    self.assertEqual(canonical(result), canonical(reference))
    self.assertTrue(all(result[name] is False for name in a1.AUTHORITIES))
    self.assert_reaped(session)
    self.assertEqual(session._process.returncode, 0)

  def test_completed_epochs_start_fresh_without_restarting_child(self):
    with self.api.LateralSession(timeout_s=10.) as session:
      first_handle = session.open_epoch(self.epoch)
      child = session._process
      first = self.complete(session, first_handle)
      second_handle = session.open_epoch(self.epoch)
      self.assertEqual(second_handle.epoch_id, first_handle.epoch_id + 1)
      self.assertIs(session._process, child)
      second = self.complete(session, second_handle)
      self.assertEqual(canonical(first), canonical(second))
    self.assert_reaped(session)

  def test_abort_drops_partial_state_before_next_epoch(self):
    with self.api.LateralSession(timeout_s=10.) as session:
      first = session.open_epoch(self.epoch)
      session.advance(first, start_index=0, count=240)
      aborted = session.abort(first)
      self.assertEqual(aborted, {'processed_frames': 240, 'completed': False})
      fresh = session.open_epoch(self.epoch)
      result = self.complete(session, fresh)
    self.assertEqual(result, continuity.execute_experiment(continuity.build_request([150, 151, 300])))

  def test_close_partial_is_not_completion_and_reaps_owned_child(self):
    session = self.api.LateralSession(timeout_s=10.)
    handle = session.open_epoch(self.epoch)
    session.advance(handle, start_index=0, count=20)
    result = session.close()
    self.assertEqual(result['status'], 'CLOSED')
    self.assertNotIn('comparison', result)
    self.assertEqual(result['worker_returncode'], 0)
    self.assert_reaped(session)
    session.close()
    with self.assertRaises(self.api.SessionError):
      session.advance(handle, start_index=20, count=1)

  def test_invalid_partition_job_permanently_closes_session(self):
    for start, count in ((1, 1), (0, 0), (0, -1), (0, True), (0, 1.5), (0, 602)):
      with self.subTest(start=start, count=count), self.api.LateralSession(timeout_s=10.) as session:
        handle = session.open_epoch(self.epoch)
        with self.assertRaises(self.api.SessionError):
          session.advance(handle, start_index=start, count=count)
        self.assert_reaped(session)
        with self.assertRaises(self.api.SessionError):
          session.open_epoch(self.epoch)

  def test_partial_finish_is_rejected_not_accepted_or_resumed(self):
    with self.api.LateralSession(timeout_s=10.) as session:
      handle = session.open_epoch(self.epoch)
      session.advance(handle, start_index=0, count=150)
      with self.assertRaises(self.api.SessionError) as caught:
        session.finish(handle)
      self.assertNotIn('comparison', caught.exception.receipt)
      self.assert_reaped(session)

  def test_stale_and_foreign_handles_cannot_rebind_state(self):
    for field, value in (('epoch_id', 99), ('epoch_sha256', '0' * 64), ('session_id', '0' * 32)):
      with self.subTest(field=field), self.api.LateralSession(timeout_s=10.) as session:
        handle = session.open_epoch(self.epoch)
        with self.assertRaises(self.api.SessionError):
          session.advance(replace(handle, **{field: value}), start_index=0, count=1)
        self.assert_reaped(session)
    with self.api.LateralSession(timeout_s=10.) as session:
      old = session.open_epoch(self.epoch)
      session.abort(old)
      session.open_epoch(self.epoch)
      with self.assertRaises(self.api.SessionError):
        session.advance(old, start_index=0, count=1)
      self.assert_reaped(session)

  def test_public_epoch_rejects_config_frames_and_extra_fields_before_spawn(self):
    variants = []
    for fixture in ('factor', 'combined', 'identity'):
      epoch = copy.deepcopy(self.epoch)
      epoch['continuity']['fixture_request']['fixture'] = fixture
      variants.append(epoch)
    variants += [dict(self.epoch, frames=[]), dict(self.epoch, configuration={'private': 1})]
    for epoch in variants:
      with self.subTest(epoch=list(epoch)), patch.object(self.api.subprocess, 'Popen') as spawn:
        with self.api.LateralSession(timeout_s=10.) as session, self.assertRaises(self.api.SessionError):
          session.open_epoch(epoch)
        spawn.assert_not_called()

  def test_source_mismatch_before_launch_and_during_epoch_is_terminal(self):
    bad = copy.deepcopy(self.epoch)
    name = next(iter(bad['overlay']))
    bad['overlay'][name] = '0' * 64
    with patch.object(self.api.subprocess, 'Popen') as spawn:
      with self.api.LateralSession(timeout_s=10.) as session, self.assertRaises(self.api.SessionError):
        session.open_epoch(bad)
      spawn.assert_not_called()
    with self.api.LateralSession(timeout_s=10.) as session:
      handle = session.open_epoch(self.epoch)
      with patch.object(self.protocol, 'verify_epoch', side_effect=ValueError('PRIVATE_SOURCE_PATH')):
        with self.assertRaises(self.api.SessionError) as caught:
          session.advance(handle, start_index=0, count=1)
      self.assertNotIn('PRIVATE_SOURCE_PATH', canonical(caught.exception.receipt).decode())
      self.assert_reaped(session)

  def test_caller_epoch_mutation_does_not_rebind_running_input(self):
    original = copy.deepcopy(self.epoch)
    with self.api.LateralSession(timeout_s=10.) as session:
      handle = session.open_epoch(self.epoch)
      self.epoch['continuity']['fixture_request']['fixture'] = 'factor'
      self.epoch['overlay'].clear()
      result = self.complete(session, handle)
    self.assertEqual(result, continuity.execute_experiment(original['continuity'] | {'chunk_sizes': [150, 151, 300]}))

  def test_protocol_duplicate_sequence_and_source_changes_close_native_state(self):
    proto = self.protocol
    open_request = proto.make_message('1' * 32, 0, 1, 'OPEN', self.epoch)
    for delta in ({'sequence': 0}, {'session_id': '2' * 32}, {'epoch_id': 2}):
      with self.subTest(delta=delta), proto.EpochMachine() as machine:
        machine.dispatch(open_request)
        job = proto.make_message('1' * 32, 1, 1, 'ADVANCE',
                                 {'epoch_sha256': digest(proto.encode_epoch(self.epoch)), 'start_index': 0, 'count': 20})
        with self.assertRaises(ValueError):
          machine.dispatch(job | delta)
        self.assertTrue(machine.closed)
        with self.assertRaises(ValueError):
          machine.dispatch(job)
    with proto.EpochMachine() as machine:
      machine.dispatch(open_request)
      with patch.object(proto, 'verify_epoch', side_effect=ValueError('SOURCE_CHANGED')):
        with self.assertRaises(ValueError):
          machine.dispatch(proto.make_message('1' * 32, 1, 1, 'ABORT', {'epoch_sha256': digest(proto.encode_epoch(self.epoch))}))
      self.assertTrue(machine.closed)

  def test_machine_native_advances_are_lazy_and_restore_context_on_abort(self):
    from openpilot.selfdrive.controls.lib.latcontrol_torque import LatControlTorque
    calls, original = [], LatControlTorque.update

    def counted(controller, *args, **kwargs):
      calls.append(1)
      return original(controller, *args, **kwargs)

    before = list(sys.path)
    with patch.object(LatControlTorque, 'update', counted), self.protocol.EpochMachine() as machine:
      machine.dispatch(self.protocol.make_message('1' * 32, 0, 1, 'OPEN', self.epoch))
      self.assertEqual(len(calls), 0)
      body = {'epoch_sha256': digest(self.protocol.encode_epoch(self.epoch)), 'start_index': 0, 'count': 20}
      machine.dispatch(self.protocol.make_message('1' * 32, 1, 1, 'ADVANCE', body))
      self.assertEqual(len(calls), 20)
      machine.dispatch(self.protocol.make_message('1' * 32, 2, 1, 'ABORT', {'epoch_sha256': body['epoch_sha256']}))
      self.assertEqual(len(calls), 20)
    self.assertEqual(sys.path, before)

  def test_response_rebinding_is_rejected_and_cleanup_confirmed(self):
    with self.api.LateralSession(timeout_s=10.) as session:
      handle = session.open_epoch(self.epoch)
      exchange = session._exchange

      def corrupt(payload):
        response = exchange(payload)
        response['request_sha256'] = '0' * 64
        response['PRIVATE_SENTINEL'] = 'discard'
        return response

      with patch.object(session, '_exchange', side_effect=corrupt), self.assertRaises(self.api.SessionError) as caught:
        session.advance(handle, start_index=0, count=1)
      self.assertNotIn('PRIVATE_SENTINEL', canonical(caught.exception.receipt).decode())
      self.assert_reaped(session)

  def test_final_validation_detects_tampered_intermediate_checkpoint(self):
    with self.api.LateralSession(timeout_s=10.) as session:
      handle = session.open_epoch(self.epoch)
      exchange = session._exchange

      def corrupt(payload):
        response = exchange(payload)
        response['data']['end_state_sha256'] = '0' * 64
        return response

      with patch.object(session, '_exchange', side_effect=corrupt):
        session.advance(handle, start_index=0, count=150)
      session.advance(handle, start_index=150, count=451)
      with self.assertRaises(self.api.SessionError):
        session.finish(handle)
      self.assert_reaped(session)

  def test_real_timeout_preserves_failure_and_cannot_retry(self):
    with self.api.LateralSession(timeout_s=.001) as session:
      with self.assertRaises(self.api.SessionError) as caught:
        session.open_epoch(self.epoch)
      self.assertEqual(caught.exception.receipt['status'], 'TIMEOUT')
      self.assertIs(type(caught.exception.receipt['worker_returncode']), int)
      self.assertTrue(caught.exception.receipt['cleanup_confirmed'])
      self.assert_reaped(session)

  def test_child_signal_exit_is_observed_and_unrelated_process_survives(self):
    unrelated = subprocess.Popen([sys.executable, '-c', 'import time;time.sleep(30)'], start_new_session=True)
    try:
      with self.api.LateralSession(timeout_s=10.) as session:
        handle = session.open_epoch(self.epoch)
        os.killpg(session._process.pid, signal.SIGKILL)
        session._process.wait(timeout=5.)
        with self.assertRaises(self.api.SessionError) as caught:
          session.advance(handle, start_index=0, count=1)
        self.assertEqual(caught.exception.receipt['worker_returncode'], -signal.SIGKILL)
        self.assert_reaped(session)
        self.assertIsNone(unrelated.poll())
    finally:
      unrelated.kill()
      unrelated.wait(timeout=5.)

  def test_interruption_terminates_only_owned_session(self):
    session = self.api.LateralSession(timeout_s=10.)
    handle = session.open_epoch(self.epoch)
    with patch.object(session, '_exchange', side_effect=KeyboardInterrupt), self.assertRaises(KeyboardInterrupt):
      session.advance(handle, start_index=0, count=1)
    self.assert_reaped(session)

  def test_raw_worker_malformed_input_does_not_leak_content(self):
    worker = Path(self.api.__file__).with_name('lateral_session_worker.py')
    for payload in (b'{"PRIVATE_SENTINEL":1}\n', b'{"version":1,"version":1}\n', b'[]\n', b'\xff\n'):
      result = _run_process([sys.executable, '-I', str(worker)], payload, 10.)
      self.assertEqual((result.status, result.returncode), ('EXITED', 1))
      self.assertEqual(json.loads(result.stdout), {'status': 'REJECTED', 'code': 'INVALID_OR_FAILED_SESSION'})

  def test_eof_after_partial_job_never_reports_completed_epoch(self):
    proto = self.protocol
    opening = proto.make_message('1' * 32, 0, 1, 'OPEN', self.epoch)
    advance = proto.make_message('1' * 32, 1, 1, 'ADVANCE',
                                 {'epoch_sha256': digest(proto.encode_epoch(self.epoch)), 'start_index': 0, 'count': 240})
    payload = proto.encode_message(opening) + b'\n' + proto.encode_message(advance) + b'\n'
    worker = Path(self.api.__file__).with_name('lateral_session_worker.py')
    result = _run_process([sys.executable, '-I', str(worker)], payload, 10.)
    self.assertEqual(result.returncode, 1)
    rows = [json.loads(line) for line in result.stdout.splitlines()]
    self.assertEqual([row['status'] for row in rows], ['OPENED', 'ADVANCED', 'REJECTED'])
    self.assertTrue(all('comparison' not in row.get('data', {}) for row in rows))

  def test_independent_sessions_have_distinct_correlation_but_equal_completed_data(self):
    results, identifiers = [], []
    for _ in range(2):
      with self.api.LateralSession(timeout_s=10.) as session:
        handle = session.open_epoch(self.epoch)
        identifiers.append(handle.session_id)
        results.append(self.complete(session, handle))
    self.assertNotEqual(identifiers[0], identifiers[1])
    self.assertEqual(canonical(results[0]), canonical(results[1]))


if __name__ == '__main__':
  unittest.main()
