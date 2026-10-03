"""Route-balanced development TLS diagnostics with a frozen route split.

Uses only compact per-route Gram matrices and structural counts. It never opens
raw points, generates a candidate, mutates Params, or grants runtime authority.
"""
from dataclasses import asdict, dataclass, field
import hashlib
import json
import math
import re

import numpy as np

from openpilot.tools.cyber_autotune.contracts import finite_number, is_sha256
from openpilot.tools.cyber_autotune.torque_aggregation import MIN_BUCKET_POINTS, MIN_POINTS_TOTAL

SPLIT_SALT = 'cyberpilot-step8-route-split-v1'
SPLIT_MODULUS = 5
EVALUATION_RESIDUE = 0
MINIMUM_ROUTE_POINTS = 100
MINIMUM_FIT_ROUTES = 20
MINIMUM_EVALUATION_ROUTES = 5
MAX_LOO_FACTOR_RELATIVE_DEVIATION = .20
MAX_LOO_OFFSET_ABSOLUTE_DEVIATION_MPS2 = .10
MAX_JACKKNIFE_95_FACTOR_RELATIVE_HALF_WIDTH = .20
MAX_EVALUATION_RMSE_MPS2 = .30
MAX_EVALUATION_ABSOLUTE_MEAN_RESIDUAL_MPS2 = .10
MAX_EVALUATION_TO_FIT_RMSE_RATIO = 1.50
EVALUATION_TO_FIT_RMSE_ALLOWANCE_MPS2 = .03
AUTHORITY_BLOCKERS = ('CONFIDENCE_QUALIFICATION_NOT_GRANTED',
                      'CANDIDATE_GENERATION_NOT_AUTHORIZED', 'QUALIFIED_REPLAY_NOT_RUN')


@dataclass(frozen=True)
class TorqueRouteStatistics:
  route_sha256: str
  source_commit: str
  point_manifest_sha256: str
  point_count: int
  bucket_counts: tuple[int, ...]
  gram_xtx: tuple[tuple[float, ...], ...]


@dataclass(frozen=True)
class TorqueRouteStatisticalPolicy:
  policy_sha256: str
  split_salt: str
  split_modulus: int
  evaluation_residue: int
  minimum_route_points: int
  minimum_fit_route_clusters: int
  minimum_evaluation_route_clusters: int
  maximum_leave_one_route_factor_relative_deviation: float
  maximum_leave_one_route_offset_absolute_deviation_mps2: float
  maximum_jackknife_95_factor_relative_half_width: float
  maximum_evaluation_residual_rmse_mps2: float
  maximum_evaluation_absolute_mean_residual_mps2: float
  maximum_evaluation_to_fit_rmse_ratio: float
  evaluation_to_fit_rmse_absolute_allowance_mps2: float


@dataclass(frozen=True)
class TorqueRouteEstimate:
  lat_accel_factor: float
  lat_accel_offset_mps2: float
  residual_rmse_mps2: float
  mean_residual_mps2: float


@dataclass(frozen=True)
class LeaveOneRouteEstimate:
  omitted_route_sha256: str
  estimate: TorqueRouteEstimate
  factor_relative_deviation: float
  offset_absolute_deviation_mps2: float


@dataclass(frozen=True)
class TorqueRouteStatisticalReport:
  status: str
  blockers: tuple[str, ...]
  input_sha256: str | None = None
  eligible_route_count: int = 0
  fit_route_count: int = 0
  evaluation_route_count: int = 0
  excluded_low_point_route_count: int = 0
  fit_estimate: TorqueRouteEstimate | None = None
  evaluation_residual_rmse_mps2: float | None = None
  evaluation_mean_residual_mps2: float | None = None
  evaluation_to_fit_rmse_ratio: float | None = None
  leave_one_route_out: tuple[LeaveOneRouteEstimate, ...] = ()
  maximum_leave_one_route_factor_relative_deviation: float | None = None
  maximum_leave_one_route_offset_absolute_deviation_mps2: float | None = None
  jackknife_95_factor_relative_half_width: float | None = None
  development_statistical_stability_pass: bool = False
  fit_executed: bool = False
  confidence_qualified: bool = field(default=False, init=False)
  candidate_generation_allowed: bool = field(default=False, init=False)
  runtime_accepted: bool = field(default=False, init=False)
  promotable: bool = field(default=False, init=False)


def route_role(route_sha256: str, policy: TorqueRouteStatisticalPolicy) -> str:
  digest = hashlib.sha256(f'{policy.split_salt}:{route_sha256}'.encode()).digest()
  value = int.from_bytes(digest[:4], 'big') % policy.split_modulus
  return 'development_evaluation' if value == policy.evaluation_residue else 'development_fit'


def _valid_policy(policy) -> bool:
  return (
    type(policy) is TorqueRouteStatisticalPolicy and
    is_sha256(policy.policy_sha256) and
    policy.split_salt == SPLIT_SALT and
    type(policy.split_modulus) is int and policy.split_modulus == SPLIT_MODULUS and
    type(policy.evaluation_residue) is int and policy.evaluation_residue == EVALUATION_RESIDUE and
    type(policy.minimum_route_points) is int and policy.minimum_route_points == MINIMUM_ROUTE_POINTS and
    type(policy.minimum_fit_route_clusters) is int and policy.minimum_fit_route_clusters == MINIMUM_FIT_ROUTES and
    type(policy.minimum_evaluation_route_clusters) is int and
    policy.minimum_evaluation_route_clusters == MINIMUM_EVALUATION_ROUTES and
    policy.maximum_leave_one_route_factor_relative_deviation == MAX_LOO_FACTOR_RELATIVE_DEVIATION and
    policy.maximum_leave_one_route_offset_absolute_deviation_mps2 == MAX_LOO_OFFSET_ABSOLUTE_DEVIATION_MPS2 and
    policy.maximum_jackknife_95_factor_relative_half_width == MAX_JACKKNIFE_95_FACTOR_RELATIVE_HALF_WIDTH and
    policy.maximum_evaluation_residual_rmse_mps2 == MAX_EVALUATION_RMSE_MPS2 and
    policy.maximum_evaluation_absolute_mean_residual_mps2 == MAX_EVALUATION_ABSOLUTE_MEAN_RESIDUAL_MPS2 and
    policy.maximum_evaluation_to_fit_rmse_ratio == MAX_EVALUATION_TO_FIT_RMSE_RATIO and
    policy.evaluation_to_fit_rmse_absolute_allowance_mps2 == EVALUATION_TO_FIT_RMSE_ALLOWANCE_MPS2
  )


def _valid_route(route) -> bool:
  if (type(route) is not TorqueRouteStatistics or not is_sha256(route.route_sha256) or
      type(route.source_commit) is not str or re.fullmatch(r'[0-9a-f]{40}', route.source_commit) is None or
      not is_sha256(route.point_manifest_sha256) or
      type(route.point_count) is not int or route.point_count < 0 or
      type(route.bucket_counts) is not tuple or len(route.bucket_counts) != len(MIN_BUCKET_POINTS) or
      any(type(count) is not int or count < 0 for count in route.bucket_counts) or
      sum(route.bucket_counts) != route.point_count or
      type(route.gram_xtx) is not tuple or len(route.gram_xtx) != 3 or
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


def _coverage(routes):
  counts = tuple(sum(route.bucket_counts[i] for route in routes) for i in range(len(MIN_BUCKET_POINTS)))
  point_count = sum(counts)
  deficits = tuple(max(0, minimum - count) for count, minimum in zip(counts, MIN_BUCKET_POINTS, strict=True))
  total_deficit = max(0, MIN_POINTS_TOTAL - point_count)
  return point_count, counts, deficits, total_deficit == 0 and not any(deficits)


def _balanced_gram(routes):
  grams = [np.asarray(route.gram_xtx, dtype=np.float64) / route.point_count for route in routes]
  return np.mean(np.stack(grams), axis=0)


def _residual_metrics(routes, slope, offset):
  residual_vector = np.array([-slope, -offset, 1.], dtype=np.float64)
  route_mse = []
  route_mean = []
  for route in routes:
    gram = np.asarray(route.gram_xtx, dtype=np.float64)
    route_mse.append(float(residual_vector @ gram @ residual_vector / route.point_count))
    sum_x = float(gram[0, 1])
    sum_y = float(gram[1, 2])
    route_mean.append((sum_y - slope * sum_x - offset * route.point_count) / route.point_count)
  mse = max(0., float(np.mean(route_mse)))
  return math.sqrt(mse), float(np.mean(route_mean))


def _tls(routes):
  gram = _balanced_gram(routes)
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
      rmse, mean_residual = _residual_metrics(routes, slope, offset)
      if not all(finite_number(value) for value in (rmse, mean_residual)):
        raise ValueError('NONFINITE_METRICS')
  except (np.linalg.LinAlgError, FloatingPointError, ValueError, OverflowError):
    return None
  return TorqueRouteEstimate(slope, offset, rmse, mean_residual)


def _input_digest(routes, policy):
  payload = {
    'policy': asdict(policy),
    'routes': [asdict(route) for route in routes],
    'algorithm': 'equal-route-weighted-tls-v1',
  }
  return hashlib.sha256(json.dumps(
    payload, sort_keys=True, separators=(',', ':'), allow_nan=False,
  ).encode()).hexdigest()


def _blocked(reason, digest=None, eligible=0, fit=0, evaluation=0, excluded=0, fit_executed=False):
  return TorqueRouteStatisticalReport(
    status='BLOCKED',
    blockers=(reason,),
    input_sha256=digest,
    eligible_route_count=eligible,
    fit_route_count=fit,
    evaluation_route_count=evaluation,
    excluded_low_point_route_count=excluded,
    fit_executed=fit_executed,
  )


def assess_route_statistics(routes: tuple[TorqueRouteStatistics, ...],
                            policy: TorqueRouteStatisticalPolicy) -> TorqueRouteStatisticalReport:
  """Run a development-only route-balanced diagnostic; never emit a candidate."""
  if not _valid_policy(policy):
    return _blocked('INVALID_STATISTICAL_POLICY')
  if type(routes) is not tuple or not routes or any(not _valid_route(route) for route in routes):
    return _blocked('INVALID_ROUTE_STATISTICS')
  if len({route.route_sha256 for route in routes}) != len(routes):
    return _blocked('DUPLICATE_ROUTE_ID')

  ordered = tuple(sorted(routes, key=lambda route: route.route_sha256))
  digest = _input_digest(ordered, policy)
  eligible = tuple(route for route in ordered if route.point_count >= policy.minimum_route_points)
  excluded = len(ordered) - len(eligible)
  fit_routes = tuple(route for route in eligible if route_role(route.route_sha256, policy) == 'development_fit')
  evaluation_routes = tuple(route for route in eligible if route_role(route.route_sha256, policy) == 'development_evaluation')
  counts = (len(eligible), len(fit_routes), len(evaluation_routes), excluded)
  if (len(fit_routes) < policy.minimum_fit_route_clusters or
      len(evaluation_routes) < policy.minimum_evaluation_route_clusters):
    return _blocked('INSUFFICIENT_SPLIT_ROUTE_CLUSTERS', digest, *counts)

  _, _, _, fit_coverage = _coverage(fit_routes)
  _, _, _, evaluation_coverage = _coverage(evaluation_routes)
  if not fit_coverage:
    return _blocked('FIT_STRUCTURAL_COUNT_COVERAGE_INSUFFICIENT', digest, *counts)
  if not evaluation_coverage:
    return _blocked('EVALUATION_STRUCTURAL_COUNT_COVERAGE_INSUFFICIENT', digest, *counts)
  for omitted in fit_routes:
    retained = tuple(route for route in fit_routes if route.route_sha256 != omitted.route_sha256)
    if not _coverage(retained)[3]:
      return _blocked('FIT_LEAVE_ONE_ROUTE_OUT_COUNT_COVERAGE_INSUFFICIENT', digest, *counts)

  fit_estimate = _tls(fit_routes)
  if fit_estimate is None:
    return _blocked('FIT_NUMERICALLY_UNIDENTIFIABLE', digest, *counts, fit_executed=True)

  loo = []
  for omitted in fit_routes:
    retained = tuple(route for route in fit_routes if route.route_sha256 != omitted.route_sha256)
    estimate = _tls(retained)
    if estimate is None:
      return _blocked('LEAVE_ONE_ROUTE_NUMERICALLY_UNIDENTIFIABLE', digest, *counts, fit_executed=True)
    factor_deviation = abs(estimate.lat_accel_factor - fit_estimate.lat_accel_factor) / fit_estimate.lat_accel_factor
    offset_deviation = abs(estimate.lat_accel_offset_mps2 - fit_estimate.lat_accel_offset_mps2)
    loo.append(LeaveOneRouteEstimate(
      omitted.route_sha256,
      estimate,
      factor_deviation,
      offset_deviation,
    ))
  loo = tuple(loo)
  max_factor_deviation = max(row.factor_relative_deviation for row in loo)
  max_offset_deviation = max(row.offset_absolute_deviation_mps2 for row in loo)

  loo_factors = np.asarray([row.estimate.lat_accel_factor for row in loo], dtype=np.float64)
  loo_mean = float(np.mean(loo_factors))
  jackknife_se = math.sqrt((len(loo) - 1) / len(loo) * float(np.sum((loo_factors - loo_mean) ** 2)))
  jackknife_relative_half_width = 1.96 * jackknife_se / fit_estimate.lat_accel_factor

  evaluation_rmse, evaluation_mean = _residual_metrics(
    evaluation_routes,
    fit_estimate.lat_accel_factor,
    fit_estimate.lat_accel_offset_mps2,
  )
  if fit_estimate.residual_rmse_mps2 <= np.finfo(np.float64).eps:
    evaluation_ratio = 1. if evaluation_rmse <= np.finfo(np.float64).eps else math.inf
  else:
    evaluation_ratio = evaluation_rmse / fit_estimate.residual_rmse_mps2

  blockers = []
  if max_factor_deviation > policy.maximum_leave_one_route_factor_relative_deviation:
    blockers.append('LEAVE_ONE_ROUTE_FACTOR_UNSTABLE')
  if max_offset_deviation > policy.maximum_leave_one_route_offset_absolute_deviation_mps2:
    blockers.append('LEAVE_ONE_ROUTE_OFFSET_UNSTABLE')
  if jackknife_relative_half_width > policy.maximum_jackknife_95_factor_relative_half_width:
    blockers.append('JACKKNIFE_FACTOR_UNCERTAINTY_EXCESSIVE')
  if evaluation_rmse > policy.maximum_evaluation_residual_rmse_mps2:
    blockers.append('EVALUATION_RMSE_EXCESSIVE')
  if abs(evaluation_mean) > policy.maximum_evaluation_absolute_mean_residual_mps2:
    blockers.append('EVALUATION_MEAN_RESIDUAL_EXCESSIVE')
  if evaluation_rmse > (fit_estimate.residual_rmse_mps2 * policy.maximum_evaluation_to_fit_rmse_ratio +
                        policy.evaluation_to_fit_rmse_absolute_allowance_mps2):
    blockers.append('EVALUATION_TO_FIT_RMSE_DEGRADATION')

  passed = not blockers
  status = 'DEVELOPMENT_STATISTICAL_DIAGNOSTIC_PASS' if passed else 'DEVELOPMENT_STATISTICAL_DIAGNOSTIC_REJECTED'
  report_blockers = tuple(blockers) + AUTHORITY_BLOCKERS
  return TorqueRouteStatisticalReport(
    status=status,
    blockers=report_blockers,
    input_sha256=digest,
    eligible_route_count=len(eligible),
    fit_route_count=len(fit_routes),
    evaluation_route_count=len(evaluation_routes),
    excluded_low_point_route_count=excluded,
    fit_estimate=fit_estimate,
    evaluation_residual_rmse_mps2=evaluation_rmse,
    evaluation_mean_residual_mps2=evaluation_mean,
    evaluation_to_fit_rmse_ratio=evaluation_ratio,
    leave_one_route_out=loo,
    maximum_leave_one_route_factor_relative_deviation=max_factor_deviation,
    maximum_leave_one_route_offset_absolute_deviation_mps2=max_offset_deviation,
    jackknife_95_factor_relative_half_width=jackknife_relative_half_width,
    development_statistical_stability_pass=passed,
    fit_executed=True,
  )
