import tempfile
import unittest
from pathlib import Path

from openpilot.tools.cyber_autotune import lane_public_publication as p
from openpilot.tools.cyber_autotune.lane_tail_report import seal
from openpilot.tools.cyber_autotune.native_protocol import digest, canonical


class TestPublicPublication(unittest.TestCase):
  def test_analysis_parent_and_self_hash(self):
    full = seal({'schema': 'PUBLIC_FULL_DIAGNOSTIC_ANALYSIS_V1', 'completion_sha256': 'a' * 64, 'processed': 11888, 'expected': 11888})
    subset = seal({'schema': 'PUBLIC_HISTORICAL_SUBSET_DERIVED_FROM_COMPLETED_FULL_RUN_V1', 'processed': 119,
                   'parent_full_completion_sha256': 'a' * 64, 'historical_subset_protocol_sha256': p.a.HISTORICAL_PROTOCOL_SHA,
                   'original_full_receipts_sha256': 'b' * 64})
    p.validate_analysis_parents({'receipt_sha256': 'a' * 64}, full, subset, 'b' * 64)
    for field, val in [('completion_sha256', 'c' * 64), ('processed', 11887), ('expected', 11889)]:
      with self.subTest(field=field), self.assertRaises(ValueError):
        p.validate_analysis_parents({'receipt_sha256': 'a' * 64}, seal({**p.unseal(full), field: val}), subset, 'b' * 64)
    with self.assertRaises(ValueError):
      p.validate_analysis_parents({'receipt_sha256': 'a' * 64}, full, {**subset, 'processed': 118}, 'b' * 64)
    with self.assertRaises(ValueError):
      p.validate_analysis_parents({'receipt_sha256': 'a' * 64}, full, subset, 'c' * 64)

  def test_wrong_subset_parent_and_protocol(self):
    full = seal({'schema': 'PUBLIC_FULL_DIAGNOSTIC_ANALYSIS_V1', 'completion_sha256': 'a' * 64, 'processed': 11888, 'expected': 11888})
    base = {'schema': 'PUBLIC_HISTORICAL_SUBSET_DERIVED_FROM_COMPLETED_FULL_RUN_V1', 'processed': 119,
            'parent_full_completion_sha256': 'a' * 64, 'historical_subset_protocol_sha256': p.a.HISTORICAL_PROTOCOL_SHA,
            'original_full_receipts_sha256': 'b' * 64}
    for field in ('parent_full_completion_sha256', 'historical_subset_protocol_sha256'):
      with self.subTest(field=field), self.assertRaises(ValueError):
        p.validate_analysis_parents({'receipt_sha256': 'a' * 64}, full, seal({**base, field: 'd' * 64}), 'b' * 64)

  def test_crash_cache_binding(self):
    hashes = {'00000.json': 'a' * 64, '00001.json': 'b' * 64}
    run = 'c' * 64
    snapshot = seal({'rows': hashes, 'run_sha256': run})
    kill = seal({'cached_rows_before_restart': {'00000.json': hashes['00000.json']}, 'run_sha256': run,
                 'intentional_exit_code': -9, 'kill_scope': 'OWNED_SESSION_PROCESS_GROUP_ONLY', 'completed_marker_present': False})
    p.validate_cached_hashes(run, snapshot, kill, hashes)
    for bad in ({**hashes, '00001.json': 'd' * 64}, {'00000.json': hashes['00000.json']}, {**hashes, '00002.json': 'd' * 64}):
      with self.subTest(hashes=bad), self.assertRaises(ValueError):
        p.validate_cached_hashes(run, snapshot, kill, bad)
    with self.assertRaises(ValueError):
      p.validate_cached_hashes('e' * 64, snapshot, kill, hashes)
    with self.assertRaises(ValueError):
      p.validate_cached_hashes(run, snapshot, seal({**p.unseal(kill), 'cached_rows_before_restart': {'00000.json': 'd' * 64}}), hashes)

  def test_immutable_all_derived_outputs(self):
    with tempfile.TemporaryDirectory() as temp:
      path = Path(temp) / 'progress.json'
      value = seal({'reviewed': 0})
      p.publish_immutable(path, value)
      before = path.read_bytes()
      p.publish_immutable(path, value)
      self.assertEqual(path.read_bytes(), before)
      with self.assertRaises(ValueError):
        p.publish_immutable(path, seal({'reviewed': 1}))
      self.assertEqual(path.read_bytes(), before)
      text = Path(temp) / 'record.md'
      p.publish_immutable_text(text, 'pending\n')
      with self.assertRaises(ValueError):
        p.publish_immutable_text(text, 'complete\n')
      self.assertEqual(text.read_text(), 'pending\n')

  def test_public_pending_requires_exact_manifest_index(self):
    from openpilot.tools.cyber_autotune.tests.test_lane_tail_review import manifest as make_manifest
    manifest = make_manifest()
    # TEST scope is never public evidence, even when all other links match.
    index = seal({'manifest_sha256': manifest['receipt_sha256'], 'rows': [], 'review_status': p.c.review_status(manifest, [])})
    with self.assertRaises(ValueError):
      p.validate_public_pending(manifest, manifest, index)
    self.assertEqual(digest(canonical([])), digest(b'[]'))

  def test_public_pending_rejects_other_manifest_and_missing_rows(self):
    from openpilot.tools.cyber_autotune.tests.test_lane_tail_review import manifest as make_manifest
    original = make_manifest()
    manifest = seal({**p.unseal(original), 'scope': 'PUBLIC_COMMA10K_HUMAN_REVIEW'})
    index = seal({'manifest_sha256': manifest['receipt_sha256'], 'rows': [], 'review_status': p.c.review_status(manifest, [])})
    self.assertEqual(p.validate_public_pending(manifest, manifest, index)['reviewed'], 0)
    with self.assertRaises(ValueError):
      p.validate_public_pending(manifest, original, index)
    for field, val in [('manifest_sha256', 'f' * 64), ('rows', ['a' * 64]),
                       ('review_status', seal({**p.unseal(index['review_status']), 'expected': 1}))]:
      with self.subTest(field=field), self.assertRaises(ValueError):
        p.validate_public_pending(manifest, manifest, seal({**p.unseal(index), field: val}))

  def test_resume_proof_links_reject_foreign_and_stale_proof(self):
    rows = {'00000.json': 'a' * 64, '00001.json': 'b' * 64}
    run = 'c' * 64
    marker = {'processed': 11888, 'expected': 11888}
    snapshot = seal({'rows': rows, 'run_sha256': run})
    kill = seal({'cached_rows_before_restart': {'00000.json': rows['00000.json']}, 'run_sha256': run,
                 'intentional_exit_code': -9, 'kill_scope': 'OWNED_SESSION_PROCESS_GROUP_ONLY', 'completed_marker_present': False})
    file_hashes = {name: digest(name.encode()) for name in ['kill', 'snapshot', 'completion', 'window1', 'progress', 'resume']}
    window = seal({'status': 'INTERRUPTED_RESUMABLE', 'processed_rows': 2, 'expected': 11888,
                   'kill_proof_sha256': file_hashes['kill'], 'cached_rows_reused_unchanged': 1, 'completion_marker_file_sha256': None})
    progress = seal({'run_sha256': run, 'completed_frames': 2, 'expected_frames': 11888, 'failure_records': []})
    resume = seal({'status': 'COMPLETED', 'processed_rows': 11888, 'expected': 11888,
                   'kill_proof_sha256': file_hashes['kill'], 'cached_rows_reused_unchanged': 1,
                   'completion_marker_file_sha256': file_hashes['completion']})
    proof = seal({'status': 'COMPLETED', 'run_sha256': run, 'cached_rows_reused_unchanged': 2, 'expected': 11888, 'processed': 11888,
                  'cache_snapshot_file_sha256': file_hashes['snapshot'], 'window1_result_file_sha256': file_hashes['window1'],
                  'window1_progress_file_sha256': file_hashes['progress'], 'final_result_file_sha256': file_hashes['resume']})
    p.validate_resume_links(run, marker, snapshot, kill, window, progress, resume, proof, rows, file_hashes)
    for field, val in [('run_sha256', 'd' * 64), ('cached_rows_reused_unchanged', 1), ('cache_snapshot_file_sha256', 'e' * 64),
                       ('window1_result_file_sha256', 'e' * 64), ('final_result_file_sha256', 'e' * 64)]:
      with self.subTest(field=field), self.assertRaises(ValueError):
        p.validate_resume_links(run, marker, snapshot, kill, window, progress, resume,
                                seal({**p.unseal(proof), field: val}), rows, file_hashes)
    with self.assertRaises(ValueError):
      p.validate_resume_links(run, marker, snapshot, kill, window, progress,
                              seal({**p.unseal(resume), 'completion_marker_file_sha256': 'e' * 64}), proof, rows, file_hashes)

  def test_completed_store_reverifies_index_and_artifacts(self):
    from unittest.mock import patch
    with tempfile.TemporaryDirectory() as temp:
      root = Path(temp)
      protocol = root / 'protocol.json'
      inputs = root / 'inputs.json'
      p.s.atomic_json(protocol, {'pairs': [{'image': f'imgs/{i:05d}.png'} for i in range(11888)]})
      p.s.atomic_json(inputs, {'files': []})
      run = seal({'protocol_file_sha256': digest(protocol.read_bytes()), 'manifest_file_sha256': digest(inputs.read_bytes())})
      p.s.atomic_json(root / 'run-freeze.json', run)
      with patch.object(p.ui, 'require_frozen_metric_sources'), patch.object(p.r, 'validate_protocol_pairs'), patch.object(p.s, 'DurableRun') as store:
        store.return_value.verify_completed.side_effect = ValueError('COMPLETION_ARTIFACT_SHA_MISMATCH')
        with self.assertRaisesRegex(ValueError, 'COMPLETION_ARTIFACT_SHA_MISMATCH'):
          p.verify_completed_store(root, protocol, inputs)
        store.return_value.verify_completed.assert_called_once()
      p.s.atomic_json(inputs, {'files': [], 'changed': True})
      with patch.object(p.ui, 'require_frozen_metric_sources'), patch.object(p.s, 'DurableRun') as store:
        with self.assertRaisesRegex(ValueError, 'INPUT_FREEZE'):
          p.verify_completed_store(root, protocol, inputs)
        store.assert_not_called()

  def test_immutable_text_refuses_symlink(self):
    with tempfile.TemporaryDirectory() as temp:
      target = Path(temp) / 'old.md'
      target.write_text('pending\n')
      alias = Path(temp) / 'alias.md'
      alias.symlink_to(target)
      with self.assertRaises(ValueError):
        p.publish_immutable_text(alias, 'pending\n')
      self.assertEqual(target.read_text(), 'pending\n')

  def test_orphan_human_row_cannot_publish_pending_zero(self):
    from openpilot.tools.cyber_autotune.tests.test_lane_tail_review import manifest as make_manifest
    manifest = seal({**p.unseal(make_manifest()), 'scope': 'PUBLIC_COMMA10K_HUMAN_REVIEW'})
    with tempfile.TemporaryDirectory() as temp:
      root = Path(temp)
      (root / 'annotations').mkdir()
      p.s.atomic_json(root / 'review-freeze.json', manifest)
      p.require_no_annotation_rows(root, manifest)
      p.s.atomic_json(root / 'annotations/00000.json', {'orphan': True})
      with self.assertRaises(ValueError):
        p.require_no_annotation_rows(root, manifest)

  def test_environment_self_hash_and_full_frozen_identity(self):
    value = {'python': '3.11.9'}
    env = {**value, 'environment_sha256': digest(canonical(value))}
    p.validate_frozen_environment(env, env)
    with self.assertRaises(ValueError):
      p.validate_frozen_environment({**env, 'python': 'other'}, env)
    other = {'python': 'other'}
    with self.assertRaises(ValueError):
      p.validate_frozen_environment({**other, 'environment_sha256': digest(canonical(other))}, env)

  def test_publication_certificate_rejects_tampered_partial_and_stale_sources(self):
    with tempfile.TemporaryDirectory() as temp:
      root = Path(temp)
      p.s.atomic_json(root / 'a.json', seal({'status': 'COMPLETED'}))
      files = {'a.json': digest((root / 'a.json').read_bytes())}
      certificate = seal({'schema': 'PUBLIC_DIAGNOSTIC_PUBLICATION_CERTIFICATE_V1',
                          'publication_source_sha256': digest(Path(p.__file__).read_bytes()), 'artifact_file_sha256': files})
      p.verify_publication_certificate(root, certificate, {'a.json'})
      with self.assertRaises(ValueError):
        p.verify_publication_certificate(root, certificate, {'a.json', 'missing.json'})
      p.s.atomic_json(root / 'a.json', seal({'status': 'PARTIAL'}))
      with self.assertRaises(ValueError):
        p.verify_publication_certificate(root, certificate, {'a.json'})
      with self.assertRaises(ValueError):
        p.verify_publication_certificate(root, seal({**p.unseal(certificate), 'publication_source_sha256': 'f' * 64}), {'a.json'})
