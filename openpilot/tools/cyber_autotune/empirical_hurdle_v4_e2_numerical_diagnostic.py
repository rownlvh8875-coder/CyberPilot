"""Differential Stage2 diagnostics only; never an E2 selector or resumed runner.

No tolerance, replacement matmul, gate policy or scientific acceptance change.
The synthetic entry point has no file inputs. Private execution is separately
bound by the scoped diagnostic adapter and its pre-execution review/CI gate.
"""

import os
import platform
import sys
import numpy as np
from openpilot.tools.cyber_autotune import empirical_hurdle_fit_cv_math as frozen

SEED = 20261018
LENGTHS = (1, 5, 15, 45)
MASKS = ('low', 'medium', 'high', 'alternating', 'contiguous')
SCALES = (1e-6, 1.0, 100.0)
ROWS = 1537  # Three 512-row chunks and a one-row tail; fixed before execution.
CHUNK = 512
MAX_ROWS = 336941  # Frozen public maximum TRAIN population, not a discovered size.


def need(condition, code='DIAGNOSTIC_INPUT_CONFLICT'):
  if not condition:
    raise ValueError(code)


def byte_equal(a, b):
  return a.dtype == b.dtype and a.shape == b.shape and a.tobytes(order='C') == b.tobytes(order='C')


def layout(a):
  return {'shape': list(a.shape), 'dtype': a.dtype.str, 'strides': list(a.strides), 'C': bool(a.flags.c_contiguous), 'F': bool(a.flags.f_contiguous),
          'data_alignment_mod64': int(a.ctypes.data % 64)}


def compare(a, b, current):
  """Aggregate diagnostics, including bits and signed zero; never row witnesses."""
  need(a.dtype == b.dtype == np.float64 and a.ndim == b.ndim == 1 and a.shape == b.shape)
  need(current.shape == a.shape and current.dtype == np.int64)
  need(bool(np.all(np.isfinite(a))) and bool(np.all(np.isfinite(b))))
  ua, ub = a.view(np.uint64), b.view(np.uint64)
  # Monotone IEEE754 key; both signed zeros have adjacent keys (distance one).
  sign = np.uint64(1 << 63)
  ka = np.where((ua & sign) != 0, ~ua, ua | sign)
  kb = np.where((ub & sign) != 0, ~ub, ub | sign)
  distance = np.maximum(ka, kb) - np.minimum(ka, kb)
  absolute = np.abs(a - b)
  denominator = np.maximum(np.abs(a), np.abs(b))
  relative = np.zeros(len(a), np.float64)
  np.divide(absolute, denominator, out=relative, where=denominator != 0)
  pa, pb = frozen.project(current.astype(np.float64) + a), frozen.project(current.astype(np.float64) + b)
  return {
    'raw_byte_equal': byte_equal(a, b), 'exact_float_equal': bool(np.array_equal(a, b)),
    'bit_mismatch_count': int(np.count_nonzero(ua != ub)), 'numeric_mismatch_count': int(np.count_nonzero(a != b)),
    'max_absolute_difference': float(np.max(absolute, initial=0)), 'max_relative_difference': float(np.max(relative, initial=0)),
    'max_ULP_distance': int(np.max(distance, initial=0)),
    'signed_zero_difference_count': int(np.count_nonzero((a == 0) & (b == 0) & (ua != ub))),
    'projected_tick_mismatch_count': int(np.count_nonzero(pa != pb)),
    'byte_qualification': 'PASS' if byte_equal(a, b) else 'FAIL',
  }


def diagnose(blocks, gate, stage2, *, current):
  """A=segment/order512 cache, B=chunk subset, C=whole-job D0 subset.

  Full transformed rows are compared before matmul. A separate full-all-row
  call helps distinguish chunk boundaries from the selected-row batch change.
  Only aggregate results escape; predictions/transformed rows remain in RAM.
  """
  need(type(blocks) in (tuple, list) and 0 < len(blocks) <= 154)
  need(gate.dtype == bool and gate.ndim == 1 and 0 < len(gate) <= MAX_ROWS and np.any(gate))
  need(current.dtype == np.int64 and current.shape == gate.shape)
  need(sum(len(x) for x in blocks) == len(gate))
  dim = blocks[0].shape[1]
  need(dim in tuple(2 * n + 3 for n in LENGTHS))
  for x in blocks:
    need(x.ndim == 2 and x.shape[1] == dim and x.dtype == np.float64 and x.flags.c_contiguous and np.all(np.isfinite(x)))
  x = np.ascontiguousarray(np.concatenate(blocks))
  selected = np.ascontiguousarray(x[gate])
  z_full = frozen.transform(x, stage2['normalizer'])
  z_selected = frozen.transform(selected, stage2['normalizer'])
  need(z_full.dtype == z_selected.dtype == np.float64)
  a, b, transformed_b = [], [], []
  n = 0
  transformed_chunk_equal = True
  calls = {'all_chunk': 0, 'chunk_subset': 0, 'whole_subset': 1, 'whole_all': 1}
  batch_layouts = []
  for block in blocks:
    for start in range(0, len(block), CHUNK):
      part = np.ascontiguousarray(block[start:start + CHUNK])
      stop = n + len(part)
      mask = gate[n:stop]
      transformed = frozen.transform(part, stage2['normalizer'])
      transformed_chunk_equal &= byte_equal(transformed, z_full[n:stop])
      a.append(frozen.predict_delta(part, stage2))
      calls['all_chunk'] += 1
      if np.any(mask):
        sub = np.ascontiguousarray(part[mask])
        zs = frozen.transform(sub, stage2['normalizer'])
        transformed_b.append(zs)
        b.append(frozen.predict_delta(sub, stage2))
        calls['chunk_subset'] += 1
        batch_layouts.append({'all': layout(transformed), 'subset': layout(zs)})
      n = stop
  a = np.concatenate(a)
  b = np.concatenate(b)
  c = frozen.predict_delta(selected, stage2)
  full = frozen.predict_delta(x, stage2)
  zb = np.concatenate(transformed_b)
  za = np.ascontiguousarray(z_full[gate])
  transform_equal = transformed_chunk_equal and byte_equal(za, zb) and byte_equal(za, z_selected)
  pairs = {'B_vs_A': compare(b, a[gate], current[gate]), 'C_vs_A': compare(c, a[gate], current[gate]),
           'B_vs_C': compare(b, c, current[gate]), 'whole_all_vs_A': compare(full, a, current)}
  return {
    'transformed_rows_byte_equal': transform_equal,
    'transformed_chunk_vs_whole_equal': transformed_chunk_equal,
    'transformed_B_vs_A_equal': byte_equal(za, zb), 'transformed_C_vs_A_equal': byte_equal(za, z_selected),
    'comparisons': pairs, 'calls': calls,
    'target_failure_reproduced': not pairs['B_vs_A']['raw_byte_equal'],
    'classification': 'TRANSFORMED_ROW_CONFLICT' if not transform_equal else
      'BATCH_LAYOUT_SENSITIVE_MATMUL_DIFFERENCE' if any(not p['raw_byte_equal'] for p in pairs.values()) else 'NO_DIFFERENCE_OBSERVED',
    'input_layout': layout(x), 'whole_selected_layout': layout(selected),
    'transformed_layout': layout(z_full), 'whole_selected_transformed_layout': layout(z_selected),
    'batch_layouts': batch_layouts,
  }


def fixture(length, scale, mask_name):
  need(length in LENGTHS and scale in SCALES and mask_name in MASKS)
  rng = np.random.default_rng(SEED + length)
  dim = 2 * length + 3
  x = rng.standard_normal((ROWS, dim)).astype(np.float64)
  x[:, 0] = 1.0
  x[:, -3:-1] = np.rint(3 * x[:, -3:-1])
  x[:, -1] = np.abs(x[:, -1])
  x[9] = x[8]
  x[10, 1:] = np.nextafter(x[8, 1:], np.inf)
  mean = rng.uniform(-0.5, 0.5, dim)
  std = rng.uniform(0.5, 2.0, dim)
  mean[0], std[0] = 0.0, 1.0
  norm = {'mean': mean, 'std': std, 'constant': np.zeros(dim, bool), 'effective': np.arange(dim), 'constant_reference': np.zeros(dim)}
  coeff = scale * rng.standard_normal(dim)
  index = np.arange(ROWS)
  masks = {'low': index % 32 == 0, 'medium': index % 4 == 0, 'high': index % 4 != 0,
           'alternating': index % 2 == 0, 'contiguous': (index >= ROWS // 4) & (index < 3 * ROWS // 4)}
  return x, masks[mask_name], {'normalizer': norm, 'coefficients': coeff}


def environment():
  return {'python': sys.version.split()[0], 'numpy': np.__version__, 'architecture': platform.machine(),
          'float64': {'bits': np.finfo(np.float64).bits, 'epsilon': float(np.finfo(np.float64).eps)},
          'threads': {k: os.environ.get(k) for k in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS')},
          'numpy_build': np.show_config(mode='dicts')}


def synthetic():
  rows = []
  for length in LENGTHS:
    for scale in SCALES:
      for mask in MASKS:
        x, gate, model = fixture(length, scale, mask)
        row = diagnose([x], gate, model, current=np.zeros(len(x), np.int64))
        row.pop('batch_layouts')
        rows.append({'L': length, 'coefficient_scale': scale, 'mask': mask, **row})
  return {'schema': 'V4_E2_NUMERICAL_SYNTHETIC_RESULT_V1', 'seed': SEED, 'fixtures': rows, 'environment': environment(),
          'private_input_openings': 0, 'E2_resumed': False, 'tolerance_applied': False}


def aligned_copy(a):
  """Synthetic control only: force the same 64-byte base alignment, same bytes."""
  need(a.dtype == np.float64 and a.flags.c_contiguous)
  storage = np.empty(a.size + 8, np.float64)
  offset = (-storage.ctypes.data % 64) // 8
  out = storage[offset:offset + a.size].reshape(a.shape)
  out[:] = a
  need(out.ctypes.data % 64 == 0 and byte_equal(a, out))
  return out


def parity_control():
  """Finite followup, predeclared after base60 and before this experiment.

  Keep seed/matrices/scales. Flip first selection bit of every full512 chunk;
  leave the one-row tail unchanged. No fixture/seed search. Also compare the
  same transformed rows with 64-byte-aligned matmul operands to control base
  pointer alignment. This is evidence, never a replacement Stage2 runtime.
  """
  rows = []
  for length in LENGTHS:
    for scale in SCALES:
      for mask_name in MASKS:
        x, gate, model = fixture(length, scale, mask_name)
        odd = gate.copy()
        for start in range(0, len(x) - CHUNK + 1, CHUNK):
          odd[start] = ~odd[start]
        result = diagnose([x], odd, model, current=np.zeros(len(x), np.int64))
        result.pop('batch_layouts')
        coefficients = aligned_copy(model['coefficients'])
        original, selected = [], []
        for start in range(0, len(x), CHUNK):
          part, mask = x[start:start + CHUNK], odd[start:start + CHUNK]
          z = aligned_copy(frozen.transform(part, model['normalizer']))
          original.append((z @ coefficients)[mask])
          if np.any(mask):
            zs = aligned_copy(np.ascontiguousarray(z[mask]))
            selected.append(zs @ coefficients)
        a, b = np.concatenate(original), np.concatenate(selected)
        result['same_alignment_B_vs_A'] = compare(b, a, np.zeros(len(a), np.int64))
        rows.append({'L': length, 'coefficient_scale': scale, 'mask': mask_name, **result})
  return {'schema': 'V4_E2_NUMERICAL_PARITY_CONTROL_V1', 'base_seed': SEED, 'fixtures': rows,
          'adaptation': 'FIXED_BATCH_PARITY_INTERVENTION_NO_SEED_SEARCH', 'private_input_openings': 0}
