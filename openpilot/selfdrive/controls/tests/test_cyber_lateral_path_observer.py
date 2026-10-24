import unittest
from dataclasses import FrozenInstanceError

from openpilot.selfdrive.controls.lib.cyber_lateral.path_observer import (
  PathQualityInput, align_path_to_stations, observe_path_quality,
)


def path_input(*, desired=(0., 0., 0.), left=(1.8, 1.8, 1.8), right=(-1.8, -1.8, -1.8),
               left_probability=(0.9, 0.9, 0.9), right_probability=(0.8, 0.8, 0.8),
               left_std=(0.1, 0.1, 0.1), right_std=(0.2, 0.2, 0.2),
               left_edge=(3., 3., 3.), right_edge=(-3., -3., -3.),
               lane_change_active=False, maneuver_state='none'):
  return PathQualityInput(
    station_m=(0., 10., 20.),
    desired_path_y_m=desired,
    left_lane_y_m=left,
    right_lane_y_m=right,
    left_lane_probability=left_probability,
    right_lane_probability=right_probability,
    left_lane_std_m=left_std,
    right_lane_std_m=right_std,
    left_road_edge_y_m=left_edge,
    right_road_edge_y_m=right_edge,
    lane_change_active=lane_change_active,
    maneuver_state=maneuver_state,
  )


class TestCarrotInspiredPathQualityObserver(unittest.TestCase):
  def test_model_path_is_interpolated_to_bounded_lane_stations_without_extrapolation(self):
    station, desired, indices = align_path_to_stations(
      (0., 5., 15., 30.), (0., 0.05, 0.15, 0.30), (0., 10., 20., 40.),
    )
    self.assertEqual(station, (0., 10., 20.))
    self.assertEqual(indices, (0, 1, 2))
    self.assertAlmostEqual(desired[0], 0.)
    self.assertAlmostEqual(desired[1], 0.1)
    self.assertAlmostEqual(desired[2], 0.2)

  def test_path_alignment_rejects_nonmonotonic_source_and_insufficient_overlap(self):
    with self.assertRaises(ValueError):
      align_path_to_stations((0., 5., 5.), (0., 0.1, 0.2), (0., 2., 4.))
    with self.assertRaises(ValueError):
      align_path_to_stations((0., 5., 10.), (0., 0.1, 0.2), (9., 10., 11.))

  def test_centered_and_signed_path_bias(self):
    centered = observe_path_quality(path_input())
    left = observe_path_quality(path_input(desired=(0.2, 0.2, 0.2)))
    right = observe_path_quality(path_input(desired=(-0.3, -0.3, -0.3)))
    self.assertTrue(centered.valid)
    self.assertEqual(centered.model_to_lane_center_bias_m, 0.)
    self.assertEqual(centered.lane_width_mean_m, 3.6)
    self.assertAlmostEqual(left.model_to_lane_center_bias_m, 0.2)
    self.assertAlmostEqual(right.model_to_lane_center_bias_m, -0.3)

  def test_asymmetric_lane_width_reports_variation(self):
    result = observe_path_quality(path_input(
      left=(1.8, 2.0, 2.2), right=(-1.8, -1.7, -1.6),
    ))
    self.assertTrue(result.valid)
    self.assertGreater(result.lane_width_std_m, 0.)

  def test_lane_loss_and_crossed_boundaries_fail_closed(self):
    lost = observe_path_quality(path_input(left_probability=(0.9, 0., 0.9)))
    crossed = observe_path_quality(path_input(left=(-1., -1., -1.), right=(1., 1., 1.)))
    self.assertFalse(lost.valid)
    self.assertEqual(lost.reason, 'lane_loss')
    self.assertFalse(crossed.valid)
    self.assertEqual(crossed.reason, 'crossed_lane_boundaries')

  def test_probability_std_and_geometry_shape_are_validated(self):
    invalid_probability = observe_path_quality(path_input(left_probability=(0.9, 1.1, 0.9)))
    invalid_std = observe_path_quality(path_input(right_std=(0.2, -0.1, 0.2)))
    invalid_shape = observe_path_quality(path_input(desired=(0., 0.)))
    self.assertEqual(invalid_probability.reason, 'invalid_lane_probability')
    self.assertEqual(invalid_std.reason, 'invalid_lane_std')
    self.assertEqual(invalid_shape.reason, 'geometry_shape_mismatch')

  def test_lane_change_or_maneuver_is_invalid_for_centering(self):
    lane_change = observe_path_quality(path_input(lane_change_active=True))
    maneuver = observe_path_quality(path_input(maneuver_state='turn'))
    self.assertEqual(lane_change.reason, 'lane_change_or_maneuver')
    self.assertEqual(maneuver.reason, 'lane_change_or_maneuver')

  def test_missing_road_edge_keeps_lane_observation_but_not_clearance(self):
    result = observe_path_quality(path_input(left_edge=None, right_edge=None))
    self.assertTrue(result.valid)
    self.assertIsNone(result.minimum_edge_clearance_m)

  def test_edge_ordering_fails_closed(self):
    result = observe_path_quality(path_input(left_edge=(1., 1., 1.)))
    self.assertFalse(result.valid)
    self.assertEqual(result.reason, 'invalid_road_edge_ordering')

  def test_input_and_observation_are_immutable(self):
    data = path_input()
    result = observe_path_quality(data)
    with self.assertRaises(FrozenInstanceError):
      data.maneuver_state = 'turn'
    with self.assertRaises(FrozenInstanceError):
      result.valid = False


if __name__ == '__main__':
  unittest.main()
