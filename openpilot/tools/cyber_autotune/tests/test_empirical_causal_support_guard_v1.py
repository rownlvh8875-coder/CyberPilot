"""Synthetic-only future row admission: no historical numeric arrays opened."""
from unittest.mock import patch
import unittest
import numpy as np

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_final_readiness as readiness


def seal(row):
  return p.seal({k: v for k, v in row.items() if k != "receipt_sha256"})


def guard_module(test):
  import importlib.util
  name = 'openpilot.tools.cyber_autotune.empirical_causal_support_guard'
  if importlib.util.find_spec(name) is None:
    test.fail('Pinned rlog segment and causal row guard not implemented')
  return __import__(name, fromlist=['eligible_rows'])


class TestFutureSupportGuard(unittest.TestCase):
  def setUp(self):
    self.x = readiness.load()
    self.route = self.x[readiness.RLOG_ROUTES]['routes'][0]
    self.coverage = self.x[readiness.RLOG_COVERAGE]['routes'][0]
    self.rid = self.route['route_id']
    self.digest = 'a'*64
    self.n = 4
    fields = self.x['empirical-causal-context-schema-v2-execution-v1.json']['required_fields']
    self.arrays = {k: np.full(self.n, 'drive', dtype='<U16') if k == 'state.gear' else np.ones(self.n, dtype='<f8') for k in fields}
    self.arrays.update({k+'.available': np.ones(self.n, dtype=bool) for k in fields})
    self.arrays.update({'grid_time_ns': np.arange(self.n, dtype='<i8')*10_000_000+100_000_000,
      'causal_run_id': np.zeros(self.n, dtype='<i8'), 'within_causal_run_index': np.arange(self.n, dtype='<i8'),
      'causal_required_valid': np.ones(self.n, dtype=bool), 'legacy_diagnostic_valid': np.ones(self.n, dtype=bool),
      'state.time_ns': np.arange(self.n, dtype='<i8')*10_000_000+100_000_000})
    for kind in ('state', 'command', 'control'):
      self.arrays[kind+'.time_ns'] = self.arrays['state.time_ns'].copy()
      self.arrays[kind+'.age_ns'] = np.zeros(self.n, dtype='<i8')
      self.arrays[kind+'.event_valid'] = np.ones(self.n, dtype='i1')
      self.arrays[kind+'.present'] = np.ones(self.n, dtype=bool)
      self.arrays[kind+'.fresh'] = np.ones(self.n, dtype=bool)
      self.arrays[kind+'.gap'] = np.zeros(self.n, dtype=bool)

  def bind(self):
    auth = self.x[readiness.RLOG_AUTH]
    self.segment = seal({'schema': 'EMPIRICAL_CAUSAL_SEGMENT_EXTRACTION_V1',
      'route_id': self.rid, 'segment_sha256': self.digest, 'ordinal': 0,
      'authorization_sha256': auth['private_authorization_sha256'],
      'source_fingerprint_sha256': auth['source_fingerprint_sha256'],
      'recorded_adapter_sha256': auth['recorded_adapter_sha256'],
      'numeric_adapter_sha256': auth['numeric_adapter_sha256'], 'config_sha256': self.coverage['config_sha256'],
      'coverage': {'total_grid_samples': self.n},
      'arrays': {k: {'dtype': a.dtype.str, 'shape': list(a.shape), 'order': 'C',
                    'array_sha256': p.sha(a.tobytes(order='C'))} for k, a in self.arrays.items()}})
    self.manifest = seal({'schema': 'EMPIRICAL_CAUSAL_PRIVATE_DATASET_MANIFEST_V1',
      'authorization_sha256': auth['private_authorization_sha256'],
      'route_set_sha256': self.x[readiness.RLOG_ROUTES]['receipt_sha256'],
      'routes': [{'route_id': r['route_id'], 'role': readiness.ROLE,
                  'segments': [self.segment['receipt_sha256']] if r['route_id'] == self.rid else []}
                 for r in self.x[readiness.RLOG_ROUTES]['routes']]})
    self.x[readiness.INTERMEDIATE] = seal({**self.x[readiness.INTERMEDIATE],
      'dataset_manifest_sha256': self.manifest['receipt_sha256']})
    self.x[readiness.MERGE] = seal({**self.x[readiness.MERGE],
      'historical_manifest_sha256': self.manifest['receipt_sha256']})
    self.x[readiness.EXECUTION] = seal({**self.x[readiness.EXECUTION],
      'artifacts': {n: self.x[n]['receipt_sha256'] for n in self.x[readiness.EXECUTION]['artifacts']}})
    self.x[readiness.FINAL] = seal({**self.x[readiness.FINAL],
      'initial_aggregate_gate_sha256': self.x[readiness.EXECUTION]['receipt_sha256'],
      'inputs': {n: self.x[n]['receipt_sha256'] for n in self.x[readiness.FINAL]['inputs']}})
    self.pins = {n: r['receipt_sha256'] for n, r in self.x.items()}
    with patch.object(readiness, 'PINS', self.pins):
      self.resolution = readiness.resolve(self.x)

  def run_guard(self, **kwargs):
    module = guard_module(self)
    with patch.object(readiness, 'PINS', self.pins):
      return module.eligible_rows(self.resolution, self.manifest, self.segment, self.arrays, self.x, **kwargs)

  def test_valid_synthetic_rows(self):
    self.bind()
    self.assertEqual(self.run_guard().tolist(), [True]*4)

  def test_qlog_rejected_before_arrays(self):
    self.digest = self.x[readiness.QLOG_COVERAGE]['segments'][0]['segment_sha256']
    self.bind()
    class NeverRead(dict):
      def __iter__(self):
        raise AssertionError('Arrays accessed before qlog rejection')
      def keys(self):
        raise AssertionError('Arrays accessed before qlog rejection')
    self.arrays = NeverRead()
    with self.assertRaisesRegex(ValueError, 'QLOG_ACCOUNTING_ONLY'):
      self.run_guard()

  def test_unknown_segment_rejected(self):
    self.bind()
    self.segment = seal({**self.segment, 'segment_sha256': 'b'*64})
    with self.assertRaises(ValueError):
      self.run_guard()

  def test_wrong_manifest_rejected(self):
    self.bind()
    self.manifest = seal({**self.manifest, 'authorization_sha256': 'wrong'})
    with self.assertRaises(ValueError):
      self.run_guard()

  def test_execution_ready_rejected_as_resolution(self):
    self.bind()
    self.resolution = self.x[readiness.EXECUTION]
    with self.assertRaises(ValueError):
      self.run_guard()

  def test_array_bytes_drift_rejected(self):
    self.bind()
    self.arrays['state.rate'][0] = 9
    with self.assertRaisesRegex(ValueError, 'ARRAY'):
      self.run_guard()

  def test_false_availability_masks_row(self):
    self.arrays['control.requested.available'][1] = False
    self.bind()
    self.assertEqual(self.run_guard().tolist(), [True, False, True, True])

  def test_nan_not_zero_filled(self):
    self.arrays['state.rate'][1] = np.nan
    self.bind()
    self.assertEqual(self.run_guard().tolist(), [True, False, True, True])

  def test_stale_row_masks(self):
    self.arrays['control.age_ns'][1] = 20_000_001
    self.arrays['control.time_ns'][1] -= 20_000_001
    self.bind()
    self.assertEqual(self.run_guard().tolist(), [True, False, True, True])

  def test_exact_twenty_ms_allowed(self):
    self.arrays['control.age_ns'][1] = 20_000_000
    self.arrays['control.time_ns'][1] -= 20_000_000
    self.bind()
    self.assertEqual(self.run_guard().tolist(), [True]*4)

  def test_future_time_rejected(self):
    self.arrays['control.time_ns'][1] += 1
    self.arrays['control.age_ns'][1] = -1
    self.bind()
    with self.assertRaisesRegex(ValueError, 'FUTURE'):
      self.run_guard()

  def test_fabricated_age_rejected(self):
    self.arrays['control.age_ns'][1] = 1
    self.bind()
    with self.assertRaisesRegex(ValueError, 'AGE'):
      self.run_guard()

  def test_invalid_event_masks(self):
    self.arrays['state.event_valid'][1] = 0
    self.bind()
    self.assertEqual(self.run_guard().tolist(), [True, False, True, True])

  def test_gap_masks(self):
    self.arrays['command.gap'][1] = True
    self.bind()
    self.assertEqual(self.run_guard().tolist(), [True, False, True, True])

  def test_negative_run_not_training_support(self):
    self.arrays['causal_run_id'][1] = -1
    self.arrays['within_causal_run_index'][1] = -1
    self.bind()
    self.assertEqual(self.run_guard().tolist(), [True, False, True, True])

  def test_diagnostic_invalid_not_training_support(self):
    self.arrays['legacy_diagnostic_valid'][1] = False
    self.bind()
    self.assertEqual(self.run_guard().tolist(), [True, False, True, True])

  def test_history_cannot_cross_gap(self):
    self.arrays['causal_required_valid'][1] = False
    self.bind()
    self.assertEqual(self.run_guard(history=2).tolist(), [False, False, False, True])

  def test_history_cannot_cross_run(self):
    self.arrays['causal_run_id'][2:] = 1
    self.arrays['within_causal_run_index'][2:] = [0, 1]
    self.bind()
    self.assertEqual(self.run_guard(history=2).tolist(), [False, True, False, True])

  def test_history_cannot_cross_integer_grid_gap(self):
    self.arrays['grid_time_ns'][2:] += 10_000_000
    self.arrays['state.time_ns'][2:] += 10_000_000
    for k in ('command', 'control'):
      self.arrays[k+'.time_ns'][2:] += 10_000_000
    self.bind()
    self.assertEqual(self.run_guard(history=2).tolist(), [False, True, False, True])

  def test_no_fitting_or_array_mutation(self):
    self.bind()
    before = {k: a.tobytes() for k, a in self.arrays.items()}
    with patch('numpy.linalg.lstsq', side_effect=AssertionError('FITTING_PROHIBITED')):
      self.assertEqual(self.run_guard().tolist(), [True]*4)
    self.assertEqual({k: a.tobytes() for k, a in self.arrays.items()}, before)

  def test_forged_qlog_stream_label_cannot_promote(self):
    self.digest = self.x[readiness.QLOG_COVERAGE]['segments'][0]['segment_sha256']
    self.bind()
    self.segment = seal({**self.segment, 'kind': 'rlog.zst'})
    with self.assertRaisesRegex(ValueError, 'QLOG_ACCOUNTING_ONLY'):
      self.run_guard()

  def test_merged_accounting_manifest_not_training_manifest(self):
    self.bind()
    self.manifest = seal({**self.manifest, 'schema': 'EMPIRICAL_QLOG_RECONCILIATION_MANIFEST_V1'})
    with self.assertRaises(ValueError):
      self.run_guard()

  def test_zero_support_old_development_route_rejected(self):
    self.bind()
    self.segment = seal({**self.segment, 'route_id': 'not-the-two-admitted-train-routes'})
    with self.assertRaises(ValueError):
      self.run_guard()

  def test_wrong_config_rejected(self):
    self.bind()
    self.segment = seal({**self.segment, 'config_sha256': 'wrong'})
    with self.assertRaises(ValueError):
      self.run_guard()

  def test_wrong_adapter_rejected(self):
    self.bind()
    self.segment = seal({**self.segment, 'numeric_adapter_sha256': 'wrong'})
    with self.assertRaises(ValueError):
      self.run_guard()

  def test_unknown_required_array_rejected(self):
    del self.arrays['state.rate']
    self.bind()
    with self.assertRaises(ValueError):
      self.run_guard()

  def test_coverage_count_cannot_replace_actual_rate(self):
    self.arrays['state.rate'] = np.asarray([4], dtype='<i8')
    self.bind()
    with self.assertRaises(ValueError):
      self.run_guard()

  def test_missing_event_masks_even_with_fresh_true(self):
    self.arrays['control.present'][1] = False
    self.bind()
    self.assertEqual(self.run_guard().tolist(), [True, False, True, True])

  def test_integer_availability_cannot_fabricate_boolean(self):
    self.arrays['state.rate.available'] = np.ones(self.n, dtype='<i8')
    self.bind()
    with self.assertRaises(ValueError):
      self.run_guard()

  def test_invalid_history_not_searched(self):
    self.bind()
    for h in (0, -1, 1.5, True):
      with self.subTest(history=h), self.assertRaises(ValueError):
        self.run_guard(history=h)

  def test_source_clock_regression_rejected(self):
    self.arrays['state.time_ns'][2] = self.arrays['state.time_ns'][0]
    self.arrays['state.age_ns'][2] = 20_000_000
    self.arrays['command.time_ns'][2] = self.arrays['state.time_ns'][0]
    self.arrays['control.time_ns'][2] = self.arrays['state.time_ns'][0]
    self.bind()
    with self.assertRaises(ValueError):
      self.run_guard()

  def test_byte_exact_mask_repeatability(self):
    self.bind()
    self.assertEqual(self.run_guard(history=2).tobytes(), self.run_guard(history=2).tobytes())


if __name__ == '__main__':
  unittest.main()
