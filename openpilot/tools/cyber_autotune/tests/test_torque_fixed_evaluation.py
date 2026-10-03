import dataclasses
import hashlib
import unittest

import numpy as np


def route(index, slope=4.0, offset=-0.18, noise=0.01, points_per_bucket=100):
  from openpilot.tools.cyber_autotune.torque_route_statistics import TorqueRouteStatistics
  bounds = ((-.5, -.3), (-.3, -.2), (-.2, -.1), (-.1, 0.),
            (0., .1), (.1, .2), (.2, .3), (.3, .5))
  x = np.concatenate([np.linspace(a + .001, b - .001, points_per_bucket) for a, b in bounds])
  y = slope * x + offset + noise * np.sin(np.arange(len(x)) + index)
  matrix = np.column_stack((x, np.ones(len(x)), y))
  gram = tuple(tuple(float(value) for value in row) for row in matrix.T @ matrix)
  return TorqueRouteStatistics(
    route_sha256=hashlib.sha256(f'eval-route-{index}'.encode()).hexdigest(),
    source_commit=f'{index % 5 + 1:040x}',
    point_manifest_sha256=hashlib.sha256(f'points-{index}'.encode()).hexdigest(),
    point_count=len(x), bucket_counts=(points_per_bucket,) * 8, gram_xtx=gram,
  )


def policy():
  from openpilot.tools.cyber_autotune.torque_fixed_evaluation import FixedEvaluationPolicy
  return FixedEvaluationPolicy(
    policy_sha256='a' * 64, minimum_route_points=100,
    minimum_route_clusters=5, minimum_source_commits=4,
    minimum_total_points=4000,
    minimum_bucket_points=(100, 300, 500, 500, 500, 500, 300, 100),
    maximum_route_balanced_rmse_mps2=.30,
    maximum_absolute_route_balanced_mean_residual_mps2=.10,
  )


def models():
  from openpilot.tools.cyber_autotune.torque_fixed_evaluation import FixedTorqueModel
  return (
    FixedTorqueModel('good', 4.0, -0.18, 'b' * 64),
    FixedTorqueModel('biased', 3.0, 0.20, 'c' * 64),
  )


class TestFixedTorqueEvaluation(unittest.TestCase):
  def test_all_fixed_models_are_reported_without_candidate_selection(self):
    from openpilot.tools.cyber_autotune.torque_fixed_evaluation import evaluate_fixed_models
    routes = tuple(route(i) for i in range(10))
    result = evaluate_fixed_models(routes, models(), policy())
    self.assertEqual(result.status, 'RETROSPECTIVE_FIXED_MODEL_DIAGNOSTIC')
    self.assertEqual(tuple(row.name for row in result.models), ('biased', 'good'))
    observed = {row.name: row for row in result.models}
    self.assertTrue(observed['good'].absolute_gate_passed)
    self.assertFalse(observed['biased'].absolute_gate_passed)
    self.assertIsNone(result.selected_model)
    self.assertTrue(result.evaluation_executed)
    self.assertFalse(result.confidence_qualified)
    self.assertFalse(result.candidate_generation_allowed)
    self.assertFalse(result.runtime_accepted)
    self.assertFalse(result.promotable)

  def test_order_is_canonical_and_repeatable(self):
    from openpilot.tools.cyber_autotune.torque_fixed_evaluation import evaluate_fixed_models
    routes = tuple(route(i) for i in range(10))
    forward = evaluate_fixed_models(routes, models(), policy())
    reverse = evaluate_fixed_models(routes[::-1], models()[::-1], policy())
    self.assertEqual(forward, reverse)
    self.assertEqual(forward.input_sha256, reverse.input_sha256)

  def test_insufficient_routes_sources_and_coverage_block_before_evaluation(self):
    from openpilot.tools.cyber_autotune.torque_fixed_evaluation import evaluate_fixed_models
    too_few = tuple(route(i) for i in range(4))
    result = evaluate_fixed_models(too_few, models(), policy())
    self.assertEqual(result.status, 'BLOCKED')
    self.assertIn('INSUFFICIENT_EVALUATION_ROUTES', result.blockers)
    self.assertFalse(result.evaluation_executed)

    one_source = tuple(dataclasses.replace(route(i), source_commit='1' * 40) for i in range(6))
    result = evaluate_fixed_models(one_source, models(), policy())
    self.assertEqual(result.status, 'BLOCKED')
    self.assertIn('INSUFFICIENT_EVALUATION_SOURCES', result.blockers)

    sparse = tuple(route(i, points_per_bucket=20) for i in range(6))
    result = evaluate_fixed_models(sparse, models(), policy())
    self.assertEqual(result.status, 'BLOCKED')
    self.assertIn('EVALUATION_STRUCTURAL_COVERAGE_INSUFFICIENT', result.blockers)

  def test_low_point_routes_are_excluded_before_counts(self):
    from openpilot.tools.cyber_autotune.torque_fixed_evaluation import evaluate_fixed_models
    routes = [route(i) for i in range(10)]
    routes[0] = dataclasses.replace(
      routes[0], point_count=80, bucket_counts=(10,) * 8,
      gram_xtx=tuple(tuple(value * .1 for value in row) for row in routes[0].gram_xtx),
    )
    result = evaluate_fixed_models(tuple(routes), models(), policy())
    self.assertEqual(result.excluded_low_point_route_count, 1)
    self.assertEqual(result.eligible_route_count, 9)
    self.assertFalse(result.candidate_generation_allowed)

  def test_invalid_policy_model_and_route_fail_closed(self):
    from openpilot.tools.cyber_autotune.torque_fixed_evaluation import evaluate_fixed_models
    routes = tuple(route(i) for i in range(10))
    bad_policies = (
      dataclasses.replace(policy(), policy_sha256='bad'),
      dataclasses.replace(policy(), minimum_route_clusters=4),
      dataclasses.replace(policy(), maximum_route_balanced_rmse_mps2=.31),
    )
    for bad in bad_policies:
      with self.subTest(bad=bad):
        result = evaluate_fixed_models(routes, models(), bad)
        self.assertEqual(result.status, 'BLOCKED')
        self.assertIn('INVALID_EVALUATION_POLICY', result.blockers)

    bad_model = dataclasses.replace(models()[0], lat_accel_factor=-1.)
    result = evaluate_fixed_models(routes, (bad_model,), policy())
    self.assertEqual(result.status, 'BLOCKED')
    self.assertIn('INVALID_FIXED_MODEL', result.blockers)

    bad_route = dataclasses.replace(routes[0], gram_xtx=((1., 0.), (0., 1.)))
    result = evaluate_fixed_models((bad_route,) + routes[1:], models(), policy())
    self.assertEqual(result.status, 'BLOCKED')
    self.assertIn('INVALID_EVALUATION_ROUTE', result.blockers)


if __name__ == '__main__':
  unittest.main()
