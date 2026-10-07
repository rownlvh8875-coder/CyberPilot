"""Negative, metadata-only audit of local curvature/yaw reference candidates.

No source bytes are opened here. Caller-reviewed classifications and content
identities are bound to a frozen inventory digest; they are not authenticated.
This report cannot create strict reference evidence or launch comparison workers.
Even an external geometry claim requires a separate reviewed sealed producer.
"""
from dataclasses import asdict, dataclass, field
import hashlib
import json

from openpilot.tools.cyber_autotune.contracts import is_sha256


REQUIRED_FAMILIES = (
  'MODEL_GEOMETRY', 'PIXEL_DIAGNOSTIC', 'RECORDED_REPLAY',
  'INITIAL_STATE', 'GPS_POSE', 'D3Y_CALIBRATION',
)
# Evidence capabilities found in the audited source paths, not quality thresholds.
FAMILY_BLOCKERS = {
  'MODEL_GEOMETRY': ('MODEL_OUTPUT_NOT_INDEPENDENT_TRUTH',),
  'PIXEL_DIAGNOSTIC': (
    'PIXEL_GEOMETRY_NOT_METRIC_ROAD_REFERENCE',
    'INDEPENDENT_DESIRED_PATH_UNAVAILABLE',
    'METRIC_FRAME_TIMEBASE_AND_UNCERTAINTY_UNREVIEWED',
  ),
  'RECORDED_REPLAY': ('REPLAY_IDENTITY_DOES_NOT_SUPPLY_ROAD_TRUTH',),
  'INITIAL_STATE': ('INITIAL_STATE_DOES_NOT_SUPPLY_ROAD_TRUTH',),
  'GPS_POSE': ('POSE_DOES_NOT_SUPPLY_LANE_GEOMETRY',),
  'D3Y_CALIBRATION': ('D3Y_POSITION_TRUTH_NOT_INDEPENDENT',),
  'EXTERNAL_GEOMETRY': ('EXTERNAL_GEOMETRY_REQUIRES_SEPARATE_PRODUCER_REVIEW',),
}
ROLES = (
  'DEVELOPMENT', 'DIAGNOSTIC', 'RETROSPECTIVE_EVALUATION',
  'DESCRIPTIVE_CALIBRATION', 'INDEPENDENT_REFERENCE', 'UNVERIFIED',
)
ARM_BLOCKERS = (
  'UPSTREAM_BASELINE_PROFILE_AND_SOURCE_NOT_FROZEN',
  'CYBER_CURRENT_NATIVE_CORE_EQUALS_BASELINE',
  'CYBER_CANDIDATE_FEEDBACK_BOUND_IMPLEMENTATION_NOT_FROZEN',
  'A3_REJECTION_REMAINS_IN_FORCE',
)


@dataclass(frozen=True)
class SourceAuditRecord:
  family: str
  artifact_sha256: str
  producer_source_sha256: str
  role: str
  candidate_outputs_used: bool | None
  semantic_opened_before_freeze: bool | None


@dataclass(frozen=True)
class SourceAuditInventory:
  version: int
  source_head: str
  scope_sha256: str
  review_sha256: str
  records: tuple[SourceAuditRecord, ...]


@dataclass(frozen=True)
class SourceAuditFinding:
  family: str
  artifact_sha256: str
  producer_source_sha256: str
  role: str
  candidate_outputs_used: bool | None
  semantic_opened_before_freeze: bool | None
  blockers: tuple[str, ...]


@dataclass(frozen=True)
class SourceAuditReport:
  blockers: tuple[str, ...]
  inventory_sha256: str | None = None
  source_head: str | None = None
  scope_sha256: str | None = None
  review_sha256: str | None = None
  findings: tuple[SourceAuditFinding, ...] = ()
  arm_blockers: tuple[str, ...] = ARM_BLOCKERS
  version: int = field(default=1, init=False)
  purpose: str = field(default='CURVATURE_YAW_SOURCE_AUDIT_ONLY', init=False)
  status: str = field(default='BLOCKED', init=False)
  claims_authenticated: bool = field(default=False, init=False)
  reference_producer_allowed: bool = field(default=False, init=False)
  comparison_execution_allowed: bool = field(default=False, init=False)
  runtime_accepted: bool = field(default=False, init=False)
  promotable: bool = field(default=False, init=False)
  vehicle_activation_allowed: bool = field(default=False, init=False)
  readiness: str = field(default='NOT_READY', init=False)
  vehicle_status: str = field(default='REAL_VEHICLE_UNVERIFIED', init=False)
  safety_status: str = field(default='VEHICLE_ACTIVATION_BLOCKED', init=False)


def _canonical(value) -> bytes:
  return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def _inventory_valid(value) -> bool:
  if (
    type(value) is not SourceAuditInventory
    or type(value.version) is not int or value.version != 1
    or type(value.source_head) is not str or len(value.source_head) != 40
    or any(char not in '0123456789abcdef' for char in value.source_head)
    or not is_sha256(value.scope_sha256) or not is_sha256(value.review_sha256)
    or type(value.records) is not tuple
    # One record per audited family, plus optional unreviewed external geometry.
    or len(value.records) > len(FAMILY_BLOCKERS)
  ):
    return False
  return all(
    type(record) is SourceAuditRecord
    and type(record.family) is str and record.family in FAMILY_BLOCKERS
    and is_sha256(record.artifact_sha256)
    and is_sha256(record.producer_source_sha256)
    and type(record.role) is str and record.role in ROLES
    and (record.candidate_outputs_used is None or type(record.candidate_outputs_used) is bool)
    and (record.semantic_opened_before_freeze is None or type(record.semantic_opened_before_freeze) is bool)
    for record in value.records
  )


def source_inventory_sha256(inventory: SourceAuditInventory) -> str:
  """Bind ordered metadata, source/producer identities, review and audit scope."""
  if not _inventory_valid(inventory):
    raise ValueError('INVALID_SOURCE_AUDIT_INVENTORY')
  return hashlib.sha256(_canonical(asdict(inventory))).hexdigest()


def assess_source_inventory(
  inventory: SourceAuditInventory,
  *,
  expected_inventory_sha256: str,
) -> SourceAuditReport:
  """Produce only a BLOCKED report; missing/unknown facts cannot grant authority.

  Scope is supplied as a digest of the caller's audit inventory, not an assertion
  about all possible driving data. Semantic timing is the historical reference
  acquisition order, not the order in which this metadata-only API was called.
  False leakage/order declarations still do not establish metric independence.
  """
  if not _inventory_valid(inventory) or not is_sha256(expected_inventory_sha256):
    return SourceAuditReport(blockers=('INVALID_SOURCE_AUDIT_INVENTORY',))
  observed = source_inventory_sha256(inventory)
  if observed != expected_inventory_sha256:
    return SourceAuditReport(blockers=('AUDIT_INVENTORY_BINDING_MISMATCH',))

  families = tuple(record.family for record in inventory.records)
  complete = (
    set(REQUIRED_FAMILIES).issubset(families)
    and len(families) == len(set(families))
  )
  blockers = []
  if not complete:
    blockers.append('AUDIT_SCOPE_INCOMPLETE_OR_DUPLICATE')
  if 'EXTERNAL_GEOMETRY' in families:
    blockers.append('EXTERNAL_GEOMETRY_REQUIRES_SEPARATE_PRODUCER_REVIEW')
  elif complete:
    blockers.append('REAL_REFERENCE_UNAVAILABLE_IN_AUDITED_SCOPE')

  findings = []
  for record in inventory.records:
    reasons = list(FAMILY_BLOCKERS[record.family])
    if record.role == 'INDEPENDENT_REFERENCE':
      reasons.append('INDEPENDENT_ROLE_NOT_SUBSTANTIATED')
    if record.candidate_outputs_used is None:
      reasons.append('CANDIDATE_LEAKAGE_UNVERIFIED')
    elif record.candidate_outputs_used:
      reasons.append('CANDIDATE_OUTPUT_LEAKAGE')
    if record.semantic_opened_before_freeze is None:
      reasons.append('SEMANTIC_OPEN_ORDER_UNVERIFIED')
    elif record.semantic_opened_before_freeze:
      reasons.append('SEMANTIC_CONTENT_PRECEDES_REFERENCE_FREEZE')
    findings.append(SourceAuditFinding(**asdict(record), blockers=tuple(reasons)))
  return SourceAuditReport(
    blockers=tuple(blockers),
    inventory_sha256=observed,
    source_head=inventory.source_head,
    scope_sha256=inventory.scope_sha256,
    review_sha256=inventory.review_sha256,
    findings=tuple(findings),
  )


def encode_source_audit_report(report: SourceAuditReport) -> bytes:
  """Encode sanitized enum/hash/boolean metadata, never reference geometry."""
  if type(report) is not SourceAuditReport:
    raise ValueError('INVALID_SOURCE_AUDIT_REPORT')
  if report.inventory_sha256 is None:
    valid = any(report == SourceAuditReport(blockers=(reason,)) for reason in (
      'INVALID_SOURCE_AUDIT_INVENTORY', 'AUDIT_INVENTORY_BINDING_MISMATCH',
    ))
  else:
    try:
      records = tuple(
        SourceAuditRecord(
          finding.family, finding.artifact_sha256, finding.producer_source_sha256,
          finding.role, finding.candidate_outputs_used, finding.semantic_opened_before_freeze,
        )
        for finding in report.findings
      )
      inventory = SourceAuditInventory(
        1, report.source_head, report.scope_sha256, report.review_sha256, records,
      )
      valid = (
        is_sha256(report.inventory_sha256)
        and report == assess_source_inventory(
          inventory, expected_inventory_sha256=report.inventory_sha256,
        )
      )
    except (AttributeError, TypeError, ValueError):
      valid = False
  if not valid:
    raise ValueError('INVALID_SOURCE_AUDIT_REPORT')
  return _canonical(asdict(report))
