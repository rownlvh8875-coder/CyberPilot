from dataclasses import replace
import json
import threading
import unittest
from unittest.mock import patch

from openpilot.tools.cyber_autotune.long_shadow import LongShadowSession
from openpilot.tools.cyber_autotune.shadow import ShadowSession
from openpilot.tools.cyber_autotune.tests.test_long_shadow import job as long_job
from openpilot.tools.cyber_autotune.tests.test_native_experiment import response as lateral_response
from openpilot.tools.cyber_autotune.tests.test_native_long_experiment import response as long_response
from openpilot.tools.cyber_autotune.tests.test_shadow import job as lateral_job, wait_until


class TestShadowAccounting(unittest.TestCase):
  def test_terminal_fault_counts_each_discarded_result_exactly_once(self):
    axes = ((ShadowSession, lateral_job, lateral_response, 'shadow'),
            (LongShadowSession, long_job, long_response, 'long_shadow'))
    # Literal expectations: buffered old result=1; previously polled/absent=0;
    # normal close already counted=1; overflowed new + buffered old results=2.
    for session_type, make_job, response, axis in axes:
      for mode, successful, expected_drops in (('buffered', 1, 1), ('polled', 1, 0), ('empty', 0, 0),
                                                ('closed_first', 1, 1), ('overflow', 2, 2)):
        with self.subTest(axis=axis, mode=mode):
          entered, release = threading.Event(), threading.Event()
          calls = []

          def worker(request, calls=calls, successful=successful, response=response, entered=entered, release=release, **_):
            calls.append(1)
            if len(calls) <= successful:
              return response(request, (0., 0.))
            entered.set()
            if not release.wait(5.):
              raise RuntimeError('test barrier failed')
            raise SystemExit('PRIVATE_TERMINAL_FAULT')

          case = make_job()
          with patch(f'openpilot.tools.cyber_autotune.{axis}.run_native', worker):
            session = session_type(case.candidate_request, timeout_s=1., deadline_s=20.)
            closer = threading.Thread(target=session.close)
            try:
              for sequence in range(successful):
                self.assertEqual(session.try_submit(replace(case, sequence=sequence)), 'ACCEPTED')
                wait_until(lambda session=session, sequence=sequence: session.snapshot()['processed'] == sequence + 1)
              if mode == 'polled':
                observed = json.loads(session.poll())
                self.assertEqual(observed['status'], 'COMPLETED_DIAGNOSTIC')
                self.assertFalse(observed['runtime_accepted'])
                self.assertFalse(observed['promotable'])
              self.assertEqual(session.try_submit(replace(case, sequence=successful)), 'ACCEPTED')
              self.assertTrue(entered.wait(2.))
              self.assertEqual(session.try_submit(replace(case, sequence=successful + 1)), 'ACCEPTED')
              if mode == 'closed_first':
                closer.start()
                wait_until(lambda session=session: session.snapshot()['closed'])
              release.set()
              wait_until(lambda session=session: session.snapshot()['terminal_fault'])
              state = session.snapshot()
              self.assertEqual(state['result_drops'], expected_drops)
              self.assertEqual(state['processed'], successful)
              self.assertEqual(state['accepted'], successful + 2)
              self.assertEqual(state['cancelled'], 2)
              self.assertTrue(state['closed'])
              self.assertFalse(state['running'])
              self.assertFalse(state['pending'])
              self.assertIsNone(session.poll())
              self.assertEqual(session.try_submit(replace(case, sequence=100)), 'CLOSED')
              session.close()
              session.close()
              self.assertEqual(session.snapshot(), state)
            finally:
              release.set()
              session.close()
              if closer.ident is not None:
                closer.join(3.)
                self.assertFalse(closer.is_alive())
