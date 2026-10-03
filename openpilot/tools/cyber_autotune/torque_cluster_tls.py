"""Route/source-cluster numerical stability for frozen torque sufficient statistics.

This module performs diagnostic pooled and leave-one-cluster-out Gram TLS only.
It never qualifies confidence, identifies deployable parameters, generates a
candidate, writes runtime state, or grants promotion authority.
"""
from dataclasses import dataclass, field
import hashlib
import json
import re

import numpy as np

from openpilot.tools.cyber_autotune.contracts import finite_number, is_sha256
from openpilot.tools.cyber_autotune.torque_gram_tls import TorqueGramInput, fit_torque_gram
from openpilot.tools.cyber_autotune.torque_identification import TorqueEstimate


REQUIRED_MINIMUM_ROUTES = 20
REQUIRED_MINIMUM_SOURCE_COMMITS = 10
REQUIRED_MAXIMUM_ROUTE_SHARE = .25
REQUIRED_MAXIMUM_SOURCE_SHARE = .40
REQUIRED_MAXIMUM_ROUTE_FACTOR_DELTA = .05
REQUIRED_MAXIMUM_SOURCE_FACTOR_DELTA = .05
REQUIRED_MAXIMUM_ROUTE_OFFSET_DELTA = .05
REQUIRED_MAXIMUM_SOURCE_OFFSET_DELTA = .05
REQUIRED_MAXIMUM_FACTOR_JACKKNIFE_RELATIVE_SE = .05
REQUIRED_MAXIMUM_OFFSET_JACKKNIFE_SE = .05


@dataclass(frozen=True)
class TorqueRouteGram:
  route_sha256: str
  source_commit: str
  gram: TorqueGramInput


@dataclass(frozen=True)
class TorqueClusterTLSPolicy:
  policy_sha256: str
  minimum_nonempty_route_clusters: int
  minimum_source_commits: int
  maximum_route_point_share: float
  maximum_source_commit_point_share: float
  maximum_route_factor_relative_delta: float
  maximum_source_factor_relative_delta: float
  maximum_route_offset_delta_mps2: float
  maximum_source_offset_delta_mps2: float
  maximum_factor_jackknife_relative_se: float
  maximum_offset_jackknife_se_mps2: float


@dataclass(frozen=True)
class ClusterOmissionEstimate:
  cluster_id: str
  omitted_route_count: int
  retained_route_count: int
  retained_point_count: int
  estimate: TorqueEstimate
  factor_relative_delta: float
  offset_delta_mps2: float


@dataclass(frozen=True)
class TorqueClusterTLSReport:
  status: str
  blockers: tuple[str, ...]
  policy_sha256: str | None = None
  route_cluster_count: int = 0
  source_commit_count: int = 0
  point_count: int = 0
  maximum_route_point_share: float = 0.0
  maximum_source_commit_point_share: float = 0.0
  pooled_estimate: TorqueEstimate | None = None
  leave_one_route_out: tuple[ClusterOmissionEstimate, ...] = ()
  leave_one_source_commit_out: tuple[ClusterOmissionEstimate, ...] = ()
  maximum_route_factor_relative_delta: float = 0.0
  maximum_source_factor_relative_delta: float = 0.0
  maximum_route_offset_delta_mps2: float = 0.0
  maximum_source_offset_delta_mps2: float = 0.0
  factor_jackknife_relative_se: float = 0.0
  offset_jackknife_se_mps2: float = 0.0
  stability_gate_passed: bool = False
  numerical_fit_executed: bool = False
  confidence_qualified: bool = field(default=False, init=False)
  parameter_identification_qualified: bool = field(default=False, init=False)
  candidate_generation_allowed: bool = field(default=False, init=False)
  runtime_accepted: bool = field(default=False, init=False)
  promotable: bool = field(default=False, init=False)


def _valid_policy(policy) -> bool:
  return (
    type(policy) is TorqueClusterTLSPolicy and is_sha256(policy.policy_sha256) and
    type(policy.minimum_nonempty_route_clusters) is int and
    policy.minimum_nonempty_route_clusters == REQUIRED_MINIMUM_ROUTES and
    type(policy.minimum_source_commits) is int and
    policy.minimum_source_commits == REQUIRED_MINIMUM_SOURCE_COMMITS and
    type(policy.maximum_route_point_share) is float and
    policy.maximum_route_point_share == REQUIRED_MAXIMUM_ROUTE_SHARE and
    type(policy.maximum_source_commit_point_share) is float and
    policy.maximum_source_commit_point_share == REQUIRED_MAXIMUM_SOURCE_SHARE and
    type(policy.maximum_route_factor_relative_delta) is float and
    policy.maximum_route_factor_relative_delta == REQUIRED_MAXIMUM_ROUTE_FACTOR_DELTA and
    type(policy.maximum_source_factor_relative_delta) is float and
    policy.maximum_source_factor_relative_delta == REQUIRED_MAXIMUM_SOURCE_FACTOR_DELTA and
    type(policy.maximum_route_offset_delta_mps2) is float and
    policy.maximum_route_offset_delta_mps2 == REQUIRED_MAXIMUM_ROUTE_OFFSET_DELTA and
    type(policy.maximum_source_offset_delta_mps2) is float and
    policy.maximum_source_offset_delta_mps2 == REQUIRED_MAXIMUM_SOURCE_OFFSET_DELTA and
    type(policy.maximum_factor_jackknife_relative_se) is float and
    policy.maximum_factor_jackknife_relative_se == REQUIRED_MAXIMUM_FACTOR_JACKKNIFE_RELATIVE_SE and
    type(policy.maximum_offset_jackknife_se_mps2) is float and
    policy.maximum_offset_jackknife_se_mps2 == REQUIRED_MAXIMUM_OFFSET_JACKKNIFE_SE
  )


def _valid_route(route) -> bool:
  if (type(route) is not TorqueRouteGram or not is_sha256(route.route_sha256) or
      type(route.source_commit) is not str or re.fullmatch(r'[0-9a-f]{40}', route.source_commit) is None or
      type(route.gram) is not TorqueGramInput):
    return False
  report = fit_torque_gram(route.gram)
  return not (report.status == 'BLOCKED' and report.blockers == ('INVALID_GRAM_INPUT',))


def _blocked(reason: str, policy=None, route_count=0, source_count=0,
             point_count=0, max_route_share=0., max_source_share=0.) -> TorqueClusterTLSReport:
  return TorqueClusterTLSReport(
    status='BLOCKED', blockers=(reason,),
    policy_sha256=None if policy is None else policy.policy_sha256,
    route_cluster_count=route_count, source_commit_count=source_count,
    point_count=point_count, maximum_route_point_share=max_route_share,
    maximum_source_commit_point_share=max_source_share,
  )


def _combine(routes: tuple[TorqueRouteGram, ...], policy_sha256: str, label: str) -> TorqueGramInput:
  ordered = tuple(sorted(routes, key=lambda route: route.route_sha256))
  point_count = sum(route.gram.point_count for route in ordered)
  gram = np.zeros((3, 3), dtype=np.float64)
  buckets = [0] * 8
  bindings = []
  for route in ordered:
    gram += np.array(route.gram.gram_xtx, dtype=np.float64)
    buckets = [left + right for left, right in zip(buckets, route.gram.bucket_counts, strict=True)]
    bindings.append((route.route_sha256, route.source_commit, route.gram.source_sha256))
  source_sha256 = hashlib.sha256(json.dumps({
    'policy_sha256': policy_sha256,
    'label': label,
    'routes': bindings,
  }, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
  return TorqueGramInput(
    point_count=point_count,
    gram_xtx=tuple(tuple(float(value) for value in row) for row in gram),
    bucket_counts=tuple(buckets),
    source_sha256=source_sha256,
  )


def _omission(cluster_id: str, omitted_count: int, retained: tuple[TorqueRouteGram, ...],
              policy: TorqueClusterTLSPolicy, pooled: TorqueEstimate) -> ClusterOmissionEstimate | None:
  report = fit_torque_gram(_combine(retained, policy.policy_sha256, f'omission:{cluster_id}'))
  if report.status != 'NUMERICAL_DIAGNOSTIC' or report.estimate is None:
    return None
  factor_delta = abs(report.estimate.lat_accel_factor - pooled.lat_accel_factor) / abs(pooled.lat_accel_factor)
  offset_delta = abs(report.estimate.lat_accel_offset_mps2 - pooled.lat_accel_offset_mps2)
  if not finite_number(factor_delta) or not finite_number(offset_delta):
    return None
  return ClusterOmissionEstimate(
    cluster_id=cluster_id,
    omitted_route_count=omitted_count,
    retained_route_count=len(retained),
    retained_point_count=sum(route.gram.point_count for route in retained),
    estimate=report.estimate,
    factor_relative_delta=float(factor_delta),
    offset_delta_mps2=float(offset_delta),
  )


def _jackknife_se(values: tuple[float, ...]) -> float:
  array = np.array(values, dtype=np.float64)
  mean = float(np.mean(array))
  return float(np.sqrt((len(array) - 1.) / len(array) * np.sum((array - mean) ** 2)))


def assess_cluster_tls(routes: tuple[TorqueRouteGram, ...], policy: TorqueClusterTLSPolicy) -> TorqueClusterTLSReport:
  """Evaluate pooled and leave-one-cluster-out numerical stability."""
  if not _valid_policy(policy):
    return _blocked('INVALID_CLUSTER_TLS_POLICY')
  if type(routes) is not tuple or not routes or any(not _valid_route(route) for route in routes):
    return _blocked('INVALID_ROUTE_GRAM', policy)
  if len({route.route_sha256 for route in routes}) != len(routes):
    return _blocked('DUPLICATE_ROUTE_ID', policy)

  ordered = tuple(sorted(routes, key=lambda route: route.route_sha256))
  route_count = len(ordered)
  source_commits = tuple(sorted({route.source_commit for route in ordered}))
  source_count = len(source_commits)
  point_count = sum(route.gram.point_count for route in ordered)
  if route_count < policy.minimum_nonempty_route_clusters:
    return _blocked('INSUFFICIENT_ROUTE_CLUSTERS', policy, route_count, source_count, point_count)
  if source_count < policy.minimum_source_commits:
    return _blocked('INSUFFICIENT_SOURCE_COMMITS', policy, route_count, source_count, point_count)
  if point_count <= 0:
    return _blocked('NO_CLUSTER_POINTS', policy, route_count, source_count)

  route_shares = tuple(route.gram.point_count / point_count for route in ordered)
  source_points = {
    commit: sum(route.gram.point_count for route in ordered if route.source_commit == commit)
    for commit in source_commits
  }
  source_shares = tuple(points / point_count for points in source_points.values())
  max_route_share = max(route_shares)
  max_source_share = max(source_shares)
  if max_route_share > policy.maximum_route_point_share:
    return _blocked('ROUTE_POINT_SHARE_DOMINANCE', policy, route_count, source_count,
                    point_count, max_route_share, max_source_share)
  if max_source_share > policy.maximum_source_commit_point_share:
    return _blocked('SOURCE_COMMIT_POINT_SHARE_DOMINANCE', policy, route_count, source_count,
                    point_count, max_route_share, max_source_share)

  pooled_report = fit_torque_gram(_combine(ordered, policy.policy_sha256, 'pooled'))
  if pooled_report.status != 'NUMERICAL_DIAGNOSTIC' or pooled_report.estimate is None:
    return _blocked('POOLED_GRAM_UNIDENTIFIABLE', policy, route_count, source_count,
                    point_count, max_route_share, max_source_share)
  pooled = pooled_report.estimate

  route_omissions = []
  for omitted in ordered:
    retained = tuple(route for route in ordered if route.route_sha256 != omitted.route_sha256)
    estimate = _omission(omitted.route_sha256, 1, retained, policy, pooled)
    if estimate is None:
      return _blocked('ROUTE_OMISSION_UNIDENTIFIABLE', policy, route_count, source_count,
                      point_count, max_route_share, max_source_share)
    route_omissions.append(estimate)

  source_omissions = []
  for commit in source_commits:
    omitted_count = sum(route.source_commit == commit for route in ordered)
    retained = tuple(route for route in ordered if route.source_commit != commit)
    estimate = _omission(commit, omitted_count, retained, policy, pooled)
    if estimate is None:
      return _blocked('SOURCE_OMISSION_UNIDENTIFIABLE', policy, route_count, source_count,
                      point_count, max_route_share, max_source_share)
    source_omissions.append(estimate)

  route_omissions = tuple(route_omissions)
  source_omissions = tuple(source_omissions)
  max_route_factor = max(row.factor_relative_delta for row in route_omissions)
  max_source_factor = max(row.factor_relative_delta for row in source_omissions)
  max_route_offset = max(row.offset_delta_mps2 for row in route_omissions)
  max_source_offset = max(row.offset_delta_mps2 for row in source_omissions)
  factor_se = _jackknife_se(tuple(row.estimate.lat_accel_factor for row in route_omissions))
  offset_se = _jackknife_se(tuple(row.estimate.lat_accel_offset_mps2 for row in route_omissions))
  factor_relative_se = factor_se / abs(pooled.lat_accel_factor)
  if not all(finite_number(value) for value in (
      max_route_factor, max_source_factor, max_route_offset, max_source_offset,
      factor_relative_se, offset_se,
  )):
    return _blocked('NONFINITE_CLUSTER_STABILITY', policy, route_count, source_count,
                    point_count, max_route_share, max_source_share)

  blockers = []
  if max_route_factor > policy.maximum_route_factor_relative_delta:
    blockers.append('ROUTE_FACTOR_INSTABILITY')
  if max_source_factor > policy.maximum_source_factor_relative_delta:
    blockers.append('SOURCE_FACTOR_INSTABILITY')
  if max_route_offset > policy.maximum_route_offset_delta_mps2:
    blockers.append('ROUTE_OFFSET_INSTABILITY')
  if max_source_offset > policy.maximum_source_offset_delta_mps2:
    blockers.append('SOURCE_OFFSET_INSTABILITY')
  if factor_relative_se > policy.maximum_factor_jackknife_relative_se:
    blockers.append('FACTOR_JACKKNIFE_UNSTABLE')
  if offset_se > policy.maximum_offset_jackknife_se_mps2:
    blockers.append('OFFSET_JACKKNIFE_UNSTABLE')

  passed = not blockers
  status = 'CLUSTER_TLS_NUMERICAL_DIAGNOSTIC' if passed else 'BLOCKED'
  report_blockers = (
    ('CLUSTER_CONFIDENCE_NOT_QUALIFIED', 'CANDIDATE_GENERATION_NOT_AUTHORIZED')
    if passed else tuple(blockers)
  )
  return TorqueClusterTLSReport(
    status=status,
    blockers=report_blockers,
    policy_sha256=policy.policy_sha256,
    route_cluster_count=route_count,
    source_commit_count=source_count,
    point_count=point_count,
    maximum_route_point_share=float(max_route_share),
    maximum_source_commit_point_share=float(max_source_share),
    pooled_estimate=pooled,
    leave_one_route_out=route_omissions,
    leave_one_source_commit_out=source_omissions,
    maximum_route_factor_relative_delta=float(max_route_factor),
    maximum_source_factor_relative_delta=float(max_source_factor),
    maximum_route_offset_delta_mps2=float(max_route_offset),
    maximum_source_offset_delta_mps2=float(max_source_offset),
    factor_jackknife_relative_se=float(factor_relative_se),
    offset_jackknife_se_mps2=float(offset_se),
    stability_gate_passed=passed,
    numerical_fit_executed=True,
  )
