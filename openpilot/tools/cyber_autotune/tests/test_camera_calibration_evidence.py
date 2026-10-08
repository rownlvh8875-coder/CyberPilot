"""Only constructed TEST_ONLY measurements, never actual physical evidence."""

import copy
from pathlib import Path
import tempfile
import unittest
from openpilot.tools.cyber_autotune.lane_tail_report import seal, unseal

try:
  from openpilot.tools.cyber_autotune import camera_calibration_evidence as c
except ImportError:
  c = None


def fixture(sensor='os04c10'):
  camera = {
    'device': 'mici',
    'hardware_generation': 'comma4',
    'sensor': sensor,
    'view': 'narrow_road',
    'unit_id_sha256': 'a' * 64,
    'hardware_evidence_sha256': 'b' * 64,
  }
  i = c.intrinsics(camera)
  vals = {
    'height_m': 1.5,
    'mount_x_m': 0.1,
    'mount_y_m': 0.02,
    'pitch_rad': 0.04,
    'roll_rad': 0.01,
    'yaw_rad': 0.02,
    'fx_px': i['matrix'][0][0],
    'fy_px': i['matrix'][1][1],
    'cx_px': i['matrix'][0][2],
    'cy_px': i['matrix'][1][2],
  }

  def obs(value, unit, bound):
    return {
      'value': value,
      'unit': unit,
      'method': 'SURVEYED_STATIONARY_TARGET',
      'provenance': {
        'role': 'INDEPENDENT_PHYSICAL',
        'source_sha256': 'c' * 64,
        'instrument_sha256': 'd' * 64,
        'model_outputs_used': False,
        'candidate_outputs_used': False,
      },
      'uncertainty': {'kind': 'ABSOLUTE_BOUND', 'value': bound, 'unit': unit, 'method': 'METROLOGY_REVIEW', 'provenance_sha256': 'e' * 64},
    }

  m = {
    'schema': 'INDEPENDENT_PHYSICAL_CAMERA_MEASUREMENT_V1',
    'scope': 'TEST_ONLY',
    'measurement_id_sha256': 'f' * 64,
    'camera': camera,
    'timestamp': '2026-10-08T00:00:00Z',
    'operator_id_sha256': '1' * 64,
    'method': 'SURVEYED_STATIONARY_TARGET',
    'human_acknowledgement': True,
    'intrinsics_sha256': i['receipt_sha256'],
    'schema_sha256': c.SCHEMA_SHA,
    'tool_sha256': c.identity(),
    'observations': {
      k: obs(v, 'm' if k.endswith('_m') else 'rad' if k.endswith('_rad') else 'px', 0.001 if not k.endswith('_px') else 0.1) for k, v in vals.items()
    },
    'mounting_reference': {'definition': 'SURVEYED_VEHICLE_ORIGIN_TO_OPTICAL_CENTER', 'convention': c.VEHICLE_FRAME, 'evidence_sha256': '2' * 64},
    'ground_surface': {'assumption': 'LOCALLY_SURVEYED_PLANAR_GROUND', 'vertical_deviation': obs(0.0, 'm', 0.002)},
    'distortion': {'state': 'INDEPENDENTLY_BOUNDED_UNDISTORTED_RESIDUAL', 'residual': obs(0.0, 'px', 0.1)},
  }
  for key in ('fx_px', 'fy_px', 'cx_px', 'cy_px'):
    m['observations'][key]['provenance']['role'] = 'STATIC_INTRINSICS'
    m['observations'][key]['provenance']['source_sha256'] = c.CAMERA_SHA
    m['observations'][key]['method'] = 'PINNED_HARDWARE_NOMINAL'
  return m, i


class TestCalibration(unittest.TestCase):
  def setUp(self):
    self.assertIsNotNone(c, 'Missing physical measurement admission')
    self.m, self.i = fixture()

  def test_none_stays_pending_without_numbers(self):
    x = c.admit(None)
    self.assertEqual(x['status'], 'CALIBRATION_MEASUREMENT_PENDING')
    self.assertIsNone(x['measurement'])
    self.assertFalse(x['reference_promotable'])

  def test_static_intrinsics_identity_and_unknown_distortion(self):
    self.assertEqual(self.i['matrix'][0][0], 1141.5)
    self.assertEqual(self.i['resolution_wh'], [1344, 760])
    self.assertEqual(self.i['provenance_role'], 'STATIC_INTRINSICS')
    self.assertEqual(self.i['distortion_model'], 'UNKNOWN_NOT_ASSUMED_ZERO')
    self.assertEqual(self.i, c.intrinsics(self.m['camera']))
    for sensor in ('ar0231', 'ox03c10'):
      _, i = fixture(sensor)
      self.assertEqual(i['matrix'][0][0], 2648.0)
    bad = copy.deepcopy(self.m['camera'])
    bad['sensor'] = 'unknown'
    with self.assertRaises(ValueError):
      c.intrinsics(bad)

  def test_admitted_is_structural_not_metrology_qualification(self):
    x = c.admit(self.m, self.i)
    self.assertEqual(x['status'], 'CALIBRATION_EVIDENCE_ADMITTED')
    self.assertFalse(x['metric_calibration_validated'])
    self.assertFalse(x['reference_promotable'])
    c.validate_admitted(x)

  def test_missing_uncertainty_or_provenance_rejected(self):
    for field in ('uncertainty', 'provenance', 'method'):
      m = copy.deepcopy(self.m)
      m['observations']['height_m'].pop(field)
      self.assertEqual(c.admit(m, self.i)['status'], 'CALIBRATION_EVIDENCE_REJECTED')

  def test_model_derived_not_physical(self):
    for change in ('role', 'model', 'candidate'):
      m = copy.deepcopy(self.m)
      o = m['observations']['pitch_rad']['provenance']
      if change == 'role':
        o['role'] = 'MODEL_DERIVED_EXTRINSICS'
      else:
        o['model_outputs_used' if change == 'model' else 'candidate_outputs_used'] = True
      self.assertEqual(c.admit(m, self.i)['status'], 'CALIBRATION_EVIDENCE_REJECTED')

  def test_units_nonfinite_impossible_or_unknown_method_rejected(self):
    for field, value in [('value', float('nan')), ('value', float('inf')), ('value', -1), ('unit', 'cm'), ('method', 'LIVE_CALIBRATION')]:
      m = copy.deepcopy(self.m)
      m['observations']['height_m'][field] = value
      self.assertEqual(c.admit(m, self.i)['status'], 'CALIBRATION_EVIDENCE_REJECTED')
    for angle in ('pitch_rad', 'roll_rad', 'yaw_rad'):
      m = copy.deepcopy(self.m)
      m['observations'][angle]['unit'] = 'deg'
      self.assertEqual(c.admit(m, self.i)['status'], 'CALIBRATION_EVIDENCE_REJECTED')

  def test_device_source_and_focal_mismatch_rejected(self):
    for change in ('device', 'source', 'focal', 'resolution'):
      m = copy.deepcopy(self.m)
      i = unseal(copy.deepcopy(self.i))
      if change == 'device':
        m['camera']['sensor'] = 'ar0231'
      if change == 'source':
        i['source_sha256'] = 'f' * 64
      if change == 'focal':
        m['observations']['fx_px']['value'] += 1
      if change == 'resolution':
        i['resolution_wh'][0] += 1
      self.assertEqual(c.admit(m, seal(i))['status'], 'CALIBRATION_EVIDENCE_REJECTED')

  def test_unknown_zero_or_statistical_uncertainty_is_not_absolute_bound(self):
    for field, value in [('value', None), ('value', 0), ('value', -1), ('value', float('inf')), ('kind', 'P95'), ('unit', 'deg')]:
      m = copy.deepcopy(self.m)
      m['observations']['pitch_rad']['uncertainty'][field] = value
      self.assertEqual(c.admit(m, self.i)['status'], 'CALIBRATION_EVIDENCE_REJECTED')

  def test_immutable_store_duplicate_conflict_and_restart(self):
    with tempfile.TemporaryDirectory() as tmp:
      store = c.ImmutableCalibrationStore(Path(tmp) / 'local-measurements')
      x = store.save(self.m, self.i)
      self.assertEqual(c.ImmutableCalibrationStore(Path(tmp) / 'local-measurements').read(), x)
      with self.assertRaises(ValueError):
        store.save(self.m, self.i)
      m = copy.deepcopy(self.m)
      m['observations']['height_m']['value'] += 0.1
      with self.assertRaises(ValueError):
        store.save(m, self.i)

  def test_pending_projection_budget_is_symbolic_and_null(self):
    x = c.projection_budget(c.admit(None), None)
    self.assertEqual([r['distance_m'] for r in x['rows']], [5.0, 10.0, 20.0, 30.0])
    self.assertTrue(all(r['total_conservative_uncertainty_m'] is None for r in x['rows']))
    self.assertFalse(x['reference_promotable'])

  def test_budget_keeps_components_and_never_certifies_remainder(self):
    x = c.projection_budget(c.admit(self.m, self.i), {'u_px': 1.0, 'v_px': 1.0, 'source_sha256': 'a' * 64, 'kind': 'ABSOLUTE_BOUND'})
    self.assertEqual(len(x['rows']), 4)
    for row in x['rows']:
      for key in ('detector_term_m', 'intrinsic_term_m', 'height_term_m', 'pitch_term_m', 'roll_term_m', 'yaw_term_m', 'ground_plane_term_m'):
        self.assertGreaterEqual(row[key], 0)
      self.assertIsNone(row['total_conservative_uncertainty_m'])
    self.assertEqual(x, c.projection_budget(c.admit(self.m, self.i), {'u_px': 1.0, 'v_px': 1.0, 'source_sha256': 'a' * 64, 'kind': 'ABSOLUTE_BOUND'}))

  def test_receipt_mutation_and_fake_status_rejected(self):
    x = unseal(c.admit(self.m, self.i))
    x['metric_calibration_validated'] = True
    with self.assertRaises(ValueError):
      c.validate_admitted(seal(x))
    x = unseal(c.admit(self.m, self.i))
    x['measurement']['observations']['height_m']['value'] += 1
    with self.assertRaises(ValueError):
      c.validate_admitted(seal(x))

  def test_input_mutation_does_not_change_admitted_receipt(self):
    x = c.admit(self.m, self.i)
    before = copy.deepcopy(x)
    self.m['observations']['height_m']['value'] = 1.8
    self.i['camera']['unit_id_sha256'] = 'f' * 64
    self.assertEqual(x, before)

  def test_euler_bound_contributions_match_fixed_pixel_finite_difference(self):
    from openpilot.tools.cyber_autotune import lane_projection_diagnostics as p
    import numpy as np

    k = np.array(self.i['matrix'])
    r, center, _, _ = c.pose(self.m)
    pixel = k @ (r.T @ (np.array([10.0, 0.0, 0.0]) - center))
    pixel = pixel[:2] / pixel[2]
    budget = c.projection_budget(c.admit(self.m, self.i), {'u_px': 1.0, 'v_px': 1.0, 'source_sha256': 'a' * 64, 'kind': 'ABSOLUTE_BOUND'})
    row = budget['rows'][1]
    step = 1e-6
    for key in ('roll', 'pitch', 'yaw'):
      plus = copy.deepcopy(self.m)
      minus = copy.deepcopy(self.m)
      plus['observations'][key + '_rad']['value'] += step
      minus['observations'][key + '_rad']['value'] -= step
      rp, cp, _, _ = c.pose(plus)
      rm, cm, _, _ = c.pose(minus)
      derivative = (p.ground_projection(k, rp, cp, pixel)['lateral_left_m'] - p.ground_projection(k, rm, cm, pixel)['lateral_left_m']) / (2 * step)
      self.assertAlmostEqual(row[key + '_term_m'], abs(derivative) * self.m['observations'][key + '_rad']['uncertainty']['value'], places=8)

  def test_pending_cannot_embed_unvalidated_localization_budget(self):
    with self.assertRaises(ValueError):
      c.projection_budget(c.admit(None), {'p95_px': 666.97})

  def test_root_substitution_rejected_on_read_and_save(self):
    with tempfile.TemporaryDirectory() as tmp:
      root = Path(tmp) / 'original'
      store = c.ImmutableCalibrationStore(root)
      store.save(self.m, self.i)
      replacement = c.ImmutableCalibrationStore(Path(tmp) / 'replacement')
      replacement.save(self.m, self.i)
      root.rename(Path(tmp) / 'original-detached')
      root.symlink_to(replacement.root, target_is_directory=True)
      with self.assertRaises(ValueError):
        store.read()
      with self.assertRaises(ValueError):
        store.save(self.m, self.i)

  def test_plain_directory_substitution_rejected(self):
    with tempfile.TemporaryDirectory() as tmp:
      root = Path(tmp) / 'original'
      store = c.ImmutableCalibrationStore(root)
      root.rename(Path(tmp) / 'original-detached')
      c.ImmutableCalibrationStore(root)
      with self.assertRaises(ValueError):
        store.save(self.m, self.i)
