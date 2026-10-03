from dataclasses import replace
import json
import math
import threading
import unittest
from unittest.mock import patch

from openpilot.tools.cyber_autotune.long_shadow import LongShadowSession
from openpilot.tools.cyber_autotune.native_long_protocol import encode_request
from openpilot.tools.cyber_autotune.native_long_runner import run_native
from openpilot.tools.cyber_autotune.native_protocol import canonical, digest
from openpilot.tools.cyber_autotune.shadow import ShadowJob, ShadowSession
from openpilot.tools.cyber_autotune.tests.test_native_long_experiment import response
from openpilot.tools.cyber_autotune.tests.test_native_long_worker import fixture
from openpilot.tools.cyber_autotune.tests.test_shadow import job as lateral_job, wait_until


WORKER = 'openpilot.tools.cyber_autotune.long_shadow.run_native'
METRICS = ('requested_accel_rmse_difference_mps2', 'requested_accel_max_difference_mps2',
           'requested_accel_pid_bound_ratio', 'long_state_mismatch_ratio')


def job():
  request = fixture()
  request['frames'] = [dict(request['frames'][1], time_ns=i * 10_000_000) for i in range(2)]
  payload = encode_request(request)
  return ShadowJob(0, payload, payload, canonical(response(request, (0., 0.))))


class TestLongShadow(unittest.TestCase):
  def test_actual_native_repeat_comparison_has_no_transport_or_authority(self):
    request = fixture()
    payload = encode_request(request)
    active = canonical(run_native(request, timeout_s=10.))
    case = ShadowJob(0, payload, payload, active)
    with LongShadowSession(payload, timeout_s=10., deadline_s=20.) as session:
      self.assertEqual(session.try_submit(case), 'ACCEPTED')
      wait_until(lambda: session.snapshot()['processed'] == 1)
      observed = session.poll()
      result = json.loads(observed)
      self.assertEqual(result['scope'], 'OFFLINE_LONGITUDINAL_SHADOW_WINDOW_ONLY')
      self.assertEqual(result['status'], 'COMPLETED_DIAGNOSTIC')
      self.assertEqual(result['sample_count'], 11)
      self.assertEqual(result[METRICS[0]], 0.)
      self.assertEqual(result[METRICS[1]], 0.)
      self.assertEqual(result[METRICS[2]], 2 / 11)
      self.assertEqual(result[METRICS[3]], 0.)
      self.assertFalse(result['runtime_accepted'])
      self.assertFalse(result['promotable'])
      for private in (b'car_params_base64', b'"samples"', request['source']['root'].encode()):
        self.assertNotIn(private, observed)
      self.assertEqual(case.active_response, active)

  def test_wrong_axis_binding_ownership_and_sequence_reject_before_execution(self):
    case = job()
    owner = json.loads(case.active_request)
    owner['openpilot_longitudinal_control'] = False
    off_response = response(owner, (0., 0.))
    for row in off_response['samples']:
      row.update(long_active=False, state_before='off', state_after='off')
    off_response['ordered_trace_sha256'] = digest(canonical(off_response['samples']))
    changed = json.loads(case.active_request)
    changed['frames'][0]['accel_mps2'] = .1
    rebound = json.loads(case.candidate_request)
    rebound['source']['head'] = '0' * 40
    stale = json.loads(case.active_response)
    stale['request_sha256'] = '0' * 64
    cases = (None, lateral_job(), replace(case, sequence=True), replace(case, sequence=-1),
             replace(case, candidate_request=bytearray(case.candidate_request)),
             replace(case, candidate_request=encode_request(rebound)),
             replace(case, active_request=encode_request(changed), active_response=canonical(response(changed, (0., 0.)))),
             replace(case, active_request=encode_request(owner), active_response=canonical(off_response)),
             replace(case, active_response=canonical(stale)), replace(case, active_response=b'null'),
             replace(case, active_response=b'{"a":1,"a":2}'))
    with patch(WORKER, side_effect=AssertionError('invalid job executed')) as worker:
      with LongShadowSession(case.candidate_request, timeout_s=1., deadline_s=2.) as session:
        for invalid in cases:
          self.assertEqual(session.try_submit(invalid), 'INVALID')
        self.assertEqual(session.snapshot()['accepted'], 0)
        worker.assert_not_called()
    with self.assertRaises(ValueError):
      LongShadowSession(lateral_job().candidate_request, timeout_s=1., deadline_s=2.)
    with self.assertRaises(ValueError):
      ShadowSession(case.candidate_request, timeout_s=1., deadline_s=2.)

  def test_nonzero_diagnostics_are_requested_stage_not_brake_or_physical_jerk(self):
    def worker(request, **_):
      result = response(request, (-3.5, 2.))
      result['samples'][1]['state_after'] = 'stopping'
      result['ordered_trace_sha256'] = digest(canonical(result['samples']))
      return result
    case = job()
    with patch(WORKER, worker), LongShadowSession(case.candidate_request, timeout_s=1., deadline_s=5.) as session:
      self.assertEqual(session.try_submit(case), 'ACCEPTED')
      wait_until(lambda: session.snapshot()['processed'] == 1)
      result = json.loads(session.poll())
      self.assertAlmostEqual(result[METRICS[0]], math.sqrt((3.5 ** 2 + 2. ** 2) / 2))
      self.assertEqual(result[METRICS[1]], 3.5)
      self.assertEqual(result[METRICS[2]], 1.)
      self.assertEqual(result[METRICS[3]], .5)
      self.assertNotIn('braking_command', result)
      self.assertNotIn('actual_accel_mps2', result)
      self.assertEqual(session.try_submit(case), 'INVALID')

  def test_failure_timeout_and_malformed_responses_never_create_zero_metrics(self):
    case = job()
    for fault in ('TIMEOUT', 'exception', 'stale', 'malformed', 'authority'):
      def worker(request, fault=fault, **_):
        if fault == 'exception':
          raise RuntimeError('PRIVATE_ERROR')
        if fault == 'malformed':
          return []
        if fault == 'stale':
          return dict(response(request, (0., 0.)), request_sha256='0'*64)
        if fault == 'authority':
          return dict(response(request, (0., 0.)), promotable=True)
        return {'status': fault, 'request_sha256': digest(encode_request(request)), 'runtime_accepted': False, 'promotable': False}
      with self.subTest(fault=fault), patch(WORKER, worker):
        with LongShadowSession(case.candidate_request, timeout_s=1., deadline_s=5.) as session:
          self.assertEqual(session.try_submit(case), 'ACCEPTED')
          wait_until(lambda: session.snapshot()['processed'] == 1)
          payload = session.poll()
          result = json.loads(payload)
          self.assertIn(result['status'], ('TIMEOUT', 'EXECUTION_EXCEPTION', 'INVALID_RESPONSE'))
          self.assertTrue(all(metric not in result for metric in METRICS))
          self.assertNotIn(b'PRIVATE_ERROR', payload)

  def test_bounded_queues_and_expiry_before_and_after_execution(self):
    entered, release = threading.Event(), threading.Event()
    now, calls = [100.], []
    def worker(request, **_):
      calls.append(1)
      entered.set()
      if not release.wait(3.):
        raise RuntimeError('barrier failed')
      return response(request, (0., 0.))
    case = job()
    with patch('openpilot.tools.cyber_autotune.shadow.monotonic', lambda: now[0]), patch(WORKER, worker):
      session = LongShadowSession(case.candidate_request, timeout_s=1., deadline_s=2.)
      try:
        self.assertEqual(session.try_submit(case), 'ACCEPTED')
        self.assertTrue(entered.wait(2.))
        self.assertEqual(session.try_submit(replace(case, sequence=1)), 'ACCEPTED')
        self.assertEqual(session.try_submit(replace(case, sequence=2)), 'BUSY')
        self.assertIsNone(session.poll())
        now[0] = 103.
        release.set()
        wait_until(lambda: session.snapshot()['processed'] == 2)
        result = json.loads(session.poll())
        self.assertEqual(result['status'], 'EXPIRED')
        self.assertEqual(result['scope'], 'OFFLINE_LONGITUDINAL_SHADOW_WINDOW_ONLY')
        self.assertTrue(all(metric not in result for metric in METRICS))
        self.assertEqual(len(calls), 1)
        self.assertEqual(session.snapshot()['busy_drops'], 1)
        self.assertEqual(session.snapshot()['result_drops'], 1)
        self.assertEqual(session.snapshot()['expired'], 2)
      finally:
        release.set()
        session.close()

  def test_delayed_poll_strips_every_longitudinal_comparison(self):
    case, now = job(), [100.]
    with patch('openpilot.tools.cyber_autotune.shadow.monotonic', lambda: now[0]), \
         patch(WORKER, lambda request, **_: response(request, (2., -3.5))):
      with LongShadowSession(case.candidate_request, timeout_s=1., deadline_s=2.) as session:
        self.assertEqual(session.try_submit(case), 'ACCEPTED')
        wait_until(lambda: session.snapshot()['processed'] == 1)
        now[0] = 103.
        result = json.loads(session.poll())
        self.assertEqual(result['status'], 'EXPIRED')
        self.assertTrue(all(metric not in result for metric in METRICS))
        self.assertEqual(session.snapshot()['expired'], 1)

  def test_terminal_failure_and_closed_session_are_visible(self):
    case = job()
    with patch(WORKER, side_effect=SystemExit('PRIVATE_EXIT')):
      with LongShadowSession(case.candidate_request, timeout_s=1., deadline_s=2.) as session:
        self.assertEqual(session.try_submit(case), 'ACCEPTED')
        wait_until(lambda: session.snapshot()['closed'])
        self.assertTrue(session.snapshot()['terminal_fault'])
        self.assertIsNone(session.poll())
        self.assertEqual(session.try_submit(replace(case, sequence=1)), 'CLOSED')
      session.close()

  def test_invalid_deadline_and_timeout_rejected(self):
    case = job()
    for field in ('timeout_s', 'deadline_s'):
      for value in (True, 0, -1, math.inf, math.nan, 61):
        with self.subTest(field=field, value=value), self.assertRaises(ValueError):
          LongShadowSession(case.candidate_request, **{'timeout_s': 1., 'deadline_s': 2., field: value})


if __name__ == '__main__':
  unittest.main()
