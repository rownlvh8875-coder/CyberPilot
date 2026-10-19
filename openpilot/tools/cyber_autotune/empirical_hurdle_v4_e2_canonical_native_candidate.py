"""Explicit receipt-bound native lab candidate. No build, discovery or auto-load.

The caller supplies a public synthetic build receipt and its independently held
hash. These checks detect artifact drift, not malicious same-user provenance or
private input authority. No existing runtime imports this module.
"""

import ctypes
import hashlib
import json
import os
from pathlib import Path
import stat
import threading
import numpy as np
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_stage2 as frozen

STATUS = 'EXPERIMENTAL_NATIVE_CANDIDATE_NON_WIRED'
SEMANTICS = frozen.SEMANTICS
SOURCE = Path(__file__).with_suffix('.c')
ABI = 'C11_LINUX_X86_64_DOUBLE_SIZE_T_INT64_V1'
FLAGS = (
  '-O2',
  '-std=c11',
  '-fPIC',
  '-shared',
  '-fno-fast-math',
  '-ffp-contract=off',
  '-fno-associative-math',
  '-frounding-math',
  '-fexcess-precision=standard',
  '-fno-tree-vectorize',
  '-mfpmath=sse',
  '-msse2',
  '-Wall',
  '-Wextra',
  '-Werror',
)
D = ctypes.POINTER(ctypes.c_double)
I = ctypes.POINTER(ctypes.c_int64)
S = ctypes.c_size_t
_LOAD_LOCK = threading.Lock()
_LOADED = None  # One verified inode/handle/retained CLOEXEC fd per process.


def need(ok, code='CANONICAL_NATIVE_ARTIFACT_CONFLICT'):
  if not ok:
    raise ValueError(code)


def canonical(value):
  return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def _stamp(fd):
  st = os.fstat(fd)
  return (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns, st.st_mode, st.st_uid, st.st_nlink)


def _open_member(path, mode, cap):
  # Descriptor-relative no-follow traversal pins each ancestor before descent.
  need(path.is_absolute() and '..' not in path.parts and '.' not in path.parts)
  directory = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
  try:
    for component in path.parts[1:-1]:
      child = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=directory)
      os.close(directory)
      directory = child
    parent = os.fstat(directory)
    need(parent.st_uid == os.getuid() and stat.S_IMODE(parent.st_mode) == 0o700)
    fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=directory)
    try:
      st = os.fstat(fd)
      need(stat.S_ISREG(st.st_mode) and st.st_uid == os.getuid() and st.st_nlink == 1 and stat.S_IMODE(st.st_mode) == mode and st.st_size <= cap)
    except BaseException:
      os.close(fd)
      raise
    return fd
  finally:
    os.close(directory)


class NativeCandidate:
  STATUS = STATUS

  def __init__(self, receipt_path, expected_receipt_sha256):
    with _LOAD_LOCK:
      self._initialize(receipt_path, expected_receipt_sha256)

  def _initialize(self, receipt_path, expected_receipt_sha256):
    global _LOADED
    frozen.qualify_environment()
    path = Path(receipt_path)
    need(path.is_absolute() and path.name == 'build.json')
    fd = _open_member(path, 0o600, 65536)
    try:
      stamp = _stamp(fd)
      with os.fdopen(os.dup(fd), 'rb') as stream:
        raw = stream.read(65537)
      need(_stamp(fd) == stamp)
    finally:
      os.close(fd)
    need(hashlib.sha256(raw).hexdigest() == expected_receipt_sha256)
    receipt = json.loads(raw)
    need(receipt['schema'] == 'PUBLIC_CANONICAL_NATIVE_BUILD_V1' and receipt['ABI'] == ABI)
    need(receipt['source_sha256'] == hashlib.sha256(SOURCE.read_bytes()).hexdigest())
    need(tuple(receipt['flags']) == FLAGS and receipt['compiler_version'] == '13.3.0')
    need(receipt['private_execution_authorized'] is False and receipt['runtime_integration_authorized'] is False)
    need(receipt['library'] == 'canonical_candidate.so' and receipt['machine_code']['no_fused_multiply_add'] is True)
    fd = _open_member(path.parent / receipt['library'], 0o500, 8 * 1024**2)
    retained = False
    try:
      stamp = _stamp(fd)
      with os.fdopen(os.dup(fd), 'rb') as stream:
        need(hashlib.file_digest(stream, 'sha256').hexdigest() == receipt['binary_sha256'])
      need(_stamp(fd) == stamp)
      identity = (stamp[0], stamp[1], receipt['binary_sha256'])
      if _LOADED is None:
        library = ctypes.CDLL('/proc/self/fd/' + str(fd), mode=os.RTLD_LOCAL | os.RTLD_NOW)
        need(_stamp(fd) == stamp)
        library.cp_environment.argtypes, library.cp_environment.restype = [], ctypes.c_int
        library.cp_noop.argtypes, library.cp_noop.restype = [], ctypes.c_int
        library.cp_stage2.argtypes = [D, S, S, I, S, D, D, D, S, D, D, S]
        library.cp_stage2.restype = ctypes.c_int
        need(library.cp_environment() == 0, 'CANONICAL_STAGE2_ENVIRONMENT_NOT_QUALIFIED')
        _LOADED = (identity, library, fd)
        retained = True
      else:
        need(_LOADED[0] == identity, 'CANONICAL_NATIVE_SECOND_ARTIFACT_DENIED')
        library = _LOADED[1]
        need(_stamp(_LOADED[2]) == stamp)
      need(library.cp_environment() == 0, 'CANONICAL_STAGE2_ENVIRONMENT_NOT_QUALIFIED')
    finally:
      if not retained:
        os.close(fd)
    self.library, self.receipt, self.receipt_path = library, receipt, path

  def noop(self):
    return self.library.cp_noop()

  def _prepare(self, x, model, trace):
    frozen.qualify_environment()
    code = 'CANONICAL_NATIVE_INPUT_INVALID'
    need(type(x) is np.ndarray and x.dtype == np.float64 and x.ndim == 2 and x.shape[1] in frozen.FEATURE_DIMENSIONS, code)
    need(bool(np.isfinite(x).all()) and bool((x[:, 0] == 1.0).all()), code)
    frozen._model_columns(model, x.shape[1])  # Validation only, never Python output substitution.
    x = np.require(x, dtype=np.float64, requirements=['C', 'A'])
    norm, beta = model['normalizer'], np.require(model['coefficients'], requirements=['C', 'A'])
    indices = np.require(norm['effective'], requirements=['C', 'A'])
    mean, std = (np.require(norm[k], requirements=['C', 'A']) for k in ('mean', 'std'))
    n, p, k = len(x), x.shape[1], len(indices)
    output = np.empty(n, np.float64)
    z = np.empty((n, k), np.float64) if trace else None
    args = [
      x.ctypes.data_as(D),
      n,
      p,
      indices.ctypes.data_as(I),
      k,
      mean.ctypes.data_as(D),
      std.ctypes.data_as(D),
      beta.ctypes.data_as(D),
      n,
      output.ctypes.data_as(D),
      z.ctypes.data_as(D) if trace else D(),
      n * k if trace else 0,
    ]
    return args, output, z

  def arguments(self, x, model, *, trace=False):
    """Explicit checked arguments for ABI-negative tests and lab-only timing."""
    return self._prepare(x, model, trace)[0]

  def predict(self, x, model, *, trace=False):
    args, output, z = self._prepare(x, model, trace)
    status = self.library.cp_stage2(*args)
    need(status == 0, 'CANONICAL_NATIVE_NUMERICAL_STATUS_' + str(status))
    return (output, z) if trace else output
