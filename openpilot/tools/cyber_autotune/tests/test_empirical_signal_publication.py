import importlib
import unittest

from openpilot.tools.cyber_autotune import empirical_plant_policy as p


class TestSignalPublication(unittest.TestCase):
  def setUp(self):
    self.pub = importlib.import_module('openpilot.tools.cyber_autotune.empirical_signal_publication')

  def test_pinned_aggregate_receipts(self):
    self.assertGreaterEqual(len(self.pub.load()), 8)

  def test_executor_identity_immutable(self):
    self.pub.validate_sources()

  def test_wrong_scale_resealed_rejected(self):
    rows = self.pub.load()
    row = rows['empirical-command-bridge-v1.json']
    row['groups'][0]['steer_max'] = 384
    with self.assertRaises(ValueError):
      self.pub.validate_row('empirical-command-bridge-v1.json', p.seal({k: v for k, v in row.items() if k != 'receipt_sha256'}))

  def test_no_vehicle_frame_promotion(self):
    row = self.pub.load()['empirical-yaw-verdict-v1.json']
    row['vehicle_frame_calibrated'] = True
    with self.assertRaises(ValueError):
      self.pub.validate_row('empirical-yaw-verdict-v1.json', p.seal({k: v for k, v in row.items() if k != 'receipt_sha256'}))

  def test_no_full_plant_promotion(self):
    row = self.pub.load()['empirical-signal-provenance-readiness-v1.json']
    row['full_plant_ready'] = True
    with self.assertRaises(ValueError):
      self.pub.validate_row('empirical-signal-provenance-readiness-v1.json', p.seal({k: v for k, v in row.items() if k != 'receipt_sha256'}))

  def test_no_holdout_selection(self):
    row = self.pub.load()['empirical-yaw-verdict-v1.json']
    self.assertFalse(row['holdout_used_for_selection'])

  def test_stage_a_and_reference_unchanged(self):
    row = self.pub.load()['empirical-signal-provenance-readiness-v1.json']
    self.assertEqual(row['historical']['stage_a'], 'STRICT_READY_GATE_FAILED')
    self.assertEqual(row['calibration_blockers'], p.BLOCKERS)
    self.assertFalse(row['counterfactual_use_admitted'])
    self.assertEqual(row['sealed_reference'], 'NOT_GENERATED')

  def test_no_ta_sg_execution_or_composition(self):
    row = self.pub.load()['empirical-signal-provenance-readiness-v1.json']['historical']
    self.assertFalse(row['ta_execution'])
    self.assertFalse(row['sg_execution'])
    self.assertFalse(row['composition_authorized'])

  def test_single_route_limit_preserved(self):
    row = self.pub.load()['empirical-signal-provenance-readiness-v1.json']
    self.assertEqual(row['route_count'], 1)
    self.assertEqual(row['route_generalization'], 'SINGLE_ROUTE_GENERALIZATION_UNAVAILABLE')

  def test_no_local_paths_or_traces(self):
    name = 'empirical-yaw-verdict-v1.json'
    row = self.pub.load()[name]
    row['gyro_trace'] = [1.0, 2.0]
    with self.assertRaises(ValueError):
      self.pub.validate_row(name, p.seal({k: v for k, v in row.items() if k != 'receipt_sha256'}))

  def test_unknown_public_filename_rejected(self):
    with self.assertRaises(ValueError):
      self.pub.validate_row('../../private.json', p.seal({'schema': 'UNKNOWN'}))

  def test_public_symlink_rejected_before_read(self):
    from pathlib import Path
    import tempfile
    from unittest.mock import patch

    with tempfile.TemporaryDirectory() as t:
      root = Path(t)
      (root / 'real').mkdir()
      (root / 'alias').symlink_to(root / 'real', target_is_directory=True)
      with patch.object(p, 'PUBLIC', root / 'alias'), patch.object(self.pub, 'validate_sources'):
        with self.assertRaisesRegex(ValueError, 'ALIAS'):
          self.pub.load()

  def test_adjudication_no_model_means_blocked_not_performance_rejection(self):
    row = self.pub.derive_adjudication(self.pub.load())
    self.assertEqual(row['yaw_model'], 'EMPIRICAL_YAW_MODEL_BLOCKED')
    self.assertEqual(row['model_reason'], 'BLOCKED_NO_CONTIGUOUS_SUPPORT')
    self.assertEqual(row['max_training_design_rows'], 82)
    self.assertFalse(row['development_model_scoring_performed'])
    self.assertFalse(row['holdout_model_evaluation_performed'])

  def test_adjudication_does_not_confirm_gyro_unit_or_axis(self):
    row = self.pub.derive_adjudication(self.pub.load())
    self.assertEqual(row['yaw_verdict'], 'YAW_UNIT_LIKELY_NOT_CONFIRMED')
    self.assertFalse(row['axis_correspondence_established'])
    self.assertFalse(row['independent_unit_confirmation'])

  def test_adjudication_repeatable_preserves_raw_receipts(self):
    rows = self.pub.load()
    import copy

    original = copy.deepcopy(rows)
    self.assertEqual(self.pub.derive_adjudication(rows), self.pub.derive_adjudication(rows))
    self.assertEqual(rows, original)
