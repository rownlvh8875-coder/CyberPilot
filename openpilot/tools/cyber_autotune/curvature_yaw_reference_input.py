"""Sealed local-file admission for curvature/yaw independent reference evidence.

This module opens one predeclared regular JSON file read-only, copies it into a
sealed memfd, and parses only the sealed snapshot. File grants and provenance
claims are structural evidence, not authentication or vehicle qualification.
"""
from contextlib import contextmanager
from dataclasses import asdict, dataclass
import fcntl
import hashlib
import json
import os
import stat

from openpilot.tools.cyber_autotune.contracts import is_sha256
from openpilot.tools.cyber_autotune.curvature_yaw_comparison import (
  CurvatureYawReferenceEvidence,
  reference_evidence_sha256,
  validate_reference_evidence,
)
from openpilot.tools.cyber_autotune.preflight import CoveragePolicy


MAX_REFERENCE_BYTES = 4 * 1024 * 1024
READ_CHUNK_BYTES = 1024 * 1024
ADD_SEALS = 1033
GET_SEALS = 1034
INPUT_SEALS = 0x000F
PURPOSE = 'CURVATURE_YAW_REFERENCE_EVIDENCE'
ROLE = 'INDEPENDENT_REFERENCE'


@dataclass(frozen=True)
class ReferenceEvidenceGrant:
  root: str
  path: str
  size_bytes: int
  file_sha256: str
  evidence_sha256: str
  manifest_sha256: str
  review_sha256: str
  role: str = ROLE


@dataclass(frozen=True)
class ReferenceEvidenceAdmission:
  status: str
  file_sha256: str
  evidence_sha256: str
  manifest_sha256: str
  review_sha256: str
  size_bytes: int
  role: str
  sealed: bool
  independent_primary_position_truth: bool
  candidate_outputs_used_for_reference: bool
  semantic_content_opened_before_manifest_freeze: bool
  runtime_accepted: bool = False
  promotable: bool = False
  vehicle_activation_allowed: bool = False


def _canonical(value) -> bytes:
  return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def _path_parts(value: str, *, absolute: bool) -> tuple[str, ...]:
  if (
    type(value) is not str
    or not value
    or len(value) > 4096
    or '\x00' in value
    or '\\' in value
    or value.startswith('/') != absolute
  ):
    raise ValueError('INVALID_REFERENCE_PATH')
  parts = tuple(value[1:].split('/')) if absolute else tuple(value.split('/'))
  if any(part in ('', '.', '..') for part in parts):
    raise ValueError('INVALID_REFERENCE_PATH')
  return parts


def _grant_valid(grant) -> bool:
  return (
    type(grant) is ReferenceEvidenceGrant
    and type(grant.size_bytes) is int
    and 0 < grant.size_bytes <= MAX_REFERENCE_BYTES
    and is_sha256(grant.file_sha256)
    and is_sha256(grant.evidence_sha256)
    and is_sha256(grant.manifest_sha256)
    and is_sha256(grant.review_sha256)
    and grant.role == ROLE
  )


def _open_directory(root: str) -> int:
  parts = _path_parts(root, absolute=True)
  fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
  try:
    for part in parts:
      child = os.open(
        part,
        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
        dir_fd=fd,
      )
      os.close(fd)
      fd = child
    return fd
  except BaseException:
    os.close(fd)
    raise


def _open_file(root_fd: int, path: str) -> int:
  parts = _path_parts(path, absolute=False)
  parent = os.dup(root_fd)
  try:
    for part in parts[:-1]:
      child = os.open(
        part,
        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
        dir_fd=parent,
      )
      os.close(parent)
      parent = child
    return os.open(
      parts[-1],
      os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC,
      dir_fd=parent,
    )
  finally:
    os.close(parent)


def _write_all(fd: int, block: bytes) -> None:
  view = memoryview(block)
  while view:
    written = os.write(fd, view)
    if written <= 0:
      raise OSError('REFERENCE_SNAPSHOT_WRITE_FAILED')
    view = view[written:]


def _seal(fd: int) -> None:
  fcntl.fcntl(fd, ADD_SEALS, INPUT_SEALS)
  if fcntl.fcntl(fd, GET_SEALS) != INPUT_SEALS:
    raise ValueError('REFERENCE_INPUT_NOT_SEALED')
  os.lseek(fd, 0, os.SEEK_SET)


def _copy_sealed(grant: ReferenceEvidenceGrant) -> tuple[int, str]:
  root_fd = _open_directory(grant.root)
  try:
    original = _open_file(root_fd, grant.path)
  finally:
    os.close(root_fd)
  try:
    before = os.fstat(original)
    if (
      not stat.S_ISREG(before.st_mode)
      or before.st_size != grant.size_bytes
      or not 0 < before.st_size <= MAX_REFERENCE_BYTES
    ):
      raise ValueError('REFERENCE_TYPE_OR_SIZE_MISMATCH')
    retained = os.memfd_create(
      'cyber-reference',
      os.MFD_CLOEXEC | os.MFD_ALLOW_SEALING,
    )
    try:
      remaining = before.st_size
      digest = hashlib.sha256()
      while remaining:
        block = os.read(original, min(READ_CHUNK_BYTES, remaining))
        if not block:
          raise ValueError('REFERENCE_CHANGED_DURING_READ')
        remaining -= len(block)
        digest.update(block)
        _write_all(retained, block)
      after = os.fstat(original)
      identity_before = (
        before.st_dev, before.st_ino, before.st_size,
        before.st_mtime_ns, before.st_ctime_ns,
      )
      identity_after = (
        after.st_dev, after.st_ino, after.st_size,
        after.st_mtime_ns, after.st_ctime_ns,
      )
      observed = digest.hexdigest()
      if (
        os.read(original, 1)
        or identity_before != identity_after
        or observed != grant.file_sha256
      ):
        raise ValueError('REFERENCE_CHANGED_OR_HASH_MISMATCH')
      _seal(retained)
      return retained, observed
    except BaseException:
      os.close(retained)
      raise
  finally:
    os.close(original)


def _unique_pairs(pairs):
  result = {}
  for key, value in pairs:
    if key in result:
      raise ValueError('DUPLICATE_REFERENCE_JSON_KEY')
    result[key] = value
  return result


def _invalid_constant(_value):
  raise ValueError('NONFINITE_REFERENCE_JSON')


def _decode_payload(
  payload: bytes,
  *,
  grant: ReferenceEvidenceGrant,
  sample_count: int,
  coverage_policy: CoveragePolicy,
) -> CurvatureYawReferenceEvidence:
  try:
    document = json.loads(
      payload.decode('utf-8'),
      object_pairs_hook=_unique_pairs,
      parse_constant=_invalid_constant,
    )
  except (UnicodeError, RecursionError) as exc:
    raise ValueError('INVALID_REFERENCE_JSON') from exc

  expected = {
    'version', 'purpose', 'role', 'manifest_sha256',
    'review_sha256', 'independent_primary_position_truth',
    'candidate_outputs_used_for_reference',
    'semantic_content_opened_before_manifest_freeze',
    'desired_path_offset_m', 'lane_center_path_offset_m',
    'left_lane_edge_offset_m', 'right_lane_edge_offset_m',
    'vehicle_half_width_m', 'curve_phase_labels', 'coverage',
    'desired_path_source_sha256', 'lane_center_source_sha256',
    'lane_edge_source_sha256', 'vehicle_geometry_sha256',
  }
  if type(document) is not dict or set(document) != expected:
    raise ValueError('INVALID_REFERENCE_FIELDS')
  if (
    type(document['version']) is not int
    or document['version'] != 1
    or document['purpose'] != PURPOSE
    or document['role'] != grant.role
    or document['manifest_sha256'] != grant.manifest_sha256
    or document['review_sha256'] != grant.review_sha256
    or document['independent_primary_position_truth'] is not True
    or document['candidate_outputs_used_for_reference'] is not False
    or document['semantic_content_opened_before_manifest_freeze'] is not False
  ):
    raise ValueError('REFERENCE_PROVENANCE_REJECTED')

  evidence = CurvatureYawReferenceEvidence(
    desired_path_offset_m=tuple(document['desired_path_offset_m']),
    lane_center_path_offset_m=tuple(document['lane_center_path_offset_m']),
    left_lane_edge_offset_m=tuple(document['left_lane_edge_offset_m']),
    right_lane_edge_offset_m=tuple(document['right_lane_edge_offset_m']),
    vehicle_half_width_m=document['vehicle_half_width_m'],
    curve_phase_labels=tuple(document['curve_phase_labels']),
    coverage=tuple(
      tuple(item) if type(item) is list else item
      for item in document['coverage']
    ),
    desired_path_source_sha256=document['desired_path_source_sha256'],
    lane_center_source_sha256=document['lane_center_source_sha256'],
    lane_edge_source_sha256=document['lane_edge_source_sha256'],
    vehicle_geometry_sha256=document['vehicle_geometry_sha256'],
    coverage_review_sha256=document['review_sha256'],
  )
  validate_reference_evidence(evidence, sample_count, coverage_policy)
  if reference_evidence_sha256(evidence) != grant.evidence_sha256:
    raise ValueError('REFERENCE_EVIDENCE_DIGEST_MISMATCH')
  return evidence


@contextmanager
def retain_reference_evidence(
  grant: ReferenceEvidenceGrant,
  *,
  sample_count: int,
  coverage_policy: CoveragePolicy,
):
  """Yield a parsed immutable evidence object and non-authoritative admission receipt."""
  if not _grant_valid(grant):
    raise ValueError('INVALID_REFERENCE_GRANT')
  _path_parts(grant.root, absolute=True)
  _path_parts(grant.path, absolute=False)
  fd, observed = _copy_sealed(grant)
  try:
    payload = os.pread(fd, grant.size_bytes + 1, 0)
    if len(payload) != grant.size_bytes or observed != grant.file_sha256:
      raise ValueError('REFERENCE_SEALED_SIZE_MISMATCH')
    evidence = _decode_payload(
      payload,
      grant=grant,
      sample_count=sample_count,
      coverage_policy=coverage_policy,
    )
    receipt = ReferenceEvidenceAdmission(
      status='REFERENCE_EVIDENCE_RETAINED_SEALED',
      file_sha256=observed,
      evidence_sha256=reference_evidence_sha256(evidence),
      manifest_sha256=grant.manifest_sha256,
      review_sha256=grant.review_sha256,
      size_bytes=grant.size_bytes,
      role=grant.role,
      sealed=fcntl.fcntl(fd, GET_SEALS) == INPUT_SEALS,
      independent_primary_position_truth=True,
      candidate_outputs_used_for_reference=False,
      semantic_content_opened_before_manifest_freeze=False,
    )
    yield evidence, receipt
  finally:
    os.close(fd)


def encode_reference_document(
  evidence: CurvatureYawReferenceEvidence,
  *,
  manifest_sha256: str,
  review_sha256: str,
) -> bytes:
  """Test/producer helper for the strict v1 document; does not write files."""
  if (
    type(evidence) is not CurvatureYawReferenceEvidence
    or not is_sha256(manifest_sha256)
    or not is_sha256(review_sha256)
    or evidence.coverage_review_sha256 != review_sha256
  ):
    raise ValueError('INVALID_REFERENCE_DOCUMENT_INPUT')
  document = {
    'version': 1,
    'purpose': PURPOSE,
    'role': ROLE,
    'manifest_sha256': manifest_sha256,
    'review_sha256': review_sha256,
    'independent_primary_position_truth': True,
    'candidate_outputs_used_for_reference': False,
    'semantic_content_opened_before_manifest_freeze': False,
    **asdict(evidence),
  }
  document.pop('coverage_review_sha256', None)
  document['coverage'] = [list(item) for item in evidence.coverage]
  return _canonical(document)
