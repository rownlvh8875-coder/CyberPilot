from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_dataset_v2_policy as old


def row(start='a', first=1, last=9, source='b', generation=None, ordinal=0, root='c'):
  return {
    'source_sha256': source * 64,
    'root_id': root * 64,
    'lineage_sha256': 'd' * 64,
    'ordinal': ordinal,
    'kind': 'rlog.zst',
    'metadata': {
      'generation': generation or old.expected_generation(),
      'logger_start_sha256': start * 64,
      'first_ns': first,
      'last_ns': last,
      'envelope_counts': {'carState': 2, 'carOutput': 2, 'carControl': 2},
    },
  }


class TestCrossRootInventory(unittest.TestCase):
  def module(self):
    from openpilot.tools.cyber_autotune import empirical_cross_root_inventory as v

    return v

  def test_filesystem_walk_never_opens_media_archive_or_other_files(self):
    v = self.module()
    with tempfile.TemporaryDirectory() as d:
      root = Path(d)
      (root / 'route--0').mkdir()
      for name in ('rlog.zst', 'qcamera.ts', 'private.zip', 'unrelated.json'):
        (root / 'route--0' / name).write_bytes(b'x')
      with patch.object(Path, 'open', side_effect=AssertionError('NO_CONTENT_DURING_ENUMERATION')):
        result = v.enumerate_directory(root)
      self.assertEqual(len(result['logs']), 1)
      self.assertEqual(result['file_count'], 4)
      self.assertEqual(result['archive_count'], 1)

  def test_symlink_cannot_escape_approved_root(self):
    v = self.module()
    with tempfile.TemporaryDirectory() as d:
      (Path(d) / 'alias').symlink_to('/tmp', target_is_directory=True)
      with self.assertRaises(ValueError):
        v.enumerate_directory(Path(d))

  def test_unknown_layout_remains_unverified(self):
    v = self.module()
    self.assertEqual(v.segment_lineage('unknown/rlog.zst')['ordinal'], None)
    self.assertEqual(v.segment_lineage('route--7/rlog.zst')['ordinal'], 7)
    self.assertEqual(v.segment_lineage('route/7/rlog.zst')['ordinal'], 7)

  def test_identical_cross_root_copy_is_one_segment(self):
    v = self.module()
    result = v.group([row(), row(root='e')], set())
    self.assertEqual(len(result), 1)
    self.assertEqual(result[0]['segment_count'], 1)
    self.assertEqual(result[0]['duplicate_file_count'], 1)

  def test_recompressed_or_renamed_copy_is_one_segment(self):
    v = self.module()
    result = v.group([row(), row(source='e', root='f')], set())
    self.assertEqual(result[0]['segment_count'], 1)
    self.assertEqual(result[0]['duplicate_file_count'], 1)

  def test_appended_segment_and_same_logger_start_are_one_route(self):
    v = self.module()
    result = v.group([row(), row(first=10, last=19, source='e', ordinal=1)], set())
    self.assertEqual(len(result), 1)
    self.assertEqual(result[0]['segment_count'], 2)

  def test_distinct_logger_start_groups_remain_distinct(self):
    v = self.module()
    self.assertEqual(len(v.group([row(), row(start='e', source='f', first=20, last=29)], set())), 2)

  def test_v1_start_excludes_copies_and_appended_segments(self):
    v = self.module()
    result = v.group([row(), row(first=10, last=19, source='e', ordinal=1)], {'a' * 64})
    self.assertEqual(result[0]['status'], 'ROUTE_DUPLICATE_EXISTING_V1')
    self.assertFalse(result[0]['untouched'])

  def test_conflicting_overlap_is_ambiguous(self):
    v = self.module()
    result = v.group([row(), row(first=5, last=14, source='e', ordinal=1)], set())
    self.assertEqual(result[0]['status'], 'ROUTE_IDENTITY_AMBIGUOUS')

  def test_mixed_generation_same_start_cannot_be_split(self):
    v = self.module()
    result = v.group([row(), row(source='e', generation={**old.expected_generation(), 'source_commit': 'f' * 40})], set())
    self.assertEqual(result[0]['status'], 'ROUTE_IDENTITY_AMBIGUOUS')

  def test_buckets_never_merge_source_generation(self):
    v = self.module()
    routes = v.group([row(), row(start='e', source='f', generation={**old.expected_generation(), 'source_commit': 'f' * 40})], set())
    buckets = v.buckets(routes)
    self.assertEqual(len(buckets), 2)
    self.assertEqual(sum(x['route_count'] for x in buckets), 2)

  def test_prior_analysis_unknown_excludes_holdout(self):
    v = self.module()
    routes = v.group([row()], set())
    self.assertEqual(routes[0]['prior_analysis'], 'ROUTE_PRIOR_ANALYSIS_STATUS_UNKNOWN')
    self.assertFalse(routes[0]['untouched'])

  def test_partial_or_missing_required_messages_not_eligible(self):
    v = self.module()
    item = row()
    item['metadata']['envelope_counts'].pop('carOutput')
    result = v.group([item], set())
    self.assertEqual(result[0]['status'], 'ROUTE_CORRUPT_OR_INCOMPLETE')
    self.assertFalse(result[0]['compatible'])

  def test_metadata_reader_does_not_touch_driving_or_gps_body(self):
    v = self.module()

    class Envelope:
      def __init__(self, kind, t):
        self.kind = kind
        self.logMonoTime = t

      def which(self):
        return self.kind

      def __getattr__(self, name):
        raise AssertionError('FORBIDDEN_BODY:' + name)

    init = SimpleNamespace(
      which=lambda: 'initData',
      logMonoTime=1,
      initData=SimpleNamespace(gitCommit='f' * 40, osVersion='other', dirty=False, wallTimeNanos=100, bootlogId='boot', dongleId='device'),
    )

    class Params:
      carFingerprint = 'HYUNDAI_SANTA_FE_2022'
      steerControlType = 'torque'
      flags = 65928

      def as_builder(self):
        return self

      def to_bytes(self):
        return b'cp'

    cp = SimpleNamespace(which=lambda: 'carParams', carParams=Params())
    events = [init, cp, *[Envelope(k, i + 2) for i, k in enumerate(('carState', 'carOutput', 'carControl', 'modelV2', 'gpsLocation', 'sensorEvents'))]]
    info = v.metadata(events)
    self.assertEqual(info['generation']['source_commit'], 'f' * 40)
    self.assertEqual(info['envelope_counts']['gpsLocation'], 1)

  def test_unknown_generation_runtime_steer_max_remains_unavailable(self):
    v = self.module()
    routes = v.group([row(generation={**old.expected_generation(), 'source_commit': 'f' * 40})], set())
    self.assertIsNone(v.buckets(routes)[0]['runtime_steer_max'])
    self.assertEqual(routes[0]['status'], 'ROUTE_DIFFERENT_SOURCE_GENERATION')

  def test_no_raw_route_names_or_clocks_in_public_projection(self):
    v = self.module()
    item = row()
    result = v.public_routes(v.group([item], set()))
    text = p.canonical(result)
    self.assertNotIn(b'first_ns', text)
    self.assertNotIn(b'logger_start', text)
    self.assertNotIn(b'lineage', text)
    self.assertIn(b'route_id', text)


class TestCrossRootIntegrity(unittest.TestCase):
  def module(self):
    from openpilot.tools.cyber_autotune import empirical_cross_root_inventory as v

    return v

  def test_same_segment_qlog_rlog_metadata_are_alternatives(self):
    v = self.module()
    first = row()
    alternate = row(first=2, last=8, source='e', root='f')
    alternate['kind'] = 'qlog.zst'
    alternate['metadata']['envelope_counts'] = {'carState': 1, 'carOutput': 1, 'carControl': 1}
    result = v.group([first, alternate], set())
    self.assertEqual(result[0]['segment_count'], 1)
    self.assertEqual(result[0]['status'], 'ROUTE_COMPATIBLE_WITH_V1_GENERATION')

  def test_same_lineage_conflicting_starts_are_ambiguous(self):
    v = self.module()
    result = v.group([row(), row(start='e', source='f', first=20, last=29)], set())
    self.assertTrue(all(x['status'] == 'ROUTE_IDENTITY_AMBIGUOUS' for x in result))

  def test_different_roots_names_do_not_erase_start_identity(self):
    v = self.module()
    alternate = row(root='e', source='f')
    alternate['lineage_sha256'] = 'f' * 64
    self.assertEqual(len(v.group([row(), alternate], set())), 1)

  def test_clock_regression_rejected_without_driving_body(self):
    v = self.module()
    events = [SimpleNamespace(which=lambda: 'carState', logMonoTime=t) for t in (10, 9)]
    with self.assertRaisesRegex(ValueError, 'CLOCK_REGRESSION'):
      v.metadata(events)

  def test_failed_member_marks_entire_route_incomplete(self):
    v = self.module()
    failed = {'root_id': 'c' * 64, 'lineage_sha256': 'd' * 64}
    self.assertEqual(v.group([row()], set(), [failed])[0]['status'], 'ROUTE_CORRUPT_OR_INCOMPLETE')

  def test_dirty_duplicate_cannot_be_hidden_by_clean_representative(self):
    v = self.module()
    dirty = row(root='e')
    dirty['metadata']['source_dirty'] = True
    self.assertEqual(v.group([row(), dirty], set())[0]['status'], 'ROUTE_IDENTITY_AMBIGUOUS')

  def test_mixed_generation_bucket_preserves_all_source_identities(self):
    v = self.module()
    result = v.buckets(v.group([row(), row(source='e', generation={**old.expected_generation(), 'source_commit': 'f' * 40})], set()))
    self.assertEqual(result[0]['generation']['status'], 'MIXED_METADATA_GENERATIONS')
    self.assertEqual(len(result[0]['generation']['observed_generations']), 2)
    self.assertEqual(result[0]['compatible_routes'], 0)
