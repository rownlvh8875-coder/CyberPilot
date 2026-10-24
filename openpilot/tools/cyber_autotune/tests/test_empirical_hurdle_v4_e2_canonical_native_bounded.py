"""Public synthetic native integration; no private evidence or model payloads."""

import gc
import os
from pathlib import Path
import tempfile
import threading
import unittest
import numpy as np

from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_bridge as b
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_bounded as reference
from tools.cyberpilot.canonical_bounded_fixture import provider
from tools.cyberpilot.canonical_readiness_fixture import models


def backend():
  from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_native_bounded as q

  return q.VerifiedNativeBackend(Path(os.environ['CYBERPILOT_PUBLIC_NATIVE_RECEIPT']), os.environ['CYBERPILOT_PUBLIC_NATIVE_RECEIPT_SHA256'])


class TestNativeBounded(unittest.TestCase):
  def test_backend_requires_verified_artifact_and_exact_type(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_native_bounded as q

    with self.assertRaises((ValueError, FileNotFoundError)):
      q.VerifiedNativeBackend(Path('/NO_PUBLIC_ARTIFACT/build.json'), '0' * 64)
    with self.assertRaises(ValueError):
      q.require_backend(object())
    self.assertEqual(backend().envelope()['python_fallback_calls'], 0)

  def test_all_layouts_and_reused_models_match_raw_python_bytes(self):
    native = backend()
    _, model = models(45)
    base = np.arange(16 * 93, dtype=np.float64).reshape(16, 93) / 64
    base[:, 0] = 1
    raw = bytearray(base.nbytes + 1)
    unaligned = np.ndarray(base.shape, np.float64, buffer=raw, offset=1)
    unaligned[:] = base
    for x in (base, np.asfortranarray(base), base[::2], unaligned, base.copy()):
      before = x.tobytes()
      expected = b.canonical.canonical_predict_delta(x, model)
      for _ in range(3):
        actual = native.predict(x, model, site='ABI_TEST')
        self.assertEqual(actual.dtype, np.float64)
        self.assertEqual(actual.tobytes(), expected.tobytes())
        gc.collect()
      self.assertEqual(x.tobytes(), before)
    self.assertEqual(native.envelope()['active_strong_reference_entries'], 0)
    self.assertGreaterEqual(native.envelope()['peak_strong_reference_entries'], 7)
    self.assertGreater(native.envelope()['input_x_copy_bytes'], 0)
    sliced = {'normalizer': {}, 'coefficients': None}
    for key, array in model['normalizer'].items():
      carrier = np.empty(len(array) * 2, dtype=array.dtype)
      carrier[::2] = array
      sliced['normalizer'][key] = carrier[::2]
    carrier = np.empty(len(model['coefficients']) * 2)
    carrier[::2] = model['coefficients']
    sliced['coefficients'] = carrier[::2]
    expected = b.canonical.canonical_predict_delta(base, sliced)
    actual = native.predict(base, sliced, site='ABI_TEST')
    self.assertEqual(actual.tobytes(), expected.tobytes())
    self.assertGreater(native.envelope()['model_array_copy_bytes'], 0)
    self.assertGreater(native.envelope()['coefficient_copy_bytes'], 0)
    self.assertIn('NOT_UNIQUE_OWNER', native.envelope()['ownership_accounting'])

  def test_real_native_call_under_gc_pressure_and_trace(self):
    native = backend()
    _, model = models(45)
    x = np.ones((8192, 93), np.float64, order='F')
    expected = b.canonical.canonical_predict_delta(x, model)
    stop = threading.Event()

    def collect():
      while not stop.is_set():
        gc.collect()
        stop.wait(0.001)

    thread = threading.Thread(target=collect)
    thread.start()
    try:
      actual, trace = native.predict(x, model, site='ABI_TEST', trace=True)
      self.assertEqual(actual.tobytes(), expected.tobytes())
      self.assertEqual(trace.shape, (len(x), 93))
    finally:
      stop.set()
      thread.join()
    self.assertEqual(native.envelope()['active_strong_reference_entries'], 0)

  def test_invalid_inputs_fail_without_python_fallback(self):
    native = backend()
    _, model = models(1)
    for x in (np.ones((1, 5), np.float32), np.ones(5), np.full((1, 5), np.nan)):
      with self.assertRaises(ValueError):
        native.predict(x, model, site='ABI_TEST')
    self.assertEqual(native.envelope()['python_fallback_calls'], 0)
    self.assertEqual(native.envelope()['active_strong_reference_entries'], 0)

  def test_empty_gate_has_zero_stage2_calls_positive_zero_and_hold(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_native_bounded as q

    stage1, model = models(1)
    x = np.ones((8, 5), np.float64)
    x[:, -3:] = 0
    native = backend()
    row = q.infer(x, np.zeros(8, np.int64), stage1, model, (1.0,), 'D0', {}, backend=native, scope=b.SCOPE)
    self.assertEqual(native.envelope()['native_calls'], 0)
    self.assertTrue(np.all(row['delta'].view(np.uint64) == 0))
    self.assertFalse(row['realized_movement'].any())

  def test_full_selected_call_and_signed_zero_corruption_detection(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_native_bounded as q

    p = provider()
    native = backend()
    with p.features(0) as job:
      cache = q.potential_cache(job, {}, native)
      gate = np.ones(len(job['p']), bool)
      proof = q.qualify(job, cache, gate, 'Q1', {}, p.lifetime, native)
      self.assertEqual(proof['selected_stage2_calls'], 1)
      cache['u'][0] = -0.0 if cache['u'][0] == 0 else np.nextafter(cache['u'][0], np.inf)
      with self.assertRaises(ValueError):
        q.qualify(job, cache, gate, 'Q1', {}, p.lifetime, native)
    with self.assertRaises(ValueError):
      b.require_bytes(np.array([-0.0]), np.array([0.0]), 'SIGNED_ZERO_MISMATCH')

  def test_recursive_full_trace_matches_both_backends_and_workspace(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_native_bounded as q

    native = backend()
    stage1, stage2 = models(45)
    n, h = 8, 200
    initial = np.zeros((n, 46), np.int64)
    command = np.resize(np.array([-0.75, 0.75, -0.25, 0.25]), (n, 45 + h - 1))
    speed = np.full((n, h), 10.0)
    available = np.full(n, 200, np.int64)
    for arm in b.ARMS:
      decisions = (0.0,) if arm == 'D0' else (0.0, 0.0)
      expected = b.recursive(initial, command, speed, 'HRI_D00_L45', stage1, stage2, decisions, arm, h, available, {}, scope=b.SCOPE)
      for optimized in (False, True):
        actual = q.recursive(
          initial, command, speed, 'HRI_D00_L45', stage1, stage2, decisions, arm, h, available, {}, scope=b.SCOPE, backend=native, optimized=optimized
        )
        for key in expected:
          self.assertEqual(actual[key].tobytes(), expected[key].tobytes(), key)
        self.assertTrue(actual['context'].any())
        self.assertTrue((~actual['context']).any())
        self.assertTrue(np.diff(actual['path'], axis=1).any())

  def test_all32_seals_scientific_payloads_and_intermediate_audits_exact(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_native_bounded as q
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_caller_profile as profile

    binding = reference.old.synthetic_binding('2' * 40)
    expected_files = expected_audit = None
    with tempfile.TemporaryDirectory() as tmp:
      for mode in q.MODES:
        path = Path(tmp) / mode
        with profile.ScientificAudit() as witness:
          result = (
            reference.run_synthetic(provider(), path, binding)
            if mode == q.MODES[0]
            else q.run_synthetic(provider(), path, binding, backend(), optimized=mode == q.MODES[2])
          )
        files = {name: (path / name).read_bytes() for name in ('train.json', 'result.json', 'complete.json')}
        if expected_files is None:
          expected_files, expected_audit = files, witness.snapshot()
        else:
          self.assertEqual(files, expected_files)
          self.assertEqual(witness.snapshot(), expected_audit)
          self.assertEqual(result['native_envelope']['python_fallback_calls'], 0)
          for site in ('TRAIN_CACHE', 'Q1', 'Q3', 'DEV_ONE_STEP', 'DEV_RECURSIVE'):
            self.assertGreater(result['native_envelope']['site_calls'].get(site, 0), 0, site)
        self.assertEqual(result['coverage'], {'D0': 32, 'D1': 64, 'D2': 64, 'Q1': 32, 'Q3': 32, 'DEV_jobs': 32})
        self.assertEqual(reference.old.verify_synthetic(path, binding, result['completion_digest'])['scientific_recomputations'], 0)
        from tools.cyberpilot.run_canonical_native_bounded import verify_output

        with q.out.Store(path, create=False) as output:
          envelope_sha = output.write('execution.json', {'binding': binding, 'completion_digest': result['completion_digest']})
        with profile.CallerProfile() as verifier:
          self.assertEqual(verify_output(path, envelope_sha)['scientific_recomputations'], 0)
        self.assertFalse(
          any(name in verifier.snapshot()['functions'] for name in ('Stage1.probability', 'PythonStage2', 'NativeWrapper.predict', 'SourceBlock.check'))
        )
        self.assertEqual(result['lifetime']['live_counts'].get('feature', 0), 0)

  def test_q1_incomplete_and_mutated_winner_block_following_phases(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_native_bounded as q

    p = provider()
    pipeline = q.NativeTrainPipeline(p, backend())
    pipeline.reconstruct_d0()
    pipeline.cache_potentials()
    with self.assertRaises(ValueError):
      pipeline.select_d2()
    self.assertEqual(pipeline.counters.get('D2_context_decision_selection_calls', 0), 0)
    pipeline.qualify_q1()
    pipeline.select_d1()
    pipeline.select_d2()
    pipeline.policies[0]['D2'] = (0.0, 0.0)
    with self.assertRaises(ValueError):
      pipeline.qualify_q3()
    self.assertEqual(p._dev_key, None)

  def test_no_private_entry_or_arbitrary_provider(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_native_bounded as q

    with self.assertRaisesRegex(ValueError, 'NOT_AUTHORIZED'):
      q.execute_private(object())
    with self.assertRaises(ValueError):
      q.NativeTrainPipeline(object(), backend())


class TestTerminalIntegrity(unittest.TestCase):
  def test_dev_before_seal_is_terminal_and_does_not_compute(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_native_bounded as q

    p = provider()
    with tempfile.TemporaryDirectory() as tmp, q.out.Store(Path(tmp) / 'output') as store:
      run = q.NativeRun(p, store, q.old.synthetic_binding('3' * 40), backend())
      with self.assertRaises(ValueError):
        run.advance(q.Phase.SEAL, q.Phase.DEV, lambda: self.fail('DEV action must not run'))
      self.assertEqual(run.phase, q.Phase.FAILED)
      with self.assertRaises(ValueError):
        run.train()
      self.assertIsNone(p._dev_key)

  def test_changed_durable_seal_blocks_dev_and_reexecution(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_native_bounded as q

    p = provider()
    with tempfile.TemporaryDirectory() as tmp, q.out.Store(Path(tmp) / 'output') as store:
      run = q.NativeRun(p, store, q.old.synthetic_binding('4' * 40), backend(), optimized=True)
      run.train()
      path = Path(tmp) / 'output' / 'train.json'
      raw = bytearray(path.read_bytes())
      raw[-2] ^= 1
      path.write_bytes(raw)
      with self.assertRaises(ValueError):
        run.evaluate(q.old.public_check()[0]['acceptance']['clauses'])
      self.assertEqual(run.phase, q.Phase.FAILED)
      self.assertIsNone(p._dev_key)
      with self.assertRaises(ValueError):
        run.train()

  def test_input_signed_zero_witness_detects_equal_predictions(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_caller_profile as audit

    stage1, stage2 = models(1)
    witnesses = []
    outputs = []
    for zero in (0.0, -0.0):
      x = np.zeros((2, 5))
      x[:, 0] = 1
      x[:, 1] = zero
      with audit.ScientificAudit() as witness:
        result = b.infer(x, np.zeros(2, np.int64), stage1, stage2, (0.0,), 'D0', {}, scope=b.SCOPE)
      outputs.append(result['delta'].tobytes())
      witnesses.append(witness.snapshot())
    self.assertEqual(outputs[0], outputs[1])
    self.assertNotEqual(witnesses[0], witnesses[1])
