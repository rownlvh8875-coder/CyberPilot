"""Public marking review only. Automatic strata are hypotheses, never human labels."""

from collections import Counter
from datetime import datetime
import math
from pathlib import Path
from pathlib import PurePosixPath

from openpilot.tools.cyber_autotune.contracts import is_sha256
from openpilot.tools.cyber_autotune.lane_tail_report import seal, unseal
from openpilot.tools.cyber_autotune.native_protocol import canonical, digest
from openpilot.tools.cyber_autotune import lane_public_storage as storage

POLICY_SHA = 'ef6c56d4f0f3fd1d377c8a35d8d92e9d5f78f8f3fd0440f998fd2f45db7bae54'
LABELS = (
  'DETECTOR_FALSE_POSITIVE',
  'DETECTOR_MISS',
  'DETECTOR_LOCALIZATION_ERROR',
  'GT_MASK_AMBIGUOUS',
  'GT_EXTRA_MARKING',
  'COMPONENT_MATCHING_ERROR',
  'REPRESENTATION_MISMATCH',
  'FAR_FIELD_AMBIGUOUS',
  'INTERSECTION_OR_MERGE',
  'MULTI_LANE_AMBIGUOUS',
  'OTHER',
  'UNRESOLVED',
)
SCHEMA = {
  'version': 'PUBLIC_MARKING_HUMAN_REVIEW_V1',
  'labels': list(LABELS),
  'no_automatic_labels': True,
  'unreviewable_label': 'UNRESOLVED',
  'history': 'IMMUTABLE_ROWS_NO_OVERWRITE',
  'scope': 'DIAGNOSTIC_PUBLIC_GT_NOT_QUALIFICATION',
}
SCHEMA_SHA = digest(canonical(SCHEMA))
SCOPES = ('PUBLIC_COMMA10K_HUMAN_REVIEW', 'TEST_ONLY_BROWSER_VALIDATION')


def selection_policy():
  path = Path(__file__).resolve().parents[3] / 'docs/cyberpilot/changes/comma10k-full-review-selection-policy.json'
  value = storage.read_json(path)
  unseal(value)
  if value['receipt_sha256'] != POLICY_SHA:
    raise ValueError('FROZEN_REVIEW_POLICY_MISMATCH')
  return value


def public_frame_id(value):
  if (
    type(value) is not str
    or str(PurePosixPath(value)) != value
    or len(PurePosixPath(value).parts) != 2
    or value.split('/')[0] not in ('imgs', 'imgs2')
    or not value.endswith('.png')
    or '..' in value
    or '\\' in value
  ):
    raise ValueError('PUBLIC_COMMA10K_FRAME_REQUIRED')


def freeze_review(ledger, completion, policy, tool_sha256, *, scope='PUBLIC_COMMA10K_HUMAN_REVIEW'):
  unseal(policy)
  marker = unseal(completion)
  if policy != selection_policy() or not is_sha256(tool_sha256) or scope not in SCOPES:
    raise ValueError('FROZEN_REVIEW_POLICY_OR_TOOL_REQUIRED')
  if (
    type(ledger) is not list
    or not ledger
    or marker.get('storage_status') != 'COMPLETED'
    or type(marker.get('expected')) is not int
    or marker.get('processed') != marker['expected']
    or len(ledger) != marker['expected']
    or marker.get('reference_promotable') is not False
    or not is_sha256(marker.get('run_sha256'))
    or scope == SCOPES[0]
    and len(ledger) != 11888
  ):
    raise ValueError('EXACT_COMPLETED_POPULATION_REQUIRED')
  rows = sorted(ledger, key=lambda f: f['frame_id'])
  if len({r['frame_id'] for r in rows}) != len(rows):
    raise ValueError('DUPLICATE_REVIEW_FRAME')
  for row in rows:
    unseal(row)
    public_frame_id(row['frame_id'])
    for field in ('image_sha256', 'gt_mask_sha256', 'detector_result_sha256'):
      if not is_sha256(row.get(field)):
        raise ValueError('BOUND_PUBLIC_FRAME_IDENTITIES_REQUIRED')
    for field in ('raw_prediction_count', 'gt_components', 'missed_gt_components', 'row_tail_still_spatially_remote_points'):
      if type(row.get(field)) is not int or row[field] < 0:
        raise ValueError('INVALID_SELECTION_COUNTS')
    for dist in [row['pred_to_gt'], *(r['pred_to_gt'] for r in row['regions'].values())]:
      if dist['p95'] is not None and (type(dist['p95']) not in (int, float) or not math.isfinite(dist['p95']) or dist['p95'] < 0):
        raise ValueError('INVALID_SELECTION_DISTANCE')
  if marker.get('artifact_file_sha256', {}).get('ledger.json') != digest(canonical(rows) + b'\n'):
    raise ValueError('COMPLETED_LEDGER_FILE_BINDING_MISMATCH')
  ranked = sorted((r for r in rows if r['pred_to_gt']['p95'] is not None), key=lambda r: (r['pred_to_gt']['p95'], r['frame_id']))
  reasons = {}

  def choose(items, name):
    for row in items[:4]:
      reasons.setdefault(row['frame_id'], []).append(name)

  choose(sorted(ranked, key=lambda r: (-r['pred_to_gt']['p95'], r['frame_id'])), 'EXTREME_TAIL')
  choose(ranked, 'LOW_ERROR_CONTROL')
  n = len(ranked)
  start = max(0, min(n - 4, math.floor(0.95 * (n - 1)) - 2))
  choose(ranked[start : start + 4], 'P95_NEIGHBORHOOD')
  if n:
    lo, hi = math.floor(0.90 * (n - 1)), math.floor(0.95 * (n - 1))
    choose([ranked[i] for i in sorted({math.floor(lo + (hi - lo) * j / 3) for j in range(4)})], 'P90_TO_P95')
  for field, name, positive in (
    ('gt_components', 'HIGH_COMPONENT_COUNT', False),
    ('row_tail_still_spatially_remote_points', 'REMOTE_PREDICTION_HYPOTHESIS', True),
    ('missed_gt_components', 'GT_MISS_HYPOTHESIS', True),
  ):
    choose(sorted((r for r in rows if not positive or r[field] > 0), key=lambda r: (-r[field], r['frame_id'])), name)

  def far_dominant(row):
    far = row['regions']['far']['pred_to_gt']
    return (
      far['sample_count'] > 0
      and far['p95'] is not None
      and all(reg['pred_to_gt']['p95'] is None or far['p95'] >= reg['pred_to_gt']['p95'] for reg in row['regions'].values())
    )

  choose(sorted((r for r in rows if far_dominant(r)), key=lambda r: (-r['regions']['far']['pred_to_gt']['p95'], r['frame_id'])), 'FAR_FIELD_DOMINANT')
  choose(sorted((r for r in rows if r['raw_prediction_count'] >= 3), key=lambda r: (-r['gt_components'], r['frame_id'])), 'MULTI_LANE_ASSOCIATION_HYPOTHESIS')
  choose([r for r in rows if r['raw_prediction_count'] == 0], 'NO_OUTPUT')
  frames = [
    {
      'frame_id': r['frame_id'],
      'image_sha256': r['image_sha256'],
      'mask_sha256': r['gt_mask_sha256'],
      'prediction_sha256': r['detector_result_sha256'],
      'metric_result_sha256': r['receipt_sha256'],
      'reasons': reasons[r['frame_id']],
      'pred_to_gt': r['pred_to_gt'],
      'gt_to_pred': r['gt_to_pred'],
      'regions': r['regions'],
      'confidence': r['confidence'],
    }
    for r in rows
    if r['frame_id'] in reasons
  ]
  return seal(
    {
      'schema': 'PUBLIC_TAIL_HUMAN_REVIEW_MANIFEST_V1',
      'scope': scope,
      'frames': frames,
      'full_completion_sha256': completion['receipt_sha256'],
      'run_sha256': marker['run_sha256'],
      'selection_policy_sha256': POLICY_SHA,
      'review_schema_sha256': SCHEMA_SHA,
      'review_tool_sha256': tool_sha256,
      'status': 'TAIL_HUMAN_REVIEW_PENDING',
      'raw_images_included': False,
      'reference_promotable': False,
    }
  )


def validate_manifest(manifest):
  core = unseal(manifest)
  if (
    set(core)
    != {
      'schema',
      'scope',
      'frames',
      'full_completion_sha256',
      'run_sha256',
      'selection_policy_sha256',
      'review_schema_sha256',
      'review_tool_sha256',
      'status',
      'raw_images_included',
      'reference_promotable',
    }
    or core['schema'] != 'PUBLIC_TAIL_HUMAN_REVIEW_MANIFEST_V1'
    or core['scope'] not in SCOPES
    or core['status'] != 'TAIL_HUMAN_REVIEW_PENDING'
    or core['raw_images_included'] is not False
    or core['reference_promotable'] is not False
    or core['selection_policy_sha256'] != POLICY_SHA
    or core['review_schema_sha256'] != SCHEMA_SHA
    or any(not is_sha256(core[k]) for k in ('full_completion_sha256', 'run_sha256', 'review_tool_sha256'))
    or type(core['frames']) is not list
    or not 0 < len(core['frames']) <= 40
  ):
    raise ValueError('INVALID_REVIEW_MANIFEST')
  seen = set()
  for frame in core['frames']:
    public_frame_id(frame['frame_id'])
    if frame['frame_id'] in seen or any(not is_sha256(frame.get(k)) for k in ('image_sha256', 'mask_sha256', 'prediction_sha256', 'metric_result_sha256')):
      raise ValueError('DUPLICATE_OR_UNBOUND_REVIEW_FRAME')
    seen.add(frame['frame_id'])
  return core


def make_annotation(manifest, frame_id, *, label, reviewable, comment, timestamp, human_ack, tool_sha256):
  core = validate_manifest(manifest)
  frame = next((f for f in core['frames'] if f['frame_id'] == frame_id), None)
  if frame is None or tool_sha256 != core['review_tool_sha256']:
    raise ValueError('REVIEW_FRAME_OR_TOOL_BINDING_MISMATCH')
  if (
    label not in LABELS
    or type(reviewable) is not bool
    or human_ack is not True
    or not reviewable
    and label != 'UNRESOLVED'
    or type(comment) is not str
    or len(comment) > 2000
    or type(timestamp) is not str
    or not timestamp.endswith('Z')
  ):
    raise ValueError('EXPLICIT_HUMAN_REVIEW_REQUIRED')
  try:
    parsed = datetime.fromisoformat(timestamp[:-1] + '+00:00')
    if parsed.isoformat().replace('+00:00', 'Z') != timestamp:
      raise ValueError()
  except (ValueError, TypeError) as exc:
    raise ValueError('UTC_REVIEW_TIMESTAMP_REQUIRED') from exc
  return seal(
    {
      'schema': SCHEMA['version'],
      'frame_id': frame_id,
      **{k: frame[k] for k in ('image_sha256', 'mask_sha256', 'prediction_sha256', 'metric_result_sha256')},
      'reviewer_label': label,
      'reviewable': reviewable,
      'comment': comment,
      'review_timestamp': timestamp,
      'human_ack': True,
      'review_schema_sha256': SCHEMA_SHA,
      'review_tool_sha256': tool_sha256,
      'review_manifest_sha256': manifest['receipt_sha256'],
      'scope': core['scope'],
      'reference_promotable': False,
    }
  )


def validate_annotation(manifest, annotation):
  core = unseal(annotation)
  required = {
    'schema',
    'frame_id',
    'image_sha256',
    'mask_sha256',
    'prediction_sha256',
    'metric_result_sha256',
    'reviewer_label',
    'reviewable',
    'comment',
    'review_timestamp',
    'human_ack',
    'review_schema_sha256',
    'review_tool_sha256',
    'review_manifest_sha256',
    'scope',
    'reference_promotable',
  }
  if set(core) != required:
    raise ValueError('EXACT_REVIEW_ANNOTATION_REQUIRED')
  expected = make_annotation(
    manifest,
    core['frame_id'],
    label=core['reviewer_label'],
    reviewable=core['reviewable'],
    comment=core['comment'],
    timestamp=core['review_timestamp'],
    human_ack=core['human_ack'],
    tool_sha256=core['review_tool_sha256'],
  )
  if expected != annotation:
    raise ValueError('REVIEW_ANNOTATION_BINDING_MISMATCH')
  return core


def review_status(manifest, annotations):
  core = validate_manifest(manifest)
  if type(annotations) is not list:
    raise ValueError('REVIEW_ROWS_REQUIRED')
  rows = [validate_annotation(manifest, a) for a in annotations]
  if len({r['frame_id'] for r in rows}) != len(rows):
    raise ValueError('DUPLICATE_HUMAN_ANNOTATION')
  missing = sorted({f['frame_id'] for f in core['frames']} - {r['frame_id'] for r in rows})
  status = (
    'TEST_ONLY_NOT_HUMAN_EVIDENCE'
    if core['scope'] == SCOPES[1] and not missing
    else 'TAIL_HUMAN_REVIEW_PENDING'
    if missing
    else 'HUMAN_REVIEW_COMPLETE_DIAGNOSTIC'
  )
  # A reviewed diagnostic sample is not the full population or qualification GT.
  return seal(
    {
      'schema': 'PUBLIC_REVIEW_PROGRESS_V1',
      'status': status,
      'review_manifest_sha256': manifest['receipt_sha256'],
      'reviewed': len(rows),
      'expected': len(core['frames']),
      'missing': missing,
      'taxonomy_counts': dict(sorted(Counter(r['reviewer_label'] for r in rows).items())) if not missing and core['scope'] == SCOPES[0] else None,
      'detector_verdict': 'TAIL_UNRESOLVED',
      'reference_promotable': False,
      'private_input_allowed': False,
    }
  )
