"""Route-cluster structural stability gate for grouped torque evidence.

This module evaluates only route-level coverage robustness. It never opens raw
points, runs TLS, computes statistical confidence, generates candidates, mutates
Params, or grants runtime/promotion authority.
"""
from dataclasses import dataclass, field
import re

from openpilot.tools.cyber_autotune.contracts import is_sha256
from openpilot.tools.cyber_autotune.evidence import PROVENANCE_KEYS
from openpilot.tools.cyber_autotune.torque_aggregation import (
  MIN_BUCKET_POINTS,
  MIN_POINTS_TOTAL,
  TorqueEpochEvidence,
)
from openpilot.tools.cyber_autotune.torque_identification import SIGNAL_CONTRACT


REQUIRED_MINIMUM_ROUTE_CLUSTERS = 4
REQUIRED_MAXIMUM_ROUTE_POINT_SHARE = 0.75


@dataclass(frozen=True)
class TorqueClusterPolicy:
  policy_sha256: str
  minimum_route_clusters: int
  maximum_route_point_share: float
  require_all_leave_one_route_out_count_thresholds: bool


@dataclass(frozen=True)
class TorqueRouteCluster:
  route_sha256: str
  source_commit: str
  group_count: int
  point_count: int
  bucket_counts: tuple[int, ...]
  point_share: float


@dataclass(frozen=True)
class LeaveOneRouteOutCoverage:
  omitted_route_sha256: str
  retained_route_count: int
  point_count: int
  bucket_counts: tuple[int, ...]
  bucket_deficits: tuple[int, ...]
  total_point_deficit: int
  thresholds_met: bool


@dataclass(frozen=True)
class TorqueClusterStabilityReport:
  status: str
  blockers: tuple[str, ...]
  policy_sha256: str | None = None
  route_cluster_count: int = 0
  nonempty_route_cluster_count: int = 0
  source_commit_count: int = 0
  point_count: int = 0
  maximum_route_point_share: float = 0.0
  routes: tuple[TorqueRouteCluster, ...] = ()
  leave_one_route_out: tuple[LeaveOneRouteOutCoverage, ...] = ()
  all_leave_one_route_out_count_thresholds_met: bool = False
  fit_executed: bool = field(default=False, init=False)
  confidence_qualified: bool = field(default=False, init=False)
  candidate_generation_allowed: bool = field(default=False, init=False)
  runtime_accepted: bool = field(default=False, init=False)
  promotable: bool = field(default=False, init=False)


def _blocked(reason, policy=None, routes=(), loo=(), point_count=0, max_share=0.0):
  nonempty_routes = tuple(route for route in routes if route.point_count > 0)
  source_count = len({route.source_commit for route in nonempty_routes})
  return TorqueClusterStabilityReport(
    status='BLOCKED',
    blockers=(reason,),
    policy_sha256=None if policy is None else policy.policy_sha256,
    route_cluster_count=len(routes),
    nonempty_route_cluster_count=len(nonempty_routes),
    source_commit_count=source_count,
    point_count=point_count,
    maximum_route_point_share=max_share,
    routes=routes,
    leave_one_route_out=loo,
    all_leave_one_route_out_count_thresholds_met=bool(loo) and all(row.thresholds_met for row in loo),
  )


def _valid_policy(policy) -> bool:
  return (
    type(policy) is TorqueClusterPolicy and
    is_sha256(policy.policy_sha256) and
    type(policy.minimum_route_clusters) is int and
    policy.minimum_route_clusters == REQUIRED_MINIMUM_ROUTE_CLUSTERS and
    type(policy.maximum_route_point_share) is float and
    policy.maximum_route_point_share == REQUIRED_MAXIMUM_ROUTE_POINT_SHARE and
    type(policy.require_all_leave_one_route_out_count_thresholds) is bool and
    policy.require_all_leave_one_route_out_count_thresholds
  )


def _valid_provenance(value) -> bool:
  if type(value) is not tuple or len(value) != len(PROVENANCE_KEYS):
    return False
  if any(type(item) is not tuple or len(item) != 2 or type(item[0]) is not str or
         not is_sha256(item[1]) for item in value):
    return False
  keys = tuple(key for key, _ in value)
  return len(keys) == len(set(keys)) and set(keys) == PROVENANCE_KEYS


def _valid_group(group) -> bool:
  return (
    type(group) is TorqueEpochEvidence and
    is_sha256(group.epoch_sha256) and
    is_sha256(group.route_sha256) and
    type(group.source_commit) is str and
    re.fullmatch(r'[0-9a-f]{40}', group.source_commit) is not None and
    type(group.start_segment) is int and
    type(group.end_segment) is int and
    0 <= group.start_segment <= group.end_segment and
    type(group.bucket_counts) is tuple and
    len(group.bucket_counts) == len(MIN_BUCKET_POINTS) and
    all(type(count) is int and 0 <= count <= 1500 for count in group.bucket_counts) and
    group.role == 'development_fit' and
    _valid_provenance(group.provenance) and
    group.signal_contract == SIGNAL_CONTRACT and
    is_sha256(group.algorithm_sha256)
  )


def _coverage(counts):
  point_count = sum(counts)
  deficits = tuple(max(0, minimum - count) for count, minimum in zip(counts, MIN_BUCKET_POINTS, strict=True))
  total_deficit = max(0, MIN_POINTS_TOTAL - point_count)
  return point_count, deficits, total_deficit, total_deficit == 0 and not any(deficits)


def assess_cluster_stability(groups: tuple[TorqueEpochEvidence, ...], policy: TorqueClusterPolicy) -> TorqueClusterStabilityReport:
  """Assess route-level structural robustness without numerical fitting."""
  if not _valid_policy(policy):
    return _blocked('INVALID_CLUSTER_POLICY')
  if type(groups) is not tuple or not groups or any(not _valid_group(group) for group in groups):
    return _blocked('INVALID_CLUSTER_GROUP', policy)
  if len({group.epoch_sha256 for group in groups}) != len(groups):
    return _blocked('DUPLICATE_EPOCH_ID', policy)
  if len({group.algorithm_sha256 for group in groups}) != 1:
    return _blocked('ALGORITHM_MISMATCH', policy)

  by_route = {}
  for group in groups:
    by_route.setdefault(group.route_sha256, []).append(group)

  if any(len({group.source_commit for group in route_groups}) != 1 for route_groups in by_route.values()):
    return _blocked('ROUTE_SOURCE_MISMATCH', policy)

  total_counts = tuple(sum(group.bucket_counts[index] for group in groups) for index in range(len(MIN_BUCKET_POINTS)))
  total_points = sum(total_counts)
  if total_points <= 0:
    return _blocked('NO_COVERAGE_POINTS', policy)

  routes = []
  for route_sha in sorted(by_route):
    route_groups = by_route[route_sha]
    counts = tuple(sum(group.bucket_counts[index] for group in route_groups) for index in range(len(MIN_BUCKET_POINTS)))
    points = sum(counts)
    routes.append(TorqueRouteCluster(
      route_sha256=route_sha,
      source_commit=route_groups[0].source_commit,
      group_count=len(route_groups),
      point_count=points,
      bucket_counts=counts,
      point_share=points / total_points,
    ))
  routes = tuple(routes)
  nonempty_routes = tuple(route for route in routes if route.point_count > 0)
  max_share = max(route.point_share for route in nonempty_routes)

  loo = []
  for omitted in nonempty_routes:
    counts = tuple(total_counts[index] - omitted.bucket_counts[index] for index in range(len(MIN_BUCKET_POINTS)))
    points, deficits, total_deficit, met = _coverage(counts)
    loo.append(LeaveOneRouteOutCoverage(
      omitted_route_sha256=omitted.route_sha256,
      retained_route_count=len(nonempty_routes) - 1,
      point_count=points,
      bucket_counts=counts,
      bucket_deficits=deficits,
      total_point_deficit=total_deficit,
      thresholds_met=met,
    ))
  loo = tuple(loo)
  all_loo_met = all(row.thresholds_met for row in loo)

  if len(nonempty_routes) < policy.minimum_route_clusters:
    return _blocked('INSUFFICIENT_ROUTE_CLUSTERS', policy, routes, loo, total_points, max_share)
  if max_share > policy.maximum_route_point_share:
    return _blocked('ROUTE_POINT_SHARE_DOMINANCE', policy, routes, loo, total_points, max_share)
  if policy.require_all_leave_one_route_out_count_thresholds and not all_loo_met:
    return _blocked('LEAVE_ONE_ROUTE_OUT_COUNT_COVERAGE_INSUFFICIENT', policy, routes, loo, total_points, max_share)

  return TorqueClusterStabilityReport(
    status='CLUSTER_STABILITY_STRUCTURAL_DIAGNOSTIC',
    blockers=('ROUTE_LEVEL_STATISTICAL_CONFIDENCE_NOT_ESTABLISHED', 'FIT_NOT_AUTHORIZED', 'CANDIDATE_GENERATION_NOT_AUTHORIZED'),
    policy_sha256=policy.policy_sha256,
    route_cluster_count=len(routes),
    nonempty_route_cluster_count=len(nonempty_routes),
    source_commit_count=len({route.source_commit for route in nonempty_routes}),
    point_count=total_points,
    maximum_route_point_share=max_share,
    routes=routes,
    leave_one_route_out=loo,
    all_leave_one_route_out_count_thresholds_met=all_loo_met,
  )
