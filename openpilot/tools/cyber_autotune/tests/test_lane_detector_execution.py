import copy
import hashlib
import tempfile
import unittest
from pathlib import Path

import numpy as np

from openpilot.tools.cyber_autotune import lane_detector_execution as e
from openpilot.tools.cyber_autotune.lane_marking_metrics import marking_frame


class TestLaneDetectorExecution(unittest.TestCase):
  def environment(self):
    return {
      'schema': 'LANE_DETECTOR_ENVIRONMENT_V1',
      'detector': 'CLRerNet',
      'repository_url': 'https://github.com/hirotomusiker/CLRerNet',
      'repository_commit': 'dae038f67da57e292e5293a68c9c1c2922de13c2',
      'license': 'Apache-2.0',
      'python': '3.11.9',
      'packages': {'torch': '2.1.0+cu121', 'torchvision': '0.16.0+cu121', 'mmcv': '2.1.0', 'mmengine': '0.10.5', 'mmdet': '3.3.0'},
      'platform': 'Linux test fixture',
      'device': 'cuda:0',
      'device_name': 'fixture GPU',
      'cuda_runtime': '12.1',
      'driver': 'fixture',
      'compiler': 'fixture nvcc',
      'source_bundle_sha256': 'a' * 64,
      'config_sha256': 'b' * 64,
      'weight_sha256': '424422f1008a5fe1717d52bbc5f631dcc2731808f8adb96110d126fa83d3a8aa',
      'preprocessing_sha256': 'c' * 64,
      'postprocessing_sha256': 'd' * 64,
      'nms_binary_sha256': 'e' * 64,
      'package_manifest_sha256': 'f' * 64,
      'toolchain_manifest_sha256': '1' * 64,
      'diagnostic_source_sha256': '2' * 64,
      'public_protocol_file_sha256': '3' * 64,
      'public_input_manifest_file_sha256': '4' * 64,
      'determinism': {'seed': 0, 'deterministic_algorithms': True, 'cudnn_benchmark': False, 'allow_tf32': False, 'cublas_workspace_config': ':4096:8'},
    }

  def test_freeze_deterministic_and_every_identity_field_bound(self):
    data = self.environment()
    frozen = e.freeze_environment(data)
    self.assertEqual(frozen, e.freeze_environment(copy.deepcopy(data)))
    changed = dict(data, platform='changed platform')
    self.assertNotEqual(frozen['environment_sha256'], e.freeze_environment(changed)['environment_sha256'])
    self.assertNotIn('reference_ready', frozen)

  def test_wrong_weight_source_package_and_missing_environment_rejected(self):
    for key, value in [('weight_sha256', '0' * 64), ('repository_commit', '0' * 40), ('python', '3.12.13'), ('device', 'cpu')]:
      with self.subTest(key=key), self.assertRaises(ValueError):
        e.freeze_environment(dict(self.environment(), **{key: value}))
    invalid = self.environment()
    invalid['packages']['torch'] = '2.2.0'
    with self.assertRaises(ValueError):
      e.freeze_environment(invalid)

  def test_environment_nonfinite_unsafe_determinism_and_extra_fields_rejected(self):
    for extra in ({'modelV2_used': True}, {'confidence': float('nan')}):
      with self.assertRaises(ValueError):
        e.freeze_environment(dict(self.environment(), **extra))
    bad = self.environment()
    bad['determinism']['deterministic_algorithms'] = False
    with self.assertRaises(ValueError):
      e.freeze_environment(bad)

  def test_no_follow_file_binding_and_mismatch(self):
    with tempfile.TemporaryDirectory() as tmp:
      path = Path(tmp) / 'config'
      path.write_bytes(b'fixed config')
      expected = hashlib.sha256(b'fixed config').hexdigest()
      self.assertEqual(e.verify_file(path, expected), expected)
      with self.assertRaises(ValueError):
        e.verify_file(path, 'a' * 64)
      link = Path(tmp) / 'link'
      link.symlink_to(path)
      with self.assertRaises(ValueError):
        e.verify_file(link, expected)

  def reproduction(self, metric=0.8111, count=34680):
    return e.reproduction_receipt(e.freeze_environment(self.environment()), {
      'dataset': 'CULane', 'split': 'test', 'expected_frames': 34680, 'evaluated_frames': count,
      'dataset_manifest_sha256': '2' * 64, 'command': ['python', 'tools/test.py', 'frozen_config', 'frozen_weight'],
      'result_artifact_sha256': '3' * 64, 'official_f1_fraction': metric, 'exit_code': 0,
    })

  def test_reproduction_uses_published_rounding_not_arbitrary_tolerance(self):
    self.assertEqual(self.reproduction()['status'], 'PUBLIC_DETECTOR_REPRODUCED')
    self.assertEqual(self.reproduction(0.8110)['status'], 'DETECTOR_REPRODUCTION_FAILED')
    self.assertAlmostEqual(self.reproduction(0.8110)['absolute_difference_percentage_points'], 0.01)

  def test_partial_split_cannot_reproduce_even_perfect_score(self):
    report = self.reproduction(0.8111, 1)
    self.assertEqual(report['status'], 'DETECTOR_REPRODUCTION_BLOCKED')
    self.assertIn('INCOMPLETE_OFFICIAL_SPLIT', report['blockers'])

  def test_bad_reproduction_metric_and_split_rejected(self):
    for value in (True, float('nan'), -0.1, 1.1):
      with self.subTest(metric=value), self.assertRaises(ValueError):
        self.reproduction(value)

  def test_no_result_is_blocked_not_metric_failure(self):
    self.assertEqual(self.reproduction(None, 0)['status'], 'DETECTOR_REPRODUCTION_BLOCKED')

  def test_localization_distribution_counts_and_width_normalization(self):
    mask = np.zeros((3, 20), dtype=bool)
    mask[:, 5] = True
    first = marking_frame(mask, [[7.0, y] for y in range(3)])
    second = marking_frame(mask, [])
    result = e.localization_summary([first, second])
    self.assertEqual(result['pred_to_gt']['p90'], 2.0)
    self.assertEqual(result['pred_to_gt']['p99'], 2.0)
    self.assertEqual(result['normalized_pred_to_gt']['p95'], 0.1)
    self.assertEqual(result['available_frame_ratio'], 0.5)
    self.assertEqual(result['detection_failure_rate'], 0.5)
    self.assertEqual(result['unmatched_gt_ratio'], 1.0)
    self.assertFalse(result['ego_lane_association_evaluated'])
    self.assertIsNone(result['meter_error'])

  def test_empty_gt_not_counted_as_detector_failure(self):
    result = e.localization_summary([marking_frame(np.zeros((3, 20), dtype=bool), [])])
    self.assertEqual(result['gt_eligible_frames'], 0)
    self.assertIsNone(result['detection_failure_rate'])
    self.assertEqual(result['unavailable_frames'], 1)

  def test_localization_tampered_report_rejected(self):
    report = marking_frame(np.zeros((3, 20), dtype=bool), [])
    report['status'] = 'PIXEL_DIAGNOSTIC'
    with self.assertRaises(ValueError):
      e.localization_summary([report])

  def test_private_gate_stays_closed_with_reproduced_f1_and_no_justified_pixel_gate(self):
    gate = e.private_pixel_gate(e.freeze_environment(self.environment()), self.reproduction())
    self.assertFalse(gate['private_input_access_allowed'])
    self.assertIn('PUBLIC_PIXEL_QUALIFICATION_THRESHOLD_UNJUSTIFIED', gate['blockers'])
    self.assertEqual(gate['qualification'], 'INDEPENDENT_REFERENCE_UNAVAILABLE')
    self.assertEqual(gate['vehicle_status'], ['NOT_READY', 'REAL_VEHICLE_UNVERIFIED', 'VEHICLE_ACTIVATION_BLOCKED'])

  def test_tampered_environment_or_reproduction_cannot_reach_private_gate(self):
    frozen = e.freeze_environment(self.environment())
    frozen['python'] = 'changed'
    with self.assertRaises(ValueError):
      e.private_pixel_gate(frozen, self.reproduction())
    reproduction = self.reproduction()
    reproduction['status'] = 'PUBLIC_GT_PASS_PIXEL_ONLY'
    with self.assertRaises(ValueError):
      e.private_pixel_gate(e.freeze_environment(self.environment()), reproduction)

  def test_not_run_command_cannot_claim_success_exit_code(self):
    env = e.freeze_environment(self.environment())
    run = copy.deepcopy(self.reproduction(None, 0)['run'])
    run['exit_code'] = None
    report = e.reproduction_receipt(env, run)
    self.assertIn('OFFICIAL_COMMAND_NOT_RUN', report['blockers'])
    run['evaluated_frames'] = 34680
    run['official_f1_fraction'] = .8111
    with self.assertRaises(ValueError):
      e.reproduction_receipt(env, run)
