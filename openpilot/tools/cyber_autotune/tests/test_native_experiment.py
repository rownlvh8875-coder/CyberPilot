import copy
import hashlib
import json
import math
import unittest
from unittest.mock import patch

from openpilot.tools.cyber_autotune.native_experiment import NativeArm, NativeExperiment, run_experiment
from openpilot.tools.cyber_autotune.native_protocol import encode_request
from openpilot.tools.cyber_autotune.tests.test_native_worker import fixture


ARMS = ('UPSTREAM_BASELINE', 'CYBER_CURRENT', 'CYBER_CANDIDATE')


def experiment():
  request = fixture()
  request['frames'] = request['frames'][:2]
  payload = encode_request(request)
  return NativeExperiment(tuple(NativeArm(arm, payload) for arm in ARMS), ('straight',))


def response(request, values):
  rows = [{'time_ns': frame['time_ns'], 'requested_torque': value, 'estimated_curvature_1pm': 0.}
          for frame, value in zip(request['frames'], values, strict=True)]
  trace = json.dumps(rows, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
  return {'status': 'COMPLETED', 'scope': 'OFFLINE_NATIVE_REQUESTED_TORQUE',
          'request_sha256': hashlib.sha256(encode_request(request)).hexdigest(),
          'source_head': request['source']['head'], 'opendbc_head': request['source']['opendbc_head'],
          'car_params_sha256': request['car_params_sha256'], 'samples': rows,
          'ordered_trace_sha256': hashlib.sha256(trace).hexdigest(), 'runtime_accepted': False, 'promotable': False}


class TestNativeExperiment(unittest.TestCase):
  def test_actual_six_native_runs_repeat_without_qualification(self):
    result = run_experiment(experiment(), timeout_s=10.)
    self.assertEqual(result['status'], 'REVALIDATION_REQUIRED')
    self.assertTrue(result['repeatable'])
    self.assertEqual(len(result['runs']), 6)
    self.assertEqual([row['arm'] for row in result['runs']], [arm for arm in ARMS for _ in range(2)])
    self.assertTrue(all(row['status'] == 'COMPLETED' and row['sample_count'] == 2 for row in result['runs']))
    self.assertEqual(len(result['comparisons']), 3)
    self.assertFalse(result['runtime_accepted'])
    self.assertFalse(result['promotable'])
    self.assertIn('METRIC_V2_PRODUCER_PENDING', result['issues'])
    self.assertIn('REVALIDATION_REQUIRED', result['markdown'])

  def test_bad_matrix_tags_and_frame_mismatch_reject_before_execution(self):
    valid = experiment()
    bad_values = [None, NativeExperiment(valid.arms[:2], valid.scenario_tags),
                  NativeExperiment((valid.arms[0],) * 3, valid.scenario_tags),
                  NativeExperiment(valid.arms, ('private-path',)), NativeExperiment(valid.arms, ()),
                  NativeExperiment(valid.arms, ('straight', 'straight')),
                  NativeExperiment(list(valid.arms), valid.scenario_tags)]
    changed = json.loads(valid.arms[0].request)
    changed['frames'][0]['angle_deg'] = 1.
    bad_values.append(NativeExperiment((*valid.arms[:2], NativeArm(ARMS[2], encode_request(changed))), ('straight',)))
    for invalid in bad_values:
      with self.subTest(invalid=type(invalid)), self.assertRaises(ValueError):
        run_experiment(invalid, timeout_s=10.)
    for timeout in (0, True, float('nan'), 61):
      with self.subTest(timeout=timeout), self.assertRaises(ValueError):
        run_experiment(valid, timeout_s=timeout)

  def test_hand_derived_command_diagnostics_and_privacy(self):
    case = experiment()
    calls = 0

    def worker(request, *, timeout_s):
      nonlocal calls
      values = ((0., 0.), (.1, .1), (.2, .4))[calls // 2]
      calls += 1
      return response(request, values)

    with patch('openpilot.tools.cyber_autotune.native_experiment.run_native', worker):
      result = run_experiment(case, timeout_s=10.)
    comparisons = {(row['reference'], row['arm']): row for row in result['comparisons']}
    current = comparisons[(ARMS[0], ARMS[1])]
    candidate = comparisons[(ARMS[1], ARMS[2])]
    self.assertAlmostEqual(current['requested_torque_rmse_difference'], .1)
    self.assertAlmostEqual(current['requested_torque_max_difference'], .1)
    self.assertAlmostEqual(candidate['requested_torque_rmse_difference'], math.sqrt(.05))
    self.assertAlmostEqual(candidate['requested_torque_max_difference'], .3)
    rates = {row['arm']: row['command_rate_rms_ratio_per_s'] for row in result['diagnostics']}
    self.assertEqual(rates, {ARMS[0]: 0., ARMS[1]: 0., ARMS[2]: 20.})
    serialized = json.dumps(result, allow_nan=False)
    request = json.loads(case.arms[0].request)
    self.assertNotIn(request['source']['root'], serialized)
    self.assertNotIn(request['car_params_base64'], serialized)
    self.assertNotIn('"samples"', serialized)
    self.assertNotIn('steering_jerk', serialized)

  def test_same_summary_but_reversed_trace_fails_repeatability(self):
    calls = 0

    def worker(request, *, timeout_s):
      nonlocal calls
      calls += 1
      return response(request, (.2, .1) if calls == 6 else (.1, .2))

    with patch('openpilot.tools.cyber_autotune.native_experiment.run_native', worker):
      result = run_experiment(experiment(), timeout_s=10.)
    self.assertEqual(result['status'], 'FAIL')
    self.assertFalse(result['repeatable'])
    self.assertIn('CYBER_CANDIDATE_REPEATABILITY_FAILED', result['issues'])
    self.assertEqual(result['comparisons'], [])

  def test_failure_timeout_exception_and_stale_outputs_are_not_zero_results(self):
    for fault in ('TIMEOUT', 'WORKER_FAILED', 'stale', 'exception', 'malformed'):
      calls = 0

      def worker(request, *, timeout_s, fault=fault):
        nonlocal calls
        calls += 1
        if calls != 1:
          return response(request, (0., 0.))
        if fault == 'exception':
          raise RuntimeError('PRIVATE_EXCEPTION_TEXT')
        if fault == 'stale':
          return dict(response(request, (0., 0.)), request_sha256='0' * 64)
        if fault == 'malformed':
          return []
        return {'status': fault, 'request_sha256': hashlib.sha256(encode_request(request)).hexdigest(),
                'runtime_accepted': False, 'promotable': False}

      with self.subTest(fault=fault), patch('openpilot.tools.cyber_autotune.native_experiment.run_native', worker):
        result = run_experiment(experiment(), timeout_s=10.)
        self.assertEqual(result['status'], 'REVALIDATION_REQUIRED')
        self.assertEqual(len(result['runs']), 6)
        self.assertFalse(result['repeatable'])
        self.assertEqual(result['comparisons'], [])
        self.assertEqual(result['diagnostics'], [])
        self.assertNotIn('PRIVATE_EXCEPTION_TEXT', json.dumps(result))

  def test_arm_input_order_does_not_change_canonical_execution_or_mutate_requests(self):
    case = experiment()
    reversed_case = NativeExperiment(tuple(reversed(case.arms)), case.scenario_tags)
    original = copy.deepcopy(reversed_case)
    with patch('openpilot.tools.cyber_autotune.native_experiment.run_native', side_effect=lambda request, **_: response(request, (0., 0.))):
      first = run_experiment(case, timeout_s=10.)
      second = run_experiment(reversed_case, timeout_s=10.)
    self.assertEqual(first, second)
    self.assertEqual(reversed_case, original)


if __name__ == '__main__':
  unittest.main()
