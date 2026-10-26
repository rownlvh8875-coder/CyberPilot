"""Four explicitly bound metadata files only; no model, member or array access.

The caller must first authenticate its private handoff/protocol and explicit human
B0 grant. Paths and outputs are private caller-owned data, never source constants.
Linux openat2 guards apply to each target open, not to the whole process.
"""

import ctypes
from dataclasses import dataclass
import errno
import hashlib
import json
import os
from pathlib import PurePosixPath
import platform
import re
import stat


RECORD_IDS = ('V4_REPEAT_1_RUN_MANIFEST', 'V4_REPEAT_2_RUN_MANIFEST', 'V1_REFERENCE_REPEAT_1_MANIFEST', 'V1_REFERENCE_REPEATABILITY_RECEIPT')
AUTHORITY_KEYS = frozenset(
  (
    'qualification_allowed',
    'reference_promotable',
    'sealed_reference_allowed',
    'vehicle_activation_allowed',
    'production_authority',
    'ta_execution',
    'sg_execution',
    'composition_authorized',
    'candidate_search_authorized',
    'publication_raw_data',
  )
)
# V4: 32 * (train6 + one-step6 + rollout16 + job2) + top3.
# V1: immutable public repeatability files_per_replica. No live size inspection.
MEMBER_LIMITS = (963, 963, 5250, 0)
MEMBER_NAME_LIMIT = 4095  # Linux PATH_MAX - terminating NUL; ASCII frozen names.
ENTRY_BYTES = MEMBER_NAME_LIMIT + 64 + 64  # Name, SHA256 and conservative JSON syntax/indent overhead.
FIXED_METADATA_BYTES = 4096  # All permitted non-map fields are fixed schema literals/digests/scalars.
BYTE_CAPS = {key: FIXED_METADATA_BYTES + count * ENTRY_BYTES for key, count in zip(RECORD_IDS, MEMBER_LIMITS, strict=True)}
JOBS = tuple(f'candidates/HRI_D{d:02}_L{length:02}/{fold}/receipt.json' for d in (0, 5, 10, 20) for length in (1, 5, 15, 45) for fold in ('FOLD_A', 'FOLD_B'))
SCOPE = 'ALL_32_JOBS_MODELS_NORMALIZERS_THRESHOLDS_PREDICTIONS_PATHS_GATES_SELECTION'


class B0Error(ValueError):
  """Only fixed codes leave the reader; never OS exception text or private paths."""

  def __init__(self, code):
    self.code = code
    super().__init__(code)


@dataclass(frozen=True)
class MetadataSpec:
  record_id: str
  path: str
  expected_receipt_sha256: str
  max_bytes: int
  expected_raw_sha256: str | None = None


@dataclass(frozen=True)
class IdentityPins:
  v4_manifest: str
  v1_manifest: str
  v1_repeatability: str
  v4_authorization: str
  v1_authorization: str


def _need(condition, code):
  if not condition:
    raise B0Error(code)


def _sha(value):
  return hashlib.sha256(value).hexdigest()


def _canonical(value):
  return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def _digest(value):
  return isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value) is not None


def _path(value, *, absolute):
  _need(isinstance(value, str) and re.fullmatch('[A-Za-z0-9_./-]+', value) is not None, 'B0_PATH_GRAMMAR_CONFLICT')
  p = PurePosixPath(value)
  _need(p.is_absolute() == absolute and str(p) == value and '..' not in p.parts and '.' not in p.parts, 'B0_PATH_GRAMMAR_CONFLICT')
  return p


class _OpenHow(ctypes.Structure):
  _fields_ = [('flags', ctypes.c_uint64), ('mode', ctypes.c_uint64), ('resolve', ctypes.c_uint64)]


def _open_relative(directory_fd, relative):
  _path(relative, absolute=False)
  _need(platform.system() == 'Linux' and platform.machine() in ('x86_64', 'aarch64'), 'B0_UNSUPPORTED_READER_ENVIRONMENT')
  # openat2=437 on these two explicitly supported Linux ABIs. No path fallback.
  library = ctypes.CDLL(None, use_errno=True)
  library.syscall.restype = ctypes.c_long
  how = _OpenHow(os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK, 0, 0x01 | 0x02 | 0x04 | 0x08)
  fd = library.syscall(ctypes.c_long(437), ctypes.c_int(directory_fd), ctypes.c_char_p(relative.encode()), ctypes.byref(how), ctypes.sizeof(how))
  if fd < 0:
    code = ctypes.get_errno()
    if code == errno.ENOENT:
      raise B0Error('B0_MISSING_EXACT_TARGET')
    if code in (errno.ENOSYS, errno.EINVAL):
      raise B0Error('B0_UNSUPPORTED_READER_ENVIRONMENT')
    raise B0Error('B0_PATH_GUARD_REJECTED')
  return int(fd)


def _mount_fd(root):
  """Open only explicit ancestor components, never list or follow an alias."""
  parts = _path(root, absolute=True).parts
  fd = os.open('/', os.O_PATH | os.O_DIRECTORY | os.O_CLOEXEC)
  try:
    for part in parts[1:]:
      child = os.open(part, os.O_PATH | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW, dir_fd=fd)
      os.close(fd)
      fd = child
    return fd
  except OSError:
    os.close(fd)
    raise B0Error('B0_PATH_GUARD_REJECTED') from None


def _unique_pairs(pairs):
  result = {}
  for key, value in pairs:
    _need(key not in result, 'B0_JSON_INVALID')
    result[key] = value
  return result


def _nonfinite(_value):
  raise B0Error('B0_JSON_INVALID')


def _decode(raw):
  try:
    row = json.loads(raw.decode('utf-8'), object_pairs_hook=_unique_pairs, parse_constant=_nonfinite)
    _need(type(row) is dict, 'B0_JSON_INVALID')
    return row
  except (UnicodeError, ValueError, RecursionError) as error:
    if isinstance(error, B0Error):
      raise
    raise B0Error('B0_JSON_INVALID') from None


def _member_map(files, limit):
  _need(type(files) is dict and 0 < len(files) <= limit, 'B0_MEMBER_MAP_CONFLICT')
  for name, digest in files.items():
    try:
      _path(name, absolute=False)
    except B0Error:
      raise B0Error('B0_MEMBER_MAP_CONFLICT') from None
    _need(len(name) <= MEMBER_NAME_LIMIT and _digest(digest), 'B0_MEMBER_MAP_CONFLICT')
  _need(all(name in files for name in (*JOBS, 'results.json', 'selection.json')), 'B0_JOB_DECLARATION_CONFLICT')
  return {
    'declared_member_count': len(files),
    'declared_member_map_sha256': _sha(_canonical(files)),
    'declared_member_identity_observed': True,
    'member_content_verified': False,
  }


def _validate(row, index, expected, pins):
  receipt = row.get('receipt_sha256')
  body = {k: v for k, v in row.items() if k != 'receipt_sha256'}
  _need(_digest(receipt) and receipt == expected and _sha(_canonical(body)) == receipt, 'B0_RECEIPT_MISMATCH')
  schemas = ('V4_RUN_MANIFEST', 'V4_RUN_MANIFEST', 'EMPIRICAL_HURDLE_FIT_CV_MANIFEST_V1', 'EMPIRICAL_HURDLE_FIT_CV_REPEATABILITY_V1')
  _need(row.get('schema') == schemas[index], 'B0_SCHEMA_CONFLICT')
  fields = (
    {'schema', 'synthetic', 'authorization_sha256', 'result_sha256', 'selection_sha256', 'source_writes', 'source_bytes_unchanged', 'files'},
    {'schema', 'status', 'authorization_sha256', 'results_sha256', 'selection_sha256', 'job_count', 'input_bytes_unchanged', 'files'},
    {
      'schema',
      'status',
      'manifest_sha256',
      'authorization_sha256',
      'independent_replicas',
      'all_file_hashes_equal',
      'all_receipts_equal',
      'trapped_resume_exact',
      'scope',
      'files_per_replica',
    },
  )[max(0, index - 1)]
  _need(set(row) == fields | AUTHORITY_KEYS | {'receipt_sha256'}, 'B0_FIELD_SCOPE_CONFLICT')
  _need(all(row[key] is False for key in AUTHORITY_KEYS), 'B0_AUTHORITY_CONFLICT')
  _need(row['authorization_sha256'] == (pins.v4_authorization if index < 2 else pins.v1_authorization), 'B0_IDENTITY_LINK_CONFLICT')
  if index < 2:
    _need(
      row['synthetic'] is False and type(row['source_writes']) is int and row['source_writes'] == 0 and row['source_bytes_unchanged'] is True,
      'B0_IDENTITY_LINK_CONFLICT',
    )
    _need(_digest(row['result_sha256']) and _digest(row['selection_sha256']), 'B0_IDENTITY_LINK_CONFLICT')
  elif index == 2:
    _need(
      row['status'] == 'HURDLE_RETROSPECTIVE_FIT_AND_CV_COMPLETE'
      and type(row['job_count']) is int
      and row['job_count'] == 32
      and row['input_bytes_unchanged'] is True,
      'B0_IDENTITY_LINK_CONFLICT',
    )
    _need(_digest(row['results_sha256']) and _digest(row['selection_sha256']), 'B0_IDENTITY_LINK_CONFLICT')
  else:
    _need(
      row['manifest_sha256'] == pins.v1_manifest
      and row['status'] == 'HURDLE_FIT_CV_EXACT_REPEATABILITY_PASS'
      and type(row['independent_replicas']) is int
      and row['independent_replicas'] == 2
      and row['scope'] == SCOPE
      and all(row[key] is True for key in ('all_file_hashes_equal', 'all_receipts_equal', 'trapped_resume_exact')),
      'B0_IDENTITY_LINK_CONFLICT',
    )
    _need(type(row['files_per_replica']) is int and row['files_per_replica'] == MEMBER_LIMITS[2], 'B0_DECLARED_COUNT_CONFLICT')
  result = {'receipt_identity': 'PASS', 'schema': row['schema'], 'identity_links': 'PASS', 'member_content_verified': False}
  if index < 3:
    result.update(_member_map(row['files'], MEMBER_LIMITS[index]))
    if index == 2:
      _need(len(row['files']) == MEMBER_LIMITS[2], 'B0_DECLARED_COUNT_CONFLICT')
  return result


def _stamp(value):
  return value.st_dev, value.st_ino, value.st_mode, value.st_nlink, value.st_size, value.st_mtime_ns, value.st_ctime_ns


def _request(specs, approved_paths, mount_root, pins, authorized):
  _need(authorized is True, 'B0_EXPLICIT_AUTHORIZATION_REQUIRED')
  _need(tuple(s.record_id for s in specs) == RECORD_IDS and len(approved_paths) == 4, 'B0_EXACT_FOUR_REQUIRED')
  _need(len(set(approved_paths)) == 4 and tuple(s.path for s in specs) == tuple(approved_paths), 'B0_ALLOWLIST_CONFLICT')
  root = _path(mount_root, absolute=True)
  expected = pins.v4_manifest, pins.v4_manifest, pins.v1_manifest, pins.v1_repeatability
  _need(all(_digest(value) for value in (*expected, pins.v4_authorization, pins.v1_authorization)), 'B0_TRUSTED_IDENTITY_REQUIRED')
  relative = []
  for spec, digest in zip(specs, expected, strict=True):
    path = _path(spec.path, absolute=True)
    _need(path != root and path.is_relative_to(root), 'B0_PATH_GRAMMAR_CONFLICT')
    _need(spec.expected_receipt_sha256 == digest, 'B0_TRUSTED_IDENTITY_REQUIRED')
    _need(type(spec.max_bytes) is int and spec.max_bytes == BYTE_CAPS[spec.record_id], 'B0_FROZEN_SIZE_BOUND_REQUIRED')
    _need(spec.expected_raw_sha256 is None or _digest(spec.expected_raw_sha256), 'B0_TRUSTED_IDENTITY_REQUIRED')
    relative.append(str(path.relative_to(root)))
  return relative


def read_four(*, specs, approved_paths, mount_root, pins, authorized=False, expected_mount_identity=None):
  """Return private identity metadata; caller persists it only to its bound private output.

  No target/member is retried. Successful fd opens and bytes are counted even on
  failure. Stop after the first conflict. Ancestor metadata fd opens are distinct
  from payload file opens. Read-only opens may update filesystem access time.
  """
  rows = [{'record_id': key, 'status': 'INPUT_INSUFFICIENT', 'reason': 'NOT_ATTEMPTED', 'file_openings': 0, 'bytes_read': 0} for key in RECORD_IDS]
  report = {
    'schema': 'CYBERPILOT_V4_B0_METADATA_RESULT_V1',
    'status': 'B0_BLOCKED_READER_OR_ENVIRONMENT',
    'records': rows,
    'metadata_file_openings': 0,
    'source_writes': 0,
    'private_array_openings': 0,
    'member_file_openings': 0,
    'replica_payload_equality': 'REPLICA_PAYLOAD_EQUALITY_NOT_REVERIFIED',
    'train_rowwise_gate': 'NOT_SAVED',
    'B1_GRANTED': False,
    'C_AUTHORIZED': False,
    'D_AUTHORIZED': False,
    'E_AUTHORIZED': False,
    'F_AUTHORIZED': False,
  }
  mount = None
  current = None
  try:
    relative = _request(specs, approved_paths, mount_root, pins, authorized)
    mount = _mount_fd(mount_root)
    if expected_mount_identity is not None:
      mounted = os.fstat(mount)
      _need((mounted.st_dev, mounted.st_ino) == expected_mount_identity, 'B0_MOUNT_IDENTITY_CONFLICT')
    seen_files = set()
    for index, (spec, name) in enumerate(zip(specs, relative, strict=True)):
      current = rows[index]
      fd = _open_relative(mount, name)
      current['file_openings'] += 1
      report['metadata_file_openings'] += 1
      try:
        before = os.fstat(fd)
        _need(stat.S_ISREG(before.st_mode) and before.st_nlink == 1, 'B0_REGULAR_SINGLE_LINK_REQUIRED')
        identity = before.st_dev, before.st_ino
        _need(identity not in seen_files, 'B0_DUPLICATE_FILE_IDENTITY')
        seen_files.add(identity)
        _need(0 < before.st_size <= spec.max_bytes, 'B0_SIZE_LIMIT')
        chunks, remaining = [], before.st_size
        while remaining:
          part = os.read(fd, min(65536, remaining))
          _need(bool(part), 'B0_METADATA_CHANGED_DURING_READ')
          chunks.append(part)
          remaining -= len(part)
          current['bytes_read'] += len(part)
        _need(_stamp(before) == _stamp(os.fstat(fd)), 'B0_METADATA_CHANGED_DURING_READ')
        raw = b''.join(chunks)
      finally:
        os.close(fd)
      observed = _sha(raw)
      current.update(observed_raw_sha256=observed, observed_size_bytes=len(raw), metadata_unchanged_during_read=True)
      if spec.expected_raw_sha256 is not None:
        _need(observed == spec.expected_raw_sha256, 'B0_RAW_HASH_MISMATCH')
      current['raw_hash_comparison'] = 'PASS' if spec.expected_raw_sha256 else 'INPUT_INSUFFICIENT_NO_TRUSTED_EXPECTED_RAW_HASH'
      current.update(_validate(_decode(raw), index, spec.expected_receipt_sha256, pins))
      current.update(status='PASS', reason='METADATA_ONLY_IDENTITY_VERIFIED')
    report.update(status='B0_VERIFIED_METADATA_ONLY', run_manifest_identities_equal=True)
  except (B0Error, OSError, ValueError, TypeError, AttributeError, RecursionError) as error:
    code = error.code if isinstance(error, B0Error) else 'B0_READER_FAILURE'
    report['error_code'] = code
    if code == 'B0_MISSING_EXACT_TARGET':
      report['status'] = 'B0_BLOCKED_TRUSTED_REFERENCE_INCOMPLETE'
    elif code in ('B0_UNSUPPORTED_READER_ENVIRONMENT', 'B0_READER_FAILURE', 'B0_EXPLICIT_AUTHORIZATION_REQUIRED'):
      report['status'] = 'B0_BLOCKED_READER_OR_ENVIRONMENT'
    else:
      report['status'] = 'B0_INPUT_CONFLICT_FAIL_CLOSED'
    if current is not None:
      current.update(status='INPUT_INSUFFICIENT' if code == 'B0_MISSING_EXACT_TARGET' else 'FAIL', reason=code)
  finally:
    if mount is not None:
      os.close(mount)
  return report


def public_summary(report):
  """Explicit public projection: no paths, observed hashes, sizes or member map."""
  _need(
    report['status']
    in ('B0_VERIFIED_METADATA_ONLY', 'B0_BLOCKED_TRUSTED_REFERENCE_INCOMPLETE', 'B0_BLOCKED_READER_OR_ENVIRONMENT', 'B0_INPUT_CONFLICT_FAIL_CLOSED'),
    'B0_PUBLIC_PROJECTION_CONFLICT',
  )
  _need(
    tuple(row['record_id'] for row in report['records']) == RECORD_IDS
    and all(row['status'] in ('PASS', 'FAIL', 'INPUT_INSUFFICIENT') for row in report['records'])
    and type(report['metadata_file_openings']) is int
    and 0 <= report['metadata_file_openings'] <= 4
    and type(report['source_writes']) is int
    and report['source_writes'] == 0
    and report['replica_payload_equality'] == 'REPLICA_PAYLOAD_EQUALITY_NOT_REVERIFIED'
    and report['train_rowwise_gate'] == 'NOT_SAVED',
    'B0_PUBLIC_PROJECTION_CONFLICT',
  )
  return {
    'status': report['status'],
    'metadata_file_openings': report['metadata_file_openings'],
    'source_writes': report['source_writes'],
    'records': [{'record_id': row['record_id'], 'status': row['status']} for row in report['records']],
    'replica_payload_equality': report['replica_payload_equality'],
    'train_rowwise_gate': report['train_rowwise_gate'],
    'B1_GRANTED': False,
    'C_AUTHORIZED': False,
    'D_AUTHORIZED': False,
    'E_AUTHORIZED': False,
    'F_AUTHORIZED': False,
  }
