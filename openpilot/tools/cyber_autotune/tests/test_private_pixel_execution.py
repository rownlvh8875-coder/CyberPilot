"""Diagnostic exception does not change the historical qualification gate."""
import copy
from pathlib import Path
import tempfile
import unittest

from openpilot.tools.cyber_autotune import private_pixel_execution as p
from openpilot.tools.cyber_autotune.lane_tail_report import seal
from openpilot.tools.cyber_autotune import lane_public_storage as s

SHA = 'a' * 64
STAMP = '2026-10-08T00:00:00Z'


class TestPrivateExecution(unittest.TestCase):
  def setUp(self):
    self.policy = p.sampling_policy(STAMP)
    self.metadata = [
      {'route_id': SHA, 'segment_id': f'{i:064x}', 'source_sha256': SHA, 'source_bytes': 100,
       'frame_count': 100, 'width': 526, 'height': 330, 'fps': 20.0, 'codec': 'h264', 'camera_role': 'NARROW_ROAD',
       'source_key': f'segment-{i}/qcamera.ts'} for i in range(3)
    ]
    self.manifest = p.freeze_manifest(self.metadata, self.policy, SHA, STAMP)
    self.auth = p.authorize(self.manifest, SHA[:40], STAMP, acknowledged=True)

  def test_policy_bounded_and_roles_disjoint(self):
    self.assertEqual(self.policy['max_frames'], 300)
    selected = self.manifest['selected']
    self.assertEqual(len(selected), 15)
    dev = {r['sample_id'] for r in selected if r['role'] == 'DEVELOPMENT'}
    hold = {r['sample_id'] for r in selected if r['role'] == 'HOLDOUT'}
    self.assertEqual((len(dev), len(hold)), (12, 3))
    self.assertFalse(dev & hold)

  def test_manifest_deterministic_order(self):
    self.assertEqual(self.manifest, p.freeze_manifest(list(reversed(self.metadata)), self.policy, SHA, STAMP))

  def test_requires_explicit_authorization(self):
    with self.assertRaises(ValueError):
      p.authorize(self.manifest, SHA[:40], STAMP, acknowledged=False)
    with self.assertRaises(ValueError):
      p.require_execution(self.manifest, None)

  def test_policy_before_content(self):
    with self.assertRaises(ValueError):
      p.freeze_manifest(self.metadata, self.policy, SHA, STAMP, content_opened=True)

  def test_unknown_metadata_and_model_stream_rejected(self):
    for change in ({'source_key': 'qlog.zst'}, {'camera_role': 'MODEL_V2'}, {'candidate': SHA}):
      with self.subTest(change=change), self.assertRaises(ValueError):
        p.freeze_manifest([{**r, **change} for r in self.metadata], self.policy, SHA, STAMP)

  def test_source_key_traversal_rejected(self):
    with self.assertRaises(ValueError):
      p.freeze_manifest([{**r, 'source_key': '../qcamera.ts'} for r in self.metadata], self.policy, SHA, STAMP)

  def test_identity_drift_rejected_even_resealed(self):
    changed = copy.deepcopy(self.auth)
    changed['detector']['config_sha256'] = 'b' * 64
    changed = seal({k: v for k, v in changed.items() if k != 'receipt_sha256'})
    with self.assertRaises(ValueError):
      p.require_execution(self.manifest, changed)

  def test_holdout_cannot_decode(self):
    row = next(r for r in self.manifest['selected'] if r['role'] == 'HOLDOUT')
    with self.assertRaises(ValueError):
      p.require_frame(self.manifest, self.auth, row['sample_id'])

  def test_prior_design_remains_closed(self):
    from openpilot.tools.cyber_autotune import private_lane_diagnostic_preparation as old
    with self.assertRaises(ValueError):
      old.require_execution(old.freeze_manifest(
        [{'route_sha256': SHA, 'segment_sha256': SHA, 'frame_ordinal': i, 'timestamp_ns': i, 'metadata_source_sha256': SHA} for i in range(4)],
        old.freeze_policy(interval=1, offset=0, holdout_modulo=2, holdout_residue=0, timestamp=STAMP),
        old.frozen_detector(), {'private_frames_opened': False, 'detector_outputs_opened': False, 'image_sampling_used': False,
                                'confidence_sampling_used': False, 'metadata_role': 'PREEXISTING_NONIMAGE_INDEX',
                                'scope': 'TEST_ONLY', 'inventory_frozen_at': STAMP}))

  def row(self):
    sample = self.manifest['selected'][0]
    return p.frame_receipt(self.manifest, self.auth, sample['sample_id'], SHA,
                           {'image_geometry': [330, 526], 'lane_count': 1, 'points': [[20.0, 200]],
                            'lanes': [{'confidence': .8, 'points': [[20.0, 200]]}]})

  def test_frame_binds_identity(self):
    row = self.row()
    p.validate_frame(row, self.manifest, self.auth)
    row['image_sha256'] = 'b' * 64
    with self.assertRaises(ValueError):
      p.validate_frame(row, self.manifest, self.auth)

  def test_nonfinite_prediction_rejected(self):
    sample = self.manifest['selected'][0]
    for bad in (float('nan'), float('inf')):
      with self.subTest(bad=bad), self.assertRaises(ValueError):
        p.frame_receipt(self.manifest, self.auth, sample['sample_id'], SHA,
                        {'image_geometry': [330, 526], 'lane_count': 1, 'points': [[bad, 200]],
                         'lanes': [{'confidence': .8, 'points': [[bad, 200]]}]})

  def test_gt_metrics_cannot_enter(self):
    row = self.row()
    row['localization_error'] = 0
    row = seal({k: v for k, v in row.items() if k != 'receipt_sha256'})
    with self.assertRaises(ValueError):
      p.validate_frame(row, self.manifest, self.auth)

  def test_publication_whitelist(self):
    summary = p.progress_summary(self.manifest, self.auth, [self.row()])
    text = str(summary)
    for key in ('source_key', 'timestamp', 'route_id', 'sample_id', 'image_sha256'):
      self.assertNotIn(key, text)
    self.assertFalse(summary['qualification_allowed'])
    self.assertFalse(summary['sealed_reference_allowed'])
    self.assertEqual(summary['status'], 'PRIVATE_PIXEL_DIAGNOSTIC_PARTIAL')

  def test_complete_requires_all_dev(self):
    self.assertNotEqual(p.progress_summary(self.manifest, self.auth, [self.row()])['status'], 'PRIVATE_PIXEL_DIAGNOSTIC_COMPLETE')
    rows = [
      p.frame_receipt(self.manifest, self.auth, r['sample_id'], SHA,
                      {'image_geometry': [330, 526], 'lane_count': 0, 'points': [], 'lanes': []})
      for r in self.manifest['selected'] if r['role'] == 'DEVELOPMENT'
    ]
    result = p.progress_summary(self.manifest, self.auth, rows)
    self.assertEqual(result['status'], 'PRIVATE_PIXEL_DIAGNOSTIC_COMPLETE')
    self.assertEqual(result['no_output_rate'], 1.0)
    self.assertEqual(result['private_human_status'], 'PRIVATE_HUMAN_HOLDOUT_PENDING')
    self.assertEqual(result['temporal'], 'NOT_EVALUATED_NO_CONSECUTIVE_SAMPLES')

  def test_duplicate_result_rejected(self):
    with self.assertRaises(ValueError):
      p.progress_summary(self.manifest, self.auth, [self.row(), self.row()])

  def test_durable_resume_and_corruption(self):
    row = self.row()
    def validator(value):
      p.validate_frame(value, self.manifest, self.auth)
    with tempfile.TemporaryDirectory() as temp:
      store = s.DurableRun(temp, self.auth, ['test'])
      store.put(0, row, validator)
      restarted = s.DurableRun(temp, self.auth, ['test'])
      self.assertEqual(restarted.recover(validator)[0], row)
      path = Path(temp) / 'rows/00000.json'
      path.write_text('{}')
      with self.assertRaises(ValueError):
        restarted.recover(validator)

  def test_cache_must_be_outside_repo(self):
    with self.assertRaises(ValueError):
      p.private_directories(Path(__file__).resolve().parents[4], Path(__file__).resolve().parents[4] / 'private-cache')

  def test_approximate_never_promotes(self):
    self.assertFalse(self.auth['reference_promotable'])
    self.assertFalse(self.auth['vehicle_activation_allowed'])
    self.assertEqual(self.auth['ground_truth'], 'ABSENT')

  def test_unusable_encoded_sources_are_explicit_not_silent_skip(self):
    unavailable = [{'source_sha256': SHA, 'source_bytes': 189, 'status': 'PRIVATE_CAMERA_SOURCE_UNUSABLE',
                    'reason': '188_BYTE_TS_REQUIRED'}]
    manifest = p.freeze_manifest(self.metadata, self.policy, SHA, STAMP, unavailable_sources=unavailable)
    auth = p.authorize(manifest, SHA[:40], STAMP, acknowledged=True)
    result = p.progress_summary(manifest, auth, [])
    self.assertEqual(result['inventory_unusable_sources'], 1)
    self.assertEqual(result['discovered_camera_segments'], 4)
