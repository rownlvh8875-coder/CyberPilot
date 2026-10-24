import dataclasses
import hashlib
import math
import unittest

import numpy as np

SALT = 'cyberpilot-step8-route-split-v1'


def split_role(route_sha):
  value = hashlib.sha256(f'{SALT}:{route_sha}'.encode()).digest()
  return 'development_evaluation' if int.from_bytes(value[:4], 'big') % 5 == 0 else 'development_fit'


def route_hashes(fit_count=25, evaluation_count=6):
  fit = []
  evaluation = []
  index = 0
  while len(fit) < fit_count or len(evaluation) < evaluation_count:
    route = hashlib.sha256(f'synthetic-route-{index}'.encode()).hexdigest()
    target = evaluation if split_role(route) == 'development_evaluation' else fit
    target.append(route)
    index += 1
  return fit[:fit_count] + evaluation[:evaluation_count]


def policy():
  from openpilot.tools.cyber_autotune.torque_route_statistics import TorqueRouteStatisticalPolicy
  return TorqueRouteStatisticalPolicy(
    policy_sha256='a' * 64,
    split_salt=SALT,
    split_modulus=5,
    evaluation_residue=0,
    minimum_route_points=100,
    minimum_fit_route_clusters=20,
    minimum_evaluation_route_clusters=5,
    maximum_leave_one_route_factor_relative_deviation=.20,
    maximum_leave_one_route_offset_absolute_deviation_mps2=.10,
    maximum_jackknife_95_factor_relative_half_width=.20,
    maximum_evaluation_residual_rmse_mps2=.30,
    maximum_evaluation_absolute_mean_residual_mps2=.10,
    maximum_evaluation_to_fit_rmse_ratio=1.50,
    evaluation_to_fit_rmse_absolute_allowance_mps2=.03,
  )


def synthetic_route(route_sha, slope=2., offset=.03, noise=.01, route_bias=0., points_per_bucket=100):
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
  gram = tuple(tuple(float(value) for value in row) for row in (matrix.T @ matrix))
  counts = (points_per_bucket,) * 8
  return TorqueRouteStatistics(
    route_sha256=route_sha,
    source_commit='1' * 40,
    point_manifest_sha256=hashlib.sha256(route_sha.encode()).hexdigest(),
    point_count=len(x),
    bucket_counts=counts,
    gram_xtx=gram,
  )


def stable_routes():
  routes = []
  for index, route_sha in enumerate(route_hashes()):
    bias = ((index % 5) - 2) * .001
    routes.append(synthetic_route(route_sha, route_bias=bias))
  return tuple(routes)


class TestTorqueRouteStatistics(unittest.TestCase):
  def test_stable_route_balanced_fit_passes_without_candidate_authority(self):
    from openpilot.tools.cyber_autotune.torque_route_statistics import assess_route_statistics
    result = assess_route_statistics(stable_routes(), policy())
    self.assertEqual(result.status, 'DEVELOPMENT_STATISTICAL_DIAGNOSTIC_PASS')
    self.assertTrue(result.development_statistical_stability_pass)
    self.assertGreaterEqual(result.fit_route_count, 20)
    self.assertGreaterEqual(result.evaluation_route_count, 5)
    self.assertAlmostEqual(result.fit_estimate.lat_accel_factor, 2., delta=.03)
    self.assertAlmostEqual(result.fit_estimate.lat_accel_offset_mps2, .03, delta=.02)
    self.assertTrue(result.fit_executed)
    self.assertFalse(result.confidence_qualified)
    self.assertFalse(result.candidate_generation_allowed)
    self.assertFalse(result.runtime_accepted)
    self.assertFalse(result.promotable)

  def test_order_and_split_are_deterministic(self):
    from openpilot.tools.cyber_autotune.torque_route_statistics import assess_route_statistics
    routes = stable_routes()
    forward = assess_route_statistics(routes, policy())
    reverse = assess_route_statistics(routes[::-1], policy())
    self.assertEqual(forward, reverse)
    self.assertEqual(forward.input_sha256, reverse.input_sha256)

  def test_evaluation_distribution_shift_is_rejected(self):
    from openpilot.tools.cyber_autotune.torque_route_statistics import assess_route_statistics
    routes = []
    for route_sha in route_hashes():
      slope = 3.0 if split_role(route_sha) == 'development_evaluation' else 2.0
      routes.append(synthetic_route(route_sha, slope=slope))
    result = assess_route_statistics(tuple(routes), policy())
    self.assertEqual(result.status, 'DEVELOPMENT_STATISTICAL_DIAGNOSTIC_REJECTED')
    self.assertTrue(any(blocker.startswith('EVALUATION_') for blocker in result.blockers))
    self.assertFalse(result.development_statistical_stability_pass)
    self.assertFalse(result.candidate_generation_allowed)

  def test_leave_one_route_out_instability_is_rejected(self):
    from openpilot.tools.cyber_autotune.torque_route_statistics import assess_route_statistics
    routes = list(stable_routes())
    outlier = next(i for i, route in enumerate(routes) if split_role(route.route_sha256) == 'development_fit')
    routes[outlier] = synthetic_route(routes[outlier].route_sha256, slope=20., noise=0.)
    result = assess_route_statistics(tuple(routes), policy())
    self.assertEqual(result.status, 'DEVELOPMENT_STATISTICAL_DIAGNOSTIC_REJECTED')
    self.assertTrue(any(blocker.startswith(('LEAVE_ONE_ROUTE_', 'JACKKNIFE_'))
                        for blocker in result.blockers))

  def test_too_few_eligible_routes_blocks_before_fit(self):
    from openpilot.tools.cyber_autotune.torque_route_statistics import assess_route_statistics
    routes = tuple(synthetic_route(route) for route in route_hashes(10, 2))
    result = assess_route_statistics(routes, policy())
    self.assertEqual(result.status, 'BLOCKED')
    self.assertIn('INSUFFICIENT_SPLIT_ROUTE_CLUSTERS', result.blockers)
    self.assertFalse(result.fit_executed)

  def test_low_point_routes_are_excluded_not_promoted(self):
    from openpilot.tools.cyber_autotune.torque_route_statistics import assess_route_statistics
    routes = list(stable_routes())
    low = dataclasses.replace(routes[0], point_count=80,
                              bucket_counts=(10, 10, 10, 10, 10, 10, 10, 10),
                              gram_xtx=tuple(tuple(value * .1 for value in row) for row in routes[0].gram_xtx))
    routes[0] = low
    result = assess_route_statistics(tuple(routes), policy())
    self.assertEqual(result.excluded_low_point_route_count, 1)
    self.assertFalse(result.candidate_generation_allowed)

  def test_invalid_policy_and_statistics_fail_closed(self):
    from openpilot.tools.cyber_autotune.torque_route_statistics import assess_route_statistics
    routes = stable_routes()
    for bad_policy in (
      dataclasses.replace(policy(), policy_sha256='bad'),
      dataclasses.replace(policy(), minimum_fit_route_clusters=19),
      dataclasses.replace(policy(), maximum_evaluation_residual_rmse_mps2=.31),
    ):
      result = assess_route_statistics(routes, bad_policy)
      self.assertEqual(result.status, 'BLOCKED')
      self.assertIn('INVALID_STATISTICAL_POLICY', result.blockers)

    bad_route = dataclasses.replace(routes[0], gram_xtx=((1., 0.), (0., 1.)))
    result = assess_route_statistics((bad_route,) + routes[1:], policy())
    self.assertEqual(result.status, 'BLOCKED')
    self.assertIn('INVALID_ROUTE_STATISTICS', result.blockers)

  def test_nonfinite_and_nonpositive_fit_are_blocked(self):
    from openpilot.tools.cyber_autotune.torque_route_statistics import assess_route_statistics
    routes = list(stable_routes())
    broken = dataclasses.replace(routes[0],
      gram_xtx=((math.nan, 0., 0.), (0., float(routes[0].point_count), 0.), (0., 0., 1.)))
    routes[0] = broken
    result = assess_route_statistics(tuple(routes), policy())
    self.assertEqual(result.status, 'BLOCKED')
    self.assertIn('INVALID_ROUTE_STATISTICS', result.blockers)


if __name__ == '__main__':
  unittest.main()
