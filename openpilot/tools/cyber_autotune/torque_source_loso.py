"""Leave-one-source-out development evaluation over compact route statistics.

Every eligible source commit is held out once and evaluated using a model fit on
all other sources. This is retrospective development cross-validation, not an
untouched holdout, confidence qualification, or candidate authority.
"""
from dataclasses import asdict, dataclass, field
import hashlib
import json
import math

from openpilot.tools.cyber_autotune.contracts import is_sha256
from openpilot.tools.cyber_autotune.torque_route_statistics import (
  TorqueRouteEstimate,
  TorqueRouteStatistics,
  _valid_route,
)
from openpilot.tools.cyber_autotune.torque_source_statistics import (
  _coverage,
  _group_by_source,
  _source_residual_metrics,
  _tls,
)

MINIMUM_ROUTE_POINTS = 100
MINIMUM_SOURCE_CLUSTERS = 10
MAXIMUM_SOURCE_POINT_SHARE = .40
MAXIMUM_FOLD_FACTOR_RELATIVE_DEVIATION = .05
MAXIMUM_FOLD_OFFSET_ABSOLUTE_DEVIATION_MPS2 = .05
MAXIMUM_FOLD_EVALUATION_RMSE_MPS2 = .30
MAXIMUM_FOLD_EVALUATION_ABSOLUTE_MEAN_RESIDUAL_MPS2 = .10
MAXIMUM_FOLD_EVALUATION_TO_FIT_RMSE_RATIO = 1.50
EVALUATION_TO_FIT_RMSE_ALLOWANCE_MPS2 = .03
AUTHORITY_BLOCKERS = (
  'CONFIDENCE_QUALIFICATION_NOT_GRANTED',
  'CANDIDATE_GENERATION_NOT_AUTHORIZED',
  'QUALIFIED_REPLAY_NOT_RUN',
)


@dataclass(frozen=True)
class TorqueSourceLosoPolicy:
  policy_sha256: str
  minimum_route_points: int
  minimum_source_clusters: int
  maximum_source_point_share: float
  maximum_fold_factor_relative_deviation: float
  maximum_fold_offset_absolute_deviation_mps2: float
  maximum_fold_evaluation_rmse_mps2: float
  maximum_fold_evaluation_absolute_mean_residual_mps2: float
  maximum_fold_evaluation_to_fit_rmse_ratio: float
  evaluation_to_fit_rmse_absolute_allowance_mps2: float
  require_all_source_folds_pass: bool


@dataclass(frozen=True)
class TorqueSourceLosoFold:
  evaluation_source_commit: str
  fit_source_count: int
  fit_route_count: int
  evaluation_route_count: int
  evaluation_point_count: int
  fit_estimate: TorqueRouteEstimate
  factor_relative_deviation_from_pooled: float
  offset_absolute_deviation_from_pooled_mps2: float
  evaluation_residual_rmse_mps2: float
  evaluation_mean_residual_mps2: float
  evaluation_to_fit_rmse_ratio: float
  blockers: tuple[str, ...]
  fold_pass: bool


@dataclass(frozen=True)
class TorqueSourceLosoReport:
  status: str
  blockers: tuple[str, ...]
  input_sha256: str | None = None
  eligible_route_count: int = 0
  excluded_low_point_route_count: int = 0
  source_count: int = 0
  point_count: int = 0
  maximum_source_point_share: float | None = None
  pooled_estimate: TorqueRouteEstimate | None = None
  folds: tuple[TorqueSourceLosoFold, ...] = ()
  maximum_fold_factor_relative_deviation: float | None = None
  maximum_fold_offset_absolute_deviation_mps2: float | None = None
  maximum_fold_evaluation_rmse_mps2: float | None = None
  maximum_fold_evaluation_absolute_mean_residual_mps2: float | None = None
  maximum_fold_evaluation_to_fit_rmse_ratio: float | None = None
  mean_fold_evaluation_rmse_mps2: float | None = None
  all_source_folds_pass: bool = False
  fit_executed: bool = False
  independent_holdout: bool = field(default=False, init=False)
  confidence_qualified: bool = field(default=False, init=False)
  candidate_generation_allowed: bool = field(default=False, init=False)
  runtime_accepted: bool = field(default=False, init=False)
  promotable: bool = field(default=False, init=False)


def _valid_policy(policy) -> bool:
  return (
    type(policy) is TorqueSourceLosoPolicy and
    is_sha256(policy.policy_sha256) and
    type(policy.minimum_route_points) is int and
    policy.minimum_route_points == MINIMUM_ROUTE_POINTS and
    type(policy.minimum_source_clusters) is int and
    policy.minimum_source_clusters == MINIMUM_SOURCE_CLUSTERS and
    policy.maximum_source_point_share == MAXIMUM_SOURCE_POINT_SHARE and
    policy.maximum_fold_factor_relative_deviation == MAXIMUM_FOLD_FACTOR_RELATIVE_DEVIATION and
    policy.maximum_fold_offset_absolute_deviation_mps2 == MAXIMUM_FOLD_OFFSET_ABSOLUTE_DEVIATION_MPS2 and
    policy.maximum_fold_evaluation_rmse_mps2 == MAXIMUM_FOLD_EVALUATION_RMSE_MPS2 and
    policy.maximum_fold_evaluation_absolute_mean_residual_mps2 == MAXIMUM_FOLD_EVALUATION_ABSOLUTE_MEAN_RESIDUAL_MPS2 and
    policy.maximum_fold_evaluation_to_fit_rmse_ratio == MAXIMUM_FOLD_EVALUATION_TO_FIT_RMSE_RATIO and
    policy.evaluation_to_fit_rmse_absolute_allowance_mps2 == EVALUATION_TO_FIT_RMSE_ALLOWANCE_MPS2 and
    type(policy.require_all_source_folds_pass) is bool and
    policy.require_all_source_folds_pass
  )


def _input_digest(routes, policy):
  payload = {
    'policy': asdict(policy),
    'routes': [asdict(route) for route in routes],
    'algorithm': 'leave-one-source-out-equal-source-equal-route-tls-v1',
  }
  return hashlib.sha256(json.dumps(
    payload, sort_keys=True, separators=(',', ':'), allow_nan=False,
  ).encode()).hexdigest()


def _blocked(reason, digest=None, eligible=0, excluded=0, sources=0,
             points=0, max_share=None, fit_executed=False):
  return TorqueSourceLosoReport(
    status='BLOCKED',
    blockers=(reason,),
    input_sha256=digest,
    eligible_route_count=eligible,
    excluded_low_point_route_count=excluded,
    source_count=sources,
    point_count=points,
    maximum_source_point_share=max_share,
    fit_executed=fit_executed,
  )


def assess_source_loso(routes: tuple[TorqueRouteStatistics, ...],
                       policy: TorqueSourceLosoPolicy) -> TorqueSourceLosoReport:
  """Evaluate each source as held-out development data; never emit a candidate."""
  if not _valid_policy(policy):
    return _blocked('INVALID_SOURCE_LOSO_POLICY')
  if type(routes) is not tuple or not routes or any(not _valid_route(route) for route in routes):
    return _blocked('INVALID_ROUTE_STATISTICS')
  if len({route.route_sha256 for route in routes}) != len(routes):
    return _blocked('DUPLICATE_ROUTE_ID')

  ordered = tuple(sorted(routes, key=lambda route: route.route_sha256))
  digest = _input_digest(ordered, policy)
  eligible = tuple(route for route in ordered if route.point_count >= policy.minimum_route_points)
  excluded = len(ordered) - len(eligible)
  source_groups = _group_by_source(eligible)
  source_count = len(source_groups)
  point_count = sum(route.point_count for route in eligible)
  if source_count < policy.minimum_source_clusters:
    return _blocked(
      'INSUFFICIENT_SOURCE_CLUSTERS', digest, len(eligible), excluded,
      source_count, point_count,
    )
  if point_count <= 0:
    return _blocked(
      'NO_COVERAGE_POINTS', digest, len(eligible), excluded,
      source_count, point_count,
    )

  source_point_share = {
    source: sum(route.point_count for route in source_routes) / point_count
    for source, source_routes in source_groups.items()
  }
  max_source_share = max(source_point_share.values())
  if max_source_share > policy.maximum_source_point_share:
    return TorqueSourceLosoReport(
      status='SOURCE_LOSO_DEVELOPMENT_DIAGNOSTIC_REJECTED',
      blockers=('SOURCE_POINT_SHARE_DOMINANCE',) + AUTHORITY_BLOCKERS,
      input_sha256=digest,
      eligible_route_count=len(eligible),
      excluded_low_point_route_count=excluded,
      source_count=source_count,
      point_count=point_count,
      maximum_source_point_share=max_source_share,
    )

  pooled_estimate = _tls(source_groups)
  if pooled_estimate is None:
    return _blocked(
      'POOLED_NUMERICALLY_UNIDENTIFIABLE', digest, len(eligible), excluded,
      source_count, point_count, max_source_share, fit_executed=True,
    )

  folds = []
  for evaluation_source in sorted(source_groups):
    fit_groups = {
      source: source_routes for source, source_routes in source_groups.items()
      if source != evaluation_source
    }
    evaluation_groups = {evaluation_source: source_groups[evaluation_source]}
    fit_routes = tuple(
      route for source_routes in fit_groups.values() for route in source_routes
    )
    evaluation_routes = evaluation_groups[evaluation_source]
    fold_blockers = []
    if not _coverage(fit_routes)[3]:
      fold_blockers.append('FIT_COUNT_COVERAGE_INSUFFICIENT')
      estimate = None
    else:
      estimate = _tls(fit_groups)
      if estimate is None:
        fold_blockers.append('FIT_NUMERICALLY_UNIDENTIFIABLE')

    if estimate is None:
      fold = TorqueSourceLosoFold(
        evaluation_source_commit=evaluation_source,
        fit_source_count=len(fit_groups),
        fit_route_count=len(fit_routes),
        evaluation_route_count=len(evaluation_routes),
        evaluation_point_count=sum(route.point_count for route in evaluation_routes),
        fit_estimate=pooled_estimate,
        factor_relative_deviation_from_pooled=math.inf,
        offset_absolute_deviation_from_pooled_mps2=math.inf,
        evaluation_residual_rmse_mps2=math.inf,
        evaluation_mean_residual_mps2=math.inf,
        evaluation_to_fit_rmse_ratio=math.inf,
        blockers=tuple(fold_blockers),
        fold_pass=False,
      )
      folds.append(fold)
      continue
    factor_deviation = abs(estimate.lat_accel_factor - pooled_estimate.lat_accel_factor) / pooled_estimate.lat_accel_factor
    offset_deviation = abs(estimate.lat_accel_offset_mps2 - pooled_estimate.lat_accel_offset_mps2)
    evaluation_rmse, evaluation_mean = _source_residual_metrics(
      evaluation_groups,
      estimate.lat_accel_factor,
      estimate.lat_accel_offset_mps2,
    )
    if estimate.residual_rmse_mps2 <= 1e-15:
      evaluation_ratio = 1. if evaluation_rmse <= 1e-15 else math.inf
    else:
      evaluation_ratio = evaluation_rmse / estimate.residual_rmse_mps2

    if factor_deviation > policy.maximum_fold_factor_relative_deviation:
      fold_blockers.append('FOLD_FACTOR_DEVIATION_EXCESSIVE')
    if offset_deviation > policy.maximum_fold_offset_absolute_deviation_mps2:
      fold_blockers.append('FOLD_OFFSET_DEVIATION_EXCESSIVE')
    if evaluation_rmse > policy.maximum_fold_evaluation_rmse_mps2:
      fold_blockers.append('EVALUATION_RMSE_EXCESSIVE')
    if abs(evaluation_mean) > policy.maximum_fold_evaluation_absolute_mean_residual_mps2:
      fold_blockers.append('EVALUATION_MEAN_RESIDUAL_EXCESSIVE')
    if evaluation_rmse > (
        estimate.residual_rmse_mps2 * policy.maximum_fold_evaluation_to_fit_rmse_ratio +
        policy.evaluation_to_fit_rmse_absolute_allowance_mps2):
      fold_blockers.append('EVALUATION_TO_FIT_RMSE_DEGRADATION')

    folds.append(TorqueSourceLosoFold(
      evaluation_source_commit=evaluation_source,
      fit_source_count=len(fit_groups),
      fit_route_count=len(fit_routes),
      evaluation_route_count=len(evaluation_routes),
      evaluation_point_count=sum(route.point_count for route in evaluation_routes),
      fit_estimate=estimate,
      factor_relative_deviation_from_pooled=factor_deviation,
      offset_absolute_deviation_from_pooled_mps2=offset_deviation,
      evaluation_residual_rmse_mps2=evaluation_rmse,
      evaluation_mean_residual_mps2=evaluation_mean,
      evaluation_to_fit_rmse_ratio=evaluation_ratio,
      blockers=tuple(fold_blockers),
      fold_pass=not fold_blockers,
    ))
  folds = tuple(folds)
  all_folds_pass = all(fold.fold_pass for fold in folds)
  status = (
    'SOURCE_LOSO_DEVELOPMENT_DIAGNOSTIC_PASS'
    if all_folds_pass else 'SOURCE_LOSO_DEVELOPMENT_DIAGNOSTIC_REJECTED'
  )
  diagnostic_blockers = () if all_folds_pass else ('ONE_OR_MORE_SOURCE_FOLDS_FAILED',)
  return TorqueSourceLosoReport(
    status=status,
    blockers=diagnostic_blockers + AUTHORITY_BLOCKERS,
    input_sha256=digest,
    eligible_route_count=len(eligible),
    excluded_low_point_route_count=excluded,
    source_count=source_count,
    point_count=point_count,
    maximum_source_point_share=max_source_share,
    pooled_estimate=pooled_estimate,
    folds=folds,
    maximum_fold_factor_relative_deviation=max(fold.factor_relative_deviation_from_pooled for fold in folds),
    maximum_fold_offset_absolute_deviation_mps2=max(fold.offset_absolute_deviation_from_pooled_mps2 for fold in folds),
    maximum_fold_evaluation_rmse_mps2=max(fold.evaluation_residual_rmse_mps2 for fold in folds),
    maximum_fold_evaluation_absolute_mean_residual_mps2=max(abs(fold.evaluation_mean_residual_mps2) for fold in folds),
    maximum_fold_evaluation_to_fit_rmse_ratio=max(fold.evaluation_to_fit_rmse_ratio for fold in folds),
    mean_fold_evaluation_rmse_mps2=sum(fold.evaluation_residual_rmse_mps2 for fold in folds) / len(folds),
    all_source_folds_pass=all_folds_pass,
    fit_executed=True,
  )
