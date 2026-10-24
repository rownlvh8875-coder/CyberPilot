"""Bounded local ZIP capabilities for the separate F8 evidence version.

No extraction, network, source execution, or controller interfaces. Limits are reader
resource bounds, never control-performance thresholds. POSIX supported environment.
"""

from dataclasses import dataclass
import gzip
import hashlib
import io
import os
from pathlib import Path, PurePosixPath
import stat
import struct
import zipfile
import zlib
from typing import BinaryIO

from tools.cyberpilot import offline_multiobjective_gates_v1 as g
from tools.cyberpilot.offline_multiobjective_v1 import strict_json


class F8Error(ValueError):
  def __init__(self, code: str):
    super().__init__(code)
    self.code = code


def need(condition: bool, code: str) -> None:
  if not condition:
    raise F8Error(code)


def json_value(raw: bytes) -> object:
  try:
    return strict_json(raw)
  except g.EvidenceError as exc:
    raise F8Error(exc.code) from exc


def digest(raw: bytes) -> str:
  return hashlib.sha256(raw).hexdigest()


def _parts(path: Path) -> tuple[str, ...]:
  need(path.is_absolute() and '..' not in path.parts, 'F8_EXPLICIT_PATH')
  return path.parts[1:]


def open_directory(path: Path) -> int:
  parts = _parts(path)
  fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
  try:
    for part in parts:
      newer = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
      os.close(fd)
      fd = newer
    return fd
  except OSError as exc:
    os.close(fd)
    raise F8Error('F8_DIRECTORY_CAPABILITY') from exc


def regular_file(path: Path, root: Path, limit: int) -> BinaryIO:
  _parts(path)
  _parts(root)
  need(root != Path('/') and path.is_relative_to(root) and path != root, 'F8_READ_SCOPE')
  parent = open_directory(path.parent)
  try:
    fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
    info = os.fstat(fd)
    if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
      os.close(fd)
      raise F8Error('F8_ARCHIVE_BOUND')
    return os.fdopen(fd, 'rb')
  except OSError as exc:
    raise F8Error('F8_REGULAR_FILE') from exc
  finally:
    os.close(parent)


def _name(name: str) -> None:
  need(
    bool(name)
    and '\\' not in name
    and ':' not in name
    and '\x00' not in name
    and not name.startswith('/')
    and all(p not in ('', '.', '..') for p in name.split('/'))
    and PurePosixPath(name).as_posix() == name,
    'F8_ENTRY_PATH',
  )


@dataclass(frozen=True)
class Limits:
  archive_bytes: int = 320 * 1024**2
  member_bytes: int = 4 * 1024**2
  outer_total_bytes: int = 384 * 1024**2
  processed_member_bytes: int = 768 * 1024**2
  inner_trace_bytes: int = 40 * 1024**2
  inner_total_bytes: int = 5 * 1024**3
  compression_ratio: int = 200
  entries: int = 512


class Archive:
  """Generic pinned-byte reader; production pins are selected only by the Adapter."""

  def __init__(self, path: Path, root: Path, archive_sha: str, manifest_sha: str, records: int, *, limits: Limits | None = None):
    self.limits = Limits() if limits is None else limits
    limits = self.limits
    self.inner_processed = 0
    self.last_trace_sha256: str | None = None
    self.member_processed = 0
    self.expected: dict[str, dict[str, object]] = {}
    self.stream = regular_file(path, root, limits.archive_bytes)
    self.archive_sha = archive_sha
    self.signature = self._signature()
    self.finished = False
    self.zip: zipfile.ZipFile | None = None
    try:
      need(self._hash() == archive_sha, 'F8_ARCHIVE_SHA')
      self._preflight_directory()
      z = zipfile.ZipFile(self.stream)
      self.zip = z
      members: dict[str, zipfile.ZipInfo] = {}
      total = 0
      for info in z.infolist():
        _name(info.filename)
        need(info.filename == info.orig_filename and info.filename not in members, 'F8_DUPLICATE_ENTRY')
        mode = stat.S_IFMT(info.external_attr >> 16)
        need(not info.is_dir() and mode in (0, stat.S_IFREG), 'F8_ENTRY_TYPE')
        need(info.compress_type in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED) and not info.flag_bits & 1, 'F8_ENTRY_ENCODING')
        need(0 <= info.file_size <= limits.member_bytes, 'F8_MEMBER_BOUND')
        need(info.file_size <= max(1, info.compress_size) * limits.compression_ratio, 'F8_ZIP_RATIO')
        total += info.file_size
        need(total <= limits.outer_total_bytes, 'F8_OUTER_TOTAL')
        members[info.filename] = info
      need(len(members) <= limits.entries, 'F8_ENTRY_COUNT')
      self.members = members
      manifest_raw = self.raw('SHA256SUMS.json')
      need(digest(manifest_raw) == manifest_sha, 'F8_MANIFEST_SHA')
      self.manifest = g.mapping(json_value(manifest_raw))
      rows = g.sequence(self.manifest['files'])
      need(len(rows) == records, 'F8_MANIFEST_COUNT')
      for value in rows:
        item = g.mapping(value)
        name = g.text(item['path'])
        _name(name)
        need(name not in self.expected and name != 'SHA256SUMS.json', 'F8_MANIFEST_DUPLICATE')
        self.expected[name] = item
      need(set(members) == set(self.expected) | {'SHA256SUMS.json'}, 'F8_MEMBER_SET')
      for name in self.expected:
        self.raw(name)
      need(self._signature() == self.signature, 'F8_ARCHIVE_MUTATION')
    except F8Error:
      self.close()
      raise
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, RuntimeError, g.EvidenceError) as exc:
      self.close()
      raise F8Error('F8_ARCHIVE_FORMAT') from exc

  def _preflight_directory(self) -> None:
    # Reject oversized inventories before ZipFile allocates its central-directory objects.
    size = self.signature[2]
    self.stream.seek(max(0, size - 65557))
    tail = self.stream.read(65557)
    at = tail.rfind(b'PK\x05\x06')
    need(at >= 0 and len(tail) - at >= 22, 'F8_ZIP_DIRECTORY')
    _, disk, start_disk, on_disk, total, length, offset, comment = struct.unpack('<4s4H2LH', tail[at : at + 22])
    end_at = size - len(tail) + at
    need(disk == start_disk == 0 and on_disk == total and total <= self.limits.entries, 'F8_ENTRY_COUNT')
    need(offset + length == end_at and length <= self.limits.member_bytes and len(tail) == at + 22 + comment, 'F8_ZIP_DIRECTORY_BOUND')
    self.stream.seek(offset)
    directory = self.stream.read(length)
    position = count = 0
    while position < length:
      need(directory[position : position + 4] == b'PK\x01\x02' and position + 46 <= length, 'F8_ZIP_DIRECTORY')
      name_size, extra_size, comment_size = struct.unpack_from('<3H', directory, position + 28)
      position += 46 + name_size + extra_size + comment_size
      count += 1
      need(position <= length and count <= self.limits.entries, 'F8_ENTRY_COUNT')
    need(position == length and count == total, 'F8_ZIP_DIRECTORY_COUNT')
    self.stream.seek(0)

  def _signature(self) -> tuple[int, int, int, int, int]:
    s = os.fstat(self.stream.fileno())
    return s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns

  def _hash(self) -> str:
    self.stream.seek(0)
    h = hashlib.sha256()
    total = 0
    while chunk := self.stream.read(1024 * 1024):
      total += len(chunk)
      need(total <= self.limits.archive_bytes, 'F8_ARCHIVE_BOUND')
      h.update(chunk)
    return h.hexdigest()

  def raw(self, name: str) -> bytes:
    try:
      need(self.zip is not None and name in self.members, 'F8_MISSING_FILE')
      if self.zip is None:
        raise F8Error('F8_CLOSED')
      with self.zip.open(self.members[name]) as source:
        raw = source.read(self.limits.member_bytes + 1)
      need(len(raw) <= self.limits.member_bytes and len(raw) == self.members[name].file_size, 'F8_MEMBER_BOUND')
      self.member_processed += len(raw)
      need(self.member_processed <= self.limits.processed_member_bytes, 'F8_PROCESSING_BOUND')
      if name in self.expected:
        item = self.expected[name]
        need(len(raw) == g.integer(item['bytes']) and digest(raw) == item['sha256'], 'F8_MEMBER_SHA')
      return raw
    except F8Error:
      raise
    except (OSError, EOFError, ValueError, KeyError, zipfile.BadZipFile, RuntimeError) as exc:
      raise F8Error('F8_MEMBER_READ') from exc

  def json(self, name: str) -> object:
    return json_value(self.raw(name))

  def trace(self, name: str) -> object:
    packed = self.raw(name)
    try:
      with gzip.GzipFile(fileobj=io.BytesIO(packed)) as source:
        raw = source.read(self.limits.inner_trace_bytes + 1)
      need(len(raw) <= self.limits.inner_trace_bytes, 'F8_INNER_BOUND')
      need(len(raw) <= max(1, len(packed)) * self.limits.compression_ratio, 'F8_GZIP_RATIO')
      self.inner_processed += len(raw)
      need(self.inner_processed <= self.limits.inner_total_bytes, 'F8_INNER_TOTAL')
      self.last_trace_sha256 = digest(raw)
      return json_value(raw)
    except F8Error:
      raise
    except (OSError, EOFError, zlib.error) as exc:
      raise F8Error('F8_GZIP') from exc

  def finish(self) -> None:
    if not self.finished:
      need(self._signature() == self.signature and self._hash() == self.archive_sha, 'F8_ARCHIVE_MUTATION')
      self.finished = True

  def close(self) -> None:
    if self.zip is not None:
      self.zip.close()
    self.stream.close()

  def __enter__(self) -> 'Archive':
    return self

  def __exit__(self, *_args: object) -> None:
    self.close()


class Output:
  """New exclusive output directory anchored by a no-follow parent descriptor."""

  def __init__(self, path: Path, *, forbidden: tuple[Path, ...], file_limit: int = 8 * 1024**2, total_limit: int = 128 * 1024**2):
    _parts(path)
    need(all(not path.is_relative_to(root) for root in forbidden), 'F8_OUTPUT_SCOPE')
    self.total = 0
    self.file_limit, self.total_limit = file_limit, total_limit
    parent = open_directory(path.parent)
    try:
      os.mkdir(path.name, mode=0o700, dir_fd=parent)
      self.fd = os.open(path.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
    except OSError as exc:
      raise F8Error('F8_NEW_OUTPUT_REQUIRED') from exc
    finally:
      os.close(parent)

  def write(self, name: str, value: object) -> dict[str, object]:
    _name(name)
    need('/' not in name, 'F8_OUTPUT_NAME')
    try:
      raw = g.canonical(value)
      need(len(raw) <= self.file_limit and self.total + len(raw) <= self.total_limit, 'F8_OUTPUT_BOUND')
      fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode=0o600, dir_fd=self.fd)
      with os.fdopen(fd, 'wb') as target:
        target.write(raw)
      self.total += len(raw)
      return {'file': name, 'bytes': len(raw), 'sha256': digest(raw)}
    except OSError as exc:
      raise F8Error('F8_OUTPUT_WRITE') from exc

  def remove_marker(self) -> None:
    os.unlink('INCOMPLETE.json', dir_fd=self.fd)

  def __enter__(self) -> 'Output':
    return self

  def __exit__(self, *_args: object) -> None:
    os.close(self.fd)
