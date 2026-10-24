import dataclasses
import hashlib
import math
import unittest

import numpy as np

SALT = 'cyberpilot-step8-source-split-v1'


def split_role(source_commit):
  digest = hashlib.sha256(f'{SALT}:{source_commit}'.encode()).digest()
  return 'development_evaluation' if int.from_bytes(digest[:4], 'big') % 3 == 0 else 'development_fit'


def source_commits(fit_count=10, evaluation_count=4):
  fit = []
  evaluation = []
  index = 0
  while len(fit) < fit_count or len(evaluation) < evaluation_count:
    commit = hashlib.sha1(f'synthetic-source-{index}'.encode()).hexdigest()
    target = evaluation if split_role(commit) == 'development_evaluation' else fit
    target.append(commit)
    index += 1
  return fit[:fit_count] + evaluation[:evaluation_count]


def policy():
  from openpilot.tools.cyber_autotune.torque_source_statistics import TorqueSourceStatisticalPolicy
  return TorqueSourceStatisticalPolicy(
    policy_sha256='a' * 64,
    split_salt=SALT,
    split_modulus=3,
    evaluation_residue=0,
    minimum_route_points=100,
    minimum_fit_source_clusters=8,
    minimum_evaluation_source_clusters=4,
    minimum_fit_route_clusters=20,
    minimum_evaluation_route_clusters=5,
    maximum_fit_source_point_share=.40,
    maximum_leave_one_source_factor_relative_deviation=.05,
    maximum_leave_one_source_offset_absolute_deviation_mps2=.05,
    maximum_jackknife_95_factor_relative_half_width=.10,
    maximum_evaluation_residual_rmse_mps2=.30,
    maximum_evaluation_absolute_mean_residual_mps2=.10,
    maximum_evaluation_to_fit_rmse_ratio=1.50,
    evaluation_to_fit_rmse_absolute_allowance_mps2=.03,
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


def stable_routes(routes_per_source=3):
  routes = []
  for source_index, source_commit in enumerate(source_commits()):
    for route_index in range(routes_per_source):
      route_sha = hashlib.sha256(f'{source_commit}:{route_index}'.encode()).hexdigest()
      bias = ((source_index + route_index) % 5 - 2) * .001
      routes.append(synthetic_route(route_sha, source_commit, route_bias=bias))
  return tuple(routes)


class TestTorqueSourceStatistics(unittest.TestCase):
  def test_stable_source_disjoint_split_passes_without_candidate_authority(self):
    from openpilot.tools.cyber_autotune.torque_source_statistics import assess_source_statistics
    result = assess_source_statistics(stable_routes(), policy())
    self.assertEqual(result.status, 'SOURCE_DISJOINT_DEVELOPMENT_DIAGNOSTIC_PASS')
    self.assertTrue(result.development_source_disjoint_stability_pass)
    self.assertGreaterEqual(result.fit_source_count, 8)
    self.assertGreaterEqual(result.evaluation_source_count, 4)
    self.assertGreaterEqual(result.fit_route_count, 20)
    self.assertGreaterEqual(result.evaluation_route_count, 5)
    self.assertAlmostEqual(result.fit_estimate.lat_accel_factor, 2., delta=.03)
    self.assertAlmostEqual(result.fit_estimate.lat_accel_offset_mps2, .03, delta=.02)
    self.assertFalse(result.independent_holdout)
    self.assertFalse(result.confidence_qualified)
    self.assertFalse(result.candidate_generation_allowed)
    self.assertFalse(result.runtime_accepted)
    self.assertFalse(result.promotable)

  def test_source_assignments_are_disjoint_and_deterministic(self):
    from openpilot.tools.cyber_autotune.torque_source_statistics import assess_source_statistics
    routes = stable_routes()
    forward = assess_source_statistics(routes, policy())
    reverse = assess_source_statistics(routes[::-1], policy())
    self.assertEqual(forward, reverse)
    self.assertFalse(set(forward.fit_source_commits) & set(forward.evaluation_source_commits))
    self.assertEqual(
      set(forward.fit_source_commits) | set(forward.evaluation_source_commits),
      {route.source_commit for route in routes},
    )

  def test_evaluation_source_distribution_shift_is_rejected(self):
    from openpilot.tools.cyber_autotune.torque_source_statistics import assess_source_statistics
    routes = []
    for source_commit in source_commits():
      slope = 3.0 if split_role(source_commit) == 'development_evaluation' else 2.0
      for route_index in range(3):
        route_sha = hashlib.sha256(f'{source_commit}:{route_index}'.encode()).hexdigest()
        routes.append(synthetic_route(route_sha, source_commit, slope=slope))
    result = assess_source_statistics(tuple(routes), policy())
    self.assertEqual(result.status, 'SOURCE_DISJOINT_DEVELOPMENT_DIAGNOSTIC_REJECTED')
    self.assertTrue(any(blocker.startswith('EVALUATION_') for blocker in result.blockers))
    self.assertFalse(result.development_source_disjoint_stability_pass)
    self.assertFalse(result.candidate_generation_allowed)

  def test_leave_one_source_instability_is_rejected(self):
    from openpilot.tools.cyber_autotune.torque_source_statistics import assess_source_statistics
    routes = list(stable_routes())
    outlier_source = next(
      commit for commit in source_commits()
      if split_role(commit) == 'development_fit'
    )
    for index, route in enumerate(routes):
      if route.source_commit == outlier_source:
        routes[index] = synthetic_route(
          route.route_sha256, route.source_commit, slope=20., noise=0.,
        )
    result = assess_source_statistics(tuple(routes), policy())
    self.assertEqual(result.status, 'SOURCE_DISJOINT_DEVELOPMENT_DIAGNOSTIC_REJECTED')
    self.assertTrue(any(blocker.startswith(('LEAVE_ONE_SOURCE_', 'JACKKNIFE_'))
                        for blocker in result.blockers))

  def test_source_point_share_dominance_is_rejected(self):
    from openpilot.tools.cyber_autotune.torque_source_statistics import assess_source_statistics
    routes = list(stable_routes())
    dominant = next(
      commit for commit in source_commits()
      if split_role(commit) == 'development_fit'
    )
    extra = []
    for index in range(20):
      route_sha = hashlib.sha256(f'dominant:{index}'.encode()).hexdigest()
      extra.append(synthetic_route(route_sha, dominant, points_per_bucket=500))
    result = assess_source_statistics(tuple(routes + extra), policy())
    self.assertEqual(result.status, 'SOURCE_DISJOINT_DEVELOPMENT_DIAGNOSTIC_REJECTED')
    self.assertIn('FIT_SOURCE_POINT_SHARE_DOMINANCE', result.blockers)
  def test_too_few_sources_and_routes_block_before_fit(self):
    from openpilot.tools.cyber_autotune.torque_source_statistics import assess_source_statistics
    routes = []
    for source_commit in source_commits(4, 2):
      route_sha = hashlib.sha256(source_commit.encode()).hexdigest()
      routes.append(synthetic_route(route_sha, source_commit))
    result = assess_source_statistics(tuple(routes), policy())
    self.assertEqual(result.status, 'BLOCKED')
    self.assertIn('INSUFFICIENT_SOURCE_DISJOINT_SPLIT', result.blockers)
    self.assertFalse(result.fit_executed)

  def test_invalid_policy_and_route_statistics_fail_closed(self):
    from openpilot.tools.cyber_autotune.torque_source_statistics import assess_source_statistics
    routes = stable_routes()
    for bad_policy in (
      dataclasses.replace(policy(), policy_sha256='bad'),
      dataclasses.replace(policy(), minimum_fit_source_clusters=7),
      dataclasses.replace(policy(), maximum_fit_source_point_share=.41),
      dataclasses.replace(policy(), maximum_evaluation_residual_rmse_mps2=.31),
    ):
      with self.subTest(bad_policy=bad_policy):
        result = assess_source_statistics(routes, bad_policy)
        self.assertEqual(result.status, 'BLOCKED')
        self.assertIn('INVALID_SOURCE_STATISTICAL_POLICY', result.blockers)

    bad_route = dataclasses.replace(routes[0], gram_xtx=((1., 0.), (0., 1.)))
    result = assess_source_statistics((bad_route,) + routes[1:], policy())
    self.assertEqual(result.status, 'BLOCKED')
    self.assertIn('INVALID_ROUTE_STATISTICS', result.blockers)

  def test_nonfinite_route_is_blocked(self):
    from openpilot.tools.cyber_autotune.torque_source_statistics import assess_source_statistics
    routes = list(stable_routes())
    routes[0] = dataclasses.replace(
      routes[0],
      gram_xtx=((math.nan, 0., 0.), (0., float(routes[0].point_count), 0.), (0., 0., 1.)),
    )
    result = assess_source_statistics(tuple(routes), policy())
    self.assertEqual(result.status, 'BLOCKED')
    self.assertIn('INVALID_ROUTE_STATISTICS', result.blockers)


if __name__ == '__main__':
  unittest.main()
