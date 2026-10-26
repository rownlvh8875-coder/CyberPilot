"""Experimental standalone Stage2 arithmetic; no scientific-runtime integration.

CANONICAL_STAGE2_SEPARATE_BINARY64_LEFT_FOLD_V1 is prospective numerical
semantics. It does not reproduce historical batch-dependent BLAS output.
Only in-memory arrays enter this module. No model/file/network loading API.
"""

import ctypes
from functools import lru_cache
import math
import platform
import struct
import sys
import numpy as np

STATUS = 'EXPERIMENTAL_NON_WIRED'
SEMANTICS = 'CANONICAL_STAGE2_SEPARATE_BINARY64_LEFT_FOLD_V1'
FEATURE_DIMENSIONS = (5, 13, 33, 93)
NORMALIZER_FIELDS = frozenset(('mean', 'std', 'constant', 'effective', 'constant_reference'))


def _require(valid, code):
  if not valid:
    raise ValueError(code)


def _bits(value):
  return struct.unpack('=Q', struct.pack('=d', value))[0]


@lru_cache(maxsize=1)
def _rounding_reader():
  # A system fenv query, not a model/file loader. Never changes the fenv.
  function = ctypes.CDLL('libm.so.6').fegetround
  function.argtypes = []
  function.restype = ctypes.c_int
  return function


def _rounding_mode():
  return _rounding_reader()()


def qualify_environment():
  """Fail closed outside the tested version/ABI/fenv and arithmetic witnesses.

  This is not a universal CPU/compiler certification. Native optimization and
  other builds require their own qualification; no fenv setting is modified.
  """
  failure = 'CANONICAL_STAGE2_ENVIRONMENT_NOT_QUALIFIED'
  f = sys.float_info
  _require(
    sys.implementation.name == 'cpython'
    and sys.version_info[:3] == (3, 12, 13)
    and platform.system() == 'Linux'
    and platform.machine() == 'x86_64'
    and np.__version__ == '2.5.3',
    failure,
  )
  _require(
    f.radix == 2 and f.mant_dig == 53 and f.max_exp == 1024 and f.min_exp == -1021 and struct.calcsize('d') == 8 and np.dtype(np.float64).itemsize == 8, failure
  )
  try:
    _require(_rounding_mode() == 0, failure)  # Linux FE_TONEAREST.
  except (OSError, AttributeError) as error:
    raise ValueError(failure) from error
  tiny = float.fromhex('0x0.0000000000001p-1022')
  normal = float.fromhex('0x1p-1022')
  _require(_bits(tiny * 1.0) == 1 and _bits(normal * 0.5) == 0x0008000000000000 and _bits(tiny / 2.0) == 0, failure)
  a, b = 1.0 + 2.0**-27, 1.0 - 2.0**-27
  product = a * b
  residual = product - 1.0
  _require(_bits(product) == 0x3FF0000000000000 and _bits(residual) == 0 and _bits(1.0 + 2.0**-53) == 0x3FF0000000000000, failure)
  return {
    'status': 'QUALIFIED_TESTED_ENVIRONMENT',
    'python': platform.python_version(),
    'numpy': np.__version__,
    'architecture': platform.machine(),
    'compiler': platform.python_compiler(),
    'rounding': 'NEAREST_TIES_EVEN',
    'gradual_underflow': True,
    'separate_multiply_add_witness': True,
  }


def _model_columns(model, dimension):
  code = 'CANONICAL_STAGE2_MODEL_INVALID'
  _require(type(model) is dict and 'normalizer' in model and 'coefficients' in model, code)
  norm, coefficients = model['normalizer'], model['coefficients']
  _require(type(norm) is dict and set(norm) == NORMALIZER_FIELDS, code)
  for name in ('mean', 'std', 'constant_reference'):
    array = norm[name]
    _require(type(array) is np.ndarray and array.dtype == np.float64 and array.shape == (dimension,) and bool(np.isfinite(array).all()), code)
  mask, indices = norm['constant'], norm['effective']
  _require(type(mask) is np.ndarray and mask.dtype == np.bool_ and mask.shape == (dimension,) and not bool(mask[0]), code)
  _require(
    type(indices) is np.ndarray
    and indices.dtype == np.int64
    and indices.ndim == 1
    and len(indices) > 0
    and indices[0] == 0
    and np.array_equal(indices, np.flatnonzero(~mask)),
    code,
  )
  _require(bool((norm['std'][indices[1:]] > 0).all()) and bool((norm['std'][mask] == 0).all()), code)
  _require(
    type(coefficients) is np.ndarray and coefficients.dtype == np.float64 and coefficients.shape == (len(indices),) and bool(np.isfinite(coefficients).all()),
    code,
  )
  # Convert each exact binary64 value once. Effective order is verified, never repaired.
  return tuple((int(j), float(norm['mean'][j]), float(norm['std'][j]), float(coefficients[k])) for k, j in enumerate(indices))


def _row_delta(row, columns):
  accumulator = 0.0
  for position, mean, std, coefficient in columns:
    if position == 0:
      normalized = 1.0
    else:
      difference = float(row[position]) - mean
      normalized = difference / std
      _require(math.isfinite(difference) and math.isfinite(normalized), 'CANONICAL_STAGE2_NORMALIZATION_NONFINITE')
    product = normalized * coefficient
    accumulator = accumulator + product
    _require(math.isfinite(product) and math.isfinite(accumulator), 'CANONICAL_STAGE2_REDUCTION_NONFINITE')
  return accumulator


def canonical_predict_delta(x, stage2_model):
  """Return original-order float64 deltas; separately rounded scalar left fold.

  Matrix validation allocates an N*P finite-mask temporary; output is O(N),
  model scalars O(P), arithmetic O(NP). No projection is reimplemented here.
  Zero-row batches still require a valid environment/model. Inputs are read-only.
  """
  qualify_environment()
  code = 'CANONICAL_STAGE2_INPUT_INVALID'
  _require(type(x) is np.ndarray and x.dtype == np.float64 and x.ndim == 2, code)
  _require(x.shape[1] in FEATURE_DIMENSIONS and bool(np.isfinite(x).all()) and bool((x[:, 0] == 1.0).all()), code)
  columns = _model_columns(stage2_model, x.shape[1])
  delta = np.empty(x.shape[0], dtype=np.float64)
  for ordinal, row in enumerate(x):
    delta[ordinal] = _row_delta(row, columns)
  return delta
