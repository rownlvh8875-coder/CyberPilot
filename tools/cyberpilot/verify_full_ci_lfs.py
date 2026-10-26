#!/usr/bin/env python3
"""Verify exact public LFS bytes in isolated staging; no upload or cache installation.

Content identity and trusted distribution provenance are separate requirements.
This module only establishes content identity. The diagnostic caller restricts
network requests to official endpoints; it never loads the downloaded models.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat

BLOCK_BYTES = 1024 * 1024
REQUIRED_STAGES = (
  "checkout",
  "setup",
  "publication_before",
  "build",
  "ruff",
  "test_dependency",
  "autotune_controls",
  "attribution",
  "syntax",
  "lateral",
  "json",
  "publication_after",
  "clean",
)
POINTER = re.compile(rb"version https://git-lfs.github.com/spec/v1\noid sha256:([0-9a-f]{64})\nsize ([1-9][0-9]*)\n")


class IntegrityError(ValueError):
  pass


def need(condition, reason):
  if not condition:
    raise IntegrityError(reason)


def validate_entry(entry):
  name = entry["path"]
  need(isinstance(name, str) and name and "\\" not in name, "INVALID_MEMBER")
  p = PurePosixPath(name)
  need(not p.is_absolute() and ".." not in p.parts and str(p) == name, "INVALID_MEMBER")
  need(re.fullmatch("[0-9a-f]{64}", entry["oid"]) is not None, "INVALID_OID")
  need(type(entry["size"]) is int and 0 < entry["size"] <= 128 * BLOCK_BYTES, "INVALID_SIZE")


def parse_pointer(data, path):
  m = POINTER.fullmatch(data)
  need(m is not None and len(data) <= 1024, "NONCANONICAL_POINTER")
  entry = {"path": path, "oid": m[1].decode(), "size": int(m[2])}
  validate_entry(entry)
  return entry


def open_directory(path):
  """Open every component relative to a no-follow fd; never resolve aliases."""
  p = Path(path)
  fd = os.open("/" if p.is_absolute() else ".", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
  try:
    for part in p.parts:
      if part in ("/", "."):
        continue
      need(part != "..", "PARENT_TRAVERSAL")
      nxt = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
      os.close(fd)
      fd = nxt
    return fd
  except BaseException:
    os.close(fd)
    raise


def _digest(stream, entry, output=None):
  digest = hashlib.sha256()
  total = 0
  prefix = bytearray()
  while True:
    data = stream.read(min(BLOCK_BYTES, entry["size"] + 1 - total))
    if not data:
      break
    total += len(data)
    need(total <= entry["size"], "SIZE_CAP_EXCEEDED")
    if len(prefix) < 128:
      prefix.extend(data[: 128 - len(prefix)])
    digest.update(data)
    if output is not None:
      output.write(data)
  need(total == entry["size"], "TRUNCATED_OR_WRONG_SIZE")
  need(not prefix.startswith(b"version https://git-lfs.github.com/spec/"), "POINTER_IS_NOT_PAYLOAD")
  need(digest.hexdigest() == entry["oid"], "SHA256_MISMATCH")
  kind = "PNG" if prefix.startswith(b"\x89PNG\r\n\x1a\n") else "ELF" if prefix.startswith(b"\x7fELF") else "BINARY_NOT_PARSED"
  return {"sha256": digest.hexdigest(), "bytes": total, "file_type": kind}


def stage_stream(stream, directory, entry):
  """Exclusive OID file, bounded stream, fsync/readback. Failure leaves no partial."""
  validate_entry(entry)
  parent = open_directory(directory)
  created = False
  try:
    st = os.fstat(parent)
    need(st.st_uid == os.getuid() and stat.S_IMODE(st.st_mode) == 0o700, "STAGING_OWNER_OR_MODE")
    fd = os.open(entry["oid"], os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
    created = True
    with os.fdopen(fd, "wb") as output:
      before = os.fstat(output.fileno())
      need(stat.S_ISREG(before.st_mode) and before.st_nlink == 1, "NOT_EXCLUSIVE_REGULAR_FILE")
      _digest(stream, entry, output)
      output.flush()
      os.fsync(output.fileno())
      after = os.fstat(output.fileno())
      need(after.st_nlink == 1 and after.st_size == entry["size"], "OUTPUT_ALIAS_OR_SIZE")
    os.fsync(parent)
    return verify_file(Path(directory) / entry["oid"], entry)
  except BaseException:
    if created:
      os.unlink(entry["oid"], dir_fd=parent)
    raise
  finally:
    os.close(parent)


def verify_file(path, entry):
  validate_entry(entry)
  p = Path(path)
  parent = open_directory(p.parent)
  try:
    fd = os.open(p.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
    with os.fdopen(fd, "rb") as source:
      before = os.fstat(source.fileno())
      need(stat.S_ISREG(before.st_mode) and before.st_nlink == 1, "NOT_EXCLUSIVE_REGULAR_FILE")
      need(before.st_size == entry["size"], "SIZE_MISMATCH")
      result = _digest(source, entry)
      after = os.fstat(source.fileno())
      need(
        (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns)
        == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns),
        "FILE_CHANGED",
      )
      return result
  finally:
    os.close(parent)


def classify_http(code):
  if code in (401, 403):
    return "AUTHORIZED_CREDENTIAL_REQUIRED"
  if code == 404:
    return "NOT_FOUND_OR_NOT_AUTHORIZED"
  if code == 429 or 500 <= code <= 599:
    return "TRANSIENT_SERVICE_FAILURE"
  return "HTTP_FAILURE"


def require_full_success(evidence, expected_head):
  """Validate supplied public CI evidence; this does not authenticate its issuer."""
  need(re.fullmatch("[0-9a-f]{40}", expected_head) is not None, "INVALID_EXPECTED_HEAD")
  need(evidence.get("head_sha") == expected_head and evidence.get("workflow_path") == ".github/workflows/cyberpilot.yaml", "WRONG_HEAD_OR_WORKFLOW")
  need(evidence.get("status") == "completed", "FULL_CI_NOT_COMPLETED")
  need(
    evidence.get("conclusion") == "success"
    and set(evidence.get("stages", {})) == set(REQUIRED_STAGES)
    and all(value == "success" for value in evidence["stages"].values()),
    "FULL_CI_REQUIRED_STAGE_NOT_SUCCESS",
  )


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("--inventory", type=Path, required=True)
  parser.add_argument("--staging", type=Path, required=True)
  args = parser.parse_args()
  entries = json.loads(args.inventory.read_text())["objects"]
  results = [{"path": entry["path"], **verify_file(args.staging / entry["oid"], entry)} for entry in entries]
  print(json.dumps({"content_verification": results, "provenance_verification": "SEPARATE_REQUIRED", "cache_installed": False}))


if __name__ == "__main__":
  main()
