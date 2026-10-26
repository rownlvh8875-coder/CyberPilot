from dataclasses import fields, replace
import unittest

from openpilot.tools.cyber_autotune import contracts, preflight
from openpilot.tools.cyber_autotune.comparison import (
  ArmSpec, ComparisonGroup, ComparisonPolicy, RunBinding, RunReceipt, compare_receipts,
)
from openpilot.tools.cyber_autotune.tests.test_contracts import binding, metric_input
from openpilot.tools.cyber_autotune.tests.test_preflight import change_metric, policy_and_coverage


def experiment(improved=True):
  """Synthetic group. No assertion of real route coverage or native execution."""
  contract = binding(contracts)
  batch = contracts.compute_metrics_v2(metric_input(), contract)
  coverage_policy, counts = policy_and_coverage(preflight)
  run_binding = RunBinding('1' * 64, '2' * 64, 'b' * 64, 'c' * 64, 'e' * 64, 'd' * 64,
                           '3' * 64, 'a' * 64, '4' * 64, '5' * 64, '6' * 64, '7' * 64)
  arms = tuple(ArmSpec(name, replace(run_binding, software_sha256=f'{i + 1:x}' * 64))
               for i, name in enumerate(('UPSTREAM_BASELINE', 'CYBER_CURRENT', 'CYBER_CANDIDATE')))
  group = ComparisonGroup('8' * 64, ('straight', 'gentle_curve'), contract, arms)
  policy = ComparisonPolicy('9' * 64, (group,), coverage_policy, .01)
  receipts = []
  for spec in arms:
    metrics = batch
    if improved and spec.arm == 'CYBER_CANDIDATE':
      metrics = change_metric(batch, 'lane_center_offset', signed_mean=.05, rmse=.05, p95_abs=.05, maximum_abs=.05)
    for repetition in (0, 1):
      receipts.append(RunReceipt(group.group_sha256, spec.arm, repetition, spec.binding, 'a' * 64,
                                 'COMPLETED', metrics, tuple(sorted(counts.items())), ()))
  return policy, tuple(receipts)


def change_arm(receipts, arm='CYBER_CANDIDATE', **changes):
  return tuple(replace(item, **changes) if item.arm == arm else item for item in receipts)


class TestComparison(unittest.TestCase):
  def codes(self, result):
    return {issue.code for issue in result.issues}

  def assert_unqualified(self, result):
    self.assertFalse(result.offline_evaluable)
    self.assertFalse(result.promotable)
    self.assertFalse(result.runtime_accepted)

  def test_local_improvement_still_requires_native_evidence(self):
    p, receipts = experiment()
    result = compare_receipts(p, receipts)
    self.assertEqual(result.status, 'REVALIDATION_REQUIRED')
    self.assertTrue(result.local_nonregression_pass)
    self.assertTrue(result.primary_improvement_pass)
    self.assertEqual((result.expected_runs, result.received_runs, result.repeatable_groups), (6, 6, 1))
    self.assertIn('EVIDENCE_AUTHENTICITY_PENDING', self.codes(result))
    self.assertIn('UNCERTAINTY_VALIDATION_PENDING', self.codes(result))
    self.assertIn('LONGITUDINAL_ADAPTER_PENDING', self.codes(result))
    self.assert_unqualified(result)

  def test_identical_arms_are_repeatable_not_improved(self):
    result = compare_receipts(*experiment(improved=False))
    self.assertEqual(result.status, 'FAIL')
    self.assertTrue(result.local_nonregression_pass)
    self.assertFalse(result.primary_improvement_pass)
    self.assertIn('NO_PRIMARY_IMPROVEMENT', self.codes(result))

  def test_receipt_order_does_not_change_assessment(self):
    p, receipts = experiment()
    self.assertEqual(compare_receipts(p, receipts), compare_receipts(p, tuple(reversed(receipts))))

  def test_invalid_policy_and_review_numeric_types_fail_closed(self):
    p, r = experiment()
    for bad in (None, {}, [], True, replace(p, review_sha256=''), replace(p, groups=()),
                replace(p, groups=list(p.groups)), replace(p, groups=p.groups * 65), replace(p, coverage_policy=None)):
      result = compare_receipts(bad, r)
      self.assertEqual(result.status, 'REVALIDATION_REQUIRED')
      self.assertIn('INVALID_POLICY', self.codes(result))
      self.assert_unqualified(result)
    for value in (0., -.1, None, True, float('nan'), float('inf'), 10 ** 400):
      self.assertIn('INVALID_POLICY', self.codes(compare_receipts(replace(p, primary_minimum_improvement_m=value), r)))

  def test_invalid_group_tags_arms_and_identities_fail_closed(self):
    p, r = experiment()
    group = p.groups[0]
    bad_groups = (replace(group, group_sha256='private/path'), replace(group, scenario_tags=()),
                  replace(group, scenario_tags=('straight', 'straight')), replace(group, scenario_tags=('unknown',)),
                  replace(group, arms=group.arms[:2]), replace(group, arms=(group.arms[0],) * 3),
                  replace(group, arms=(replace(group.arms[0], arm=[]), *group.arms[1:])), replace(group, contract=None))
    for bad in bad_groups:
      self.assertIn('INVALID_POLICY', self.codes(compare_receipts(replace(p, groups=(bad,)), r)))
    for item in fields(group.arms[0].binding):
      bad_arm = replace(group.arms[0], binding=replace(group.arms[0].binding, **{item.name: None}))
      bad_group = replace(group, arms=(bad_arm, *group.arms[1:]))
      self.assertIn('INVALID_POLICY', self.codes(compare_receipts(replace(p, groups=(bad_group,)), r)))

  def test_common_basis_cannot_differ_between_declared_arms(self):
    p, r = experiment()
    group = p.groups[0]
    for name in ('inputs_sha256', 'reset_sha256', 'mask_sha256', 'plant_sha256', 'domain_sha256',
                 'environment_sha256', 'timebase_sha256', 'metric_sha256'):
      arm = replace(group.arms[2], binding=replace(group.arms[2].binding, **{name: '0' * 64}))
      self.assertIn('INVALID_POLICY', self.codes(compare_receipts(replace(p, groups=(replace(group, arms=(*group.arms[:2], arm)),)), r)))

  def test_missing_extra_duplicate_and_unknown_receipts_do_not_form_experiment(self):
    p, r = experiment()
    for bad in (r[:-1], (*r, r[-1]), (r[0], *r[0:5]), (replace(r[0], group_sha256='0' * 64), *r[1:]),
                (replace(r[0], arm='UNKNOWN'), *r[1:]), (replace(r[0], repetition=True), *r[1:]),
                (replace(r[0], repetition=2), *r[1:]), (None, *r[1:]), list(r), None):
      result = compare_receipts(p, bad)
      self.assertEqual(result.status, 'REVALIDATION_REQUIRED')
      self.assertFalse(result.local_nonregression_pass)

  def test_arm_identity_and_metric_contract_must_match_declaration(self):
    p, r = experiment()
    for item in fields(r[0].binding):
      changed = replace(r[0], binding=replace(r[0].binding, **{item.name: '0' * 64}))
      result = compare_receipts(p, (changed, *r[1:]))
      self.assertIn('RUN_BINDING_MISMATCH', self.codes(result))
    bad = replace(r[0].metrics, contract=replace(r[0].metrics.contract, mask_sha256='0' * 64))
    self.assertIn('METRIC_CONTRACT_MISMATCH', self.codes(compare_receipts(p, (replace(r[0], metrics=bad), *r[1:]))))

  def test_equal_metrics_do_not_hide_trace_nondeterminism(self):
    p, r = experiment()
    for index, expected in ((1, 'BASELINE_AA_FAILED'), (3, 'BASELINE_AA_FAILED'), (5, 'CANDIDATE_REPEATABILITY_FAILED')):
      changed = tuple(replace(item, trace_sha256='0' * 64) if i == index else item for i, item in enumerate(r))
      result = compare_receipts(p, changed)
      self.assertEqual(result.status, 'FAIL')
      self.assertIn(expected, self.codes(result))
      self.assertFalse(result.local_nonregression_pass)

  def test_failed_timeout_missing_trace_and_metrics_are_not_complete(self):
    p, r = experiment()
    for outcome in ('FAILED', 'TIMEOUT'):
      changed = change_arm(r, outcome=outcome, metrics=None, trace_sha256=None, coverage=())
      result = compare_receipts(p, changed)
      self.assertEqual(result.status, 'REVALIDATION_REQUIRED')
      self.assertIn(f'RUN_{outcome}', self.codes(result))
    for changes in ({'trace_sha256': None}, {'metrics': None}, {'outcome': 'PASS'}, {'hard_violations': ('NOT_A_CODE',)}):
      self.assertEqual(compare_receipts(p, change_arm(r, **changes)).status, 'REVALIDATION_REQUIRED')

  def test_hard_failure_cannot_be_offset_by_primary_improvement(self):
    p, r = experiment()
    for violation in ('ACTUATOR_LIMIT', 'PLANT_DOMAIN', 'INVALID_VEHICLE_STATE', 'SAFETY_BOUNDARY'):
      result = compare_receipts(p, change_arm(r, hard_violations=(violation,)))
      self.assertEqual(result.status, 'FAIL')
      self.assertIn('HARD_CONSTRAINT_VIOLATION', self.codes(result))
      self.assertFalse(result.local_nonregression_pass)

  def test_primary_edge_right_phase_and_zero_regressions_cannot_hide(self):
    p, r = experiment()
    for name, changes in (('lane_center_offset', {'rmse': .11}), ('lane_edge_minimum_margin', {'signed_mean': .9}),
                          ('right_curve_lane_center_error', {'rmse': .2}),
                          ('declared_delay_phase_residual_entry', {'maximum_abs': .2}),
                          ('torque_saturation_ratio', {'signed_mean': 1e-15})):
      candidate = change_metric(r[-1].metrics, name, **changes)
      result = compare_receipts(p, change_arm(r, metrics=candidate))
      self.assertEqual(result.status, 'FAIL')
      self.assertIn('CANDIDATE_REGRESSION', self.codes(result))

  def test_missing_invalid_numeric_and_phase_metrics_block(self):
    p, r = experiment()
    for name in ('lane_center_offset', 'declared_delay_phase_residual_entry'):
      for changes in ({'rmse': float('nan')}, {'rmse': True}, {'count': 0}, {'valid': False}):
        candidate = change_metric(r[-1].metrics, name, **changes)
        result = compare_receipts(p, change_arm(r, metrics=candidate))
        self.assertEqual(result.status, 'REVALIDATION_REQUIRED')
        self.assertFalse(result.local_nonregression_pass)
      candidate = replace(r[-1].metrics, metrics=tuple(item for item in r[-1].metrics.metrics if item.name != name))
      self.assertEqual(compare_receipts(p, change_arm(r, metrics=candidate)).status, 'REVALIDATION_REQUIRED')

  def test_coverage_shape_counts_and_masks_are_not_inferred(self):
    p, r = experiment()
    for coverage in ((), list(r[-1].coverage), r[-1].coverage[:-1], (r[-1].coverage[0],) * 16,
                     tuple((name, True) for name, _ in r[-1].coverage), tuple((name, 0) for name, _ in r[-1].coverage),
                     tuple((name, 2) for name, _ in r[-1].coverage)):
      result = compare_receipts(p, change_arm(r, coverage=coverage))
      self.assertEqual(result.status, 'REVALIDATION_REQUIRED')
      self.assertFalse(result.local_nonregression_pass)

  def test_candidate_compared_against_both_baselines(self):
    p, r = experiment()
    better_current = change_metric(r[2].metrics, 'lane_center_offset', signed_mean=.02, rmse=.02, p95_abs=.02, maximum_abs=.02)
    result = compare_receipts(p, change_arm(r, arm='CYBER_CURRENT', metrics=better_current))
    self.assertEqual(result.status, 'FAIL')
    self.assertTrue(any(issue.code == 'CANDIDATE_REGRESSION' and issue.detail.startswith('CYBER_CURRENT:') for issue in result.issues))

  def test_current_regression_is_diagnostic_when_candidate_fixes_it(self):
    p, r = experiment()
    worse = change_metric(r[2].metrics, 'lane_center_offset', rmse=.2, p95_abs=.2, maximum_abs=.2)
    result = compare_receipts(p, change_arm(r, arm='CYBER_CURRENT', metrics=worse))
    self.assertEqual(result.status, 'REVALIDATION_REQUIRED')
    self.assertIn('CURRENT_REGRESSION_DIAGNOSTIC', self.codes(result))
    self.assertTrue(result.local_nonregression_pass)

  def test_two_groups_require_their_own_six_records(self):
    p, r = experiment()
    second_group = replace(p.groups[0], group_sha256='0' * 64)
    p = replace(p, groups=(*p.groups, second_group))
    extra = tuple(replace(item, group_sha256=second_group.group_sha256) for item in r)
    result = compare_receipts(p, (*r, *extra))
    self.assertEqual((result.expected_runs, result.repeatable_groups), (12, 2))
    self.assertTrue(result.local_nonregression_pass)
    self.assertEqual(compare_receipts(p, (*r, *r)).status, 'REVALIDATION_REQUIRED')

  def test_improved_and_unchanged_groups_preserve_local_improvement_in_either_order(self):
    p, improved = experiment()
    _, unchanged = experiment(improved=False)
    second_group = replace(p.groups[0], group_sha256='0' * 64)
    unchanged = tuple(replace(item, group_sha256=second_group.group_sha256) for item in unchanged)
    for groups in ((p.groups[0], second_group), (second_group, p.groups[0])):
      with self.subTest(first_group=groups[0].group_sha256):
        result = compare_receipts(replace(p, groups=groups), (*improved, *unchanged))
        self.assertEqual(result.status, 'REVALIDATION_REQUIRED')
        self.assertEqual((result.expected_runs, result.received_runs, result.repeatable_groups), (12, 12, 2))
        self.assertTrue(result.local_nonregression_pass)
        self.assertTrue(result.primary_improvement_pass)
        self.assertNotIn('NO_PRIMARY_IMPROVEMENT', self.codes(result))
        self.assertNotIn('CANDIDATE_REGRESSION', self.codes(result))
        self.assert_unqualified(result)

  def test_improved_group_cannot_cancel_another_groups_regression_in_either_order(self):
    p, improved = experiment()
    _, other = experiment(improved=False)
    second_group = replace(p.groups[0], group_sha256='0' * 64)
    worse = change_metric(other[-1].metrics, 'lane_center_offset',
                          signed_mean=.11, rmse=.11, p95_abs=.11, maximum_abs=.11)
    other = tuple(replace(item, group_sha256=second_group.group_sha256)
                  for item in change_arm(other, metrics=worse))
    for groups in ((p.groups[0], second_group), (second_group, p.groups[0])):
      with self.subTest(first_group=groups[0].group_sha256):
        result = compare_receipts(replace(p, groups=groups), (*improved, *other))
        self.assertEqual(result.status, 'FAIL')
        self.assertEqual((result.expected_runs, result.received_runs, result.repeatable_groups), (12, 12, 2))
        self.assertFalse(result.local_nonregression_pass)
        self.assertFalse(result.primary_improvement_pass)
        regressions = tuple(issue for issue in result.issues if issue.code == 'CANDIDATE_REGRESSION')
        self.assertTrue(regressions)
        self.assertEqual({issue.group_sha256 for issue in regressions}, {'0' * 64})
        self.assertEqual({issue.detail.split(':', 1)[0] for issue in regressions}, {'UPSTREAM_BASELINE', 'CYBER_CURRENT'})
        self.assert_unqualified(result)


if __name__ == '__main__':
  unittest.main()
