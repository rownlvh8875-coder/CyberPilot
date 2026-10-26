"""Retain an authorized input as sealed Linux memory, never as a disk copy.

Trusted local grants only; CP/cache declarations are not native observations.
Consumers must not close the borrowed FD and must not treat receipts as authority.
"""
from contextlib import contextmanager, ExitStack
import fcntl
import hashlib
import json
import os
import stat
import subprocess

from openpilot.tools.cyber_autotune.replay_admission import _check_source, _digest, _directory, _path, _validate, READ_CHUNK_BYTES


# Linux UAPI linux/fcntl.h, asm-generic/fcntl.h. The pinned standalone Python
# build omits these fcntl names; the kernel ABI values are not tuning constants.
ADD_SEALS = 1033
GET_SEALS = 1034
INPUT_SEALS = 0x000F  # SEAL_WRITE | SEAL_GROW | SEAL_SHRINK | SEAL_SEAL


def _write_all(fd, block):
  view = memoryview(block)
  while view:
    written = os.write(fd, view)
    if written <= 0:
      raise OSError('SNAPSHOT_WRITE_FAILED')
    view = view[written:]


def _seal(fd):
  fcntl.fcntl(fd, ADD_SEALS, INPUT_SEALS)
  if fcntl.fcntl(fd, GET_SEALS) != INPUT_SEALS:
    raise ValueError('INPUT_NOT_SEALED')
  os.lseek(fd, 0, os.SEEK_SET)


@contextmanager
def _sealed_bytes(data):
  fd = os.memfd_create('cyber-offline', os.MFD_CLOEXEC | os.MFD_ALLOW_SEALING)
  try:
    _write_all(fd, data)
    _seal(fd)
    yield fd
  finally:
    os.close(fd)


@contextmanager
def _copied_input(grant):
  with _directory(grant['root']) as root_fd:
    parent = os.dup(root_fd)
    try:
      parts = _path(grant['path'])
      for part in parts[:-1]:
        child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=parent)
        os.close(parent)
        parent = child
      original = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=parent)
    finally:
      os.close(parent)
  try:
    before = os.fstat(original)
    if not stat.S_ISREG(before.st_mode) or before.st_size != grant['size_bytes']:
      raise ValueError('INPUT_TYPE_OR_SIZE_MISMATCH')
    retained = os.memfd_create('cyber-input', os.MFD_CLOEXEC | os.MFD_ALLOW_SEALING)
    try:
      digest = hashlib.sha256()
      remaining = before.st_size
      while remaining:
        block = os.read(original, min(READ_CHUNK_BYTES, remaining))
        if not block:
          raise ValueError('INPUT_CHANGED')
        remaining -= len(block)
        digest.update(block)
        _write_all(retained, block)
      after = os.fstat(original)
      def identity(s):
        return s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns
      if os.read(original, 1) or identity(before) != identity(after) or digest.hexdigest() != grant['sha256']:
        raise ValueError('INPUT_CHANGED_OR_HASH_MISMATCH')
      _seal(retained)
    except BaseException:
      os.close(retained)
      raise
  finally:
    os.close(original)
  try:
    yield retained
  finally:
    os.close(retained)


@contextmanager
def _retain_input(request, *, grants, authority_sha256, observation):
  selected = _validate(request, grants, authority_sha256, observation=observation)
  request, grant = json.loads(json.dumps((request, selected), allow_nan=False))
  with ExitStack() as stack:
    try:
      source_fd = stack.enter_context(_directory(request['source']['root']))
      _check_source(source_fd, request['source'])
      fd = stack.enter_context(_copied_input(grant))
      _check_source(source_fd, request['source'])
    except (OSError, subprocess.SubprocessError, UnicodeError):
      raise ValueError('INPUT_OR_SOURCE_UNAVAILABLE') from None
    receipt = {
      'status': 'INPUT_RETAINED_SEALED', 'request_sha256': _digest(request), 'grant_sha256': _digest(grant),
      'authority_sha256': authority_sha256, 'input_sha256': grant['sha256'], 'input_size_bytes': grant['size_bytes'],
      'source_head': request['source']['head'], 'replay_allowed': False, 'runtime_accepted': False, 'promotable': False,
    }
    if observation:
      receipt['purpose'] = 'OBSERVE_INITIAL_STATE'
    yield fd, receipt
    try:
      _check_source(source_fd, request['source'])
    except (OSError, subprocess.SubprocessError, UnicodeError):
      raise ValueError('SOURCE_UNAVAILABLE_AFTER_RUN') from None


@contextmanager
def retain_replay_input(request, *, grants, authority_sha256):
  with _retain_input(request, grants=grants, authority_sha256=authority_sha256, observation=False) as retained:
    yield retained


@contextmanager
def retain_observation_input(request, *, grants, authority_sha256):
  """Observation-only schema: cannot bypass the separate replay initial-state gate."""
  with _retain_input(request, grants=grants, authority_sha256=authority_sha256, observation=True) as retained:
    yield retained
