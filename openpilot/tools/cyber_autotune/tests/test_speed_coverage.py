import dataclasses
import json
import math
import unittest


class TestSpeedCoverage(unittest.TestCase):
  def test_bins_are_left_closed_with_overflow_and_no_authority(self):
    from openpilot.tools.cyber_autotune.speed_coverage import summarize_segment, summarize_routes
    segment = summarize_segment((i * 10_000_000, True, speed) for i, speed in enumerate((0., .99, 1., 59.99, 60., 100.)))
    self.assertEqual(segment.counts[:2], (2, 1))
    self.assertEqual(segment.counts[59:], (1, 2))
    self.assertEqual(segment.accepted, 6)
    self.assertEqual(segment.observed_interval_ns, 50_000_000)
    report = summarize_routes(((segment,),))
    self.assertEqual(report['status'], 'DESCRIPTIVE_COMPLETE')
    for name in ('candidate_generation_allowed', 'confidence_qualified', 'promotable', 'runtime_accepted'):
      self.assertIs(report[name], False)

  def test_invalid_samples_are_visible_and_do_not_bridge_duration(self):
    from openpilot.tools.cyber_autotune.speed_coverage import summarize_segment
    speeds = (1., math.nan, math.inf, -1., 2., 3.)
    segment = summarize_segment((i * 10_000_000, i != 4, speed) for i, speed in enumerate(speeds))
    self.assertEqual((segment.total, segment.accepted, segment.invalid), (6, 2, 4))
    self.assertEqual(segment.observed_interval_ns, 0)

  def test_duplicate_reset_and_gap_do_not_inflate_duration(self):
    from openpilot.tools.cyber_autotune.speed_coverage import summarize_segment
    segment = summarize_segment((ns, True, 2.) for ns in (0, 10_000_000, 10_000_000, 5_000_000, 15_000_000, 500_000_000, 510_000_000))
    self.assertEqual((segment.total, segment.accepted, segment.duplicate, segment.backward, segment.gaps), (7, 5, 1, 1, 1))
    self.assertEqual(segment.observed_interval_ns, 20_000_000)
    self.assertEqual(segment.interval_min_ns, 10_000_000)
    self.assertEqual(segment.interval_max_ns, 485_000_000)

  def test_route_balancing_differs_from_sample_weighting(self):
    from openpilot.tools.cyber_autotune.speed_coverage import summarize_segment, summarize_routes
    a = summarize_segment((i, True, 2.) for i in range(3))
    b = summarize_segment(((0, True, 8.),))
    report = summarize_routes(((a,), (b,), ()))
    self.assertEqual((report['route_count'], report['nonempty_route_count'], report['empty_route_count']), (3, 2, 1))
    self.assertEqual(report['sample_proportions'][2], .75)
    self.assertEqual(report['route_balanced_proportions'][2], .5)
    self.assertEqual(report['route_balanced_proportions'][8], .5)
    self.assertEqual(report['status'], 'DESCRIPTIVE_INCOMPLETE')

  def test_segments_do_not_create_cross_boundary_dwell(self):
    from openpilot.tools.cyber_autotune.speed_coverage import summarize_segment, summarize_routes
    a = summarize_segment(((0, True, 2.), (10_000_000, True, 2.)))
    b = summarize_segment(((20_000_000, True, 2.), (30_000_000, True, 2.)))
    report = summarize_routes(((a, b),))
    self.assertEqual(report['observed_interval_ns'], 20_000_000)

  def test_empty_input_and_invalid_timestamp_do_not_report_complete(self):
    from openpilot.tools.cyber_autotune.speed_coverage import summarize_segment, summarize_routes
    self.assertEqual(summarize_routes(())['status'], 'DESCRIPTIVE_INCOMPLETE')
    for time in (-1, True, 1.5, 2**64):
      with self.subTest(time=time):
        segment = summarize_segment(((time, True, 2.),))
        self.assertEqual(segment.invalid, 1)
        self.assertEqual(segment.accepted, 0)
    for valid, speed in ((1, 2.), (True, True), (True, '2')):
      with self.subTest(valid=valid, speed=speed):
        self.assertEqual(summarize_segment(((0, valid, speed),)).invalid, 1)

  def test_summary_rejects_forged_counts_and_is_deterministic(self):
    from openpilot.tools.cyber_autotune.speed_coverage import summarize_segment, summarize_routes
    segment = summarize_segment(((0, True, 2.), (10_000_000, True, 3.)))
    with self.assertRaises(ValueError):
      summarize_routes(((dataclasses.replace(segment, accepted=99),),))
    expected = json.dumps(summarize_routes(((segment,),)), sort_keys=True, allow_nan=False)
    self.assertEqual(expected, json.dumps(summarize_routes(((segment,),)), sort_keys=True, allow_nan=False))

  def test_resource_bound_rejects_instead_of_truncating(self):
    from openpilot.tools.cyber_autotune.speed_coverage import MAX_SAMPLES, summarize_segment
    with self.assertRaisesRegex(ValueError, 'SAMPLE_LIMIT'):
      summarize_segment((i, True, 1.) for i in range(MAX_SAMPLES + 1))


if __name__ == '__main__':
  unittest.main()
