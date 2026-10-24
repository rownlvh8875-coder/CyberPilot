"""One-job A/C observation; no alternative private Stage2 computation.

Wrappers return the original transform/output objects unchanged. They retain
RAM-only row witnesses for exact correspondence, never serialize row values.
Synthetic canonical reduction is diagnostic only, not a replacement kernel.
"""

from contextlib import ExitStack
from unittest.mock import patch
import hashlib
import numpy as np
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_v2_qualification as q
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_numerical_diagnostic as prior

need = q.need
MAX_ROWS = 336941
CHUNK = 512
MODEL_FIELDS = ('normalizer', 'coefficients')


def snapshot(model):
  need(set(model) == set(MODEL_FIELDS), 'Q1_DIAGNOSTIC_MODEL_SCHEMA')
  arrays = {'coefficients': model['coefficients'], **model['normalizer']}
  return {k: (a.dtype.str, a.shape, a.tobytes(order='C')) for k, a in arrays.items()}


def classify(a, c, current, *, input_equal, transform_equal, model_unchanged):
  comparison = prior.compare(c, a, current)
  cases = []
  if not (input_equal and transform_equal and model_unchanged):
    cases.append('INPUT_OR_TRANSFORM_CONFLICT')
  elif not comparison['raw_byte_equal']:
    cases.append('SIGNED_ZERO_ONLY_MISMATCH' if comparison['exact_float_equal'] else 'BATCH_LAYOUT_SENSITIVE_MATMUL_DIFFERENCE')
  else:
    cases.append('NO_DIFFERENCE_OBSERVED')
  if comparison['projected_tick_mismatch_count']:
    cases.append('PROJECTED_TICK_CHANGED')
  return {
    'cases': cases,
    'comparisons': comparison,
    'nonfinite': False,
    'finite_range_valid': True,
    'continuous_delta_difference': not comparison['exact_float_equal'],
    'rounding_decision_changed': bool(comparison['projected_tick_mismatch_count']),
  }


class Trace:
  """No inference substitution: same input, same callable, same returned objects."""

  def __init__(self, stage2, gate, dimension):
    need(gate.dtype == np.bool_ and gate.ndim == 1 and 0 < len(gate) <= MAX_ROWS and bool(np.any(gate)), 'Q1_DIAGNOSTIC_NONEMPTY_D0_REQUIRED')
    self.model, self.gate, self.mode = stage2, gate, 'A'
    self.math = q.decision.frozen.m
    self.predict_original, self.transform_original = self.math.predict_delta, self.math.transform
    n = int(np.count_nonzero(gate))
    self.xa = np.empty((n, dimension), np.float64)
    self.za = np.empty((n, len(stage2['coefficients'])), np.float64)
    self.a_offset = self.selected_offset = 0
    self.calls = {'A': 0, 'C': 0, 'B': 0, 'W': 0, 'canonical_private': 0}
    self.layouts, self.current_transform_count = [], 0
    self.xc = self.zc = self.c = None

  def predict(self, x, model):
    need(model is self.model and self.mode in ('A', 'C'), 'Q1_DIAGNOSTIC_UNEXPECTED_PREDICTION')
    need(x.dtype == np.float64 and x.ndim == 2 and x.flags.c_contiguous, 'Q1_DIAGNOSTIC_DESIGN_LAYOUT')
    self.current_transform_count = 0
    if self.mode == 'A':
      need(0 < len(x) <= CHUNK and self.a_offset + len(x) <= len(self.gate))
      self.mask = self.gate[self.a_offset : self.a_offset + len(x)]
      self.stop = self.selected_offset + int(np.count_nonzero(self.mask))
      self.xa[self.selected_offset : self.stop] = x[self.mask]
    else:
      need(self.calls['C'] == 0 and self.a_offset == len(self.gate) and self.selected_offset == len(x) == len(self.xa))
      self.xc = x
    self.calls[self.mode] += 1
    value = self.predict_original(x, model)
    need(self.current_transform_count == 1, 'Q1_DIAGNOSTIC_TRANSFORM_CALL_COUNT')
    if self.mode == 'A':
      self.a_offset += len(x)
      self.selected_offset = self.stop
    else:
      self.c = value
    return value

  def transform(self, x, normalizer):
    need(normalizer is self.model['normalizer'], 'Q1_DIAGNOSTIC_NORMALIZER_OBJECT_CONFLICT')
    z = self.transform_original(x, normalizer)
    self.current_transform_count += 1
    if self.mode == 'A':
      self.za[self.selected_offset : self.stop] = z[self.mask]
      self.layouts.append({'input': prior.layout(x), 'transformed': prior.layout(z)})
    else:
      self.zc = z
      self.selected_layout = {'input': prior.layout(x), 'transformed': prior.layout(z)}
    return z


def diagnose_training(blocks, candidate, stage2, p, y, prior_delta, identity, *, counters=None):
  """One D0 reconstruction, frozen fixed512 A once and frozen whole-job C once."""
  need(identity['job'][0] == candidate and tuple(identity['job']) in q.JOBS, 'Q1_DIAGNOSTIC_EXACT_JOB')
  d = q.decision
  d.validate(p, y, prior_delta)
  counters = {} if counters is None else counters
  d0 = d.reconstruct_D0(p, y, role='TRAIN', counters=counters)
  gate = p > d0['value']
  dimension = q.layout(blocks, candidate, len(p))
  before = snapshot(stage2)
  trace = Trace(stage2, gate, dimension)
  with ExitStack() as stack:
    stack.enter_context(patch.object(trace.math, 'predict_delta', trace.predict))
    stack.enter_context(patch.object(trace.math, 'transform', trace.transform))
    cache = q.potentials(blocks, candidate, stage2, p, y, prior_delta, d0['value'], counters)
    trace.mode = 'C'
    proof = q.qualification('Q1', blocks, candidate, stage2, cache, gate, identity, counters)
  need(trace.calls['C'] == 1 and trace.a_offset == len(p) and trace.selected_offset == len(trace.c), 'Q1_DIAGNOSTIC_ROW_CORRESPONDENCE')
  input_equal = d.byte_equal(trace.xa, trace.xc)
  transform_equal = d.byte_equal(trace.za, trace.zc)
  model_equal = before == snapshot(stage2)
  a = cache['u'][gate]
  result = classify(a, trace.c, cache['current'][gate], input_equal=input_equal, transform_equal=transform_equal, model_unchanged=model_equal)
  pa = trace.math.project(cache['current'][gate].astype(np.float64) + a)
  pc = trace.math.project(cache['current'][gate].astype(np.float64) + trace.c)
  result.update(
    input_rows_byte_equal=input_equal,
    transformed_rows_byte_equal=transform_equal,
    coefficient_normalizer_unchanged=model_equal,
    qualification_proof=proof,
    calls=trace.calls,
    A_chunk_layouts=trace.layouts,
    C_layout=trace.selected_layout,
    projection={
      'A': {'shape': list(pa.shape), 'dtype': pa.dtype.str, 'payload_sha256': hashlib.sha256(pa.tobytes()).hexdigest()},
      'C': {'shape': list(pc.shape), 'dtype': pc.dtype.str, 'payload_sha256': hashlib.sha256(pc.tobytes()).hexdigest()},
      'byte_equal': d.byte_equal(pa, pc),
    },
    row_values_persisted=False,
    tolerance_used=False,
    coefficient_instruction_kernel='NOT_IDENTIFIED',
  )
  need((proof['status'] == 'BYTE_EXACT_PASS') == result['comparisons']['raw_byte_equal'], 'Q1_DIAGNOSTIC_OBSERVATION_CONFLICT')
  return result, counters


def outcome(result):
  if 'INPUT_OR_TRANSFORM_CONFLICT' in result['cases']:
    return 'E2_V2_Q1_INPUT_OR_TRANSFORM_CONFLICT'
  if result['comparisons']['raw_byte_equal']:
    return 'E2_V2_Q1_DIAGNOSTIC_REPRODUCTION_CONFLICT'
  if 'BATCH_LAYOUT_SENSITIVE_MATMUL_DIFFERENCE' in result['cases']:
    return 'E2_V2_Q1_BATCH_LAYOUT_NUMERICAL_DIFFERENCE_CONFIRMED'
  if 'SIGNED_ZERO_ONLY_MISMATCH' in result['cases']:
    return 'E2_V2_Q1_ROOT_CAUSE_IDENTIFIED'
  return 'E2_V2_Q1_DIAGNOSTIC_UNRESOLVED'


def canonical_synthetic(z, coefficients):
  """Public fixtures only. Separate multiply/add, left-to-right binary64 order."""
  need(z.dtype == coefficients.dtype == np.float64 and z.ndim == 2 and coefficients.shape == (z.shape[1],))
  out = np.empty(len(z), np.float64)
  for i, row in enumerate(z):
    total = 0.0
    for a, b in zip(row, coefficients, strict=True):
      product = float(a) * float(b)
      total = total + product
    out[i] = total
  return out


def synthetic_controls():
  """Fixed60: same original seeds/shapes/scales/masks, aligned A/C and canonical.

  This is the entire declared set, no seed/mask search or post-hoc subset.
  The original60 plus parity60 are executed separately without modification.
  """
  rows = []
  for length in prior.LENGTHS:
    for scale in prior.SCALES:
      for mask in prior.MASKS:
        x, gate, model = prior.fixture(length, scale, mask)
        coefficients = prior.aligned_copy(model['coefficients'])
        chunks = []
        for start in range(0, len(x), CHUNK):
          z = prior.aligned_copy(prior.frozen.transform(np.ascontiguousarray(x[start : start + CHUNK]), model['normalizer']))
          chunks.append(z @ coefficients)
        a = np.concatenate(chunks)[gate]
        zc = prior.aligned_copy(prior.frozen.transform(np.ascontiguousarray(x[gate]), model['normalizer']))
        c = zc @ coefficients
        canonical = canonical_synthetic(zc, coefficients)
        rows.append(
          {
            'L': length,
            'scale': scale,
            'mask': mask,
            'aligned_A_C': prior.compare(c, a, np.zeros(len(a), np.int64)),
            'C_canonical': prior.compare(c, canonical, np.zeros(len(c), np.int64)),
          }
        )
  return {
    'schema': 'V4_E2_V2_Q1_PUBLIC_SYNTHETIC_CONTROLS_V1',
    'fixture_count': 60,
    'seed': prior.SEED,
    'fixtures': rows,
    'private_input_openings': 0,
    'replacement_kernel_adopted': False,
  }
