"""Read-only input snapshot checks for a trusted local replay coordinator.

Grants and review digests are externally reviewed assertions, not authentication.
Receipts are not capabilities: containment must reopen/reverify inputs before use.
No replay, log decoding, estimator, Params or actuator imports are allowed here.
"""
from contextlib import contextmanager
import hashlib
import json
import os
import re
import stat
import subprocess


# Infrastructure resource ceilings, not control or scientific acceptance limits.
MAX_INPUT_BYTES = 512 * 1024 * 1024
MAX_SOURCE_BYTES = 64 * 1024 * 1024
MAX_SOURCE_FILES = 256
READ_CHUNK_BYTES = 1024 * 1024
MAX_GRANTS = 10000
MAX_REPOSITORIES = 64
GIT_TIMEOUT_S = 15
PROTECTED_SEGMENTS = frozenset((53, 71))


def _fields(value, names):
  if type(value) is not dict or set(value) != set(names.split()):
    raise ValueError('INVALID_FIELDS')


def _hex(value, length=64):
  return type(value) is str and re.fullmatch('[0-9a-f]{' + str(length) + '}', value) is not None


def _path(value, *, absolute=False):
  if (type(value) is not str or not value or len(value) > 4096 or '\x00' in value or '\\' in value or
      value.startswith('/') != absolute):
    raise ValueError('INVALID_PATH')
  parts = value[1:].split('/') if absolute else value.split('/')
  if any(part in ('', '.', '..') for part in parts):
    raise ValueError('INVALID_PATH')
  return parts


def _positive_time(value):
  return type(value) is int and 0 < value < 2 ** 63


def _initial_state(state):
  _fields(state, 'run_start_ns cache_mode cache_time_ns previous_cp_sha256 torque_cache_sha256 ' +
                'original_cp_sha256 migrated_cp_sha256 initialized_cp_sha256 review_sha256 sampling_review_sha256')
  if not _positive_time(state['run_start_ns']) or any(not _hex(state[k]) for k in (
    'original_cp_sha256', 'migrated_cp_sha256', 'initialized_cp_sha256', 'review_sha256', 'sampling_review_sha256',
  )):
    raise ValueError('INVALID_INITIAL_STATE')
  if state['cache_mode'] == 'recorded_before_start':
    if (not _positive_time(state['cache_time_ns']) or state['cache_time_ns'] >= state['run_start_ns'] or
        not _hex(state['previous_cp_sha256']) or not _hex(state['torque_cache_sha256'])):
      raise ValueError('INVALID_CACHE_EPOCH')
  elif state['cache_mode'] == 'reviewed_empty':
    if any(state[k] is not None for k in ('cache_time_ns', 'previous_cp_sha256', 'torque_cache_sha256')):
      raise ValueError('CONTRADICTORY_EMPTY_CACHE')
  else:
    raise ValueError('UNKNOWN_CACHE_STATE')


def _validate(request, grants, authority, *, observation=False):
  _fields(request, 'version process input_id source ' + ('purpose' if observation else 'initial_state'))
  if type(request['version']) is not int or request['version'] != 1 or request['process'] != 'torqued':
    raise ValueError('UNSUPPORTED_CONTRACT')
  if observation and request['purpose'] != 'OBSERVE_INITIAL_STATE':
    raise ValueError('UNSUPPORTED_OBSERVATION')
  if not _hex(authority) or type(grants) is not tuple or not 0 < len(grants) <= MAX_GRANTS:
    raise ValueError('INVALID_AUTHORITY')
  if type(request['input_id']) is not str or not 0 < len(request['input_id']) <= 256:
    raise ValueError('INVALID_INPUT_ID')
  ids = set()
  selected = None
  for grant in grants:
    _fields(grant, 'input_id root path role segment size_bytes sha256')
    if type(grant['input_id']) is not str or not 0 < len(grant['input_id']) <= 256 or grant['input_id'] in ids:
      raise ValueError('INVALID_GRANT_ID')
    ids.add(grant['input_id'])
    _path(grant['root'], absolute=True)
    _path(grant['path'])
    if (type(grant['segment']) is not int or grant['segment'] < 0 or
        type(grant['size_bytes']) is not int or not 0 < grant['size_bytes'] <= MAX_INPUT_BYTES or
        not _hex(grant['sha256']) or type(grant['role']) is not str):
      raise ValueError('INVALID_GRANT')
    if grant['input_id'] == request['input_id']:
      selected = grant
  if selected is None or selected['role'] != 'development' or selected['segment'] in PROTECTED_SEGMENTS:
    raise ValueError('INPUT_NOT_AUTHORIZED')
  source = request['source']
  _fields(source, 'root head files')
  _path(source['root'], absolute=True)
  if (not _hex(source['head'], 40) or type(source['files']) is not dict or
      not 0 < len(source['files']) <= MAX_SOURCE_FILES):
    raise ValueError('INVALID_SOURCE')
  for path, digest in source['files'].items():
    _path(path)
    if not _hex(digest):
      raise ValueError('INVALID_SOURCE_DIGEST')
  if not observation:
    _initial_state(request['initial_state'])
  return selected


@contextmanager
def _directory(root):
  parts = _path(root, absolute=True)
  fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
  try:
    for part in parts:
      child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)
      os.close(fd)
      fd = child
    yield fd
  finally:
    os.close(fd)


def _hash_file(root_fd, path, ceiling, expected_size=None):
  parts = _path(path)
  parent = os.dup(root_fd)
  try:
    for part in parts[:-1]:
      child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=parent)
      os.close(parent)
      parent = child
    fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=parent)
    try:
      before = os.fstat(fd)
      if not stat.S_ISREG(before.st_mode) or not 0 <= before.st_size <= ceiling:
        raise ValueError('INVALID_FILE_TYPE_OR_SIZE')
      if expected_size is not None and before.st_size != expected_size:
        raise ValueError('INPUT_SIZE_MISMATCH')
      remaining = before.st_size
      digest = hashlib.sha256()
      while remaining:
        block = os.read(fd, min(READ_CHUNK_BYTES, remaining))
        if not block:
          raise ValueError('FILE_CHANGED_DURING_READ')
        digest.update(block)
        remaining -= len(block)
      after = os.fstat(fd)
      def identity(s):
        return s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns
      if os.read(fd, 1) or identity(before) != identity(after):
        raise ValueError('FILE_CHANGED_DURING_READ')
      return digest.hexdigest()
    finally:
      os.close(fd)
  finally:
    os.close(parent)


def _git(root_fd, *args, missing_ok=False):
  # Directory FD keeps Git on the validated directory even if its name is moved.
  environment = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
  environment.update(GIT_OPTIONAL_LOCKS='0', GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL='/dev/null')
  result = subprocess.run(['/usr/bin/git', '-c', 'core.fsmonitor=false', '-C', f'/proc/self/fd/{root_fd}', *args],
                          pass_fds=(root_fd,), env=environment, stdout=subprocess.PIPE,
                          stderr=subprocess.DEVNULL, timeout=GIT_TIMEOUT_S, check=False)
  if result.returncode != 0 and not (missing_ok and result.returncode == 1):
    raise ValueError('SOURCE_GIT_CHECK_FAILED')
  return result.stdout


def _check_repository(root_fd, head, budget):
  budget[0] -= 1
  if budget[0] < 0:
    raise ValueError('TOO_MANY_REPOSITORIES')
  if _git(root_fd, 'rev-parse', '--show-prefix').strip():
    raise ValueError('SOURCE_NOT_REPOSITORY_ROOT')
  if _git(root_fd, 'rev-parse', 'HEAD').decode().strip() != head:
    raise ValueError('SOURCE_REVISION_MISMATCH')
  if _git(root_fd, 'config', '--name-only', '--get-regexp', r'^filter\..*\.(clean|process)$', missing_ok=True):
    raise ValueError('EXECUTABLE_GIT_FILTER_UNSUPPORTED')
  # Avoid Git recursively invoking a submodule's unchecked filter configuration.
  if _git(root_fd, 'status', '--porcelain=v1', '--untracked-files=no', '--ignore-submodules=all'):
    raise ValueError('SOURCE_DIRTY')
  for row in _git(root_fd, 'ls-files', '--stage', '-z').split(b'\x00'):
    if not row.startswith(b'160000 '):
      continue
    metadata, path = row.split(b'\t', 1)
    child_head = metadata.split()[1].decode('ascii')
    fd = os.dup(root_fd)
    try:
      for part in _path(path.decode('utf-8')):
        child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)
        os.close(fd)
        fd = child
      _check_repository(fd, child_head, budget)
    finally:
      os.close(fd)


def _check_source(root_fd, source):
  _check_repository(root_fd, source['head'], [MAX_REPOSITORIES])
  for path, expected in source['files'].items():
    if _hash_file(root_fd, path, MAX_SOURCE_BYTES) != expected:
      raise ValueError('SOURCE_DIGEST_MISMATCH')


def _digest(value):
  return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def inspect_replay_input(request: dict, *, grants: tuple[dict, ...], authority_sha256: str) -> dict:
  """Verify a local input snapshot; caller owns grant authenticity and clock truth.

CP/cache/sampling hashes are assertions awaiting a native adapter's observations.
This function does not certify those assertions or full environment closure.
"""
  grant = _validate(request, grants, authority_sha256)
  # Snapshot validated plain JSON structures before filesystem operations.
  request, grant = json.loads(json.dumps((request, grant), allow_nan=False))
  try:
    with _directory(request['source']['root']) as source_fd:
      _check_source(source_fd, request['source'])
      with _directory(grant['root']) as input_fd:
        observed = _hash_file(input_fd, grant['path'], MAX_INPUT_BYTES, grant['size_bytes'])
      if observed != grant['sha256']:
        raise ValueError('INPUT_DIGEST_MISMATCH')
      _check_source(source_fd, request['source'])
  except (OSError, subprocess.SubprocessError, UnicodeError):
    raise ValueError('INPUT_OR_SOURCE_UNAVAILABLE') from None
  return {
    'status': 'INPUT_SNAPSHOT_VERIFIED', 'request_sha256': _digest(request),
    'grant_sha256': _digest(grant), 'authority_sha256': authority_sha256,
    'input_sha256': observed, 'input_size_bytes': grant['size_bytes'], 'source_head': request['source']['head'],
    'replay_allowed': False, 'runtime_accepted': False, 'promotable': False,
  }
