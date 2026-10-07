import unittest
import numpy as np
from openpilot.tools.cyber_autotune import lane_marking_metrics as m


class TestLaneMarkingMetrics(unittest.TestCase):
  def mask(self):
    mask = np.zeros((4, 20), dtype=bool)
    mask[1, 3:6] = True
    mask[1, 13:16] = True
    mask[2, 4:7] = True
    mask[2, 12:15] = True
    return mask

  def test_run_center_distance_and_exact_mask_coverage(self):
    result = m.marking_frame(self.mask(), [(4.0, 1), (14.0, 1), (6.0, 2), (18.0, 2)])
    self.assertEqual(result['unit'], 'px')
    self.assertEqual(result['gt_runs'], 4)
    self.assertEqual(result['covered_gt_runs'], 3)
    self.assertEqual(result['coverage'], 0.75)
    self.assertEqual(result['pred_to_gt']['maximum'], 5.0)
    self.assertEqual(result['pred_to_gt']['median'], 0.5)
    self.assertEqual(result['pred_to_gt']['p95'], 4.399999999999999)
    self.assertFalse(result['ego_lane_association_evaluated'])
    self.assertIsNone(result['meter_error'])

  def test_missing_rows_are_unavailable_without_interpolation(self):
    result = m.marking_frame(self.mask(), [(4.0, 1), (14.0, 1)])
    self.assertEqual(result['unavailable_gt_runs'], 2)
    self.assertEqual(result['coverage'], 0.5)
    self.assertEqual(result['gt_to_pred']['sample_count'], 2)

  def test_empty_gt_not_perfect_zero_error(self):
    result = m.marking_frame(np.zeros((3, 10), dtype=bool), [(3.0, 1)])
    self.assertEqual(result['status'], 'REFERENCE_UNAVAILABLE')
    self.assertIsNone(result['pred_to_gt']['median'])
    self.assertIsNone(result['coverage'])
    self.assertEqual(result['unsupported_pred_points'], 1)

  def test_no_detector_output_counts_failure(self):
    result = m.marking_frame(self.mask(), [])
    self.assertEqual(result['status'], 'REFERENCE_UNAVAILABLE')
    self.assertEqual(result['unavailable_gt_runs'], 4)
    aggregate = m.aggregate([result, result])
    self.assertEqual(aggregate['frame_count'], 2)
    self.assertEqual(aggregate['unavailable_frame_rate'], 1.0)
    self.assertEqual(aggregate['coverage'], 0.0)

  def test_extra_markings_do_not_become_ego_lane_gt(self):
    mask = self.mask()
    mask[1, 9:11] = True
    result = m.marking_frame(mask, [(4.0, 1), (14.0, 1)])
    self.assertEqual(result['gt_runs'], 5)
    self.assertFalse(result['ego_lane_association_evaluated'])

  def test_invalid_geometry_points_and_duplicates_fail_closed(self):
    for mask, points in (
      (self.mask().astype(np.uint8), []),
      (np.zeros((1, 1, 1), bool), []),
      (self.mask(), [(float('nan'), 1)]),
      (self.mask(), [(2.0, True)]),
      (self.mask(), [(30.0, 1)]),
      (self.mask(), [(2.0, 1), (2.0, 1)]),
    ):
      with self.subTest(points=points):
        with self.assertRaises(ValueError):
          m.marking_frame(mask, points)

  def test_category_2_exact_palette_not_class_number_intensity(self):
    rgb = np.array([[[255, 0, 0], [64, 32, 32], [0, 255, 102]]], dtype=np.uint8)
    self.assertEqual(m.category2_mask(rgb).tolist(), [[True, False, False]])
    rgb[0, 0] = [254, 0, 0]
    with self.assertRaises(ValueError):
      m.category2_mask(rgb)

  def test_aggregation_deterministic_denominators_and_empty_input(self):
    a = m.marking_frame(self.mask(), [(4.0, 1), (14.0, 1)])
    b = m.marking_frame(self.mask(), [])
    report = m.aggregate([a, b])
    self.assertEqual(report, m.aggregate([a, b]))
    self.assertEqual(report['coverage'], 0.25)
    self.assertEqual(report['unavailable_frame_rate'], 0.5)
    with self.assertRaises(ValueError):
      m.aggregate([])
    a['gt_runs'] = 999
    with self.assertRaises(ValueError):
      m.aggregate([a])

  def test_rehashed_malformed_report_is_not_metric_evidence(self):
    from openpilot.tools.cyber_autotune.native_protocol import canonical, digest

    result = m.marking_frame(self.mask(), [(4.0, 1)])
    for field, value in [('covered_gt_runs', -1), ('gt_runs', 1), ('status', 'PUBLIC_GT_PASS'), ('pred_errors_px', [-1.0])]:
      damaged = dict(result)
      damaged[field] = value
      damaged['receipt_sha256'] = digest(canonical({k: v for k, v in damaged.items() if k != 'receipt_sha256'}))
      with self.subTest(field=field):
        with self.assertRaises(ValueError):
          m.aggregate([damaged])

  def test_only_background_predictions_are_frame_failure_not_available(self):
    result = m.marking_frame(self.mask(), [(5.0, 0)])
    self.assertEqual(result['status'], 'REFERENCE_UNAVAILABLE')
    self.assertEqual(result['unavailable_gt_runs'], 4)
    self.assertEqual(result['unsupported_pred_points'], 1)
