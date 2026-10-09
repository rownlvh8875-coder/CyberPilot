"""User-reported mean is useful evidence, never a complete calibration."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from openpilot.tools.cyber_autotune import camera_calibration_evidence as c
from openpilot.tools.cyber_autotune import coarse_camera_height_diagnostic as coarse
from openpilot.tools.cyber_autotune import physical_calibration_wizard as w
from openpilot.tools.cyber_autotune import physical_projection_uncertainty as u
from openpilot.tools.cyber_autotune.native_protocol import canonical, digest

try:
  from openpilot.tools.cyber_autotune import physical_height_observation as h
except ImportError:
  h = None


class TestPhysicalHeightObservation(unittest.TestCase):
  def setUp(self):
    self.assertIsNotNone(h, 'Physical observation implementation required')

  def test_exact_physical_mean_and_reported_provenance(self):
    o = h.observation()
    self.assertEqual(o['value_m'], 1.385)
    self.assertTrue(o['physical_measurement'])
    self.assertEqual(o['source'], 'USER_REPORTED_REPEATED_PHYSICAL_MEASUREMENT')
    self.assertEqual(o['status'], 'PHYSICAL_HEIGHT_OBSERVATION_RECORDED')
    for key in ('coarse_prior', 'model_derived', 'liveCalibration_derived', 'candidate_derived'):
      self.assertIs(o[key], False)

  def test_uncertainty_and_unprovided_details_remain_pending(self):
    o = h.observation()
    self.assertEqual(o['uncertainty_status'], 'CALIBRATION_UNCERTAINTY_PENDING')
    for key in ('measurement_uncertainty', 'individual_measurements_m', 'repetition_count', 'instrument', 'measurement_timestamp', 'operator_id'):
      self.assertIsNone(o[key])

  def test_coarse_history_and_range_unchanged(self):
    before = coarse.height_prior()
    x = h.consistency(h.observation())
    self.assertEqual(x['coarse_nominal_m'], 1.40)
    self.assertAlmostEqual(x['delta_physical_minus_coarse_m'], -0.015)
    self.assertTrue(x['within_historical_diagnostic_range'])
    self.assertFalse(x['coarse_prior_validated'])
    self.assertEqual(before, coarse.height_prior())
    self.assertEqual(coarse.HEIGHT_GRID_M, (1.33, 1.35, 1.375, 1.40, 1.425, 1.45, 1.47))

  def test_higher_provenance_selection_is_diagnostic_only(self):
    x = h.geometry_context(h.observation())
    self.assertEqual(x['selected_height_m'], 1.385)
    self.assertEqual(x['height_role'], 'PHYSICAL_HEIGHT_OBSERVATION')
    self.assertEqual(x['orientation']['role'], 'MODEL_DERIVED_EXTRINSICS_PRIOR')
    self.assertEqual(x['orientation']['reported_deg'], [0.0, 2.34, 0.2])
    self.assertEqual(x['mount_y']['declaration'], 'USER_DECLARED_APPROX_CENTER_MOUNT')
    self.assertFalse(x['independent_calibration_validated'])

  def test_modified_or_promoted_observation_rejected(self):
    for key, value in (('value_m', 1.40), ('measurement_uncertainty', 0.01), ('reference_promotable', True), ('model_derived', True)):
      o = copy.deepcopy(h.observation())
      o.pop('receipt_sha256')
      o[key] = value
      with self.assertRaises(ValueError):
        h.geometry_context(c.seal(o))

  def test_height_cannot_enter_strict_admission(self):
    o = h.observation()
    self.assertEqual(c.admit(o)['status'], 'CALIBRATION_EVIDENCE_REJECTED')
    with self.assertRaises(ValueError):
      c.validate_admitted(o)

  def test_no_meter_results_or_registration_promotion(self):
    x = h.readiness(h.observation())
    self.assertIsNone(x['meter_results'])
    self.assertEqual(x['pixel_registration_status'], 'PIXEL_GEOMETRY_REGISTRATION_PARTIAL')
    for blocker in ('CALIBRATION_UNCERTAINTY_PENDING', 'INDEPENDENT_CALIBRATION_VALIDATION_PENDING',
                    'PIXEL_GEOMETRY_REGISTRATION_PENDING', 'METRIC_CALIBRATION_UNAVAILABLE', 'INDEPENDENT_REFERENCE_UNAVAILABLE'):
      self.assertIn(blocker, x['blockers'])
    self.assertIsNone(u.report(None, None, None)['meter_results'])

  def test_sensitivity_additive_deterministic_with_same_coarse_rays(self):
    x = h.sensitivity(h.observation())
    self.assertEqual(x, h.sensitivity(h.observation()))
    self.assertEqual(x['historical_height_grid_m'], list(coarse.HEIGHT_GRID_M))
    self.assertEqual({row['height_m'] for row in x['observed_mean_rows']}, {1.385})
    self.assertEqual(len(x['observed_mean_rows']), 4)
    for old, new in zip(x['coarse_nominal_rows'], x['observed_mean_rows'], strict=True):
      self.assertEqual(old['fixed_normalized_optical_uv'], new['fixed_normalized_optical_uv'])
      self.assertAlmostEqual(new['forward_m'] / old['forward_m'], 1.385 / 1.40)
    self.assertIsNone(x['detector_meter_error'])
    self.assertIsNone(x['total_conservative_uncertainty_m'])

  def test_target_comparison_does_not_constrain_pose_or_invent_threshold(self):
    x = h.target_height_consistency(h.observation(), 1.6)
    self.assertEqual(x['solved_height_m'], 1.6)
    self.assertIsNone(x['warning'])
    self.assertIsNone(x['declared_diagnostic_discrepancy_bound_m'])
    y = h.target_height_consistency(h.observation(), 1.6, discrepancy_bound_m=0.1)
    self.assertEqual(y['warning'], 'HEIGHT_POSE_CONSISTENCY_WARNING')
    self.assertFalse(y['solver_constrained'])
    for v in (0, -1, float('nan'), True):
      with self.assertRaises(ValueError):
        h.target_height_consistency(h.observation(), v)

  def test_observation_deterministic_receipt(self):
    o = h.observation()
    core = dict(o)
    core.pop('receipt_sha256')
    self.assertEqual(o['receipt_sha256'], digest(canonical(core)))
    self.assertEqual(o, h.observation())

  def test_sealed_vehicle_private_firewall(self):
    for x in (h.observation(), h.readiness(h.observation()), h.geometry_context(h.observation()), h.sensitivity(h.observation())):
      for key in ('qualification_allowed', 'reference_promotable', 'sealed_reference_allowed', 'vehicle_activation_allowed', 'private_input_allowed'):
        self.assertIs(x[key], False)

  def test_wizard_blank_until_explicit_import_and_pending_after_restart(self):
    with tempfile.TemporaryDirectory() as tmp:
      root = Path(tmp) / 'wizard'
      session = w.MeasurementSession(root, scope='TEST_ONLY')
      self.assertIsNone(session.draft()['observations']['height_m']['value'])
      s = session.load_height_observation()
      row = s['draft']['observations']['height_m']
      self.assertEqual(row['value'], 1.385)
      self.assertEqual(row['unit'], 'm')
      self.assertIn(h.observation()['receipt_sha256'], row['note'])
      for key in ('uncertainty', 'uncertainty_unit', 'method', 'instrument_type', 'instrument_resolution'):
        self.assertIsNone(row[key])
      self.assertEqual(w.MeasurementSession(root, scope='TEST_ONLY').draft(), s['draft'])
      self.assertFalse(session.preflight(s['draft'])['valid'])
      with self.assertRaises(ValueError):
        session.admit()

  def test_explicit_import_does_not_reuse_stale_bound_or_clear_other_observations(self):
    with tempfile.TemporaryDirectory() as tmp:
      session = w.MeasurementSession(Path(tmp) / 'wizard', scope='TEST_ONLY')
      d = w.blank_draft()
      d['observations']['height_m'].update(value=1.4, uncertainty=0.01, instrument_type='TAPE_MEASURE')
      d['general']['note'] = 'Preserve unrelated draft'
      session.save_draft(d)
      s = session.load_height_observation()
      self.assertIsNone(s['draft']['observations']['height_m']['uncertainty'])
      self.assertEqual(s['draft']['general']['note'], d['general']['note'])

  def test_import_cannot_mutate_admitted_session(self):
    from openpilot.tools.cyber_autotune.tests.test_physical_calibration_wizard import filled
    with tempfile.TemporaryDirectory() as tmp:
      session = w.MeasurementSession(Path(tmp) / 'wizard', scope='TEST_ONLY')
      session.save_draft(filled(session))
      receipt = session.admit()
      with self.assertRaises(ValueError):
        session.load_height_observation()
      self.assertEqual(session.package(), receipt)

  def test_running_source_drift_cannot_mint_new_observation_receipt(self):
    original = Path.read_bytes
    def changed(path):
      return b'changed source on disk' if path == Path(h.__file__) else original(path)
    with patch.object(Path, 'read_bytes', changed):
      with self.assertRaises(ValueError):
        h.observation()
