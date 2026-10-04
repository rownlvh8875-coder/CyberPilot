"""Finite logical joint epochs, no device or physical qualification."""
import base64
import copy
import importlib
import importlib.util
from pathlib import Path
import sys
import threading
import unittest
from unittest.mock import patch

from opendbc.car import structs
from openpilot.tools.cyber_autotune import native_long_worker as long_worker
from openpilot.tools.cyber_autotune import native_protocol as lat, native_long_protocol as lng, paired_shadow
from openpilot.tools.cyber_autotune.native_runner import ProcessOutcome, _run_process
from openpilot.tools.cyber_autotune.tests.test_paired_shadow import requests


def pair_fixture(nonzero_ki=False):
  lateral, longitudinal = requests(full=True)
  if nonzero_ki:
    with structs.CarParams.from_bytes(base64.b64decode(longitudinal['car_params_base64'])) as reader:
      cp = reader.as_builder()
    # Exact nonzero gain/range already exercised by test_native_long_worker;
    # synthetic test only, not a candidate or recommended vehicle tuning.
    cp.longitudinalTuning.kiBP = [0., 30.]
    cp.longitudinalTuning.kiV = [.1, .2]
    raw = cp.to_bytes()
    for request in (lateral, longitudinal):
      request['car_params_base64'] = base64.b64encode(raw).decode()
      request['car_params_sha256'] = lat.digest(raw)
    left, right = lateral['frames'][1], longitudinal['frames'][1]
    lateral['frames'] = [dict(left, time_ns=i * lat.TIMESTEP_NS, accel_mps2=.023456789) for i in range(20)]
    longitudinal['frames'] = [dict(right, time_ns=i * lat.TIMESTEP_NS, a_target_mps2=.123456789,
                                  accel_mps2=.023456789) for i in range(20)]
  return paired_shadow.pack_requests(lat.encode_request(lateral), lng.encode_request(longitudinal))


class TestJointContinuity(unittest.TestCase):
  def setUp(self):
    name = 'openpilot.tools.cyber_autotune.joint_continuity'
    self.assertIsNotNone(importlib.util.find_spec(name), 'Longitudinal and joint state continuity is not implemented')
    self.api = importlib.import_module(name)
    self.pair = pair_fixture()
    self.request = self.api.build_request(self.pair, [2, 3, 6])
    self.lateral, self.longitudinal = paired_shadow._split(paired_shadow.decode_request(self.pair))

  def test_long_legacy_return_shape_and_all_samples_remain_unchanged(self):
    baseline = long_worker._execute_request(self.longitudinal)
    with self.api._LongChunkCursor(self.longitudinal) as cursor:
      cursor.advance(2)
      cursor.advance(3)
      cursor.advance(6)
      captured = cursor.finish()
    self.assertEqual({key: value for key, value in captured.items() if key != 'continuity'}, baseline)
    self.assertEqual(captured['continuity']['state_schema'], 'native-long-state-v1')
    self.assertEqual(len(captured['continuity']['states']), 11)
    self.assertNotIn('continuity', baseline)

  def test_same_native_output_and_states_under_all_partition_patterns(self):
    baseline = self.api.execute_experiment(self.api.build_request(self.pair, [11]))
    for sizes in ([2, 3, 6], [1] * 11, [4, 7], [10, 1]):
      with self.subTest(sizes=sizes):
        request = self.api.build_request(self.pair, sizes)
        result = self.api.execute_experiment(request)
        self.api.validate_response(request, result)
        self.assertEqual(result['axes'], baseline['axes'])
        for axis in paired_shadow.AXES:
          self.assertEqual(result['axes'][axis]['baseline'], result['axes'][axis]['candidate'])
        self.assertEqual(len(result['checkpoints']), len(sizes))
        self.assertTrue(all(result[name] is False for name in self.api.AUTHORITIES))

  def test_advances_execute_exact_native_frame_counts_not_prefix_replay(self):
    from openpilot.selfdrive.controls.lib.latcontrol_torque import LatControlTorque
    from openpilot.selfdrive.controls.lib.longcontrol import LongControl
    counts = [0, 0]
    left, right = LatControlTorque.update, LongControl.update

    def count_left(controller, *args, **kwargs):
      counts[0] += 1
      return left(controller, *args, **kwargs)

    def count_right(controller, *args, **kwargs):
      counts[1] += 1
      return right(controller, *args, **kwargs)

    before = list(sys.path)
    with patch.object(LatControlTorque, 'update', count_left), patch.object(LongControl, 'update', count_right):
      with self.api._JointEpoch(self.request) as epoch:
        self.assertEqual(counts, [0, 0])
        epoch.advance(2)
        self.assertEqual(counts, [2, 2])
        epoch.advance(3)
        self.assertEqual(counts, [5, 5])
        epoch.advance(6)
        self.assertEqual(counts, [11, 11])
        result = epoch.finish()
        self.assertEqual(counts, [11, 11])
        self.assertEqual(set(result), set(paired_shadow.AXES))
    self.assertEqual(sys.path, before)

  def test_stopping_history_reset_is_observably_not_continuation(self):
    full = long_worker._execute_request(self.longitudinal, _capture_state=True)
    fresh = long_worker._execute_request(dict(self.longitudinal, frames=self.longitudinal['frames'][3:]), _capture_state=True)
    self.assertNotEqual(full['samples'][3]['requested_accel_mps2'], fresh['samples'][0]['requested_accel_mps2'])
    self.assertNotEqual(full['continuity']['states'][3]['state_sha256'], fresh['continuity']['states'][0]['state_sha256'])
    with self.api._LongChunkCursor(self.longitudinal) as cursor:
      cursor.advance(3)
      cursor.advance(8)
      self.assertEqual(cursor.finish(), full)

  def test_nonzero_pid_integrator_survives_chunks_and_starts_fresh(self):
    pair = pair_fixture(nonzero_ki=True)
    request = self.api.build_request(pair, [7, 5, 8])
    first = self.api.execute_experiment(request)
    second = self.api.execute_experiment(request)
    self.assertEqual(first, second)
    states = first['axes']['longitudinal']['candidate']['continuity']['states']
    self.assertGreater(states[-1]['snapshot']['pid']['i'], states[0]['snapshot']['pid']['i'])
    native = paired_shadow._split(paired_shadow.decode_request(pair))[1]
    reset = long_worker._execute_request(dict(native, frames=native['frames'][7:]), _capture_state=True)
    self.assertNotEqual(reset['samples'][0], first['axes']['longitudinal']['candidate']['samples'][7])

  def test_caller_input_and_checkpoint_mutations_do_not_change_epoch(self):
    request = copy.deepcopy(self.request)
    with self.api._JointEpoch(request) as epoch:
      first = epoch.advance(2)
      request['pair']['frames']['longitudinal'][2]['a_target_mps2'] = 1e100
      first['axes']['lateral']['end_state_sha256'] = '0' * 64
      epoch.advance(3)
      epoch.advance(6)
      result = epoch.finish()
    self.assertEqual(result['longitudinal'], long_worker._execute_request(self.longitudinal, _capture_state=True))

  def test_abort_closes_both_without_returning_partial_success(self):
    before = list(sys.path)
    with self.api._JointEpoch(self.request) as epoch:
      epoch.advance(2)
      epoch.close()
      self.assertTrue(epoch.closed)
      self.assertTrue(all(cursor._closed for cursor in epoch._cursors))
      with self.assertRaises(ValueError):
        epoch.advance(3)
      with self.assertRaises(ValueError):
        epoch.finish()
    self.assertEqual(sys.path, before)
    self.assertEqual(self.api.execute_experiment(self.request), self.api.execute_experiment(self.request))

  def test_invalid_advance_or_incomplete_finish_closes_both(self):
    for action in (lambda epoch: epoch.advance(1), lambda epoch: epoch.advance(True),
                   lambda epoch: epoch.advance(0), lambda epoch: epoch.finish()):
      with self.subTest(action=action), self.api._JointEpoch(self.request) as epoch:
        epoch.advance(2)
        with self.assertRaises(ValueError):
          action(epoch)
        self.assertTrue(epoch.closed)
        self.assertTrue(all(cursor._closed for cursor in epoch._cursors))

  def test_native_failure_in_either_axis_terminates_joint_state(self):
    for axis, field in (('lateral', 'desired_curvature_1pm'), ('longitudinal', 'a_target_mps2')):
      envelope = paired_shadow.decode_request(self.pair)
      envelope['frames'][axis][3][field] = 1e308
      request = self.api.build_request(paired_shadow.encode_request(envelope), [2, 3, 6])
      before = list(sys.path)
      with self.subTest(axis=axis), self.api._JointEpoch(request) as epoch:
        epoch.advance(2)
        with self.assertRaises((ValueError, FloatingPointError)):
          epoch.advance(3)
        self.assertTrue(epoch.closed)
        self.assertTrue(all(cursor._closed for cursor in epoch._cursors))
        with self.assertRaises(ValueError):
          epoch.finish()
      self.assertEqual(sys.path, before)

  def test_interruption_preserves_original_and_attempts_both_closes(self):
    with self.api._JointEpoch(self.request) as epoch:
      epoch.advance(2)
      original = KeyboardInterrupt('CALLER_PRIVATE')
      calls = []
      first, second = epoch._cursors
      close_first, close_second = first.close, second.close

      def close_left():
        calls.append('lateral')
        close_first()

      def close_right():
        calls.append('longitudinal')
        close_second()
        raise ValueError('PRIVATE_CLOSE_FAILURE')

      with patch.object(first, 'advance', side_effect=original), patch.object(first, 'close', close_left), \
           patch.object(second, 'close', close_right), self.assertRaises(KeyboardInterrupt) as caught:
        epoch.advance(3)
      self.assertIs(caught.exception, original)
      self.assertEqual(calls, ['longitudinal', 'lateral'])
      self.assertTrue(epoch.closed)
      self.assertFalse(epoch.cleanup_confirmed)
      self.assertNotIn('PRIVATE_CLOSE_FAILURE', str(getattr(original, '__notes__', [])))

  def test_wrong_thread_cannot_consume_or_close_owner_epoch(self):
    result = []
    with self.api._JointEpoch(self.request) as epoch:
      def other():
        try:
          epoch.close()
        except ValueError:
          result.append('REJECTED')
      thread = threading.Thread(target=other)
      thread.start()
      thread.join(timeout=3.)
      self.assertFalse(thread.is_alive())
      self.assertEqual(result, ['REJECTED'])
      self.assertFalse(epoch.closed)
      for count in (2, 3, 6):
        epoch.advance(count)
      self.assertEqual(set(epoch.finish()), set(paired_shadow.AXES))

  def test_mismatched_pair_and_bad_partition_block_before_native_execution(self):
    variants = []
    for field in ('time_ns', 'speed_mps', 'accel_mps2'):
      request = copy.deepcopy(self.request)
      request['pair']['frames']['longitudinal'][0][field] += 1
      variants.append(request)
    for sizes in ([], [10], [12], [True, 10], [1.0, 10], [11, 0], None):
      variants.append(dict(self.request, chunk_sizes=sizes))
    for index, request in enumerate(variants):
      with self.subTest(case=index), patch.object(self.api, '_run_process') as run:
        with self.assertRaises(ValueError):
          self.api.run_experiment(request, timeout_s=5.)
        run.assert_not_called()

  def test_source_drift_before_and_during_epoch_is_terminal(self):
    bad = copy.deepcopy(self.request)
    bad['overlay'][next(iter(bad['overlay']))] = '0' * 64
    with patch.object(self.api, '_run_process') as run:
      result = self.api.run_experiment(bad, timeout_s=5.)
      self.assertEqual(result['status'], 'BINDING_REJECTED')
      run.assert_not_called()
    with self.api._JointEpoch(self.request) as epoch:
      epoch.advance(2)
      with patch.object(self.api, '_verify_bindings', side_effect=ValueError('PRIVATE_SOURCE_PATH')):
        with self.assertRaises(ValueError):
          epoch.advance(3)
      self.assertTrue(epoch.closed)
      self.assertTrue(all(cursor._closed for cursor in epoch._cursors))

  def test_rebound_response_bad_states_and_forged_authority_are_rejected(self):
    original = self.api.execute_experiment(self.request)
    variants = []
    for axis in paired_shadow.AXES:
      result = copy.deepcopy(original)
      result['axes'][axis]['candidate']['samples'][1]['time_ns'] += 1
      variants.append(result)
    result = copy.deepcopy(original)
    result['axes']['longitudinal']['candidate']['continuity']['states'][1]['snapshot']['pid']['i'] += .1
    variants.append(result)
    result = copy.deepcopy(original)
    result['checkpoints'][0]['axes']['longitudinal']['end_state_sha256'] = '0' * 64
    result['checkpoints_sha256'] = lat.digest(lat.canonical(result['checkpoints']))
    variants.append(result)
    for name in self.api.AUTHORITIES:
      variants.append(dict(original, **{name: True}))
    for index, result in enumerate(variants):
      with self.subTest(case=index), self.assertRaises(ValueError):
        self.api.validate_response(self.request, result)
    with self.assertRaises(ValueError):
      self.api.validate_response(self.api.build_request(self.pair, [11]), original)

  def test_supervisor_failure_precedence_privacy_and_postrun_source_check(self):
    for status, code, expected in (('TIMEOUT', 0, 'TIMEOUT'), ('TIMEOUT', -9, 'TIMEOUT'), ('EXITED', 7, 'WORKER_FAILED'),
                                   ('EXITED', 0, 'INVALID_RESPONSE')):
      with self.subTest(status=status, code=code), patch.object(self.api, '_run_process', return_value=ProcessOutcome(status, code, b'PRIVATE_SENTINEL', 1)):
        result = self.api.run_experiment(self.request, timeout_s=5.)
      self.assertEqual(result, {'status': expected, 'worker_returncode': code,
                               'request_sha256': lat.digest(self.api.encode_request(self.request)),
                               **dict.fromkeys(self.api.AUTHORITIES, False)})
    valid = self.api.execute_experiment(self.request)
    with patch.object(self.api, '_run_process', return_value=ProcessOutcome('EXITED', 0, lat.canonical(valid), 1)), \
         patch.object(self.api, '_verify_bindings', side_effect=[None, ValueError('SOURCE_CHANGED')]):
      self.assertEqual(self.api.run_experiment(self.request, timeout_s=5.)['status'], 'INVALID_RESPONSE')

  def test_real_worker_repeatability_and_real_timeout(self):
    first = self.api.run_experiment(self.request, timeout_s=20.)
    second = self.api.run_experiment(self.request, timeout_s=20.)
    self.assertEqual(first['status'], self.api.PASS)
    self.assertEqual(lat.canonical(first), lat.canonical(second))
    self.assertEqual(first, self.api.execute_experiment(self.request))
    expired = self.api.run_experiment(self.request, timeout_s=.001)
    self.assertEqual(expired['status'], 'TIMEOUT')
    self.assertNotIn('axes', expired)

  def test_raw_worker_rejects_bad_content_without_reflection(self):
    worker = Path(self.api.__file__).with_name('joint_continuity_worker.py')
    outcome = _run_process([sys.executable, '-I', str(worker)], b'{"PRIVATE_SENTINEL":"route"}', 10.)
    self.assertEqual((outcome.status, outcome.returncode), ('EXITED', 1))
    self.assertEqual(outcome.stdout.strip(), lat.canonical({'status': 'REJECTED', 'code': 'INVALID_OR_FAILED_JOINT_REQUEST'}))


if __name__ == '__main__':
  unittest.main()
