import copy
import unittest
from unittest.mock import patch

from openpilot.selfdrive.controls.lib.cyber_lateral.command_domain import OfflineTorqueCommandContract
from openpilot.tools.cyber_autotune.contracts import MetricContract
from openpilot.tools.cyber_autotune.curvature_yaw_comparison import reference_evidence_sha256
from openpilot.tools.cyber_autotune.curvature_yaw_closed_loop import closed_loop_state_sha256
from openpilot.tools.cyber_autotune.curvature_yaw_native_protocol import encode_request
from openpilot.tools.cyber_autotune.curvature_yaw_native_runner import closed_loop_frames, initial_state, run_native_transcript
from openpilot.tools.cyber_autotune.curvature_yaw_three_arm import (
  CurvatureYawArmDeclaration,
  CurvatureYawThreeArmExperiment,
  run_three_arm_experiment,
)
from openpilot.tools.cyber_autotune.lateral_closed_loop import ClosedLoopDomain, frames_sha256
from openpilot.tools.cyber_autotune.preflight import CoveragePolicy, REQUIRED_STRATA
from openpilot.tools.cyber_autotune.tests.test_curvature_yaw_comparison import curved_request, reference_fixture


def h(char):
  return char * 64


def experiment_fixture():
  request = curved_request()
  frames = closed_loop_frames(request)
  reference = reference_fixture(len(frames))
  coverage = CoveragePolicy(
    h('b'), tuple(sorted((name, 1) for name in REQUIRED_STRATA)),
  )
  contract = MetricContract(
    pipeline_sha256=h('c'),
    configuration_sha256=h('d'),
    inputs_sha256=frames_sha256(frames),
    mask_sha256=h('e'),
    reset_policy_sha256=closed_loop_state_sha256(initial_state(request)),
    reference_evidence_sha256=reference_evidence_sha256(reference),
    command=OfflineTorqueCommandContract(384, 3, 7, 0.01, 'synthetic three-arm coordinator test'),
    alignment_delay_s=0.0,
    reversal_deadband_ratio_per_s=0.0,
  )
  payload = encode_request(request)
  arms = tuple(
    CurvatureYawArmDeclaration(arm, payload)
    for arm in ('UPSTREAM_BASELINE', 'CYBER_CURRENT', 'CYBER_CANDIDATE')
  )
  experiment = CurvatureYawThreeArmExperiment(
    group_sha256=h('1'),
    review_sha256=h('2'),
    scenario_tags=('straight', 'gentle_curve'),
    arms=arms,
    domain=ClosedLoopDomain(h('5'), 0.01, 3.0, 7.0, 0.02, 'PLANT', 1.0),
    metric_contract=contract,
    coverage_policy=coverage,
    environment_sha256=h('f'),
    plant_calibration_sha256=h('6'),
    primary_minimum_improvement_m=0.01,
  )
  return experiment, reference, request


class TestCurvatureYawThreeArmCoordinator(unittest.TestCase):
  def test_missing_reference_blocks_before_native_worker_launch(self):
    experiment, _reference, _request = experiment_fixture()
    with patch(
      'openpilot.tools.cyber_autotune.curvature_yaw_three_arm.run_native_transcript',
    ) as worker:
      result = run_three_arm_experiment(experiment, None, timeout_s=10.0)
    self.assertEqual(result.status, 'BLOCKED')
    self.assertEqual(result.blockers, ('REFERENCE_EVIDENCE_REQUIRED',))
    self.assertEqual(result.executed_runs, 0)
    worker.assert_not_called()
    self.assertFalse(result.runtime_accepted)
    self.assertFalse(result.promotable)

  def test_identical_three_arm_native_matrix_is_repeatable_but_not_improved(self):
    experiment, reference, _request = experiment_fixture()
    result = run_three_arm_experiment(experiment, reference, timeout_s=10.0)
    self.assertEqual(result.status, 'COMPARISON_EVALUATED')
    self.assertEqual(result.executed_runs, 6)
    self.assertTrue(result.native_repeatable)
    self.assertEqual(len(result.receipts), 6)
    self.assertIsNotNone(result.comparison)
    self.assertEqual(result.comparison.status, 'FAIL')
    self.assertEqual(result.comparison.repeatable_groups, 1)
    self.assertTrue(result.comparison.local_nonregression_pass)
    self.assertFalse(result.comparison.primary_improvement_pass)
    self.assertIn('NO_PRIMARY_IMPROVEMENT', result.blockers)
    self.assertFalse(result.runtime_accepted)
    self.assertFalse(result.promotable)
    self.assertFalse(result.vehicle_activation_allowed)

  def test_duplicate_or_mismatched_arm_declarations_block_before_execution(self):
    experiment, reference, request = experiment_fixture()
    duplicate = CurvatureYawThreeArmExperiment(
      **{
        **experiment.__dict__,
        'arms': (
          experiment.arms[0],
          experiment.arms[0],
          experiment.arms[2],
        ),
      },
    )
    with patch(
      'openpilot.tools.cyber_autotune.curvature_yaw_three_arm.run_native_transcript',
    ) as worker:
      result = run_three_arm_experiment(duplicate, reference, timeout_s=10.0)
    self.assertEqual(result.status, 'BLOCKED')
    self.assertEqual(result.executed_runs, 0)
    worker.assert_not_called()

    changed = copy.deepcopy(request)
    changed['native']['frames'][0]['desired_curvature_1pm'] = 0.003
    candidate = CurvatureYawArmDeclaration('CYBER_CANDIDATE', encode_request(changed))
    mismatch = CurvatureYawThreeArmExperiment(
      **{**experiment.__dict__, 'arms': (*experiment.arms[:2], candidate)},
    )
    with patch(
      'openpilot.tools.cyber_autotune.curvature_yaw_three_arm.run_native_transcript',
    ) as worker:
      result = run_three_arm_experiment(mismatch, reference, timeout_s=10.0)
    self.assertEqual(result.status, 'BLOCKED')
    self.assertEqual(result.executed_runs, 0)
    worker.assert_not_called()

  def test_repeatability_failure_stops_before_receipt_comparison(self):
    experiment, reference, request = experiment_fixture()
    first = run_native_transcript(request, timeout_s=10.0)
    self.assertEqual(first['status'], 'COMPLETED')
    second = copy.deepcopy(first)
    second['final_state_sha256'] = h('7')
    with patch(
      'openpilot.tools.cyber_autotune.curvature_yaw_three_arm.run_native_transcript',
      side_effect=(first, second),
    ):
      result = run_three_arm_experiment(experiment, reference, timeout_s=10.0)
    self.assertEqual(result.status, 'BLOCKED')
    self.assertEqual(result.blockers, ('UPSTREAM_BASELINE_NATIVE_REPEATABILITY_FAILED',))
    self.assertEqual(result.executed_runs, 2)
    self.assertFalse(result.native_repeatable)
    self.assertEqual(result.receipts, ())


if __name__ == '__main__':
  unittest.main()
