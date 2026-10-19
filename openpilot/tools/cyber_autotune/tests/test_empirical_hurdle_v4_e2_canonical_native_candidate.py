"""Public native tests. Real compiled ABI, frozen Python plus independent oracle."""

import copy
import ctypes
import hashlib
import json
import subprocess
import sys
import tempfile
import importlib
import importlib.util
import os
from pathlib import Path
import unittest
import numpy as np
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_stage2 as python
from openpilot.tools.cyber_autotune.tests import test_empirical_hurdle_v4_e2_deterministic_numerics_design as oracle
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_runtime_model as model

MODULE = 'openpilot.tools.cyber_autotune.empirical_hurdle_v4_e2_canonical_native_candidate'


def candidate():
  if importlib.util.find_spec(MODULE) is None:
    raise AssertionError('NATIVE_CANDIDATE_NOT_IMPLEMENTED')
  q = importlib.import_module(MODULE)
  name = os.environ.get('CYBERPILOT_PUBLIC_NATIVE_RECEIPT')
  digest = os.environ.get('CYBERPILOT_PUBLIC_NATIVE_RECEIPT_SHA256')
  if not name or not digest:
    raise AssertionError('EXPLICIT_NATIVE_BUILD_RECEIPT_REQUIRED_NO_SKIP')
  return q.NativeCandidate(Path(name), digest)


def exact(test, a, b):
  test.assertEqual(a.dtype, b.dtype)
  test.assertEqual(a.shape, b.shape)
  test.assertEqual(a.tobytes(), b.tobytes(), 'CANONICAL_NATIVE_BYTE_PARITY_FAILED')


class TestNativeCandidate(unittest.TestCase):
  def test_explicit_receipt_and_no_automatic_build(self):
    q = candidate()
    self.assertEqual(q.STATUS, 'EXPERIMENTAL_NATIVE_CANDIDATE_NON_WIRED')
    self.assertEqual(q.noop(), 0)
    self.assertEqual(q.library.cp_environment(), 0)

  def test_600_fixed_batch_checks(self):
    q = candidate()
    checks = 0
    for length in oracle.old.LENGTHS:
      for scale in oracle.old.SCALES:
        for name in oracle.old.MASKS:
          x, gate, m = oracle.old.fixture(length, scale, name)
          reference = python.canonical_predict_delta(x, m)
          exact(self, reference, oracle.scalar_reference(x, m))
          masks = [np.arange(len(x)) % 32 == 0, np.arange(len(x)) % 4 != 0, np.arange(len(x)) % 2 == 0, np.isin(np.arange(len(x)), [0, len(x) - 1]), gate]
          variants = [
            q.predict(x, m),
            np.concatenate([q.predict(x[i : i + 1], m) for i in range(len(x))]),
            np.concatenate([q.predict(x[i : i + 512], m) for i in range(0, len(x), 512)]),
            np.concatenate([q.predict(x[a:b], m) for a, b in zip(oracle.PARTITIONS[:-1], oracle.PARTITIONS[1:], strict=True)]),
          ]
          for output in variants:
            exact(self, output, reference)
            checks += 1
          for mask in masks:
            exact(self, q.predict(np.ascontiguousarray(x[mask]), m), reference[mask])
            checks += 1
          changed = x.copy()
          changed[~gate, 1:] += 0.125
          exact(self, q.predict(np.asfortranarray(changed), m)[gate], reference[gate])
          checks += 1
    self.assertEqual(checks, 600)

  def test_normalized_intermediates_constant_and_intercept(self):
    q = candidate()
    for p in (5, 13, 33, 93):
      x, m = model.fixture(8, p)
      n = m['normalizer']
      n['mean'][0], n['std'][0] = 77.0, 0.0
      n['constant'][2], n['std'][2] = True, 0.0
      n['effective'] = np.delete(n['effective'], 2)
      m['coefficients'] = np.delete(m['coefficients'], 2)
      output, z = q.predict(x, m, trace=True)
      expected, expected_z = oracle.scalar_reference(x, m, return_transform=True)
      exact(self, output, expected)
      exact(self, z, expected_z)
      exact(self, z, oracle.old.frozen.transform(x, n))
      n['constant_reference'][:] = 123.0
      exact(self, q.predict(x, m), expected)

  def test_zero_and_all_selected_Q1_Q3(self):
    q = candidate()
    x, m = model.fixture(1537, 93)
    cache = np.concatenate([q.predict(x[i : i + 512], m) for i in range(0, len(x), 512)])
    for mask in (np.zeros(len(x), bool), np.ones(len(x), bool), np.arange(len(x)) % 7 == 0, np.arange(len(x)) % 3 != 0):
      selected = q.predict(x[mask], m)
      exact(self, selected, cache[mask])
      exact(self, selected, python.canonical_predict_delta(x[mask], m))
    exact(self, q.predict(x[:0], m), np.empty(0, np.float64))

  def test_unaligned_fortran_and_input_immutable(self):
    q = candidate()
    x, m = model.fixture(8, 13)
    a = np.ndarray(x.shape, np.float64, buffer=bytearray(x.nbytes + 1), offset=1)
    a[:] = x
    before = a.tobytes(), copy.deepcopy(m)
    for v in (a, np.asfortranarray(x), x[::2]):
      exact(self, q.predict(v, m), python.canonical_predict_delta(v, m))
    self.assertEqual(a.tobytes(), before[0])
    exact(self, m['coefficients'], before[1]['coefficients'])

  def test_signed_zero_subnormal_underflow_and_fma_witness(self):
    q = candidate()
    x, m = model.fixture(3, 5)
    n = m['normalizer']
    n['mean'][:] = 0
    n['std'][:] = 1
    m['coefficients'][:] = 0
    m['coefficients'][1] = 1
    x[:, 1] = [-0.0, float.fromhex('0x0.0000000000001p-1022'), float.fromhex('0x1p-1022')]
    actual, z = q.predict(x, m, trace=True)
    self.assertEqual(z[0, 1].tobytes(), np.float64(-0.0).tobytes())
    exact(self, actual, python.canonical_predict_delta(x, m))
    self.assertEqual(actual[1].view(np.uint64), 1)
    m['coefficients'][1] = 0.5
    exact(self, q.predict(x, m), python.canonical_predict_delta(x, m))
    x, m = model.fixture(1, 5)
    n = m['normalizer']
    n['mean'][:] = 0
    n['std'][:] = 1
    x[0, 1] = 1 + 2**-27
    m['coefficients'][:] = 0
    m['coefficients'][:2] = [-1.0, 1 - 2**-27]
    out = q.predict(x, m)
    self.assertEqual(out.tobytes(), np.array([0.0]).tobytes())
    exact(self, out, python.canonical_predict_delta(x, m))

  def test_half_tick_and_signed16_projection(self):
    q = candidate()
    x, m = model.fixture(1, 5)
    for value, tick in ((0.5, 0), (1.5, 2), (-0.5, 0), (-1.5, -2)):
      m['coefficients'][:] = 0
      m['coefficients'][0] = value
      actual = q.predict(x, m)
      exact(self, actual, python.canonical_predict_delta(x, m))
      self.assertEqual(int(oracle.old.frozen.project(actual)[0]), tick)
    m['coefficients'][0] = 32768
    with self.assertRaises(ValueError):
      oracle.old.frozen.project(q.predict(x, m))

  def test_invalid_dtype_shape_model_rejected(self):
    q = candidate()
    x, m = model.fixture(8, 5)
    for bad in (x.astype(np.float32), x.astype('>f8'), x[0], x[:, :4], np.zeros_like(x), [[1.0] * 5]):
      with self.subTest(case=type(bad)), self.assertRaises(ValueError):
        q.predict(bad, m)
    for key in ('mean', 'std', 'constant', 'effective', 'constant_reference'):
      bad = copy.deepcopy(m)
      del bad['normalizer'][key]
      with self.subTest(key=key), self.assertRaises(ValueError):
        q.predict(x, bad)
    for idx in ([0, 1, 1, 3, 4], [1, 0, 2, 3, 4], [0, 1, 2, 3, 5]):
      bad = copy.deepcopy(m)
      bad['normalizer']['effective'] = np.array(idx, np.int64)
      with self.assertRaises(ValueError):
        q.predict(x, bad)
    bad = copy.deepcopy(m)
    bad['coefficients'] = bad['coefficients'][:-1]
    with self.assertRaises(ValueError):
      q.predict(x, bad)

  def test_nonfinite_input_model_and_intermediates_fail(self):
    q = candidate()
    for where in ('input', 'coefficient', 'subtraction', 'division', 'multiply', 'accumulation'):
      x, m = model.fixture(1, 5)
      n = m['normalizer']
      n['mean'][:] = 0
      n['std'][:] = 1
      m['coefficients'][:] = 0
      if where == 'input':
        x[0, 2] = np.nan
      if where == 'coefficient':
        m['coefficients'][1] = np.inf
      if where == 'subtraction':
        x[0, 1], n['mean'][1] = np.finfo(float).max, -np.finfo(float).max
      if where == 'division':
        x[0, 1], n['std'][1] = 1.0, np.nextafter(0.0, 1.0)
      if where == 'multiply':
        x[0, 1], m['coefficients'][1] = np.finfo(float).max, 2.0
      if where == 'accumulation':
        x[0, 1], m['coefficients'][:2] = 1.0, np.finfo(float).max
      with self.subTest(where=where), self.assertRaises(ValueError):
        q.predict(x, m)
      with self.subTest(reference=where), self.assertRaises(ValueError):
        python.canonical_predict_delta(x, m)

  def test_receipt_tamper_or_no_grant_does_not_load(self):
    q = candidate()
    cls = type(q)
    with self.assertRaises(ValueError):
      cls(q.receipt_path, '0' * 64)
    with self.assertRaises(ValueError):
      cls(Path('relative.json'), '0' * 64)
    self.assertFalse(q.receipt['private_execution_authorized'])
    self.assertFalse(q.receipt['runtime_integration_authorized'])

  def test_null_short_output_and_extent_abi_errors(self):
    q = candidate()
    x, m = model.fixture(1, 5)
    args = q.arguments(x, m, trace=False)
    args[0] = ctypes.POINTER(ctypes.c_double)()
    self.assertNotEqual(q.library.cp_stage2(*args), 0)
    args = q.arguments(x, m, trace=False)
    args[8] = 0
    self.assertNotEqual(q.library.cp_stage2(*args), 0)
    args = q.arguments(x, m, trace=False)
    args[1] = 2**63
    self.assertNotEqual(q.library.cp_stage2(*args), 0)

  def test_repeated_output_identity(self):
    q = candidate()
    x, m = model.fixture(512, 33)
    reference = python.canonical_predict_delta(x, m)
    for _ in range(3):
      exact(self, q.predict(x, m), reference)

  def test_Original_Parity_Aligned_180_fixed_controls(self):
    q = candidate()
    controls = 0
    for length in oracle.old.LENGTHS:
      for scale in oracle.old.SCALES:
        for name in oracle.old.MASKS:
          x, gate, m = oracle.old.fixture(length, scale, name)
          odd = gate.copy()
          for start in range(0, len(x) - 512 + 1, 512):
            odd[start] = ~odd[start]
          for mask, aligned in ((gate, False), (odd, False), (odd, True)):
            selected = np.ascontiguousarray(x[mask])
            if aligned:
              selected = oracle.old.aligned_copy(selected)
            exact(self, q.predict(selected, m), python.canonical_predict_delta(selected, m))
            controls += 1
    self.assertEqual(controls, 180)

  def test_all32_native_Q1_Q3_and_frozen_decisions(self):
    from tools.cyberpilot.canonical_readiness_fixture import job
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_bridge as b

    q = candidate()
    for index in range(32):
      data, _ = job(index, 'TRAIN')
      x, m, p, y, prior = (data[k] for k in ('x', 'stage2', 'p', 'y', 'prior'))
      u = q.predict(x, m)
      exact(self, u, python.canonical_predict_delta(x, m))
      d0 = b.d2.reconstruct_D0(p, y, role='TRAIN', counters={})['value']
      exact(self, q.predict(x[p > d0], m), u[p > d0])
      winners = []
      for state in (False, True):
        mask = (prior != 0) == state
        c, t = data['current'][mask], data['target'][mask]
        result = b.d2.select_context(p[mask], y[mask], c, t, u[mask], b.original.m.project(c.astype(np.float64) + u[mask]), float(d0), role='TRAIN')
        self.assertTrue(all(result['guards'].values()))
        self.assertTrue(result['witness_verified'])
        winners.append(result['decision'])
      gate = b.apply_gate(p, prior, tuple(winners), 'D2')
      exact(self, q.predict(x[gate], m), u[gate])

  def test_C_ABI_rejects_divergent_SSE_rounding_in_isolated_process(self):
    script = """
import ctypes
from openpilot.tools.cyber_autotune.tests.test_empirical_hurdle_v4_e2_canonical_native_candidate import candidate
q = candidate()
libm = ctypes.CDLL('libm.so.6')
buffer = ctypes.create_string_buffer(32)
assert libm.fegetenv(ctypes.byref(buffer)) == 0
saved = buffer.raw
try:
  for bits in (0x2000, 0x6000):
    env = bytearray(saved)
    mxcsr = int.from_bytes(env[28:32], 'little')
    env[28:32] = ((mxcsr & ~0x6000) | bits).to_bytes(4, 'little')
    buffer.raw = bytes(env)
    assert libm.fesetenv(ctypes.byref(buffer)) == 0
    assert libm.fegetround() == 0
    assert q.library.cp_environment() != 0, 'SSE_ROUNDING_NOT_REJECTED'
finally:
  buffer.raw = saved
  assert libm.fesetenv(ctypes.byref(buffer)) == 0
"""
    result = subprocess.run([sys.executable, '-B', '-c', script], capture_output=True, text=True, timeout=10)
    self.assertEqual(result.returncode, 0, result.stderr)

  def test_second_artifact_not_silently_reused_by_dlopen(self):
    q = candidate()
    with tempfile.TemporaryDirectory(prefix='public-native-second-') as tmp:
      parent = Path(tmp)
      raw = (q.receipt_path.parent / 'canonical_candidate.so').read_bytes() + b'PUBLIC_PADDING_WITNESS'
      (parent / 'canonical_candidate.so').write_bytes(raw)
      (parent / 'canonical_candidate.so').chmod(0o500)
      receipt = dict(q.receipt)
      receipt['binary_sha256'] = hashlib.sha256(raw).hexdigest()
      data = json.dumps(receipt, sort_keys=True, separators=(',', ':')).encode() + b'\n'
      (parent / 'build.json').write_bytes(data)
      (parent / 'build.json').chmod(0o600)
      with self.assertRaises(ValueError):
        type(q)(parent / 'build.json', hashlib.sha256(data).hexdigest())

  def test_FIFO_receipt_fails_without_blocking(self):
    with tempfile.TemporaryDirectory(prefix='public-native-fifo-') as tmp:
      path = Path(tmp) / 'build.json'
      os.mkfifo(path, 0o600)
      script = """
import sys
from pathlib import Path
from openpilot.tools.cyber_autotune.empirical_hurdle_v4_e2_canonical_native_candidate import NativeCandidate
try:
  NativeCandidate(Path(sys.argv[1]), '0'*64)
except ValueError:
  raise SystemExit(0)
raise SystemExit(1)
"""
      try:
        result = subprocess.run([sys.executable, '-B', '-c', script, str(path)], capture_output=True, text=True, timeout=3)
      except subprocess.TimeoutExpired:
        self.fail('FIFO_RECEIPT_BLOCKED_BEFORE_TYPE_CHECK')
      self.assertEqual(result.returncode, 0, result.stderr)

  def test_unscaled_recursive_control_exercises_both_contexts(self):
    from tools.cyberpilot.canonical_readiness_fixture import models
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_bridge as b

    q = candidate()
    n, h, length = 8, 200, 45
    stage1, stage2 = models(length)
    command = np.resize(np.array([-0.75, 0.75, -0.25, 0.25]), (n, length + h - 1))
    initial = np.zeros((n, length + 1), np.int64)
    reference = b.recursive(
      initial, command, np.full((n, h), 10.0), 'HRI_D00_L45', stage1, stage2, (0.5, 0.5), 'D2', h, np.full(n, h, np.int64), {}, scope=b.SCOPE
    )
    current, past = initial[:, -1].copy(), np.diff(initial, axis=1)
    contexts, gates, probabilities, deltas, paths, histories = [], [], [], [], [current.copy()], []
    for step in range(h):
      x = np.ascontiguousarray(np.column_stack((np.ones(n), command[:, step : step + length], past, current, np.full(n, 10.0))))
      probability = b.original.probability(x, stage1)
      gate = b.apply_gate(probability, past[:, -1], (0.5, 0.5), 'D2')
      delta = np.zeros(n, np.float64)
      if np.any(gate):
        delta[gate] = q.predict(x[gate], stage2)
      new = current.copy()
      if np.any(gate):
        new[gate] = b.original.m.project(current[gate].astype(np.float64) + delta[gate])
      contexts.append(past[:, -1] != 0)
      histories.append(past.copy())
      gates.append(gate)
      probabilities.append(probability)
      deltas.append(delta)
      paths.append(new.copy())
      past[:, :-1] = past[:, 1:]
      past[:, -1] = new - current
      current = new
    outputs = {
      'path': np.stack(paths, axis=1),
      'history_before': np.stack(histories, axis=1),
      'context': np.stack(contexts, axis=1),
      'gate': np.stack(gates, axis=1),
      'p_move': np.stack(probabilities, axis=1),
      'delta': np.stack(deltas, axis=1),
    }
    for name, value in outputs.items():
      exact(self, value, reference[name])
    self.assertTrue(np.any(outputs['context']))
    self.assertTrue(np.any(~outputs['context']))
    self.assertTrue(np.any(np.diff(outputs['path'], axis=1) != 0))

  def test_descriptor_modes_and_links(self):
    q = candidate()
    for kind in ('mode', 'hardlink', 'symlink'):
      with tempfile.TemporaryDirectory(prefix='public-native-descriptor-') as tmp:
        parent = Path(tmp)
        original = q.receipt_path.read_bytes()
        path = parent / 'build.json'
        if kind == 'symlink':
          path.symlink_to(q.receipt_path)
        else:
          path.write_bytes(original)
          path.chmod(0o600)
          if kind == 'mode':
            path.chmod(0o644)
          else:
            os.link(path, parent / 'second-link.json')
        with self.assertRaises((ValueError, OSError)):
          type(q)(path, hashlib.sha256(original).hexdigest())
