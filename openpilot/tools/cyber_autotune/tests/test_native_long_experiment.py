import copy
import hashlib
import json
import math
import unittest
from unittest.mock import patch

from openpilot.tools.cyber_autotune.native_long_experiment import NativeLongArm, NativeLongExperiment, run_experiment
from openpilot.tools.cyber_autotune.native_long_protocol import encode_request
from openpilot.tools.cyber_autotune.tests.test_native_long_worker import fixture


ARMS = ('UPSTREAM_BASELINE', 'CYBER_CURRENT', 'CYBER_CANDIDATE')
WORKER = 'openpilot.tools.cyber_autotune.native_long_experiment.run_native'


def experiment():
  request = fixture()
  request['frames'] = [dict(request['frames'][1], time_ns=i * 10_000_000) for i in range(2)]
  return NativeLongExperiment(tuple(NativeLongArm(arm, encode_request(request)) for arm in ARMS), ('straight',))


def response(request, values):
  rows = [{'time_ns': frame['time_ns'], 'requested_accel_mps2': value, 'long_active': True,
           'state_before': 'off' if index == 0 else 'pid', 'state_after': 'pid'}
          for index, (frame, value) in enumerate(zip(request['frames'], values, strict=True))]
  trace = json.dumps(rows, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
  return {'status': 'COMPLETED', 'scope': 'OFFLINE_NATIVE_REQUESTED_ACCEL',
          'request_sha256': hashlib.sha256(encode_request(request)).hexdigest(),
          'source_head': request['source']['head'], 'opendbc_head': request['source']['opendbc_head'],
          'car_params_sha256': request['car_params_sha256'], 'samples': rows,
          'ordered_trace_sha256': hashlib.sha256(trace).hexdigest(), 'runtime_accepted': False, 'promotable': False}


class TestNativeLongExperiment(unittest.TestCase):
  def test_actual_six_native_runs_repeat_without_qualification(self):
    result = run_experiment(experiment(), timeout_s=10.)
    self.assertEqual(result['status'], 'REVALIDATION_REQUIRED')
    self.assertTrue(result['repeatable'])
    self.assertEqual([r['arm'] for r in result['runs']], [arm for arm in ARMS for _ in range(2)])
    self.assertTrue(all(r['status'] == 'COMPLETED' and r['sample_count'] == 2 for r in result['runs']))
    self.assertEqual(len(result['comparisons']), 3)
    self.assertFalse(result['runtime_accepted'])
    self.assertFalse(result['promotable'])
    self.assertIn('COUPLED_PLANNER_EVENT_REPLAY_PENDING', result['issues'])
    self.assertIn('REVALIDATION_REQUIRED', result['markdown'])

  def test_invalid_matrix_tags_inputs_and_owner_never_launch(self):
    valid = experiment()
    bad = [None, NativeLongExperiment(valid.arms[:2], ('straight',)),
           NativeLongExperiment((valid.arms[0],) * 3, ('straight',)),
           NativeLongExperiment(list(valid.arms), ('straight',)),
           NativeLongExperiment(valid.arms, ()), NativeLongExperiment(valid.arms, ('private',)),
           NativeLongExperiment(valid.arms, ('straight', 'straight'))]
    for owner in (False, True):
      request = json.loads(valid.arms[2].request)
      if owner:
        request['openpilot_longitudinal_control'] = False
      else:
        request['frames'][0]['accel_mps2'] = .1
      bad.append(NativeLongExperiment((*valid.arms[:2], NativeLongArm(ARMS[2], encode_request(request))), ('straight',)))
    bad.append(NativeLongExperiment((*valid.arms[:2], NativeLongArm(ARMS[2], bytearray(valid.arms[2].request))), ('straight',)))
    with patch(WORKER, side_effect=AssertionError('must not launch')) as worker:
      for item in bad:
        with self.subTest(item=type(item)), self.assertRaises(ValueError):
          run_experiment(item, timeout_s=10.)
      for timeout in (0, -1, True, float('nan'), 61):
        with self.subTest(timeout=timeout), self.assertRaises(ValueError):
          run_experiment(valid, timeout_s=timeout)
      worker.assert_not_called()

  def test_hand_derived_requested_units_and_private_content_exclusion(self):
    case = experiment()
    calls = 0

    def worker(request, **_):
      nonlocal calls
      values = ((0., 0.), (.1, .1), (2., -3.5))[calls // 2]
      calls += 1
      return response(request, values)

    with patch(WORKER, worker):
      result = run_experiment(case, timeout_s=10.)
    comparisons = {(row['reference'], row['arm']): row for row in result['comparisons']}
    candidate = comparisons[(ARMS[1], ARMS[2])]
    self.assertAlmostEqual(candidate['requested_accel_rmse_difference_mps2'], math.sqrt((1.9 ** 2 + 3.6 ** 2) / 2))
    self.assertAlmostEqual(candidate['requested_accel_max_difference_mps2'], 3.6)
    diagnostic = result['diagnostics'][2]
    self.assertEqual(diagnostic['requested_accel_rate_rms_mps3'], 550.)
    self.assertEqual(diagnostic['native_pid_bound_occupancy_ratio'], 1.)
    self.assertEqual(diagnostic['long_active_ratio'], 1.)
    self.assertEqual(diagnostic['stopping_state_ratio'], 0.)
    serialized = json.dumps(result, allow_nan=False)
    request = json.loads(case.arms[0].request)
    self.assertNotIn(request['source']['root'], serialized)
    self.assertNotIn(request['car_params_base64'], serialized)
    self.assertNotIn('"samples"', serialized)
    self.assertNotIn('"stopping_distance"', serialized)
    self.assertIn('not measured vehicle jerk', result['markdown'])

  def test_same_summary_reordered_commands_fail_repeatability(self):
    calls = 0

    def worker(request, **_):
      nonlocal calls
      calls += 1
      return response(request, (.2, .1) if calls == 6 else (.1, .2))

    with patch(WORKER, worker):
      result = run_experiment(experiment(), timeout_s=10.)
    self.assertEqual(result['status'], 'FAIL')
    self.assertFalse(result['repeatable'])
    self.assertIn('CYBER_CANDIDATE_REPEATABILITY_FAILED', result['issues'])
    self.assertEqual(result['comparisons'], [])
    self.assertEqual(result['diagnostics'], [])

  def test_incomplete_stale_and_exception_results_are_not_zero_evidence(self):
    for fault in ('TIMEOUT', 'WORKER_FAILED', 'stale', 'exception', 'malformed', 'invalid_authority'):
      calls = 0

      def worker(request, fault=fault, **_):
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
        if fault == 'invalid_authority':
          return dict(response(request, (0., 0.)), runtime_accepted=True)
        return {'status': fault}

      with self.subTest(fault=fault), patch(WORKER, worker):
        result = run_experiment(experiment(), timeout_s=10.)
        self.assertEqual(result['status'], 'REVALIDATION_REQUIRED')
        self.assertFalse(result['repeatable'])
        self.assertEqual(len(result['runs']), 6)
        self.assertEqual(result['comparisons'], [])
        self.assertEqual(result['diagnostics'], [])
        self.assertNotIn('PRIVATE_EXCEPTION_TEXT', json.dumps(result))

  def test_distinct_source_and_cp_cannot_reuse_other_arm_response(self):
    original = experiment()
    arms = []
    for index, arm in enumerate(original.arms):
      request = json.loads(arm.request)
      request['source']['head'] = str(index + 1) * 40
      # Separate valid CP serialization identities, not a device write/tuning permission.
      from opendbc.car import structs
      import base64
      from openpilot.tools.cyber_autotune.tests.test_native_long_worker import bind_cp
      with structs.CarParams.from_bytes(base64.b64decode(request['car_params_base64'])) as cp:
        builder = cp.as_builder()
      builder.stopAccel = -1. - .1 * index
      bind_cp(request, builder.to_bytes())
      arms.append(NativeLongArm(arm.arm, encode_request(request)))
    case = NativeLongExperiment(tuple(arms), original.scenario_tags)
    with patch(WORKER, side_effect=lambda request, **_: response(request, (0., 0.))):
      valid = run_experiment(case, timeout_s=10.)
    self.assertTrue(valid['repeatable'])
    self.assertEqual(len({r['car_params_sha256'] for r in valid['runs']}), 3)
    stale = response(json.loads(arms[0].request), (0., 0.))
    with patch(WORKER, return_value=stale):
      result = run_experiment(case, timeout_s=10.)
    self.assertFalse(result['repeatable'])
    self.assertEqual(result['comparisons'], [])
    self.assertTrue(all(r['status'] == 'INVALID_RESPONSE' for r in result['runs'][2:]))

  def test_order_is_canonical_and_input_is_not_mutated(self):
    case = experiment()
    reverse = NativeLongExperiment(tuple(reversed(case.arms)), case.scenario_tags)
    before = copy.deepcopy(reverse)
    with patch(WORKER, side_effect=lambda request, **_: response(request, (0., 0.))):
      first = run_experiment(case, timeout_s=10.)
      second = run_experiment(reverse, timeout_s=10.)
    self.assertEqual(first, second)
    self.assertEqual(reverse, before)


if __name__ == '__main__':
  unittest.main()
