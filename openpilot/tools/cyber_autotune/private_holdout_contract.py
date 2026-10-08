"""Separate frozen-60 authorization and blind pixel first-decision evidence.

Hashes attest bytes/provenance, not human expertise or meter calibration.
No detector selection, model output, independent road truth or vehicle authority.
"""
from pathlib import Path
import math
import os
import re
import tempfile

import numpy as np

from openpilot.tools.cyber_autotune import private_pixel_execution as p
from openpilot.tools.cyber_autotune import camera_calibration_evidence as c
from openpilot.tools.cyber_autotune import lane_public_storage as storage
from openpilot.tools.cyber_autotune.lane_tail_report import seal, unseal
from openpilot.tools.cyber_autotune.native_protocol import canonical, digest

EXPECTED = 60  # Exact historical frozen holdout; never resample or shrink.
STATES = ('BOTH_EGO_BOUNDARIES_VISIBLE', 'LEFT_ONLY_VISIBLE', 'RIGHT_ONLY_VISIBLE',
          'EGO_BOUNDARIES_AMBIGUOUS', 'INTERSECTION_OR_MERGE', 'NO_CLEAR_LANE_MARKINGS', 'UNREVIEWABLE')
COORDINATES = {'units': 'ORIGINAL_IMAGE_PIXEL', 'origin': 'TOP_LEFT_PIXEL_CENTER',
               'x': 'RIGHT', 'y': 'DOWN', 'point_precision': 'FINITE_SUBPIXEL_FLOAT',
               'ordering': 'NEAR_TO_FAR_STRICTLY_DECREASING_Y', 'minimum_points': 3, 'maximum_points': 12}
FIREWALL = {k: v for k, v in p.FIREWALL.items() if k != 'ground_truth'}
PRIVACY = {'schema': 'PRIVATE_BLIND_HOLDOUT_PRIVACY_V1', 'raw_storage': 'LOCAL_PRIVATE_OUTSIDE_REPOSITORY',
           'publication': 'AGGREGATE_WHITELIST_AND_WHOLE_SET_RECEIPTS_ONLY',
           'raw_images_polylines_paths_routes_timestamps_gps_publication': False,
           'upload_allowed': False, 'pre_exposure': 'RAW_IMAGE_AND_HUMAN_DRAWING_ONLY'}
EVALUATION_POLICY = {
  'schema': 'PRIVATE_PIXEL_HOLDOUT_EVALUATION_POLICY_V1', 'units': 'ORIGINAL_IMAGE_PIXELS',
  'source_semantics': 'HUMAN_VISIBLE_EGO_BOUNDARIES_NOT_ALL_MARKINGS',
  'rows': 'INTEGER_Y_IN_COMMON_OBSERVED_SUPPORT_INCLUSIVE',
  'interpolation': 'PIECEWISE_LINEAR_WITHIN_OBSERVED_SPAN_NO_EXTRAPOLATION',
  'cost': 'MEAN_ABSOLUTE_LATERAL_PIXEL_DISTANCE_ON_COMMON_ROWS',
  'assignment': 'MAXIMUM_OVERLAP_ELIGIBLE_MATCH_COUNT_THEN_MINIMUM_TOTAL_COST_THEN_LANE_INDEX',
  'confidence_filter': 'NONE_FROZEN_DETECTOR_POSTPROCESSING_ONLY', 'acceptance_threshold': None,
  'center': 'ONLY_BOTH_HUMAN_AND_DISTINCT_MATCHED_DETECTOR_BOUNDARIES_COMMON_SUPPORT',
  'ambiguous_states': 'EXCLUDED_LOCALIZATION_DENOMINATOR_REPORTED_COUNTS',
  'unsupported_detector_lane': 'NO_OBSERVED_Y_OVERLAP_NOT_FALSE_POSITIVE_TRUTH',
  'metric_projection': 'FORBIDDEN', 'detector_tuning': 'FORBIDDEN', **FIREWALL,
}


def source_identity():
  names = ('private_holdout_contract.py', 'private_holdout_materializer.py', 'private_holdout_annotation.py', 'private_holdout_pixel_metrics.py')
  return {name: digest((Path(__file__).parent / name).read_bytes()) for name in names}


def holdouts(manifest):
  p.validate_manifest(manifest)
  rows = [r for r in manifest['selected'] if r['role'] == 'HOLDOUT']
  if len(rows) != EXPECTED or len({r['sample_id'] for r in rows}) != EXPECTED:
    raise ValueError('EXACT_FROZEN_SIXTY_HOLDOUT_REQUIRED')
  return rows


def authorize(manifest, head, timestamp, *, acknowledged):
  rows = holdouts(manifest)
  if acknowledged is not True or re.fullmatch('[0-9a-f]{40}', head or '') is None:
    raise ValueError('SEPARATE_EXPLICIT_HOLDOUT_AUTHORIZATION_REQUIRED')
  if c.utc(timestamp) < c.utc(manifest['frozen_at']):
    raise ValueError('AUTHORIZATION_AFTER_ORIGINAL_FREEZE_REQUIRED')
  return seal({
    'schema': 'PRIVATE_HUMAN_HOLDOUT_MATERIALIZATION_AUTHORIZATION_V1',
    'status': 'AUTHORIZED_RAW_HOLDOUT_ONLY_NO_INFERENCE', 'manifest_sha256': manifest['receipt_sha256'],
    'holdout_selection_sha256': digest(canonical(rows)), 'holdout_samples': rows,
    'branch_commit_sha': head, 'authorized_at': timestamp, 'explicit_user_authorization': True,
    'source_identity': source_identity(), 'original_executor_identity': p.identity(),
    'privacy_policy_sha256': digest(canonical(PRIVACY)),
    'coordinate_policy_sha256': digest(canonical(COORDINATES)),
    'evaluation_policy_sha256': digest(canonical(EVALUATION_POLICY)),
    'detector': manifest['detector'], 'detector_output_pre_exposure': False,
    'ai_suggestion_pre_exposure': False, 'holdout_detector_inference_allowed_at_materialization': False,
    **FIREWALL,
  })


def require_materialization(manifest, auth, sample_id):
  if type(auth) is not dict:
    raise ValueError('HOLDOUT_AUTH_REQUIRED_BEFORE_DECODE')
  unseal(auth)
  if canonical(auth) != canonical(authorize(manifest, auth['branch_commit_sha'], auth['authorized_at'], acknowledged=True)):
    raise ValueError('EXACT_HOLDOUT_AUTH_SOURCE_PRIVACY_BINDING_REQUIRED')
  rows = [r for r in holdouts(manifest) if r['sample_id'] == sample_id]
  if len(rows) != 1:
    raise ValueError('ONLY_ORIGINAL_FROZEN_HOLDOUT_ALLOWED')
  return rows[0]


def image_receipt(manifest, auth, sample_id, image_sha):
  sample = require_materialization(manifest, auth, sample_id)
  return _image_receipt(manifest, auth, sample, image_sha)


def _image_receipt(manifest, auth, sample, image_sha):
  c.sha(image_sha)
  sample_id = sample['sample_id']
  meta = next(r for r in manifest['metadata'] if r['segment_id'] == sample['segment_id'])
  return seal({
    'schema': 'PRIVATE_RAW_HOLDOUT_IMAGE_V1', 'manifest_sha256': manifest['receipt_sha256'],
    'authorization_sha256': auth['receipt_sha256'], 'sample_id': sample_id,
    'image_sha256': image_sha, 'width': meta['width'], 'height': meta['height'],
    'source_sha256': meta['source_sha256'], 'coordinate_policy': COORDINATES,
    'detector_inference': 'NOT_RUN', 'ai_review': 'NOT_RUN', **FIREWALL,
  })


def materialization_complete(manifest, auth, images):
  rows = holdouts(manifest)
  if type(images) is not list or len(images) != EXPECTED or [r['sample_id'] for r in images] != [r['sample_id'] for r in rows]:
    raise ValueError('ALL_SIXTY_EXACT_ORDERED_IMAGES_REQUIRED')
  require_materialization(manifest, auth, rows[0]['sample_id'])
  for sample, row in zip(rows, images, strict=True):
    unseal(row)
    if canonical(row) != canonical(_image_receipt(manifest, auth, sample, row['image_sha256'])):
      raise ValueError('MATERIALIZED_IMAGE_IDENTITY_MISMATCH')
  return seal({'schema': 'PRIVATE_HUMAN_HOLDOUT_MATERIALIZATION_COMPLETE_V1',
               'status': 'PRIVATE_HUMAN_HOLDOUT_READY_FOR_REVIEW', 'images': images,
               'manifest_sha256': manifest['receipt_sha256'], 'frozen_manifest': manifest, 'authorization': auth,
               'evaluation_policy': EVALUATION_POLICY, 'reviewed': 0, **FIREWALL})


def finite(value):
  if type(value) not in (int, float) or not math.isfinite(value):
    raise ValueError('FINITE_PIXEL_NUMBER_REQUIRED')
  return float(value)


def validate_points(points, width, height, *, draft=False):
  if type(points) is not list or (points and not draft and not 3 <= len(points) <= 12) or len(points) > 12:
    raise ValueError('THREE_TO_TWELVE_VISIBLE_CONTROL_POINTS_REQUIRED')
  for point in points:
    if type(point) is not list or len(point) != 2:
      raise ValueError('XY_PIXEL_PAIR_REQUIRED')
    x, y = map(finite, point)
    if not 0 <= x <= width - 1 or not 0 <= y <= height - 1:
      raise ValueError('POINT_OUTSIDE_ORIGINAL_IMAGE')
  if any(points[i][1] <= points[i + 1][1] for i in range(len(points) - 1)):
    raise ValueError('STRICT_NEAR_TO_FAR_Y_ORDER_REQUIRED')


def interpolate(points, ys):
  ascending = sorted(points, key=lambda point: point[1])
  if not ascending or any(y < ascending[0][1] or y > ascending[-1][1] for y in ys):
    raise ValueError('OBSERVED_SUPPORT_ONLY_NO_EXTRAPOLATION')
  return np.interp(ys, [y for _, y in ascending], [x for x, _ in ascending]).tolist()


def common_rows(left, right, *, integer=False):
  if not left or not right:
    return []
  lo, hi = max(min(y for _, y in left), min(y for _, y in right)), min(max(y for _, y in left), max(y for _, y in right))
  if lo > hi:
    return []
  if integer:
    return list(range(math.ceil(lo), math.floor(hi) + 1))
  return sorted({lo, hi, *[y for _, y in left + right if lo <= y <= hi]}, reverse=True)


def validate_body(image, body, *, draft=False):
  c.exact(body, ('state', 'left', 'right', 'acknowledged_blind', 'reviewer_id'))
  if body['state'] not in STATES or re.fullmatch('[A-Za-z0-9_-]{1,48}', body['reviewer_id'] or '') is None:
    raise ValueError('KNOWN_STATE_AND_OPAQUE_REVIEWER_ID_REQUIRED')
  if not draft and body['acknowledged_blind'] is not True:
    raise ValueError('EXPLICIT_BLIND_HUMAN_ACK_REQUIRED')
  if type(body['acknowledged_blind']) is not bool:
    raise ValueError('BOOLEAN_ACK_REQUIRED')
  for key in ('left', 'right'):
    validate_points(body[key], image['width'], image['height'], draft=draft)
  if draft:
    return
  expected = {'BOTH_EGO_BOUNDARIES_VISIBLE': (True, True), 'LEFT_ONLY_VISIBLE': (True, False),
              'RIGHT_ONLY_VISIBLE': (False, True)}.get(body['state'], (False, False))
  if (bool(body['left']), bool(body['right'])) != expected:
    raise ValueError('STATE_VISIBLE_BOUNDARIES_MUST_MATCH_NO_FORCED_AMBIGUOUS_GT')
  if all(expected):
    ys = common_rows(body['left'], body['right'])
    if not ys or any(l >= r for l, r in zip(interpolate(body['left'], ys), interpolate(body['right'], ys), strict=True)):
      raise ValueError('LEFT_RIGHT_CROSSING_OR_NO_SHARED_SUPPORT')


def annotation(image, body, timestamp):
  unseal(image)
  c.utc(timestamp)
  validate_body(image, body)
  return seal({'schema': 'PRIVATE_BLIND_PIXEL_FIRST_DECISION_V1',
               'sample_id': image['sample_id'], 'image_sha256': image['image_sha256'],
               'image_receipt_sha256': image['receipt_sha256'], 'width': image['width'], 'height': image['height'],
               'manifest_sha256': image['manifest_sha256'], 'coordinate_policy': COORDINATES,
               **body, 'saved_at': timestamp, 'annotation_tool_sha256': source_identity()['private_holdout_annotation.py'],
               'annotation_schema_sha256': digest(Path(__file__).read_bytes()),
               'detector_prediction_exposed_before_save': False, 'ai_suggestion_exposed_before_save': False,
               'model_output_exposed_before_save': False, 'provenance': 'PRIVATE_BLIND_FIRST_HUMAN_PIXEL_ANNOTATION',
               **FIREWALL})


def correction(first, body, timestamp, reason):
  unseal(first)
  if not isinstance(reason, str) or not 1 <= len(reason) <= 1000:
    raise ValueError('CORRECTION_REASON_REQUIRED')
  validate_body(first, body)
  c.utc(timestamp)
  return seal({'schema': 'PRIVATE_PIXEL_ANNOTATION_CORRECTION_V1',
               'first_decision_sha256': first['receipt_sha256'], 'sample_id': first['sample_id'],
               'image_sha256': first['image_sha256'], 'corrected': body, 'reason': reason, 'saved_at': timestamp,
               'provenance': 'POST_DECISION_CORRECTION_NOT_NEW_BLIND_FIRST_DECISION', **FIREWALL})


def pixel_center(row):
  unseal(row)
  if row['state'] != 'BOTH_EGO_BOUNDARIES_VISIBLE':
    return []
  ys = common_rows(row['left'], row['right'])
  return [[(l + r) / 2, y] for l, r, y in zip(interpolate(row['left'], ys), interpolate(row['right'], ys), ys, strict=True)]


def original_point(display_x, display_y, offset_x, offset_y, scale):
  scale = finite(scale)
  if scale <= 0:
    raise ValueError('POSITIVE_DISPLAY_SCALE_REQUIRED')
  return [(finite(display_x) - finite(offset_x)) / scale, (finite(display_y) - finite(offset_y)) / scale]


def freeze_reference(package, rows, timestamp):
  unseal(package)
  expected = materialization_complete(package['frozen_manifest'], package['authorization'], package['images'])
  if canonical(package) != canonical(expected):
    raise ValueError('EXACT_FROZEN_MATERIALIZATION_PACKAGE_REQUIRED')
  frozen_at = c.utc(timestamp)
  images = package['images']
  if len(rows) != EXPECTED or [r['sample_id'] for r in rows] != [i['sample_id'] for i in images]:
    raise ValueError('SIXTY_ORDERED_IMMUTABLE_FIRST_DECISIONS_REQUIRED')
  for image, row in zip(images, rows, strict=True):
    unseal(row)
    if c.utc(row['saved_at']) > frozen_at:
      raise ValueError('REFERENCE_FREEZE_CANNOT_PRECEDE_FIRST_DECISIONS')
    body = {k: row[k] for k in ('state', 'left', 'right', 'acknowledged_blind', 'reviewer_id')}
    if canonical(row) != canonical(annotation(image, body, row['saved_at'])):
      raise ValueError('FIRST_DECISION_BINDING_OR_PROVENANCE_MISMATCH')
  return seal({'schema': 'PRIVATE_BLIND_HUMAN_PIXEL_REFERENCE_V1', 'annotations': rows,
               'materialization_sha256': package['receipt_sha256'], 'frozen_at': timestamp,
               'evaluation_policy': EVALUATION_POLICY, 'corrections_used': False,
               'status': 'PRIVATE_BLIND_HUMAN_HOLDOUT_COMPLETE', **FIREWALL})


def require_detector_gate(package, reference):
  if type(reference) is not dict:
    raise ValueError('ALL_SIXTY_BLIND_DECISIONS_AND_SET_FREEZE_REQUIRED')
  unseal(reference)
  expected = freeze_reference(package, reference['annotations'], reference['frozen_at'])
  if canonical(reference) != canonical(expected):
    raise ValueError('EXACT_FROZEN_HUMAN_REFERENCE_REQUIRED')


def private_path(path):
  path = Path(path).absolute()
  if '..' in path.parts or any(v.is_symlink() for v in (path, *path.parents)):
    raise ValueError('PRIVATE_STORE_SYMLINK_OR_TRAVERSAL_FORBIDDEN')
  if path.resolve().is_relative_to(p.ROOT) or str(path).startswith(('/tmp/', '/run/', '/dev/shm/')):
    raise ValueError('PERSISTENT_PRIVATE_STORE_OUTSIDE_REPO_REQUIRED')
  return path


def read(path):
  private_path(path)
  return storage.read_json(path)


def write_immutable(path, value):
  path = private_path(path)
  storage.durable_mkdir(path.parent)
  if path.exists():
    if canonical(read(path)) != canonical(value):
      raise ValueError('IMMUTABLE_HOLDOUT_ARTIFACT_CONFLICT')
    return
  data = canonical(value) + b'\n'
  directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
  fd, temporary = tempfile.mkstemp(prefix='.' + path.name + '.', suffix='.tmp', dir=path.parent)
  try:
    with os.fdopen(fd, 'wb') as stream:
      stream.write(data)
      stream.flush()
      os.fsync(stream.fileno())
    os.link(Path(temporary).name, path.name, src_dir_fd=directory, dst_dir_fd=directory, follow_symlinks=False)
    os.fsync(directory)
  finally:
    os.close(directory)
    os.unlink(temporary)
