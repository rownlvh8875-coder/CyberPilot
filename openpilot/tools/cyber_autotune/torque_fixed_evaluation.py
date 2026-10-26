"""Evaluate predeclared torque models on route-balanced compact statistics.

This module performs no fitting, model selection, candidate generation, profile
mutation, runtime control, CAN access, or promotion.
"""
from dataclasses import asdict, dataclass, field
import hashlib
import json
import math
import re

import numpy as np

from openpilot.tools.cyber_autotune.contracts import finite_number, is_sha256
from openpilot.tools.cyber_autotune.torque_aggregation import MIN_BUCKET_POINTS
from openpilot.tools.cyber_autotune.torque_route_statistics import TorqueRouteStatistics

MIN_ROUTE_POINTS = 100
MIN_ROUTE_CLUSTERS = 5
MIN_SOURCE_COMMITS = 4
MIN_TOTAL_POINTS = 4000
MAX_ROUTE_BALANCED_RMSE_MPS2 = .30
MAX_ABSOLUTE_ROUTE_BALANCED_MEAN_RESIDUAL_MPS2 = .10
AUTHORITY_BLOCKERS = (
  'CONFIDENCE_QUALIFICATION_NOT_GRANTED',
  'CANDIDATE_GENERATION_NOT_AUTHORIZED',
  'QUALIFIED_REPLAY_NOT_RUN',
)


@dataclass(frozen=True)
class FixedTorqueModel:
  name: str
  lat_accel_factor: float
  lat_accel_offset_mps2: float
  source_result_sha256: str


@dataclass(frozen=True)
class FixedEvaluationPolicy:
  policy_sha256: str
  minimum_route_points: int
  minimum_route_clusters: int
  minimum_source_commits: int
  minimum_total_points: int
  minimum_bucket_points: tuple[int, ...]
  maximum_route_balanced_rmse_mps2: float
  maximum_absolute_route_balanced_mean_residual_mps2: float


@dataclass(frozen=True)
class FixedModelEvaluation:
  name: str
  lat_accel_factor: float
  lat_accel_offset_mps2: float
  source_result_sha256: str
  route_balanced_residual_rmse_mps2: float
  route_balanced_mean_residual_mps2: float
  absolute_gate_passed: bool


@dataclass(frozen=True)
class FixedEvaluationReport:
  status: str
  blockers: tuple[str, ...]
  input_sha256: str | None = None
  eligible_route_count: int = 0
  source_commit_count: int = 0
  excluded_low_point_route_count: int = 0
  point_count: int = 0
  bucket_counts: tuple[int, ...] = ()
  models: tuple[FixedModelEvaluation, ...] = ()
  selected_model: str | None = None
  evaluation_executed: bool = False
  confidence_qualified: bool = field(default=False, init=False)
  candidate_generation_allowed: bool = field(default=False, init=False)
  runtime_accepted: bool = field(default=False, init=False)
  promotable: bool = field(default=False, init=False)


def _valid_policy(policy):
  return (
    type(policy) is FixedEvaluationPolicy and
    is_sha256(policy.policy_sha256) and
    policy.minimum_route_points == MIN_ROUTE_POINTS and
    policy.minimum_route_clusters == MIN_ROUTE_CLUSTERS and
    policy.minimum_source_commits == MIN_SOURCE_COMMITS and
    policy.minimum_total_points == MIN_TOTAL_POINTS and
    policy.minimum_bucket_points == MIN_BUCKET_POINTS and
    policy.maximum_route_balanced_rmse_mps2 == MAX_ROUTE_BALANCED_RMSE_MPS2 and
    policy.maximum_absolute_route_balanced_mean_residual_mps2 ==
      MAX_ABSOLUTE_ROUTE_BALANCED_MEAN_RESIDUAL_MPS2
  )


def _valid_model(model):
  return (
    type(model) is FixedTorqueModel and
    type(model.name) is str and re.fullmatch(r'[a-z][a-z0-9_]{0,63}', model.name) is not None and
    finite_number(model.lat_accel_factor) and model.lat_accel_factor > 0 and
    finite_number(model.lat_accel_offset_mps2) and
    is_sha256(model.source_result_sha256)
  )


def _valid_route(route):
  if (type(route) is not TorqueRouteStatistics or not is_sha256(route.route_sha256) or
      not re.fullmatch(r'[0-9a-f]{40}', route.source_commit) or
      not is_sha256(route.point_manifest_sha256) or
      type(route.point_count) is not int or route.point_count < 0 or
      type(route.bucket_counts) is not tuple or len(route.bucket_counts) != 8 or
      any(type(count) is not int or count < 0 for count in route.bucket_counts) or
      sum(route.bucket_counts) != route.point_count):
    return False
  if (type(route.gram_xtx) is not tuple or len(route.gram_xtx) != 3 or
      any(type(row) is not tuple or len(row) != 3 for row in route.gram_xtx)):
    return False
  values = tuple(value for row in route.gram_xtx for value in row)
  if any(not finite_number(value) for value in values):
    return False
  gram = np.asarray(route.gram_xtx, dtype=np.float64)
  tolerance = 1e-9 * max(1.0, float(route.point_count), float(np.max(np.abs(gram))))
  if not np.allclose(gram, gram.T, rtol=1e-12, atol=tolerance):
    return False
  if abs(float(gram[1, 1]) - route.point_count) > tolerance:
    return False
  try:
    eigenvalues = np.linalg.eigvalsh(gram)
  except np.linalg.LinAlgError:
    return False
  return bool(np.min(eigenvalues) >= -tolerance)


def _blocked(reason, digest=None, eligible=0, sources=0, excluded=0,
             points=0, buckets=()):
  return FixedEvaluationReport(
    status='BLOCKED', blockers=(reason,), input_sha256=digest,
    eligible_route_count=eligible, source_commit_count=sources,
    excluded_low_point_route_count=excluded, point_count=points,
    bucket_counts=buckets,
  )


def _metrics(routes, model):
  vector = np.array([
    -model.lat_accel_factor, -model.lat_accel_offset_mps2, 1.0,
  ], dtype=np.float64)
  route_mse = []
  route_mean = []
  for route in routes:
    gram = np.asarray(route.gram_xtx, dtype=np.float64)
    route_mse.append(float(vector @ gram @ vector / route.point_count))
    sum_x = float(gram[0, 1])
    sum_y = float(gram[1, 2])
    route_mean.append((sum_y - model.lat_accel_factor * sum_x -
                       model.lat_accel_offset_mps2 * route.point_count) / route.point_count)
  mse = max(0.0, float(np.mean(route_mse)))
  rmse = math.sqrt(mse)
  mean_residual = float(np.mean(route_mean))
  return rmse, mean_residual


def _input_digest(routes, models, policy):
  payload = {
    'algorithm': 'equal-route-fixed-model-residual-v1',
    'policy': asdict(policy),
    'models': [asdict(model) for model in models],
    'routes': [asdict(route) for route in routes],
  }
  return hashlib.sha256(json.dumps(
    payload, sort_keys=True, separators=(',', ':'), allow_nan=False,
  ).encode()).hexdigest()


def evaluate_fixed_models(routes: tuple[TorqueRouteStatistics, ...],
                          models: tuple[FixedTorqueModel, ...],
                          policy: FixedEvaluationPolicy) -> FixedEvaluationReport:
  """Evaluate every predeclared model without selecting or promoting one."""
  if not _valid_policy(policy):
    return _blocked('INVALID_EVALUATION_POLICY')
  if (type(routes) is not tuple or not routes or
      any(not _valid_route(route) for route in routes)):
    return _blocked('INVALID_EVALUATION_ROUTE')
  if (type(models) is not tuple or not models or
      any(not _valid_model(model) for model in models)):
    return _blocked('INVALID_FIXED_MODEL')
  if len({route.route_sha256 for route in routes}) != len(routes):
    return _blocked('DUPLICATE_ROUTE_ID')
  if len({model.name for model in models}) != len(models):
    return _blocked('DUPLICATE_MODEL_NAME')

  ordered_routes = tuple(sorted(routes, key=lambda route: route.route_sha256))
  ordered_models = tuple(sorted(models, key=lambda model: model.name))
  digest = _input_digest(ordered_routes, ordered_models, policy)
  eligible = tuple(route for route in ordered_routes if route.point_count >= policy.minimum_route_points)
  excluded = len(ordered_routes) - len(eligible)
  sources = len({route.source_commit for route in eligible})
  buckets = tuple(sum(route.bucket_counts[i] for route in eligible) for i in range(8))
  points = sum(buckets)
  if len(eligible) < policy.minimum_route_clusters:
    return _blocked('INSUFFICIENT_EVALUATION_ROUTES', digest, len(eligible), sources, excluded, points, buckets)
  if sources < policy.minimum_source_commits:
    return _blocked('INSUFFICIENT_EVALUATION_SOURCES', digest, len(eligible), sources, excluded, points, buckets)
  deficits = tuple(max(0, minimum - count) for count, minimum in zip(
    buckets, policy.minimum_bucket_points, strict=True,
  ))
  if points < policy.minimum_total_points or any(deficits):
    return _blocked('EVALUATION_STRUCTURAL_COVERAGE_INSUFFICIENT',
                    digest, len(eligible), sources, excluded, points, buckets)

  evaluations = []
  rejected = []
  for model in ordered_models:
    rmse, mean_residual = _metrics(eligible, model)
    if not finite_number(rmse) or not finite_number(mean_residual):
      return _blocked('NONFINITE_EVALUATION_METRICS',
                      digest, len(eligible), sources, excluded, points, buckets)
    passed = (
      rmse <= policy.maximum_route_balanced_rmse_mps2 and
      abs(mean_residual) <= policy.maximum_absolute_route_balanced_mean_residual_mps2
    )
    if not passed:
      rejected.append(f'MODEL_ABSOLUTE_GATE_REJECTED:{model.name}')
    evaluations.append(FixedModelEvaluation(
      name=model.name,
      lat_accel_factor=model.lat_accel_factor,
      lat_accel_offset_mps2=model.lat_accel_offset_mps2,
      source_result_sha256=model.source_result_sha256,
      route_balanced_residual_rmse_mps2=rmse,
      route_balanced_mean_residual_mps2=mean_residual,
      absolute_gate_passed=passed,
    ))

  return FixedEvaluationReport(
    status='RETROSPECTIVE_FIXED_MODEL_DIAGNOSTIC',
    blockers=tuple(rejected) + AUTHORITY_BLOCKERS,
    input_sha256=digest,
    eligible_route_count=len(eligible),
    source_commit_count=sources,
    excluded_low_point_route_count=excluded,
    point_count=points,
    bucket_counts=buckets,
    models=tuple(evaluations),
    selected_model=None,
    evaluation_executed=True,
  )
