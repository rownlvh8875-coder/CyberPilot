import copy
import json
import os
import unittest
from unittest.mock import patch

from openpilot.tools.cyber_autotune import native_long_runner as runner
from openpilot.tools.cyber_autotune.native_protocol import canonical, digest
from openpilot.tools.cyber_autotune.native_runner import ProcessOutcome, _run_process
from openpilot.tools.cyber_autotune.tests.test_native_long_worker import fixture


class TestNativeLongRunner(unittest.TestCase):
  def test_invalid_timeouts_and_request_never_launch(self):
    for timeout in (0, -1, True, 61, float('nan')):
      with self.subTest(timeout=timeout), self.assertRaises(ValueError):
        runner.run_native(fixture(), timeout_s=timeout)
    with patch.object(runner, '_run_process', side_effect=AssertionError('must not launch')):
      with self.assertRaises(ValueError):
        runner.run_native(dict(fixture(), accel_limits=(-4, 4)), timeout_s=1)

  def test_real_timeout_reaps_only_owned_child_and_next_request_succeeds(self):
    observed = []
    def launch(*args):
      outcome = _run_process(*args)
      observed.append(outcome)
      return outcome
    with patch.object(runner, '_run_process', side_effect=launch):
      result = runner.run_native(fixture(), timeout_s=.000001)
    self.assertEqual(result['status'], 'TIMEOUT')
    self.assertFalse(result['runtime_accepted'])
    with self.assertRaises(ProcessLookupError):
      os.kill(observed[0].pid, 0)
    self.assertEqual(runner.run_native(fixture(), timeout_s=10)['status'], 'COMPLETED')

  def test_response_binding_state_and_native_envelope_are_validated(self):
    request = fixture()
    good = runner.run_native(request, timeout_s=10)
    self.assertEqual(good['status'], 'COMPLETED')
    runner.validate_response(request, good)
    mutations = (
      lambda r: r.update(runtime_accepted=True), lambda r: r.update(promotable=True),
      lambda r: r.update(request_sha256='0' * 64), lambda r: r.update(source_head='0' * 40),
      lambda r: r.update(car_params_sha256='0' * 64), lambda r: r.update(samples=[]),
      lambda r: r['samples'][0].update(requested_accel_mps2=.1),
      lambda r: r['samples'][1].update(requested_accel_mps2=2.1),
      lambda r: r['samples'][1].update(requested_accel_mps2=float('inf')),
      lambda r: r['samples'][1].update(requested_accel_mps2=True),
      lambda r: r['samples'][1].update(time_ns=0), lambda r: r['samples'][1].update(long_active=False),
      lambda r: r['samples'][1].update(state_before='pid'),
      lambda r: r['samples'][1].update(state_after='off'),
      lambda r: r['samples'][1].update(applied_accel_mps2=1.),
    )
    for index, mutate in enumerate(mutations):
      changed = copy.deepcopy(good)
      mutate(changed)
      if index != 8:
        changed['ordered_trace_sha256'] = digest(canonical(changed['samples']))
      with self.subTest(index=index), self.assertRaises(ValueError):
        runner.validate_response(request, changed)
    changed = copy.deepcopy(good)
    changed['ordered_trace_sha256'] = '0' * 64
    with self.assertRaises(ValueError):
      runner.validate_response(request, changed)

  def test_malformed_process_results_do_not_escape_as_completed(self):
    request = fixture()
    good = runner.run_native(request, timeout_s=10)
    payload = canonical(good)
    for outcome, expected in (
      (ProcessOutcome('EXITED', 1, b'private diagnostic', 1), 'WORKER_FAILED'),
      (ProcessOutcome('EXITED', 0, b'{}', 1), 'INVALID_RESPONSE'),
      (ProcessOutcome('EXITED', 0, b' ' * (4 * 1024 * 1024 + 1), 1), 'INVALID_RESPONSE'),
      (ProcessOutcome('EXITED', 0, payload.replace(b'"promotable":false', b'"promotable":false,"promotable":false'), 1),
       'INVALID_RESPONSE'),
    ):
      with self.subTest(expected=expected), patch.object(runner, '_run_process', return_value=outcome):
        result = runner.run_native(request, timeout_s=1)
        self.assertEqual(result['status'], expected)
        self.assertNotIn('samples', result)
        self.assertNotIn('private', json.dumps(result))
        self.assertFalse(result['runtime_accepted'])


if __name__ == '__main__':
  unittest.main()
