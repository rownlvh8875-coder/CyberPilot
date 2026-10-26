import unittest
import numpy as np

from openpilot.tools.cyber_autotune import lane_public_protocol as p


class TestLanePublicProtocol(unittest.TestCase):
  def test_region_boundaries_and_full_frame_sampling(self):
    mask = np.zeros((9, 20), dtype=bool)
    mask[:, 5] = True
    reports = p.region_reports(mask, [[5., y] for y in range(9)])
    self.assertEqual(set(reports), {'far', 'mid', 'near'})
    for r in reports.values():
      self.assertEqual(r['gt_runs'], 3)
      self.assertEqual(r['coverage'], 1.)

  def test_invalid_region_points_not_silently_dropped(self):
    mask = np.zeros((9, 20), dtype=bool)
    for points in ([[5., -1]], [[float('nan'), 3]], [[21., 3]], [[5., 9]], [[5., 3], [5., 3]]):
      with self.subTest(points=points), self.assertRaises(ValueError):
        p.region_reports(mask, points)

  def test_ambiguous_palette_and_short_image_fail_closed(self):
    with self.assertRaises(ValueError):
      p.region_reports(np.zeros((2, 20), dtype=bool), [])
    with self.assertRaises(ValueError):
      p.category2_regions(np.ones((9, 20, 3), dtype=np.uint8), [])

  def test_polyline_samples_map_original_geometry_and_ignore_only_declared_invalid(self):
    # Detector normalized lane representation; no temporal interpolation.
    def lane(rows):
      return np.where((rows >= .3) & (rows <= .9), .4, -2.)
    points = p.sample_detector_lanes([lane], width=100, height=10)
    self.assertEqual(points, [[40., y] for y in range(3, 10)])
    self.assertEqual(points, p.sample_detector_lanes([lane], width=100, height=10))

  def test_nonfinite_and_out_of_contract_lanes_rejected(self):
    for val in (float('nan'), float('inf')):
      with self.subTest(val=val), self.assertRaises(ValueError):
        p.sample_detector_lanes([lambda rows, x=val: np.full_like(rows, x)], width=100, height=10)

  def test_no_output_is_not_filled_and_overlapping_lanes_deduplicate(self):
    self.assertEqual(p.sample_detector_lanes([], width=100, height=10), [])
    def lane(rows):
      return np.full_like(rows, .5)
    self.assertEqual(len(p.sample_detector_lanes([lane, lane], width=100, height=10)), 10)

  def test_metadata_selection_independent_of_confidence_and_model_outputs(self):
    metadata = [{'route_sha256': 'a' * 64, 'segment': 0, 'frame_index': i, 'frame_sha256': 'b' * 64} for i in range(10)]
    manifest = p.human_holdout_manifest(metadata, stride=3)
    self.assertEqual([r['frame_index'] for r in manifest['selected']], [0, 3, 6, 9])
    self.assertEqual(manifest['status'], 'PRIVATE_HUMAN_LABEL_PENDING')
    self.assertFalse(manifest['images_opened'])
    bad = [dict(metadata[0], detector_confidence=.99)]
    with self.assertRaises(ValueError):
      p.human_holdout_manifest(bad, stride=3)
    with self.assertRaises(ValueError):
      p.human_holdout_manifest([metadata[0], metadata[0]], stride=3)

  def test_metric_dataset_requires_all_geometry_and_gt_provenance(self):
    evidence = dict.fromkeys(p.METRIC_REQUIRED_FIELDS, 'a' * 64)
    self.assertEqual(p.metric_dataset_availability(evidence)['status'], 'METRIC_DATASET_STRUCTURALLY_PRESENT_NOT_QUALIFIED')
    evidence['extrinsics_sha256'] = None
    self.assertEqual(p.metric_dataset_availability(evidence)['status'], 'METRIC_PUBLIC_GT_UNAVAILABLE')
    with self.assertRaises(ValueError):
      p.metric_dataset_availability(dict(evidence, pixel_meter_scale=.01))

  def test_off_canvas_polyline_samples_are_counted_not_whole_frame_rejected(self):
    def lane(rows):
      return np.array([-2., -.1, .25, .5, 1.2])
    report = p.sample_detector_lane_diagnostics([lane], width=100, height=5)
    self.assertEqual(report['points'], [[25., 2], [50., 3]])
    self.assertEqual(report['outside_y_support_points'], 1)
    self.assertEqual(report['outside_image_points'], 2)
    self.assertEqual(report['source_points'], 5)
