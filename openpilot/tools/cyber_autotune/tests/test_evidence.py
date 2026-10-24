from dataclasses import replace
import hashlib
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from openpilot.tools.cyber_autotune import evidence
from openpilot.tools.cyber_autotune.coverage import CoverageGroup, summarize_coverage
from openpilot.tools.cyber_autotune.evidence import (
  PROVENANCE_KEYS, DatasetEvidence, EvidenceManifest, EvidencePolicy, manifest_sha256, verify_evidence,
)
from openpilot.tools.cyber_autotune.preflight import CoveragePolicy, REQUIRED_STRATA


HASH = 'a' * 64


class TestEvidence(unittest.TestCase):
  def setUp(self):
    self.temp = tempfile.TemporaryDirectory()
    self.addCleanup(self.temp.cleanup)
    root = Path(self.temp.name)
    datasets = []
    for i, role in enumerate(('development_fit', 'development_evaluation')):
      path = root / f'synthetic-{i}'
      data = f'synthetic aggregate {i}'.encode()
      path.write_bytes(data)
      group = CoverageGroup(f'vehicle-{i}', f'route-{i}', f'day-{i}', tuple(sorted(REQUIRED_STRATA)))
      datasets.append(DatasetEvidence(f'data-{i}', role, str(path), hashlib.sha256(data).hexdigest(), len(data),
                                      group, tuple((key, HASH) for key in sorted(PROVENANCE_KEYS)), True))
    self.manifest = EvidenceManifest(tuple(datasets))
    self.minimums = CoveragePolicy(HASH, tuple((key, 1) for key in sorted(REQUIRED_STRATA)))
    self.policy = self.approve(self.manifest)

  def approve(self, manifest):
    return EvidencePolicy(HASH, manifest_sha256(manifest), tuple(d.path for d in manifest.datasets), 1024, self.minimums)

  def changed(self, **kwargs):
    return replace(self.manifest, datasets=(replace(self.manifest.datasets[0], **kwargs), self.manifest.datasets[1]))

  def assert_blocked_without_open(self, manifest, policy=None):
    with patch('openpilot.tools.cyber_autotune.evidence.os.open', side_effect=AssertionError('must not open')):
      result = verify_evidence(manifest, policy or self.approve(manifest))
    self.assertEqual(result.status, 'BLOCKED')
    self.assertEqual(result.artifacts_verified, 0)
    return result

  def test_reviewed_synthetic_manifest_integrity_only(self):
    result = verify_evidence(self.manifest, self.policy)
    self.assertEqual(result.status, 'INTEGRITY_AND_COVERAGE_PASS')
    self.assertEqual(result.artifacts_verified, 2)
    self.assertFalse(result.offline_evaluable)
    self.assertFalse(result.runtime_accepted)
    self.assertFalse(result.candidate_generation_allowed)
    self.assertNotIn(self.temp.name, repr(result))
    self.assertEqual(len(result.coverage), 2)

  def test_manifest_tamper_blocked(self):
    self.assert_blocked_without_open(self.changed(dataset_id='other'), self.policy)

  def test_holdout_and_validation_never_opened_even_if_reviewed(self):
    for role in ('holdout', 'validation', 'H1', 'H2', 'unknown'):
      with self.subTest(role=role):
        self.assert_blocked_without_open(self.changed(role=role))

  def test_allowlist_not_manifest_controlled(self):
    self.assert_blocked_without_open(self.manifest, replace(self.policy, allowed_paths=()))

  def test_missing_or_unknown_provenance(self):
    provenance = self.manifest.datasets[0].provenance
    for value in (provenance[:-1], provenance + (('unknown', HASH),), ((provenance[0][0], None),) + provenance[1:]):
      self.assert_blocked_without_open(self.changed(provenance=value))

  def test_runtime_configuration_bindings_required_before_artifact_io(self):
    provenance = self.manifest.datasets[0].provenance
    for key in ('configuration', 'runtime_epoch', 'signal_units_frames_stages', 'timestamp_join_staleness'):
      remaining = tuple(pair for pair in provenance if pair[0] != key)
      for changed in (remaining, remaining + ((key, None),), remaining + ((key, ''),)):
        with self.subTest(key=key, provenance=changed):
          result = self.assert_blocked_without_open(self.changed(provenance=changed))
          self.assertEqual(result.blockers, ('INVALID_DATASET_CONTRACT',))

  def test_changed_runtime_configuration_invalidates_prior_manifest_review(self):
    provenance = self.manifest.datasets[0].provenance
    for key in ('configuration', 'runtime_epoch', 'signal_units_frames_stages', 'timestamp_join_staleness'):
      changed = tuple((name, 'b' * 64 if name == key else digest) for name, digest in provenance)
      with self.subTest(key=key):
        result = self.assert_blocked_without_open(self.changed(provenance=changed), self.policy)
        self.assertEqual(result.blockers, ('REVIEWED_MANIFEST_MISMATCH',))

  def test_route_and_vehicle_day_leakage(self):
    fit, evaluation = self.manifest.datasets
    for group in (replace(fit.group, route_group=evaluation.group.route_group),
                  replace(fit.group, vehicle_group=evaluation.group.vehicle_group, day_group=evaluation.group.day_group)):
      self.assert_blocked_without_open(self.changed(group=group))

  def test_content_duplicate_across_roles(self):
    self.assert_blocked_without_open(self.changed(artifact_sha256=self.manifest.datasets[1].artifact_sha256))

  def test_missing_role_or_duplicate_id(self):
    self.assert_blocked_without_open(replace(self.manifest, datasets=self.manifest.datasets[:1]))
    self.assert_blocked_without_open(self.changed(dataset_id=self.manifest.datasets[1].dataset_id))

  def test_hash_and_length_mismatch(self):
    for changes in ({'artifact_sha256': HASH}, {'size_bytes': 1}):
      manifest = self.changed(**changes)
      self.assertEqual(verify_evidence(manifest, self.approve(manifest)).status, 'BLOCKED')

  def test_declared_size_bound_before_open(self):
    self.assert_blocked_without_open(self.changed(size_bytes=1025))

  def test_symlink_leaf_and_parent(self):
    original = Path(self.manifest.datasets[0].path)
    link = original.with_name('link')
    link.symlink_to(original)
    parent_link = original.with_name('parent-link')
    parent_link.symlink_to(original.parent, target_is_directory=True)
    for path in (link, parent_link / original.name):
      manifest = self.changed(path=str(path))
      self.assert_blocked_without_open(manifest)

  def test_noncanonical_path_before_open(self):
    path = self.manifest.datasets[0].path
    for value in (path + '/../synthetic-0', 'relative', '/' + path, path + '\x00'):
      self.assert_blocked_without_open(self.changed(path=value))

  def test_hardlink_and_fifo_no_content_read(self):
    original = Path(self.manifest.datasets[0].path)
    hardlink = original.with_name('hardlink')
    os.link(original, hardlink)
    fifo = original.with_name('fifo')
    os.mkfifo(fifo)
    for path in (original, fifo):
      manifest = self.changed(path=str(path))
      with patch('openpilot.tools.cyber_autotune.evidence.os.read', side_effect=AssertionError('no content read')):
        result = verify_evidence(manifest, self.approve(manifest))
      self.assertEqual(result.status, 'BLOCKED')

  def test_unsupported_platform_blocked(self):
    with patch('openpilot.tools.cyber_autotune.evidence.os.name', 'nt'):
      self.assert_blocked_without_open(self.manifest, self.policy)

  def test_unknown_schema_and_invalid_types(self):
    for manifest in (replace(self.manifest, schema_version=True), replace(self.manifest, datasets=[]),
                     self.changed(previously_seen=1), self.changed(size_bytes=True)):
      self.assert_blocked_without_open(manifest)

  def test_coverage_gap_blocks_before_read(self):
    group = replace(self.manifest.datasets[0].group, strata=('straight',))
    self.assert_blocked_without_open(self.changed(group=group))

  def test_late_holdout_blocks_earlier_development_file(self):
    manifest = replace(self.manifest, datasets=(self.manifest.datasets[0], replace(self.manifest.datasets[1], role='holdout')))
    self.assert_blocked_without_open(manifest)

  def test_symlink_swap_after_preflight_never_reads_target(self):
    preflight = evidence._preflight
    original = Path(self.manifest.datasets[0].path)

    def swap_after_preflight(manifest, policy):
      result = preflight(manifest, policy)
      self.assertEqual(result[0], ())
      original.unlink()
      original.symlink_to(self.manifest.datasets[1].path)
      return result

    with patch.object(evidence, '_preflight', side_effect=swap_after_preflight), \
         patch.object(evidence.os, 'read', side_effect=AssertionError('symlink target must not be read')):
      result = verify_evidence(self.manifest, self.policy)
    self.assertEqual(result.status, 'BLOCKED')

  def test_file_metadata_mutation_during_read(self):
    read = os.read
    original = Path(self.manifest.datasets[0].path)
    before = original.stat()

    def mutate_after_read(fd, size):
      data = read(fd, size)
      os.utime(original, ns=(before.st_atime_ns, before.st_mtime_ns + 10_000_000_000))
      return data

    with patch.object(evidence.os, 'read', side_effect=mutate_after_read):
      result = verify_evidence(self.manifest, self.policy)
    self.assertEqual(result.status, 'BLOCKED')
    self.assertEqual(result.artifacts_verified, 0)

  def test_artifact_cannot_gain_coverage_by_group_relabeling(self):
    for copied in (False, True):
      with self.subTest(copied=copied):
        duplicates = []
        for item in self.manifest.datasets:
          path = item.path
          if copied:
            copy = Path(path).with_name(Path(path).name + '-copy')
            copy.write_bytes(Path(path).read_bytes())
            path = str(copy)
          group = replace(item.group, route_group=item.group.route_group + '-relabeled', day_group=item.group.day_group + '-relabeled')
          duplicates.append(replace(item, dataset_id=item.dataset_id + '-repeat', path=path, group=group))
        manifest = replace(self.manifest, datasets=self.manifest.datasets + tuple(duplicates))
        coverage = replace(self.minimums, minimum_counts=tuple((name, 2) for name in sorted(REQUIRED_STRATA)))
        policy = replace(self.approve(manifest), allowed_paths=tuple(dict.fromkeys(item.path for item in manifest.datasets)), coverage=coverage)
        result = verify_evidence(manifest, policy)
        self.assertEqual(result.status, 'BLOCKED')
        self.assertIn('ARTIFACT_GROUP_CONFLICT', result.blockers)
        self.assertEqual(result.artifacts_verified, 0)


class TestCoverage(unittest.TestCase):
  def setUp(self):
    self.policy = CoveragePolicy(HASH, tuple((key, 1) for key in sorted(REQUIRED_STRATA)))

  def test_corpus_union_not_each_window(self):
    groups = tuple(CoverageGroup('v', 'r', 'd', (name,)) for name in sorted(REQUIRED_STRATA))
    result = summarize_coverage(groups, self.policy)
    self.assertTrue(result.sufficient)
    self.assertEqual(set(dict(result.counts).values()), {1})

  def test_repeats_do_not_inflate_groups(self):
    group = CoverageGroup('v', 'r', 'd', tuple(sorted(REQUIRED_STRATA)))
    policy = replace(self.policy, minimum_counts=tuple((name, 2) for name in sorted(REQUIRED_STRATA)))
    result = summarize_coverage((group,) * 20, policy)
    self.assertFalse(result.sufficient)
    self.assertEqual(set(dict(result.counts).values()), {1})

  def test_distinct_reviewed_groups(self):
    group = CoverageGroup('v', 'r', 'd', tuple(sorted(REQUIRED_STRATA)))
    other = replace(group, route_group='r2', day_group='d2')
    result = summarize_coverage((group, other), self.policy)
    self.assertEqual(set(dict(result.counts).values()), {2})

  def test_missing_and_invalid_group(self):
    for groups in ((), (CoverageGroup('v', '', 'd', ('straight',)),),
                   (CoverageGroup('v', 'r', 'd', ('invented',)),),
                   (CoverageGroup('v', 'r', 'd', ('straight', 'straight')),)):
      self.assertFalse(summarize_coverage(groups, self.policy).sufficient)


if __name__ == '__main__':
  unittest.main()
