"""Offline worker noninterference, NOT real-time controlsd scheduling evidence."""
from contextlib import nullcontext
from dataclasses import replace
import json
import unittest
from unittest.mock import patch

from openpilot.tools.cyber_autotune.native_protocol import canonical, digest
from openpilot.tools.cyber_autotune.shadow import ShadowSession
from openpilot.tools.cyber_autotune.long_shadow import LongShadowSession
from openpilot.tools.cyber_autotune.native_runner import run_native as run_lateral
from openpilot.tools.cyber_autotune.native_long_runner import run_native as run_longitudinal
from openpilot.tools.cyber_autotune.tests.test_shadow import job as lateral_job, wait_until
from openpilot.tools.cyber_autotune.tests.test_long_shadow import job as longitudinal_job


class TestShadowNoninterference(unittest.TestCase):
  def test_shadow_on_fault_and_restart_leave_active_bytes_count_and_inputs_identical(self):
    axes = ((lateral_job, ShadowSession, run_lateral, 'shadow'),
            (longitudinal_job, LongShadowSession, run_longitudinal, 'long_shadow'))
    for make_job, session_type, run_active, module in axes:
      job = make_job()
      request = json.loads(job.active_request)
      input_sha = digest(canonical(request))
      baseline = run_active(request, timeout_s=10.)
      self.assertEqual(baseline['status'], 'COMPLETED')
      baseline_bytes = canonical(baseline)
      job = replace(job, active_response=baseline_bytes)
      for fault in (False, True, False):  # final iteration is a fresh recovered session
        with self.subTest(axis=module, fault=fault):
          target = 'openpilot.tools.cyber_autotune.' + module + '.run_native'
          context = patch(target, side_effect=RuntimeError('INJECTED_SHADOW_FAILURE')) if fault else nullcontext()
          with context, session_type(job.candidate_request, timeout_s=10., deadline_s=20.) as session:
            self.assertEqual(session.try_submit(job), 'ACCEPTED')
            # A distinct active worker is never fed shadow output or mutable state.
            active = run_active(request, timeout_s=10.)
            wait_until(lambda: session.snapshot()['processed'] == 1)
            observed = json.loads(session.poll())
            self.assertEqual(observed['status'], 'EXECUTION_EXCEPTION' if fault else 'COMPLETED_DIAGNOSTIC')
            self.assertEqual(canonical(active), baseline_bytes)
            self.assertEqual(len(active['samples']), len(request['frames']))
            self.assertEqual(digest(canonical(request)), input_sha)
            self.assertEqual(job.active_response, baseline_bytes)
            self.assertFalse(observed['runtime_accepted'])
            self.assertFalse(observed['promotable'])
          self.assertTrue(session.snapshot()['closed'])
          self.assertFalse(session.snapshot()['running'])
