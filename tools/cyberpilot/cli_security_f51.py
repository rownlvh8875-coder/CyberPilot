"""F51_SECURITY_PATCH_CANDIDATE_V1: private CLI and local POSIX output capabilities.

No controller, schema conversion, credentials or driving data access. Same-user
malicious processes and root are outside the POSIX discretionary access boundary.
"""
import argparse
from contextlib import contextmanager
import ctypes
from dataclasses import dataclass
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys

IDENTITY = 'F51_SECURITY_PATCH_CANDIDATE_V1'
# ext2/3/4 and tmpfs only. DrvFS/9p, remote, unknown and native Windows fail closed.
TRUSTED_FS = frozenset((0xEF53, 0x01021994))
KNOWN_CODES = frozenset(('INVALID_CLI_ARGUMENT', 'INVALID_ARGUMENTS', 'INVALID_INPUT_SCHEMA',
                         'INPUT_FILE_ACCESS_DENIED', 'UNEXPECTED_INTERNAL_ERROR',
                         'UNSAFE_OUTPUT', 'UNQUALIFIED_FILESYSTEM', 'OUTPUT_PATH_CHANGED',
                         'WORKER_OWNERSHIP_REQUIRED', 'WORKER_OUTPUT_NOT_EMPTY',
                         'OUTPUT_FILE_COLLISION', 'UNSAFE_OUTPUT_FILE', 'READER_BLOCKED'))


class SecurityError(ValueError):
  """A fixed public error code, never untrusted text."""


def require(condition, code):
  if not condition:
    raise SecurityError(code)


class PrivateParser(argparse.ArgumentParser):
  def error(self, message):
    raise SecurityError('INVALID_CLI_ARGUMENT')


def error_code(error, known=()):
  if isinstance(error, (ValueError, SecurityError)) and error.args and type(error.args[0]) is str:
    if error.args[0] in KNOWN_CODES or error.args[0] in known:
      return error.args[0]
  if isinstance(error, (json.JSONDecodeError, KeyError, TypeError)):
    return 'INVALID_INPUT_SCHEMA'
  if isinstance(error, PermissionError):
    return 'INPUT_FILE_ACCESS_DENIED'
  return 'UNEXPECTED_INTERNAL_ERROR'


def worker_error(stdout, prefix, known=()):
  # No arbitrary exception text or child stderr crosses this boundary.
  try:
    text = stdout.decode('ascii').strip()
  except (UnicodeError, AttributeError):
    return 'READER_BLOCKED'
  code = text.removeprefix(prefix)
  return code if text.startswith(prefix) and code in KNOWN_CODES.union(known) else 'READER_BLOCKED'


def filesystem_type(fd):
  require(sys.platform == 'linux' and ctypes.sizeof(ctypes.c_long) == 8, 'UNQUALIFIED_FILESYSTEM')
  libc = ctypes.CDLL(None, use_errno=True)
  data = ctypes.create_string_buffer(256)
  require(libc.fstatfs(fd, ctypes.byref(data)) == 0, 'UNQUALIFIED_FILESYSTEM')
  return ctypes.c_long.from_buffer(data).value


def _platform():
  require(sys.platform == 'linux' and hasattr(os, 'geteuid') and
          hasattr(os, 'O_NOFOLLOW') and os.open in os.supports_dir_fd and
          os.mkdir in os.supports_dir_fd, 'UNQUALIFIED_FILESYSTEM')


def _directory(fd, leaf=False):
  info = os.fstat(fd)
  require(stat.S_ISDIR(info.st_mode), 'UNSAFE_OUTPUT')
  require(filesystem_type(fd) in TRUSTED_FS, 'UNQUALIFIED_FILESYSTEM')
  if leaf:
    require(info.st_uid == os.geteuid() and info.st_mode & 0o077 == 0, 'UNSAFE_OUTPUT')
  else:
    # A root-owned sticky directory permits private temp directories, not shared leaves.
    sticky_root = info.st_uid == 0 and bool(info.st_mode & stat.S_ISVTX)
    require(info.st_uid in (0, os.geteuid()) and
            (info.st_mode & 0o022 == 0 or sticky_root), 'UNSAFE_OUTPUT')
  return info


def _absolute(path):
  value = Path(path)
  require('..' not in value.parts and '\x00' not in str(value), 'UNSAFE_OUTPUT')
  return value.absolute()


def _walk(path, create=False, exclusive=False):
  _platform()
  path = _absolute(path)
  require(len(path.parts) > 1, 'UNSAFE_OUTPUT')
  fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
  try:
    _directory(fd)
    for index, part in enumerate(path.parts[1:]):
      leaf = index == len(path.parts) - 2
      if create:
        try:
          os.mkdir(part, 0o700, dir_fd=fd)
        except FileExistsError:
          require(not (leaf and exclusive), 'OUTPUT_FILE_COLLISION')
      next_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)
      os.close(fd)
      fd = next_fd
      _directory(fd, leaf=leaf)
    return path, fd
  except BaseException:
    os.close(fd)
    raise


@dataclass(frozen=True, slots=True)
class FileRef:
  directory: 'SecureDirectory'
  name: str


class SecureDirectory:
  def __init__(self, path, fd):
    self.path, self.fd = path, fd
    self.identity = (os.fstat(fd).st_dev, os.fstat(fd).st_ino)
    self.closed = False

  @classmethod
  def create(cls, path):
    location, fd = _walk(path, create=True, exclusive=True)
    return cls(location, fd)

  @classmethod
  def existing(cls, path):
    location, fd = _walk(path)
    return cls(location, fd)

  def __str__(self):
    return str(self.path)

  def __truediv__(self, name):
    require(type(name) is str and name not in ('', '.', '..') and
            '/' not in name and '\\' not in name and '\x00' not in name, 'UNSAFE_OUTPUT_FILE')
    return FileRef(self, name)

  def close(self):
    if not self.closed:
      os.close(self.fd)
      self.closed = True

  def verify(self):
    require(not self.closed, 'UNSAFE_OUTPUT')
    _directory(self.fd, leaf=True)
    _, check = _walk(self.path)
    try:
      info = os.fstat(check)
      require((info.st_dev, info.st_ino) == self.identity, 'OUTPUT_PATH_CHANGED')
    finally:
      os.close(check)

  def write(self, name, data):
    self / name
    self.verify()
    try:
      fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                   0o600, dir_fd=self.fd)
    except FileExistsError as error:
      raise SecurityError('OUTPUT_FILE_COLLISION') from error
    with os.fdopen(fd, 'wb') as stream:
      self._file(stream.fileno())
      stream.write(data)
      stream.flush()
    self.verify()

  def _file(self, fd):
    info = os.fstat(fd)
    require(stat.S_ISREG(info.st_mode) and info.st_uid == os.geteuid() and
            info.st_mode & 0o077 == 0 and info.st_nlink == 1, 'UNSAFE_OUTPUT_FILE')
    require(filesystem_type(fd) in TRUSTED_FS, 'UNQUALIFIED_FILESYSTEM')
    return info

  def read(self, name, expected_bytes=None, max_bytes=None):
    self / name
    self.verify()
    fd = os.open(name, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=self.fd)
    with os.fdopen(fd, 'rb') as stream:
      info = self._file(stream.fileno())
      require(expected_bytes is None or info.st_size == expected_bytes, 'INVALID_INPUT_SCHEMA')
      bound = expected_bytes if expected_bytes is not None else max_bytes
      data = stream.read() if bound is None else stream.read(bound + 1)
    self.verify()
    return data


def write_private(path, data):
  if isinstance(path, FileRef):
    path.directory.write(path.name, data)
    return
  # Compatibility for existing F49 callers, without path-following output writes.
  path = _absolute(path)
  directory = SecureDirectory.existing(path.parent)
  try:
    directory.write(path.name, data)
  finally:
    directory.close()


def read_output(path, expected_bytes=None, max_bytes=None):
  require(isinstance(path, FileRef), 'UNSAFE_OUTPUT_FILE')
  return path.directory.read(path.name, expected_bytes, max_bytes)


def from_worker(path, dir_descriptor, proof_descriptor):
  require(type(dir_descriptor) is int and dir_descriptor >= 0 and
          type(proof_descriptor) is int and proof_descriptor >= 0, 'WORKER_OWNERSHIP_REQUIRED')
  _platform()
  require(stat.S_ISFIFO(os.fstat(proof_descriptor).st_mode), 'WORKER_OWNERSHIP_REQUIRED')
  with os.fdopen(os.dup(proof_descriptor), 'rb') as stream:
    data = stream.read(4097)
  require(len(data) <= 4096, 'WORKER_OWNERSHIP_REQUIRED')
  proof = json.loads(data)
  fd = os.dup(dir_descriptor)
  try:
    location = _absolute(path)
    info = _directory(fd, leaf=True)
    require(proof == {'parent_pid': os.getppid(), 'path': str(location),
                      'device': info.st_dev, 'inode': info.st_ino}, 'WORKER_OWNERSHIP_REQUIRED')
    result = SecureDirectory(location, fd)
    result.verify()
    require(not os.listdir(fd), 'WORKER_OUTPUT_NOT_EMPTY')
    return result
  except BaseException:
    os.close(fd)
    raise


def run_worker(command, output, timeout):
  output.verify()
  read_fd, write_fd = os.pipe()
  try:
    info = os.fstat(output.fd)
    proof = json.dumps({'parent_pid': os.getpid(), 'path': str(output.path),
                        'device': info.st_dev, 'inode': info.st_ino}).encode('utf-8')
    require(len(proof) <= 4096, 'WORKER_OWNERSHIP_REQUIRED')
    os.write(write_fd, proof)
    os.close(write_fd)
    write_fd = -1
    result = subprocess.run([*command, '--output-dir-fd', str(output.fd), '--worker-proof-fd', str(read_fd)],
                            pass_fds=(output.fd, read_fd), capture_output=True, timeout=timeout, check=False)
    output.verify()
    return result
  finally:
    os.close(read_fd)
    if write_fd >= 0:
      os.close(write_fd)


@contextmanager
def private_decoder():
  """Capture Python prints and suppress native decoder fd output, including tracebacks."""
  saved = []
  libc = ctypes.CDLL(None)
  libc.fflush.argtypes = [ctypes.c_void_p]
  libc.fflush.restype = ctypes.c_int
  sys.stdout.flush()
  sys.stderr.flush()
  require(libc.fflush(None) == 0, 'UNEXPECTED_INTERNAL_ERROR')
  with io.StringIO() as sink, open(os.devnull, 'w') as null:
    from contextlib import redirect_stderr, redirect_stdout
    try:
      for descriptor in (1, 2):
        saved.append((descriptor, os.dup(descriptor)))
        os.dup2(null.fileno(), descriptor)
      with redirect_stdout(sink), redirect_stderr(sink):
        yield
    finally:
      # Flush native stdio while fds still point at /dev/null. Restore even on failure.
      try:
        require(libc.fflush(None) == 0, 'UNEXPECTED_INTERNAL_ERROR')
      finally:
        for descriptor, backup in saved:
          os.dup2(backup, descriptor)
          os.close(backup)
