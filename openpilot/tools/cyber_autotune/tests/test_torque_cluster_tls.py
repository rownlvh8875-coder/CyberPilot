import dataclasses
import hashlib
import unittest

import numpy as np


def sha(value):
  return hashlib.sha256(str(value).encode()).hexdigest()


def route(index, slope=2., offset=.03, weight=1, commit_index=None):
  from openpilot.tools.cyber_autotune.torque_cluster_tls import TorqueRouteGram
  from openpilot.tools.cyber_autotune.torque_gram_tls import TorqueGramInput
  x = np.concatenate((np.linspace(-.44, -.03, 80), np.linspace(.03, .44, 80)))
  y = slope * x + offset + .006 * np.sin(np.arange(len(x)) * .5)
  matrix = np.column_stack((x, np.ones_like(x), y))
  gram = matrix.T @ matrix * weight
  counts = tuple(20 * weight for _ in range(8))
  request = TorqueGramInput(
    point_count=len(x) * weight,
    gram_xtx=tuple(tuple(float(value) for value in row) for row in gram),
    bucket_counts=counts,
    source_sha256=sha(f'gram-{index}-{slope}-{offset}-{weight}'),
  )
  commit = hashlib.sha1(f'commit-{index if commit_index is None else commit_index}'.encode()).hexdigest()
  return TorqueRouteGram(sha(f'route-{index}'), commit, request)


def policy():
  from openpilot.tools.cyber_autotune.torque_cluster_tls import TorqueClusterTLSPolicy
  return TorqueClusterTLSPolicy(
    policy_sha256='9' * 64,
    minimum_nonempty_route_clusters=20,
    minimum_source_commits=10,
    maximum_route_point_share=.25,
    maximum_source_commit_point_share=.40,
    maximum_route_factor_relative_delta=.05,
    maximum_source_factor_relative_delta=.05,
    maximum_route_offset_delta_mps2=.05,
    maximum_source_offset_delta_mps2=.05,
    maximum_factor_jackknife_relative_se=.05,
    maximum_offset_jackknife_se_mps2=.05,
  )


class TestTorqueClusterTLS(unittest.TestCase):
  def test_stable_routes_pass_numerical_stability_without_authority(self):
    from openpilot.tools.cyber_autotune.torque_cluster_tls import assess_cluster_tls
    routes = tuple(route(i, commit_index=i % 10) for i in range(20))
    result = assess_cluster_tls(routes, policy())
    self.assertEqual(result.status, 'CLUSTER_TLS_NUMERICAL_DIAGNOSTIC')
    self.assertEqual(result.route_cluster_count, 20)
    self.assertEqual(result.source_commit_count, 10)
    self.assertTrue(result.stability_gate_passed)
    self.assertEqual(len(result.leave_one_route_out), 20)
    self.assertEqual(len(result.leave_one_source_commit_out), 10)
    self.assertLess(result.maximum_route_factor_relative_delta, .05)
    self.assertLess(result.maximum_source_factor_relative_delta, .05)
    self.assertLess(result.factor_jackknife_relative_se, .05)
    self.assertFalse(result.confidence_qualified)
    self.assertFalse(result.parameter_identification_qualified)
    self.assertFalse(result.candidate_generation_allowed)
    self.assertFalse(result.runtime_accepted)
    self.assertFalse(result.promotable)

  def test_route_factor_and_offset_instability_block(self):
    from openpilot.tools.cyber_autotune.torque_cluster_tls import assess_cluster_tls
    routes = [route(i, commit_index=i % 10) for i in range(19)]
    routes.append(route(19, slope=4.5, offset=.25, weight=6, commit_index=9))
    result = assess_cluster_tls(tuple(routes), policy())
    self.assertEqual(result.status, 'BLOCKED')
    self.assertTrue({'ROUTE_FACTOR_INSTABILITY', 'ROUTE_OFFSET_INSTABILITY'} & set(result.blockers))
    self.assertFalse(result.stability_gate_passed)
    self.assertFalse(result.candidate_generation_allowed)

  def test_source_commit_instability_block(self):
    from openpilot.tools.cyber_autotune.torque_cluster_tls import assess_cluster_tls
    routes = []
    for i in range(20):
      bad_commit = i in (18, 19)
      routes.append(route(i, slope=4.2 if bad_commit else 2., offset=.18 if bad_commit else .03,
                          weight=3 if bad_commit else 1, commit_index=9 if bad_commit else i % 9))
    result = assess_cluster_tls(tuple(routes), policy())
    self.assertEqual(result.status, 'BLOCKED')
    self.assertTrue({'SOURCE_FACTOR_INSTABILITY', 'SOURCE_OFFSET_INSTABILITY'} & set(result.blockers))
    self.assertFalse(result.candidate_generation_allowed)

  def test_route_and_source_dominance_block_before_fit(self):
    from openpilot.tools.cyber_autotune.torque_cluster_tls import assess_cluster_tls
    dominant = tuple([route(0, weight=7, commit_index=0)] + [route(i, commit_index=i % 10) for i in range(1, 20)])
    result = assess_cluster_tls(dominant, policy())
    self.assertEqual(result.status, 'BLOCKED')
    self.assertIn('ROUTE_POINT_SHARE_DOMINANCE', result.blockers)
    self.assertIsNone(result.pooled_estimate)

    source_dominant = tuple(route(i, commit_index=0 if i < 9 else i) for i in range(20))
    result = assess_cluster_tls(source_dominant, policy())
    self.assertEqual(result.status, 'BLOCKED')
    self.assertIn('SOURCE_COMMIT_POINT_SHARE_DOMINANCE', result.blockers)
    self.assertIsNone(result.pooled_estimate)

  def test_insufficient_clusters_and_bad_policy_block(self):
    from openpilot.tools.cyber_autotune.torque_cluster_tls import assess_cluster_tls
    routes = tuple(route(i, commit_index=i % 5) for i in range(19))
    result = assess_cluster_tls(routes, policy())
    self.assertEqual(result.status, 'BLOCKED')
    self.assertIn('INSUFFICIENT_ROUTE_CLUSTERS', result.blockers)

    routes = tuple(route(i, commit_index=i % 5) for i in range(20))
    result = assess_cluster_tls(routes, policy())
    self.assertEqual(result.status, 'BLOCKED')
    self.assertIn('INSUFFICIENT_SOURCE_COMMITS', result.blockers)

    bad_policies = (
      dataclasses.replace(policy(), policy_sha256='bad'),
      dataclasses.replace(policy(), minimum_nonempty_route_clusters=10),
      dataclasses.replace(policy(), minimum_source_commits=5),
      dataclasses.replace(policy(), maximum_route_point_share=.5),
      dataclasses.replace(policy(), maximum_factor_jackknife_relative_se=.5),
    )
    valid_routes = tuple(route(i, commit_index=i % 10) for i in range(20))
    for bad in bad_policies:
      with self.subTest(bad=bad):
        result = assess_cluster_tls(valid_routes, bad)
        self.assertEqual(result.status, 'BLOCKED')
        self.assertIn('INVALID_CLUSTER_TLS_POLICY', result.blockers)

  def test_duplicate_route_invalid_group_and_unidentifiable_omission_block(self):
    from openpilot.tools.cyber_autotune.torque_cluster_tls import assess_cluster_tls
    routes = [route(i, commit_index=i % 10) for i in range(20)]
    routes[1] = dataclasses.replace(routes[1], route_sha256=routes[0].route_sha256)
    result = assess_cluster_tls(tuple(routes), policy())
    self.assertEqual(result.status, 'BLOCKED')
    self.assertIn('DUPLICATE_ROUTE_ID', result.blockers)

    routes = [route(i, commit_index=i % 10) for i in range(20)]
    bad_gram = dataclasses.replace(routes[0].gram, source_sha256='bad')
    routes[0] = dataclasses.replace(routes[0], gram=bad_gram)
    result = assess_cluster_tls(tuple(routes), policy())
    self.assertEqual(result.status, 'BLOCKED')
    self.assertIn('INVALID_ROUTE_GRAM', result.blockers)
    self.assertIsNone(result.pooled_estimate)

  def test_result_is_repeatable_and_estimates_remain_diagnostic(self):
    from openpilot.tools.cyber_autotune.torque_cluster_tls import assess_cluster_tls
    routes = tuple(route(i, commit_index=i % 10) for i in range(20))
    result = assess_cluster_tls(routes, policy())
    self.assertEqual(result, assess_cluster_tls(routes[::-1], policy()))
    self.assertIsNotNone(result.pooled_estimate)
    self.assertGreater(result.pooled_estimate.lat_accel_factor, 0.)
    self.assertTrue(result.numerical_fit_executed)
    self.assertFalse(result.confidence_qualified)


if __name__ == '__main__':
  unittest.main()
