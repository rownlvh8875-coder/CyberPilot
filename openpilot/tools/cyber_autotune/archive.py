"""Linux local immutable OFFLINE proposal/audit archive, never an active profile.

Caller supplies an existing owned directory. No mkdir, chmod, recursive scan,
repair, overwrite, Params or vehicle transport. Local fsync is not authentication
or a guarantee about remote filesystems/disk-controller power loss. Cooperating
operations use nonblocking directory locks; same-UID hostile mutation is outside
the trust boundary, although observed races/corruption fail closed.
"""
from contextlib import contextmanager
import ctypes
import errno
from functools import wraps
import os
from pathlib import PurePosixPath
import stat
import sys
import uuid

if sys.platform == 'linux':
  import fcntl

from openpilot.tools.cyber_autotune.archive_codec import MAX_ARCHIVE_BYTES, decode_audit, decode_proposal, encode_audit, encode_proposal
from openpilot.tools.cyber_autotune.contracts import is_sha256
from openpilot.tools.cyber_autotune.profiles import inspect_proposal


READ_CHUNK_BYTES = 64 * 1024
RENAME_NOREPLACE = 1  # Linux renameat2 UAPI flag; atomic failure if target exists


class ArchiveError(ValueError):
  def __init__(self, code):
    self.code = code
    super().__init__(code)


def _boundary(function):
  @wraps(function)
  def wrapped(*args, **kwargs):
    try:
      return function(*args, **kwargs)
    except ArchiveError:
      raise
    except OSError:
      raise ArchiveError('IO_ERROR') from None
    except (ValueError, TypeError, UnicodeError, RecursionError):
      raise ArchiveError('INVALID_INPUT') from None
  return wrapped


def _key(value):
  if type(value) is not str or not is_sha256(value):
    raise ArchiveError('INVALID_IDENTITY')
  return value


@contextmanager
def _directory(root):
  if sys.platform != 'linux':
    raise ArchiveError('UNSUPPORTED_PLATFORM')
  if (type(root) is not str or '\x00' in root or not root.startswith('/') or root.startswith('//') or
      str(PurePosixPath(root)) != root or '..' in PurePosixPath(root).parts or root == '/'):
    raise ArchiveError('INVALID_ROOT')
  flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
  descriptor = os.open('/', flags)
  try:
    for part in PurePosixPath(root).parts[1:]:
      child = os.open(part, flags, dir_fd=descriptor)
      os.close(descriptor)
      descriptor = child
    metadata = os.fstat(descriptor)
    if metadata.st_uid != os.geteuid() or metadata.st_mode & 0o022:
      raise ArchiveError('UNSAFE_ROOT')
    try:
      fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
      raise ArchiveError('BUSY') from None
    yield descriptor
  finally:
    os.close(descriptor)


def _signature(metadata):
  return (metadata.st_dev, metadata.st_ino, metadata.st_size, metadata.st_mtime_ns, metadata.st_ctime_ns, metadata.st_nlink)


def _read(directory, name, *, durable=False):
  try:
    descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=directory)
  except FileNotFoundError:
    return None
  try:
    before = os.fstat(descriptor)
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or not 0 < before.st_size <= MAX_ARCHIVE_BYTES:
      raise ArchiveError('UNSAFE_ARTIFACT')
    chunks = []
    count = 0
    while True:
      chunk = os.read(descriptor, min(READ_CHUNK_BYTES, MAX_ARCHIVE_BYTES + 1 - count))
      if not chunk:
        break
      chunks.append(chunk)
      count += len(chunk)
      if count > MAX_ARCHIVE_BYTES:
        raise ArchiveError('ARTIFACT_TOO_LARGE')
    after = os.fstat(descriptor)
    named = os.stat(name, dir_fd=directory, follow_symlinks=False)
    if _signature(before) != _signature(after) or _signature(after) != _signature(named) or count != before.st_size:
      raise ArchiveError('ARTIFACT_CHANGED')
    if durable:
      os.fsync(descriptor)
      os.fsync(directory)
    return b''.join(chunks)
  finally:
    os.close(descriptor)


def _decode(decoder, payload):
  try:
    return decoder(payload)
  except (ValueError, TypeError, RecursionError):
    raise ArchiveError('CORRUPT_ARTIFACT') from None


def _rename_no_replace(directory, temporary, target):
  library = ctypes.CDLL(None, use_errno=True)
  try:
    rename = library.renameat2
  except AttributeError:
    raise ArchiveError('UNSUPPORTED_PUBLICATION') from None
  rename.argtypes = (ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint)
  rename.restype = ctypes.c_int
  if rename(directory, os.fsencode(temporary), directory, os.fsencode(target), RENAME_NOREPLACE) != 0:
    error = ctypes.get_errno()
    if error in (errno.ENOSYS, errno.EINVAL, errno.EOPNOTSUPP):
      raise ArchiveError('UNSUPPORTED_PUBLICATION')
    if error == errno.EEXIST:
      raise ArchiveError('CONFLICT')
    raise OSError(error, 'Archive publication failed')


def _store(directory, name, payload, decoder):
  existing = _read(directory, name, durable=True)
  if existing is not None:
    _decode(decoder, existing)
    if existing != payload:
      raise ArchiveError('CONFLICT')
    return
  temporary = '.tmp-' + uuid.uuid4().hex
  descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600, dir_fd=directory)
  identity = os.fstat(descriptor)
  published = False
  try:
    remaining = memoryview(payload)
    while remaining:
      count = os.write(descriptor, remaining)
      if count <= 0:
        raise OSError('Archive write did not progress')
      remaining = remaining[count:]
    os.fsync(descriptor)
    _rename_no_replace(directory, temporary, name)
    published = True
    os.fsync(directory)
  finally:
    os.close(descriptor)
    if not published:
      try:
        observed = os.stat(temporary, dir_fd=directory, follow_symlinks=False)
        if (observed.st_dev, observed.st_ino) == (identity.st_dev, identity.st_ino):
          os.unlink(temporary, dir_fd=directory)
      except FileNotFoundError:
        pass


def _audit_state(directory, run):
  first_payload = _read(directory, f'job-{run}-0.json')
  last_payload = _read(directory, f'job-{run}-1.json')
  if first_payload is None:
    if last_payload is not None:
      raise ArchiveError('ORPHAN_TERMINAL')
    return None
  first = _decode(decode_audit, first_payload)
  if len(first) != 1 or first[0].event.run_sha256 != run:
    raise ArchiveError('AUDIT_BINDING_MISMATCH')
  if last_payload is None:
    return first
  last = _decode(decode_audit, last_payload)
  if len(last) != 2 or last[:1] != first:
    raise ArchiveError('AUDIT_BINDING_MISMATCH')
  return last


@_boundary
def save_proposal(root: str, proposal) -> str:
  payload = encode_proposal(proposal)
  profile = inspect_proposal(proposal).profile_sha256
  with _directory(root) as directory:
    _store(directory, f'proposal-{profile}.json', payload, decode_proposal)
  return profile


@_boundary
def load_proposal(root: str, profile_sha256: str):
  profile = _key(profile_sha256)
  with _directory(root) as directory:
    payload = _read(directory, f'proposal-{profile}.json')
    if payload is None:
      raise ArchiveError('NOT_FOUND')
    proposal = _decode(decode_proposal, payload)
    if inspect_proposal(proposal).profile_sha256 != profile:
      raise ArchiveError('PROFILE_BINDING_MISMATCH')
    return proposal


@_boundary
def save_audit(root: str, chain) -> str:
  payload = encode_audit(chain)
  run = chain[0].event.run_sha256
  with _directory(root) as directory:
    existing = _audit_state(directory, run)
    if len(chain) == 2 and existing is None:
      raise ArchiveError('MISSING_START')
    if existing is not None and (existing[:1] != chain[:1] or (len(existing) == len(chain) == 2 and existing != chain)):
      raise ArchiveError('CONFLICT')
    _store(directory, f'job-{run}-{len(chain) - 1}.json', payload, decode_audit)
  return run


@_boundary
def load_audit(root: str, run_sha256: str):
  """One record is INCOMPLETE; two mean terminal execution, never qualification."""
  run = _key(run_sha256)
  with _directory(root) as directory:
    state = _audit_state(directory, run)
    if state is None:
      raise ArchiveError('NOT_FOUND')
    return state
