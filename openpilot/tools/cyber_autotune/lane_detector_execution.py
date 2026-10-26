"""Public detector execution receipts and diagnostics. No private reader or promotion.

Receipt hashes bind declarations, not authentication of benchmark execution.
This protocol deliberately keeps private access closed while CyberPilot pixel
qualification thresholds lack an independently justified error requirement.
"""

import math
import os
import stat
from decimal import Decimal, ROUND_HALF_UP

import numpy as np

from openpilot.tools.cyber_autotune.contracts import is_sha256
from openpilot.tools.cyber_autotune.native_protocol import canonical, digest
from openpilot.tools.cyber_autotune.lane_marking_metrics import aggregate

REPOSITORY = 'https://github.com/hirotomusiker/CLRerNet'
COMMIT = 'dae038f67da57e292e5293a68c9c1c2922de13c2'
WEIGHT = '424422f1008a5fe1717d52bbc5f631dcc2731808f8adb96110d126fa83d3a8aa'
PACKAGES = {'torch': '2.1.0+cu121', 'torchvision': '0.16.0+cu121', 'mmcv': '2.1.0', 'mmengine': '0.10.5', 'mmdet': '3.3.0'}
DETERMINISM = {'seed': 0, 'deterministic_algorithms': True, 'cudnn_benchmark': False, 'allow_tf32': False, 'cublas_workspace_config': ':4096:8'}
SHA_FIELDS = {'source_bundle_sha256', 'config_sha256', 'weight_sha256', 'preprocessing_sha256', 'postprocessing_sha256',
              'nms_binary_sha256', 'package_manifest_sha256', 'toolchain_manifest_sha256', 'diagnostic_source_sha256',
              'public_protocol_file_sha256', 'public_input_manifest_file_sha256'}
ENV_FIELDS = SHA_FIELDS | {'schema', 'detector', 'repository_url', 'repository_commit', 'license', 'python', 'packages', 'platform',
                          'device', 'device_name', 'cuda_runtime', 'driver', 'compiler', 'determinism'}
REPRO_FIELDS = {'dataset', 'split', 'expected_frames', 'evaluated_frames', 'dataset_manifest_sha256', 'command',
                'result_artifact_sha256', 'official_f1_fraction', 'exit_code'}
CULANE_TEST_FRAMES = 34680
PUBLISHED_NON_EMA_F1_PERCENT = Decimal('81.11')


def _seal(payload, name='receipt_sha256'):
  return dict(payload, **{name: digest(canonical(payload))})


def _unseal(receipt, name='receipt_sha256'):
  if type(receipt) is not dict or name not in receipt or not is_sha256(receipt[name]):
    raise ValueError('INVALID_RECEIPT')
  payload = {k: v for k, v in receipt.items() if k != name}
  if digest(canonical(payload)) != receipt[name]:
    raise ValueError('RECEIPT_BINDING_MISMATCH')
  return payload


def freeze_environment(data):
  if type(data) is not dict or set(data) != ENV_FIELDS:
    raise ValueError('EXACT_EXECUTION_ENVIRONMENT_REQUIRED')
  if (
    data['schema'] != 'LANE_DETECTOR_ENVIRONMENT_V1' or data['detector'] != 'CLRerNet'
    or data['repository_url'] != REPOSITORY or data['repository_commit'] != COMMIT or data['license'] != 'Apache-2.0'
    or data['python'] != '3.11.9' or data['device'] != 'cuda:0' or data['cuda_runtime'] != '12.1'
    or data['weight_sha256'] != WEIGHT or type(data['packages']) is not dict
    or any(data['packages'].get(k) != v for k, v in PACKAGES.items())
    or any(type(k) is not str or type(v) is not str or not k or not v for k, v in data['packages'].items())
    or data['determinism'] != DETERMINISM
    or canonical(data['determinism']) != canonical(DETERMINISM)
    or any(not is_sha256(data[k]) for k in SHA_FIELDS)
    or any(type(data[k]) is not str or not data[k] for k in ('platform', 'device_name', 'driver', 'compiler'))
  ):
    raise ValueError('UNSUPPORTED_EXECUTION_IDENTITY')
  return _seal(data, 'environment_sha256')


def verify_file(path, expected_sha256):
  if not is_sha256(expected_sha256):
    raise ValueError('INVALID_EXPECTED_FILE_SHA256')
  try:
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as stream:
      if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
        raise ValueError('REGULAR_EXECUTION_FILE_REQUIRED')
      actual = digest(stream.read())
  except OSError as exc:
    raise ValueError('EXECUTION_FILE_NO_FOLLOW_READ_FAILED') from exc
  if actual != expected_sha256:
    raise ValueError('EXECUTION_FILE_SHA256_MISMATCH')
  return actual


def reproduction_receipt(environment, run):
  freeze_environment(_unseal(environment, 'environment_sha256'))
  if (
    type(run) is not dict or set(run) != REPRO_FIELDS or run['dataset'] != 'CULane' or run['split'] != 'test'
    or type(run['expected_frames']) is not int or run['expected_frames'] != CULANE_TEST_FRAMES
    or type(run['evaluated_frames']) is not int or not 0 <= run['evaluated_frames'] <= CULANE_TEST_FRAMES
    or not is_sha256(run['dataset_manifest_sha256']) or not is_sha256(run['result_artifact_sha256'])
    or (run['exit_code'] is not None and type(run['exit_code']) is not int)
    or (run['exit_code'] is None and (run['evaluated_frames'] != 0 or run['official_f1_fraction'] is not None))
    or type(run['command']) is not list or not run['command']
    or any(type(v) is not str or not v for v in run['command'])
  ):
    raise ValueError('INVALID_OFFICIAL_REPRODUCTION_INPUT')
  metric = run['official_f1_fraction']
  if metric is not None and (type(metric) not in (int, float) or not math.isfinite(metric) or not 0 <= metric <= 1):
    raise ValueError('INVALID_F1_FRACTION')
  blockers = []
  if run['evaluated_frames'] != CULANE_TEST_FRAMES:
    blockers.append('INCOMPLETE_OFFICIAL_SPLIT')
  if metric is None:
    blockers.append('OFFICIAL_METRIC_NOT_RUN')
  if run['exit_code'] is None:
    blockers.append('OFFICIAL_COMMAND_NOT_RUN')
  elif run['exit_code'] != 0:
    blockers.append('OFFICIAL_COMMAND_FAILED')
  percent = Decimal(str(metric)) * 100 if metric is not None else None
  match = percent is not None and percent.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP) == PUBLISHED_NON_EMA_F1_PERCENT
  status = 'DETECTOR_REPRODUCTION_BLOCKED' if blockers else 'PUBLIC_DETECTOR_REPRODUCED' if match else 'DETECTOR_REPRODUCTION_FAILED'
  return _seal({
    'schema': 'OFFICIAL_CLRERNET_REPRODUCTION_V1', 'environment_sha256': environment['environment_sha256'], 'run': run,
    'reported_f1_percentage': float(PUBLISHED_NON_EMA_F1_PERCENT), 'absolute_difference_percentage_points':
    float(abs(percent - PUBLISHED_NON_EMA_F1_PERCENT)) if percent is not None else None,
    'comparison_rule': 'NON_EMA_RELEASE_F1_ROUNDED_TWO_DECIMAL_PERCENT_MATCH', 'status': status, 'blockers': blockers,
    'pixel_qualification_granted': False, 'metric_qualification_granted': False,
  })


def _distribution(values):
  return {'sample_count': len(values), **{k: float(np.quantile(values, q, method='linear')) if values else None
                                        for k, q in (('median', .5), ('p90', .9), ('p95', .95), ('p99', .99), ('maximum', 1.0))}}


def localization_summary(reports):
  base = aggregate(reports)  # Validates exact schemas, counts, units and hashes.
  eligible = sum(r['gt_runs'] > 0 for r in reports)
  runs, points = base['gt_runs'], sum(r['pred_points'] for r in reports)
  payload = {
    'schema': 'LANE_MARKING_LOCALIZATION_DISTRIBUTION_V1', 'scope': 'PUBLIC_PIXEL_DIAGNOSTIC_NOT_QUALIFICATION',
    'total_frames': len(reports), 'gt_eligible_frames': eligible,
    'usable_frames': sum(r['status'] == 'PIXEL_DIAGNOSTIC' for r in reports),
    'unavailable_frames': sum(r['status'] == 'REFERENCE_UNAVAILABLE' for r in reports),
    'available_frame_ratio': 1 - base['unavailable_frame_rate'],
    'detection_failure_rate': sum(r['gt_runs'] > 0 and r['pred_points'] == 0 for r in reports) / eligible if eligible else None,
    'mask_coverage': base['coverage'],
    'false_positive_marking_ratio': sum(r['off_marking_pred_points'] for r in reports) / points if points else None,
    'unmatched_gt_ratio': sum(r['gt_runs'] - r['covered_gt_runs'] for r in reports) / runs if runs else None,
    'missing_row_support_ratio': base['unavailable_gt_runs'] / runs if runs else None,
    'source_receipts_sha256': digest(canonical(base['source_receipts'])), 'unit': 'px', 'normalized_unit': 'image_width_fraction',
    'ego_lane_association_evaluated': False, 'meter_error': None, 'reference_promotable': False,
  }
  for direction, field in (('pred_to_gt', 'pred_errors_px'), ('gt_to_pred', 'gt_errors_px')):
    payload[direction] = _distribution([v for r in reports for v in r[field]])
    payload['normalized_' + direction] = _distribution([v / r['geometry'][1] for r in reports for v in r[field]])
  return _seal(payload)


def private_pixel_gate(environment, reproduction):
  frozen = freeze_environment(_unseal(environment, 'environment_sha256'))
  rep = _unseal(reproduction)
  if set(rep) != {'schema', 'environment_sha256', 'run', 'reported_f1_percentage', 'absolute_difference_percentage_points',
                  'comparison_rule', 'status', 'blockers', 'pixel_qualification_granted', 'metric_qualification_granted'}:
    raise ValueError('EXACT_REPRODUCTION_RECEIPT_REQUIRED')
  if reproduction != reproduction_receipt(frozen, rep['run']):
    raise ValueError('REPRODUCTION_RECEIPT_RECOMPUTATION_MISMATCH')
  blockers = ['PUBLIC_PIXEL_QUALIFICATION_THRESHOLD_UNJUSTIFIED', 'INDEPENDENT_REFERENCE_UNAVAILABLE']
  if rep['status'] != 'PUBLIC_DETECTOR_REPRODUCED':
    blockers.insert(0, rep['status'])
  return _seal({
    'schema': 'PRIVATE_PIXEL_ACCESS_GATE_V1', 'environment_sha256': frozen['environment_sha256'],
    'reproduction_sha256': reproduction['receipt_sha256'], 'status': 'BLOCKED', 'blockers': blockers,
    'private_input_access_allowed': False, 'qualification': 'INDEPENDENT_REFERENCE_UNAVAILABLE',
    'sealed_reference_generation_allowed': False,
    'vehicle_status': ['NOT_READY', 'REAL_VEHICLE_UNVERIFIED', 'VEHICLE_ACTIVATION_BLOCKED'],
  })
