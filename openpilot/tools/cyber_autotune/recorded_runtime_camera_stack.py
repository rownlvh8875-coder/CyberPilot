"""Offline, additive recorded-runtime audit. No image/log I/O or numeric meter path.

Build-string equality is not binary attestation. Source frame-size properties
cannot admit firmware crop/phase, physical intrinsics or residual bounds.
"""
import copy
import datetime
import json
import re

import numpy as np

from openpilot.tools.cyber_autotune import camera_calibration_evidence as c
from openpilot.tools.cyber_autotune import qcamera_pixel_registration as q
from openpilot.tools.cyber_autotune.lane_tail_report import unseal
from openpilot.tools.cyber_autotune.native_protocol import digest

ROOT = c.ROOT / 'docs/cyberpilot/changes'
BUILDER = 'f5b3f77e59f1917f95e0752630ca08050463eede'
KERNEL_BASE = 'eccd146599f2e2f159d951092642689bede91632'
RELEASE_NORMALIZED_BANNER_SHA = '93c2a50c5c4defdf55ecbd72be4d10958fa76c4b18cbe2cbbc3ed30b83df6586'
RELEASE_BOOT_SHA = 'dccd7965346b0a87a9f64cb6be257f6bb5d3d0f368c8655085efc1e460527f5a'
RUNTIME_SHA = 'fbdb4f3fd44387a3f278779458da029ee1ab42007a0702db25ad9ab106cf5fc1'
SCALER_SHA = '44b507d1e36612515593e85da54d1c75a8c212981863f4b4cb7668a669d8ed3f'
PREVIOUS_SHA = '708ad7256727e69cba61e9575ec6bbe3363465f48f9ba221dcbc963281b9d25c'
HEIGHT_SHA = 'bc6eada2f78d371aaacc34b4c0ce86f46c89056a0574e3f981f32b9807fe7802'


def parse_kernel(value):
  """Normalize proc/version vs embedded Linux banner, retaining compiler/build.

  Only the first two tokens differ (Linux hostname vs Linux version). Their
  omission is explicit, not a fuzzy version-number comparison. No hostname,
  builder user/host or compiler text is published; their digest remains binding.
  """
  if not isinstance(value, str) or len(value) > 4096:
    raise ValueError('BOUNDED_KERNEL_BUILD_STRING_REQUIRED')
  line = value.strip()
  match = re.fullmatch(r'Linux \S+ ((\d+\.\d+\.\d+(?:[-+.\w]*)?) .+ (#\d+ SMP PREEMPT ' +
                       r'([A-Z][a-z]{2} [A-Z][a-z]{2} +\d{1,2} \d{2}:\d{2}:\d{2} UTC \d{4})))', line)
  if not match:
    raise ValueError('EXACT_KERNEL_BUILD_IDENTITY_REQUIRED')
  datetime.datetime.strptime(match[4], '%a %b %d %H:%M:%S UTC %Y')
  return {'release': match[2], 'normalized_sha256': digest(match[1].encode()),
          'build_ordinal': match[3].split()[0], 'normalization': 'DROP_LINUX_AND_HOST_OR_VERSION_TOKEN_STRIP_EOL'}


def bind_runtime(*, kernel, public_banner, build, os_version, device, kernel_sha256):
  c.sha(kernel_sha256)
  if digest(kernel.encode()) != kernel_sha256:
    raise ValueError('RECORDED_KERNEL_DIGEST_MISMATCH')
  observed, public = parse_kernel(kernel), parse_kernel(public_banner)
  if public['normalized_sha256'] != RELEASE_NORMALIZED_BANNER_SHA:
    raise ValueError('VERIFIED_PUBLIC_RELEASE_BANNER_REQUIRED')
  if observed != public:
    raise ValueError('RECORDED_PUBLIC_KERNEL_BUILD_MISMATCH')
  if not isinstance(build, str) or build.splitlines()[0:1] != [BUILDER]:
    raise ValueError('RECORDED_BUILDER_MISMATCH')
  if os_version.strip() != '19.8-carrot-bt1' or device != 'mici':
    raise ValueError('RECORDED_OS_OR_HARDWARE_MISMATCH')
  return c.seal({'schema': 'RECORDED_KERNEL_BINDING_V1', 'status': 'RECORDED_KERNEL_BUILD_IDENTITY_BOUND',
                 'kernel': observed, 'recorded_kernel_sha256': kernel_sha256, 'builder_commit': BUILDER,
                 'kernel_base': KERNEL_BASE, 'applied_patches_required': True, 'binary_attested': False,
                 'partition_hash_observed': False, 'verified_public_boot_sha256': RELEASE_BOOT_SHA, **q.FLAGS})


def crop_layers():
  return {'native_input_wh': [1344, 760], 'coded_wh': [528, 336], 'visible_wh': [526, 330],
          'codec_display_crop_lrtb': [0, 2, 0, 6], 'codec_padding_is_optical_crop': False,
          'application_qcamera_explicit_crop': None, 'effective_native_crop': None}


def bounded_points(values, wh):
  q.dimensions(wh)
  p = q.points(values)
  if (p < 0).any() or (p > np.asarray(wh)-1).any():
    raise ValueError('POINT_OUTSIDE_PIXEL_CENTER_INDEX_DOMAIN')
  return p


def orient(values, wh, clockwise_degrees, mirror_x):
  """Conditional test arithmetic only, not an observed stream orientation."""
  p = bounded_points(values, wh)
  if type(clockwise_degrees) is not int or clockwise_degrees not in (0, 90, 180, 270) or type(mirror_x) is not bool:
    raise ValueError('EXPLICIT_ORTHOGONAL_ORIENTATION_REQUIRED')
  x, y = p.T
  width, height = wh
  if clockwise_degrees == 90:
    x, y, width = height-1-y, x, height
  elif clockwise_degrees == 180:
    x, y = width-1-x, height-1-y
  elif clockwise_degrees == 270:
    x, y, width = y, width-1-x, height
  if mirror_x:
    x = width-1-x
  return np.column_stack((x, y)).tolist()


def hypotheses(exclusion=None):
  # No phase-semantic proof is admitted in this audit; self-declared source
  # assertions must not silently prune the conditional set.
  if exclusion is not None:
    raise ValueError('NO_EXACT_RUNTIME_PHASE_EXCLUSION_EVIDENCE_ADMITTED')
  return {'retained': list(q.RULES), 'pruned': [], 'exhaustive': False,
          'reason': 'FIRMWARE_SAMPLE_PHASE_AND_EFFECTIVE_CROP_NOT_OBSERVED'}


def conditional_envelope(values):
  p = bounded_points(values, [526, 330])
  mapped = np.asarray([q.forward(p, q.affine([1344, 760], [526, 330], [0, 0, 1344, 760], rule)) for rule in q.RULES])
  return c.seal({'schema': 'CONDITIONAL_MAPPING_ENVELOPE_V1', 'source_xy': p.tolist(),
                 'minimum_native_xy': mapped.min(axis=0).tolist(), 'maximum_native_xy': mapped.max(axis=0).tolist(),
                 'hypotheses': hypotheses(), 'assumed_crop': [0, 0, 1344, 760], 'assumed_orientation': 'IDENTITY',
                 'exhaustive': False, 'physical_uncertainty_bound': False, 'residual_bound_native_px': None,
                 **q.FLAGS})


def pinned(value, expected):
  unseal(value)
  if value['receipt_sha256'] != expected:
    raise ValueError('FROZEN_RUNTIME_AUDIT_IDENTITY_MISMATCH')
  return value


def validate_runtime(value):
  return pinned(value, RUNTIME_SHA)


def load_runtime():
  return validate_runtime(json.loads((ROOT / 'recorded-runtime-camera-stack-v1.json').read_bytes()))


def load_scaler():
  return pinned(json.loads((ROOT / 'qcamera-hardware-scaler-evidence-v1.json').read_bytes()), SCALER_SHA)


def readiness():
  runtime, scaler = load_runtime(), load_scaler()
  previous = json.loads((ROOT / 'qcamera-pixel-registration-readiness-v1.json').read_bytes())
  pinned(previous, PREVIOUS_SHA)
  height = json.loads((ROOT / 'physical-height-observation-v1.json').read_bytes())
  pinned(height, HEIGHT_SHA)
  blockers = copy.deepcopy(previous['blockers'])

  def node(key, status, evidence, condition, dependencies=()):
    blockers[key] = {'status': status, 'evidence_sha256': evidence, 'resolution_condition': condition,
                     'dependencies': list(dependencies)}

  for key, status in runtime['outcomes'].items():
    node(key, status, RUNTIME_SHA, runtime['resolution_conditions'][key], runtime['dependencies'].get(key, ()))
  for key, status in scaler['outcomes'].items():
    node(key, status, SCALER_SHA, scaler['resolution_conditions'][key], scaler['dependencies'].get(key, ()))
  node('CALIBRATION_UNCERTAINTY_PENDING', 'BLOCKED', HEIGHT_SHA, 'Actual conservative physical height uncertainty evidence')
  node('PHYSICAL_HEIGHT_OBSERVATION_AVAILABLE', 'PASS_OBSERVATION_ONLY', HEIGHT_SHA,
       '1.385 m user-reported physical mean; uncertainty and independent full pose validation remain pending')
  node('CALIBRATION_MEASUREMENT_PENDING', 'PARTIAL', HEIGHT_SHA,
       'Height observation exists; remaining physical pose and all required uncertainty measurements are absent',
       ('CALIBRATION_UNCERTAINTY_PENDING',))
  node('INDEPENDENT_CALIBRATION_VALIDATION_PENDING', 'BLOCKED', HEIGHT_SHA,
       'Separate full physical pose/intrinsics/distortion validation; height observation is insufficient',
       ('CALIBRATION_MEASUREMENT_PENDING',))
  # Verify graph structure; no opaque or cycle dependencies can disappear.
  visited, active = set(), set()

  def visit(key):
    if key in active or key not in blockers:
      raise ValueError('INVALID_BLOCKER_DAG')
    if key in visited:
      return
    active.add(key)
    for dep in blockers[key]['dependencies']:
      visit(dep)
    active.remove(key)
    visited.add(key)

  for key in blockers:
    visit(key)
  return c.seal({'schema': 'QCAMERA_RECORDED_RUNTIME_READINESS_V1', 'baseline_sha': runtime['baseline_sha'],
                 'status': 'PIXEL_GEOMETRY_REGISTRATION_PARTIAL', 'validated': False,
                 'software_contract_status': 'PIXEL_GEOMETRY_REGISTRATION_DEFINED_STRUCTURAL_ONLY',
                 'runtime_sha256': RUNTIME_SHA, 'scaler_sha256': SCALER_SHA, 'previous_readiness_sha256': PREVIOUS_SHA,
                 'physical_height_context': {'receipt_sha256': HEIGHT_SHA, 'value_m': height['value_m'],
                                             'uncertainty_m': None, 'use': 'CONTEXT_ONLY_NOT_SCALER_INPUT'},
                 'blockers': blockers, 'dag_verified': True,
                 'actual_forward_mapping': None, 'actual_inverse_mapping': None, 'actual_qcamera_intrinsics': None,
                 'pixel_mapping_bound_native_px': None, 'numeric_meter_results': None,
                 'conditional_hypotheses': hypotheses(),
                 'conditional_envelope_known_points': conditional_envelope([[0, 0], [262.5, 164.5], [525, 329]]),
                 'stationary_target_path': {
                   'native_input_wh': [1344, 760], 'qcamera_input_allowed': False,
                   'future_qcamera_requirements': ['VALIDATED_REGISTRATION', 'SOURCE_DERIVED_KQ',
                                                  'APPLICABLE_INTRINSICS_DISTORTION', 'PHYSICAL_TARGET_EVIDENCE']},
                 'historical_metrics_modified': False, 'historical_coordinate_system': 'ORIGINAL_QCAMERA_526x330',
                 'new_holdout_access': False, 'private_images_decoded': False, 'detector_inference_this_increment': False,
                 'raw_publication': False, 'sealed_reference': 'NOT_GENERATED',
                 'vehicle_status': ['NOT_READY', 'REAL_VEHICLE_UNVERIFIED', 'VEHICLE_ACTIVATION_BLOCKED'], **q.FLAGS})


def validate_readiness(value):
  unseal(value)
  if value != readiness():
    raise ValueError('RUNTIME_AUDIT_CANNOT_PROMOTE_REGISTRATION_OR_REFERENCE')
  return value
