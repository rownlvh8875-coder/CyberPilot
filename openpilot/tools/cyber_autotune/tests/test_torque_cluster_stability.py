import dataclasses
import unittest

from openpilot.tools.cyber_autotune.evidence import PROVENANCE_KEYS
from openpilot.tools.cyber_autotune.torque_identification import SIGNAL_CONTRACT


def provenance(fill='a'):
  return tuple((key, fill * 64) for key in sorted(PROVENANCE_KEYS))


def group(epoch, route, source, counts, start=0, end=9, boundary='START'):
  from openpilot.tools.cyber_autotune.torque_aggregation import TorqueEpochEvidence
  return TorqueEpochEvidence(
    epoch_sha256=epoch * 64,
    route_sha256=route * 64,
    source_commit=source * 40,
    start_segment=start,
    end_segment=end,
    bucket_counts=counts,
    role='development_fit',
    provenance=provenance(),
    signal_contract=SIGNAL_CONTRACT,
    algorithm_sha256='f' * 64,
    boundary_reason=boundary,
  )


def policy():
  from openpilot.tools.cyber_autotune.torque_cluster_stability import TorqueClusterPolicy
  return TorqueClusterPolicy(
    policy_sha256='9' * 64,
    minimum_route_clusters=4,
    maximum_route_point_share=0.75,
    require_all_leave_one_route_out_count_thresholds=True,
  )


class TestTorqueClusterStability(unittest.TestCase):
  def test_four_balanced_routes_pass_structural_cluster_gate_without_fit_authority(self):
    from openpilot.tools.cyber_autotune.torque_cluster_stability import assess_cluster_stability
    counts = (40, 120, 200, 400, 400, 200, 120, 40)
    groups = tuple(group(str(i), str(i + 4), str(i + 1), counts) for i in range(4))
    result = assess_cluster_stability(groups, policy())
    self.assertEqual(result.status, 'CLUSTER_STABILITY_STRUCTURAL_DIAGNOSTIC')
    self.assertEqual(result.route_cluster_count, 4)
    self.assertEqual(result.source_commit_count, 4)
    self.assertLessEqual(result.maximum_route_point_share, .75)
    self.assertTrue(result.all_leave_one_route_out_count_thresholds_met)
    self.assertTrue(all(row.thresholds_met for row in result.leave_one_route_out))
    self.assertFalse(result.fit_executed)
    self.assertFalse(result.confidence_qualified)
    self.assertFalse(result.candidate_generation_allowed)
    self.assertFalse(result.runtime_accepted)
    self.assertFalse(result.promotable)

  def test_route_is_minimum_cluster_and_same_route_groups_are_aggregated(self):
    from openpilot.tools.cyber_autotune.torque_cluster_stability import assess_cluster_stability
    a = group('1', '5', '1', (20, 60, 100, 200, 200, 100, 60, 20), start=0, end=9)
    b = group('2', '5', '1', (20, 60, 100, 200, 200, 100, 60, 20), start=10, end=19, boundary='CLOCK_RESET')
    c = group('3', '6', '2', (40, 120, 200, 400, 400, 200, 120, 40))
    d = group('4', '7', '3', (40, 120, 200, 400, 400, 200, 120, 40))
    e = group('8', '8', '4', (40, 120, 200, 400, 400, 200, 120, 40))
    result = assess_cluster_stability((a, b, c, d, e), policy())
    self.assertEqual(result.route_cluster_count, 4)
    route = next(row for row in result.routes if row.route_sha256 == '5' * 64)
    self.assertEqual(route.group_count, 2)
    self.assertEqual(route.point_count, sum(a.bucket_counts) + sum(b.bucket_counts))

  def test_dominant_route_blocks_even_when_pooled_counts_are_large(self):
    from openpilot.tools.cyber_autotune.torque_cluster_stability import assess_cluster_stability
    dominant = group('1', '5', '1', (100, 300, 600, 1500, 1500, 1000, 400, 150))
    small = (5, 15, 25, 50, 50, 25, 15, 5)
    groups = (dominant, group('2', '6', '2', small), group('3', '7', '3', small), group('4', '8', '4', small))
    result = assess_cluster_stability(groups, policy())
    self.assertEqual(result.status, 'BLOCKED')
    self.assertIn('ROUTE_POINT_SHARE_DOMINANCE', result.blockers)
    self.assertGreater(result.maximum_route_point_share, .75)

  def test_leave_one_route_out_failure_blocks_before_fit(self):
    from openpilot.tools.cyber_autotune.torque_cluster_stability import assess_cluster_stability
    # Pooled counts meet minima, but every route contributes required outer-negative coverage.
    groups = (
      group('1', '5', '1', (30, 100, 180, 500, 500, 300, 100, 30)),
      group('2', '6', '2', (30, 100, 180, 500, 500, 300, 100, 30)),
      group('3', '7', '3', (30, 100, 180, 500, 500, 300, 100, 30)),
      group('4', '8', '4', (30, 100, 180, 500, 500, 300, 100, 30)),
    )
    result = assess_cluster_stability(groups, policy())
    self.assertEqual(result.status, 'BLOCKED')
    self.assertIn('LEAVE_ONE_ROUTE_OUT_COUNT_COVERAGE_INSUFFICIENT', result.blockers)
    self.assertFalse(result.all_leave_one_route_out_count_thresholds_met)
    self.assertFalse(result.fit_executed)

  def test_too_few_routes_blocks(self):
    from openpilot.tools.cyber_autotune.torque_cluster_stability import assess_cluster_stability
    counts = (100, 300, 500, 1000, 1000, 500, 300, 100)
    groups = tuple(group(str(i), str(i + 5), str(i + 1), counts) for i in range(3))
    result = assess_cluster_stability(groups, policy())
    self.assertEqual(result.status, 'BLOCKED')
    self.assertIn('INSUFFICIENT_ROUTE_CLUSTERS', result.blockers)

  def test_zero_point_routes_do_not_satisfy_minimum_cluster_count(self):
    from openpilot.tools.cyber_autotune.torque_cluster_stability import assess_cluster_stability
    counts = (100, 300, 500, 1000, 1000, 500, 300, 100)
    nonempty = tuple(group(str(i), str(i + 5), str(i + 1), counts) for i in range(3))
    empty = group('9', '9', '9', (0, 0, 0, 0, 0, 0, 0, 0))
    result = assess_cluster_stability(nonempty + (empty,), policy())
    self.assertEqual(result.route_cluster_count, 4)
    self.assertEqual(result.nonempty_route_cluster_count, 3)
    self.assertEqual(result.status, 'BLOCKED')
    self.assertIn('INSUFFICIENT_ROUTE_CLUSTERS', result.blockers)

  def test_policy_and_group_contract_fail_closed(self):
    from openpilot.tools.cyber_autotune.torque_cluster_stability import assess_cluster_stability
    counts = (40, 120, 200, 400, 400, 200, 120, 40)
    groups = tuple(group(str(i), str(i + 4), str(i + 1), counts) for i in range(4))
    bad_policies = (
      dataclasses.replace(policy(), policy_sha256='bad'),
      dataclasses.replace(policy(), minimum_route_clusters=3),
      dataclasses.replace(policy(), maximum_route_point_share=.99),
      dataclasses.replace(policy(), require_all_leave_one_route_out_count_thresholds=False),
    )
    for bad in bad_policies:
      with self.subTest(bad=bad):
        result = assess_cluster_stability(groups, bad)
        self.assertEqual(result.status, 'BLOCKED')
        self.assertIn('INVALID_CLUSTER_POLICY', result.blockers)

    bad_group = dataclasses.replace(groups[0], role='holdout')
    result = assess_cluster_stability((bad_group,) + groups[1:], policy())
    self.assertEqual(result.status, 'BLOCKED')
    self.assertIn('INVALID_CLUSTER_GROUP', result.blockers)


if __name__ == '__main__':
  unittest.main()
