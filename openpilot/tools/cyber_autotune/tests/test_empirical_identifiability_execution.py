import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from openpilot.tools.cyber_autotune import empirical_identifiability_execution as e
from openpilot.tools.cyber_autotune import empirical_identifiability_publication as publication
from openpilot.tools.cyber_autotune import empirical_causal_dataset_store as storage
from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_identifiability_policy as policy


class TestIdentifiabilityExecution(unittest.TestCase):
  def test_input_admission_precedes_array_load(self):
    with tempfile.TemporaryDirectory() as td, patch('numpy.load', side_effect=AssertionError('TOO_EARLY')):
      with self.assertRaises((ValueError, FileNotFoundError)):
        e.preflight(Path(td), policy.policy())

  def test_policy_drift_before_array(self):
    with tempfile.TemporaryDirectory() as td, patch('numpy.load', side_effect=AssertionError):
      pol = policy.policy()
      pol['lags'] = [5]
      with self.assertRaises(ValueError):
        e.preflight(Path(td), pol)

  def test_array_file_hash_drift(self):
    with tempfile.TemporaryDirectory() as td:
      path = Path(td)/'x.npy'
      binding = storage.array_write(path, np.arange(5, dtype=float))
      path.write_bytes(b'bad')
      with patch('numpy.load', side_effect=AssertionError):
        with self.assertRaisesRegex(ValueError, 'HASH'):
          e.read_array(path, binding)

  def test_array_exact_readonly(self):
    with tempfile.TemporaryDirectory() as td:
      path = Path(td)/'x.npy'
      binding = storage.array_write(path, np.arange(5, dtype=float))
      a = e.read_array(path, binding)
      self.assertFalse(a.flags.writeable)
      np.testing.assert_array_equal(a, np.arange(5))

  def test_raw_extension_rejected_before_read(self):
    with tempfile.TemporaryDirectory() as td:
      with self.assertRaises(ValueError):
        e.read_array(Path(td)/'rlog.zst', {})

  def test_symlink_rejected(self):
    with tempfile.TemporaryDirectory() as td:
      root = Path(td)
      storage.array_write(root/'x.npy', np.arange(2))
      (root/'alias.npy').symlink_to(root/'x.npy')
      with self.assertRaises(ValueError):
        e.read_array(root/'alias.npy', {})

  def test_no_traversal_field_name(self):
    for name in ('../x', '/tmp/x', 'gyro/xyz', 'x\\y', ''):
      with self.subTest(name=name), self.assertRaises(ValueError):
        e.array_name(name)

  def test_no_object_array(self):
    with tempfile.TemporaryDirectory() as td:
      path = Path(td)/'x.npy'
      b = io.BytesIO()
      np.save(b, np.array([{}], dtype=object))
      path.write_bytes(b.getvalue())
      with self.assertRaises(ValueError):
        e.read_array(path, {'file_sha256': p.sha(b.getvalue())})

  def test_public_rows_rejected(self):
    for key in ('targets', 'predictions', 'residuals', 'coefficients', 'row_origin', 'grid_time_ns', 'local_path'):
      with self.subTest(key=key), self.assertRaises(ValueError):
        publication.validate_public(p.seal({'schema': 'TEST', key: [1]}))

  def test_public_absolute_paths_rejected(self):
    for value in ('/home/private', 'D:\\CarrotLogs\\x'):
      with self.subTest(value=value), self.assertRaises(ValueError):
        publication.validate_public(p.seal({'schema': 'TEST', 'value': value}))

  def test_count_rows_is_not_private_row_data(self):
    with self.assertRaises(ValueError):
      publication.validate_public(p.seal({'schema': 'TEST', 'rows': 201, 'singular_values': [1., .1]}))

  def test_array_changed_after_read_rejected(self):
    with tempfile.TemporaryDirectory() as td:
      root = Path(td)
      path = root/'x.json'
      path.write_bytes(b'a')
      pins = {'x.json': p.sha(b'a')}
      e.verify_files(root, pins)
      path.write_bytes(b'b')
      with self.assertRaises(ValueError):
        e.verify_files(root, pins)

  def test_history_count_has_no_selection(self):
    data = {'streak': np.arange(1, 51), 'segment': np.zeros(50, int), 'causal': np.zeros(50, int),
            'speed': np.ones(50)*10}
    rows = e.history_report(data)
    self.assertEqual(len(rows), 45)
    self.assertEqual(rows[0]['eligible_windows'], 50)
    self.assertEqual(rows[-1]['eligible_windows'], 6)
    self.assertTrue(all('selected' not in r for r in rows))

  def test_next_pair_cannot_cross_join(self):
    data = {'streak': np.array([1, 2, 3, 1, 2])}
    np.testing.assert_array_equal(e.next_pairs(data), [0, 1, 3])

  def test_pooled_rank_cannot_hide_route_gate(self):
    rows = [{'support': {'A': 300, 'B': 200}, 'rank': {'A': 5, 'B': 4, 'POOLED': 5}}]
    self.assertFalse(all(v >= 201 for v in rows[0]['support'].values()))

  def test_qlog_whole_manifest_rejected_before_arrays(self):
    pol = policy.policy()
    auth = {'segments': {pol['route_ids'][0]: [pol['excluded_qlog_content_sha256'][0]]}}
    with tempfile.TemporaryDirectory() as td, patch.object(e, 'read_json', side_effect=[{}, auth]), \
         patch('numpy.load', side_effect=AssertionError('QLOG_OPENED')):
      with self.assertRaisesRegex(ValueError, 'QLOG_CAUSAL_ADMISSION_FORBIDDEN'):
        e.preflight(Path(td), pol)

  def test_history_kernel_matches_existing_guard(self):
    from openpilot.tools.cyber_autotune.tests import test_empirical_causal_support_guard_v1 as existing
    fixture = existing.TestFutureSupportGuard()
    fixture.setUp()
    fixture.arrays['legacy_diagnostic_valid'][1] = False
    fixture.bind()
    a = fixture.arrays
    base = fixture.run_guard()
    from openpilot.tools.cyber_autotune import empirical_identifiability_math as m
    streak = m.streaks(base, a['causal_run_id'], a['within_causal_run_index'], a['grid_time_ns'])
    for length in m.HISTORIES:
      np.testing.assert_array_equal(streak >= length, fixture.run_guard(history=length))

  def test_complete_synthetic_execution_repeats_without_model_or_raw_calls(self):
    import contextlib
    import os
    from openpilot.tools.cyber_autotune import empirical_final_readiness as readiness
    from openpilot.tools.cyber_autotune.tests import test_empirical_causal_support_guard_v1 as existing
    fixture = existing.TestFutureSupportGuard()
    fixture.setUp()
    fixture.bind()
    with tempfile.TemporaryDirectory() as td:
      top = Path(td)
      root, output, source = top/'input', top/'output', top/'source'
      root.mkdir()
      source.mkdir()
      records = []
      for rid in policy.policy()['route_ids']:
        base = root/rid
        arrays = {k: v.copy() for k, v in fixture.arrays.items()}
        n = fixture.n
        arrays['state.angle_deg'] = np.array([0., .1, .1, .2])
        arrays['state.rate'] = np.array([0., 4., 4., 8.])
        arrays['state.speed_mps'] = np.full(n, 10.)
        arrays['state.eps_fault'] = np.zeros(n)
        arrays['state.eps_fault.available'] = np.ones(n, dtype=bool)
        arrays['command.raw'] = np.arange(n, dtype=float)
        arrays['command.normalized'] = (arrays['command.raw']/409).astype(np.float32).astype(float)
        for field in ('active_rising', 'active_falling', 'pressed_rising', 'pressed_falling', 'run_boundary', 'segment_boundary'):
          arrays[field] = np.zeros(n, dtype=bool)
        arrays['consumed_input_snapshot_sha256'] = np.full(n, 'a'*64, dtype='U64')
        segment = {**fixture.segment, 'route_id': rid,
          'arrays': {k: storage.array_write(base/'arrays'/e.array_name(k), v) for k, v in arrays.items()}}
        records.append((base, segment))
      fake = (readiness.load(), readiness.resolve(), {'receipt_sha256': 'a'*64}, records, {})
      with patch.dict(os.environ, {'OPENBLAS_NUM_THREADS': '1', 'OMP_NUM_THREADS': '1'}), \
           patch.object(e, 'preflight', return_value=fake), patch.object(e.policy, 'audit_source', return_value=policy.source_contract()), \
           patch.object(e.guard, 'eligible_rows', return_value=np.ones(fixture.n, bool)), \
           patch('numpy.linalg.lstsq', side_effect=AssertionError('FITTING')), \
           patch('numpy.linalg.pinv', side_effect=AssertionError('FITTING')), contextlib.redirect_stdout(io.StringIO()):
        a = e.run(root, output, source, 'repeat-1')
        b = e.run(root, output, source, 'repeat-2')
        self.assertEqual(a, b)
        e.run(root, output, source, 'repeat-1')
      self.assertEqual(len(a['families']['S1']), 21)
      self.assertEqual(len(a['families']['S2']), 45)
      self.assertEqual(a['qlog_arrays_opened'], 0)
      self.assertFalse(any(a['authority'].values()))
      # Toy fixture proves kernels, not the exact historical 154-stream admission.
      with self.assertRaises(ValueError):
        publication.build(output)

  def test_unknown_nested_samples_rejected(self):
    with self.assertRaises(ValueError):
      publication.validate_public(p.seal({'schema': 'EMPIRICAL_IDENTIFIABILITY_EXCITATION_V1',
        'policy_sha256': policy.policy()['receipt_sha256'], 'coverage': {},
        'scopes': {'individual_angle_samples': [1.2, 3.4], 'timestamp_ns': [100, 200]}}))

  def test_empty_matching_results_cannot_publish_complete(self):
    pol = policy.policy()
    result = p.seal({'schema': 'EMPIRICAL_MODEL_FAMILY_IDENTIFIABILITY_RESULTS_V1',
      'policy_sha256': pol['receipt_sha256'], 'source_contract_sha256': policy.source_contract()['receipt_sha256'],
      'families': {'S1': [], 'S2': []}, 'excitation': {}, 'coverage': {}, 'history_support': {},
      'historical_inputs_byte_identical': False, 'raw_logs_opened': 1, 'qlog_arrays_opened': 1})
    with tempfile.TemporaryDirectory() as td, patch.object(publication, 'read_json', side_effect=[
        pol, policy.source_contract(), result, result, {}]):
      with self.assertRaises(ValueError):
        publication.build(Path(td))
