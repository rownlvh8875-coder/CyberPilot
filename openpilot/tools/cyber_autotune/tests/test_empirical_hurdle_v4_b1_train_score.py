"""Only synthetic TRAIN bytes and recorded provenance; never actual evidence."""

import copy
import gzip
import importlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from openpilot.tools.cyber_autotune import empirical_hurdle_v4_b1_evidence as b1
from openpilot.tools.cyber_autotune.tests.test_empirical_hurdle_v4_b1_evidence import array, canonical, fixture, seal, sha

try:
  score = importlib.import_module('openpilot.tools.cyber_autotune.empirical_hurdle_v4_b1_train_score')
except ModuleNotFoundError:
  score = None


def train_fixture(root):
  old = fixture(root)
  for owner in ('V4_REPEAT_1', 'V4_REPEAT_2'):
    path = Path(old['roots'][owner])
    manifest = json.loads((path / 'manifest.json').read_bytes())
    files = manifest['files']
    for job in old['jobs']:
      prefix = f"candidates/{job['candidate_id']}/{job['fold']}"
      raw, _ = array()
      mixed = b'{"threshold":"UNREAD_PRIVATE_SENTINEL","heads":"UNREAD"}'
      members = {
        'receipt.json': sha(mixed),
        'combined_probability.npy.gz': sha(raw),
        'STATIC_coefficients.npy.gz': 'c' * 64,
        'MOVE_coefficients.npy.gz': 'd' * 64,
      }
      sub = seal({'schema': 'V4_TRAIN_MANIFEST', 'train_receipt_sha256': job['train_receipt'], 'files': members})
      job['train_manifest'] = sub['receipt_sha256']
      final = seal(
        {
          'schema': 'V4_TRAIN_FINALIZED',
          'status': 'TRAIN_COMPLETE',
          'candidate_id': job['candidate_id'],
          'fold': job['fold'],
          'train_anchor_sha256': job['train_anchor'],
          'authorization_sha256': 'a' * 64,
          'train_manifest_sha256': sub['receipt_sha256'],
          'model_threshold_receipt_sha256': job['train_receipt'],
        }
      )
      job['finalized_receipt'] = final['receipt_sha256']
      for name, content in (
        ('train/manifest.json', canonical(sub)),
        ('train/combined_probability.npy.gz', raw),
        ('train/receipt.json', mixed),
        ('train-finalized.json', canonical(final)),
      ):
        target = path / prefix / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        files[prefix + '/' + name] = sha(content)
      for name, digest in members.items():
        files[prefix + '/train/' + name] = digest
      devpath = path / prefix / 'one-step/receipt.json'
      dev = json.loads(devpath.read_bytes())
      dev['train_finalized_sha256'] = final['receipt_sha256']
      dev = seal({k: v for k, v in dev.items() if k != 'receipt_sha256'})
      devpath.write_bytes(canonical(dev))
      files[prefix + '/one-step/receipt.json'] = sha(canonical(dev))
    manifest = seal({k: v for k, v in manifest.items() if k != 'receipt_sha256'})
    raw = canonical(manifest)
    (path / 'manifest.json').write_bytes(raw)
    old['manifests'][owner] = {'receipt_sha256': manifest['receipt_sha256'], 'raw_sha256': sha(raw)}
  old_binding = seal(
    {
      'schema': 'CYBERPILOT_V4_B1_PRIVATE_BINDING_V1',
      'request': {k: v for k, v in old.items() if k != 'binding_sha256'},
      'mixed_carrier_open_authorized': False,
    }
  )
  old['binding_sha256'] = old_binding['receipt_sha256']
  previous_result = b1.run(old)
  assert previous_result['field_status_counts'] == {'PASS': 192, 'AUTHORITY_BLOCKED': 32}
  previous_resume = b1.verify_only(previous_result, sha(canonical(previous_result)), old_binding['receipt_sha256'])
  previous = {'binding': old_binding, 'result': previous_result, 'resume': previous_resume}
  request = {
    'authorized': True,
    'binding_sha256': 'e' * 64,
    'previous_binding_sha256': old_binding['receipt_sha256'],
    'previous_result_receipt_sha256': previous_result['receipt_sha256'],
    'previous_result_raw_sha256': sha(canonical(previous_result)),
    'mount_root': old['mount_root'],
    'mount_identity': old['mount_identity'],
    'roots': {k: v for k, v in old['roots'].items() if k != 'V1_REFERENCE'},
    'manifests': {k: v for k, v in old['manifests'].items() if k != 'V1_REFERENCE'},
    'jobs': copy.deepcopy(old['jobs']),
    'authorization': old['authorization']['V4'],
  }
  request['order_provenance'] = dict(b1.ORDER_SOURCES, **{'empirical_hurdle_v3_store.py': 'eadb505681a5e46f6cf447afcf4ccc1d68c6977c5a0c2e2ded8944465450567b'})
  return request, previous


class FormatTests(unittest.TestCase):
  def setUp(self):
    self.assertIsNotNone(score, 'Restricted TRAIN-score verifier missing')

  def inspect(self, raw=None, n=3):
    raw = array()[0] if raw is None else raw
    return score.inspect_score(raw, sha(raw), n)

  def test_compressed_expected_but_inner_digests_observed_only(self):
    row = self.inspect()
    self.assertEqual(row['shape'], [3])
    self.assertEqual(row['dtype'], '<f8')
    self.assertEqual(row['payload_sha256'], sha(bytes(24)))
    self.assertEqual(row['compressed_identity'], 'MANIFEST_BOUND_COMPRESSED_FILE_VERIFIED')
    self.assertEqual(row['inner_identity'], 'LIVE_NPY_AND_PAYLOAD_HASH_OBSERVED')
    self.assertFalse(row['original_descriptor_compared'])

  def test_wrong_compressed_digest_rejected(self):
    with self.assertRaisesRegex(ValueError, 'HASH_CONFLICT'):
      score.inspect_score(array()[0], '0' * 64, 3)

  def test_exact_npy_v1_and_v2(self):
    self.assertEqual(self.inspect(array(version=2)[0])['shape'], [3])

  def test_wrong_full_count(self):
    with self.assertRaises(ValueError):
      self.inspect(n=4)

  def test_wrong_dtype_without_cast(self):
    with self.assertRaises(ValueError):
      self.inspect(array(dtype='<i8')[0])

  def test_non_vector_shape_rejected(self):
    with self.assertRaises(ValueError):
      self.inspect(array(header="{'descr':'<f8','fortran_order':False,'shape':(3,1)}")[0])

  def test_fortran_order_rejected(self):
    with self.assertRaises(ValueError):
      self.inspect(array(header="{'descr':'<f8','fortran_order':True,'shape':(3,)}")[0])

  def test_object_or_executable_or_duplicate_header_rejected(self):
    for header in (
      "{'descr':'|O','fortran_order':False,'shape':(3,)}",
      "dict(descr='<f8',fortran_order=False,shape=(3,))",
      "{'descr':'|O','descr':'<f8','fortran_order':False,'shape':(3,)}",
    ):
      with self.subTest(header=header), self.assertRaises(ValueError):
        self.inspect(array(header=header)[0])

  def test_truncated_gzip(self):
    with self.assertRaises(ValueError):
      self.inspect(array()[0][:-3])

  def test_single_gzip_member_only(self):
    with self.assertRaises(ValueError):
      self.inspect(array()[0] + gzip.compress(b'not-approved'))

  def test_gzip_trailing_and_crc_rejected(self):
    raw = array()[0]
    for invalid in (raw + b'trailing', raw[:-8] + bytes(8)):
      with self.subTest(invalid=sha(invalid)), self.assertRaises(ValueError):
        self.inspect(invalid)

  def test_bounded_compressed_and_decompressed_bytes(self):
    for raw in (array(data=bytes(200000))[0], array()[0] + bytes(300000)):
      with self.subTest(raw=sha(raw)), self.assertRaises(ValueError):
        self.inspect(raw)

  def test_no_truncate_or_padding_repair(self):
    with self.assertRaises(ValueError):
      self.inspect(array(data=bytes(25))[0])


class IntegrationTests(unittest.TestCase):
  def setUp(self):
    self.assertIsNotNone(score, 'Restricted TRAIN-score verifier missing')
    self.tmp = tempfile.TemporaryDirectory()
    self.addCleanup(self.tmp.cleanup)
    self.request, self.previous = train_fixture(Path(self.tmp.name))

  def path(self, owner='V4_REPEAT_1', member='train/combined_probability.npy.gz'):
    return Path(self.request['roots'][owner]) / 'candidates/HRI_D00_L01/FOLD_A' / member

  def test_manifest_only_full_completion_without_old_payload_reopens(self):
    with patch.object(os, 'scandir', side_effect=AssertionError('scan')), patch.object(os, 'listdir', side_effect=AssertionError('scan')):
      result = score.run(self.request, self.previous)
    self.assertEqual(result['status'], 'B1_TRAIN_SCORE_INTEGRITY_AND_RECORDED_ALIGNMENT_VERIFIED')
    self.assertEqual(result['new_train_fields_pass'], 32)
    self.assertEqual(result['prior_fields_carried_forward'], 192)
    self.assertEqual(result['cumulative_fields_verified'], 224)
    self.assertEqual(result['train_three_field_aligned_jobs'], 32)
    self.assertEqual(result['train_equal_field_pairs'], 32)
    self.assertEqual(result['reads']['array_file_openings'], 64)
    self.assertEqual(result['reads']['metadata_file_openings'], 130)
    self.assertEqual(result['mixed_carrier_openings'], 0)
    self.assertEqual(result['source_writes'], 0)
    self.assertEqual(result['train_rowwise_gate'], 'NOT_SAVED')
    self.assertEqual(result['replica_payload_equality'], 'REPLICA_PAYLOAD_EQUALITY_NOT_FULLY_REVERIFIED')

  def test_sensitive_carriers_and_old_arrays_are_never_allowlisted_or_opened(self):
    allow = score.paths(self.request)
    self.assertEqual(len(allow), 194)
    self.assertNotIn(str(self.path(member='train/receipt.json')), allow)
    self.assertNotIn(str(self.path(member='train/STATIC_coefficients.npy.gz')), allow)
    original = b1.GuardedReader.read

    def guarded(reader, path, cap, kind):
      self.assertIn(path, allow)
      self.assertFalse(path.endswith('/train/receipt.json'))
      return original(reader, path, cap, kind)

    with patch.object(b1.GuardedReader, 'read', guarded), patch.object(json, 'load', side_effect=AssertionError('full JSON mixed read')):
      result = score.run(self.request, self.previous)
    self.assertEqual(result['new_train_fields_pass'], 32)
    self.assertNotIn('UNREAD_PRIVATE_SENTINEL', json.dumps(result))

  def test_absent_grant_before_source_open(self):
    result = score.run({**self.request, 'authorized': False}, self.previous)
    self.assertEqual(result['reads']['metadata_file_openings'], 0)
    self.assertEqual(result['status'], 'B1_TRAIN_INPUT_CONFLICT_FAIL_CLOSED')

  def test_wrong_candidate_or_fold_before_open(self):
    self.request['jobs'][0]['fold'] = 'FOLD_C'
    self.assertEqual(score.run(self.request, self.previous)['reads']['array_file_openings'], 0)

  def test_prior_proof_seal_or_raw_binding_mismatch_stops_before_read(self):
    self.previous['result']['fields'][1]['status'] = 'INPUT_INSUFFICIENT'
    result = score.run(self.request, self.previous)
    self.assertEqual(result['reads']['metadata_file_openings'], 0)
    self.assertEqual(result['cumulative_fields_verified'], 0)

  def test_same_n_without_source_order_contract_is_not_alignment(self):
    self.request['order_provenance'] = {}
    result = score.run(self.request, self.previous)
    self.assertEqual(result['status'], 'B1_TRAIN_PROVENANCE_INSUFFICIENT')
    self.assertEqual(result['reads']['array_file_openings'], 0)

  def test_untrusted_root_manifest_hash(self):
    self.request['manifests']['V4_REPEAT_1']['raw_sha256'] = '1' * 64
    self.assertEqual(score.run(self.request, self.previous)['reads']['array_file_openings'], 0)

  def test_submanifest_raw_change_fails_before_score(self):
    self.path(member='train/manifest.json').write_bytes(b'{}')
    result = score.run(self.request, self.previous)
    self.assertEqual(result['status'], 'B1_TRAIN_INPUT_CONFLICT_FAIL_CLOSED')
    self.assertEqual(result['reads']['array_file_openings'], 0)

  def test_finalized_raw_change_fails_before_score(self):
    self.path(member='train-finalized.json').write_bytes(b'{}')
    self.assertEqual(score.run(self.request, self.previous)['reads']['array_file_openings'], 0)

  def test_compressed_hash_conflict_is_not_retried(self):
    self.path().write_bytes(b'changed')
    result = score.run(self.request, self.previous)
    self.assertEqual(result['status'], 'B1_TRAIN_INPUT_CONFLICT_FAIL_CLOSED')
    self.assertEqual(result['reads']['array_file_openings'], 1)

  def test_no_pass_if_second_replica_missing(self):
    self.path('V4_REPEAT_2').unlink()
    result = score.run(self.request, self.previous)
    self.assertEqual(result['new_train_fields_pass'], 0)
    self.assertEqual(result['fields'][0]['status'], 'INPUT_INSUFFICIENT')

  def test_alias_root_rejected(self):
    self.request['roots']['V4_REPEAT_2'] = self.request['roots']['V4_REPEAT_1']
    self.assertEqual(score.run(self.request, self.previous)['reads']['metadata_file_openings'], 0)

  def test_symlink_payload_rejected(self):
    path = self.path()
    path.unlink()
    path.symlink_to(self.path('V4_REPEAT_2'))
    self.assertEqual(score.run(self.request, self.previous)['status'], 'B1_TRAIN_INPUT_CONFLICT_FAIL_CLOSED')

  def test_duplicate_inode_rejected(self):
    other = self.path('V4_REPEAT_2')
    other.unlink()
    os.link(self.path(), other)
    self.assertEqual(score.run(self.request, self.previous)['status'], 'B1_TRAIN_INPUT_CONFLICT_FAIL_CLOSED')

  def test_path_traversal_rejected(self):
    self.request['roots']['V4_REPEAT_1'] += '/../r1'
    self.assertEqual(score.run(self.request, self.previous)['reads']['metadata_file_openings'], 0)

  def test_verify_only_no_source_decode_or_recomputation(self):
    result = score.run(self.request, self.previous)
    with (
      patch.object(score, 'run', side_effect=AssertionError('recompute')),
      patch.object(score, 'inspect_score', side_effect=AssertionError('decode')),
      patch.object(b1.GuardedReader, 'read', side_effect=AssertionError('source')),
    ):
      resume = score.verify_only(result, sha(canonical(result)), self.request['binding_sha256'])
    self.assertEqual(resume['recompute_calls'], 0)
    self.assertEqual(resume['source_file_openings'], 0)

  def test_resume_corruption_rejected(self):
    result = score.run(self.request, self.previous)
    rawsha = sha(canonical(result))
    result['new_train_fields_pass'] = 1
    with self.assertRaises(ValueError):
      score.verify_only(result, rawsha, self.request['binding_sha256'])

  def test_public_projection_has_no_private_paths_or_digests(self):
    result = score.run(self.request, self.previous)
    public = score.public_summary(result)
    text = json.dumps(public)
    self.assertNotIn(self.request['mount_root'], text)
    self.assertNotIn('payload_sha256', text)
    self.assertFalse(public['C_AUTHORIZED'])
    self.assertEqual(public['cumulative_fields_verified'], 224)

  def test_public_projection_rejects_poisoned_or_false_completion(self):
    result = score.run(self.request, self.previous)
    for key in ('new_train_fields_pass', 'prior_fields_carried_forward', 'cumulative_fields_verified', 'train_equal_field_pairs'):
      with self.subTest(key=key), self.assertRaises(ValueError):
        score.public_summary({**result, key: '/private/sentinel'})
    result['fields'][0]['status'] = 'INPUT_INSUFFICIENT'
    with self.assertRaises(ValueError):
      score.public_summary(result)

  def changed_chain(self, *, sub_change=None, final_change=None, root_change=None):
    job = copy.deepcopy(self.request['jobs'][0])
    root = self.request['roots']['V4_REPEAT_1']
    manifest = json.loads((Path(root) / 'manifest.json').read_bytes())
    prefix = 'candidates/HRI_D00_L01/FOLD_A/'
    sub = json.loads(self.path(member='train/manifest.json').read_bytes())
    final = json.loads(self.path(member='train-finalized.json').read_bytes())
    if sub_change:
      sub_change(sub)
    sub = seal({k: v for k, v in sub.items() if k != 'receipt_sha256'})
    job['train_manifest'] = final['train_manifest_sha256'] = sub['receipt_sha256']
    if final_change:
      final_change(final)
    final = seal({k: v for k, v in final.items() if k != 'receipt_sha256'})
    job['finalized_receipt'] = final['receipt_sha256']
    for name, row in (('train/manifest.json', sub), ('train-finalized.json', final)):
      raw = canonical(row)
      self.path(member=name).write_bytes(raw)
      manifest['files'][prefix + name] = sha(raw)
    if root_change:
      root_change(manifest['files'], prefix)
    mount = Path(self.request['mount_root']).stat()
    with b1.GuardedReader(self.request['mount_root'], (mount.st_dev, mount.st_ino), score.paths(self.request)) as reader:
      return score.chain(reader, root, manifest, job, self.request['authorization'])

  def test_unopened_mixed_canonical_link_disagreement_rejected(self):
    with self.assertRaises(ValueError):
      self.changed_chain(sub_change=lambda r: r.update(train_receipt_sha256='9' * 64))

  def test_unopened_mixed_raw_hash_declarations_must_agree(self):
    with self.assertRaisesRegex(ValueError, 'HASH_CONFLICT'):
      self.changed_chain(root_change=lambda r, p: r.update({p + 'train/receipt.json': '9' * 64}))

  def test_compressed_declarations_must_agree_before_payload_open(self):
    with self.assertRaisesRegex(ValueError, 'HASH_CONFLICT'):
      self.changed_chain(root_change=lambda r, p: r.update({p + 'train/combined_probability.npy.gz': '9' * 64}))

  def test_finalized_wrong_anchor_same_count_is_not_alignment(self):
    with self.assertRaisesRegex(ValueError, 'ALIGNMENT_NOT_PROVEN'):
      self.changed_chain(final_change=lambda r: r.update(train_anchor_sha256='9' * 64))

  def test_finalized_wrong_candidate_fold_authority_or_status_rejected(self):
    for changes in ({'candidate_id': 'HRI_D05_L01'}, {'fold': 'FOLD_B'}, {'authorization_sha256': '9' * 64}, {'status': 'NOT_COMPLETE'}):
      with self.subTest(changes=changes), self.assertRaises(ValueError):
        self.changed_chain(final_change=lambda r, changes=changes: r.update(changes))

  def test_no_source_bytes_changed_and_no_old_reference_reopen(self):
    allow = score.paths(self.request)
    before = {path: Path(path).read_bytes() for path in allow}
    result = score.run(self.request, self.previous)
    self.assertEqual(result['new_train_fields_pass'], 32)
    self.assertEqual(before, {path: Path(path).read_bytes() for path in allow})
    self.assertEqual(len(result['read_events']), 194)
