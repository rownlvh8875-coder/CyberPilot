"""Exact same-phase null-safe conversion and immutable page/storage tests."""

from pathlib import Path
import tempfile
import unittest

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import cyber_h1_pairing as q
from openpilot.tools.cyber_autotune import cyber_h1_paired_visual_adapter as a
from openpilot.tools.cyber_autotune import cyber_h1_comparison_catalog as catalog
from openpilot.tools.cyber_autotune import cyber_lateral_h1_producer as h
from openpilot.tools.cyber_autotune.tests.h1_pair_fixture import pairs


class TestPairedVisual(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.packages = pairs()['SG_A']
    cls.fs = a.convert(*cls.packages)

  def test_one_to_one_exact_phase(self):
    self.assertEqual(self.fs['frame_count'], 800)
    for i, f in enumerate(self.fs['frames']):
      self.assertEqual(f['capture_time_ns'], i * 10_000_000)
      self.assertEqual(f['decision_time_ns'], i * 10_000_000 + 1)
      self.assertEqual(f['completion_time_ns'], (i + 1) * 10_000_000)
      self.assertEqual(f['baseline']['actual_curvature_pre_step_1pm'], self.packages[0]['rows'][i]['signals']['actual_curvature'])
      self.assertEqual(f['candidate']['curvature_post_step_1pm'], self.packages[1]['rows'][i]['plant_output']['curvature'])

  def test_candidate_minus_baseline(self):
    for f in self.fs['frames']:
      for field in a.DELTAS:
        self.assertEqual(f['delta'][field], f['candidate'][field] - f['baseline'][field])

  def test_null_delta(self):
    self.assertIsNone(a.delta('applied_torque', {'applied_torque': None}, {'applied_torque': 0.1}))
    self.assertIsNone(a.delta('applied_torque', {'applied_torque': 0.1}, {'applied_torque': None}))

  def test_shared_or_cross_phase_delta_rejected(self):
    for field in ('desired_curvature_1pm', 'speed_mps', 'event', 'curvature_post_minus_pre', 'evidence_tier'):
      with self.assertRaises(ValueError):
        a.delta(field, {field: 1}, {field: 2})

  def test_no_sensor_or_prelimit_fabrication(self):
    for f in self.fs['frames']:
      for arm in ('baseline', 'candidate'):
        for key in ('requested_pre_limit_torque', 'pre_limit_torque', 'torque_output_can', 'steering_angle_deg', 'steering_rate_deg_s', 'driver_torque'):
          self.assertIsNone(f[arm][key])
          self.assertIn(key, f[arm]['unavailable'])

  def test_no_fill_or_dropped_support(self):
    self.assertEqual(self.fs['coverage'], {'input_pairs': 800, 'output_frames': 800, 'dropped': 0, 'filled': 0, 'interpolated': 0})
    for stats in self.fs['delta_statistics'].values():
      self.assertEqual(stats['count'], 800)
      self.assertEqual(stats['coverage'], 1)

  def test_stats_known_values(self):
    self.assertEqual(a.quantile([4, 0, 2], 0.5), 2)
    self.assertEqual(a.quantile([4, 0, 2], 0.95), 3.8)

  def test_same_source_inputs_not_mutated(self):
    before = p.canonical(self.packages)
    a.convert(*self.packages)
    self.assertEqual(before, p.canonical(self.packages))

  def test_resealed_frame_corruption_rejected(self):
    fs = h.clone(self.fs)
    fs['frames'][120]['candidate']['applied_torque'] += 0.1
    with self.assertRaisesRegex(ValueError, 'PAIR_FRAME_PHASE_VALUE_OR_METADATA_DRIFT'):
      a.validate(q.verify(q.seal({k: v for k, v in fs.items() if k != 'receipt_sha256'})), *self.packages)

  def test_resealed_metadata_corruption_rejected(self):
    fs = h.clone(self.fs)
    fs['evidence_tier'] = 'T2_EMPIRICAL_PLANT_CLOSED_LOOP'
    with self.assertRaisesRegex(ValueError, 'PAIR_FRAME_PHASE_VALUE_OR_METADATA_DRIFT'):
      a.validate(q.verify(q.seal({k: v for k, v in fs.items() if k != 'receipt_sha256'})), *self.packages)

  def test_repeat_exact_frameset(self):
    self.assertEqual(p.canonical(self.fs), p.canonical(a.convert(*self.packages)))

  def test_immutable_pages_exact_resume(self):
    pair = q.pair(*self.packages)
    with tempfile.TemporaryDirectory() as folder:
      catalog.persist_run(folder, 'SG_A', 'driver_events', self.packages, pair, self.fs)
      root = Path(folder)
      before = {str(f.relative_to(root)): p.sha(f.read_bytes()) for f in root.rglob('*.json')}
      catalog.persist_run(folder, 'SG_A', 'driver_events', self.packages, pair, self.fs)
      self.assertEqual(before, {str(f.relative_to(root)): p.sha(f.read_bytes()) for f in root.rglob('*.json')})
      self.assertEqual(len(list((root / 'SG_A' / 'driver_events').glob('page-*.json'))), 8)

  def test_page_drift_rejected(self):
    pair = q.pair(*self.packages)
    with tempfile.TemporaryDirectory() as folder:
      catalog.persist_run(folder, 'SG_A', 'driver_events', self.packages, pair, self.fs)
      root = Path(folder)
      path = root / 'SG_A' / 'driver_events' / 'page-000.json'
      path.write_bytes(path.read_bytes() + b' ')
      with self.assertRaises(ValueError):
        catalog.persist_run(folder, 'SG_A', 'driver_events', self.packages, pair, self.fs)

  def test_symlink_rejected(self):
    with tempfile.TemporaryDirectory() as folder:
      path = Path(folder) / 'link'
      path.symlink_to(folder, target_is_directory=True)
      with self.assertRaises(ValueError):
        catalog.persist_run(path, 'SG_A', 'driver_events', self.packages, q.pair(*self.packages), self.fs)

  def test_stale_atomic_rejected(self):
    with tempfile.TemporaryDirectory() as folder:
      path = Path(folder) / 'result.json'
      path.with_name('result.json.atomic').write_bytes(b'{}')
      with self.assertRaises(ValueError):
        catalog.persist_exact(path, q.seal({'schema': 'TEST'}))

  def test_catalog_never_adds_current(self):
    pair = q.pair(*self.packages)
    cat = catalog.catalog([{'kind': 'SG_A', 'scenario': 'driver_events', 'pair': pair, 'frameset': self.fs}])
    self.assertEqual([c['candidate_arm'] for c in cat['campaigns']], ['TA_B_V0', 'SG_A_V0'])
    self.assertTrue(all('CURRENT' not in str(c['candidate_arm']) for c in cat['campaigns']))

  def test_historical_verdict_not_recomputed(self):
    self.assertFalse(self.fs['verdict_recomputed'])
    self.assertEqual(self.fs['historical_verdict'], 'SG_CLOSED_LOOP_TRADEOFF_ONLY')

  def test_external_store_only(self):
    for store in (
      '.',
      str(Path(__file__).resolve().parents[1]),
      str(Path('/') / 'mnt' / 'd' / 'carrotlog' / 'test'),
      str(Path('/') / 'mnt' / 'd' / 'CarrotLogs' / 'test'),
    ):
      with self.assertRaises(ValueError):
        h.store_path(store)
