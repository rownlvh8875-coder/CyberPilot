#!/usr/bin/env python3
"""Explicit inactive Source A/B file integrity. No execution or promotion authority.

The single contract byte identity is a reviewed-code anchor, not a hash allowlist.
Verifier code integrity is bound by the external source manifest/review.
Validation is a declared component-set read, not an atomic whole-tree snapshot.
"""

import argparse
import errno
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import stat
import sys

CONTRACT_RAW_SHA256 = "7f76b6d571092ae86200d963edc2959333fbf95868d443b78dc73bc02ec9d782"
SCHEMA = "CYBERPILOT_INACTIVE_SOURCE_VERSION_CONTRACT_V1"
SOURCE_A = "SOURCE_A_HEAD_51C1CDB3_V1"
SOURCE_B = "SOURCE_B_F19_CAPTURE_ONLY_LOCAL_V1"
ANCHOR = "openpilot/selfdrive/controls/controlsd.py"
# Resource bounds for this small declared source set, not vehicle/performance limits.
MAX_CONTRACT_BYTES = 128 * 1024
MAX_FILE_BYTES = 4 * 1024 * 1024
MAX_TOTAL_BYTES = 16 * 1024 * 1024
READ_CHUNK_BYTES = 64 * 1024
MAX_JSON_DEPTH = 32
LEGACY_ERROR = "F-19 Legacy Source Publication: UNRESOLVED ERROR"
FALSE_AUTHORITY = ("effective", "runtime_authorized", "promotion_enabled", "performance_qualified")
REQUIRED_KEYS = frozenset(
  (
    "schema_version",
    "registration_status",
    "source_a_version",
    "source_b_version",
    "original_git_head",
    "source_anchor_path",
    "source_a_sha256",
    "source_b_sha256",
    "modified_file_sha256",
    "source_a_absent_files",
    "immutable_source_dependencies",
    "frozen_source_sha256",
    "historical_receipts",
    "parent_source_version",
    "allowed_validation_scope",
    "evidence_identity",
    "historical_receipts_unchanged",
    "identity_semantics",
    *FALSE_AUTHORITY,
    "diagnostic_only",
    "vehicle_authority",
    "selected_candidate",
    "selected_policy",
    "legacy_source_publication",
  )
)
SCOPES = ["EXACT_FILE_COMPONENT_INTEGRITY", "FROZEN_SOURCE_PRESERVATION", "HISTORICAL_RECEIPT_PRESERVATION"]


class SourceVersionError(ValueError):
  """Stable non-qualifying rejection code."""


def _need(condition, code):
  if not condition:
    raise SourceVersionError(code)


def _digest(data):
  return hashlib.sha256(data).hexdigest()


def _canonical(value):
  return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _sha(value):
  return type(value) is str and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def _relative(value):
  _need(type(value) is str and value and "\\" not in value, "CONTRACT_SCHEMA")
  p = PurePosixPath(value)
  _need(not p.is_absolute() and p.as_posix() == value and all(x not in ("", ".", "..") for x in value.split("/")), "CONTRACT_SCHEMA")
  return value


def _hash_map(value):
  _need(type(value) is dict and 0 < len(value) <= 512, "CONTRACT_SCHEMA")
  for name, digest in value.items():
    _relative(name)
    _need(_sha(digest), "CONTRACT_SCHEMA")


def validate_contract_schema(row):
  """Shape/authority checks only; this alone does not admit a contract."""
  _need(type(row) is dict and set(row) == REQUIRED_KEYS, "CONTRACT_SCHEMA")
  _need(
    all(row[key] is False for key in FALSE_AUTHORITY)
    and row["diagnostic_only"] is True
    and row["historical_receipts_unchanged"] is True
    and row["vehicle_authority"] == "NONE"
    and row["selected_candidate"] is None
    and row["selected_policy"] is None,
    "AUTHORITY_INVARIANT",
  )
  _need(
    row["schema_version"] == SCHEMA
    and row["registration_status"] == "LOCAL_INACTIVE_RECORD_ONLY"
    and row["source_a_version"] == SOURCE_A
    and row["source_b_version"] == SOURCE_B
    and row["original_git_head"] == "51c1cdb3327f442d026e5ba3bdcc173438a6aae1"
    and row["source_anchor_path"] == ANCHOR
    and row["allowed_validation_scope"] == SCOPES
    and row["legacy_source_publication"] == LEGACY_ERROR,
    "CONTRACT_SCHEMA",
  )
  _need(_sha(row["source_a_sha256"]) and _sha(row["source_b_sha256"]), "CONTRACT_SCHEMA")
  for key in ("modified_file_sha256", "immutable_source_dependencies", "frozen_source_sha256"):
    _hash_map(row[key])
  modified = row["modified_file_sha256"]
  _need(len(modified) == 3 and modified.get(ANCHOR) == row["source_b_sha256"], "CONTRACT_SCHEMA")
  _need(type(row["identity_semantics"]) is str and row["identity_semantics"], "CONTRACT_SCHEMA")
  _need(
    type(row["source_a_absent_files"]) is list
    and all(type(x) is str for x in row["source_a_absent_files"])
    and sorted(row["source_a_absent_files"]) == sorted(set(modified) - {ANCHOR}),
    "CONTRACT_SCHEMA",
  )
  _need(
    len(row["frozen_source_sha256"]) == 231
    and not (set(modified) & set(row["immutable_source_dependencies"]))
    and not (set(modified) & set(row["frozen_source_sha256"])),
    "CONTRACT_SCHEMA",
  )
  parent = row["parent_source_version"]
  _need(parent == {"version_id": SOURCE_A, "git_head": row["original_git_head"], "source_anchor_sha256": row["source_a_sha256"]}, "CONTRACT_SCHEMA")
  receipts = row["historical_receipts"]
  _need(type(receipts) is dict and len(receipts) == 16, "CONTRACT_SCHEMA")
  for path, value in receipts.items():
    _relative(path)
    _need(type(value) is dict and set(value) == {"file_sha256", "receipt_sha256"} and all(_sha(x) for x in value.values()), "CONTRACT_SCHEMA")
  evidence = row["evidence_identity"]
  _need(
    type(evidence) is dict
    and set(evidence) == {"F19_manifest_sha256", "F20_manifest_sha256", "F19_native_parity_sha256", "F19_publication_error_sha256", "status"},
    "CONTRACT_SCHEMA",
  )
  _need(
    evidence["status"] == "REFERENCE_HASHES_ONLY_NOT_REEXECUTED_BY_VALIDATOR" and all(_sha(v) for k, v in evidence.items() if k != "status"), "CONTRACT_SCHEMA"
  )


def _absolute(value):
  _need(isinstance(value, (str, Path)), "PATH_TYPE")
  _need(chr(0) not in str(value), "UNSAFE_PATH")
  p = Path(value)
  _need(p.is_absolute(), "ABSOLUTE_PATH_REQUIRED")
  _need(".." not in p.parts and p.parts[1:2] not in (("dev",), ("proc",), ("sys",)), "UNSAFE_PATH")
  return p


def _parent_fd(path):
  # Directory descriptors and O_NOFOLLOW prevent parent/leaf symlink traversal.
  flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
  fd = os.open("/", flags)
  try:
    for part in path.parent.parts[1:]:
      nxt = os.open(part, flags, dir_fd=fd)
      os.close(fd)
      fd = nxt
    return fd
  except BaseException:
    os.close(fd)
    raise


def _read_regular(path, maximum):
  path = _absolute(path)
  parent = file_fd = None
  try:
    parent = _parent_fd(path)
    file_fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
    before = os.fstat(file_fd)
    _need(stat.S_ISREG(before.st_mode), "NON_REGULAR_FILE")
    _need(before.st_size <= maximum, "FILE_SIZE_LIMIT")
    chunks, size = [], 0
    while True:
      part = os.read(file_fd, min(READ_CHUNK_BYTES, maximum + 1 - size))
      if not part:
        break
      size += len(part)
      _need(size <= maximum, "FILE_SIZE_LIMIT")
      chunks.append(part)
    after = os.fstat(file_fd)
    _need(
      (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
      and size == before.st_size,
      "FILE_CHANGED_DURING_READ",
    )
    return b"".join(chunks)
  except OSError as exc:
    raise SourceVersionError("REQUIRED_FILE_MISSING" if exc.errno == errno.ENOENT else "UNSAFE_PATH") from exc
  finally:
    if file_fd is not None:
      os.close(file_fd)
    if parent is not None:
      os.close(parent)


def _absent(path):
  parent = None
  try:
    parent = _parent_fd(_absolute(path))
    os.stat(path.name, dir_fd=parent, follow_symlinks=False)
    return False
  except FileNotFoundError:
    return True
  except OSError as exc:
    raise SourceVersionError("UNSAFE_PATH") from exc
  finally:
    if parent is not None:
      os.close(parent)


def _unique(pairs):
  row = {}
  for key, value in pairs:
    _need(key not in row, "DUPLICATE_JSON_KEY")
    row[key] = value
  return row


def _nonfinite(_):
  raise SourceVersionError("NONFINITE_JSON")


def _json(data):
  try:
    row = json.loads(data.decode("utf-8"), object_pairs_hook=_unique, parse_constant=_nonfinite)

    def check(value, depth=0):
      _need(depth <= MAX_JSON_DEPTH, "JSON_DEPTH_LIMIT")
      if type(value) is float:
        _need(math.isfinite(value), "NONFINITE_JSON")
      if type(value) is dict:
        for item in value.values():
          check(item, depth + 1)
      elif type(value) is list:
        for item in value:
          check(item, depth + 1)

    check(row)
    return row
  except SourceVersionError:
    raise
  except (UnicodeError, ValueError, RecursionError) as exc:
    raise SourceVersionError("INVALID_CONTRACT_JSON") from exc


class _FileSet:
  def __init__(self, root):
    self.root = root
    self.data = {}
    self.hashes = {}
    self.total = 0

  def read(self, name):
    _relative(name)
    if name not in self.data:
      data = _read_regular(self.root / name, MAX_FILE_BYTES)
      self.total += len(data)
      _need(self.total <= MAX_TOTAL_BYTES, "TOTAL_SIZE_LIMIT")
      self.data[name] = data
      self.hashes[name] = _digest(data)
    return self.data[name]

  def verify(self, mapping, code):
    for path, expected in sorted(mapping.items()):
      self.read(path)
      _need(self.hashes[path] == expected, code)


def validate_source_version(source_root, contract_path, source_version):
  """Read declared files only. No history rewriting or legacy Source A admission."""
  _need(source_version in (SOURCE_A, SOURCE_B), "SOURCE_VERSION_UNKNOWN")
  root = _absolute(source_root)
  raw = _read_regular(contract_path, MAX_CONTRACT_BYTES)
  row = _json(raw)
  _need(_digest(raw) == CONTRACT_RAW_SHA256, "CONTRACT_IDENTITY_MISMATCH")
  validate_contract_schema(row)
  files = _FileSet(root)
  modified = row["modified_file_sha256"] if source_version == SOURCE_B else {ANCHOR: row["source_a_sha256"]}
  files.verify(modified, "SOURCE_FILE_HASH_MISMATCH")
  if source_version == SOURCE_A:
    for path in row["source_a_absent_files"]:
      _need(_absent(root / path), "UNEXPECTED_SOURCE_FILE_FOR_A")
  files.verify(row["immutable_source_dependencies"], "SOURCE_DEPENDENCY_MISMATCH")
  files.verify(row["frozen_source_sha256"], "FROZEN_SOURCE_MISMATCH")
  for path, expected in sorted(row["historical_receipts"].items()):
    data = files.read(path)
    _need(files.hashes[path] == expected["file_sha256"], "HISTORICAL_RECEIPT_MISMATCH")
    receipt = _json(data)
    _need(
      type(receipt) is dict
      and receipt.get("receipt_sha256") == expected["receipt_sha256"]
      and _digest(_canonical({k: v for k, v in receipt.items() if k != "receipt_sha256"})) == expected["receipt_sha256"],
      "HISTORICAL_RECEIPT_MISMATCH",
    )
  return {
    "schema": "CYBERPILOT_INACTIVE_SOURCE_VERSION_RESULT_V1",
    "status": "STRUCTURALLY_VALID",
    "source_version": source_version,
    "source_root": str(root),
    "contract_sha256": CONTRACT_RAW_SHA256,
    "validator_source_sha256": _digest(_read_regular(Path(__file__).absolute(), MAX_FILE_BYTES)),
    "source_anchor_sha256": files.hashes[ANCHOR],
    "checked_files": len(files.hashes),
    "checked_component_sha256": _digest(_canonical(files.hashes)),
    "reference_git_head": row["original_git_head"],
    "git_head_observed_by_validator": False,
    "historical_receipts_verified": len(row["historical_receipts"]),
    "external_evidence_status": "REFERENCE_HASHES_ONLY_NOT_REEXECUTED_BY_VALIDATOR",
    "qualification": "PERFORMANCE_NOT_QUALIFIED",
    "measurement_qualification": "UNQUALIFIED",
    "legacy_source_publication": LEGACY_ERROR,
    **_authority(),
  }


def _authority():
  return {
    "effective": False,
    "runtime_authorized": False,
    "diagnostic_only": True,
    "promotion_enabled": False,
    "performance_qualified": False,
    "vehicle_authority": "NONE",
    "selected_candidate": None,
    "selected_policy": None,
    "runtime_integration": "NO-GO",
  }


def main(argv=None):
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("--source-root", required=True)
  parser.add_argument("--contract", required=True)
  parser.add_argument("--source-version", required=True)
  args = parser.parse_args(argv)
  try:
    row = validate_source_version(args.source_root, args.contract, args.source_version)
  except SourceVersionError as exc:
    row = {
      "schema": "CYBERPILOT_INACTIVE_SOURCE_VERSION_RESULT_V1",
      "status": "STRUCTURALLY_BLOCKED",
      "reason": str(exc),
      "legacy_source_publication": LEGACY_ERROR,
      **_authority(),
    }
    code = 2
  else:
    code = 0
  print(json.dumps(row, sort_keys=True, separators=(",", ":"), allow_nan=False))
  return code


if __name__ == "__main__":
  sys.exit(main())
