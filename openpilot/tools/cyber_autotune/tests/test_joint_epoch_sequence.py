"""Different synthetic epochs require ordered admission and explicit fresh resets."""
import copy
import importlib
import importlib.util
import json
import unittest
from unittest.mock import patch

from openpilot.tools.cyber_autotune import joint_continuity as joint, joint_session as ipc
from openpilot.tools.cyber_autotune import joint_session_protocol as protocol, native_protocol as native, paired_shadow
from openpilot.tools.cyber_autotune.lateral_session import SessionError
from openpilot.tools.cyber_autotune.native_runner import _owned_group_running
from openpilot.tools.cyber_autotune.tests.test_joint_continuity import pair_fixture


# Different requested targets in synthetic software tests, not vehicle tuning.
SYNTHETIC_TARGET_INCREMENT_MPS2 = .05


def sequence_epochs(count=2):
  base = paired_shadow.decode_request(pair_fixture(True))
  result = []
  for index in range(count):
    pair = copy.deepcopy(base)
    offset = index * len(pair['frames']['lateral']) * native.TIMESTEP_NS
    for axis in paired_shadow.AXES:
      for frame in pair['frames'][axis]:
        frame['time_ns'] += offset
    for frame in pair['frames']['longitudinal']:
      frame['a_target_mps2'] += index * SYNTHETIC_TARGET_INCREMENT_MPS2
    result.append(protocol.encode_epoch(ipc.build_epoch(paired_shadow.encode_request(pair), [7, 5, 8])))
  return result


class TestJointEpochSequence(unittest.TestCase):
  def setUp(self):
    name = 'openpilot.tools.cyber_autotune.joint_epoch_sequence'
    self.assertIsNotNone(importlib.util.find_spec(name), 'Ordered changing-input sequence is not implemented')
    self.api = importlib.import_module(name)
    self.epochs = sequence_epochs()
    self.plan = self.api.build_sequence(self.epochs)

  def assert_failure(self, result, status):
    self.assertEqual(result['status'], status)
    self.assertNotIn('epochs', result)
    self.assertNotIn('axes', result)
    self.assertNotIn('PRIVATE_SENTINEL', json.dumps(result))
    self.assertTrue(all(result[name] is False for name in joint.AUTHORITIES))

  def test_changed_inputs_execute_in_order_with_closed_child_before_next(self):
    sessions = []
    def create(**kwargs):
      if sessions:
        self.assertIsNotNone(sessions[-1]._process.poll())
        self.assertFalse(_owned_group_running(sessions[-1]._process.pid))
      session = ipc.JointSession(**kwargs)
      sessions.append(session)
      return session
    with patch.object(self.api, 'JointSession', side_effect=create):
      result = self.api.run_sequence(self.plan, timeout_s=15.)
    self.assertEqual(result['status'], self.api.PASS)
    self.assertEqual(len(result['epochs']), 2)
    self.assertEqual(len(sessions), 2)
    self.assertIsNot(sessions[0]._process, sessions[1]._process)
    for index, row in enumerate(result['epochs']):
      epoch = protocol.decode_json(self.epochs[index])
      reference = joint.execute_experiment(epoch['joint'])
      self.assertEqual(row['index'], index)
      self.assertEqual(row['epoch_sha256'], native.digest(self.epochs[index]))
      self.assertEqual(row['result_sha256'], native.digest(native.canonical(reference)))
      self.assertEqual(row['boundary'], 'FRESH_PROCESS_RESET')
      self.assertEqual(row['worker_returncode'], 0)
      self.assertIs(row['cleanup_confirmed'], True)
      self.assertIsNotNone(sessions[index]._process.poll())
    self.assertNotEqual(result['epochs'][0]['result_sha256'], result['epochs'][1]['result_sha256'])
    self.assertFalse(result['state_carried_between_epochs'])
    self.assertTrue(all(result[name] is False for name in joint.AUTHORITIES))

  def test_fresh_reset_is_not_continuation_of_previous_integrator(self):
    pairs = [protocol.decode_json(epoch)['joint']['pair'] for epoch in self.epochs]
    combined = copy.deepcopy(pairs[0])
    for axis in paired_shadow.AXES:
      combined['frames'][axis].extend(copy.deepcopy(pairs[1]['frames'][axis]))
    full = joint.execute_experiment(joint.build_request(paired_shadow.encode_request(combined), [20, 20]))
    fresh = joint.execute_experiment(protocol.decode_json(self.epochs[1])['joint'])
    carried = full['axes']['longitudinal']['candidate']['continuity']['states'][20]['snapshot']['pid']['i']
    restarted = fresh['axes']['longitudinal']['candidate']['continuity']['states'][0]['snapshot']['pid']['i']
    self.assertNotEqual(carried, restarted)
    result = self.api.run_sequence(self.plan, timeout_s=15.)
    self.assertEqual(result['epochs'][1]['result_sha256'], native.digest(native.canonical(fresh)))

  def test_admission_checks_all_future_epochs_before_starting_first(self):
    for delta in (-native.TIMESTEP_NS, 1, native.TIMESTEP_NS):
      plan = self.api.decode_sequence(self.plan)
      for axis in paired_shadow.AXES:
        for frame in plan['epochs'][1]['joint']['pair']['frames'][axis]:
          frame['time_ns'] += delta
      with self.subTest(delta=delta), patch.object(self.api, 'JointSession') as spawn, self.assertRaises(ValueError):
        self.api.run_sequence(native.canonical(plan), timeout_s=5.)
      spawn.assert_not_called()

  def test_duplicate_reversed_or_config_changed_epochs_are_rejected(self):
    variants = ([self.epochs[0], self.epochs[0]], list(reversed(self.epochs)))
    for values in variants:
      with self.assertRaises(ValueError):
        self.api.build_sequence(values)
    changed = protocol.decode_json(self.epochs[1])
    other = protocol.decode_json(protocol.encode_epoch(ipc.build_epoch(pair_fixture(), [2, 3, 6])))
    for axis in paired_shadow.AXES:
      changed['joint']['pair'][axis] = other['joint']['pair'][axis]
    with self.assertRaises(ValueError):
      self.api.build_sequence([self.epochs[0], protocol.encode_epoch(changed)])

  def test_cross_axis_mismatch_and_unknown_fields_never_run(self):
    plan = self.api.decode_sequence(self.plan)
    plan['epochs'][1]['joint']['pair']['frames']['longitudinal'][0]['speed_mps'] += 1.
    variants = [plan, self.api.decode_sequence(self.plan) | {'runtime_accepted': True},
                self.api.decode_sequence(self.plan) | {'version': True}, self.api.decode_sequence(self.plan) | {'epochs': []}]
    for invalid in variants:
      with patch.object(self.api, 'JointSession') as spawn, self.assertRaises(ValueError):
        self.api.run_sequence(native.canonical(invalid), timeout_s=5.)
      spawn.assert_not_called()

  def test_size_frame_and_json_limits_are_not_expanded(self):
    for payload in (bytearray(self.plan), 'PRIVATE_SENTINEL', b'[]', b'{"version":1,"version":1}',
                    b'{"epochs":NaN}', b'\xff', b' ' * (native.MAX_REQUEST_BYTES + 1)):
      with self.subTest(kind=type(payload)), self.assertRaises(ValueError):
        self.api.decode_sequence(payload)
    with patch.object(self.api, 'MAX_TOTAL_FRAMES', 39), self.assertRaises(ValueError):
      self.api.decode_sequence(self.plan)
    with self.assertRaises(ValueError):
      self.api.build_sequence([])

  def test_source_drift_in_last_epoch_blocks_every_session(self):
    invalid = self.api.decode_sequence(self.plan)
    for epoch in invalid['epochs']:
      key = next(iter(epoch['overlay']))
      epoch['overlay'][key] = '0' * 64
    with patch.object(self.api, 'JointSession') as spawn:
      result = self.api.run_sequence(native.canonical(invalid), timeout_s=5.)
    spawn.assert_not_called()
    self.assert_failure(result, 'BINDING_REJECTED')
    self.assertEqual(result['completed_count'], 0)
    self.assertIsNone(result['worker_returncode'])

  def test_input_bytes_are_frozen_and_public_report_has_no_raw_frames_or_paths(self):
    caller = list(self.epochs)
    plan = self.api.build_sequence(caller)
    caller[:] = []
    result = self.api.run_sequence(plan, timeout_s=15.)
    self.assertEqual(result['status'], self.api.PASS)
    encoded = native.canonical(result)
    for token in (b'car_params_base64', b'"frames"', str(joint.ROOT).encode(), b'pid_i', b'"samples"'):
      self.assertNotIn(token, encoded)
    self.assertEqual(plan, self.plan)

  def test_second_epoch_failure_stops_third_and_strips_success_rows(self):
    epochs = sequence_epochs(3)
    broken = protocol.decode_json(epochs[1])
    broken['joint']['pair']['frames']['longitudinal'][3]['a_target_mps2'] = 1e308
    epochs[1] = protocol.encode_epoch(broken)
    sessions = []
    def create(**kwargs):
      session = ipc.JointSession(**kwargs)
      sessions.append(session)
      return session
    with patch.object(self.api, 'JointSession', side_effect=create):
      result = self.api.run_sequence(self.api.build_sequence(epochs), timeout_s=15.)
    self.assert_failure(result, 'SESSION_FAILED')
    self.assertEqual(len(sessions), 2)
    self.assertEqual(result['completed_count'], 1)
    self.assertEqual(result['failed_index'], 1)
    self.assertTrue(all(session.closed for session in sessions))
    self.assertTrue(result['cleanup_confirmed'])

  def test_unconfirmed_close_prevents_transition_and_returns_no_success(self):
    close = ipc.JointSession.close
    def unconfirmed(session):
      receipt = close(session)
      return receipt | {'cleanup_confirmed': False}
    with patch.object(ipc.JointSession, 'close', unconfirmed), patch.object(self.api, 'JointSession', wraps=ipc.JointSession) as spawn:
      result = self.api.run_sequence(self.plan, timeout_s=15.)
    self.assert_failure(result, 'CLEANUP_UNCONFIRMED')
    self.assertEqual(spawn.call_count, 1)
    self.assertEqual(result['completed_count'], 0)
    self.assertFalse(result['cleanup_confirmed'])

  def test_malformed_result_does_not_become_success_or_start_next(self):
    finish = ipc.JointSession.finish
    def forged(session, handle):
      result = finish(session, handle)
      result['runtime_accepted'] = True
      result['PRIVATE_SENTINEL'] = 'raw'
      return result
    with patch.object(ipc.JointSession, 'finish', forged), patch.object(self.api, 'JointSession', wraps=ipc.JointSession) as spawn:
      result = self.api.run_sequence(self.plan, timeout_s=15.)
    self.assert_failure(result, 'INVALID_RESULT')
    self.assertEqual(spawn.call_count, 1)
    self.assertEqual(result['completed_count'], 0)

  def test_budget_is_shared_and_expiry_after_close_stops_next_epoch(self):
    clock = [100.]
    advance, close = ipc.JointSession.advance, ipc.JointSession.close
    budgets = []
    def consume(session, *args, **kwargs):
      budgets.append(session._timeout)
      result = advance(session, *args, **kwargs)
      clock[0] += .2
      return result
    def expire(session):
      result = close(session)
      clock[0] = 103.
      return result
    with patch.object(self.api, 'monotonic', lambda: clock[0]), patch.object(ipc.JointSession, 'advance', consume), \
         patch.object(ipc.JointSession, 'close', expire), patch.object(self.api, 'JointSession', wraps=ipc.JointSession) as spawn:
      result = self.api.run_sequence(self.plan, timeout_s=2.)
    self.assert_failure(result, 'TIMEOUT')
    self.assertEqual(spawn.call_count, 1)
    self.assertGreater(budgets[0], budgets[1])
    self.assertGreater(budgets[1], budgets[2])

  def test_interruption_keeps_original_exception_and_reaps_owned_child(self):
    sessions = []
    def create(**kwargs):
      session = ipc.JointSession(**kwargs)
      sessions.append(session)
      return session
    original = KeyboardInterrupt('CALLER_PRIVATE_TEXT')
    with patch.object(self.api, 'JointSession', side_effect=create), patch.object(ipc.JointSession, 'advance', side_effect=original):
      with self.assertRaises(KeyboardInterrupt) as caught:
        self.api.run_sequence(self.plan, timeout_s=15.)
    self.assertIs(caught.exception, original)
    self.assertEqual(len(sessions), 1)
    self.assertTrue(sessions[0].closed)
    self.assertFalse(_owned_group_running(sessions[0]._process.pid))

  def test_real_timeout_and_invalid_timeout_values_never_qualify(self):
    for value in (True, 0., -1., 61., float('inf'), float('nan')):
      with self.subTest(value=value), self.assertRaises(ValueError):
        self.api.run_sequence(self.plan, timeout_s=value)
    result = self.api.run_sequence(self.plan, timeout_s=.001)
    self.assert_failure(result, 'TIMEOUT')
    self.assertEqual(result['completed_count'], 0)

  def test_old_same_session_rule_still_rejects_changed_input(self):
    with ipc.JointSession(timeout_s=10.) as session:
      first = session.open_epoch(protocol.decode_json(self.epochs[0]))
      session.abort(first)
      with self.assertRaises(SessionError):
        session.open_epoch(protocol.decode_json(self.epochs[1]))
    self.assertTrue(session.closed)

  def test_identical_plan_repeats_exact_summary_with_no_session_ids(self):
    first = self.api.run_sequence(self.plan, timeout_s=15.)
    second = self.api.run_sequence(self.plan, timeout_s=15.)
    self.assertEqual(first['status'], self.api.PASS)
    self.assertEqual(native.canonical(first), native.canonical(second))
    self.assertNotIn('session_id', json.dumps(first))


if __name__ == '__main__':
  unittest.main()
