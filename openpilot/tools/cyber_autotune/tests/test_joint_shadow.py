"""Complete epochs in an existing bounded queue; not droppable live chunks."""
from dataclasses import replace
import copy
import importlib
import importlib.util
import json
import threading
import time
import unittest
from unittest.mock import patch

from openpilot.tools.cyber_autotune import joint_continuity as joint, shadow
from openpilot.tools.cyber_autotune.native_protocol import canonical
from openpilot.tools.cyber_autotune.native_runner import _owned_group_running
from openpilot.tools.cyber_autotune.tests.test_joint_continuity import pair_fixture
from openpilot.tools.cyber_autotune.tests.test_shadow import wait_until


class TestJointShadow(unittest.TestCase):
  def setUp(self):
    name = 'openpilot.tools.cyber_autotune.joint_shadow'
    self.assertIsNotNone(importlib.util.find_spec(name), 'Joint IPC scheduler integration is not implemented')
    self.api = importlib.import_module(name)
    self.request = joint.build_request(pair_fixture(), [2, 3, 6])
    payload = joint.encode_request(self.request)
    reference = joint.execute_experiment(self.request)
    self.job = shadow.ShadowJob(0, payload, payload, canonical(reference))

  def test_two_queued_epochs_use_same_child_preserve_reference_and_close(self):
    original = copy.deepcopy(self.job)
    with self.api.JointShadowSession(self.job.candidate_request, timeout_s=10., deadline_s=20.) as queue:
      results, children = [], []
      for index in range(2):
        self.assertEqual(queue.try_submit(replace(self.job, sequence=index)), 'ACCEPTED')
        wait_until(lambda index=index: queue.snapshot()['processed'] == index + 1)
        result = json.loads(queue.poll())
        self.assertEqual(result['status'], 'COMPLETED_DIAGNOSTIC')
        self.assertEqual(result['scope'], self.api.SCOPE)
        self.assertEqual(result['sample_count'], 11)
        self.assertFalse(result['runtime_accepted'])
        self.assertFalse(result['promotable'])
        results.append(result['axes'])
        children.append(queue._session._process)
      self.assertIs(children[0], children[1])
      self.assertEqual(results[0], results[1])
      self.assertIsNone(children[0].poll())
    self.assertIsNotNone(children[0].poll())
    self.assertFalse(_owned_group_running(children[0].pid))
    self.assertTrue(queue.snapshot()['worker_cleanup_confirmed'])
    self.assertEqual(self.job, original)

  def test_invalid_reference_or_different_template_never_launches(self):
    for mode in ('reference', 'frames', 'sequence'):
      candidate = self.job
      if mode == 'reference':
        candidate = replace(candidate, active_response=b'{"PRIVATE_SENTINEL":true}')
      elif mode == 'frames':
        request = copy.deepcopy(self.request)
        for axis in ('lateral', 'longitudinal'):
          request['pair']['frames'][axis][0]['speed_mps'] += 1
        candidate = replace(candidate, candidate_request=joint.encode_request(request))
      else:
        candidate = replace(candidate, sequence=True)
      with self.subTest(mode=mode), self.api.JointShadowSession(self.job.candidate_request, timeout_s=2., deadline_s=3.) as queue:
        self.assertEqual(queue.try_submit(candidate), 'INVALID')
        self.assertIsNone(queue._session)
        self.assertFalse(queue.snapshot()['running'])

  def test_existing_backpressure_drops_whole_jobs_not_running_chunks(self):
    entered, release = threading.Event(), threading.Event()
    advance = self.api.JointSession.advance
    calls = []
    def pause(session, handle, *, start_index, count):
      calls.append((handle.epoch_id, start_index, count))
      entered.set()
      if not release.wait(5.):
        raise RuntimeError('TEST_BARRIER_EXPIRED')
      return advance(session, handle, start_index=start_index, count=count)
    with patch.object(self.api.JointSession, 'advance', pause):
      queue = self.api.JointShadowSession(self.job.candidate_request, timeout_s=10., deadline_s=20.)
      try:
        self.assertEqual(queue.try_submit(self.job), 'ACCEPTED')
        self.assertTrue(entered.wait(3.))
        self.assertEqual(queue.try_submit(replace(self.job, sequence=1)), 'ACCEPTED')
        self.assertEqual(queue.try_submit(replace(self.job, sequence=2)), 'BUSY')
        release.set()
        wait_until(lambda: queue.snapshot()['processed'] == 2)
        self.assertEqual(calls, [(1, 0, 2), (1, 2, 3), (1, 5, 6), (2, 0, 2), (2, 2, 3), (2, 5, 6)])
        self.assertEqual(queue.snapshot()['busy_drops'], 1)
        self.assertEqual(queue.snapshot()['result_drops'], 1)
      finally:
        release.set()
        queue.close()
    self.assertTrue(queue.snapshot()['worker_cleanup_confirmed'])

  def test_poll_expiry_removes_completed_comparison_and_no_authority(self):
    clock = [100.]
    with patch.object(shadow, 'monotonic', lambda: clock[0]):
      with self.api.JointShadowSession(self.job.candidate_request, timeout_s=10., deadline_s=20.) as queue:
        self.assertEqual(queue.try_submit(self.job), 'ACCEPTED')
        wait_until(lambda: queue.snapshot()['processed'] == 1)
        clock[0] = 121.
        result = json.loads(queue.poll())
        self.assertEqual(result['status'], 'EXPIRED')
        self.assertNotIn('axes', result)
        self.assertNotIn('completed_result_sha256', result)
        self.assertFalse(result['runtime_accepted'])

  def test_joint_fault_is_terminal_and_cleans_up_without_retry(self):
    with patch.object(self.api.JointSession, 'advance', side_effect=KeyboardInterrupt('PRIVATE_SENTINEL')):
      with self.api.JointShadowSession(self.job.candidate_request, timeout_s=10., deadline_s=20.) as queue:
        self.assertEqual(queue.try_submit(self.job), 'ACCEPTED')
        wait_until(lambda: queue.snapshot()['closed'])
        self.assertTrue(queue.snapshot()['terminal_fault'])
        self.assertEqual(queue.try_submit(replace(self.job, sequence=1)), 'CLOSED')
        self.assertIsNone(queue.poll())
      self.assertTrue(queue.snapshot()['worker_cleanup_confirmed'])
      self.assertNotIn('PRIVATE_SENTINEL', str(queue.snapshot()))
      self.assertIsNotNone(queue._session._process.poll())

  def test_complete_epoch_uses_one_budget_and_late_result_is_not_published(self):
    original = self.api.JointSession.advance
    budgets = []
    clock = [time.monotonic()]
    def consume(session, handle, *, start_index, count):
      budgets.append(session._timeout)
      result = original(session, handle, start_index=start_index, count=count)
      clock[0] += .4
      return result
    with patch.object(self.api, 'monotonic', lambda: clock[0]), patch.object(self.api.JointSession, 'advance', consume):
      with self.api.JointShadowSession(self.job.candidate_request, timeout_s=1., deadline_s=5.) as queue:
        self.assertEqual(queue.try_submit(self.job), 'ACCEPTED')
        wait_until(lambda: queue.snapshot()['closed'])
        self.assertTrue(queue.snapshot()['terminal_fault'])
        self.assertIsNone(queue.poll())
      self.assertTrue(queue.snapshot()['worker_cleanup_confirmed'])
    self.assertEqual(len(budgets), 3)
    self.assertGreater(budgets[0], budgets[1])
    self.assertGreater(budgets[1], budgets[2])


if __name__ == '__main__':
  unittest.main()
