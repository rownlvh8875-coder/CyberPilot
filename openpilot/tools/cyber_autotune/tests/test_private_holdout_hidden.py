import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

from openpilot.tools.cyber_autotune import private_holdout_contract as h
from openpilot.tools.cyber_autotune import private_holdout_annotation as old
from openpilot.tools.cyber_autotune.tests.test_private_holdout_contract import setup_package, payload
from openpilot.tools.cyber_autotune.tests.test_private_pixel_execution import STAMP, SHA


def prediction():
  return {
    'image_geometry': [330, 526],
    'lane_count': 1,
    'points': [[100.0, 100.0], [110.0, 200.0], [120.0, 300.0]],
    'lanes': [{'confidence': 0.5, 'points': [[100.0, 100.0], [110.0, 200.0], [120.0, 300.0]]}],
  }


class TestHiddenHoldout(unittest.TestCase):
  def setUp(self):
    try:
      from openpilot.tools.cyber_autotune import private_holdout_hidden as hidden
    except ImportError:
      self.fail('Separate hidden-output authorization contract is not implemented')
    self.hidden = hidden
    self.temp = tempfile.TemporaryDirectory(dir=Path.home())
    self.addCleanup(self.temp.cleanup)
    self.root = Path(self.temp.name)
    _, _, self.package = setup_package(self.root)
    h.write_immutable(self.root / 'materialization.json', self.package)
    self.auth = hidden.authorize(self.package, SHA[:40], STAMP, acknowledged=True)

  def row(self, ordinal=0):
    return self.hidden.detector_row(self.package, self.auth, ordinal, prediction(), prediction(), STAMP)

  def test_authorization_exact_original_sixty(self):
    self.assertEqual(self.auth['materialization_sha256'], self.package['receipt_sha256'])
    self.assertEqual(self.auth['holdout_selection_sha256'], self.package['authorization']['holdout_selection_sha256'])
    self.assertEqual(self.auth['expected'], 60)

  def test_no_execution_without_authorization(self):
    with self.assertRaises(ValueError):
      self.hidden.require_execution(self.package, None)

  def test_no_resealed_source_drift(self):
    changed = h.seal({**h.unseal(self.auth), 'source_identity': {'fake': SHA}})
    with self.assertRaises(ValueError):
      self.hidden.require_execution(self.package, changed)

  def test_exact_package_duplicate_rejected(self):
    changed = h.unseal(self.package)
    changed['images'] = [self.package['images'][0]] * 60
    with self.assertRaises(ValueError):
      self.hidden.authorize(h.seal(changed), SHA[:40], STAMP, acknowledged=True)

  def test_unknown_ordinal_rejected(self):
    for ordinal in (-1, 60, True):
      with self.assertRaises(ValueError):
        self.row(ordinal)

  def test_non_repeatable_prediction_rejected(self):
    second = prediction()
    second['lanes'][0]['confidence'] = 0.6
    with self.assertRaises(ValueError):
      self.hidden.detector_row(self.package, self.auth, 0, prediction(), second, STAMP)

  def test_prediction_stale_image_binding_rejected(self):
    row = h.unseal(self.row())
    row['image_sha256'] = 'b' * 64
    with self.assertRaises(ValueError):
      self.hidden.validate_detector_row(self.package, self.auth, 0, h.seal(row))

  def test_identity_drift_rejected(self):
    row = h.unseal(self.row())
    row['detector'] = {'bad': SHA}
    with self.assertRaises(ValueError):
      self.hidden.validate_detector_row(self.package, self.auth, 0, h.seal(row))

  def test_nonfinite_prediction_rejected(self):
    invalid = prediction()
    invalid['lanes'][0]['points'][0][0] = float('nan')
    with self.assertRaises(ValueError):
      self.hidden.detector_row(self.package, self.auth, 0, invalid, invalid, STAMP)

  def test_hidden_rows_do_not_create_human_decisions(self):
    self.assertIsNone(self.row()['human_annotation'])
    self.assertEqual(old.ReviewStore(self.root).progress()['reviewed'], 0)

  def test_completion_requires_exact_all_sixty(self):
    with self.assertRaises(ValueError):
      self.hidden.complete(self.package, self.auth, [self.row()] * 60)

  def test_complete_has_no_prediction_summary(self):
    rows = [self.row(i) for i in range(60)]
    complete = self.hidden.complete(self.package, self.auth, rows)
    self.assertEqual(complete['processed'], 60)
    for forbidden in ('confidence', 'no_output', 'lane_count', 'predictions'):
      self.assertNotIn(forbidden, complete)

  def test_ai_is_separate_null_human_local_only(self):
    model = {'provider': 'LOCAL_ONLY', 'model': 'synthetic-vision-fixture', 'version': 'test-v1', 'weight_sha256': SHA, 'environment_sha256': SHA}
    row = self.hidden.ai_row(
      self.package, self.auth, self.row(), 'EGO_BOUNDARIES_AMBIGUOUS', 'Visible support is ambiguous in the synthetic fixture.', 'LOW', model, STAMP
    )
    self.assertIsNone(row['human_annotation'])
    self.assertEqual(row['schema'], 'PRIVATE_HOLDOUT_AI_PREREVIEW_V1')
    self.assertEqual(old.ReviewStore(self.root).progress()['reviewed'], 0)

  def test_ai_no_human_polylines_or_unknown_state(self):
    model = {'provider': 'LOCAL_ONLY', 'model': 'fixture', 'version': 'v1', 'weight_sha256': SHA, 'environment_sha256': SHA}
    with self.assertRaises(ValueError):
      self.hidden.ai_row(self.package, self.auth, self.row(), 'HUMAN_LABEL_COMPLETE', 'no', 'HIGH', model, STAMP)

  def test_private_image_requires_auth_before_opener(self):
    opener = Mock()
    with self.assertRaises(ValueError):
      self.hidden.guarded_input(self.package, None, 0, opener)
    opener.assert_not_called()

  def test_after_first_save_relation_preserves_blind(self):
    first = old.ReviewStore(self.root).save(0, payload())
    relation = self.hidden.first_relation(self.package, self.auth, 0, first, self.row(), None)
    self.assertTrue(relation['blind_human_review'])
    self.assertTrue(relation['detector_computed_before_human'])
    self.assertFalse(relation['ai_exposed_before_human'])
    self.assertFalse(relation['detector_exposed_before_human'])
    self.assertEqual(relation['first_decision_sha256'], first['receipt_sha256'])

  def test_ai_relation_is_actual_computation_not_assumption(self):
    first = old.ReviewStore(self.root).save(0, payload())
    model = {'provider': 'LOCAL_ONLY', 'model': 'fixture', 'version': 'v1', 'weight_sha256': SHA, 'environment_sha256': SHA}
    ai = self.hidden.ai_row(self.package, self.auth, self.row(), 'UNREVIEWABLE', 'Synthetic blank frame.', 'LOW', model, STAMP)
    with self.assertRaisesRegex(ValueError, 'AI_VISION_EXECUTION_UNVERIFIED'):
      self.hidden.first_relation(self.package, self.auth, 0, first, self.row(), ai)

  def test_whole_set_evaluation_requires_sixty_real_human_rows(self):
    rows = [self.row(i) for i in range(60)]
    with self.assertRaises(ValueError):
      self.hidden.evaluate(self.package, self.auth, None, rows, [])

  def test_post_freeze_metrics_preserve_early_inference_receipts(self):
    store = old.ReviewStore(self.root)
    for i in range(60):
      store.save(i, payload())
    reference = h.read(self.root / 'human-reference.json')
    rows = [self.row(i) for i in range(60)]
    snapshot = copy.deepcopy(rows)
    result = self.hidden.evaluate(self.package, self.auth, reference, rows, [])
    self.assertEqual(result['human_frames'], 60)
    self.assertEqual(rows, snapshot)
    self.assertEqual(result['ai_comparison']['status'], 'AI_NOT_RUN')
    self.assertFalse(result['qualification_allowed'])

  def test_ai_results_immutable(self):
    path = self.root / 'private-ai-fixture.json'
    first = self.row()
    h.write_immutable(path, first)
    with self.assertRaises(ValueError):
      h.write_immutable(path, {**first, 'human_annotation': {}})

  def test_ai_confusion_matrix_totals_only_after_human_freeze(self):
    store = old.ReviewStore(self.root)
    rows = [self.row(i) for i in range(60)]
    model = {'provider': 'LOCAL_ONLY', 'model': 'synthetic-vision-fixture', 'version': 'test-v1', 'weight_sha256': SHA, 'environment_sha256': SHA}
    ai = [
      self.hidden.ai_row(
        self.package, self.auth, row, 'BOTH_EGO_BOUNDARIES_VISIBLE', 'Synthetic fixture only, not an actual vision review.', 'MEDIUM', model, STAMP
      )
      for row in rows
    ]
    with self.assertRaises(ValueError):
      self.hidden.evaluate(self.package, self.auth, None, rows, ai)
    for i in range(60):
      store.save(i, payload())
    reference = h.read(self.root / 'human-reference.json')
    with self.assertRaisesRegex(ValueError, 'AI_VISION_EXECUTION_UNVERIFIED'):
      self.hidden.evaluate(self.package, self.auth, reference, rows, ai)
