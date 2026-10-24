import dataclasses
import unittest

from openpilot.tools.cyber_autotune.evidence import PROVENANCE_KEYS
from openpilot.tools.cyber_autotune.torque_identification import SIGNAL_CONTRACT


def provenance(fill='a'):
  return tuple((key, fill * 64) for key in sorted(PROVENANCE_KEYS))


def group(epoch='1', route='2', start=0, end=9, counts=(60, 160, 260, 500, 500, 300, 160, 60),
          role='development_fit', algorithm='3' * 64, contract=SIGNAL_CONTRACT,
          boundary='START'):
  from openpilot.tools.cyber_autotune.torque_aggregation import TorqueEpochEvidence
  return TorqueEpochEvidence(
    epoch_sha256=epoch * 64,
    route_sha256=route * 64,
    source_commit='1' * 40,
    start_segment=start,
    end_segment=end,
    bucket_counts=counts,
    role=role,
    provenance=provenance(),
    signal_contract=contract,
    algorithm_sha256=algorithm,
    boundary_reason=boundary,
  )


class TestTorqueAggregation(unittest.TestCase):
  def test_structural_pool_reports_coverage_without_fit_authority(self):
    from openpilot.tools.cyber_autotune.torque_aggregation import TorqueAggregationInput, aggregate_torque_coverage
    first = group(epoch='1', route='2', counts=(60, 160, 260, 500, 500, 300, 160, 60))
    second = group(epoch='4', route='5', counts=(50, 150, 250, 500, 500, 500, 150, 50))
    request = TorqueAggregationInput((first, second), 'development_fit', '6' * 64)
    result = aggregate_torque_coverage(request)
    self.assertEqual(result, aggregate_torque_coverage(request))
    self.assertEqual(result.status, 'STRUCTURAL_COVERAGE_DIAGNOSTIC')
    self.assertEqual(result.group_count, 2)
    self.assertEqual(result.bucket_counts, (110, 310, 510, 1000, 1000, 800, 310, 110))
    self.assertEqual(result.point_count, sum(result.bucket_counts))
    self.assertTrue(result.pooled_count_thresholds_met)
    self.assertTrue(result.blockers)
    self.assertFalse(result.raw_points_combined)
    self.assertFalse(result.fit_executed)
    self.assertFalse(result.parameter_identification_qualified)
    self.assertFalse(result.candidate_generation_allowed)
    self.assertFalse(result.runtime_accepted)
    self.assertFalse(result.promotable)

  def test_group_order_is_canonical_and_does_not_imply_sequence(self):
    from openpilot.tools.cyber_autotune.torque_aggregation import TorqueAggregationInput, aggregate_torque_coverage
    a = group(epoch='1', route='2')
    b = group(epoch='4', route='5')
    x = aggregate_torque_coverage(TorqueAggregationInput((a, b), 'development_fit', '6' * 64))
    y = aggregate_torque_coverage(TorqueAggregationInput((b, a), 'development_fit', '6' * 64))
    self.assertEqual(x.aggregate_sha256, y.aggregate_sha256)
    self.assertEqual(x.bucket_counts, y.bucket_counts)
    self.assertFalse(x.raw_points_combined)

  def test_same_route_nonoverlap_epochs_are_allowed_but_overlap_is_blocked(self):
    from openpilot.tools.cyber_autotune.torque_aggregation import TorqueAggregationInput, aggregate_torque_coverage
    a = group(epoch='1', route='2', start=0, end=9)
    b = group(epoch='4', route='2', start=10, end=19, boundary='CLOCK_RESET')
    ok = aggregate_torque_coverage(TorqueAggregationInput((a, b), 'development_fit', '6' * 64))
    self.assertEqual(ok.status, 'STRUCTURAL_COVERAGE_DIAGNOSTIC')
    overlap = dataclasses.replace(b, start_segment=9)
    bad = aggregate_torque_coverage(TorqueAggregationInput((a, overlap), 'development_fit', '6' * 64))
    self.assertEqual(bad.status, 'BLOCKED')
    self.assertIn('OVERLAPPING_ROUTE_EPOCHS', bad.blockers)

  def test_duplicate_epoch_and_identity_conflicts_block(self):
    from openpilot.tools.cyber_autotune.torque_aggregation import TorqueAggregationInput, aggregate_torque_coverage
    a = group(epoch='1', route='2')
    same_epoch = dataclasses.replace(a, route_sha256='5' * 64, start_segment=20, end_segment=29)
    result = aggregate_torque_coverage(TorqueAggregationInput((a, same_epoch), 'development_fit', '6' * 64))
    self.assertEqual(result.status, 'BLOCKED')
    self.assertIn('DUPLICATE_EPOCH_ID', result.blockers)

  def test_algorithm_signal_role_and_policy_are_strict(self):
    from openpilot.tools.cyber_autotune.torque_aggregation import TorqueAggregationInput, aggregate_torque_coverage
    a = group(epoch='1', route='2')
    for changed in (
      dataclasses.replace(a, algorithm_sha256='9' * 64),
      dataclasses.replace(a, signal_contract='other'),
      dataclasses.replace(a, role='holdout'),
    ):
      with self.subTest(change=changed):
        result = aggregate_torque_coverage(TorqueAggregationInput((a, changed), 'development_fit', '6' * 64))
        self.assertEqual(result.status, 'BLOCKED')
    for role in ('holdout', 'evaluation', '', None):
      result = aggregate_torque_coverage(TorqueAggregationInput((a,), role, '6' * 64))
      self.assertEqual(result.status, 'BLOCKED')
    result = aggregate_torque_coverage(TorqueAggregationInput((a,), 'development_fit', 'bad'))
    self.assertEqual(result.status, 'BLOCKED')

  def test_bad_group_counts_segments_provenance_and_boundary_block(self):
    from openpilot.tools.cyber_autotune.torque_aggregation import TorqueAggregationInput, aggregate_torque_coverage
    a = group(epoch='1', route='2')
    bads = (
      dataclasses.replace(a, bucket_counts=(1, 2)),
      dataclasses.replace(a, bucket_counts=(True, 1, 1, 1, 1, 1, 1, 1)),
      dataclasses.replace(a, bucket_counts=(1501, 1, 1, 1, 1, 1, 1, 1)),
      dataclasses.replace(a, start_segment=10, end_segment=9),
      dataclasses.replace(a, provenance=()),
      dataclasses.replace(a, boundary_reason='MERGED'),
      dataclasses.replace(a, epoch_sha256='bad'),
      dataclasses.replace(a, source_commit='x' * 40),
    )
    for bad in bads:
      with self.subTest(bad=bad):
        result = aggregate_torque_coverage(TorqueAggregationInput((bad,), 'development_fit', '6' * 64))
        self.assertEqual(result.status, 'BLOCKED')

  def test_threshold_shortfall_is_reported_not_repaired(self):
    from openpilot.tools.cyber_autotune.torque_aggregation import TorqueAggregationInput, aggregate_torque_coverage
    a = group(epoch='1', route='2', counts=(42, 247, 782, 1500, 1500, 980, 455, 138))
    result = aggregate_torque_coverage(TorqueAggregationInput((a,), 'development_fit', '6' * 64))
    self.assertFalse(result.pooled_count_thresholds_met)
    self.assertEqual(result.bucket_deficits, (58, 53, 0, 0, 0, 0, 0, 0))
    self.assertEqual(result.total_point_deficit, 0)
    self.assertFalse(result.candidate_generation_allowed)

  def test_same_route_followup_requires_real_boundary_and_same_source(self):
    from openpilot.tools.cyber_autotune.torque_aggregation import TorqueAggregationInput, aggregate_torque_coverage
    first = group(epoch='1', route='2', start=0, end=9, boundary='START')
    fake_restart = group(epoch='4', route='2', start=10, end=19, boundary='START')
    result = aggregate_torque_coverage(TorqueAggregationInput((first, fake_restart), 'development_fit', '6' * 64))
    self.assertEqual(result.status, 'BLOCKED')
    self.assertIn('INVALID_ROUTE_BOUNDARY_SEQUENCE', result.blockers)

    changed_source = dataclasses.replace(fake_restart, boundary_reason='CLOCK_RESET', source_commit='2' * 40)
    result = aggregate_torque_coverage(TorqueAggregationInput((first, changed_source), 'development_fit', '6' * 64))
    self.assertEqual(result.status, 'BLOCKED')
    self.assertIn('ROUTE_SOURCE_MISMATCH', result.blockers)

  def test_zero_point_epoch_can_preserve_boundary_but_all_zero_is_blocked(self):
    from openpilot.tools.cyber_autotune.torque_aggregation import TorqueAggregationInput, aggregate_torque_coverage
    first = group(epoch='1', route='2', start=0, end=9, boundary='START')
    empty = group(epoch='4', route='2', start=10, end=10, boundary='CLOCK_RESET',
                  counts=(0, 0, 0, 0, 0, 0, 0, 0))
    third = group(epoch='5', route='2', start=11, end=19, boundary='CLOCK_RESET')
    result = aggregate_torque_coverage(TorqueAggregationInput((first, empty, third), 'development_fit', '6' * 64))
    self.assertEqual(result.status, 'STRUCTURAL_COVERAGE_DIAGNOSTIC')
    self.assertEqual(result.group_count, 3)
    self.assertEqual(result.nonempty_group_count, 2)

    result = aggregate_torque_coverage(TorqueAggregationInput((empty,), 'development_fit', '6' * 64))
    self.assertEqual(result.status, 'BLOCKED')
    self.assertIn('NO_COVERAGE_POINTS', result.blockers)

  def test_verified_point_identity_removes_only_identity_blocker(self):
    from openpilot.tools.cyber_autotune.torque_aggregation import (
      TorqueAggregationInput, TorquePointIdentityEvidence, aggregate_torque_coverage,
    )
    first = group(epoch='1', route='2', counts=(60, 160, 260, 500, 500, 300, 160, 60))
    second = group(epoch='4', route='5', counts=(50, 150, 250, 500, 500, 500, 150, 50))
    buckets = tuple(a + b for a, b in zip(first.bucket_counts, second.bucket_counts, strict=True))
    identity = TorquePointIdentityEvidence(
      summary_sha256='7' * 64,
      manifest_sha256='8' * 64,
      policy_sha256='9' * 64,
      group_count=2,
      nonempty_group_count=2,
      point_count=sum(buckets),
      bucket_counts=buckets,
      cross_group_duplicate_sample_id_count=0,
      within_group_duplicate_sample_id_count=0,
      within_group_duplicate_time_count=0,
      within_group_nonincreasing_time_count=0,
      raw_can_exported=False,
      gps_exported=False,
      video_exported=False,
      route_label_exported=False,
      fit_executed=False,
      candidate_generation_allowed=False,
    )
    result = aggregate_torque_coverage(TorqueAggregationInput((first, second), 'development_fit', '6' * 64, identity))
    self.assertTrue(result.point_identity_verified)
    self.assertNotIn('RAW_POINT_IDENTITY_UNVERIFIED', result.blockers)
    self.assertIn('CROSS_GROUP_STATISTICAL_INDEPENDENCE_UNVERIFIED', result.blockers)
    self.assertFalse(result.candidate_generation_allowed)

    for bad in (
      dataclasses.replace(identity, point_count=identity.point_count + 1),
      dataclasses.replace(identity, cross_group_duplicate_sample_id_count=1),
      dataclasses.replace(identity, raw_can_exported=True),
      dataclasses.replace(identity, summary_sha256='bad'),
    ):
      with self.subTest(bad=bad):
        blocked = aggregate_torque_coverage(TorqueAggregationInput((first, second), 'development_fit', '6' * 64, bad))
        self.assertEqual(blocked.status, 'BLOCKED')
        self.assertIn('POINT_IDENTITY_EVIDENCE_MISMATCH', blocked.blockers)

  def test_boundary_reason_must_match_segment_continuity(self):
    from openpilot.tools.cyber_autotune.torque_aggregation import TorqueAggregationInput, aggregate_torque_coverage
    first = group(epoch='1', route='2', start=0, end=9, boundary='START')

    contiguous_bad = group(epoch='4', route='2', start=10, end=19, boundary='MANIFEST_GAP')
    result = aggregate_torque_coverage(TorqueAggregationInput((first, contiguous_bad), 'development_fit', '6' * 64))
    self.assertEqual(result.status, 'BLOCKED')
    self.assertIn('BOUNDARY_REASON_MISMATCH', result.blockers)

    gap_bad = group(epoch='4', route='2', start=11, end=19, boundary='CLOCK_RESET')
    result = aggregate_torque_coverage(TorqueAggregationInput((first, gap_bad), 'development_fit', '6' * 64))
    self.assertEqual(result.status, 'BLOCKED')
    self.assertIn('BOUNDARY_REASON_MISMATCH', result.blockers)

    gap_ok = dataclasses.replace(gap_bad, boundary_reason='MANIFEST_GAP')
    result = aggregate_torque_coverage(TorqueAggregationInput((first, gap_ok), 'development_fit', '6' * 64))
    self.assertEqual(result.status, 'STRUCTURAL_COVERAGE_DIAGNOSTIC')


if __name__ == '__main__':
  unittest.main()
