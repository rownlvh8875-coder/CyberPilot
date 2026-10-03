"""Offline reviewed-manifest binding and bounded read-only artifact integrity.

The policy is a TRUSTED caller input, never created from an untrusted manifest
inside this validator. A digest does not authenticate a reviewer, firmware,
lane truth, masks, or plant validity. Producer payload verification and native
evaluation remain pending. No raw bytes/paths escape in the result, and no
qualification, candidate-generation, or runtime authority is granted.

Only POSIX local regular files are supported. Descriptor-relative O_NOFOLLOW
walk rejects symlink races; hardlinks and special files are not read. A hostile
mount namespace or privileged filesystem adversary is outside this contract.
"""
from dataclasses import asdict, dataclass, field
import hashlib
import json
import os
from pathlib import Path
import stat

from openpilot.tools.cyber_autotune.contracts import is_sha256
from openpilot.tools.cyber_autotune.coverage import CoverageGroup, CoverageReport, summarize_coverage, valid_group
from openpilot.tools.cyber_autotune.preflight import CoveragePolicy


DEVELOPMENT_ROLES = frozenset({'development_fit', 'development_evaluation'})
# These digests bind reviewed payloads, NOT claims that this module has inspected
# their physical meaning. Missing/unknown firmware etc. must remain absent.
PROVENANCE_KEYS = frozenset({
  'source', 'submodules', 'dirty_overlay', 'car_params', 'firmware', 'model',
  'schema', 'runtime_epoch', 'configuration', 'signal_units_frames_stages',
  'timestamp_join_staleness', 'plant_domain_scale_delay_uncertainty',
  'metric_v2', 'masks', 'classifier', 'reset_policy',
})


@dataclass(frozen=True)
class DatasetEvidence:
  dataset_id: str
  role: str
  path: str
  artifact_sha256: str
  size_bytes: int
  group: CoverageGroup
  provenance: tuple[tuple[str, str], ...]
  previously_seen: bool


@dataclass(frozen=True)
class EvidenceManifest:
  datasets: tuple[DatasetEvidence, ...]
  schema_version: int = 2


@dataclass(frozen=True)
class EvidencePolicy:
  review_sha256: str
  manifest_sha256: str
  allowed_paths: tuple[str, ...]
  maximum_artifact_bytes: int
  coverage: CoveragePolicy


@dataclass(frozen=True)
class EvidenceReport:
  status: str
  blockers: tuple[str, ...]
  artifacts_verified: int = 0
  coverage: tuple[tuple[str, CoverageReport], ...] = ()
  offline_evaluable: bool = field(default=False, init=False)
  candidate_generation_allowed: bool = field(default=False, init=False)
  runtime_accepted: bool = field(default=False, init=False)


def manifest_sha256(manifest: EvidenceManifest) -> str:
  """Review helper only; never use to auto-approve incoming evidence."""
  return hashlib.sha256(json.dumps(asdict(manifest), sort_keys=True, separators=(',', ':'),
                                   ensure_ascii=True, allow_nan=False).encode('utf-8')).hexdigest()


def _canonical_path(value: str) -> bool:
  if not isinstance(value, str) or '\x00' in value or not value.startswith('/') or value.startswith('//'):
    return False
  path = Path(value)
  return str(path) == value and '..' not in path.parts and len(path.parts) > 1


def _valid_provenance(provenance) -> bool:
  if not isinstance(provenance, tuple) or any(not isinstance(item, tuple) or len(item) != 2 or
                                           not isinstance(item[0], str) or not is_sha256(item[1]) for item in provenance):
    return False
  keys = tuple(key for key, _ in provenance)
  return len(keys) == len(set(keys)) and set(keys) == PROVENANCE_KEYS


def _preflight(manifest: EvidenceManifest, policy: EvidencePolicy) -> tuple[tuple[str, ...], tuple[tuple[str, CoverageReport], ...]]:
  if os.name != 'posix' or not all(hasattr(os, name) for name in ('O_NOFOLLOW', 'O_DIRECTORY', 'O_NONBLOCK')):
    return ('UNSUPPORTED_PLATFORM',), ()
  if (not isinstance(policy, EvidencePolicy) or not is_sha256(policy.review_sha256) or not is_sha256(policy.manifest_sha256) or
      type(policy.maximum_artifact_bytes) is not int or policy.maximum_artifact_bytes <= 0 or
      not isinstance(policy.coverage, CoveragePolicy) or not isinstance(policy.allowed_paths, tuple) or
      not policy.allowed_paths or not all(_canonical_path(path) for path in policy.allowed_paths) or
      len(set(policy.allowed_paths)) != len(policy.allowed_paths)):
    return ('INVALID_TRUSTED_POLICY',), ()
  if (not isinstance(manifest, EvidenceManifest) or type(manifest.schema_version) is not int or manifest.schema_version != 2 or
      not isinstance(manifest.datasets, tuple) or not manifest.datasets or
      not all(isinstance(item, DatasetEvidence) for item in manifest.datasets)):
    return ('INVALID_MANIFEST',), ()
  # Check ALL roles before touching ANY artifact, including earlier safe entries.
  if any(not isinstance(item.role, str) or item.role not in DEVELOPMENT_ROLES for item in manifest.datasets):
    return ('DISALLOWED_DATASET_ROLE',), ()
  for item in manifest.datasets:
    if (not isinstance(item.dataset_id, str) or not item.dataset_id.strip() or type(item.previously_seen) is not bool or
        not _canonical_path(item.path) or item.path not in policy.allowed_paths or
        not is_sha256(item.artifact_sha256) or type(item.size_bytes) is not int or
        not 0 < item.size_bytes <= policy.maximum_artifact_bytes or not valid_group(item.group) or
        not _valid_provenance(item.provenance)):
      return ('INVALID_DATASET_CONTRACT',), ()
  if len({item.dataset_id for item in manifest.datasets}) != len(manifest.datasets):
    return ('DUPLICATE_DATASET_ID',), ()
  # Never accept a different serialization on the basis of path/hash alone.
  if manifest_sha256(manifest) != policy.manifest_sha256:
    return ('REVIEWED_MANIFEST_MISMATCH',), ()
  if {item.role for item in manifest.datasets} != DEVELOPMENT_ROLES:
    return ('MISSING_DEVELOPMENT_SPLIT',), ()
  for i, item in enumerate(manifest.datasets):
    for other in manifest.datasets[:i]:
      same_artifact = item.artifact_sha256 == other.artifact_sha256 or item.path == other.path
      item_group = (item.group.vehicle_group, item.group.route_group, item.group.day_group)
      other_group = (other.group.vehicle_group, other.group.route_group, other.group.day_group)
      if same_artifact and item_group != other_group:
        return ('ARTIFACT_GROUP_CONFLICT',), ()
      if item.role != other.role and (item.artifact_sha256 == other.artifact_sha256 or item.path == other.path or
                                     item.group.route_group == other.group.route_group or
                                     (item.group.vehicle_group, item.group.day_group) == (other.group.vehicle_group, other.group.day_group)):
        return ('FIT_EVALUATION_LEAKAGE',), ()
  coverage = tuple((role, summarize_coverage(tuple(item.group for item in manifest.datasets if item.role == role), policy.coverage))
                   for role in sorted(DEVELOPMENT_ROLES))
  if any(not report.sufficient for _, report in coverage):
    return ('CORPUS_COVERAGE_INSUFFICIENT',), coverage
  # Metadata-only resolution before any content open. The descriptor walk below
  # separately guards against a component being replaced by a symlink afterward.
  try:
    if any(str(Path(item.path).resolve(strict=True)) != item.path for item in manifest.datasets):
      return ('NONCANONICAL_OR_SYMLINK_PATH',), coverage
  except (OSError, RuntimeError, ValueError):
    return ('PATH_RESOLUTION_FAILED',), coverage
  return (), coverage


def _fingerprint(info):
  return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns, info.st_nlink, info.st_mode


def _verify_file(item: DatasetEvidence) -> bool:
  """Hash a bounded stable descriptor, never following a symlink component."""
  directory = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
  fd = None
  try:
    parts = Path(item.path).parts[1:]
    for part in parts[:-1]:
      child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
      os.close(directory)
      directory = child
    fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
    before = os.fstat(fd)
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size != item.size_bytes:
      return False
    digest = hashlib.sha256()
    remaining = item.size_bytes
    while remaining:
      data = os.read(fd, min(1024 * 1024, remaining))
      if not data:
        return False
      digest.update(data)
      remaining -= len(data)
    # One bounded extra byte detects growth; fstat detects metadata/identity drift.
    if os.read(fd, 1) or _fingerprint(before) != _fingerprint(os.fstat(fd)):
      return False
    return digest.hexdigest() == item.artifact_sha256
  finally:
    if fd is not None:
      os.close(fd)
    os.close(directory)


def verify_evidence(manifest: EvidenceManifest, policy: EvidencePolicy) -> EvidenceReport:
  """Review binding + file integrity + coverage only, not provenance semantics.

No automatic policy generation, directory discovery, raw export or device I/O.
Counts are reported per split. Partial reads on I/O failure cannot become PASS.
"""
  blockers, coverage = _preflight(manifest, policy)
  if blockers:
    return EvidenceReport('BLOCKED', blockers, coverage=coverage)
  verified = 0
  for item in manifest.datasets:
    try:
      valid = _verify_file(item)
    except OSError:
      valid = False
    if not valid:
      return EvidenceReport('BLOCKED', ('ARTIFACT_INTEGRITY_FAILED',), verified, coverage)
    verified += 1
  return EvidenceReport('INTEGRITY_AND_COVERAGE_PASS', (), verified, coverage)
