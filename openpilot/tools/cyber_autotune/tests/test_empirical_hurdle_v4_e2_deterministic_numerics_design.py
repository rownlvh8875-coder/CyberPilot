"""DESIGN ONLY: scalar oracle on declared public synthetic fixtures.

No scientific runtime imports this test-local reference; no file/model input API.
No BLAS, reduction primitive, fsum, native replacement, private reader or selector.
"""

import ctypes
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import struct
import subprocess
import sys
import time
import unittest
import numpy as np
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_numerical_diagnostic as old

BASELINE = '602855e53fe1f66bbb8c4a99e6d8841b4a6c2afc'
ROOT = Path(__file__).resolve().parents[4]
PUBLIC = ROOT / 'docs/cyberpilot/changes'
NUMERICAL_CONTRACT = 'empirical-hurdle-stage1-v4-e2-deterministic-numerics-contract.json'
LFS_CONTRACT = 'cyberpilot-ci-lfs-triage.json'
DIMENSIONS = (5, 13, 33, 93)
PARTITIONS = (0, 1, 511, 512, 513, 1025, 1536, 1537)
BENCHMARK_ROWS = (8192, 336941)


def qualified_host():
  f = sys.float_info
  if not (sys.implementation.name == 'cpython' and f.radix == 2 and f.mant_dig == 53 and f.max_exp == 1024 and struct.calcsize('d') == 8):
    raise ValueError('SYNTHETIC_HOST_NOT_QUALIFIED')
  if ctypes.CDLL('libm.so.6').fegetround() != 0:
    raise ValueError('ROUND_TO_NEAREST_REQUIRED')
  minimum = float.fromhex('0x0.0000000000001p-1022')
  if minimum * 1.0 != minimum or minimum / 2.0 != 0.0 or float.fromhex('0x1p-1022') * 0.5 == 0.0:
    raise ValueError('GRADUAL_UNDERFLOW_REQUIRED')


def scalar_reference(x, model, *, return_transform=False):
  """Test-only proposed semantics, with every operation a separate PyFloat op."""
  qualified_host()
  norm, beta = model['normalizer'], model['coefficients']
  idx = norm['effective']
  if x.dtype != np.float64 or x.ndim != 2 or x.shape[1] not in DIMENSIONS or not np.all(np.isfinite(x)) or not np.all(x[:, 0] == 1):
    raise ValueError('SYNTHETIC_INPUT_CONFLICT')
  if set(norm) != {'mean', 'std', 'constant', 'effective', 'constant_reference'}:
    raise ValueError('SYNTHETIC_NORMALIZER_CONFLICT')
  p = x.shape[1]
  if any(norm[n].dtype != np.float64 or norm[n].shape != (p,) or not np.all(np.isfinite(norm[n])) for n in ('mean', 'std', 'constant_reference')):
    raise ValueError('SYNTHETIC_NORMALIZER_CONFLICT')
  if norm['constant'].dtype != np.bool_ or norm['constant'].shape != (p,) or norm['constant'][0]:
    raise ValueError('SYNTHETIC_NORMALIZER_CONFLICT')
  if idx.dtype != np.int64 or not np.array_equal(idx, np.flatnonzero(~norm['constant'])) or len(idx) == 0 or idx[0] != 0:
    raise ValueError('SYNTHETIC_EFFECTIVE_ORDER_CONFLICT')
  if (
    beta.dtype != np.float64
    or beta.shape != (len(idx),)
    or not np.all(np.isfinite(beta))
    or not np.all(norm['std'][idx[1:]] > 0)
    or not np.all(norm['std'][norm['constant']] == 0)
  ):
    raise ValueError('SYNTHETIC_COEFFICIENT_OR_STD_CONFLICT')
  columns = [int(j) for j in idx]
  means, stds, coefficients = ([float(v) for v in values] for values in (norm['mean'], norm['std'], beta))
  out = np.empty(len(x), np.float64)
  transformed = np.empty((len(x), len(idx)), np.float64) if return_transform else None
  for i, row in enumerate(x):
    acc = 0.0
    for k, column in enumerate(columns):
      if k == 0:
        z = 1.0  # Source transform never normalizes the intercept.
      else:
        difference = float(row[column]) - means[column]
        z = difference / stds[column]
        if not math.isfinite(difference) or not math.isfinite(z):
          raise ValueError('SYNTHETIC_NORMALIZATION_NONFINITE')
      product = z * coefficients[k]
      acc = acc + product
      if not math.isfinite(product) or not math.isfinite(acc):
        raise ValueError('SYNTHETIC_PRODUCT_OR_SUM_NONFINITE')
      if transformed is not None:
        transformed[i, k] = z
    out[i] = acc
  return (out, transformed) if return_transform else out


def fixed_sum(values):
  """Original row order, positive-zero padding, fixed complete binary tree."""
  n = 1 << max(0, (len(values) - 1).bit_length())
  tree = [0.0] * (2 * n)
  for i, value in enumerate(values):
    tree[n + i] = float(value)
  for node in range(n - 1, 0, -1):
    tree[node] = tree[2 * node] + tree[2 * node + 1]
  if not math.isfinite(tree[1]):
    raise ValueError('SYNTHETIC_LOSS_NONFINITE')
  return tree[1]


def losses(delta, target):
  error = delta - target.astype(np.float64)
  return {'SSE': fixed_sum(error * error), 'SAE': fixed_sum(np.abs(error))}


def public_experiment():
  """Exactly sixty existing seed/scale/mask fixtures; no search/adaptation."""
  rows = []
  for length in old.LENGTHS:
    for scale in old.SCALES:
      for mask_name in old.MASKS:
        x, gate, model = old.fixture(length, scale, mask_name)
        canonical, z = scalar_reference(x, model, return_transform=True)
        if not old.byte_equal(z, old.frozen.transform(x, model['normalizer'])):
          raise ValueError('SYNTHETIC_NORMALIZATION_PARITY_NOT_PROVEN')
        chunks = np.concatenate([scalar_reference(x[i : i + 512], model) for i in range(0, len(x), 512)])
        segments = np.concatenate([scalar_reference(x[a:b], model) for a, b in zip(PARTITIONS[:-1], PARTITIONS[1:], strict=True)])
        single = np.concatenate([scalar_reference(x[i : i + 1], model) for i in range(len(x))])
        masks = {
          'fixture': gate,
          'sparse': np.arange(len(x)) % 32 == 0,
          'dense': np.arange(len(x)) % 4 != 0,
          'alternating': np.arange(len(x)) % 2 == 0,
          'first_last': np.isin(np.arange(len(x)), [0, len(x) - 1]),
        }
        checks = {
          'fixed512': old.byte_equal(canonical, chunks),
          'partitions': old.byte_equal(canonical, segments),
          'single_rows': old.byte_equal(canonical, single),
          'Fortran_layout': old.byte_equal(canonical, scalar_reference(np.asfortranarray(x), model)),
        }
        for name, mask in masks.items():
          checks[name] = old.byte_equal(canonical[mask], scalar_reference(np.ascontiguousarray(x[mask]), model))
        unrelated = x.copy()
        unrelated[~gate, 1:] += 0.125
        checks['unrelated_adjacent_rows'] = old.byte_equal(canonical[gate], scalar_reference(unrelated, model)[gate])
        if not all(checks.values()):
          raise ValueError('SYNTHETIC_BATCH_INVARIANCE_FAILED')
        historical = old.frozen.predict_delta(x, model)
        target = ((np.arange(len(x)) % 5) - 2).astype(np.int64)
        rows.append(
          {
            'L': length,
            'dimension': x.shape[1],
            'scale': scale,
            'mask': mask_name,
            'batch_checks': checks,
            'transform_byte_equal': True,
            'canonical_vs_historical': old.compare(canonical, historical, np.zeros(len(x), np.int64)),
            'continuous_loss': {'canonical': losses(canonical, target), 'historical': losses(historical, target)},
          }
        )
  return rows


def synthetic_benchmark(n):
  if n not in BENCHMARK_ROWS:
    raise ValueError('UNDECLARED_SYNTHETIC_BENCHMARK')
  rng = np.random.default_rng(20261019)
  x = rng.uniform(-1, 1, (n, 93)).astype(np.float64)
  x[:, 0] = 1.0
  _, _, model = old.fixture(45, 1.0, 'medium')
  started = time.perf_counter()
  out = scalar_reference(x, model)
  elapsed = time.perf_counter() - started
  return {
    'N': n,
    'P': 93,
    'wall_seconds': elapsed,
    'input_bytes': x.nbytes,
    'output_bytes': out.nbytes,
    'output_sha256': hashlib.sha256(out.tobytes()).hexdigest(),
    'cells': n * 93,
  }


class TestCanonicalDesign(unittest.TestCase):
  def fixture(self):
    return old.fixture(1, 1.0, 'medium')

  def test_proposed_contract_required(self):
    self.assertTrue((PUBLIC / NUMERICAL_CONTRACT).is_file())

  def test_intercept_not_normalized_even_with_zero_std(self):
    x, _, model = self.fixture()
    model['normalizer']['mean'][0] = 1.0
    model['normalizer']['std'][0] = 0.0
    value, z = scalar_reference(x[:2], model, return_transform=True)
    self.assertTrue(np.all(z[:, 0] == 1.0))
    self.assertTrue(np.all(np.isfinite(value)))

  def test_constant_column_ignored_in_original_effective_order(self):
    x, _, model = self.fixture()
    model['normalizer']['constant'][2] = True
    model['normalizer']['std'][2] = 0.0
    model['normalizer']['effective'] = np.array([0, 1, 3, 4], dtype=np.int64)
    model['coefficients'] = model['coefficients'][[0, 1, 3, 4]]
    a = scalar_reference(x[:2], model)
    x[:2, 2] = 1e300
    self.assertTrue(old.byte_equal(a, scalar_reference(x[:2], model)))

  def test_signed_zero_starts_positive_zero(self):
    x, _, model = self.fixture()
    model['coefficients'][:] = -0.0
    x[:] = 1.0
    model['normalizer']['mean'][:] = 0.0
    self.assertEqual(scalar_reference(x[:1], model).view(np.uint64)[0], 0)

  def test_separate_product_and_accumulator_not_fused(self):
    x, _, model = self.fixture()
    x = x[:1].copy()
    x[:] = 0.0
    x[:, 0] = 1.0
    model['normalizer']['mean'][:] = 0.0
    model['normalizer']['std'][:] = 1.0
    model['coefficients'][:] = 0.0
    a = 1.0 + 2.0**-27
    b = 1.0 - 2.0**-27
    model['coefficients'][0] = -1.0
    model['coefficients'][1] = b
    x[0, 1] = a
    value = scalar_reference(x, model)[0]
    self.assertEqual(value, 0.0)
    exact_fused = Fraction.from_float(a) * Fraction.from_float(b) - 1
    self.assertNotEqual(value, float(exact_fused))

  def test_empty_and_all_row_batch(self):
    x, _, model = self.fixture()
    self.assertEqual(scalar_reference(x[:0], model).shape, (0,))
    self.assertTrue(old.byte_equal(scalar_reference(x, model), scalar_reference(x.copy(), model)))

  def test_half_tick_one_ulp_can_change_projection(self):
    a = np.array([0.5])
    b = np.nextafter(a, np.inf)
    comparison = old.compare(a, b, np.zeros(1, np.int64))
    self.assertFalse(comparison['raw_byte_equal'])
    self.assertEqual(comparison['projected_tick_mismatch_count'], 1)

  def test_projection_ties_even_and_signed16_failure(self):
    np.testing.assert_array_equal(old.frozen.project(np.array([0.5, 1.5, -1.5])), [0, 2, -2])
    with self.assertRaises(ValueError):
      old.frozen.project(np.array([32768.0]))

  def test_invalid_dtype_and_nonfinite_rejected(self):
    x, _, model = self.fixture()
    for value in (x[:2].astype(np.float32), np.full_like(x[:2], np.nan)):
      with self.assertRaises(ValueError):
        scalar_reference(value, model)
    model['coefficients'][0] = np.inf
    with self.assertRaises(ValueError):
      scalar_reference(x[:2], model)

  def test_overflow_rejected_without_clipping(self):
    x, _, model = self.fixture()
    x = x[:1].copy()
    x[0, 1] = 1e308
    model['coefficients'][1] = 1e308
    with self.assertRaises(ValueError):
      scalar_reference(x, model)

  def test_loss_tree_and_signed_zero_byte_semantics(self):
    self.assertEqual(fixed_sum([1.0, 2.0, 3.0]), 6.0)
    self.assertFalse(old.byte_equal(np.array([0.0]), np.array([-0.0])))
    self.assertEqual(losses(np.array([1.0, 2.0]), np.array([1, 0], np.int64)), {'SSE': 4.0, 'SAE': 2.0})

  def test_no_unfrozen_benchmark_search(self):
    with self.assertRaises(ValueError):
      synthetic_benchmark(2)

  def test_invalid_constant_std_rejected(self):
    x, _, model = self.fixture()
    model['normalizer']['constant'][2] = True
    model['normalizer']['effective'] = np.array([0, 1, 3, 4], dtype=np.int64)
    model['coefficients'] = model['coefficients'][[0, 1, 3, 4]]
    with self.assertRaises(ValueError):
      scalar_reference(x[:2], model)

  def test_contract_identity_and_closed_authority(self):
    for filename in (NUMERICAL_CONTRACT, LFS_CONTRACT):
      payload = json.loads((PUBLIC / filename).read_text())
      receipt = payload.pop('receipt_sha256')
      self.assertEqual(receipt, hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest())
    contract = json.loads((PUBLIC / NUMERICAL_CONTRACT).read_text())
    for key in ('implementation_authorized', 'private_access_authorized', 'E2_execution_authorized'):
      self.assertIs(contract[key], False)
    self.assertEqual(contract['acceptance']['clauses'], 32)
    self.assertEqual(contract['acceptance']['horizons'], [25, 50, 100, 200])
    self.assertTrue(contract['acceptance']['both_folds'])
    self.assertEqual(contract['future_validation_domains']['count'], 22)
    self.assertEqual(contract['future_execution']['policies'], ['D0', 'D1', 'D2'])
    self.assertIn('DO_NOT_DELETE', contract['batch_invariant']['Q1_Q3'])
    self.assertTrue(all(v == 0 for v in contract['forbidden_operation_counters'].values()))
    self.assertEqual(contract['safety']['HOLDOUT'], 'CLOSED')
    self.assertEqual(contract['safety']['vehicle_authority'], 'NONE')

  def test_original_source_and_public_receipt_pins(self):
    contract = json.loads((PUBLIC / NUMERICAL_CONTRACT).read_text())
    for filename, expected in contract['source_sha256'].items():
      self.assertEqual(hashlib.sha256((ROOT / 'openpilot/tools/cyber_autotune' / filename).read_bytes()).hexdigest(), expected)
    for filename, identity in contract['public_identity'].items():
      raw = (PUBLIC / filename).read_bytes()
      self.assertEqual(hashlib.sha256(raw).hexdigest(), identity['raw_sha256'])
      self.assertEqual(json.loads(raw)['receipt_sha256'], identity['receipt_sha256'])

  def test_public_lfs_pointer_inventory_exact_baseline(self):
    inventory = json.loads((PUBLIC / LFS_CONTRACT).read_text())
    self.assertEqual(inventory['frozen_git_reference'], BASELINE)
    self.assertEqual(len(inventory['inventory']), 252)
    missing = [r for r in inventory['inventory'] if r['reported_404_in_baseline_attempt2']]
    self.assertEqual(len(missing), 15)
    self.assertEqual(sum(r['size'] for r in missing), 95348970)
    for row in inventory['inventory']:
      # git object is public pointer metadata, never a working-tree model payload.
      raw = subprocess.check_output(['git', 'show', BASELINE + ':' + row['path']], cwd=ROOT)
      expected = f"version https://git-lfs.github.com/spec/v1\noid sha256:{row['oid']}\nsize {row['size']}\n".encode()
      self.assertEqual(raw, expected)
      self.assertEqual(hashlib.sha256(raw).hexdigest(), row['pointer_raw_sha256'])
    self.assertFalse(any(r['existing_workflow_exclusion_applies'] for r in missing))

  def test_lfs_unknown_not_optional_and_required_not_skipped(self):
    inventory = json.loads((PUBLIC / LFS_CONTRACT).read_text())
    monitor = next(r for r in inventory['inventory'] if r['path'].endswith('/dmonitoring_model.onnx'))
    self.assertEqual(monitor['classification'], 'REQUIRED_FOR_VALIDATION')
    self.assertEqual(inventory['classification_status'], 'CI_LFS_DEPENDENCY_CLASSIFICATION_INCOMPLETE')
    self.assertFalse(inventory['remedies']['B']['exact_minimum_list_complete'])
    self.assertFalse(inventory['remedies']['B']['implementation_authorized'])
    self.assertEqual(inventory['baseline_ci']['build_lint_tests'], 'NOT_EXECUTED')
    for path, expected in inventory['source_sha256'].items():
      self.assertEqual(hashlib.sha256((ROOT / path).read_bytes()).hexdigest(), expected)

  def test_fixed_public_batch_matrix(self):
    rows = public_experiment()
    self.assertEqual(len(rows), 60)
    self.assertTrue(all(r['transform_byte_equal'] and all(r['batch_checks'].values()) for r in rows))

  def test_subnormal_and_normalizer_domain(self):
    x, _, model = self.fixture()
    x = x[:1].copy()
    x[:] = 0.0
    x[0, 0] = 1.0
    model['normalizer']['mean'][:] = 0.0
    model['normalizer']['std'][:] = 1.0
    model['coefficients'][:] = 0.0
    model['coefficients'][1] = 1.0
    minimum = float.fromhex('0x0.0000000000001p-1022')
    x[0, 1] = minimum
    self.assertEqual(scalar_reference(x, model)[0], minimum)
    model['normalizer']['std'][1] = 0.0
    with self.assertRaises(ValueError):
      scalar_reference(x, model)

  def test_underflow_product_retains_ieee_zero(self):
    x, _, model = self.fixture()
    x = x[:1].copy()
    x[:] = 0.0
    x[0, 0] = 1.0
    model['normalizer']['mean'][:] = 0.0
    model['normalizer']['std'][:] = 1.0
    model['coefficients'][:] = 0.0
    model['coefficients'][1] = 0.5
    x[0, 1] = float.fromhex('0x0.0000000000001p-1022')
    self.assertEqual(scalar_reference(x, model).view(np.uint64)[0], 0)

  def test_each_overflow_stage_rejects(self):
    for stage in ('subtraction', 'division', 'accumulation'):
      x, _, model = self.fixture()
      x = x[:1].copy()
      x[:] = 0.0
      x[0, 0] = 1.0
      model['normalizer']['mean'][:] = 0.0
      model['normalizer']['std'][:] = 1.0
      model['coefficients'][:] = 0.0
      if stage == 'subtraction':
        x[0, 1] = 1e308
        model['normalizer']['mean'][1] = -1e308
      elif stage == 'division':
        x[0, 1] = 1e308
        model['normalizer']['std'][1] = 1e-308
      else:
        x[0, 1] = 1.0
        model['coefficients'][:2] = 1e308
      with self.subTest(stage=stage), self.assertRaises(ValueError):
        scalar_reference(x, model)
