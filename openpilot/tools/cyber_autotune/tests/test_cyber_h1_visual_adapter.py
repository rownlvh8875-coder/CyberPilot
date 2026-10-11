"""Adapter boundaries: pinned source, honest phases/nulls and immutable paging."""

from copy import deepcopy
import tempfile
from pathlib import Path
import unittest
from openpilot.tools.cyber_autotune import cyber_h1_visual_adapter as a
from openpilot.tools.cyber_autotune import cyber_h1_visual_catalog as cat
from openpilot.tools.cyber_autotune import cyber_lateral_h1_experiment as e
from openpilot.tools.cyber_autotune import empirical_plant_policy as p


class TestVisualAdapter(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    _, cls.package = e.run_once()
    cls.frameset = a.convert(cls.package)

  def test_exact_count_single_arm(self):
    f = self.frameset
    self.assertEqual(f['frame_count'], 800)
    self.assertEqual(f['arms'], ['UPSTREAM_BASELINE_CLOSED_LOOP'])
    self.assertFalse(f['comparison_ready'])
    self.assertEqual(f['duration_ns'], 8_000_000_000)

  def test_phase_map(self):
    row, frame = self.package['rows'][400], self.frameset['frames'][400]
    self.assertEqual(frame['actual_curvature_pre_step_1pm'], row['signals']['actual_curvature'])
    self.assertEqual(frame['curvature_post_step_1pm'], row['plant_output']['curvature'])
    self.assertEqual(frame['capture_time_ns'], 4_000_000_000)
    self.assertEqual(frame['completion_time_ns'], 4_010_000_000)
    self.assertEqual(frame['relative_time_s'], 4.0)
    self.assertEqual(frame['pose_x_post_step_m'], row['plant_output']['pose_x'])

  def test_null_preserved(self):
    f = self.frameset['frames'][0]
    for key in ('requested_pre_limit_torque', 'pre_limit_torque', 'torque_output_can', 'steering_angle_deg', 'steering_rate_deg_s', 'driver_torque'):
      self.assertIsNone(f[key])
      self.assertIn(key, f['unavailable'])
    self.assertIsNone(f['service_health']['carState']['valid'])

  def test_no_input_mutation_repeatability(self):
    before = p.canonical(self.package)
    self.assertEqual(p.canonical(self.frameset), p.canonical(a.convert(self.package)))
    self.assertEqual(before, p.canonical(self.package))

  def test_published_pin_required_by_default(self):
    f = deepcopy(self.package)
    f['receipt_sha256'] = '0' * 64
    with self.assertRaises(ValueError):
      a.convert(f)

  def test_source_drift(self):
    f = deepcopy(self.package)
    f['rows'][0]['signals']['actual_curvature'] += 1
    with self.assertRaises(ValueError):
      a.convert(f)

  def test_missing_rows(self):
    f = deepcopy(self.package)
    f['rows'].pop()
    with self.assertRaises(ValueError):
      a.convert(f)

  def test_fidelity_drift(self):
    f = deepcopy(self.package)
    f['binding']['tier'] = 'T2_EMPIRICAL_PLANT_CLOSED_LOOP'
    with self.assertRaises(ValueError):
      a.convert(f)

  def test_store_roundtrip_resume(self):
    with tempfile.TemporaryDirectory() as store:
      first = cat.persist(store, self.frameset)
      second = cat.persist(store, self.frameset)
      self.assertEqual(first, second)
      loaded = cat.load(store)
      self.assertEqual(p.canonical(loaded['frames']), p.canonical(self.frameset['frames']))
      self.assertEqual(len(loaded['pages']), 8)
      self.assertEqual(loaded['catalog']['runs'][0]['arm_names'], ['UPSTREAM_BASELINE_CLOSED_LOOP'])

  def test_page_drift_rejected(self):
    with tempfile.TemporaryDirectory() as store:
      cat.persist(store, self.frameset)
      path = Path(store) / 'page-000.json'
      path.write_bytes(b'{}')
      with self.assertRaises(ValueError):
        cat.load(store)
      with self.assertRaises(ValueError):
        cat.persist(store, self.frameset)

  def test_symlink_rejected(self):
    with tempfile.TemporaryDirectory() as store:
      alias = Path(store) / 'alias'
      alias.symlink_to(store, target_is_directory=True)
      with self.assertRaises(ValueError):
        cat.persist(alias, self.frameset)

  def test_repo_store_rejected(self):
    with self.assertRaises(ValueError):
      cat.persist(p.PUBLIC, self.frameset)

  def test_aggregate_not_full_source(self):
    with tempfile.TemporaryDirectory() as store:
      (Path(store) / 'cyber-lateral-h1-trace-v1.json').write_bytes(b'{}')
      with self.assertRaises(ValueError):
        a.load_source(store)

  def test_missing_source(self):
    with tempfile.TemporaryDirectory() as store:
      with self.assertRaisesRegex(ValueError, 'VISUAL_SOURCE_ROWS_UNAVAILABLE'):
        a.load_source(store)

  def test_resealed_frame_value_drift(self):
    fs = deepcopy(self.frameset)
    fs['frames'][400]['pose_x_post_step_m'] += 1
    fs['frames_sha256'] = p.sha(p.canonical(fs['frames']))
    fs.pop('receipt_sha256')
    fs = p.seal(fs)
    with self.assertRaises(ValueError):
      a.validate_frameset(fs)

  def test_resealed_metadata_drift(self):
    changes = {
      'verdict': 'ACCEPTED',
      'blockers': [],
      'unavailable_fields': {},
      'scenario': 'other',
      'run_id': '0' * 64,
      'source_sha256': '0' * 64,
      'dt_ns': 1,
      'origin_time_ns': 1,
      'coverage': {},
    }
    for key, value in changes.items():
      with self.subTest(key=key):
        fs = deepcopy(self.frameset)
        fs[key] = value
        fs.pop('receipt_sha256')
        with self.assertRaises(ValueError):
          a.validate_frameset(p.seal(fs))

  def test_metadata_integer_types(self):
    for key, value in (('origin_time_ns', False), ('opening_count', False), ('arm_count', True), ('frame_count', 800.0), ('dt_ns', 10000000.0)):
      with self.subTest(key=key):
        fs = deepcopy(self.frameset)
        fs[key] = value
        fs.pop('receipt_sha256')
        with self.assertRaises(ValueError):
          a.validate_frameset(p.seal(fs))

  def test_repartitioned_pages_rejected(self):
    with tempfile.TemporaryDirectory() as store:
      cat.persist(store, self.frameset)
      root = Path(store)
      manifest = cat.read_json(root, 'manifest.json')
      for i, rows in enumerate((self.frameset['frames'][:150], self.frameset['frames'][150:200])):
        page = cat.read_json(root, f'page-{i:03d}.json')
        page.update(frames=rows, count=len(rows), frames_sha256=p.sha(p.canonical(rows)))
        page.pop('receipt_sha256')
        page = p.seal(page)
        (root / f'page-{i:03d}.json').write_text(__import__('json').dumps(page, sort_keys=True, indent=2) + '\n')
        manifest['pages'][i]['receipt_sha256'] = page['receipt_sha256']
      manifest.pop('receipt_sha256')
      (root / 'manifest.json').write_text(__import__('json').dumps(p.seal(manifest), sort_keys=True, indent=2) + '\n')
      with self.assertRaises(ValueError):
        cat.load(root)

  def test_exact_file_bytes_resume(self):
    with tempfile.TemporaryDirectory() as store:
      cat.persist(store, self.frameset)
      path = Path(store) / 'page-000.json'
      before = path.read_bytes()
      path.write_bytes(before + b' ')
      with self.assertRaises(ValueError):
        cat.persist(store, self.frameset)
      self.assertEqual(path.read_bytes(), before + b' ')

  def test_interrupted_store_resume(self):
    with tempfile.TemporaryDirectory() as store:
      original = cat.persist(store, self.frameset)
      root = Path(store)
      (root / 'manifest.json').unlink()
      for i in range(3, 8):
        (root / f'page-{i:03d}.json').unlink()
      with self.assertRaises(ValueError):
        cat.load(root)
      self.assertEqual(cat.persist(root, self.frameset), original)

  def test_atomic_resume_and_stale_rejection(self):
    import json

    with tempfile.TemporaryDirectory() as store:
      root = Path(store)
      row = a.policy()
      expected = (json.dumps(row, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()
      (root / 'policy.json.atomic').write_bytes(expected)
      cat.persist(root, self.frameset)
      self.assertEqual((root / 'policy.json').read_bytes(), expected)
      self.assertFalse((root / 'policy.json.atomic').exists())
    with tempfile.TemporaryDirectory() as store:
      root = Path(store)
      (root / 'policy.json.atomic').write_bytes(b'{}')
      with self.assertRaises(ValueError):
        cat.persist(root, self.frameset)
      self.assertEqual((root / 'policy.json.atomic').read_bytes(), b'{}')

  def test_server_asset_source_drift(self):
    from unittest.mock import patch
    from openpilot.tools.cyber_autotune import cyber_h1_visual_server as server

    with tempfile.TemporaryDirectory() as store:
      cat.persist(store, self.frameset)
      changed = deepcopy(server.contract())
      changed['source_files']['cyber_h1_visual_server.py'] = '0' * 64
      changed.pop('receipt_sha256')
      with patch.object(server, 'contract', return_value=p.seal(changed)):
        with self.assertRaises(ValueError):
          cat.load(store)

  def test_raw_decoder_and_experiment_unneeded(self):
    from unittest.mock import patch

    with (
      patch.object(p, 'inventory', side_effect=AssertionError('RAW_ACCESS_FORBIDDEN')),
      patch.object(e, 'run_once', side_effect=AssertionError('EXPERIMENT_FORBIDDEN')),
    ):
      self.assertEqual(a.convert(self.package), self.frameset)

  def test_false_zero_fabrication_rejected(self):
    for field, value in (('driver_torque', 0), ('steering_rate_deg_s', 0.0), ('torque_output_can', False)):
      fs = deepcopy(self.frameset)
      fs['frames'][0][field] = value
      fs['frames_sha256'] = p.sha(p.canonical(fs['frames']))
      fs.pop('receipt_sha256')
      with self.assertRaises(ValueError):
        a.validate_frameset(p.seal(fs))
