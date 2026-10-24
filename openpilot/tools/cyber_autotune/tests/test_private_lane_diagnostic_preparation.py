"""Constructed metadata only; no actual private frame/path is read."""

import copy
from pathlib import Path
import unittest
from unittest.mock import patch
from openpilot.tools.cyber_autotune.lane_tail_report import seal, unseal

try:
  from openpilot.tools.cyber_autotune import private_lane_diagnostic_preparation as d
except ImportError:
  d = None


def metadata():
  return [
    {'route_sha256': 'a' * 64, 'segment_sha256': 'b' * 64, 'frame_ordinal': i, 'timestamp_ns': i * 100000000, 'metadata_source_sha256': 'c' * 64}
    for i in range(12)
  ]


class TestPrivatePreparation(unittest.TestCase):
  def setUp(self):
    self.assertIsNotNone(d, 'Missing private metadata-only preparation')
    self.policy = d.freeze_policy(interval=2, offset=0, holdout_modulo=3, holdout_residue=1, timestamp='2026-10-08T00:00:00Z')
    self.attestation = {
      'private_frames_opened': False,
      'detector_outputs_opened': False,
      'image_sampling_used': False,
      'confidence_sampling_used': False,
      'metadata_role': 'PREEXISTING_NONIMAGE_INDEX',
      'scope': 'TEST_ONLY',
      'inventory_frozen_at': '2026-10-08T00:00:01Z',
    }

  def manifest(self):
    return d.freeze_manifest(metadata(), self.policy, d.frozen_detector(), self.attestation)

  def test_latest_completed_detector_identity_is_exact(self):
    x = d.frozen_detector()
    self.assertEqual(x['detector'], 'CLRerNet')
    self.assertEqual(x['environment_sha256'], 'a4f0529fef22655b8e7509022f7f06acf4250c2a72681dc649801a829f2655e5')
    for key in ('source_sha256', 'weight_sha256', 'config_sha256', 'preprocessing_sha256', 'postprocessing_sha256'):
      self.assertEqual(len(x[key]), 64)

  def test_policy_determinism_and_bounds(self):
    self.assertEqual(self.policy, d.freeze_policy(interval=2, offset=0, holdout_modulo=3, holdout_residue=1, timestamp='2026-10-08T00:00:00Z'))
    for args in ((0, 0, 3, 1), (2, 2, 3, 1), (2, 0, 1, 0), (2, 0, 3, 3), (True, 0, 3, 1)):
      with self.assertRaises(ValueError):
        d.freeze_policy(interval=args[0], offset=args[1], holdout_modulo=args[2], holdout_residue=args[3], timestamp='2026-10-08T00:00:00Z')

  def test_disjoint_deterministic_holdout_before_any_inputs(self):
    x = self.manifest()
    self.assertEqual(x, self.manifest())
    self.assertEqual([r['frame_ordinal'] for r in x['selected']], [0, 2, 4, 6, 8, 10])
    self.assertEqual([r['frame_ordinal'] for r in x['selected'] if r['role'] == 'HOLDOUT'], [2, 8])
    self.assertEqual(x['status'], 'TEST_ONLY_MANIFEST_READY')
    self.assertFalse(x['private_input_allowed'])
    self.assertEqual(x['execution'], 'NOT_RUN')

  def test_manifest_freeze_does_not_read_any_input_file(self):
    detector = d.frozen_detector()
    original_open = Path.open

    def repo_source_only(path, *args, **kwargs):
      if not path.resolve().is_relative_to(d.ROOT) or path.suffix not in ('.py', '.json', '.md'):
        raise AssertionError('Private input open forbidden')
      return original_open(path, *args, **kwargs)

    with patch.object(Path, 'open', autospec=True, side_effect=repo_source_only):
      x = d.freeze_manifest(metadata(), self.policy, detector, self.attestation)
    self.assertEqual(len(x['selected']), 6)

  def test_open_before_freeze_or_cherry_picking_rejected(self):
    for key in ('private_frames_opened', 'detector_outputs_opened', 'image_sampling_used', 'confidence_sampling_used'):
      att = copy.deepcopy(self.attestation)
      att[key] = True
      with self.assertRaises(ValueError):
        d.freeze_manifest(metadata(), self.policy, d.frozen_detector(), att)
    att = copy.deepcopy(self.attestation)
    att['inventory_frozen_at'] = '2026-10-07T00:00:00Z'
    with self.assertRaises(ValueError):
      d.freeze_manifest(metadata(), self.policy, d.frozen_detector(), att)

  def test_extra_private_paths_gps_content_and_duplicate_rows_rejected(self):
    for key in ('local_path', 'GPS', 'EXIF', 'confidence', 'modelV2', 'daylight_from_image'):
      m = metadata()
      m[0][key] = 'NOT_ALLOWED'
      with self.assertRaises(ValueError):
        d.freeze_manifest(m, self.policy, d.frozen_detector(), self.attestation)
    m = metadata()
    m.append(m[0])
    with self.assertRaises(ValueError):
      d.freeze_manifest(m, self.policy, d.frozen_detector(), self.attestation)

  def test_detector_identity_mutation_rejected(self):
    for key in ('source_sha256', 'weight_sha256', 'config_sha256', 'environment_sha256', 'preprocessing_sha256', 'postprocessing_sha256'):
      detector = unseal(d.frozen_detector())
      detector[key] = 'f' * 64
      with self.assertRaises(ValueError):
        d.freeze_manifest(metadata(), self.policy, seal(detector), self.attestation)

  def test_private_public_cache_separation_without_filesystem_crawl(self):
    with patch.object(Path, 'exists', side_effect=AssertionError('Directory crawl forbidden')):
      x = d.directory_contract('/local/private', '/local/public', '/local/private/cache')
    self.assertTrue(x['future_resolved_no_follow_check_required'])
    for roots in (
      ('/local/private', '/local/private/public', '/local/private/cache'),
      ('/local/private', '/local/public', '/local/public/cache'),
      ('/local/private', '/local/public', '/local/private/../public/cache'),
    ):
      with self.assertRaises(ValueError):
        d.directory_contract(*roots)

  def test_publication_contains_no_route_frame_ids_paths_or_timestamps(self):
    summary = d.publication_summary(self.manifest())
    text = str(summary)
    for secret in ('a' * 64, 'b' * 64, 'c' * 64, 'frame_ordinal', 'timestamp_ns', 'selected', 'local_path', 'EXIF'):
      self.assertNotIn(secret, text)
    self.assertEqual(summary['sample_counts'], {'DIAGNOSTIC': 4, 'HOLDOUT': 2})

  def test_holdout_is_pending_no_fabricated_labels(self):
    x = d.human_holdout(self.manifest())
    self.assertEqual(x['status'], 'TEST_ONLY_HOLDOUT_PROTOCOL')
    self.assertIsNone(x['annotations'])
    self.assertFalse(x['human_validation_complete'])

  def test_execution_denied_even_if_resealed_as_authorized(self):
    x = self.manifest()
    with self.assertRaisesRegex(ValueError, 'PRIVATE_INPUT_OPEN_PROHIBITED_THIS_INCREMENT'):
      d.require_execution(x)
    x = unseal(x)
    x['private_input_allowed'] = True
    x['execution'] = 'AUTHORIZED'
    with self.assertRaises(ValueError):
      d.require_execution(seal(x))

  def test_nonqualifying_output_contract_has_no_truth_error(self):
    x = d.output_contract()
    self.assertEqual(x['unit'], 'PIXEL_DOMAIN_ONLY')
    self.assertFalse(x['localization_error_against_truth_allowed'])
    self.assertFalse(x['qualification_allowed'])
    self.assertFalse(x['sealed_reference_allowed'])

  def test_private_preparation_pending_without_real_inventory(self):
    x = d.pending()
    self.assertEqual(x['status'], 'PROPOSED_NOT_RUN')
    self.assertIsNone(x['manifest_sha256'])
    self.assertFalse(x['private_input_allowed'])

  def test_freeze_detaches_caller_metadata(self):
    rows = metadata()
    x = d.freeze_manifest(rows, self.policy, d.frozen_detector(), self.attestation)
    before = copy.deepcopy(x)
    rows[0]['frame_ordinal'] = 100
    self.policy['interval'] = 100
    self.assertEqual(x, before)

  def test_network_or_device_roots_rejected_without_access(self):
    for root in ('//server/share/private', r'\\server\share\private', r'\\?\C:\private'):
      with self.assertRaises(ValueError):
        d.directory_contract(root, root + '-public', root + '/cache')
