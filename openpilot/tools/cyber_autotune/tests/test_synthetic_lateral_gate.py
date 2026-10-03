import hashlib
import math
import unittest
from dataclasses import replace
from pathlib import Path

from openpilot.tools.cyber_autotune.synthetic_lateral_closed_loop import (
  SyntheticClosedLoopMatrixReport,
  SyntheticClosedLoopScenarioResult,
)


ROOT = Path(__file__).resolve().parents[4]
POLICY_PATH = ROOT / 'docs/cyberpilot/policies/synthetic-lateral-nonregression-v1.json'
POLICY_SHA = 'ae4ad7f1cad3e4e5f138df2d4ef8feae17e881a951a5b37caa481fd124ba2a62'


def sha(value):
  return hashlib.sha256(value.encode()).hexdigest()


def scenario(scenario_id, *, fault=False, scale=1.0):
  if fault:
    return SyntheticClosedLoopScenarioResult(
      scenario_id=scenario_id,
      status='REJECTED_INPUT',
      blockers=('SENSOR_INVALID' if scenario_id == 'sensor_dropout' else 'NONUNIFORM_TIMEBASE',),
    )
  sign = -1.0 if 'right' in scenario_id else 1.0
  zero = scenario_id in {'straight_low', 'straight_high', 'friction_low'}
  base = 0.0 if zero else scale
  return SyntheticClosedLoopScenarioResult(
    scenario_id=scenario_id,
    status='COMPLETED_DIAGNOSTIC',
    blockers=('GENERIC_SYNTHETIC_PLANT_NOT_VEHICLE_CALIBRATED',),
    sample_count=600,
    trace_sha256=sha(scenario_id + str(scale)),
    car_params_sha256=sha('cp'),
    controller_executed=True,
    plant_executed=True,
    physical_delay_owner='PLANT',
    controller_delay_queue_present=False,
    lateral_error_rmse_m=10.0 * base,
    maximum_abs_lateral_error_m=20.0 * base,
    maximum_abs_heading_error_rad=0.1 * base,
    steering_jerk_rmse_deg_s3=100.0 * base,
    saturation_ratio=0.5 * base,
    command_reversal_events=2 if not zero else 0,
    signed_mean_desired_curvature_1pm=0.005 * sign * base,
    signed_mean_actual_curvature_1pm=0.004 * sign * base,
    maximum_abs_requested_torque=0.8 * base,
    inactive_requested_torque_max_abs=0.0,
    inactive_applied_command_max_abs=0.0,
    driver_intervention_frames=20 if scenario_id == 'driver_override' else 0,
  )


SCENARIO_IDS = (
  'straight_low', 'straight_high', 'gentle_left', 'gentle_right',
  'tight_left', 'tight_right', 's_curve', 'ramp_curve', 'lane_change',
  'driver_override', 'friction_low', 'friction_high',
  'sensor_dropout', 'timebase_gap',
)
STRESS_IDS = frozenset({
  'tight_left', 'tight_right', 's_curve', 'ramp_curve',
  'lane_change', 'driver_override',
})


def matrix(*, improved=False):
  rows = []
  for scenario_id in SCENARIO_IDS:
    if scenario_id in {'sensor_dropout', 'timebase_gap'}:
      rows.append(scenario(scenario_id, fault=True))
    else:
      scale = 0.8 if improved and scenario_id in STRESS_IDS else 1.0
      rows.append(scenario(scenario_id, scale=scale))
  result_sha256 = (
    sha('improved') if improved
    else '2421a5399f33fb7b523f8f4b4e486c0f9d717c70edd3a89750cbe49c03e8bdfd'
  )
  return SyntheticClosedLoopMatrixReport(
    status='SYNTHETIC_CLOSED_LOOP_DIAGNOSTIC',
    blockers=(
      'GENERIC_SYNTHETIC_PLANT_NOT_VEHICLE_CALIBRATED',
      'PERFORMANCE_GATE_NOT_EVALUATED',
    ),
    catalog_sha256=sha('catalog'),
    car_params_sha256=sha('cp'),
    result_sha256=result_sha256,
    scenario_count=len(rows),
    completed_count=12,
    rejected_input_count=2,
    blocked_count=0,
    all_nominal_completed=True,
    fault_inputs_rejected=True,
    scenarios=tuple(rows),
  )


class TestSyntheticLateralCandidateGate(unittest.TestCase):
  def policy(self):
    from openpilot.tools.cyber_autotune.synthetic_lateral_gate import load_policy
    return load_policy(POLICY_PATH, expected_sha256=POLICY_SHA)

  def test_identical_candidate_passes_nonregression_without_improvement(self):
    from openpilot.tools.cyber_autotune.synthetic_lateral_gate import (
      evaluate_candidate,
    )

    result = evaluate_candidate(matrix(), matrix(), self.policy())
    self.assertEqual(result.status, 'SYNTHETIC_NONREGRESSION_PASS')
    self.assertTrue(result.no_regression_pass)
    self.assertFalse(result.improvement_pass)
    self.assertEqual(result.improved_stress_scenarios, ())
    self.assertEqual(result.compared_scenario_count, 14)
    self.assertFalse(result.performance_qualified)
    self.assertFalse(result.candidate_generation_allowed)
    self.assertFalse(result.shadow_promotion_allowed)
    self.assertFalse(result.runtime_accepted)
    self.assertFalse(result.promotable)

  def test_all_stress_scenarios_improved_passes_improvement_gate(self):
    from openpilot.tools.cyber_autotune.synthetic_lateral_gate import (
      evaluate_candidate,
    )

    result = evaluate_candidate(matrix(), matrix(improved=True), self.policy())
    self.assertEqual(result.status, 'SYNTHETIC_IMPROVEMENT_PASS')
    self.assertTrue(result.no_regression_pass)
    self.assertTrue(result.improvement_pass)
    self.assertEqual(set(result.improved_stress_scenarios), STRESS_IDS)
    self.assertFalse(result.performance_qualified)
    self.assertFalse(result.candidate_generation_allowed)

  def test_metric_regression_is_rejected(self):
    from openpilot.tools.cyber_autotune.synthetic_lateral_gate import (
      evaluate_candidate,
    )

    candidate = matrix()
    rows = list(candidate.scenarios)
    index = SCENARIO_IDS.index('gentle_left')
    rows[index] = replace(rows[index], lateral_error_rmse_m=11.0)
    candidate = replace(candidate, scenarios=tuple(rows), result_sha256=sha('regression'))
    result = evaluate_candidate(matrix(), candidate, self.policy())
    self.assertEqual(result.status, 'REJECTED')
    self.assertFalse(result.no_regression_pass)
    self.assertIn('gentle_left:lateral_error_rmse_m', result.regressions)
    self.assertFalse(result.candidate_generation_allowed)
    self.assertFalse(result.runtime_accepted)

  def test_saturation_torque_and_inactive_torque_regressions_are_rejected(self):
    from openpilot.tools.cyber_autotune.synthetic_lateral_gate import (
      evaluate_candidate,
    )

    baseline = matrix()
    cases = (
      ('saturation_ratio', 0.53),
      ('maximum_abs_requested_torque', 0.82),
      ('inactive_requested_torque_max_abs', 1e-5),
      ('command_reversal_events', 4),
    )
    for field, value in cases:
      rows = list(baseline.scenarios)
      index = SCENARIO_IDS.index('gentle_left')
      rows[index] = replace(rows[index], **{field: value})
      candidate = replace(
        baseline, scenarios=tuple(rows), result_sha256=sha(field),
      )
      with self.subTest(field=field):
        result = evaluate_candidate(baseline, candidate, self.policy())
        self.assertEqual(result.status, 'REJECTED')
        self.assertFalse(result.no_regression_pass)
        self.assertTrue(any(field in item for item in result.regressions))

  def test_identity_and_fault_outcome_mismatch_block(self):
    from openpilot.tools.cyber_autotune.synthetic_lateral_gate import (
      evaluate_candidate,
    )

    baseline = matrix()
    mismatches = (
      replace(baseline, catalog_sha256=sha('other catalog')),
      replace(baseline, car_params_sha256=sha('other cp')),
      replace(baseline, scenarios=tuple(reversed(baseline.scenarios))),
      replace(
        baseline,
        scenarios=(replace(baseline.scenarios[0], sample_count=599),) + baseline.scenarios[1:],
      ),
      replace(
        baseline,
        scenarios=baseline.scenarios[:-2] + (
          replace(baseline.scenarios[-2], status='COMPLETED_DIAGNOSTIC', sample_count=600),
          baseline.scenarios[-1],
        ),
      ),
    )
    for candidate in mismatches:
      with self.subTest(candidate=candidate):
        result = evaluate_candidate(baseline, candidate, self.policy())
        self.assertEqual(result.status, 'BLOCKED')
        self.assertFalse(result.no_regression_pass)
        self.assertFalse(result.candidate_generation_allowed)

  def test_left_right_symmetry_violation_is_rejected(self):
    from openpilot.tools.cyber_autotune.synthetic_lateral_gate import (
      evaluate_candidate,
    )

    baseline = matrix()
    rows = list(baseline.scenarios)
    index = SCENARIO_IDS.index('gentle_right')
    rows[index] = replace(rows[index], lateral_error_rmse_m=9.0)
    candidate = replace(
      baseline, scenarios=tuple(rows), result_sha256=sha('asymmetric'),
    )
    result = evaluate_candidate(baseline, candidate, self.policy())
    self.assertEqual(result.status, 'REJECTED')
    self.assertFalse(result.symmetry_pass)
    self.assertTrue(any('SYMMETRY' in item for item in result.regressions))

  def test_partial_stress_improvement_remains_nonregression_only(self):
    from openpilot.tools.cyber_autotune.synthetic_lateral_gate import (
      evaluate_candidate,
    )

    baseline = matrix()
    rows = list(baseline.scenarios)
    index = SCENARIO_IDS.index('s_curve')
    rows[index] = replace(
      rows[index],
      lateral_error_rmse_m=rows[index].lateral_error_rmse_m * 0.8,
    )
    candidate = replace(
      baseline, scenarios=tuple(rows), result_sha256=sha('partial'),
    )
    result = evaluate_candidate(baseline, candidate, self.policy())
    self.assertEqual(result.status, 'SYNTHETIC_NONREGRESSION_PASS')
    self.assertTrue(result.no_regression_pass)
    self.assertFalse(result.improvement_pass)
    self.assertEqual(result.improved_stress_scenarios, ('s_curve',))

  def test_nonfinite_candidate_metric_is_blocked(self):
    from openpilot.tools.cyber_autotune.synthetic_lateral_gate import (
      evaluate_candidate,
    )

    baseline = matrix()
    rows = list(baseline.scenarios)
    rows[2] = replace(rows[2], steering_jerk_rmse_deg_s3=math.nan)
    candidate = replace(
      baseline, scenarios=tuple(rows), result_sha256=sha('nonfinite'),
    )
    result = evaluate_candidate(baseline, candidate, self.policy())
    self.assertEqual(result.status, 'BLOCKED')
    self.assertIn('INVALID_CANDIDATE_METRICS', result.blockers)

  def test_policy_digest_and_shape_are_fail_closed(self):
    from openpilot.tools.cyber_autotune.synthetic_lateral_gate import load_policy

    with self.assertRaises(ValueError):
      load_policy(POLICY_PATH, expected_sha256='0' * 64)
    with self.assertRaises(ValueError):
      load_policy(ROOT / 'does-not-exist.json', expected_sha256=POLICY_SHA)

  def test_invalid_input_types_return_blocked(self):
    from openpilot.tools.cyber_autotune.synthetic_lateral_gate import (
      evaluate_candidate,
    )

    policy = self.policy()
    for baseline, candidate in ((None, matrix()), (matrix(), None), ({}, [])):
      result = evaluate_candidate(baseline, candidate, policy)
      self.assertEqual(result.status, 'BLOCKED')
      self.assertFalse(result.runtime_accepted)
      self.assertFalse(result.promotable)


if __name__ == '__main__':
  unittest.main()
