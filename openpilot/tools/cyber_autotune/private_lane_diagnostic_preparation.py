"""Metadata-only private diagnostic planning. No acquisition/inference/authorization API."""

from collections import Counter
from pathlib import Path, PurePosixPath, PureWindowsPath
from openpilot.tools.cyber_autotune import camera_calibration_evidence as c
from openpilot.tools.cyber_autotune import lane_public_storage as s
from openpilot.tools.cyber_autotune.lane_tail_report import unseal
from openpilot.tools.cyber_autotune.camera_calibration_evidence import seal
from openpilot.tools.cyber_autotune.native_protocol import canonical, digest

ROOT = Path(__file__).resolve().parents[3]
ENV_FILE = 'docs/cyberpilot/changes/comma10k-completed-full-environment.json'
ENV_FILE_SHA = '7d39efce7a0cb3fb5e6cd4703b93252bc469d9e9bdb815a4b89a08bc95dd31ae'
IDENTITY_KEYS = ('source_sha256', 'weight_sha256', 'config_sha256', 'environment_sha256', 'preprocessing_sha256', 'postprocessing_sha256')
POLICY = {
  'schema': 'PRIVATE_METADATA_PREPARATION_POLICY_V1',
  'selection': 'ORDINAL_MODULAR_STRIDE_AND_DISJOINT_HOLDOUT_NO_CONTENT',
  'private_inputs': 'DO_NOT_OPEN_THIS_INCREMENT',
  'execution': 'NOT_RUN',
  'qualification': False,
  'privacy': 'LOCAL_PRIVATE_ROWS; PUBLIC_AGGREGATES_AND_WHOLE_MANIFEST_DIGEST_ONLY',
  'future_executor': 'REQUIRES_SEPARATE_EXPLICIT_INCREMENT_AND_EXISTING_GATE_EXCEPTION; NO_IMPLICIT_AUTHORIZATION',
}


def identity():
  return digest(canonical({'source': digest(Path(__file__).read_bytes()), 'policy': POLICY, 'environment_file': ENV_FILE_SHA}))


def frozen_detector():
  path = ROOT / ENV_FILE
  if digest(path.read_bytes()) != ENV_FILE_SHA:
    raise ValueError('EXACT_COMPLETED_PUBLIC_DETECTOR_ENVIRONMENT_REQUIRED')
  env = s.read_json(path)
  value = {key: env['source_bundle_sha256'] if key == 'source_sha256' else env[key] for key in IDENTITY_KEYS}
  for item in value.values():
    c.sha(item)
  return seal(
    {
      'schema': 'PRIVATE_DIAGNOSTIC_DETECTOR_FREEZE_V1',
      'detector': 'CLRerNet',
      'repository_commit': env['repository_commit'],
      'public_environment_file_sha256': ENV_FILE_SHA,
      **value,
      'reselection_allowed': False,
      'fine_tuning_allowed': False,
      'threshold_optimization_allowed': False,
      'ensemble_allowed': False,
      'postprocessing_mutation_allowed': False,
    }
  )


def freeze_policy(*, interval, offset, holdout_modulo, holdout_residue, timestamp):
  if (
    any(type(v) is not int for v in (interval, offset, holdout_modulo, holdout_residue))
    or interval <= 0
    or not 0 <= offset < interval
    or holdout_modulo < 2
    or not 0 <= holdout_residue < holdout_modulo
  ):
    raise ValueError('EXPLICIT_BOUNDED_MODULAR_SAMPLING_REQUIRED')
  c.utc(timestamp)
  return seal(
    {
      'schema': 'PRIVATE_METADATA_SAMPLE_POLICY_V1',
      'interval': interval,
      'offset': offset,
      'holdout_modulo': holdout_modulo,
      'holdout_residue': holdout_residue,
      'frozen_at': timestamp,
      'policy': POLICY,
      'tool_sha256': identity(),
      'metadata_role': 'PREEXISTING_NONIMAGE_INDEX',
      'private_input_allowed': False,
      'execution': 'NOT_RUN',
    }
  )


def validate_policy(value):
  unseal(value)
  expected = freeze_policy(
    interval=value['interval'],
    offset=value['offset'],
    holdout_modulo=value['holdout_modulo'],
    holdout_residue=value['holdout_residue'],
    timestamp=value['frozen_at'],
  )
  if value != expected:
    raise ValueError('EXACT_FROZEN_PRIVATE_SAMPLING_POLICY_REQUIRED')


def freeze_manifest(metadata, policy, detector, attestation):
  validate_policy(policy)
  if detector != frozen_detector():
    raise ValueError('DETECTOR_MUST_EQUAL_PUBLIC_FREEZE')
  c.exact(
    attestation,
    ('private_frames_opened', 'detector_outputs_opened', 'image_sampling_used', 'confidence_sampling_used', 'metadata_role', 'scope', 'inventory_frozen_at'),
  )
  for key in ('private_frames_opened', 'detector_outputs_opened', 'image_sampling_used', 'confidence_sampling_used'):
    if attestation[key] is not False:
      raise ValueError('OPENED_OR_CONTENT_SELECTED_INPUT_FORBIDDEN')
  if attestation['metadata_role'] != 'PREEXISTING_NONIMAGE_INDEX' or attestation['scope'] not in ('TEST_ONLY', 'PRIVATE_METADATA_ONLY'):
    raise ValueError('METADATA_ONLY_PROVENANCE_REQUIRED')
  if c.utc(attestation['inventory_frozen_at']) < c.utc(policy['frozen_at']):
    raise ValueError('POLICY_MUST_PRECEDE_SELECTION')
  if type(metadata) is not list or not metadata:
    raise ValueError('NONEMPTY_PREEXISTING_METADATA_REQUIRED')
  ordered = []
  seen = set()
  for row in metadata:
    c.exact(row, ('route_sha256', 'segment_sha256', 'frame_ordinal', 'timestamp_ns', 'metadata_source_sha256'))
    for key in ('route_sha256', 'segment_sha256', 'metadata_source_sha256'):
      c.sha(row[key])
    if any(type(row[k]) is not int or row[k] < 0 for k in ('frame_ordinal', 'timestamp_ns')):
      raise ValueError('NONNEGATIVE_ORDINAL_TIME_METADATA_REQUIRED')
    key = (row['route_sha256'], row['segment_sha256'], row['frame_ordinal'])
    if key in seen:
      raise ValueError('DUPLICATE_PRIVATE_FRAME_METADATA')
    seen.add(key)
    ordered.append(row)
  ordered = sorted(ordered, key=lambda row: (row['route_sha256'], row['segment_sha256'], row['frame_ordinal']))
  for left, right in zip(ordered, ordered[1:], strict=False):
    if left['route_sha256'] == right['route_sha256'] and left['segment_sha256'] == right['segment_sha256'] and left['timestamp_ns'] >= right['timestamp_ns']:
      raise ValueError('MONOTONIC_SEGMENT_TIMESTAMPS_REQUIRED')
  selected = []
  for row in ordered:
    if row['frame_ordinal'] % policy['interval'] == policy['offset']:
      group = row['frame_ordinal'] // policy['interval'] % policy['holdout_modulo']
      selected.append({**row, 'role': 'HOLDOUT' if group == policy['holdout_residue'] else 'DIAGNOSTIC'})
  if {row['role'] for row in selected} != {'HOLDOUT', 'DIAGNOSTIC'}:
    raise ValueError('TWO_DISJOINT_NONEMPTY_PARTITIONS_REQUIRED')
  return seal(
    {
      'schema': 'PRIVATE_PIXEL_DIAGNOSTIC_METADATA_MANIFEST_V1',
      'status': 'TEST_ONLY_MANIFEST_READY' if attestation['scope'] == 'TEST_ONLY' else 'MANIFEST_READY_NOT_AUTHORIZED',
      'metadata': ordered,
      'selected': selected,
      'metadata_sha256': digest(canonical(ordered)),
      'policy': policy,
      'detector': detector,
      'attestation': attestation,
      'tool_sha256': identity(),
      'execution': 'NOT_RUN',
      'private_input_allowed': False,
      'sealed_reference_allowed': False,
      'qualification_allowed': False,
      'reference_promotable': False,
      'storage': 'LOCAL_PRIVATE_ONLY_NOT_FOR_REPOSITORY_PUBLICATION',
    }
  )


def validate_manifest(value):
  core = unseal(value)
  if value != freeze_manifest(core['metadata'], core['policy'], core['detector'], core['attestation']):
    raise ValueError('IMMUTABLE_PRIVATE_METADATA_MANIFEST_REQUIRED')


def directory_contract(private_root, public_root, cache_root):
  """Lexical contract only: no exists/resolve/crawl or real root materialization."""
  paths = []
  for raw in (private_root, public_root, cache_root):
    if type(raw) is not str or not raw:
      raise ValueError('EXPLICIT_LOCAL_DIRECTORIES_REQUIRED')
    if raw.startswith(('\\\\', '//')):
      raise ValueError('NETWORK_AND_DEVICE_ROOTS_FORBIDDEN')
    kind = PureWindowsPath if ':' in raw or raw.startswith('\\') else PurePosixPath
    path = kind(raw)
    if not path.is_absolute() or '..' in path.parts:
      raise ValueError('ABSOLUTE_NO_TRAVERSAL_LOCAL_DIRECTORIES_REQUIRED')
    paths.append(path)
  private, public, cache = paths
  if (
    type(private) is not type(public)
    or type(private) is not type(cache)
    or private.is_relative_to(public)
    or public.is_relative_to(private)
    or not cache.is_relative_to(private)
    or cache == private
  ):
    raise ValueError('DISJOINT_PUBLIC_PRIVATE_ROOTS_AND_PRIVATE_CACHE_REQUIRED')
  return seal(
    {
      'schema': 'PRIVATE_LOCAL_DIRECTORY_CONTRACT_V1',
      'private_root': str(private),
      'public_root': str(public),
      'cache_root': str(cache),
      'future_resolved_no_follow_check_required': True,
      'actual_filesystem_separation_verified': False,
      'publish_this_receipt': False,
      'private_input_allowed': False,
    }
  )


def publication_summary(manifest):
  validate_manifest(manifest)
  return seal(
    {
      'schema': 'PRIVATE_METADATA_PUBLIC_SUMMARY_V1',
      'manifest_sha256': manifest['receipt_sha256'],
      'sample_counts': dict(sorted(Counter(row['role'] for row in manifest['selected']).items())),
      'policy_sha256': manifest['policy']['receipt_sha256'],
      'detector_sha256': manifest['detector']['receipt_sha256'],
      'scope': 'TEST_ONLY' if manifest['attestation']['scope'] == 'TEST_ONLY' else 'PRIVATE_PIXEL_DIAGNOSTIC_ONLY',
      'execution': 'NOT_RUN',
      'private_input_allowed': False,
      'qualification_allowed': False,
      'reference_promotable': False,
    }
  )


def human_holdout(manifest):
  validate_manifest(manifest)
  return seal(
    {
      'schema': 'PRIVATE_HUMAN_HOLDOUT_PROTOCOL_V1',
      'status': 'TEST_ONLY_HOLDOUT_PROTOCOL' if manifest['attestation']['scope'] == 'TEST_ONLY' else 'PRIVATE_HUMAN_HOLDOUT_PENDING',
      'manifest_sha256': manifest['receipt_sha256'],
      'heldout_frame_rows': [row for row in manifest['selected'] if row['role'] == 'HOLDOUT'],
      'annotations': None,
      'annotation_fields': ['ego_left_boundary', 'ego_right_boundary', 'ambiguous_or_unavailable', 'visibility_quality'],
      'workflow': 'UNINFORMED_HUMAN_FIRST_ORIGINAL_IMAGE_ONLY_NO_DETECTOR_CONFIDENCE_OR_RESULTS_BEFORE_LABEL',
      'known_failure_guide': 'EXISTING_PUBLIC_DIAGNOSTIC_TAXONOMY_GUIDANCE_ONLY_NOT_SELECTION_OR_FILTER',
      'human_validation_complete': False,
      'training_or_selection_allowed': False,
      'private_input_allowed': False,
      'publish_this_receipt': False,
      'reference_promotable': False,
    }
  )


def output_contract():
  return seal(
    {
      'schema': 'PRIVATE_PIXEL_DIAGNOSTIC_OUTPUT_CONTRACT_V1',
      'unit': 'PIXEL_DOMAIN_ONLY',
      'allowed': ['detected_lane_count', 'confidence_distribution', 'temporal_availability', 'prediction_geometry_stability', 'unavailable_rate'],
      'unavailable_handling': 'ACCOUNT_ALL_FROZEN_FRAMES_NO_CONFIDENCE_POSTHOC_EXCLUSION',
      'localization_error_against_truth_allowed': False,
      'qualification_allowed': False,
      'sealed_reference_allowed': False,
      'no_gt_semantics': 'GEOMETRY_STABILITY_IS_NOT_LOCALIZATION_ACCURACY_OR_LANE_QUALITY',
      'reference_promotable': False,
    }
  )


def pending():
  return seal(
    {
      'schema': 'PRIVATE_PIXEL_PREPARATION_READINESS_V1',
      'status': 'PROPOSED_NOT_RUN',
      'manifest_sha256': None,
      'sampling_policy_sha256': None,
      'private_input_allowed': False,
      'execution': 'NOT_RUN',
      'human_holdout_status': 'PRIVATE_HUMAN_HOLDOUT_PENDING',
      'detector': frozen_detector(),
      'output_contract': output_contract(),
      'privacy': [
        'NO_RAW_FRAME_LOG_UPLOAD_OR_REPOSITORY_COMMIT',
        'NO_EXIF_GPS_OR_RAW_METADATA_PUBLICATION',
        'NO_INDIVIDUAL_ROUTE_FRAME_HASHES_OR_LOCAL_PATHS_IN_PUBLIC_OUTPUT',
        'SEPARATE_LOCAL_PRIVATE_CACHE_PUBLIC_REPORTS',
      ],
      'qualification_allowed': False,
      'sealed_reference_allowed': False,
      'reference_promotable': False,
      'tool_sha256': identity(),
    }
  )


def require_execution(manifest):
  validate_manifest(manifest)
  raise ValueError('PRIVATE_INPUT_OPEN_PROHIBITED_THIS_INCREMENT')
