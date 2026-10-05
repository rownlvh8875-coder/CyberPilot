"""Predetermined segment boundaries must not reset the shared native epoch."""
import copy
import importlib
import importlib.util
import json
import unittest
from unittest.mock import patch

from openpilot.tools.cyber_autotune import joint_continuity as joint, joint_session_protocol as protocol
from openpilot.tools.cyber_autotune import joint_epoch_sequence as resets, native_protocol as native, paired_shadow
from openpilot.tools.cyber_autotune.lateral_session import SessionError
from openpilot.tools.cyber_autotune.native_runner import _owned_group_running
from openpilot.tools.cyber_autotune.tests.test_joint_epoch_sequence import sequence_epochs


def combined_request(segments):
  """Independent construction of the unchanged one-shot native reference."""
  epochs = [protocol.decode_json(raw) for raw in segments]
  pair = copy.deepcopy(epochs[0]['joint']['pair'])
  for axis in paired_shadow.AXES:
    pair['frames'][axis] = [copy.deepcopy(frame) for epoch in epochs for frame in epoch['joint']['pair']['frames'][axis]]
  chunks = [count for epoch in epochs for count in epoch['joint']['chunk_sizes']]
  return joint.build_request(paired_shadow.encode_request(pair), chunks)


class TestSegmentedContinuity(unittest.TestCase):
  def setUp(self):
    name = 'openpilot.tools.cyber_autotune.joint_segmented_continuity'
    self.assertIsNotNone(importlib.util.find_spec(name), 'Predetermined segments are not connected to one native epoch')
    self.api = importlib.import_module(name)
    self.segments = sequence_epochs(2)
    self.plan = self.api.build_plan(self.segments)

  def assert_failure(self, result, status):
    self.assertEqual(result['status'], status)
    self.assertNotIn('segments', result)
    self.assertNotIn('axes', result)
    self.assertNotIn('native_result_sha256', result)
    self.assertTrue(all(result[name] is False for name in joint.AUTHORITIES))
    self.assertNotIn('PRIVATE_SENTINEL', json.dumps(result))

  def test_one_session_one_open_carries_both_states_across_segment_boundary(self):
    sessions, calls, outputs = [], [], []
    original = resets.JointSession
    advance, finish = original.advance, original.finish
    def create(**kwargs):
      session = original(**kwargs)
      sessions.append(session)
      return session
    def observed(session, handle, *, start_index, count):
      calls.append((handle.epoch_id, start_index, count, session._process))
      return advance(session, handle, start_index=start_index, count=count)
    def capture(session, handle):
      result = finish(session, handle)
      outputs.append(copy.deepcopy(result))
      return result
    with patch.object(self.api, 'JointSession', side_effect=create), patch.object(original, 'advance', observed), patch.object(original, 'finish', capture):
      result = self.api.run_plan(self.plan, timeout_s=15.)
    self.assertEqual(result['status'], self.api.PASS)
    self.assertEqual(len(sessions), 1)
    self.assertEqual([(epoch, start, count) for epoch, start, count, _ in calls],
                     [(1, 0, 7), (1, 7, 5), (1, 12, 8), (1, 20, 7), (1, 27, 5), (1, 32, 8)])
    self.assertTrue(all(child is sessions[0]._process for _, _, _, child in calls))
    self.assertEqual(outputs, [joint.execute_experiment(combined_request(self.segments))])
    self.assertEqual(result['native_result_sha256'], native.digest(native.canonical(outputs[0])))
    self.assertTrue(result['state_carried_between_segments'])
    self.assertTrue(result['cleanup_confirmed'])
    self.assertEqual(result['worker_returncode'], 0)
    self.assertFalse(_owned_group_running(sessions[0]._process.pid))

  def test_nonzero_integrator_is_not_reset_at_second_segment(self):
    result = self.api.run_plan(self.plan, timeout_s=15.)
    full = joint.execute_experiment(combined_request(self.segments))
    fresh = joint.execute_experiment(protocol.decode_json(self.segments[1])['joint'])
    carried = full['axes']['longitudinal']['candidate']['continuity']['states'][20]['snapshot']['pid']['i']
    restarted = fresh['axes']['longitudinal']['candidate']['continuity']['states'][0]['snapshot']['pid']['i']
    self.assertNotEqual(carried, restarted)
    self.assertEqual(result['segments'][1]['end_state_sha256']['longitudinal'],
                     full['axes']['longitudinal']['candidate']['continuity']['states'][-1]['state_sha256'])
    self.assertNotEqual(result['segments'][1]['end_state_sha256']['longitudinal'],
                        fresh['axes']['longitudinal']['candidate']['continuity']['states'][-1]['state_sha256'])

  def test_segment_boundaries_are_reporting_only_and_repartition_preserves_axes(self):
    request = combined_request(self.segments)
    epoch = copy.deepcopy(protocol.decode_json(self.segments[0]))
    repartitioned, start = [], 0
    for count in (13, 14, 13):
      item = copy.deepcopy(epoch)
      item['joint']['chunk_sizes'] = [count]
      for axis in paired_shadow.AXES:
        item['joint']['pair']['frames'][axis] = copy.deepcopy(request['pair']['frames'][axis][start:start + count])
      repartitioned.append(protocol.encode_epoch(item))
      start += count
    first = self.api.run_plan(self.plan, timeout_s=15.)
    second = self.api.run_plan(self.api.build_plan(repartitioned), timeout_s=15.)
    self.assertEqual(first['axes'], second['axes'])
    self.assertEqual(first['frame_count'], second['frame_count'])
    self.assertEqual(len(second['segments']), 3)
    self.assertEqual([(row['start_index'], row['end_index_exclusive']) for row in second['segments']], [(0, 13), (13, 27), (27, 40)])

  def test_all_future_time_or_configuration_mismatches_block_before_session(self):
    for mode in ('gap', 'overlap', 'config', 'axis'):
      values = [protocol.decode_json(raw) for raw in self.segments]
      second = values[1]['joint']['pair']
      if mode in ('gap', 'overlap'):
        for axis in paired_shadow.AXES:
          for frame in second['frames'][axis]:
            frame['time_ns'] += native.TIMESTEP_NS if mode == 'gap' else -native.TIMESTEP_NS
      elif mode == 'config':
        for axis in paired_shadow.AXES:
          second[axis]['source']['head'] = '0' * 40
      else:
        second['frames']['longitudinal'][0]['speed_mps'] += 1.
      with self.subTest(mode=mode), patch.object(self.api, 'JointSession') as spawn, self.assertRaises(ValueError):
        self.api.build_plan([protocol.encode_epoch(value) for value in values])
      spawn.assert_not_called()

  def test_raw_aggregate_limit_precedes_json_and_outer_plan_schema_is_strict(self):
    half = native.MAX_REQUEST_BYTES // 2 + 1
    padded = [raw + b' ' * (half - len(raw)) for raw in self.segments]
    with patch.object(joint.paired_shadow, '_read_json') as decode, self.assertRaises(ValueError):
      self.api.build_plan(padded)
    decode.assert_not_called()
    for payload in (bytearray(self.plan), b'[]', b'{"version":1,"version":1}', b'{"sequence":NaN}', b'\xff'):
      with self.subTest(kind=type(payload)), self.assertRaises(ValueError):
        self.api.decode_plan(payload)
    invalid = self.api.decode_plan(self.plan) | {'live_activation': True}
    with self.assertRaises(ValueError):
      self.api.run_plan(native.canonical(invalid), timeout_s=10.)

  def test_caller_mutations_cannot_rewrite_plan_or_expose_native_data(self):
    caller = list(self.segments)
    plan = self.api.build_plan(caller)
    caller.clear()
    decoded = self.api.decode_plan(plan)
    decoded['sequence']['epochs'].clear()
    result = self.api.run_plan(plan, timeout_s=15.)
    self.assertEqual(result['status'], self.api.PASS)
    self.assertEqual(len(result['segments']), 2)
    for forbidden in ('car_params_base64', '"frames"', '"samples"', str(joint.ROOT), '"snapshot"', 'session_id'):
      self.assertNotIn(forbidden, native.canonical(result).decode())
    self.assertEqual(plan, self.plan)

  def test_last_segment_source_binding_rejected_before_any_native_execution(self):
    invalid = self.api.decode_plan(self.plan)
    for epoch in invalid['sequence']['epochs']:
      name = next(iter(epoch['overlay']))
      epoch['overlay'][name] = '0' * 64
    with patch.object(self.api, 'JointSession') as spawn:
      result = self.api.run_plan(native.canonical(invalid), timeout_s=10.)
    spawn.assert_not_called()
    self.assert_failure(result, 'BINDING_REJECTED')

  def test_source_change_after_chunks_blocks_success_and_confirms_close(self):
    original, sessions = resets.JointSession, []
    verify = self.api._verify
    def create(**kwargs):
      session = original(**kwargs)
      sessions.append(session)
      return session
    def changed(plan):
      if sessions and sessions[0]._index >= 20:
        raise ValueError('PRIVATE_SENTINEL')
      return verify(plan)
    with patch.object(self.api, 'JointSession', side_effect=create), patch.object(self.api, '_verify', side_effect=changed):
      result = self.api.run_plan(self.plan, timeout_s=15.)
    self.assert_failure(result, 'BINDING_REJECTED')
    self.assertTrue(sessions[0].closed)
    self.assertFalse(_owned_group_running(sessions[0]._process.pid))

  def test_second_segment_native_error_produces_no_partial_comparison(self):
    segments = list(self.segments)
    broken = protocol.decode_json(segments[1])
    broken['joint']['pair']['frames']['longitudinal'][3]['a_target_mps2'] = 1e308
    segments[1] = protocol.encode_epoch(broken)
    with patch.object(self.api, 'JointSession', wraps=resets.JointSession) as spawn:
      result = self.api.run_plan(self.api.build_plan(segments), timeout_s=15.)
    self.assert_failure(result, 'SESSION_FAILED')
    self.assertEqual(spawn.call_count, 1)
    self.assertTrue(result['cleanup_confirmed'])

  def test_forged_finish_and_unconfirmed_close_never_return_success(self):
    finish, close = resets.JointSession.finish, resets.JointSession.close
    def forged(session, handle):
      result = finish(session, handle)
      result['promotable'] = True
      return result
    with patch.object(resets.JointSession, 'finish', forged):
      self.assert_failure(self.api.run_plan(self.plan, timeout_s=15.), 'INVALID_RESULT')
    def unconfirmed(session):
      return close(session) | {'cleanup_confirmed': False}
    with patch.object(resets.JointSession, 'close', unconfirmed):
      self.assert_failure(self.api.run_plan(self.plan, timeout_s=15.), 'CLEANUP_UNCONFIRMED')

  def test_whole_plan_budget_includes_checks_and_post_close(self):
    clock, original = [100.], resets.JointSession.advance
    budgets = []
    def consume(session, *args, **kwargs):
      budgets.append(session._timeout)
      result = original(session, *args, **kwargs)
      clock[0] += .4
      return result
    with patch.object(resets, 'monotonic', lambda: clock[0]), patch.object(resets.JointSession, 'advance', consume):
      result = self.api.run_plan(self.plan, timeout_s=2.)
    self.assert_failure(result, 'TIMEOUT')
    self.assertGreater(budgets[0], budgets[1])
    self.assertTrue(result['cleanup_confirmed'])

  def test_real_timeout_and_invalid_timeouts_do_not_create_authority(self):
    for value in (True, 0, -1., float('nan'), float('inf'), 61.):
      with self.subTest(value=value), self.assertRaises(ValueError):
        self.api.run_plan(self.plan, timeout_s=value)
    self.assert_failure(self.api.run_plan(self.plan, timeout_s=.001), 'TIMEOUT')

  def test_interruption_preserved_and_owned_child_reaped(self):
    sessions, original = [], resets.JointSession
    def create(**kwargs):
      session = original(**kwargs)
      sessions.append(session)
      return session
    interrupted = KeyboardInterrupt('CALLER_PRIVATE_TEXT')
    with patch.object(self.api, 'JointSession', side_effect=create), patch.object(original, 'advance', side_effect=interrupted):
      with self.assertRaises(KeyboardInterrupt) as caught:
        self.api.run_plan(self.plan, timeout_s=15.)
    self.assertIs(caught.exception, interrupted)
    self.assertTrue(sessions[0].closed)
    self.assertFalse(_owned_group_running(sessions[0]._process.pid))

  def test_existing_reset_sequence_and_changed_input_guard_remain_distinct(self):
    reset = resets.run_sequence(resets.build_sequence(self.segments), timeout_s=15.)
    continuous = self.api.run_plan(self.plan, timeout_s=15.)
    self.assertFalse(reset['state_carried_between_epochs'])
    self.assertTrue(continuous['state_carried_between_segments'])
    with resets.JointSession(timeout_s=10.) as session:
      session._sequence_deadline = resets.monotonic() + 10.
      handle = session.open_epoch(protocol.decode_json(self.segments[0]))
      session.abort(handle)
      with self.assertRaises(SessionError):
        session.open_epoch(protocol.decode_json(self.segments[1]))

  def test_identical_plans_have_identical_sanitized_reports(self):
    first = self.api.run_plan(self.plan, timeout_s=15.)
    second = self.api.run_plan(self.plan, timeout_s=15.)
    self.assertEqual(first['status'], self.api.PASS)
    self.assertEqual(native.canonical(first), native.canonical(second))


if __name__ == '__main__':
  unittest.main()
