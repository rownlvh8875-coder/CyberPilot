"""Reproductions of independent lifecycle-review findings, not relaxed limits."""
import io
import json
import subprocess
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from openpilot.tools.cyber_autotune import lateral_session as api, lateral_session_worker as worker
from openpilot.tools.cyber_autotune.native_runner import _owned_group_running


class TestSessionReview(unittest.TestCase):
  def observe_bootstrap(self, argv):
    events = []

    def arm(_which, seconds, *_):
      events.append(('timer', seconds))

    def bootstrap(*_, **__):
      events.append(('bootstrap', None))
      raise OSError('SYNTHETIC_BOOTSTRAP_STOP')

    with patch.object(worker.sys, 'argv', argv), patch.object(worker.sys, 'stdout', SimpleNamespace(buffer=io.BytesIO())), \
         patch.object(worker.signal, 'signal'), patch.object(worker.signal, 'setitimer', side_effect=arm), \
         patch.object(worker.tempfile, 'TemporaryDirectory', side_effect=bootstrap), \
         patch.object(time, 'monotonic_ns', return_value=1_000_000_000):
      self.assertEqual(worker.main(), 1)
    return events

  def test_wall_timer_is_armed_before_any_bootstrap_work(self):
    events = self.observe_bootstrap(['lateral_session_worker.py'])
    self.assertEqual(events[0][0], 'timer')
    self.assertGreater(events[0][1], 0)
    self.assertLessEqual(events[0][1], 60.)
    self.assertEqual(events[1][0], 'bootstrap')

  def test_launch_deadline_deducts_startup_elapsed_time(self):
    events = self.observe_bootstrap(['lateral_session_worker.py', '1100000000'])
    self.assertEqual(events[0][0], 'timer')
    self.assertAlmostEqual(events[0][1], .1)

  def test_parent_supplies_its_absolute_deadline_to_fixed_child(self):
    real = subprocess.Popen
    epoch = api.build_epoch()
    with patch.object(api.subprocess, 'Popen', wraps=real) as spawn, api.LateralSession(timeout_s=10.) as session:
      session.open_epoch(epoch)
      workers = [call.args[0] for call in spawn.call_args_list if 'lateral_session_worker.py' in str(call.args[0])]
      self.assertEqual(len(workers), 1)
      self.assertEqual(len(workers[0]), 4)
      self.assertEqual(int(workers[0][3]), int(session._expires * 1e9))

  def test_exceptional_exit_publicly_reports_unconfirmed_cleanup(self):
    epoch = api.build_epoch()
    session = api.LateralSession(timeout_s=10.)
    session.open_epoch(epoch)
    original = ValueError('CALLER_PRIVATE_TEXT')
    with patch.object(api, '_wait_owned_group_exit', side_effect=TimeoutError('PRIVATE_CLEANUP_PATH')):
      with self.assertRaises(ValueError) as caught:
        with session:
          raise original
    self.assertIs(caught.exception, original)
    notes = getattr(caught.exception, '__notes__', [])
    self.assertTrue(notes, 'Cleanup failure was hidden from the public exception')
    receipt = json.loads(notes[-1])
    self.assertIs(receipt['cleanup_confirmed'], False)
    self.assertNotIn('PRIVATE', notes[-1])
    self.assertIsNotNone(session._process.returncode)
    self.assertFalse(_owned_group_running(session._process.pid))

  def test_keyboard_interrupt_retains_type_and_public_cleanup_failure(self):
    with api.LateralSession(timeout_s=10.) as session:
      handle = session.open_epoch(api.build_epoch())
      original = KeyboardInterrupt('CALLER_PRIVATE_TEXT')
      with patch.object(session, '_exchange', side_effect=original), \
           patch.object(api, '_wait_owned_group_exit', side_effect=TimeoutError('PRIVATE_CLEANUP_PATH')):
        with self.assertRaises(KeyboardInterrupt) as caught:
          session.advance(handle, start_index=0, count=1)
      self.assertIs(caught.exception, original)
      notes = getattr(caught.exception, '__notes__', [])
      self.assertTrue(notes, 'Interrupted cleanup failure was not publicly visible')
      self.assertIs(json.loads(notes[-1])['cleanup_confirmed'], False)
      self.assertNotIn('PRIVATE', notes[-1])
      self.assertFalse(_owned_group_running(session._process.pid))


if __name__ == '__main__':
  unittest.main()
