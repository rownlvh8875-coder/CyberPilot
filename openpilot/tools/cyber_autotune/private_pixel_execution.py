"""Separately authorized, bounded private diagnostics; no qualification path.

Historical private admission remains closed. Only this versioned exception may
open metadata-selected DEVELOPMENT camera frames. HOLDOUT remains unopened.
Hash receipts bind declarations and execution bytes, not independent lane truth.
"""
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath

import numpy as np

from openpilot.tools.cyber_autotune import camera_calibration_evidence as c
from openpilot.tools.cyber_autotune import private_lane_diagnostic_preparation as preparation
from openpilot.tools.cyber_autotune import lane_public_storage as storage
from openpilot.tools.cyber_autotune.lane_tail_report import seal, unseal
from openpilot.tools.cyber_autotune.native_protocol import canonical, digest

ROOT = Path(__file__).resolve().parents[3]
FIREWALL = {
  'qualification_allowed': False, 'reference_promotable': False, 'sealed_reference_allowed': False,
  'vehicle_activation_allowed': False, 'modelv2_usage': False, 'candidate_usage': False,
  'publication_raw_data': False, 'ground_truth': 'ABSENT',
}
PRIVACY = {
  'schema': 'PRIVATE_DIAGNOSTIC_PRIVACY_V1', 'raw_storage': 'LOCAL_PRIVATE_OUTSIDE_REPOSITORY',
  'publication': 'AGGREGATE_WHITELIST_AND_WHOLE_MANIFEST_HASH_ONLY',
  'upload': False, 'paths_routes_timestamps_gps_exif_publication': False,
  'holdout': 'FROZEN_DISJOINT_NOT_DECODED_NOT_INFERRED_THIS_EXPERIMENT',
}


def identity():
  names = ('private_pixel_execution.py', 'private_pixel_executor.py', 'private_lane_diagnostic_preparation.py',
           'lane_public_storage.py', 'lane_tail_report.py', 'native_protocol.py', 'private_camera_metadata.py')
  return digest(canonical({name: digest((Path(__file__).parent / name).read_bytes()) for name in names}))


def sampling_policy(timestamp):
  c.utc(timestamp)
  return seal({
    'schema': 'ROUTE_BALANCED_DETERMINISTIC_SAMPLE_V2', 'frozen_at': timestamp,
    'max_segments': 60, 'samples_per_segment': 5, 'max_frames': 300,
    'selection': 'OPAQUE_ROUTE_SORT_ROUND_ROBIN_OPAQUE_SEGMENT_SORT',
    'ordinal': 'FLOOR((2*SLOT+1)*FRAME_COUNT/10)',
    'holdout_slot': 4, 'roles': ['DEVELOPMENT', 'HOLDOUT'],
    'selection_uses_images_or_detector_outputs': False,
    'small_segment': 'EXPLICIT_UNUSABLE_FRAME_COUNT_BELOW_10',
    'eligibility': 'COMPLETE_ENCODED_TS_STABLE_SPS_AUD_PTS_REQUIRED_BEFORE_CONTENT',
    'unusable_sources': 'EXPLICIT_HASH_SIZE_REASON_IN_INVENTORY_NOT_SILENT_SKIP',
    'temporal': 'NOT_EVALUATED_UNLESS_CONSECUTIVE_SELECTED_FRAMES',
    'privacy_sha256': digest(canonical(PRIVACY)), **FIREWALL,
  })


def freeze_manifest(metadata, policy, root_identity, timestamp, *, content_opened=False, unavailable_sources=None):
  unseal(policy)
  if policy != sampling_policy(policy['frozen_at']) or content_opened is not False:
    raise ValueError('POLICY_MUST_FREEZE_BEFORE_CONTENT')
  c.sha(root_identity)
  if c.utc(timestamp) < c.utc(policy['frozen_at']):
    raise ValueError('MANIFEST_MUST_FOLLOW_POLICY')
  if type(metadata) is not list or not metadata:
    raise ValueError('NONEMPTY_CAMERA_METADATA_REQUIRED')
  fields = ('route_id', 'segment_id', 'source_sha256', 'source_bytes', 'frame_count', 'width', 'height',
            'fps', 'codec', 'camera_role', 'source_key')
  unavailable_sources = [] if unavailable_sources is None else unavailable_sources
  if type(unavailable_sources) is not list:
    raise ValueError('UNUSABLE_SOURCE_DISPOSITIONS_REQUIRED')
  for row in unavailable_sources:
    c.exact(row, ('source_sha256', 'source_bytes', 'status', 'reason'))
    c.sha(row['source_sha256'])
    if (type(row['source_bytes']) is not int or row['source_bytes'] < 0 or row['status'] != 'PRIVATE_CAMERA_SOURCE_UNUSABLE'
        or row['reason'] not in ('188_BYTE_TS_REQUIRED', 'STABLE_SPS_AUD_AND_ONE_PTS_PER_FRAME_REQUIRED', 'UNSUPPORTED_CAMERA_TIMEBASE',
                                 'VIDEO_TRANSPORT_CONTINUITY_FAILURE', 'TRUNCATED_SPS', 'SEGMENT_TOO_SHORT')):
      raise ValueError('EXPLICIT_KNOWN_UNUSABLE_METADATA_REQUIRED')
  routes = defaultdict(list)
  seen = set()
  for row in metadata:
    c.exact(row, fields)
    for key in ('route_id', 'segment_id', 'source_sha256'):
      c.sha(row[key])
    path = PurePosixPath(row['source_key'])
    if (path.is_absolute() or '..' in path.parts or '\\' in row['source_key']
        or str(path) != row['source_key'] or path.name != 'qcamera.ts' or row['camera_role'] != 'NARROW_ROAD'):
      raise ValueError('CAMERA_ONLY_NO_LOG_MODEL_OR_CANDIDATE_INPUT')
    if row['segment_id'] in seen:
      raise ValueError('DUPLICATE_SEGMENT')
    seen.add(row['segment_id'])
    for key in ('source_bytes', 'frame_count', 'width', 'height'):
      if type(row[key]) is not int or row[key] <= 0:
        raise ValueError('POSITIVE_CAMERA_METADATA_REQUIRED')
    if row['frame_count'] < 10 or row['width'] * row['height'] > 6_000_000:
      raise ValueError('UNSUPPORTED_CAMERA_DOMAIN')
    c.number(row['fps'], positive=True)
    if row['codec'] != 'h264':
      raise ValueError('AUDITED_QCAM_H264_REQUIRED')
    routes[row['route_id']].append(row)
  queues = [sorted(rows, key=lambda r: r['segment_id']) for _, rows in sorted(routes.items())]
  chosen = []
  for round_index in range(max(map(len, queues))):
    for queue in queues:
      if round_index < len(queue) and len(chosen) < policy['max_segments']:
        chosen.append(queue[round_index])
  selected = []
  for row in chosen:
    for slot in range(5):
      ordinal = (2 * slot + 1) * row['frame_count'] // 10
      sample = {
        'segment_id': row['segment_id'], 'frame_ordinal': ordinal,
        'role': 'HOLDOUT' if slot == policy['holdout_slot'] else 'DEVELOPMENT',
      }
      selected.append({**sample, 'sample_id': digest(canonical(sample))})
  return seal({
    'schema': 'PRIVATE_CAMERA_FRAME_MANIFEST_V1', 'metadata': sorted(metadata, key=lambda r: r['segment_id']),
    'selected': selected, 'unavailable_sources': unavailable_sources, 'policy': policy, 'root_identity': root_identity, 'frozen_at': timestamp,
    'detector': preparation.frozen_detector(), 'content_opened_before_freeze': False,
    'execution_source_sha256': identity(), 'storage': 'LOCAL_PRIVATE_ONLY', **FIREWALL,
  })


def validate_manifest(manifest):
  unseal(manifest)
  expected = freeze_manifest(manifest['metadata'], manifest['policy'], manifest['root_identity'], manifest['frozen_at'],
                             unavailable_sources=manifest['unavailable_sources'])
  if manifest != expected:
    raise ValueError('EXACT_MANIFEST_EXECUTOR_DETECTOR_BINDING_REQUIRED')


def authorize(manifest, branch_commit_sha, timestamp, *, acknowledged):
  validate_manifest(manifest)
  if type(branch_commit_sha) is not str or len(branch_commit_sha) != 40 or any(v not in '0123456789abcdef' for v in branch_commit_sha):
    raise ValueError('EXACT_GIT_BRANCH_COMMIT_REQUIRED')
  if acknowledged is not True or c.utc(timestamp) < c.utc(manifest['frozen_at']):
    raise ValueError('EXPLICIT_CURRENT_INCREMENT_AUTHORIZATION_AFTER_FREEZE_REQUIRED')
  return seal({
    'schema': 'PRIVATE_PIXEL_DIAGNOSTIC_AUTHORIZATION_V1',
    'status': 'EXECUTION_AUTHORIZED_DIAGNOSTIC_ONLY',
    'branch_commit_sha': branch_commit_sha, 'manifest_sha256': manifest['receipt_sha256'],
    'sampling_policy_sha256': manifest['policy']['receipt_sha256'],
    'privacy_policy_sha256': digest(canonical(PRIVACY)), 'executor_sha256': identity(),
    'source_root_identity': manifest['root_identity'], 'detector': preparation.frozen_detector(),
    'authorized_at': timestamp, 'explicit_user_authorization': True,
    'exception': 'NONQUALIFYING_ONLY_OFFICIAL_BENCHMARK_AND_HUMAN_VALIDATION_STILL_BLOCKED', **FIREWALL,
  })


def require_execution(manifest, authorization):
  validate_manifest(manifest)
  if type(authorization) is not dict:
    raise ValueError('AUTHORIZATION_REQUIRED_BEFORE_FRAME_OPEN')
  unseal(authorization)
  if authorization != authorize(manifest, authorization['branch_commit_sha'], authorization['authorized_at'], acknowledged=True):
    raise ValueError('EXACT_AUTHORIZATION_REQUIRED')


def require_frame(manifest, authorization, sample_id):
  require_execution(manifest, authorization)
  matches = [r for r in manifest['selected'] if r['sample_id'] == sample_id]
  if len(matches) != 1 or matches[0]['role'] != 'DEVELOPMENT':
    raise ValueError('ONLY_FROZEN_DEVELOPMENT_FRAME_OPEN_ALLOWED')
  return matches[0]


def private_directories(source_root, cache):
  paths = [Path(p).absolute() for p in (source_root, cache)]
  for path in paths:
    if any(p.is_symlink() for p in (path, *path.parents)) or '..' in path.parts:
      raise ValueError('PRIVATE_NO_SYMLINK_NO_TRAVERSAL_REQUIRED')
    if path.resolve().is_relative_to(ROOT.resolve()) or str(path).startswith(('/tmp/', '/run/', '/dev/shm/')):
      raise ValueError('PERSISTENT_PRIVATE_STORAGE_OUTSIDE_REPO_REQUIRED')
  if paths[0] == paths[1] or paths[0].is_relative_to(paths[1]) or paths[1].is_relative_to(paths[0]):
    raise ValueError('SOURCE_CACHE_MUST_BE_SEPARATE')
  return paths


def validate_prediction(record, geometry):
  c.exact(record, ('image_geometry', 'lane_count', 'points', 'lanes'))
  if record['image_geometry'] != geometry or type(record['lane_count']) is not int or not 0 <= record['lane_count'] <= 4:
    raise ValueError('FROZEN_GEOMETRY_AND_LANE_COUNT_REQUIRED')
  if type(record['lanes']) is not list or len(record['lanes']) != record['lane_count']:
    raise ValueError('LANE_COUNT_MISMATCH')
  h, w = geometry
  for points in [record['points'], *[lane['points'] for lane in record['lanes']]]:
    if type(points) is not list:
      raise ValueError('POLYLINE_POINTS_REQUIRED')
    for point in points:
      if type(point) is not list or len(point) != 2:
        raise ValueError('XY_POINTS_REQUIRED')
      x, y = [c.number(v) for v in point]
      if not 0 <= x <= w - 1 or not 0 <= y < h:
        raise ValueError('FINITE_ON_CANVAS_POINTS_REQUIRED')
  for lane in record['lanes']:
    c.exact(lane, ('confidence', 'points'))
    score = lane['confidence']
    if score is not None and not 0 <= c.number(score) <= 1:
      raise ValueError('CONFIDENCE_PROBABILITY_REQUIRED')
  union = sorted({tuple(point) for lane in record['lanes'] for point in lane['points']}, key=lambda v: (v[1], v[0]))
  if canonical(record['points']) != canonical([list(point) for point in union]):
    raise ValueError('POOLED_POINTS_MUST_MATCH_PER_LANE')


def frame_receipt(manifest, auth, sample_id, image_sha256, prediction):
  sample = require_frame(manifest, auth, sample_id)
  c.sha(image_sha256)
  metadata = next(r for r in manifest['metadata'] if r['segment_id'] == sample['segment_id'])
  validate_prediction(prediction, [metadata['height'], metadata['width']])
  dev = [r for r in manifest['selected'] if r['role'] == 'DEVELOPMENT']
  return seal({
    'schema': 'PRIVATE_PIXEL_FRAME_DIAGNOSTIC_V1', 'run_sha256': auth['receipt_sha256'],
    'ordinal': dev.index(sample), 'sample_id': sample_id, 'image_sha256': image_sha256,
    'source_sha256': metadata['source_sha256'], 'detector_sha256': auth['detector']['receipt_sha256'],
    'prediction': prediction, 'prediction_sha256': digest(canonical(prediction)),
    'frame_status': 'COMPLETED' if prediction['points'] else 'REFERENCE_UNAVAILABLE', **FIREWALL,
  })


def validate_frame(row, manifest, auth):
  unseal(row)
  if row != frame_receipt(manifest, auth, row['sample_id'], row['image_sha256'], row['prediction']):
    raise ValueError('EXACT_FRAME_RECEIPT_REQUIRED')


def distribution(values):
  return {'count': len(values), **{
    key: float(np.quantile(values, q, method='linear')) if values else None
    for key, q in (('median', .5), ('p95', .95), ('min', 0), ('max', 1))
  }}


def prediction_behavior(records):
  counts, confidence, xs, ys, extents, separations = [], [], [], [], [], []
  for record in records:
    h, w = record['image_geometry']
    counts.append(record['lane_count'])
    for lane in record['lanes']:
      if lane['confidence'] is not None:
        confidence.append(lane['confidence'])
      if lane['points']:
        extents.append((max(p[1] for p in lane['points']) - min(p[1] for p in lane['points'])) / h)
    for x, y in record['points']:
      xs.append(x / w)
      ys.append(y / h)
    at_row = defaultdict(list)
    for lane in record['lanes']:
      for x, y in lane['points']:
        at_row[y].append(x / w)
    for values in at_row.values():
      values.sort()
      separations.extend(b - a for a, b in zip(values, values[1:], strict=False))
  return {
    'frames': len(records), 'lane_count_distribution': dict(sorted(Counter(counts).items())),
    'no_output_count': sum(not r['points'] for r in records),
    'per_lane_confidence': distribution(confidence),
    'per_frame_mean_confidence': distribution([float(np.mean([l['confidence'] for l in r['lanes'] if l['confidence'] is not None]))
                                              for r in records if any(l['confidence'] is not None for l in r['lanes'])]),
    'normalized_x': distribution(xs), 'normalized_y': distribution(ys),
    'normalized_polyline_vertical_extent': distribution(extents),
    'sorted_adjacent_marking_separation_image_width_fraction': distribution(separations),
    'separation_semantics': 'ALL_DETECTED_MARKINGS_NOT_EGO_LANE_WIDTH',
  }


def progress_summary(manifest, auth, rows):
  require_execution(manifest, auth)
  seen = set()
  for row in rows:
    validate_frame(row, manifest, auth)
    if row['sample_id'] in seen:
      raise ValueError('DUPLICATE_RESULT')
    seen.add(row['sample_id'])
  dev = sum(r['role'] == 'DEVELOPMENT' for r in manifest['selected'])
  return seal({
    'schema': 'PRIVATE_PIXEL_DIAGNOSTIC_PUBLIC_AGGREGATE_V1',
    'status': 'PRIVATE_PIXEL_DIAGNOSTIC_COMPLETE' if len(rows) == dev else 'PRIVATE_PIXEL_DIAGNOSTIC_PARTIAL',
    'manifest_sha256': manifest['receipt_sha256'], 'authorization_sha256': auth['receipt_sha256'],
    'sampling_policy_sha256': manifest['policy']['receipt_sha256'], 'privacy_policy_sha256': digest(canonical(PRIVACY)),
    'executor_sha256': identity(), 'detector_sha256': auth['detector']['receipt_sha256'],
    'discovered_routes': len({r['route_id'] for r in manifest['metadata']}),
    'discovered_camera_segments': len(manifest['metadata']) + len(manifest['unavailable_sources']),
    'eligible_camera_segments': len(manifest['metadata']), 'inventory_unusable_sources': len(manifest['unavailable_sources']),
    'selected_samples': len(manifest['selected']),
    'development_samples': dev, 'holdout_samples': len(manifest['selected']) - dev,
    'successfully_decoded_and_inferred': len(rows), 'unprocessed': dev - len(rows),
    'no_output_rate': sum(not r['prediction']['points'] for r in rows) / len(rows) if rows else None,
    'behavior': prediction_behavior([row['prediction'] for row in rows]),
    'temporal': 'NOT_EVALUATED_NO_CONSECUTIVE_SAMPLES',
    'private_human_status': 'PRIVATE_HUMAN_HOLDOUT_PENDING',
    'private_domain_validation': 'NOT_RUN', 'sealed_reference': 'NOT_GENERATED',
    'blocker': 'INDEPENDENT_REFERENCE_UNAVAILABLE',
    'vehicle_status': ['NOT_READY', 'REAL_VEHICLE_UNVERIFIED', 'VEHICLE_ACTIVATION_BLOCKED'], **FIREWALL,
  })


def immutable_json(path, value):
  path = Path(path)
  if path.exists():
    if storage.read_json(path) != value:
      raise ValueError('IMMUTABLE_PRIVATE_ARTIFACT_MISMATCH')
  else:
    storage.atomic_json(path, value)
