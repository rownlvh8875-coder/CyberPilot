"""Constructed TEST_ONLY workflow; never actual camera measurements."""

import copy
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from openpilot.tools.cyber_autotune import camera_calibration_evidence as c
from openpilot.tools.cyber_autotune.native_protocol import canonical, digest
from openpilot.tools.cyber_autotune.tests.test_camera_calibration_evidence import fixture

try:
  from openpilot.tools.cyber_autotune import physical_calibration_wizard as w
except ImportError:
  w = None


def filled(session):
  evidence = session.attach(b'Explicit constructed stationary survey and metrology evidence TEST_ONLY')
  e = evidence['opaque_id']
  draft = w.blank_draft()
  draft['camera'].update(device='mici', hardware_generation='comma4', sensor='os04c10', view='narrow_road', unit_id='TEST_CAMERA', hardware_evidence_id=e)
  draft['general'].update(
    version_id='TEST_V1',
    operator_id='TEST_OPERATOR',
    timestamp='2026-10-08T00:00:00Z',
    method='OPTICAL_CENTER_SURVEY',
    note='TEST ONLY',
    independence_confirmed=True,
  )
  original, i = fixture()
  obs = {
    **original['observations'],
    'ground_vertical_m': original['ground_surface']['vertical_deviation'],
    'distortion_residual_px': original['distortion']['residual'],
  }
  for key, x in obs.items():
    unit = x['unit']
    value = x['value']
    bound = x['uncertainty']['value']
    if unit == 'rad':
      unit = 'deg'
      value = math.degrees(value)
      bound = math.degrees(bound)
    draft['observations'][key].update(
      value=value,
      unit=unit,
      uncertainty=bound,
      uncertainty_unit=unit,
      method=x['method'] if key in w.STATIC_KEYS else 'OPTICAL_CENTER_SURVEY',
      source_kind='STATIC_SOURCE' if key.endswith('_px') and key != 'distortion_residual_px' else 'PHYSICAL_OBSERVATION',
      tier='TIER_B',
      instrument_type='INDEPENDENT_METROLOGY_RECORD',
      instrument_resolution=0.0001,
      instrument_unit=unit,
      source_evidence_id=e,
      instrument_evidence_id=e,
      uncertainty_evidence_id=e,
      uncertainty_method='METROLOGY_REVIEW',
      note='',
    )
  draft['mount'].update(datum_description='Independently surveyed vehicle datum TEST', evidence_id=e, convention_confirmed=True)
  draft['ground'].update(surface_method='INDEPENDENT_LEVEL_SURVEY', slope_bound_deg=0.1, evidence_id=e)
  draft['distortion'].update(state='INDEPENDENTLY_BOUNDED_UNDISTORTED_RESIDUAL', evidence_id=e)
  return draft


class TestWizard(unittest.TestCase):
  def setUp(self):
    self.assertIsNotNone(w, 'Missing physical calibration wizard')
    self.temp = tempfile.TemporaryDirectory()
    self.root = Path(self.temp.name) / 'session'
    self.session = w.MeasurementSession(self.root, scope='TEST_ONLY')

  def tearDown(self):
    self.temp.cleanup()

  def test_no_measurement_defaults(self):
    d = self.session.state()['draft']
    for row in d['observations'].values():
      for key in ('value', 'unit', 'uncertainty', 'method', 'source_kind', 'tier'):
        self.assertIsNone(row[key])
    self.assertEqual(self.session.state()['readiness'], 'CALIBRATION_MEASUREMENT_PENDING')
    self.assertEqual(d['camera']['sensor'], None)
    self.assertEqual(d['distortion']['state'], None)

  def test_draft_editable_and_restart(self):
    d = w.blank_draft()
    d['general']['note'] = 'First'
    self.session.save_draft(d)
    d['general']['note'] = 'Second'
    self.session.save_draft(d)
    self.assertEqual(w.MeasurementSession(self.root, scope='TEST_ONLY').state()['draft'], d)

  def test_pending_ground_and_distortion(self):
    x = self.session.preflight(w.blank_draft())
    self.assertFalse(x['valid'])
    self.assertIn('GROUND_SURVEY_PENDING', x['errors'])
    self.assertIn('DISTORTION_VALIDATION_PENDING', x['errors'])

  def test_authoritative_admission_and_no_validation_promotion(self):
    d = filled(self.session)
    x = self.session.preflight(d)
    self.assertTrue(x['valid'], x)
    c.validate_admitted(x['admission'])
    self.assertFalse(x['admission']['metric_calibration_validated'])
    self.assertFalse(x['admission']['reference_promotable'])

  def test_degrees_radians_and_original_input_bound(self):
    d = filled(self.session)
    x = self.session.preflight(d)
    for key in ('pitch_rad', 'roll_rad', 'yaw_rad'):
      self.assertEqual(x['admission']['measurement']['observations'][key]['value'], math.radians(d['observations'][key]['value']))
    self.session.save_draft(d)
    p = self.session.admit()
    self.assertEqual(p['original_input'], d)
    self.assertEqual(p['original_input_sha256'], digest(canonical(d)))

  def test_units_rejected(self):
    for unit in ('meters', '°', 'mm', None):
      d = filled(self.session)
      d['observations']['height_m']['unit'] = unit
      self.assertFalse(self.session.preflight(d)['valid'])

  def test_uncertainty_required(self):
    for value in (None, 0, -1, float('inf')):
      d = filled(self.session)
      d['observations']['pitch_rad']['uncertainty'] = value
      self.assertFalse(self.session.preflight(d)['valid'])

  def test_geometry_and_source_mismatch(self):
    for key, value in (('height_m', -1), ('pitch_rad', 100)):
      d = filled(self.session)
      d['observations'][key]['value'] = value
      self.assertFalse(self.session.preflight(d)['valid'])
    d = filled(self.session)
    d['camera']['sensor'] = 'unknown'
    self.assertFalse(self.session.preflight(d)['valid'])

  def test_forbidden_source_categories(self):
    for source in ('modelV2', 'cameraOdometry', 'liveCalibration', 'calibrationd', 'candidate', 'planner'):
      d = filled(self.session)
      d['observations']['yaw_rad']['source_kind'] = source
      self.assertFalse(self.session.preflight(d)['valid'])

  def test_phone_tier_rejected(self):
    d = filled(self.session)
    d['observations']['roll_rad']['tier'] = 'TIER_C'
    self.assertFalse(self.session.preflight(d)['valid'])

  def test_acknowledgement_required(self):
    d = filled(self.session)
    d['general']['independence_confirmed'] = False
    self.assertFalse(self.session.preflight(d)['valid'])

  def test_static_intrinsics_not_measured(self):
    d = filled(self.session)
    x = self.session.preflight(d)
    self.assertEqual(x['admission']['intrinsics']['distortion_model'], 'UNKNOWN_NOT_ASSUMED_ZERO')
    for key in ('fx_px', 'fy_px', 'cx_px', 'cy_px'):
      self.assertEqual(x['admission']['measurement']['observations'][key]['provenance']['role'], 'STATIC_INTRINSICS')
    d['observations']['fx_px']['source_kind'] = 'PHYSICAL_OBSERVATION'
    self.assertFalse(self.session.preflight(d)['valid'])

  def test_admitted_immutable_duplicate_and_restart(self):
    d = filled(self.session)
    self.session.save_draft(d)
    p = self.session.admit()
    other = w.MeasurementSession(self.root, scope='TEST_ONLY')
    self.assertEqual(other.package(), p)
    with self.assertRaises(ValueError):
      other.admit()
    with self.assertRaises(ValueError):
      other.save_draft(d)
    with self.assertRaises(ValueError):
      other.attach(b'Additional evidence')

  def test_attachment_hash_size_no_filename(self):
    e = self.session.attach(b'local explicit TEST evidence')
    self.assertEqual(e['sha256'], digest(b'local explicit TEST evidence'))
    self.assertEqual(e['byte_size'], 28)
    self.assertEqual(set(e), {'opaque_id', 'sha256', 'byte_size', 'status'})
    self.assertEqual(self.session.attach(b'local explicit TEST evidence'), e)

  def test_attachment_corruption_blocks_admission(self):
    d = filled(self.session)
    self.session.save_draft(d)
    evidence = self.session.state()['attachments'][0]
    (self.root / 'evidence' / f"{evidence['opaque_id']}.bin").write_bytes(b'corrupt')
    with self.assertRaises(ValueError):
      self.session.admit()

  def test_unknown_evidence_reference(self):
    d = filled(self.session)
    d['observations']['height_m']['source_evidence_id'] = 'f' * 64
    self.assertFalse(self.session.preflight(d)['valid'])

  def test_public_summary_redacts_values_and_personal_notes(self):
    d = filled(self.session)
    d['general']['note'] = 'PERSONAL_PATH_NEVER_PUBLISH'
    self.session.save_draft(d)
    self.session.admit()
    s = self.session.public_summary()
    for key in ('original_input', 'camera', 'observations', 'note', 'local_path', 'operator_id'):
      self.assertNotIn(key, s)
    self.assertNotIn('PERSONAL_PATH', str(s))

  def test_root_outside_repository_and_symlink_guard(self):
    with self.assertRaises(ValueError):
      w.MeasurementSession(c.ROOT / 'wizard-artifacts', scope='TEST_ONLY')
    self.root.rename(self.root.with_name('detached'))
    self.root.symlink_to(self.root.with_name('detached'), target_is_directory=True)
    with self.assertRaises(ValueError):
      self.session.state()

  def test_unknown_keys_and_stale_binding_rejected(self):
    d = w.blank_draft()
    d['model_import'] = 'forbidden'
    with self.assertRaises(ValueError):
      self.session.save_draft(d)
    path = self.root / 'binding.json'
    path.write_text('{}')
    with self.assertRaises(ValueError):
      self.session.state()

  def test_recovery_after_prepared_before_receipt(self):
    d = filled(self.session)
    self.session.save_draft(d)
    with patch.object(c.ImmutableCalibrationStore, 'save', side_effect=RuntimeError('TEST crash')):
      with self.assertRaises(RuntimeError):
        self.session.admit()
    other = w.MeasurementSession(self.root, scope='TEST_ONLY')
    self.assertEqual(other.state()['status'], 'ADMISSION_INTERRUPTED_PENDING_RECOVERY')
    with self.assertRaises(ValueError):
      other.save_draft(d)
    p = other.recover()
    self.assertEqual(p['admission']['status'], 'CALIBRATION_EVIDENCE_ADMITTED')
    self.assertFalse(p['independent_calibration_validated'])

  def test_receipt_corruption_and_draft_conflict(self):
    d = filled(self.session)
    self.session.save_draft(d)
    self.session.admit()
    (self.root / 'admitted.json').write_text('{}')
    with self.assertRaises(ValueError):
      self.session.package()

  def test_current_tool_change_blocks_running_session(self):
    with patch.object(w, 'identity', return_value='f' * 64):
      with self.assertRaises(ValueError):
        self.session.state()

  def test_mutations_guard_before_writer_lease(self):
    self.root.rename(self.root.with_name('detached'))
    self.root.symlink_to(self.root.with_name('detached'), target_is_directory=True)
    with patch.object(w.s, 'writer_lease', side_effect=AssertionError('Writer reached substituted root')):
      for action in (lambda: self.session.save_draft(w.blank_draft()), lambda: self.session.attach(b'TEST'), self.session.admit, self.session.recover):
        with self.assertRaises(ValueError):
          action()

  def test_phone_instrument_cannot_claim_tier_b(self):
    for instrument in ('PHONE_IMU', 'phone app', 'INFORMAL'):
      d = filled(self.session)
      d['observations']['roll_rad']['instrument_type'] = instrument
      self.assertFalse(self.session.preflight(d)['valid'])

  def test_instrument_dimension_must_match_observation(self):
    for key, unit in (('height_m', 'deg'), ('roll_rad', 'm'), ('fx_px', 'mm')):
      d = filled(self.session)
      d['observations'][key]['instrument_unit'] = unit
      self.assertFalse(self.session.preflight(d)['valid'])

  def test_individual_target_method_requires_actual_target_geometry(self):
    d = filled(self.session)
    d['observations']['roll_rad']['method'] = 'SURVEYED_CHECKERBOARD'
    self.assertFalse(self.session.preflight(d)['valid'])

  def test_dangling_marker_symlink_cannot_be_overwritten(self):
    (self.root / 'admitted.json').symlink_to(self.root / 'missing-marker')
    with self.assertRaises(ValueError):
      self.session.save_draft(w.blank_draft())

  def test_surveyed_target_requires_and_binds_explicit_geometry(self):
    d = filled(self.session)
    e = d['camera']['hardware_evidence_id']
    d['observations']['roll_rad']['method'] = 'SURVEYED_CHECKERBOARD'
    d['target'].update(
      width_m=0.16,
      height_m=0.12,
      distance_m=5.0,
      absolute_bound_m=0.002,
      geometry_note='TEST_ONLY surveyed target-to-vehicle geometry',
      target_evidence_id=e,
      geometry_evidence_id=e,
    )
    a = self.session.preflight(d)
    self.assertTrue(a['valid'])
    changed = copy.deepcopy(d)
    changed['target']['absolute_bound_m'] = 0
    self.assertFalse(self.session.preflight(changed)['valid'])
    changed = copy.deepcopy(d)
    changed['target']['geometry_evidence_id'] = None
    self.assertFalse(self.session.preflight(changed)['valid'])
