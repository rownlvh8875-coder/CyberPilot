import unittest

from openpilot.tools.cyber_autotune import private_holdout_pixel_metrics as metrics
from openpilot.tools.cyber_autotune import private_holdout_contract as h
from openpilot.tools.cyber_autotune.tests.test_private_holdout_contract import setup_package, payload
from openpilot.tools.cyber_autotune.tests.test_private_pixel_execution import STAMP


class TestHoldoutPixelMetrics(unittest.TestCase):
  def setUp(self):
    _, _, self.package = setup_package(None)
    self.rows = [h.annotation(image, payload(), STAMP) for image in self.package['images']]
    self.reference = h.freeze_reference(self.package, self.rows, STAMP)

  def predictions(self, offset=0):
    return [metrics.prediction_receipt(
      self.package, self.reference, i,
      [{'points': [[x + offset, y] for x, y in self.rows[i][side]], 'confidence': .7}
       for side in ('right', 'left')], STAMP) for i in range(60)]

  def test_exact_overlap_zero_error_and_assignment(self):
    result = metrics.evaluate(self.package, self.reference, self.predictions())
    self.assertEqual(result['left']['median'], 0.)
    self.assertEqual(result['right']['p95'], 0.)
    self.assertEqual(result['center']['median'], 0.)
    self.assertEqual(result['both_boundary_geometry_match_frames'], 60)
    self.assertFalse(result['qualification_allowed'])

  def test_five_pixel_shift(self):
    result = metrics.evaluate(self.package, self.reference, self.predictions(5.))
    self.assertEqual(result['left']['median'], 5.)
    self.assertEqual(result['right']['p95'], 5.)
    self.assertEqual(result['center']['median'], 5.)

  def test_empty_predictions_availability_not_omitted(self):
    predictions = [metrics.prediction_receipt(self.package, self.reference, i, [], STAMP) for i in range(60)]
    result = metrics.evaluate(self.package, self.reference, predictions)
    self.assertEqual(result['left_unavailable_visible_frames'], 60)
    self.assertEqual(result['right_unavailable_visible_frames'], 60)
    self.assertIsNone(result['combined']['median'])

  def test_ambiguous_excluded_counts_preserved(self):
    body = payload('EGO_BOUNDARIES_AMBIGUOUS')
    body['left'] = body['right'] = []
    rows = [h.annotation(image, body, STAMP) for image in self.package['images']]
    reference = h.freeze_reference(self.package, rows, STAMP)
    predictions = [metrics.prediction_receipt(self.package, reference, i, [], STAMP) for i in range(60)]
    result = metrics.evaluate(self.package, reference, predictions)
    self.assertEqual(result['evaluable_visible_boundary_frames'], 0)
    self.assertEqual(result['state_counts']['EGO_BOUNDARIES_AMBIGUOUS'], 60)
    self.assertEqual(result['left_unavailable_visible_frames'], 0)

  def test_one_side_never_center(self):
    body = payload('LEFT_ONLY_VISIBLE')
    body['right'] = []
    rows = [h.annotation(image, body, STAMP) for image in self.package['images']]
    reference = h.freeze_reference(self.package, rows, STAMP)
    predictions = [metrics.prediction_receipt(self.package, reference, i,
                                             [{'points': body['left'], 'confidence': .2}], STAMP) for i in range(60)]
    result = metrics.evaluate(self.package, reference, predictions)
    self.assertEqual(result['left']['median'], 0.)
    self.assertEqual(result['center']['count'], 0)
    self.assertEqual(result['right']['count'], 0)

  def test_no_pre_freeze_detector_receipt(self):
    with self.assertRaises(ValueError):
      metrics.prediction_receipt(self.package, None, 0, [], STAMP)

  def test_pre_freeze_timestamp_rejected(self):
    with self.assertRaises(ValueError):
      metrics.prediction_receipt(self.package, self.reference, 0, [], '2026-10-07T00:00:00Z')

  def test_duplicate_or_missing_prediction_rejected(self):
    for predictions in (self.predictions()[:-1], [self.predictions()[0]] * 60):
      with self.assertRaises(ValueError):
        metrics.evaluate(self.package, self.reference, predictions)

  def test_no_extrapolation_support(self):
    lanes = [{'points': [[100., 70.], [110., 60.], [120., 50.]], 'confidence': .7}]
    predictions = [metrics.prediction_receipt(self.package, self.reference, i, lanes, STAMP) for i in range(60)]
    result = metrics.evaluate(self.package, self.reference, predictions)
    self.assertEqual(result['left_unavailable_visible_frames'], 60)
    self.assertEqual(result['unsupported_no_y_overlap_lanes'], 60)

  def test_pixel_policy_frozen_no_confidence_optimization(self):
    self.assertIsNone(h.EVALUATION_POLICY['acceptance_threshold'])
    self.assertEqual(h.EVALUATION_POLICY['metric_projection'], 'FORBIDDEN')
    low = self.predictions()
    self.assertEqual(metrics.evaluate(self.package, self.reference, low),
                     metrics.evaluate(self.package, self.reference, low))
