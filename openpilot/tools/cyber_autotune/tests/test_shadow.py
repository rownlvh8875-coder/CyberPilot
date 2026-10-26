from dataclasses import replace
import json
import math
import threading
import time
import unittest
from unittest.mock import patch

from openpilot.tools.cyber_autotune.native_protocol import canonical, encode_request
from openpilot.tools.cyber_autotune.native_runner import run_native
from openpilot.tools.cyber_autotune.shadow import ShadowJob, ShadowSession
from openpilot.tools.cyber_autotune.tests.test_native_experiment import response
from openpilot.tools.cyber_autotune.tests.test_native_worker import fixture


def job(sequence=0):
  request = fixture()
  request['frames'] = request['frames'][:2]
  payload = encode_request(request)
  return ShadowJob(sequence, payload, payload, canonical(response(request, (0., 0.))))


def wait_until(predicate):
  deadline = time.monotonic() + 5.
  while not predicate():
    if time.monotonic() >= deadline:
      raise AssertionError('scheduler did not settle')
    time.sleep(.005)


class TestShadow(unittest.TestCase):
  def test_actual_native_observation_is_immutable_non_actuating_diagnostic(self):
    case = job()
    active = canonical(run_native(json.loads(case.active_request), timeout_s=10.))
    case = replace(case, active_response=active)
    with ShadowSession(case.candidate_request, timeout_s=10., deadline_s=20.) as session:
      self.assertEqual(session.try_submit(case), 'ACCEPTED')
      wait_until(lambda: session.snapshot()['processed'] == 1)
      payload = session.poll()
      self.assertIs(type(payload), bytes)
      result = json.loads(payload)
      self.assertEqual(result['status'], 'COMPLETED_DIAGNOSTIC')
      self.assertEqual(result['sequence'], 0)
      self.assertEqual(result['requested_torque_rmse_difference'], 0.)
      self.assertFalse(result['runtime_accepted'])
      self.assertFalse(result['promotable'])
      self.assertEqual(case.active_response, active)
      self.assertNotIn(b'car_params_base64', payload)
      self.assertNotIn(b'"samples"', payload)
      self.assertNotIn(json.loads(case.candidate_request)['source']['root'].encode(), payload)
      self.assertIsNone(session.poll())
    self.assertTrue(session.snapshot()['closed'])

  def test_admission_rejects_rebinding_stale_mutable_and_invalid_jobs(self):
    case = job()
    changed = json.loads(case.candidate_request)
    changed['source']['head'] = '0' * 40
    frame_changed = json.loads(case.active_request)
    frame_changed['frames'][0]['angle_deg'] = 1.
    stale = json.loads(case.active_response)
    stale['request_sha256'] = '0' * 64
    cases = [None, replace(case, sequence=True), replace(case, sequence=-1),
             replace(case, candidate_request=bytearray(case.candidate_request)),
             replace(case, candidate_request=encode_request(changed)),
             replace(case, active_request=encode_request(frame_changed)),
             replace(case, active_response=canonical(stale)), replace(case, active_response=b'{"a":1,"a":2}'),
             replace(case, active_response=b'null')]
    with ShadowSession(case.candidate_request, timeout_s=1., deadline_s=2.) as session:
      for invalid in cases:
        self.assertEqual(session.try_submit(invalid), 'INVALID')
      self.assertEqual(session.snapshot()['accepted'], 0)
      self.assertEqual(session.snapshot()['invalid'], len(cases))
      self.assertEqual(session.try_submit(case), 'ACCEPTED')
      self.assertEqual(session.try_submit(case), 'INVALID')
      self.assertEqual(session.try_submit(replace(case, sequence=-1)), 'INVALID')

  def test_invalid_policy_rejected_without_launch(self):
    case = job()
    for field in ('timeout_s', 'deadline_s'):
      for value in (True, 0., -1., math.inf, math.nan, 61., 10**400):
        policy = {'timeout_s': 1., 'deadline_s': 2., field: value}
        with self.subTest(field=field, value=value), self.assertRaises(ValueError):
          ShadowSession(case.candidate_request, **policy)

  def test_slow_worker_bounds_pending_queue_without_blocking_submission(self):
    entered, release = threading.Event(), threading.Event()

    def slow(request, **_):
      entered.set()
      if not release.wait(3.):
        raise RuntimeError('test barrier failed')
      return response(request, (.2, .4))

    case = job()
    with patch('openpilot.tools.cyber_autotune.shadow.run_native', slow):
      session = ShadowSession(case.candidate_request, timeout_s=1., deadline_s=5.)
      try:
        self.assertEqual(session.try_submit(case), 'ACCEPTED')
        self.assertTrue(entered.wait(2.))
        self.assertEqual(session.try_submit(replace(case, sequence=1)), 'ACCEPTED')
        self.assertEqual(session.try_submit(replace(case, sequence=2)), 'BUSY')
        self.assertIsNone(session.poll())
        self.assertEqual(session.snapshot()['busy_drops'], 1)
        release.set()
        wait_until(lambda: session.snapshot()['processed'] == 2)
        self.assertEqual(session.snapshot()['result_drops'], 1)
        result = json.loads(session.poll())
        self.assertEqual(result['sequence'], 0)
        self.assertAlmostEqual(result['requested_torque_rmse_difference'], math.sqrt(.1))
        self.assertAlmostEqual(result['requested_torque_max_difference'], .4)
        self.assertEqual(session.try_submit(replace(case, sequence=2)), 'ACCEPTED')
        wait_until(lambda: session.snapshot()['processed'] == 3)
        self.assertEqual(json.loads(session.poll())['sequence'], 2)
      finally:
        release.set()
        session.close()

  def test_timeout_exception_stale_and_malformed_have_no_zero_comparison(self):
    case = job()
    for fault in ('TIMEOUT', 'exception', 'stale', 'malformed'):
      def worker(request, fault=fault, **_):
        if fault == 'exception':
          raise RuntimeError('PRIVATE_FAULT')
        if fault == 'stale':
          return dict(response(request, (0., 0.)), request_sha256='0' * 64)
        if fault == 'malformed':
          return []
        return {'status': 'TIMEOUT', 'request_sha256': response(request, (0., 0.))['request_sha256'],
                'runtime_accepted': False, 'promotable': False}
      with self.subTest(fault=fault), patch('openpilot.tools.cyber_autotune.shadow.run_native', worker):
        with ShadowSession(case.candidate_request, timeout_s=1., deadline_s=5.) as session:
          self.assertEqual(session.try_submit(case), 'ACCEPTED')
          wait_until(lambda: session.snapshot()['processed'] == 1)
          payload = session.poll()
          result = json.loads(payload)
          self.assertIn(result['status'], ('TIMEOUT', 'EXECUTION_EXCEPTION', 'INVALID_RESPONSE'))
          self.assertNotIn('requested_torque_rmse_difference', result)
          self.assertNotIn(b'PRIVATE_FAULT', payload)

  def test_deadline_expires_queued_and_running_without_comparison(self):
    entered, release = threading.Event(), threading.Event()
    now = [100.]
    calls = []

    def worker(request, **_):
      calls.append(1)
      entered.set()
      release.wait(3.)
      return response(request, (0., 0.))

    case = job()
    with patch('openpilot.tools.cyber_autotune.shadow.monotonic', lambda: now[0]), \
         patch('openpilot.tools.cyber_autotune.shadow.run_native', worker):
      session = ShadowSession(case.candidate_request, timeout_s=1., deadline_s=2.)
      try:
        self.assertEqual(session.try_submit(case), 'ACCEPTED')
        self.assertTrue(entered.wait(2.))
        self.assertEqual(session.try_submit(replace(case, sequence=1)), 'ACCEPTED')
        now[0] = 103.
        release.set()
        wait_until(lambda: session.snapshot()['processed'] == 2)
        result = json.loads(session.poll())
        self.assertEqual(result['status'], 'EXPIRED')
        self.assertNotIn('requested_torque_rmse_difference', result)
        self.assertEqual(len(calls), 1)
        self.assertEqual(session.snapshot()['expired'], 2)
      finally:
        release.set()
        session.close()

  def test_waiting_result_expires_at_poll_and_does_not_leak_stale_comparison(self):
    now = [100.]
    case = job()
    with patch('openpilot.tools.cyber_autotune.shadow.monotonic', lambda: now[0]), \
         patch('openpilot.tools.cyber_autotune.shadow.run_native', lambda request, **_: response(request, (0., 0.))):
      with ShadowSession(case.candidate_request, timeout_s=1., deadline_s=2.) as session:
        self.assertEqual(session.try_submit(case), 'ACCEPTED')
        wait_until(lambda: session.snapshot()['processed'] == 1)
        now[0] = 103.
        result = json.loads(session.poll())
        self.assertEqual(result['status'], 'EXPIRED')
        self.assertNotIn('requested_torque_rmse_difference', result)
        self.assertEqual(session.snapshot()['expired'], 1)

  def test_close_discards_pending_and_late_output_and_is_idempotent(self):
    entered, release = threading.Event(), threading.Event()

    def worker(request, **_):
      entered.set()
      release.wait(3.)
      return response(request, (0., 0.))

    case = job()
    with patch('openpilot.tools.cyber_autotune.shadow.run_native', worker):
      session = ShadowSession(case.candidate_request, timeout_s=1., deadline_s=5.)
      closer = threading.Thread(target=session.close)
      try:
        self.assertEqual(session.try_submit(case), 'ACCEPTED')
        self.assertTrue(entered.wait(2.))
        self.assertEqual(session.try_submit(replace(case, sequence=1)), 'ACCEPTED')
        closer.start()
        wait_until(lambda: session.snapshot()['closed'])
        self.assertEqual(session.try_submit(replace(case, sequence=2)), 'CLOSED')
        self.assertTrue(closer.is_alive())
        release.set()
        closer.join(3.)
        self.assertFalse(closer.is_alive())
        self.assertIsNone(session.poll())
        self.assertEqual(session.snapshot()['cancelled'], 2)
        session.close()
      finally:
        release.set()
        session.close()
        if closer.ident is not None:
          closer.join(3.)

  def test_unexpected_worker_base_exception_closes_session_visibly(self):
    case = job()
    with patch('openpilot.tools.cyber_autotune.shadow.run_native', side_effect=SystemExit('PRIVATE_EXIT')):
      with ShadowSession(case.candidate_request, timeout_s=1., deadline_s=5.) as session:
        self.assertEqual(session.try_submit(case), 'ACCEPTED')
        wait_until(lambda: session.snapshot()['closed'])
        self.assertTrue(session.snapshot()['terminal_fault'])
        self.assertIsNone(session.poll())
        self.assertEqual(session.try_submit(replace(case, sequence=1)), 'CLOSED')


if __name__ == '__main__':
  unittest.main()
