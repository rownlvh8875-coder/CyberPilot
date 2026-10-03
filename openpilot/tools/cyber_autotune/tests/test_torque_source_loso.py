import dataclasses
import hashlib
import unittest

import numpy as np


def policy():
  from openpilot.tools.cyber_autotune.torque_source_loso import TorqueSourceLosoPolicy
  return TorqueSourceLosoPolicy(
    policy_sha256='a' * 64,
    minimum_route_points=100,
    minimum_source_clusters=10,
    maximum_source_point_share=.40,
    maximum_fold_factor_relative_deviation=.05,
    maximum_fold_offset_absolute_deviation_mps2=.05,
    maximum_fold_evaluation_rmse_mps2=.30,
    maximum_fold_evaluation_absolute_mean_residual_mps2=.10,
    maximum_fold_evaluation_to_fit_rmse_ratio=1.50,
    evaluation_to_fit_rmse_absolute_allowance_mps2=.03,
    require_all_source_folds_pass=True,
  )


def synthetic_route(route_sha, source_commit, slope=2., offset=.03,
                    noise=.01, route_bias=0., points_per_bucket=100):
  from openpilot.tools.cyber_autotune.torque_route_statistics import TorqueRouteStatistics
  bounds = ((-.5, -.3), (-.3, -.2), (-.2, -.1), (-.1, 0.),
            (0., .1), (.1, .2), (.2, .3), (.3, .5))
  xs = []
  for lower, upper in bounds:
    xs.extend(np.linspace(lower + .001, upper - .001, points_per_bucket))
  x = np.asarray(xs, dtype=np.float64)
  phase = int(route_sha[:8], 16) % 101
  y = slope * x + offset + route_bias + noise * np.sin(np.arange(len(x)) + phase)
  matrix = np.column_stack((x, np.ones(len(x)), y))
  gram = tuple(tuple(float(value) for value in row) for row in matrix.T @ matrix)
  counts = (points_per_bucket,) * 8
  return TorqueRouteStatistics(
    route_sha256=route_sha,
    source_commit=source_commit,
    point_manifest_sha256=hashlib.sha256(route_sha.encode()).hexdigest(),
    point_count=len(x),
    bucket_counts=counts,
    gram_xtx=gram,
  )


def stable_routes(source_count=12, routes_per_source=2):
  routes = []
  for source_index in range(source_count):
    source = hashlib.sha1(f'loso-source-{source_index}'.encode()).hexdigest()
    for route_index in range(routes_per_source):
      route_sha = hashlib.sha256(f'{source}:{route_index}'.encode()).hexdigest()
      bias = ((source_index + route_index) % 5 - 2) * .001
      routes.append(synthetic_route(route_sha, source, route_bias=bias))
  return tuple(routes)


class TestTorqueSourceLoso(unittest.TestCase):
  def test_stable_source_loso_passes_without_authority(self):
    from openpilot.tools.cyber_autotune.torque_source_loso import assess_source_loso
    result = assess_source_loso(stable_routes(), policy())
    self.assertEqual(result.status, 'SOURCE_LOSO_DEVELOPMENT_DIAGNOSTIC_PASS')
    self.assertTrue(result.all_source_folds_pass)
    self.assertEqual(result.source_count, 12)
    self.assertEqual(len(result.folds), 12)
    self.assertTrue(result.fit_executed)
    self.assertFalse(result.independent_holdout)
    self.assertFalse(result.confidence_qualified)
    self.assertFalse(result.candidate_generation_allowed)
    self.assertFalse(result.runtime_accepted)
    self.assertFalse(result.promotable)

  def test_result_is_order_invariant(self):
    from openpilot.tools.cyber_autotune.torque_source_loso import assess_source_loso
    routes = stable_routes()
    self.assertEqual(
      assess_source_loso(routes, policy()),
      assess_source_loso(routes[::-1], policy()),
    )

  def test_shifted_source_is_rejected_on_held_out_fold(self):
    from openpilot.tools.cyber_autotune.torque_source_loso import assess_source_loso
    routes = list(stable_routes())
    shifted_source = routes[0].source_commit
    for index, route in enumerate(routes):
      if route.source_commit == shifted_source:
        routes[index] = synthetic_route(
          route.route_sha256, route.source_commit, slope=3., noise=.01,
        )
    result = assess_source_loso(tuple(routes), policy())
    self.assertEqual(result.status, 'SOURCE_LOSO_DEVELOPMENT_DIAGNOSTIC_REJECTED')
    fold = next(row for row in result.folds if row.evaluation_source_commit == shifted_source)
    self.assertFalse(fold.fold_pass)
    self.assertTrue(any(blocker.startswith('EVALUATION_') for blocker in fold.blockers))
  def test_source_point_share_dominance_is_rejected(self):
    from openpilot.tools.cyber_autotune.torque_source_loso import assess_source_loso
    routes = list(stable_routes())
    dominant_source = routes[0].source_commit
    for index in range(20):
      route_sha = hashlib.sha256(f'dominant-loso:{index}'.encode()).hexdigest()
      routes.append(synthetic_route(
        route_sha, dominant_source, points_per_bucket=500,
      ))
    result = assess_source_loso(tuple(routes), policy())
    self.assertEqual(result.status, 'SOURCE_LOSO_DEVELOPMENT_DIAGNOSTIC_REJECTED')
    self.assertIn('SOURCE_POINT_SHARE_DOMINANCE', result.blockers)
    self.assertFalse(result.fit_executed)

  def test_too_few_sources_blocks_before_fit(self):
    from openpilot.tools.cyber_autotune.torque_source_loso import assess_source_loso
    result = assess_source_loso(stable_routes(source_count=8), policy())
    self.assertEqual(result.status, 'BLOCKED')
    self.assertIn('INSUFFICIENT_SOURCE_CLUSTERS', result.blockers)
    self.assertFalse(result.fit_executed)

  def test_invalid_policy_and_routes_fail_closed(self):
    from openpilot.tools.cyber_autotune.torque_source_loso import assess_source_loso
    routes = stable_routes()
    for bad_policy in (
      dataclasses.replace(policy(), policy_sha256='bad'),
      dataclasses.replace(policy(), minimum_source_clusters=9),
      dataclasses.replace(policy(), maximum_source_point_share=.41),
      dataclasses.replace(policy(), require_all_source_folds_pass=False),
    ):
      with self.subTest(bad_policy=bad_policy):
        result = assess_source_loso(routes, bad_policy)
        self.assertEqual(result.status, 'BLOCKED')
        self.assertIn('INVALID_SOURCE_LOSO_POLICY', result.blockers)

    bad_route = dataclasses.replace(routes[0], gram_xtx=((1., 0.), (0., 1.)))
    result = assess_source_loso((bad_route,) + routes[1:], policy())
    self.assertEqual(result.status, 'BLOCKED')
    self.assertIn('INVALID_ROUTE_STATISTICS', result.blockers)


if __name__ == '__main__':
  unittest.main()
