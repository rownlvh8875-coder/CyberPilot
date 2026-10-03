"""Grouped torque-coverage admission; never flattens epochs or executes a fit.

This module combines only bounded aggregate counts from independently preserved
development-fit epochs. It does not consume raw torque points, infer sample
independence, establish provenance authenticity, or grant tuning/runtime authority.
"""
from dataclasses import asdict, dataclass, field
import hashlib
import json
import re

from openpilot.tools.cyber_autotune.contracts import is_sha256
from openpilot.tools.cyber_autotune.evidence import PROVENANCE_KEYS
from openpilot.tools.cyber_autotune.torque_identification import SIGNAL_CONTRACT


BUCKET_BOUNDS = (
  (-.5, -.3), (-.3, -.2), (-.2, -.1), (-.1, 0.),
  (0., .1), (.1, .2), (.2, .3), (.3, .5),
)
MIN_BUCKET_POINTS = (100, 300, 500, 500, 500, 500, 300, 100)
MIN_POINTS_TOTAL = 4000
MAX_POINTS_PER_BUCKET = 1500
MAX_GROUPS = 128
BOUNDARY_REASONS = frozenset({'START', 'CLOCK_RESET', 'MANIFEST_GAP', 'MALFORMED_PREVIOUS'})
BASE_DIAGNOSTIC_BLOCKERS = (
  'CROSS_GROUP_STATISTICAL_INDEPENDENCE_UNVERIFIED',
  'NATIVE_EPOCH_VALIDITY_NOT_ESTABLISHED',
  'FIT_NOT_AUTHORIZED',
  'CANDIDATE_GENERATION_NOT_AUTHORIZED',
)


@dataclass(frozen=True)
class TorqueEpochEvidence:
  epoch_sha256: str
  route_sha256: str
  source_commit: str
  start_segment: int
  end_segment: int
  bucket_counts: tuple[int, ...]
  role: str
  provenance: tuple[tuple[str, str], ...]
  signal_contract: str
  algorithm_sha256: str
  boundary_reason: str


@dataclass(frozen=True)
class TorquePointIdentityEvidence:
  summary_sha256: str
  manifest_sha256: str
  policy_sha256: str
  group_count: int
  nonempty_group_count: int
  point_count: int
  bucket_counts: tuple[int, ...]
  cross_group_duplicate_sample_id_count: int
  within_group_duplicate_sample_id_count: int
  within_group_duplicate_time_count: int
  within_group_nonincreasing_time_count: int
  raw_can_exported: bool
  gps_exported: bool
  video_exported: bool
  route_label_exported: bool
  fit_executed: bool
  candidate_generation_allowed: bool


@dataclass(frozen=True)
class TorqueAggregationInput:
  groups: tuple[TorqueEpochEvidence, ...]
  role: str
  selection_policy_sha256: str
  point_identity: TorquePointIdentityEvidence | None = None


@dataclass(frozen=True)
class TorqueAggregationReport:
  status: str
  blockers: tuple[str, ...]
  aggregate_sha256: str | None = None
  group_count: int = 0
  nonempty_group_count: int = 0
  point_count: int = 0
  bucket_counts: tuple[int, ...] = ()
  bucket_deficits: tuple[int, ...] = ()
  total_point_deficit: int = 0
  pooled_count_thresholds_met: bool = False
  point_identity_verified: bool = False
  raw_points_combined: bool = field(default=False, init=False)
  fit_executed: bool = field(default=False, init=False)
  parameter_identification_qualified: bool = field(default=False, init=False)
  candidate_generation_allowed: bool = field(default=False, init=False)
  runtime_accepted: bool = field(default=False, init=False)
  promotable: bool = field(default=False, init=False)


def _valid_provenance(value) -> bool:
  if type(value) is not tuple or len(value) != len(PROVENANCE_KEYS):
    return False
  if any(type(item) is not tuple or len(item) != 2 or type(item[0]) is not str or
         not is_sha256(item[1]) for item in value):
    return False
  keys = tuple(key for key, _ in value)
  return len(keys) == len(set(keys)) and set(keys) == PROVENANCE_KEYS


def _valid_group(group) -> bool:
  if (type(group) is not TorqueEpochEvidence or not is_sha256(group.epoch_sha256) or
      not is_sha256(group.route_sha256) or
      type(group.source_commit) is not str or re.fullmatch(r'[0-9a-f]{40}', group.source_commit) is None or
      type(group.start_segment) is not int or type(group.end_segment) is not int or
      group.start_segment < 0 or group.end_segment < group.start_segment or
      type(group.bucket_counts) is not tuple or len(group.bucket_counts) != len(MIN_BUCKET_POINTS) or
      any(type(count) is not int or not 0 <= count <= MAX_POINTS_PER_BUCKET for count in group.bucket_counts) or
      group.role != 'development_fit' or not _valid_provenance(group.provenance) or
      group.signal_contract != SIGNAL_CONTRACT or not is_sha256(group.algorithm_sha256) or
      group.boundary_reason not in BOUNDARY_REASONS):
    return False
  return True


def _valid_point_identity(value) -> bool:
  if (type(value) is not TorquePointIdentityEvidence or not is_sha256(value.summary_sha256) or
      not is_sha256(value.manifest_sha256) or not is_sha256(value.policy_sha256) or
      type(value.group_count) is not int or not 1 <= value.group_count <= MAX_GROUPS or
      type(value.nonempty_group_count) is not int or not 0 <= value.nonempty_group_count <= value.group_count or
      type(value.point_count) is not int or value.point_count < 0 or
      type(value.bucket_counts) is not tuple or len(value.bucket_counts) != len(MIN_BUCKET_POINTS) or
      any(type(count) is not int or count < 0 for count in value.bucket_counts) or
      any(type(count) is not int or count != 0 for count in (
        value.cross_group_duplicate_sample_id_count,
        value.within_group_duplicate_sample_id_count,
        value.within_group_duplicate_time_count,
        value.within_group_nonincreasing_time_count,
      )) or
      any(type(flag) is not bool or flag for flag in (
        value.raw_can_exported, value.gps_exported, value.video_exported,
        value.route_label_exported, value.fit_executed, value.candidate_generation_allowed,
      ))):
    return False
  return sum(value.bucket_counts) == value.point_count


def _blocked(reason: str) -> TorqueAggregationReport:
  return TorqueAggregationReport('BLOCKED', (reason,))


def _canonical_group(group: TorqueEpochEvidence) -> dict:
  row = asdict(group)
  row['provenance'] = sorted(group.provenance)
  return row


def aggregate_torque_coverage(request: TorqueAggregationInput) -> TorqueAggregationReport:
  """Combine structural bucket coverage while preserving independent group identity."""
  if (type(request) is not TorqueAggregationInput or request.role != 'development_fit' or
      not is_sha256(request.selection_policy_sha256) or type(request.groups) is not tuple or
      not 1 <= len(request.groups) <= MAX_GROUPS):
    return _blocked('INVALID_AGGREGATION_INPUT')
  if any(not _valid_group(group) for group in request.groups):
    return _blocked('INVALID_EPOCH_EVIDENCE')
  if any(group.role != request.role for group in request.groups):
    return _blocked('ROLE_MISMATCH')
  if len({group.epoch_sha256 for group in request.groups}) != len(request.groups):
    return _blocked('DUPLICATE_EPOCH_ID')
  if len({group.algorithm_sha256 for group in request.groups}) != 1:
    return _blocked('ALGORITHM_MISMATCH')
  if len({group.signal_contract for group in request.groups}) != 1:
    return _blocked('SIGNAL_CONTRACT_MISMATCH')

  ordered = tuple(sorted(request.groups, key=lambda group: group.epoch_sha256))
  routes = {}
  for group in ordered:
    routes.setdefault(group.route_sha256, []).append(group)
  for route_groups in routes.values():
    by_segment = sorted(route_groups, key=lambda group: (group.start_segment, group.end_segment, group.epoch_sha256))
    if len({group.source_commit for group in by_segment}) != 1:
      return _blocked('ROUTE_SOURCE_MISMATCH')
    for index, group in enumerate(by_segment):
      if index == 0:
        continue
      previous = by_segment[index - 1]
      if group.start_segment <= previous.end_segment:
        return _blocked('OVERLAPPING_ROUTE_EPOCHS')
      if group.boundary_reason == 'START':
        return _blocked('INVALID_ROUTE_BOUNDARY_SEQUENCE')
      segment_gap = group.start_segment - previous.end_segment
      if (segment_gap == 1 and group.boundary_reason != 'CLOCK_RESET') or (
          segment_gap > 1 and group.boundary_reason not in {'MANIFEST_GAP', 'MALFORMED_PREVIOUS'}):
        return _blocked('BOUNDARY_REASON_MISMATCH')

  bucket_counts = tuple(sum(group.bucket_counts[i] for group in ordered) for i in range(len(MIN_BUCKET_POINTS)))
  point_count = sum(bucket_counts)
  if point_count == 0:
    return _blocked('NO_COVERAGE_POINTS')
  nonempty_group_count = sum(sum(group.bucket_counts) > 0 for group in ordered)
  bucket_deficits = tuple(max(0, minimum - actual) for actual, minimum in zip(bucket_counts, MIN_BUCKET_POINTS, strict=True))
  total_point_deficit = max(0, MIN_POINTS_TOTAL - point_count)
  thresholds_met = total_point_deficit == 0 and not any(bucket_deficits)

  identity = request.point_identity
  if identity is None:
    point_identity_verified = False
    blockers = ('RAW_POINT_IDENTITY_UNVERIFIED',) + BASE_DIAGNOSTIC_BLOCKERS
    identity_payload = None
  else:
    if (not _valid_point_identity(identity) or identity.group_count != len(ordered) or
        identity.nonempty_group_count != nonempty_group_count or identity.point_count != point_count or
        identity.bucket_counts != bucket_counts):
      return _blocked('POINT_IDENTITY_EVIDENCE_MISMATCH')
    point_identity_verified = True
    blockers = BASE_DIAGNOSTIC_BLOCKERS
    identity_payload = asdict(identity)

  payload = {
    'role': request.role,
    'selection_policy_sha256': request.selection_policy_sha256,
    'groups': [_canonical_group(group) for group in ordered],
    'bucket_counts': bucket_counts,
    'point_count': point_count,
    'nonempty_group_count': nonempty_group_count,
    'pooled_count_thresholds_met': thresholds_met,
    'point_identity': identity_payload,
  }
  aggregate_sha256 = hashlib.sha256(json.dumps(
    payload, sort_keys=True, separators=(',', ':'), allow_nan=False,
  ).encode()).hexdigest()
  return TorqueAggregationReport(
    status='STRUCTURAL_COVERAGE_DIAGNOSTIC',
    blockers=blockers,
    aggregate_sha256=aggregate_sha256,
    group_count=len(ordered),
    nonempty_group_count=nonempty_group_count,
    point_count=point_count,
    bucket_counts=bucket_counts,
    bucket_deficits=bucket_deficits,
    total_point_deficit=total_point_deficit,
    pooled_count_thresholds_met=thresholds_met,
    point_identity_verified=point_identity_verified,
  )
