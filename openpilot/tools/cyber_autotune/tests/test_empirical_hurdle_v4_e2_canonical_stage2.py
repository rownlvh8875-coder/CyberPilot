"""Public synthetic tests; independent frozen oracle remains unchanged."""

import ast
import copy
from fractions import Fraction
import hashlib
import importlib
import importlib.util
import inspect
import json
import subprocess
from pathlib import Path
import unittest
from unittest.mock import patch
import numpy as np
from openpilot.tools.cyber_autotune.tests import test_empirical_hurdle_v4_e2_deterministic_numerics_design as oracle

MODULE = 'openpilot.tools.cyber_autotune.empirical_hurdle_v4_e2_canonical_stage2'
ROOT = Path(__file__).resolve().parents[4]
BASELINE = 'd9d6b6f2747925fc386af4dbf44145861d8c6a01'


def implementation():
  if importlib.util.find_spec(MODULE) is None:
    raise AssertionError('STANDALONE_CANONICAL_MODULE_NOT_IMPLEMENTED')
  return importlib.import_module(MODULE)


def fixture():
  x, _, model = oracle.old.fixture(1, 1.0, 'medium')
  return x[:3].copy(), copy.deepcopy(model)


def batch_matrix():
  """Predeclared same60 configurations/12 pairs, ten conditions per fixture."""
  kernel = implementation().canonical_predict_delta
  results = []
  for length in oracle.old.LENGTHS:
    for scale in oracle.old.SCALES:
      for name in oracle.old.MASKS:
        x, gate, model = oracle.old.fixture(length, scale, name)
        expected, z = oracle.scalar_reference(x, model, return_transform=True)
        original = kernel(x, model)
        if not oracle.old.byte_equal(expected, original):
          raise AssertionError('CANONICAL_ORACLE_BYTE_MISMATCH')
        masks = [np.arange(len(x)) % 32 == 0, np.arange(len(x)) % 4 != 0, np.arange(len(x)) % 2 == 0, np.isin(np.arange(len(x)), [0, len(x) - 1])]
        variants = [
          np.concatenate([kernel(x[i : i + 1], model) for i in range(len(x))]),
          np.concatenate([kernel(x[i : i + 512], model) for i in range(0, len(x), 512)]),
          np.concatenate([kernel(x[a:b], model) for a, b in zip(oracle.PARTITIONS[:-1], oracle.PARTITIONS[1:], strict=True)]),
        ]
        checks = [oracle.old.byte_equal(expected, v) for v in variants]
        checks += [oracle.old.byte_equal(expected[m], kernel(np.ascontiguousarray(x[m]), model)) for m in masks]
        checks.append(oracle.old.byte_equal(expected[gate], kernel(np.ascontiguousarray(x[gate]), model)))
        changed = x.copy()
        changed[~gate, 1:] += 0.125
        checks += [oracle.old.byte_equal(expected[gate], kernel(changed, model)[gate]), oracle.old.byte_equal(expected, kernel(np.asfortranarray(x), model))]
        historical = oracle.old.frozen.predict_delta(x, model)
        results.append(
          {
            'L': length,
            'scale': scale,
            'mask': name,
            'checks': checks,
            'normalization_parity': oracle.old.byte_equal(z, oracle.old.frozen.transform(x, model['normalizer'])),
            'historical_comparison': oracle.old.compare(original, historical, np.zeros(len(x), np.int64)),
          }
        )
  return results


class TestCanonicalStage2(unittest.TestCase):
  def test_standalone_module_exists(self):
    self.assertIsNotNone(importlib.util.find_spec(MODULE), 'STANDALONE_CANONICAL_MODULE_NOT_IMPLEMENTED')

  def test_public_api_matches_independent_oracle(self):
    x, model = fixture()
    actual = implementation().canonical_predict_delta(x, model)
    self.assertEqual(actual.dtype, np.float64)
    self.assertEqual(actual.shape, (len(x),))
    self.assertTrue(oracle.old.byte_equal(actual, oracle.scalar_reference(x, model)))

  def test_new_normalized_intermediates_match_original_transform(self):
    # Observe actual new-kernel locals without changing operands or arithmetic.
    m = implementation()
    original_require = m._require
    for length in oracle.old.LENGTHS:
      x, _, model = oracle.old.fixture(length, 1.0, 'medium')
      x, model = x[:3].copy(), copy.deepcopy(model)
      norm = model['normalizer']
      norm['mean'][0], norm['std'][0] = 77.0, 0.0
      norm['constant'][-1], norm['std'][-1] = True, 0.0
      norm['effective'] = norm['effective'][:-1].copy()
      model['coefficients'] = model['coefficients'][:-1].copy()
      observed = []

      def observe(condition, code, observed=observed):
        original_require(condition, code)
        if code == 'CANONICAL_STAGE2_REDUCTION_NONFINITE':
          caller = inspect.currentframe().f_back
          self.assertEqual(caller.f_code.co_name, '_row_delta')
          observed.append(caller.f_locals['normalized'])

      with self.subTest(length=length), patch.object(m, '_require', new=observe):
        actual = m.canonical_predict_delta(x, model)
      expected = oracle.old.frozen.transform(x, norm)
      traced = np.array(observed, np.float64).reshape(expected.shape)
      reference, reference_z = oracle.scalar_reference(x, model, return_transform=True)
      self.assertTrue(oracle.old.byte_equal(traced, expected))
      self.assertTrue(oracle.old.byte_equal(traced, reference_z))
      self.assertTrue(oracle.old.byte_equal(actual, reference))

  def test_full_fixed_batch_matrix_600(self):
    rows = batch_matrix()
    self.assertEqual(len(rows), 60)
    self.assertEqual(len(rows) * len(rows[0]['checks']), 600)
    self.assertTrue(all(all(r['checks']) and r['normalization_parity'] for r in rows))

  def test_environment_is_qualified_without_mutation(self):
    q = implementation().qualify_environment()
    self.assertEqual(q['python'], '3.12.13')
    self.assertEqual(q['numpy'], '2.5.3')
    self.assertEqual(q['rounding'], 'NEAREST_TIES_EVEN')
    self.assertTrue(q['gradual_underflow'])
    self.assertEqual(q['status'], 'QUALIFIED_TESTED_ENVIRONMENT')

  def test_unsupported_environment_fails_closed(self):
    m = implementation()
    with patch.object(m.platform, 'machine', return_value='unqualified'), self.assertRaisesRegex(ValueError, 'ENVIRONMENT_NOT_QUALIFIED'):
      m.qualify_environment()
    with patch.object(m, '_rounding_mode', return_value=1), self.assertRaisesRegex(ValueError, 'ENVIRONMENT_NOT_QUALIFIED'):
      m.qualify_environment()

  def test_intercept_is_positive_one_unscaled(self):
    x, model = fixture()
    model['normalizer']['mean'][0] = 77.0
    model['normalizer']['std'][0] = 0.0
    self.assertTrue(oracle.old.byte_equal(implementation().canonical_predict_delta(x, model), oracle.scalar_reference(x, model)))

  def test_constant_exclusion_and_metadata_only_reference(self):
    x, model = fixture()
    n = model['normalizer']
    n['constant'][2] = True
    n['std'][2] = 0.0
    n['effective'] = np.array([0, 1, 3, 4], np.int64)
    model['coefficients'] = model['coefficients'][[0, 1, 3, 4]]
    a = implementation().canonical_predict_delta(x, model)
    x[:, 2] = 1e300
    n['constant_reference'][:] = 123.0
    self.assertTrue(oracle.old.byte_equal(a, implementation().canonical_predict_delta(x, model)))
    self.assertTrue(oracle.old.byte_equal(a, oracle.scalar_reference(x, model)))

  def test_invalid_effective_rejected(self):
    for values in ([0, 1, 1, 3, 4], [1, 0, 2, 3, 4], [0, 1, 2, 3, 5], [0, 1, 2, -1, 4], []):
      x, model = fixture()
      model['normalizer']['effective'] = np.array(values, np.int64)
      with self.subTest(values=values), self.assertRaises(ValueError):
        implementation().canonical_predict_delta(x, model)

  def test_invalid_array_domain_rejected(self):
    x, model = fixture()
    for bad in (x.astype(np.float32), x.astype('>f8'), x[:, :4], x[0], [[1.0] * 5], np.zeros((2, 5))):
      with self.subTest(shape=getattr(bad, 'shape', None)), self.assertRaises(ValueError):
        implementation().canonical_predict_delta(bad, model)

  def test_missing_and_malformed_model_rejected(self):
    for mutation in ('field', 'dtype', 'length', 'std', 'constant', 'reference', 'effective_dtype', 'model'):
      x, model = fixture()
      n = model['normalizer']
      if mutation == 'field':
        del n['mean']
      elif mutation == 'dtype':
        model['coefficients'] = model['coefficients'].astype(np.float32)
      elif mutation == 'length':
        model['coefficients'] = model['coefficients'][:-1]
      elif mutation == 'std':
        n['std'][1] = 0.0
      elif mutation == 'constant':
        n['constant'][1] = True
      elif mutation == 'reference':
        n['constant_reference'] = n['constant_reference'][:-1]
      elif mutation == 'effective_dtype':
        n['effective'] = n['effective'].astype(float)
      else:
        del model['coefficients']
      with self.subTest(mutation=mutation), self.assertRaises(ValueError):
        implementation().canonical_predict_delta(x, model)

  def test_constant_std_guard_is_independently_exercised(self):
    x, model = fixture()
    norm = model['normalizer']
    norm['constant'][2] = True
    norm['effective'] = np.array([0, 1, 3, 4], np.int64)
    model['coefficients'] = model['coefficients'][[0, 1, 3, 4]]
    self.assertNotEqual(norm['std'][2], 0.0)
    with self.assertRaisesRegex(ValueError, 'MODEL_INVALID'):
      implementation().canonical_predict_delta(x, model)
    with self.assertRaises(ValueError):
      oracle.scalar_reference(x, model)

  def test_zero_size_still_validates_model(self):
    x, model = fixture()
    a = implementation().canonical_predict_delta(x[:0], model)
    self.assertEqual((a.dtype, a.shape), (np.dtype('float64'), (0,)))
    del model['coefficients']
    with self.assertRaises(ValueError):
      implementation().canonical_predict_delta(x[:0], model)

  def test_nonfinite_input_model_and_every_intermediate(self):
    for mode in ('input', 'coefficient', 'mean', 'subtraction', 'division', 'multiplication', 'accumulation'):
      x, model = fixture()
      x = x[:1].copy()
      x[:] = 0.0
      x[:, 0] = 1.0
      n = model['normalizer']
      n['mean'][:] = 0.0
      n['std'][:] = 1.0
      model['coefficients'][:] = 0.0
      if mode == 'input':
        x[0, 1] = np.nan
      elif mode == 'coefficient':
        model['coefficients'][0] = np.inf
      elif mode == 'mean':
        n['mean'][1] = np.inf
      elif mode == 'subtraction':
        x[0, 1] = 1e308
        n['mean'][1] = -1e308
      elif mode == 'division':
        x[0, 1] = 1e308
        n['std'][1] = 1e-308
      elif mode == 'multiplication':
        x[0, 1] = 1e308
        model['coefficients'][1] = 1e308
      else:
        x[0, 1] = 1.0
        model['coefficients'][:2] = 1e308
      with self.subTest(mode=mode), self.assertRaises(ValueError):
        implementation().canonical_predict_delta(x, model)

  def test_signed_zero_and_subnormal(self):
    x, model = fixture()
    x = x[:1].copy()
    x[:] = 0.0
    x[:, 0] = 1.0
    model['normalizer']['mean'][:] = 0.0
    model['normalizer']['std'][:] = 1.0
    model['coefficients'][:] = -0.0
    self.assertEqual(implementation().canonical_predict_delta(x, model).view(np.uint64)[0], 0)
    model['coefficients'][:] = 0.0
    model['coefficients'][1] = 1.0
    x[0, 1] = float.fromhex('0x0.0000000000001p-1022')
    self.assertEqual(implementation().canonical_predict_delta(x, model).view(np.uint64)[0], 1)
    model['coefficients'][1] = 0.5
    self.assertEqual(implementation().canonical_predict_delta(x, model).view(np.uint64)[0], 0)

  def test_fused_and_reassociated_mutants_detectable(self):
    x, model = fixture()
    x = x[:1].copy()
    x[:] = 0.0
    x[:, 0] = 1.0
    model['normalizer']['mean'][:] = 0.0
    model['normalizer']['std'][:] = 1.0
    model['coefficients'][:] = 0.0
    a = 1.0 + 2.0**-27
    b = 1.0 - 2.0**-27
    x[0, 1] = a
    model['coefficients'][:2] = [-1.0, b]
    actual = implementation().canonical_predict_delta(x, model)[0]
    self.assertEqual(actual, 0.0)
    self.assertNotEqual(actual, float(Fraction.from_float(a) * Fraction.from_float(b) - 1))
    x[0, 1:3] = 1.0
    model['coefficients'][:3] = [1e16, -1e16, 1.0]
    self.assertEqual(implementation().canonical_predict_delta(x, model)[0], 1.0)
    self.assertNotEqual(1e16 + (-1e16 + 1.0), 1.0)

  def test_frozen_projection_and_boundary(self):
    for value in (0.5, np.nextafter(0.5, np.inf), 1.5, -1.5):
      x, model = fixture()
      x = x[:1]
      model['coefficients'][:] = 0.0
      model['coefficients'][0] = value
      a = implementation().canonical_predict_delta(x, model)
      self.assertTrue(oracle.old.byte_equal(a, oracle.scalar_reference(x, model)))
      self.assertEqual(oracle.old.frozen.project(a)[0], np.rint(value))
    with self.assertRaises(ValueError):
      oracle.old.frozen.project(np.array([32768.0]))

  def test_inputs_are_not_mutated(self):
    x, model = fixture()
    before = x.tobytes()
    n = {k: v.tobytes() for k, v in model['normalizer'].items()}
    beta = model['coefficients'].tobytes()
    implementation().canonical_predict_delta(x, model)
    self.assertEqual(before, x.tobytes())
    self.assertEqual(beta, model['coefficients'].tobytes())
    self.assertEqual(n, {k: v.tobytes() for k, v in model['normalizer'].items()})

  def test_independent_code_no_loading_or_wiring(self):
    source = inspect.getsource(implementation())
    tree = ast.parse(source)
    imports = [n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
    roots = {a.name.split('.')[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    roots.update(name.split('.')[0] for name in imports if name)
    self.assertLessEqual(roots, {'ctypes', 'functools', 'math', 'platform', 'struct', 'sys', 'numpy'})
    self.assertFalse(any(s and (s.startswith('openpilot') or 'tests' in s) for s in imports))
    for forbidden in ('matmul', 'dot', 'sum', 'fsum', 'load', 'loadtxt', 'open', 'urlopen', 'connect', 'fesetround'):
      self.assertFalse(
        any(
          isinstance(n, ast.Call)
          and ((isinstance(n.func, ast.Name) and n.func.id == forbidden) or (isinstance(n.func, ast.Attribute) and n.func.attr == forbidden))
          for n in ast.walk(tree)
        ),
        forbidden,
      )
    self.assertEqual(implementation().STATUS, 'EXPERIMENTAL_NON_WIRED')


class TestOfflineContract(unittest.TestCase):
  def test_workflow_exists_and_is_lfs_independent(self):
    p = ROOT / '.github/workflows/cyberpilot-numerical-offline.yaml'
    self.assertTrue(p.is_file())
    import yaml

    source = p.read_text()
    data = yaml.safe_load(source)
    self.assertEqual(data['name'], 'CyberPilot Offline Static Numerical CI')
    self.assertEqual(data['permissions'], {'contents': 'read'})
    steps = data['jobs']['numerical']['steps']
    checkout = next(s for s in steps if 'uses' in s and s['uses'].startswith('actions/checkout@'))
    self.assertIs(checkout['with']['lfs'], False)
    self.assertIs(checkout['with']['submodules'], False)
    self.assertIs(checkout['with']['persist-credentials'], False)
    self.assertEqual(checkout['with']['fetch-depth'], 0)
    for text in ('git lfs pull', 'tools/op.sh setup', 'openpilot[submodules]', 'secrets.', 'huggingface.co', 'continue-on-error: true'):
      self.assertNotIn(text, source)
    self.assertIn('OFFLINE_STATIC_NUMERICAL_CI', source)

  def test_implementation_lock_and_historical_immutability(self):
    path = ROOT / 'docs/cyberpilot/changes/empirical-hurdle-stage1-v4-e2-canonical-implementation-lock.json'
    self.assertTrue(path.is_file())
    lock = json.loads(path.read_text())
    receipt = lock.pop('receipt_sha256')
    self.assertEqual(receipt, hashlib.sha256(json.dumps(lock, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest())
    # Preserve this immutable historical receipt. Current authorized CI-extension
    # bytes are independently bound by the new canonical bridge lock/test.
    extension_paths = {
      '.github/workflows/cyberpilot-numerical-offline.yaml',
      'tools/cyberpilot/run_numerical_offline.py',
      'openpilot/tools/cyber_autotune/tests/test_empirical_hurdle_v4_e2_canonical_stage2.py',
    }
    for name, sha in lock['source_sha256'].items():
      raw = (
        subprocess.check_output(['git', 'show', '99cd6aa62d00bfb2a27b8d5fcf08cf06cdb129cb:' + name], cwd=ROOT)
        if name in extension_paths
        else (ROOT / name).read_bytes()
      )
      self.assertEqual(hashlib.sha256(raw).hexdigest(), sha)
    for name, sha in lock['historical_sha256'].items():
      self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), sha)
    self.assertFalse(lock['authority']['private_access'])
    self.assertFalse(lock['authority']['E2_integration'])
    self.assertEqual(lock['safety']['vehicle_authority'], 'NONE')

  def test_offline_audit_boundary_rejects_sources_writes_and_network(self):
    from tools.cyberpilot import run_numerical_offline as runner

    runner.public_boundary('open', (str(ROOT / 'AGENTS.md'), 'r', 0))
    for event, args in [
      ('open', ('/unapproved-source-sentinel', 'r', 0)),
      ('open', (str(ROOT / 'forbidden.npy'), 'r', 0)),
      ('open', (str(ROOT / 'AGENTS.md'), 'w', 577)),
      ('socket.connect', ()),
      ('subprocess.Popen', ('curl', ['curl', 'example.invalid'], None, None)),
      ('os.remove', ('sentinel',)),
    ]:
      with self.subTest(event=event), self.assertRaises(PermissionError):
        runner.public_boundary(event, args)

  def test_offline_forbidden_imports(self):
    from tools.cyberpilot import run_numerical_offline as runner

    for name in ('openpilot.selfdrive.controls', 'huggingface_hub', 'openpilot.tools.cyber_autotune.empirical_hurdle_v4_e2_numerical_diagnostic_private'):
      with self.subTest(name=name), self.assertRaises(ImportError):
        runner.PublicImports().find_spec(name)

  def test_numpy_private_helpers_are_public_package_imports(self):
    from tools.cyberpilot import run_numerical_offline as runner

    self.assertIsNone(runner.PublicImports().find_spec('numpy.testing._private'))

  def test_only_readonly_fifo_descriptor_is_admitted(self):
    import os
    from tools.cyberpilot import run_numerical_offline as runner

    read_fd, write_fd = os.pipe()
    try:
      runner.public_boundary('open', (read_fd, 'rb', 0))
      with self.assertRaises(PermissionError):
        runner.public_boundary('open', (write_fd, 'wb', os.O_WRONLY))
    finally:
      os.close(read_fd)
      os.close(write_fd)
    with (ROOT / 'AGENTS.md').open('rb') as stream:
      with self.assertRaises(PermissionError):
        runner.public_boundary('open', (stream.fileno(), 'rb', 0))


class TestFrozenPublicFixtures(unittest.TestCase):
  def test_original_parity_aligned_60_are_executed_without_repair(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_v2_q1_diagnostic as public_q1

    original = oracle.old.synthetic()
    parity = oracle.old.parity_control()
    aligned = public_q1.synthetic_controls()
    for result in (original, parity, aligned):
      self.assertEqual(len(result['fixtures']), 60)
      self.assertEqual(result['private_input_openings'], 0)
    self.assertFalse(aligned['replacement_kernel_adopted'])
    self.assertFalse(original['tolerance_applied'])
