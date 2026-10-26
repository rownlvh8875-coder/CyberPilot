"""Structural same-window pairing, not continuous or vehicle Shadow qualification."""
from dataclasses import replace
import copy
import importlib
import importlib.util
import json
import threading
import unittest
from unittest.mock import patch

from openpilot.tools.cyber_autotune import shadow
from openpilot.tools.cyber_autotune import native_protocol as lat, native_long_protocol as lng
from openpilot.tools.cyber_autotune.native_runner import run_native as run_lat
from openpilot.tools.cyber_autotune.native_long_runner import run_native as run_long
from openpilot.tools.cyber_autotune.tests.test_native_worker import fixture as lateral_fixture
from openpilot.tools.cyber_autotune.tests.test_native_long_worker import fixture as long_fixture
from openpilot.tools.cyber_autotune.tests.test_native_experiment import response as lateral_response
from openpilot.tools.cyber_autotune.tests.test_native_long_experiment import response as long_response
from openpilot.tools.cyber_autotune.tests.test_shadow import wait_until


LAT_WORKER = 'openpilot.tools.cyber_autotune.shadow.run_native'
LONG_WORKER = 'openpilot.tools.cyber_autotune.long_shadow.run_native'


def requests(full=False):
  lateral, longitudinal = lateral_fixture(), long_fixture()
  if not full:
    longitudinal['frames'] = [dict(longitudinal['frames'][1], time_ns=i * lat.TIMESTEP_NS) for i in range(2)]
  for field in ('car_params_base64', 'car_params_sha256'):
    lateral[field] = longitudinal[field]
  seed = lateral['frames'][0]
  lateral['frames'] = [dict(seed, time_ns=row['time_ns'], speed_mps=row['speed_mps'], accel_mps2=row['accel_mps2'],
                            desired_curvature_1pm=.001 if index % 2 else -.001)
                       for index, row in enumerate(longitudinal['frames'])]
  return lateral, longitudinal


def job(api, full=False):
  lateral, longitudinal = requests(full)
  payload = api.pack_requests(lat.encode_request(lateral), lng.encode_request(longitudinal))
  if full:
    first, second = run_lat(lateral, timeout_s=10.), run_long(longitudinal, timeout_s=10.)
  else:
    first, second = lateral_response(lateral, (0., 0.)), long_response(longitudinal, (0., 0.))
  active = api.pack_responses(payload, lat.canonical(first), lat.canonical(second))
  return shadow.ShadowJob(0, payload, payload, active)


def fake_workers():
  return (patch(LAT_WORKER, lambda request, **_: lateral_response(request, (.2, .4))),
          patch(LONG_WORKER, lambda request, **_: long_response(request, (-3.5, 2.))))


class TestPairedShadow(unittest.TestCase):
  def setUp(self):
    name = 'openpilot.tools.cyber_autotune.paired_shadow'
    self.assertIsNotNone(importlib.util.find_spec(name), 'Two-axis same-window scheduler bridge is not implemented')
    self.api = importlib.import_module(name)
    self.case = job(self.api)

  def collect(self, session, case=None):
    self.assertEqual(session.try_submit(self.case if case is None else case), 'ACCEPTED')
    wait_until(lambda: session.snapshot()['processed'] == 1)
    return json.loads(session.poll())

  def test_real_native_pair_matches_separate_axes_and_preserves_observations(self):
    case = job(self.api, full=True)
    before = copy.deepcopy(case)
    expected_lat, expected_long = requests(full=True)
    runs = []
    for _ in range(2):
      with self.api.PairedShadowSession(case.candidate_request, timeout_s=15., deadline_s=30.) as session:
        result = self.collect(session, case)
      self.assertEqual(result['status'], 'COMPLETED_DIAGNOSTIC')
      self.assertEqual(result['scope'], self.api.SCOPE)
      self.assertEqual(result['input_alignment'], 'STRUCTURAL_WINDOW_MATCH_ONLY')
      self.assertEqual(result['axes']['lateral']['sample_count'], 11)
      self.assertEqual(result['axes']['longitudinal']['sample_count'], 11)
      self.assertEqual(result['axes']['lateral']['requested_torque_max_difference'], 0.)
      self.assertEqual(result['axes']['longitudinal']['requested_accel_max_difference_mps2'], 0.)
      self.assertEqual(result['axes']['longitudinal']['requested_accel_pid_bound_ratio'], 2 / 11)
      self.assertFalse(result['runtime_accepted'])
      self.assertFalse(result['promotable'])
      runs.append(result['axes'])
    self.assertEqual(runs[0], runs[1])
    self.assertEqual(case, before)
    active = json.loads(case.active_response)
    self.assertEqual(active['lateral'], run_lat(expected_lat, timeout_s=10.))
    self.assertEqual(active['longitudinal'], run_long(expected_long, timeout_s=10.))

  def test_nonzero_metrics_remain_axis_specific_and_public(self):
    first, second = fake_workers()
    with first, second, self.api.PairedShadowSession(self.case.candidate_request, timeout_s=2., deadline_s=5.) as session:
      result = self.collect(session)
    self.assertEqual(result['axes']['lateral']['requested_torque_max_difference'], .4)
    self.assertEqual(result['axes']['longitudinal']['requested_accel_max_difference_mps2'], 3.5)
    encoded = lat.canonical(result)
    for token in (b'car_params_base64', b'"samples"', requests()[0]['source']['root'].encode(), b'joint_actuator_command'):
      self.assertNotIn(token, encoded)

  def test_cross_axis_common_frame_mismatches_never_execute(self):
    for field, value in (('time_ns', 1), ('speed_mps', 21.), ('accel_mps2', .5)):
      envelope = json.loads(self.case.candidate_request)
      envelope['frames']['longitudinal'][0][field] = value
      with self.subTest(field=field), patch(LAT_WORKER) as left, patch(LONG_WORKER) as right:
        with self.api.PairedShadowSession(self.case.candidate_request, timeout_s=1., deadline_s=2.) as session:
          self.assertEqual(session.try_submit(replace(self.case, candidate_request=lat.canonical(envelope))), 'INVALID')
          left.assert_not_called()
          right.assert_not_called()

  def test_equal_clock_offsets_and_frame_counts_are_not_silently_joined(self):
    for mode in ('shift', 'drop', 'reverse', 'duplicate'):
      envelope = json.loads(self.case.candidate_request)
      frames = envelope['frames']['longitudinal']
      if mode == 'shift':
        for frame in frames:
          frame['time_ns'] += lat.TIMESTEP_NS
      elif mode == 'drop':
        frames.pop()
      elif mode == 'reverse':
        frames.reverse()
      else:
        frames[1]['time_ns'] = frames[0]['time_ns']
      with self.subTest(mode=mode), self.assertRaises(ValueError):
        self.api.decode_request(lat.canonical(envelope))

  def test_source_cp_shared_file_and_axis_identity_must_match(self):
    cases = []
    for key, value in (('root', '/different-source'), ('head', '0' * 40), ('opendbc_head', '0' * 40)):
      envelope = json.loads(self.case.candidate_request)
      envelope['longitudinal']['source'][key] = value
      cases.append(envelope)
    envelope = json.loads(self.case.candidate_request)
    envelope['longitudinal']['source']['files']['openpilot/common/pid.py'] = '0' * 64
    cases.append(envelope)
    other = lateral_fixture()
    envelope = json.loads(self.case.candidate_request)
    for field in ('car_params_base64', 'car_params_sha256'):
      envelope['lateral'][field] = other[field]
    cases.append(envelope)
    envelope = json.loads(self.case.candidate_request)
    envelope['lateral'], envelope['longitudinal'] = envelope['longitudinal'], envelope['lateral']
    cases.append(envelope)
    for index, envelope in enumerate(cases):
      with self.subTest(case=index), self.assertRaises(ValueError):
        self.api.decode_request(lat.canonical(envelope))

  def test_invalid_other_axis_active_response_rejects_entire_job_before_execution(self):
    for value in (None, {'runtime_accepted': True}, [], 'PRIVATE_SENTINEL'):
      response = json.loads(self.case.active_response)
      response['longitudinal'] = value
      with self.subTest(value=type(value)), patch(LAT_WORKER) as left, patch(LONG_WORKER) as right:
        with self.api.PairedShadowSession(self.case.candidate_request, timeout_s=1., deadline_s=2.) as session:
          self.assertEqual(session.try_submit(replace(self.case, active_response=lat.canonical(response))), 'INVALID')
        left.assert_not_called()
        right.assert_not_called()

  def test_malformed_envelopes_and_mutable_bytes_are_rejected(self):
    for payload in (b'null', b'[]', b'{"version":1,"version":1}', b'{"a":NaN}', b'\xff', bytearray(self.case.candidate_request)):
      with self.subTest(payload=type(payload)), self.assertRaises(ValueError):
        self.api.decode_request(payload)
    envelope = json.loads(self.case.candidate_request)
    for change in ({'version': True}, {'unqualified_extra': {}}, {'frames': []}):
      with self.assertRaises(ValueError):
        self.api.decode_request(lat.canonical(envelope | change))
    with self.assertRaises(ValueError):
      self.api.decode_request(b' ' * (lat.MAX_REQUEST_BYTES + 1))

  def test_first_axis_failure_skips_second_without_partial_metrics(self):
    with patch(LAT_WORKER, side_effect=RuntimeError('PRIVATE_SENTINEL')), patch(LONG_WORKER) as second:
      with self.api.PairedShadowSession(self.case.candidate_request, timeout_s=1., deadline_s=3.) as session:
        result = self.collect(session)
    self.assertEqual(result['status'], 'PAIR_INCOMPLETE')
    self.assertEqual(result['axis_status'], {'lateral': 'EXECUTION_EXCEPTION', 'longitudinal': 'NOT_RUN'})
    self.assertNotIn('axes', result)
    self.assertNotIn(b'PRIVATE_SENTINEL', lat.canonical(result))
    second.assert_not_called()

  def test_second_axis_failure_removes_both_comparisons(self):
    first, _ = fake_workers()
    with first, patch(LONG_WORKER, side_effect=RuntimeError('PRIVATE_SENTINEL')):
      with self.api.PairedShadowSession(self.case.candidate_request, timeout_s=2., deadline_s=3.) as session:
        result = self.collect(session)
    self.assertEqual(result['status'], 'PAIR_INCOMPLETE')
    self.assertEqual(result['axis_status']['lateral'], 'COMPLETED_DIAGNOSTIC')
    self.assertNotIn('axes', result)
    self.assertNotIn(b'requested_torque_max_difference', lat.canonical(result))

  def test_second_axis_gets_only_remaining_shared_budget(self):
    now, budgets = [100.], []
    def first(request, *, timeout_s):
      budgets.append(timeout_s)
      now[0] += .4
      return lateral_response(request, (0., 0.))
    def second(request, *, timeout_s):
      budgets.append(timeout_s)
      now[0] += .3
      return long_response(request, (0., 0.))
    with patch.object(self.api, 'monotonic', lambda: now[0]), patch(LAT_WORKER, first), patch(LONG_WORKER, second):
      result = self.api._diagnostic(self.case, 1.)
    self.assertEqual(result['status'], 'COMPLETED_DIAGNOSTIC')
    self.assertAlmostEqual(budgets[0], 1.)
    self.assertAlmostEqual(budgets[1], .6)

  def test_budget_exhaustion_and_late_success_never_form_completed_pair(self):
    for expire_in in ('lateral', 'longitudinal'):
      now = [100.]
      def first(request, now=now, expire_in=expire_in, **_):
        now[0] += 2. if expire_in == 'lateral' else .1
        return lateral_response(request, (0., 0.))
      def second(request, now=now, **_):
        now[0] += 2.
        return long_response(request, (0., 0.))
      with self.subTest(axis=expire_in), patch.object(self.api, 'monotonic', lambda now=now: now[0]), \
           patch(LAT_WORKER, first), patch(LONG_WORKER, side_effect=second) as worker:
        result = self.api._diagnostic(self.case, 1.)
      self.assertEqual(result['status'], 'TIMEOUT')
      self.assertNotIn('axes', result)
      self.assertEqual(worker.call_count, int(expire_in == 'longitudinal'))

  def test_forged_per_axis_diagnostic_is_not_trusted(self):
    prepared = self.api._prepare(self.case, shadow._identity(self.api.decode_request(self.case.candidate_request)))
    first, second = fake_workers()
    with first, second:
      good = self.api._diagnostic(prepared, 2.)['axes']['lateral']
    for change in ({'promotable': True}, {'sequence': True}, {'active_trace_sha256': '0' * 64},
                   {'candidate_request_sha256': '0' * 64}, {'sample_count': 99},
                   {'requested_torque_max_difference': float('nan')}, {'PRIVATE_SENTINEL': 'raw'}):
      with self.subTest(change=list(change)), patch.object(shadow, '_diagnostic', return_value=good | change), patch(LONG_WORKER) as worker:
        result = self.api._diagnostic(prepared, 2.)
        self.assertEqual(result['status'], 'PAIR_INCOMPLETE')
        self.assertEqual(result['axis_status']['lateral'], 'INVALID_RESPONSE')
        self.assertNotIn('axes', result)
        self.assertNotIn(b'PRIVATE_SENTINEL', lat.canonical(result))
        worker.assert_not_called()

  def test_delayed_poll_strips_both_axes_metrics(self):
    now = [100.]
    first, second = fake_workers()
    with first, second, patch.object(shadow, 'monotonic', lambda: now[0]):
      with self.api.PairedShadowSession(self.case.candidate_request, timeout_s=1., deadline_s=2.) as session:
        self.assertEqual(session.try_submit(self.case), 'ACCEPTED')
        wait_until(lambda: session.snapshot()['processed'] == 1)
        now[0] = 103.
        result = json.loads(session.poll())
        self.assertEqual(result['status'], 'EXPIRED')
        self.assertNotIn('axes', result)
        self.assertEqual(session.snapshot()['expired'], 1)

  def test_existing_queue_bounds_and_preexecution_expiry_are_reused(self):
    entered, release, now = threading.Event(), threading.Event(), [100.]
    def first(request, **_):
      entered.set()
      if not release.wait(3.):
        raise RuntimeError('test barrier failed')
      return lateral_response(request, (0., 0.))
    with patch.object(shadow, 'monotonic', lambda: now[0]), patch(LAT_WORKER, first), \
         patch(LONG_WORKER, lambda request, **_: long_response(request, (0., 0.))):
      session = self.api.PairedShadowSession(self.case.candidate_request, timeout_s=2., deadline_s=2.)
      try:
        self.assertEqual(session.try_submit(self.case), 'ACCEPTED')
        self.assertTrue(entered.wait(2.))
        self.assertEqual(session.try_submit(replace(self.case, sequence=1)), 'ACCEPTED')
        self.assertEqual(session.try_submit(replace(self.case, sequence=2)), 'BUSY')
        now[0] = 103.
        release.set()
        wait_until(lambda: session.snapshot()['processed'] == 2)
        result = json.loads(session.poll())
        self.assertEqual(result['status'], 'EXPIRED')
        self.assertNotIn('axes', result)
        self.assertEqual(session.snapshot()['busy_drops'], 1)
        self.assertEqual(session.snapshot()['result_drops'], 1)
      finally:
        release.set()
        session.close()

  def test_terminal_interrupt_and_new_session_do_not_change_active_data(self):
    saved = copy.deepcopy(self.case)
    with patch(LAT_WORKER, side_effect=KeyboardInterrupt):
      with self.api.PairedShadowSession(self.case.candidate_request, timeout_s=1., deadline_s=2.) as session:
        self.assertEqual(session.try_submit(self.case), 'ACCEPTED')
        wait_until(lambda: session.snapshot()['closed'])
        self.assertTrue(session.snapshot()['terminal_fault'])
        self.assertIsNone(session.poll())
        self.assertEqual(session.try_submit(replace(self.case, sequence=1)), 'CLOSED')
    self.assertEqual(self.case, saved)
    first, second = fake_workers()
    with first, second, self.api.PairedShadowSession(self.case.candidate_request, timeout_s=2., deadline_s=3.) as session:
      self.assertEqual(self.collect(session)['status'], 'COMPLETED_DIAGNOSTIC')
      self.assertEqual(session.try_submit(self.case), 'INVALID')
    self.assertEqual(self.case, saved)

  def test_candidate_nonframe_change_and_invalid_policies_fail_closed(self):
    envelope = json.loads(self.case.candidate_request)
    for axis in ('lateral', 'longitudinal'):
      envelope[axis]['source']['head'] = '0' * 40
    with self.api.PairedShadowSession(self.case.candidate_request, timeout_s=1., deadline_s=2.) as session:
      self.assertEqual(session.try_submit(replace(self.case, candidate_request=lat.canonical(envelope))), 'INVALID')
    for field in ('timeout_s', 'deadline_s'):
      for value in (True, 0., -1., 61., float('nan'), float('inf')):
        with self.subTest(field=field, value=value), self.assertRaises(ValueError):
          self.api.PairedShadowSession(self.case.candidate_request, **{'timeout_s': 1., 'deadline_s': 2., field: value})


if __name__ == '__main__':
  unittest.main()
