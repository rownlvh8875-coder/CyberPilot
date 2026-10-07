import copy
import unittest

from openpilot.selfdrive.controls.lib.cyber_lateral.command_domain import OfflineTorqueCommandContract
from openpilot.tools.cyber_autotune.comparison import ArmSpec, ComparisonGroup, ComparisonPolicy, compare_receipts
from openpilot.tools.cyber_autotune.contracts import MetricContract
from openpilot.tools.cyber_autotune.curvature_yaw_comparison import (
  CurvatureYawReferenceEvidence,
  build_comparison_receipt,
  closed_loop_binding_for_comparison,
  reference_evidence_sha256,
  run_binding_for_native,
)
from openpilot.tools.cyber_autotune.curvature_yaw_native_runner import admit_native_transcript, closed_loop_frames, initial_state, run_native_transcript
from openpilot.tools.cyber_autotune.curvature_yaw_closed_loop import closed_loop_state_sha256
from openpilot.tools.cyber_autotune.lateral_closed_loop import ClosedLoopDomain, frames_sha256
from openpilot.tools.cyber_autotune.preflight import CoveragePolicy, REQUIRED_STRATA
from openpilot.tools.cyber_autotune.tests.test_curvature_yaw_native_runner import request_fixture


def h(char):
  return char * 64


def curved_request():
  request = request_fixture()
  pattern = (
    0.0, 0.001, 0.002, 0.002, 0.001,
    0.0, -0.001, -0.002, -0.002, -0.001,
    0.0, 0.001, 0.002, 0.001, 0.0,
    -0.001, -0.002, -0.001, 0.0, 0.0,
  )
  for frame, curvature in zip(request['native']['frames'], pattern, strict=True):
    frame['desired_curvature_1pm'] = curvature
  return request


def reference_fixture(count):
  coverage = tuple(sorted((name, min(2, count)) for name in REQUIRED_STRATA))
  phases = ('straight', 'entry', 'apex', 'exit') * (count // 4) + ('straight',) * (count % 4)
  return CurvatureYawReferenceEvidence(
    desired_path_offset_m=(0.0,) * count,
    lane_center_path_offset_m=(0.0,) * count,
    left_lane_edge_offset_m=(-1.8,) * count,
    right_lane_edge_offset_m=(1.8,) * count,
    vehicle_half_width_m=0.9,
    curve_phase_labels=tuple(phases),
    coverage=coverage,
    desired_path_source_sha256=h('8'),
    lane_center_source_sha256=h('9'),
    lane_edge_source_sha256=h('a'),
    vehicle_geometry_sha256=h('7'),
    coverage_review_sha256=h('b'),
  )


class TestCurvatureYawComparisonBridge(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.request = curved_request()
    cls.result = run_native_transcript(cls.request, timeout_s=10.0)
    if cls.result.get('status') != 'COMPLETED':
      raise AssertionError(cls.result)
    cls.frames = closed_loop_frames(cls.request)
    cls.domain = ClosedLoopDomain(h('5'), 0.01, 3.0, 7.0, 0.02, 'PLANT', 1.0)
    cls.reference = reference_fixture(len(cls.frames))
    cls.coverage_policy = CoveragePolicy(
      h('b'), tuple(sorted((name, 1) for name in REQUIRED_STRATA)),
    )
    cls.contract = MetricContract(
      pipeline_sha256=h('c'),
      configuration_sha256=h('d'),
      inputs_sha256=frames_sha256(cls.frames),
      mask_sha256=h('e'),
      reset_policy_sha256=closed_loop_state_sha256(initial_state(cls.request)),
      reference_evidence_sha256=reference_evidence_sha256(cls.reference),
      command=OfflineTorqueCommandContract(384, 3, 7, 0.01, 'synthetic comparison bridge test'),
      alignment_delay_s=0.0,
      reversal_deadband_ratio_per_s=0.0,
    )
    cls.run_binding = run_binding_for_native(
      cls.request, cls.result, cls.domain, cls.contract,
      environment_sha256=h('f'),
    )

  def admitted(self, arm):
    closed = closed_loop_binding_for_comparison(
      self.run_binding, self.result, plant_calibration_sha256=h('6'),
    )
    return admit_native_transcript(
      self.request, self.result, self.domain, closed, arm=arm,
    )

  def group(self):
    arms = tuple(
      ArmSpec(arm, self.run_binding)
      for arm in ('UPSTREAM_BASELINE', 'CYBER_CURRENT', 'CYBER_CANDIDATE')
    )
    return ComparisonGroup(h('1'), ('straight', 'gentle_curve'), self.contract, arms)

  def test_three_arm_receipts_reach_frozen_comparator_without_inventing_improvement(self):
    group = self.group()
    receipts = []
    for arm_spec in group.arms:
      admitted = self.admitted(arm_spec.arm)
      self.assertEqual(admitted.status, 'STRUCTURAL_ADMISSION')
      for repetition in (0, 1):
        receipts.append(build_comparison_receipt(
          self.request, self.result, admitted, group, arm_spec, repetition,
          self.reference, self.coverage_policy,
        ))
    policy = ComparisonPolicy(h('2'), (group,), self.coverage_policy, 0.01)
    assessment = compare_receipts(policy, tuple(receipts))
    self.assertEqual(assessment.expected_runs, 6)
    self.assertEqual(assessment.received_runs, 6)
    self.assertEqual(assessment.repeatable_groups, 1)
    self.assertEqual(assessment.status, 'FAIL')
    self.assertTrue(assessment.local_nonregression_pass)
    self.assertFalse(assessment.primary_improvement_pass)
    self.assertIn('NO_PRIMARY_IMPROVEMENT', {issue.code for issue in assessment.issues})
    self.assertFalse(assessment.runtime_accepted)
    self.assertFalse(assessment.promotable)

  def test_missing_or_dependent_reference_is_rejected_before_comparison_receipt(self):
    group = self.group()
    arm = group.arms[0]
    admitted = self.admitted(arm.arm)
    short = CurvatureYawReferenceEvidence(
      desired_path_offset_m=self.reference.desired_path_offset_m[:-1],
      lane_center_path_offset_m=self.reference.lane_center_path_offset_m,
      left_lane_edge_offset_m=self.reference.left_lane_edge_offset_m,
      right_lane_edge_offset_m=self.reference.right_lane_edge_offset_m,
      vehicle_half_width_m=self.reference.vehicle_half_width_m,
      curve_phase_labels=self.reference.curve_phase_labels,
      coverage=self.reference.coverage,
      desired_path_source_sha256=h('8'),
      lane_center_source_sha256=h('9'),
      lane_edge_source_sha256=h('a'),
      vehicle_geometry_sha256=h('7'),
      coverage_review_sha256=h('b'),
    )
    dependent = CurvatureYawReferenceEvidence(
      **{**self.reference.__dict__, 'lane_center_source_sha256': h('8')},
    )
    for evidence in (short, dependent):
      contract = MetricContract(
        pipeline_sha256=self.contract.pipeline_sha256,
        configuration_sha256=self.contract.configuration_sha256,
        inputs_sha256=self.contract.inputs_sha256,
        mask_sha256=self.contract.mask_sha256,
        reset_policy_sha256=self.contract.reset_policy_sha256,
        reference_evidence_sha256=reference_evidence_sha256(evidence),
        command=self.contract.command,
        alignment_delay_s=self.contract.alignment_delay_s,
        reversal_deadband_ratio_per_s=self.contract.reversal_deadband_ratio_per_s,
      )
      bad_group = ComparisonGroup(group.group_sha256, group.scenario_tags, contract, group.arms)
      with self.subTest(evidence=evidence), self.assertRaises(ValueError):
        build_comparison_receipt(
          self.request, self.result, admitted, bad_group, arm, 0,
          evidence, self.coverage_policy,
        )

  def test_reference_hash_and_run_binding_tamper_are_rejected(self):
    group = self.group()
    arm = group.arms[0]
    admitted = self.admitted(arm.arm)
    bad_contract = MetricContract(
      pipeline_sha256=self.contract.pipeline_sha256,
      configuration_sha256=self.contract.configuration_sha256,
      inputs_sha256=self.contract.inputs_sha256,
      mask_sha256=self.contract.mask_sha256,
      reset_policy_sha256=self.contract.reset_policy_sha256,
      reference_evidence_sha256=h('7'),
      command=self.contract.command,
      alignment_delay_s=self.contract.alignment_delay_s,
      reversal_deadband_ratio_per_s=self.contract.reversal_deadband_ratio_per_s,
    )
    bad_group = ComparisonGroup(group.group_sha256, group.scenario_tags, bad_contract, group.arms)
    with self.assertRaises(ValueError):
      build_comparison_receipt(
        self.request, self.result, admitted, bad_group, arm, 0,
        self.reference, self.coverage_policy,
      )

    changed_result = copy.deepcopy(self.result)
    changed_result['car_params_sha256'] = h('7')
    with self.assertRaises(ValueError):
      build_comparison_receipt(
        self.request, changed_result, admitted, group, arm, 0,
        self.reference, self.coverage_policy,
      )

  def test_metric_observation_tamper_is_rejected_by_native_response_binding(self):
    changed = copy.deepcopy(self.result)
    changed['metric_observations'][0]['steering_angle_deg'] += 0.1
    group = self.group()
    admitted = self.admitted(group.arms[0].arm)
    with self.assertRaises(ValueError):
      build_comparison_receipt(
        self.request, changed, admitted, group, group.arms[0], 0,
        self.reference, self.coverage_policy,
      )


if __name__ == '__main__':
  unittest.main()
