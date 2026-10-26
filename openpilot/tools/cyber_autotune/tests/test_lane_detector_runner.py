import copy
import hashlib
import tempfile
import unittest
from pathlib import Path

from openpilot.tools.cyber_autotune import lane_detector_runner as r


class TestPublicLaneDetectorRunner(unittest.TestCase):
  def manifest(self):
    return {
      'schema': 'PUBLIC_DIAGNOSTIC_INPUT_MANIFEST_V1',
      'dataset_commit': '6c205fe4c43cc53b2b1befafb1060d0606555027',
      'protocol_file_sha256': 'a' * 64,
      'files': [{'path': 'imgs/0.png', 'sha256': hashlib.sha256(b'image bytes').hexdigest(),
                 'size': len(b'image bytes'), 'git_blob_sha1': hashlib.sha1(b'blob 11\0image bytes').hexdigest()}],
      'semantic_content_opened': False,
    }

  def test_public_manifest_rejects_private_model_candidate_and_unpinned_sources(self):
    for change in ({'dataset_commit': '0' * 40}, {'semantic_content_opened': True}, {'candidate_outputs_used': True}):
      with self.subTest(change=change), self.assertRaises(ValueError):
        r.validate_manifest(dict(self.manifest(), **change))
    for path in ('../private.png', '/tmp/private.png', 'imgs/../private.png', 'imgs//0.png', 'imgs/./0.png', 'modelV2/path.png', 'raw/log.png'):
      m = self.manifest()
      m['files'][0]['path'] = path
      with self.subTest(path=path), self.assertRaises(ValueError):
        r.validate_manifest(m)

  def test_manifest_duplicate_and_size_type_rejected(self):
    m = self.manifest()
    m['files'].append(copy.deepcopy(m['files'][0]))
    with self.assertRaises(ValueError):
      r.validate_manifest(m)
    m = self.manifest()
    m['files'][0]['size'] = True
    with self.assertRaises(ValueError):
      r.validate_manifest(m)

  def test_verified_public_bytes_only_no_symlink_escape(self):
    with tempfile.TemporaryDirectory() as tmp:
      root = Path(tmp)
      (root / 'imgs').mkdir()
      (root / 'imgs/0.png').write_bytes(b'image bytes')
      r.verify_inputs(root, self.manifest())
      (root / 'imgs/0.png').write_bytes(b'changed')
      with self.assertRaises(ValueError):
        r.verify_inputs(root, self.manifest())

  def test_symlink_parent_rejected_before_any_file_open(self):
    with tempfile.TemporaryDirectory() as tmp:
      root = Path(tmp)
      (root / 'elsewhere').mkdir()
      (root / 'elsewhere/0.png').write_bytes(b'image bytes')
      (root / 'imgs').symlink_to(root / 'elsewhere')
      with self.assertRaises(ValueError):
        r.verify_inputs(root, self.manifest())

  def test_network_namespace_required(self):
    with self.assertRaises(ValueError):
      r.require_network_isolation('lo eth0')
    r.require_network_isolation('lo')

  def test_exact_repeatability_failure_is_not_warning(self):
    self.assertEqual(r.require_repeatability([{'points': [[2., 1]]}], [{'points': [[2., 1]]}]), True)
    with self.assertRaises(ValueError):
      r.require_repeatability([{'points': [[2., 1]]}], [{'points': [[2.1, 1]]}])

  def test_runtime_snapshot_mismatch_rejected_even_rehashed_environment(self):
    first = {'python': '3.11.9', 'nms_binary_sha256': 'a' * 64}
    self.assertTrue(r.require_runtime_match(first, dict(first)))
    with self.assertRaises(ValueError):
      r.require_runtime_match(first, dict(first, nms_binary_sha256='b' * 64))

  def test_namespace_interfaces_use_proc_view_not_host_sysfs(self):
    proc = 'Inter-| Receive | Transmit\n face |bytes packets\n lo: 0 0 0 0\n'
    self.assertEqual(r.network_interfaces(proc), 'lo')
    r.require_network_isolation(r.network_interfaces(proc))
    with self.assertRaises(ValueError):
      r.require_network_isolation(r.network_interfaces(proc + ' eth0: 0 0 0 0\n'))

  def test_only_exact_unused_training_keys_may_be_absent(self):
    r.validate_inference_state_keys(sorted(r.TRAINING_ONLY_MISSING_KEYS), [])
    for missing, unexpected in ((['backbone.base_layer.0.weight'], []),
                                (sorted(r.TRAINING_ONLY_MISSING_KEYS) + ['bbox_head.cls_layers.0.weight'], []),
                                (sorted(r.TRAINING_ONLY_MISSING_KEYS), ['unexpected.weight'])):
      with self.subTest(missing=missing), self.assertRaises(ValueError):
        r.validate_inference_state_keys(missing, unexpected)

  def test_revision_chain_cannot_hide_prior_gt_inspection(self):
    initial_sha = 'a' * 64
    revision = {'initial_protocol_file_sha256': initial_sha, 'prior_result_file_sha256': 'b' * 64,
                'semantic_GT_outputs_seen_before_this_revision': True,
                'evidence_tier': 'POST_RESULT_ADAPTER_CORRECTION_DIAGNOSTIC_NOT_QUALIFICATION'}
    r.validate_revision_chain(revision, 'c' * 64, initial_sha)
    with self.assertRaises(ValueError):
      r.validate_revision_chain(dict(revision, semantic_GT_outputs_seen_before_this_revision=False), 'c' * 64, initial_sha)
    with self.assertRaises(ValueError):
      r.validate_revision_chain(revision, 'c' * 64, 'd' * 64)

  def test_protocol_pairs_reject_wrong_mask_duplicate_and_blob_mismatch(self):
    image = self.manifest()['files'][0]
    mask = dict(image, path='masks/0.png')
    manifest = self.manifest()
    manifest['files'].append(mask)
    pair = {'image': image['path'], 'mask': mask['path'],
            'image_git_blob_sha1': image['git_blob_sha1'], 'mask_git_blob_sha1': mask['git_blob_sha1']}
    protocol = {'pairs': [pair]}
    r.validate_protocol_pairs(protocol, manifest)
    for pairs in ([pair, pair], [dict(pair, mask='masks/1.png')], [dict(pair, image_git_blob_sha1='0' * 40)]):
      with self.subTest(pairs=pairs), self.assertRaises(ValueError):
        r.validate_protocol_pairs({'pairs': pairs}, manifest)
    r.require_original_geometry((10, 20), (10, 20))
    with self.assertRaises(ValueError):
      r.require_original_geometry((10, 20), (10, 21))

  def test_protocol_revision_cannot_change_sample_or_detector_selection(self):
    initial = {'pairs': [{'image': 'imgs/0.png'}], 'confidence_threshold': .41}
    r.require_unchanged_declaration(initial, dict(initial))
    for changed in (dict(initial, pairs=[]), dict(initial, confidence_threshold=.1)):
      with self.assertRaises(ValueError):
        r.require_unchanged_declaration(initial, changed)

  def test_bound_json_buffers_reject_mutation_after_runtime_snapshot(self):
    with tempfile.TemporaryDirectory() as tmp:
      path = Path(tmp) / 'protocol'
      data = b'{"fixed":true}'
      path.write_bytes(data)
      self.assertEqual(r.read_bound_bytes(path, hashlib.sha256(data).hexdigest()), data)
      path.write_bytes(b'{"fixed":false}')
      with self.assertRaises(ValueError):
        r.read_bound_bytes(path, hashlib.sha256(data).hexdigest())

  def test_weight_snapshot_is_sealed_and_survives_original_mutation(self):
    with tempfile.TemporaryDirectory() as tmp:
      path = Path(tmp) / 'weight'
      data = b'public weights fixture'
      path.write_bytes(data)
      with r.sealed_weight(path, hashlib.sha256(data).hexdigest()) as sealed:
        path.write_bytes(b'changed')
        self.assertEqual(Path(sealed).read_bytes(), data)
        with self.assertRaises(OSError):
          with open(sealed, 'wb') as stream:
            stream.write(b'overwrite')
      with self.assertRaises(ValueError):
        with r.sealed_weight(path, hashlib.sha256(data).hexdigest()):
          pass
