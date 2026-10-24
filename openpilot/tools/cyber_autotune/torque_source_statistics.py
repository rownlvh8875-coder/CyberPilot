"""Source-disjoint development TLS diagnostic with a frozen source split.

Uses compact per-route Gram matrices only. Each source commit is a cluster and
fit/evaluation source sets are disjoint. No raw points, candidate, Params write,
or runtime/promotion authority is provided.
"""
from dataclasses import asdict, dataclass, field
import hashlib
import json
import math

import numpy as np

from openpilot.tools.cyber_autotune.contracts import finite_number, is_sha256
from openpilot.tools.cyber_autotune.torque_aggregation import MIN_BUCKET_POINTS, MIN_POINTS_TOTAL
from openpilot.tools.cyber_autotune.torque_route_statistics import (
  TorqueRouteEstimate,
  TorqueRouteStatistics,
  _valid_route,
)

SOURCE_SPLIT_SALT = 'cyberpilot-step8-source-split-v1'
SOURCE_SPLIT_MODULUS = 3
SOURCE_EVALUATION_RESIDUE = 0
MINIMUM_ROUTE_POINTS = 100
MINIMUM_FIT_SOURCES = 8
MINIMUM_EVALUATION_SOURCES = 4
MINIMUM_FIT_ROUTES = 20
MINIMUM_EVALUATION_ROUTES = 5
MAXIMUM_FIT_SOURCE_POINT_SHARE = .40
MAXIMUM_LOO_SOURCE_FACTOR_RELATIVE_DEVIATION = .05
MAXIMUM_LOO_SOURCE_OFFSET_ABSOLUTE_DEVIATION_MPS2 = .05
MAXIMUM_JACKKNIFE_95_FACTOR_RELATIVE_HALF_WIDTH = .10
MAXIMUM_EVALUATION_RMSE_MPS2 = .30
MAXIMUM_EVALUATION_ABSOLUTE_MEAN_RESIDUAL_MPS2 = .10
MAXIMUM_EVALUATION_TO_FIT_RMSE_RATIO = 1.50
EVALUATION_TO_FIT_RMSE_ALLOWANCE_MPS2 = .03
AUTHORITY_BLOCKERS = (
  'CONFIDENCE_QUALIFICATION_NOT_GRANTED',
  'CANDIDATE_GENERATION_NOT_AUTHORIZED',
  'QUALIFIED_REPLAY_NOT_RUN',
)


@dataclass(frozen=True)
class TorqueSourceStatisticalPolicy:
  policy_sha256: str
  split_salt: str
  split_modulus: int
  evaluation_residue: int
  minimum_route_points: int
  minimum_fit_source_clusters: int
  minimum_evaluation_source_clusters: int
  minimum_fit_route_clusters: int
  minimum_evaluation_route_clusters: int
  maximum_fit_source_point_share: float
  maximum_leave_one_source_factor_relative_deviation: float
  maximum_leave_one_source_offset_absolute_deviation_mps2: float
  maximum_jackknife_95_factor_relative_half_width: float
  maximum_evaluation_residual_rmse_mps2: float
  maximum_evaluation_absolute_mean_residual_mps2: float
  maximum_evaluation_to_fit_rmse_ratio: float
  evaluation_to_fit_rmse_absolute_allowance_mps2: float


@dataclass(frozen=True)
class LeaveOneSourceEstimate:
  omitted_source_commit: str
  estimate: TorqueRouteEstimate
  factor_relative_deviation: float
  offset_absolute_deviation_mps2: float


@dataclass(frozen=True)
class TorqueSourceStatisticalReport:
  status: str
  blockers: tuple[str, ...]
  input_sha256: str | None = None
  eligible_route_count: int = 0
  fit_route_count: int = 0
  evaluation_route_count: int = 0
  excluded_low_point_route_count: int = 0
  fit_source_count: int = 0
  evaluation_source_count: int = 0
  fit_source_commits: tuple[str, ...] = ()
  evaluation_source_commits: tuple[str, ...] = ()
  maximum_fit_source_point_share: float | None = None
  fit_estimate: TorqueRouteEstimate | None = None
  evaluation_residual_rmse_mps2: float | None = None
  evaluation_mean_residual_mps2: float | None = None
  evaluation_to_fit_rmse_ratio: float | None = None
  leave_one_source_out: tuple[LeaveOneSourceEstimate, ...] = ()
  maximum_leave_one_source_factor_relative_deviation: float | None = None
  maximum_leave_one_source_offset_absolute_deviation_mps2: float | None = None
  jackknife_95_factor_relative_half_width: float | None = None
  development_source_disjoint_stability_pass: bool = False
  fit_executed: bool = False
  independent_holdout: bool = field(default=False, init=False)
  confidence_qualified: bool = field(default=False, init=False)
  candidate_generation_allowed: bool = field(default=False, init=False)
  runtime_accepted: bool = field(default=False, init=False)
  promotable: bool = field(default=False, init=False)


def source_role(source_commit: str, policy: TorqueSourceStatisticalPolicy) -> str:
  digest = hashlib.sha256(f'{policy.split_salt}:{source_commit}'.encode()).digest()
  value = int.from_bytes(digest[:4], 'big') % policy.split_modulus
  return 'development_evaluation' if value == policy.evaluation_residue else 'development_fit'


def _valid_policy(policy) -> bool:
  return (
    type(policy) is TorqueSourceStatisticalPolicy and
    is_sha256(policy.policy_sha256) and
    policy.split_salt == SOURCE_SPLIT_SALT and
    type(policy.split_modulus) is int and policy.split_modulus == SOURCE_SPLIT_MODULUS and
    type(policy.evaluation_residue) is int and policy.evaluation_residue == SOURCE_EVALUATION_RESIDUE and
    type(policy.minimum_route_points) is int and policy.minimum_route_points == MINIMUM_ROUTE_POINTS and
    type(policy.minimum_fit_source_clusters) is int and
    policy.minimum_fit_source_clusters == MINIMUM_FIT_SOURCES and
    type(policy.minimum_evaluation_source_clusters) is int and
    policy.minimum_evaluation_source_clusters == MINIMUM_EVALUATION_SOURCES and
    type(policy.minimum_fit_route_clusters) is int and
    policy.minimum_fit_route_clusters == MINIMUM_FIT_ROUTES and
    type(policy.minimum_evaluation_route_clusters) is int and
    policy.minimum_evaluation_route_clusters == MINIMUM_EVALUATION_ROUTES and
    policy.maximum_fit_source_point_share == MAXIMUM_FIT_SOURCE_POINT_SHARE and
    policy.maximum_leave_one_source_factor_relative_deviation == MAXIMUM_LOO_SOURCE_FACTOR_RELATIVE_DEVIATION and
    policy.maximum_leave_one_source_offset_absolute_deviation_mps2 == MAXIMUM_LOO_SOURCE_OFFSET_ABSOLUTE_DEVIATION_MPS2 and
    policy.maximum_jackknife_95_factor_relative_half_width == MAXIMUM_JACKKNIFE_95_FACTOR_RELATIVE_HALF_WIDTH and
    policy.maximum_evaluation_residual_rmse_mps2 == MAXIMUM_EVALUATION_RMSE_MPS2 and
    policy.maximum_evaluation_absolute_mean_residual_mps2 == MAXIMUM_EVALUATION_ABSOLUTE_MEAN_RESIDUAL_MPS2 and
    policy.maximum_evaluation_to_fit_rmse_ratio == MAXIMUM_EVALUATION_TO_FIT_RMSE_RATIO and
    policy.evaluation_to_fit_rmse_absolute_allowance_mps2 == EVALUATION_TO_FIT_RMSE_ALLOWANCE_MPS2
  )


def _coverage(routes):
  counts = tuple(sum(route.bucket_counts[i] for route in routes) for i in range(len(MIN_BUCKET_POINTS)))
  point_count = sum(counts)
  deficits = tuple(max(0, minimum - count) for count, minimum in zip(counts, MIN_BUCKET_POINTS, strict=True))
  total_deficit = max(0, MIN_POINTS_TOTAL - point_count)
  return point_count, counts, deficits, total_deficit == 0 and not any(deficits)


def _group_by_source(routes):
  grouped = {}
  for route in routes:
    grouped.setdefault(route.source_commit, []).append(route)
  return {key: tuple(sorted(value, key=lambda route: route.route_sha256)) for key, value in grouped.items()}


def _source_balanced_gram(source_groups):
  source_grams = []
  for routes in source_groups.values():
    route_grams = [np.asarray(route.gram_xtx, dtype=np.float64) / route.point_count for route in routes]
    source_grams.append(np.mean(np.stack(route_grams), axis=0))
  return np.mean(np.stack(source_grams), axis=0)


def _source_residual_metrics(source_groups, slope, offset):
  residual_vector = np.array([-slope, -offset, 1.], dtype=np.float64)
  source_mse = []
  source_mean = []
  for routes in source_groups.values():
    route_mse = []
    route_mean = []
    for route in routes:
      gram = np.asarray(route.gram_xtx, dtype=np.float64)
      route_mse.append(float(residual_vector @ gram @ residual_vector / route.point_count))
      sum_x = float(gram[0, 1])
      sum_y = float(gram[1, 2])
      route_mean.append((sum_y - slope * sum_x - offset * route.point_count) / route.point_count)
    source_mse.append(float(np.mean(route_mse)))
    source_mean.append(float(np.mean(route_mean)))
  mse = max(0., float(np.mean(source_mse)))
  return math.sqrt(mse), float(np.mean(source_mean))


def _tls(source_groups):
  gram = _source_balanced_gram(source_groups)
  try:
    with np.errstate(all='raise'):
      eigenvalues, vectors = np.linalg.eigh(gram)
      tolerance = np.finfo(np.float64).eps * 3 * max(1., float(abs(eigenvalues[-1])))
      if (eigenvalues[1] <= tolerance or eigenvalues[1] - eigenvalues[0] <= tolerance or
          abs(vectors[2, 0]) <= tolerance):
        raise ValueError('DEGENERATE_TLS')
      vector = vectors[:, 0]
      slope = float(-vector[0] / vector[2])
      offset = float(-vector[1] / vector[2])
      if not finite_number(slope) or slope <= 0 or not finite_number(offset):
        raise ValueError('NONPOSITIVE_FACTOR')
      rmse, mean_residual = _source_residual_metrics(source_groups, slope, offset)
      if not all(finite_number(value) for value in (rmse, mean_residual)):
        raise ValueError('NONFINITE_METRICS')
  except (np.linalg.LinAlgError, FloatingPointError, ValueError, OverflowError):
    return None
  return TorqueRouteEstimate(slope, offset, rmse, mean_residual)


def _input_digest(routes, policy):
  payload = {
    'policy': asdict(policy),
    'routes': [asdict(route) for route in routes],
    'algorithm': 'equal-source-equal-route-tls-v1',
  }
  return hashlib.sha256(json.dumps(
    payload, sort_keys=True, separators=(',', ':'), allow_nan=False,
  ).encode()).hexdigest()


def _blocked(reason, digest=None, eligible=0, fit_routes=0, evaluation_routes=0,
             excluded=0, fit_sources=(), evaluation_sources=(), fit_executed=False):
  return TorqueSourceStatisticalReport(
    status='BLOCKED',
    blockers=(reason,),
    input_sha256=digest,
    eligible_route_count=eligible,
    fit_route_count=fit_routes,
    evaluation_route_count=evaluation_routes,
    excluded_low_point_route_count=excluded,
    fit_source_count=len(fit_sources),
    evaluation_source_count=len(evaluation_sources),
    fit_source_commits=tuple(sorted(fit_sources)),
    evaluation_source_commits=tuple(sorted(evaluation_sources)),
    fit_executed=fit_executed,
  )


def assess_source_statistics(routes: tuple[TorqueRouteStatistics, ...],
                             policy: TorqueSourceStatisticalPolicy) -> TorqueSourceStatisticalReport:
  """Run a source-disjoint development diagnostic; never emit a candidate."""
  if not _valid_policy(policy):
    return _blocked('INVALID_SOURCE_STATISTICAL_POLICY')
  if type(routes) is not tuple or not routes or any(not _valid_route(route) for route in routes):
    return _blocked('INVALID_ROUTE_STATISTICS')
  if len({route.route_sha256 for route in routes}) != len(routes):
    return _blocked('DUPLICATE_ROUTE_ID')

  ordered = tuple(sorted(routes, key=lambda route: route.route_sha256))
  digest = _input_digest(ordered, policy)
  eligible = tuple(route for route in ordered if route.point_count >= policy.minimum_route_points)
  excluded = len(ordered) - len(eligible)
  source_groups = _group_by_source(eligible)
  fit_sources = tuple(sorted(
    source for source in source_groups
    if source_role(source, policy) == 'development_fit'
  ))
  evaluation_sources = tuple(sorted(
    source for source in source_groups
    if source_role(source, policy) == 'development_evaluation'
  ))
  fit_routes = tuple(route for route in eligible if route.source_commit in fit_sources)
  evaluation_routes = tuple(route for route in eligible if route.source_commit in evaluation_sources)
  counts = (
    len(eligible), len(fit_routes), len(evaluation_routes), excluded,
    fit_sources, evaluation_sources,
  )
  if (len(fit_sources) < policy.minimum_fit_source_clusters or
      len(evaluation_sources) < policy.minimum_evaluation_source_clusters or
      len(fit_routes) < policy.minimum_fit_route_clusters or
      len(evaluation_routes) < policy.minimum_evaluation_route_clusters):
    return _blocked('INSUFFICIENT_SOURCE_DISJOINT_SPLIT', digest, *counts)

  _, _, _, fit_coverage = _coverage(fit_routes)
  _, _, _, evaluation_coverage = _coverage(evaluation_routes)
  if not fit_coverage:
    return _blocked('FIT_STRUCTURAL_COUNT_COVERAGE_INSUFFICIENT', digest, *counts)
  if not evaluation_coverage:
    return _blocked('EVALUATION_STRUCTURAL_COUNT_COVERAGE_INSUFFICIENT', digest, *counts)

  fit_point_count = sum(route.point_count for route in fit_routes)
  fit_source_point_share = {
    source: sum(route.point_count for route in fit_routes if route.source_commit == source) / fit_point_count
    for source in fit_sources
  }
  max_fit_source_share = max(fit_source_point_share.values())
  if max_fit_source_share > policy.maximum_fit_source_point_share:
    return TorqueSourceStatisticalReport(
      status='SOURCE_DISJOINT_DEVELOPMENT_DIAGNOSTIC_REJECTED',
      blockers=('FIT_SOURCE_POINT_SHARE_DOMINANCE',) + AUTHORITY_BLOCKERS,
      input_sha256=digest,
      eligible_route_count=len(eligible),
      fit_route_count=len(fit_routes),
      evaluation_route_count=len(evaluation_routes),
      excluded_low_point_route_count=excluded,
      fit_source_count=len(fit_sources),
      evaluation_source_count=len(evaluation_sources),
      fit_source_commits=fit_sources,
      evaluation_source_commits=evaluation_sources,
      maximum_fit_source_point_share=max_fit_source_share,
    )

  for omitted_source in fit_sources:
    retained = tuple(route for route in fit_routes if route.source_commit != omitted_source)
    if not _coverage(retained)[3]:
      return _blocked(
        'FIT_LEAVE_ONE_SOURCE_OUT_COUNT_COVERAGE_INSUFFICIENT',
        digest, *counts,
      )

  fit_groups = _group_by_source(fit_routes)
  evaluation_groups = _group_by_source(evaluation_routes)
  fit_estimate = _tls(fit_groups)
  if fit_estimate is None:
    return _blocked('FIT_NUMERICALLY_UNIDENTIFIABLE', digest, *counts, fit_executed=True)

  loo = []
  for omitted_source in fit_sources:
    retained_groups = {
      source: source_routes for source, source_routes in fit_groups.items()
      if source != omitted_source
    }
    estimate = _tls(retained_groups)
    if estimate is None:
      return _blocked(
        'LEAVE_ONE_SOURCE_NUMERICALLY_UNIDENTIFIABLE',
        digest, *counts, fit_executed=True,
      )
    factor_deviation = abs(
      estimate.lat_accel_factor - fit_estimate.lat_accel_factor
    ) / fit_estimate.lat_accel_factor
    offset_deviation = abs(
      estimate.lat_accel_offset_mps2 - fit_estimate.lat_accel_offset_mps2
    )
    loo.append(LeaveOneSourceEstimate(
      omitted_source,
      estimate,
      factor_deviation,
      offset_deviation,
    ))
  loo = tuple(loo)
  max_factor_deviation = max(row.factor_relative_deviation for row in loo)
  max_offset_deviation = max(row.offset_absolute_deviation_mps2 for row in loo)

  loo_factors = np.asarray(
    [row.estimate.lat_accel_factor for row in loo], dtype=np.float64,
  )
  loo_mean = float(np.mean(loo_factors))
  jackknife_se = math.sqrt(
    (len(loo) - 1) / len(loo) *
    float(np.sum((loo_factors - loo_mean) ** 2))
  )
  jackknife_relative_half_width = (
    1.96 * jackknife_se / fit_estimate.lat_accel_factor
  )
  evaluation_rmse, evaluation_mean = _source_residual_metrics(
    evaluation_groups,
    fit_estimate.lat_accel_factor,
    fit_estimate.lat_accel_offset_mps2,
  )
  if fit_estimate.residual_rmse_mps2 <= np.finfo(np.float64).eps:
    evaluation_ratio = (
      1. if evaluation_rmse <= np.finfo(np.float64).eps else math.inf
    )
  else:
    evaluation_ratio = evaluation_rmse / fit_estimate.residual_rmse_mps2

  blockers = []
  if max_factor_deviation > policy.maximum_leave_one_source_factor_relative_deviation:
    blockers.append('LEAVE_ONE_SOURCE_FACTOR_UNSTABLE')
  if max_offset_deviation > policy.maximum_leave_one_source_offset_absolute_deviation_mps2:
    blockers.append('LEAVE_ONE_SOURCE_OFFSET_UNSTABLE')
  if jackknife_relative_half_width > policy.maximum_jackknife_95_factor_relative_half_width:
    blockers.append('JACKKNIFE_SOURCE_FACTOR_UNCERTAINTY_EXCESSIVE')
  if evaluation_rmse > policy.maximum_evaluation_residual_rmse_mps2:
    blockers.append('EVALUATION_RMSE_EXCESSIVE')
  if abs(evaluation_mean) > policy.maximum_evaluation_absolute_mean_residual_mps2:
    blockers.append('EVALUATION_MEAN_RESIDUAL_EXCESSIVE')
  if evaluation_rmse > (
      fit_estimate.residual_rmse_mps2 * policy.maximum_evaluation_to_fit_rmse_ratio +
      policy.evaluation_to_fit_rmse_absolute_allowance_mps2):
    blockers.append('EVALUATION_TO_FIT_RMSE_DEGRADATION')

  passed = not blockers
  status = (
    'SOURCE_DISJOINT_DEVELOPMENT_DIAGNOSTIC_PASS'
    if passed else 'SOURCE_DISJOINT_DEVELOPMENT_DIAGNOSTIC_REJECTED'
  )
  return TorqueSourceStatisticalReport(
    status=status,
    blockers=tuple(blockers) + AUTHORITY_BLOCKERS,
    input_sha256=digest,
    eligible_route_count=len(eligible),
    fit_route_count=len(fit_routes),
    evaluation_route_count=len(evaluation_routes),
    excluded_low_point_route_count=excluded,
    fit_source_count=len(fit_sources),
    evaluation_source_count=len(evaluation_sources),
    fit_source_commits=fit_sources,
    evaluation_source_commits=evaluation_sources,
    maximum_fit_source_point_share=max_fit_source_share,
    fit_estimate=fit_estimate,
    evaluation_residual_rmse_mps2=evaluation_rmse,
    evaluation_mean_residual_mps2=evaluation_mean,
    evaluation_to_fit_rmse_ratio=evaluation_ratio,
    leave_one_source_out=loo,
    maximum_leave_one_source_factor_relative_deviation=max_factor_deviation,
    maximum_leave_one_source_offset_absolute_deviation_mps2=max_offset_deviation,
    jackknife_95_factor_relative_half_width=jackknife_relative_half_width,
    development_source_disjoint_stability_pass=passed,
    fit_executed=True,
  )
