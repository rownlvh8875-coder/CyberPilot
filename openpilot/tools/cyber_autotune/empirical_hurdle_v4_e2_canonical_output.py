"""Bounded exclusive synthetic/private-ready receipt primitive; no source access."""

from contextlib import contextmanager
from contextvars import ContextVar
import hashlib
import json
import os
from pathlib import Path
import re
import stat

MAX_FILE = 8 * 1024**2
MAX_TOTAL = 384 * 1024**2
RESERVE = 2 * 1024**3


def need(value, reason='CANONICAL_OUTPUT_CONFLICT'):
  if not value:
    raise ValueError(reason)


def canonical(value):
  return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def sha(raw):
  return hashlib.sha256(raw).hexdigest()


def sealed(value):
  need(type(value) is dict and 'receipt_sha256' not in value)
  return {**value, 'receipt_sha256': sha(canonical(value))}


def decode(raw):
  def pairs(items):
    result = {}
    for k, v in items:
      need(k not in result, 'CANONICAL_DUPLICATE_JSON_KEY')
      result[k] = v
    return result

  def invalid(_):
    raise ValueError('CANONICAL_NONFINITE_JSON')

  return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)


def checked(value):
  need(
    type(value) is dict and value.get('receipt_sha256') == sha(canonical({k: v for k, v in value.items() if k != 'receipt_sha256'})),
    'CANONICAL_RECEIPT_CONFLICT',
  )
  return value


IO_PERMISSION = ContextVar('canonical_store_io', default=None)


@contextmanager
def permission(event, name, flags, dir_fd=None):
  parent = None if dir_fd is None else os.fstat(dir_fd)
  target = Path(name) if dir_fd is None else Path(os.readlink(f'/proc/self/fd/{dir_fd}')) / name
  stamp = None if parent is None else (parent.st_dev, parent.st_ino)
  token = IO_PERMISSION.set((event, str(name), flags, str(target), dir_fd, stamp))
  try:
    yield
  finally:
    IO_PERMISSION.reset(token)


def open_at(name, flags, mode=0o600, *, dir_fd=None):
  with permission('open', name, flags, dir_fd):
    return os.open(name, flags, mode, dir_fd=dir_fd)


class Store:
  def __init__(self, path, *, create=True):
    path = Path(path)
    need(path.is_absolute() and '..' not in path.parts and path.name not in ('', '.', '..'))
    repo = Path(__file__).resolve().parents[3]
    need(not path.is_relative_to(repo), 'CANONICAL_OUTPUT_OUTSIDE_GIT_REQUIRED')
    flags = os.O_DIRECTORY | os.O_RDONLY | os.O_NOFOLLOW
    fd = open_at('/', flags)
    device = os.fstat(fd).st_dev
    child = None
    try:
      for component in path.parts[1:-1]:
        next_fd = open_at(component, flags, dir_fd=fd)
        if os.fstat(next_fd).st_dev != device:
          os.close(next_fd)
          raise ValueError('CANONICAL_OUTPUT_CROSS_DEVICE')
        os.close(fd)
        fd = next_fd
      if create:
        with permission('os.mkdir', path.name, 0o700, fd):
          os.mkdir(path.name, 0o700, dir_fd=fd)
        os.fsync(fd)
      child = open_at(path.name, flags, dir_fd=fd)
      st = os.fstat(child)
      need(st.st_dev == device, 'CANONICAL_OUTPUT_CROSS_DEVICE')
      need(st.st_uid == os.geteuid() and stat.S_IMODE(st.st_mode) == 0o700, 'CANONICAL_OUTPUT_MODE')
      space = os.fstatvfs(child)
      need(space.f_bavail * space.f_frsize >= RESERVE + MAX_TOTAL, 'CANONICAL_OUTPUT_RESERVE')
      self.fd, self.path, self.total, self.device = child, path, 0, device
      child = None
    finally:
      os.close(fd)
      if child is not None:
        os.close(child)

  def __enter__(self):
    return self

  def __exit__(self, *args):
    os.close(self.fd)

  def _stat(self, fd):
    st = os.fstat(fd)
    need(
      stat.S_ISREG(st.st_mode) and st.st_nlink == 1 and st.st_dev == self.device and st.st_uid == os.geteuid() and stat.S_IMODE(st.st_mode) == 0o600,
      'CANONICAL_OUTPUT_ALIAS_OR_MODE',
    )
    return st

  def read(self, name, digest):
    need(re.fullmatch('[a-z0-9-]+[.]json', name) is not None)
    fd = open_at(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=self.fd)
    try:
      before = self._stat(fd)
      need(before.st_size <= MAX_FILE)
      with os.fdopen(fd, 'rb', closefd=False) as stream:
        raw = stream.read(MAX_FILE + 1)
      after = self._stat(fd)
      need((before.st_ino, before.st_size, before.st_mtime_ns) == (after.st_ino, after.st_size, after.st_mtime_ns))
      need(sha(raw) == digest, 'CANONICAL_DURABLE_READBACK_MISMATCH')
      return checked(decode(raw))
    finally:
      os.close(fd)

  def write(self, name, value):
    need(re.fullmatch('[a-z0-9-]+[.]json', name) is not None)
    raw = canonical(sealed(value))
    need(len(raw) <= MAX_FILE and self.total + len(raw) <= MAX_TOTAL, 'CANONICAL_OUTPUT_SIZE')
    fd = open_at(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, dir_fd=self.fd)
    try:
      self._stat(fd)
      with os.fdopen(fd, 'wb', closefd=False) as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(fd)
      os.fsync(self.fd)
    finally:
      os.close(fd)
    digest = sha(raw)
    self.read(name, digest)
    self.total += len(raw)
    return digest
