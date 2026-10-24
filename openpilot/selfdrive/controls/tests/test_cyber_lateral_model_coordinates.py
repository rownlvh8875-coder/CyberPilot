import unittest

from openpilot.selfdrive.controls.lib.cyber_lateral.path_observer import (
  PathQualityInput, observe_path_quality,
)


class TestCyberLateralRealModelCoordinates(unittest.TestCase):
  def test_model_coordinate_lane_order_is_valid(self):
    result = observe_path_quality(PathQualityInput(
      station_m=(0., 10., 20.),
      desired_path_y_m=(0., 0.1, 0.2),
      left_lane_y_m=(-1.3, -1.2, -1.1),
      right_lane_y_m=(1.7, 1.7, 1.8),
      left_lane_probability=(.97, .97, .97),
      right_lane_probability=(.96, .96, .96),
      left_lane_std_m=(.09, .09, .09),
      right_lane_std_m=(.11, .11, .11),
      left_road_edge_y_m=(-2.2, -2.2, -2.2),
      right_road_edge_y_m=(7.4, 7.4, 7.4),
      lane_change_active=False,
      maneuver_state='none',
    ))
    self.assertTrue(result.valid, result.reason)
    self.assertEqual(result.reason, 'ok')
    self.assertGreater(result.lane_width_mean_m, 0.)
    self.assertGreater(result.minimum_edge_clearance_m, 0.)

  def test_mirrored_coordinate_axis_preserves_geometry(self):
    negative_left = PathQualityInput(
      station_m=(0., 10., 20.),
      desired_path_y_m=(0.1, 0.1, 0.1),
      left_lane_y_m=(-1.8, -1.8, -1.8),
      right_lane_y_m=(1.8, 1.8, 1.8),
      left_lane_probability=(.9, .9, .9),
      right_lane_probability=(.8, .8, .8),
      left_lane_std_m=(.1, .1, .1),
      right_lane_std_m=(.2, .2, .2),
      left_road_edge_y_m=(-3., -3., -3.),
      right_road_edge_y_m=(3., 3., 3.),
      lane_change_active=False,
      maneuver_state='none',
    )
    positive_left = PathQualityInput(
      station_m=negative_left.station_m,
      desired_path_y_m=tuple(-v for v in negative_left.desired_path_y_m),
      left_lane_y_m=tuple(-v for v in negative_left.left_lane_y_m),
      right_lane_y_m=tuple(-v for v in negative_left.right_lane_y_m),
      left_lane_probability=negative_left.left_lane_probability,
      right_lane_probability=negative_left.right_lane_probability,
      left_lane_std_m=negative_left.left_lane_std_m,
      right_lane_std_m=negative_left.right_lane_std_m,
      left_road_edge_y_m=tuple(-v for v in negative_left.left_road_edge_y_m),
      right_road_edge_y_m=tuple(-v for v in negative_left.right_road_edge_y_m),
      lane_change_active=False,
      maneuver_state='none',
    )
    first = observe_path_quality(negative_left)
    second = observe_path_quality(positive_left)
    self.assertTrue(first.valid)
    self.assertTrue(second.valid)
    self.assertAlmostEqual(first.lane_width_mean_m, second.lane_width_mean_m)
    self.assertAlmostEqual(first.minimum_edge_clearance_m, second.minimum_edge_clearance_m)
    self.assertAlmostEqual(first.model_to_lane_center_bias_m, -second.model_to_lane_center_bias_m)


if __name__ == '__main__':
  unittest.main()
