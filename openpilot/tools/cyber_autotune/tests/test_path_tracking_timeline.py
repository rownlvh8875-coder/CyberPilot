from dataclasses import FrozenInstanceError
import importlib
import importlib.util
import math
import unittest


class TestPathTrackingTimeline(unittest.TestCase):
  def api(self):
    name = 'openpilot.tools.cyber_autotune.path_tracking_timeline'
    self.assertIsNotNone(importlib.util.find_spec(name), 'path tracking timeline analyzer not implemented')
    return importlib.import_module(name)

  def sample(self, path_ns, tracking_ns, bias, desired, current):
    api = self.api()
    return api.PathTrackingTimelineSample(path_ns, tracking_ns, bias, desired, current)

  def test_keeps_path_and_tracking_times_separate_and_reports_peak_order(self):
    api = self.api()
    result = api.summarize_path_tracking_timeline((
      self.sample(100, 112, 0.05, 0.010, 0.011),
      self.sample(200, 215, 0.30, 0.012, 0.014),
      self.sample(300, 319, 0.10, 0.014, 0.020),
    ))

    self.assertEqual(result.sample_count, 3)
    self.assertEqual(tuple(point.path_mono_time_ns for point in result.points), (100, 200, 300))
    self.assertEqual(tuple(point.tracking_mono_time_ns for point in result.points), (112, 215, 319))
    self.assertEqual(tuple(point.time_skew_ns for point in result.points), (12, 15, 19))
    self.assertAlmostEqual(result.points[1].curvature_tracking_error_1pm, 0.002)
    self.assertEqual(result.model_bias_peak_path_time_ns, 200)
    self.assertEqual(result.tracking_error_peak_tracking_time_ns, 319)
    self.assertEqual(result.tracking_peak_minus_bias_peak_ns, 119)
    self.assertIsNone(getattr(result, 'root_cause', None))

  def test_positive_negative_and_zero_curvature_are_summarized_separately(self):
    api = self.api()
    result = api.summarize_path_tracking_timeline((
      self.sample(100, 110, 0.20, 0.010, 0.011),
      self.sample(200, 210, 0.40, 0.020, 0.023),
      self.sample(300, 310, -0.30, -0.010, -0.012),
      self.sample(400, 410, -0.10, -0.020, -0.021),
      self.sample(500, 510, 0.05, 0.0, 0.0),
    ))

    self.assertEqual(result.positive_curvature.count, 2)
    self.assertAlmostEqual(result.positive_curvature.model_bias_signed_mean_m, 0.30)
    self.assertAlmostEqual(result.positive_curvature.tracking_error_signed_mean_1pm, 0.002)
    self.assertEqual(result.negative_curvature.count, 2)
    self.assertAlmostEqual(result.negative_curvature.model_bias_signed_mean_m, -0.20)
    self.assertAlmostEqual(result.negative_curvature.tracking_error_signed_mean_1pm, -0.0015)
    self.assertEqual(result.zero_curvature.count, 1)
    self.assertAlmostEqual(result.zero_curvature.model_bias_signed_mean_m, 0.05)
    self.assertAlmostEqual(result.zero_curvature.tracking_error_signed_mean_1pm, 0.0)

  def test_time_axes_fail_closed_on_reversal_but_tracking_reuse_is_allowed(self):
    api = self.api()
    allowed = api.summarize_path_tracking_timeline((
      self.sample(100, 110, 0.1, 0.01, 0.01),
      self.sample(200, 110, 0.2, 0.02, 0.021),
    ))
    self.assertEqual(allowed.sample_count, 2)
    self.assertEqual(allowed.unique_tracking_time_count, 1)

    bad_sequences = (
      (
        self.sample(100, 110, 0.1, 0.01, 0.01),
        self.sample(100, 120, 0.2, 0.02, 0.021),
      ),
      (
        self.sample(100, 120, 0.1, 0.01, 0.01),
        self.sample(200, 119, 0.2, 0.02, 0.021),
      ),
    )
    for samples in bad_sequences:
      with self.subTest(samples=samples):
        with self.assertRaises(ValueError):
          api.summarize_path_tracking_timeline(samples)

  def test_invalid_types_nonfinite_and_subtraction_overflow_fail_closed(self):
    api = self.api()
    invalid = (
      (100, 110, math.nan, 0.01, 0.01),
      (100, 110, 0.1, math.inf, 0.01),
      (100, 110, 0.1, -1e308, 1e308),
      (100, 110, 0.1, -(10 ** 308), 10 ** 308),
      (100, 110, 10 ** 1000, 0.01, 0.01),
    )
    for args in invalid:
      with self.subTest(args=args):
        with self.assertRaises(ValueError):
          api.summarize_path_tracking_timeline((
            api.PathTrackingTimelineSample(*args),
            api.PathTrackingTimelineSample(200, 210, 0.2, 0.02, 0.021),
          ))

    with self.assertRaises(ValueError):
      api.summarize_path_tracking_timeline((
        api.PathTrackingTimelineSample(True, 110, 0.1, 0.01, 0.01),
        api.PathTrackingTimelineSample(200, 210, 0.2, 0.02, 0.021),
      ))

  def test_signed_means_preserve_representable_cancellation_remainder(self):
    api = self.api()
    tiny = 1e-100
    result = api.summarize_path_tracking_timeline((
      self.sample(100, 110, 1e308, 0.0, 1e308),
      self.sample(200, 210, tiny, 0.0, tiny),
      self.sample(300, 310, -1e308, 0.0, -1e308),
    ))
    expected = tiny / 3.
    self.assertEqual(result.model_bias_signed_mean_m, expected)
    self.assertEqual(result.tracking_error_signed_mean_1pm, expected)
    self.assertEqual(result.zero_curvature.model_bias_signed_mean_m, expected)
    self.assertEqual(result.zero_curvature.tracking_error_signed_mean_1pm, expected)

  def test_signed_means_preserve_representable_subnormal_values(self):
    api = self.api()
    tiny = float.fromhex('0x0.0000000000001p-1022')
    result = api.summarize_path_tracking_timeline((
      self.sample(100, 110, tiny, 0.0, tiny),
      self.sample(200, 210, tiny, 0.0, tiny),
      self.sample(300, 310, 0.0, 0.0, 0.0),
    ))
    self.assertEqual(result.model_bias_signed_mean_m, tiny)
    self.assertEqual(result.tracking_error_signed_mean_1pm, tiny)
    self.assertEqual(result.zero_curvature.model_bias_signed_mean_m, tiny)
    self.assertEqual(result.zero_curvature.tracking_error_signed_mean_1pm, tiny)

  def test_input_and_output_are_immutable_and_deterministic(self):
    api = self.api()
    samples = (
      self.sample(100, 111, 0.2, 0.01, 0.011),
      self.sample(200, 213, -0.1, -0.01, -0.012),
    )
    first = api.summarize_path_tracking_timeline(samples)
    second = api.summarize_path_tracking_timeline(samples)
    self.assertEqual(first, second)
    with self.assertRaises(FrozenInstanceError):
      first.sample_count = 99
    self.assertEqual(samples[0].model_to_lane_center_bias_m, 0.2)


if __name__ == '__main__':
  unittest.main()
