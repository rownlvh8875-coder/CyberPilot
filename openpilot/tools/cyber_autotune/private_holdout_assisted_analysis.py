"""Read-only post-freeze diagnostics. All per-frame evidence remains private."""
from collections import Counter
from pathlib import Path

from openpilot.tools.cyber_autotune import private_holdout_assisted as a
from openpilot.tools.cyber_autotune import private_holdout_contract as h
from openpilot.tools.cyber_autotune import private_holdout_pixel_metrics as math

FAILURES = ('LEFT_MISS', 'RIGHT_MISS', 'BOTH_MISS', 'WRONG_LANE_ASSOCIATION', 'EXTRA_FALSE_POSITIVE',
            'INTERSECTION_OR_MERGE', 'HUMAN_AMBIGUOUS', 'OTHER', 'UNRESOLVED')
CONFIDENCE_BINS = ('0.00_TO_0.50', '0.50_TO_0.75', '0.75_TO_0.90', '0.90_TO_1.00', 'NO_OUTPUT', 'UNKNOWN_CONFIDENCE')
POLICY = {
  'schema': 'PRIVATE_ASSISTED_POST_FREEZE_ANALYSIS_POLICY_V1',
  'matching': h.EVALUATION_POLICY,
  'confidence': 'FRAME_MEAN_LANE_SCORE_BINS_[0,.5)_[.5,.75)_[.75,.9)_[.9,1];NO_OUTPUT_SEPARATE',
  'confidence_use': 'DESCRIPTIVE_ONLY_NO_THRESHOLD_OPTIMIZATION;MISSING_SCORES_UNKNOWN_NOT_ZERO',
  'modification': 'CHANGED_BOUNDARIES_COMMON_OBSERVED_INTEGER_Y_ABSOLUTE_X_DELTA;ADDITIONS_NOT_ZERO_DISTANCE',
  'failure': 'FROZEN_Y_OVERLAP_MATCH_UNAVAILABLE_NOT_SEMANTIC_FALSE_POSITIVE_ADJUDICATION',
  'center': 'COMMON_OBSERVED_INTEGER_Y_MIDPOINT_NO_EXTRAPOLATION',
  'pooling': 'POINT_WEIGHTED_REPORT_FRAME_COUNTS_SEPARATELY',
  **h.FIREWALL,
}
CRITICAL_PATH = (
  ('CALIBRATION_MEASUREMENT_PENDING', [], 'Actual physically observed measurements with uncertainties and provenance'),
  ('INDEPENDENT_CALIBRATION_VALIDATION_PENDING', ['CALIBRATION_MEASUREMENT_PENDING'], 'Independent validation of admitted measurement'),
  ('METRIC_CALIBRATION_UNAVAILABLE', ['INDEPENDENT_CALIBRATION_VALIDATION_PENDING'], 'Validated calibration and conservative projection budget'),
  ('EGO_ASSOCIATION_VALIDATION_PENDING', [], 'Independent ego-association validation; assisted matching is insufficient'),
  ('INDEPENDENT_REFERENCE_UNAVAILABLE', ['METRIC_CALIBRATION_UNAVAILABLE', 'EGO_ASSOCIATION_VALIDATION_PENDING'],
   'Road registration, desired-path provenance and all existing strict evidence gates'),
)


def confidence_bucket(value):
  if value is None:
    return 'NO_OUTPUT'
  value = h.finite(value)
  if not 0 <= value <= 1:
    raise ValueError('CONFIDENCE_DOMAIN')
  return CONFIDENCE_BINS[0 if value < .5 else 1 if value < .75 else 2 if value < .9 else 3]


def center_points(left, right):
  ys = h.common_rows(left, right, integer=True)
  if not ys:
    return []
  return [[(l + r) / 2, y] for l, r, y in zip(h.interpolate(left, ys), h.interpolate(right, ys), ys, strict=True)]


def group_summary(rows):
  left = [v for r in rows for v in r['errors']['left']]
  right = [v for r in rows for v in r['errors']['right']]
  both = [r for r in rows if r['both_visible']]
  matched = sum(r['both_matched'] for r in both)
  return {'frames': len(rows), 'left': math.distribution(left), 'right': math.distribution(right),
          'both_visible_frames': len(both), 'both_matched_frames': matched,
          'both_boundary_matching_rate': matched / len(both) if both else None}


def analyze(package, auth, ai_rows, reference, detector_auth, predictions, evaluation):
  # Recompute with authoritative unchanged admission/math; stale or incomplete inputs fail closed.
  expected = a.evaluate(package, auth, ai_rows, reference, detector_auth, predictions)
  h.unseal(evaluation)
  if h.canonical(expected) != h.canonical(evaluation):
    raise ValueError('HISTORICAL_EVALUATION_MISMATCH')
  rows, bindings, failure_ledger, magnitudes = [], [], [], []
  changes = Counter()
  added, removed, no_common, state_changes = 0, 0, 0, 0
  center_errors, center_available = [], 0
  lane_counts = Counter()
  all_scores, frame_scores, extents = [], [], []
  unknown_scores, empty_geometry = 0, 0
  for ai, human, pred, image in zip(ai_rows, reference['annotations'], predictions, package['images'], strict=True):
    lanes = pred['prediction']['lanes']
    matched = math.assignment(human, lanes)
    errors = {side: matched[side][1][2] if side in matched else [] for side in ('left', 'right')}
    scores = [lane['confidence'] for lane in lanes]
    known_scores = [score for score in scores if score is not None]
    mean_score = sum(scores) / len(scores) if scores and len(known_scores) == len(scores) else None
    bucket = 'UNKNOWN_CONFIDENCE' if scores and mean_score is None else confidence_bucket(mean_score)
    unknown_scores += len(scores) - len(known_scores)
    all_scores.extend(known_scores)
    if mean_score is not None:
      frame_scores.append(mean_score)
    lane_counts[len(lanes)] += 1
    empty_geometry += sum(not lane['points'] for lane in lanes)
    extents.extend((max(pt[1] for pt in lane['points']) - min(pt[1] for pt in lane['points'])) / image['height']
                   for lane in lanes if lane['points'])
    both_visible = human['state'] == 'BOTH_EGO_BOUNDARIES_VISIBLE'
    both_matched = both_visible and set(matched) == {'left', 'right'}
    hc = center_points(human['left'], human['right']) if both_visible else []
    dc = center_points(lanes[matched['left'][0]]['points'], lanes[matched['right'][0]]['points']) if both_matched else []
    common = h.common_rows(hc, dc, integer=True)
    ce = [abs(l - r) for l, r in zip(h.interpolate(hc, common), h.interpolate(dc, common), strict=True)] if common else []
    center_errors.extend(ce)
    center_available += bool(ce)
    missing = [side for side in ('left', 'right') if human[side] and side not in matched]
    cause = 'BOTH_MISS' if len(missing) == 2 else 'LEFT_MISS' if missing == ['left'] else 'RIGHT_MISS' if missing else None
    binding = {'sample_id': image['sample_id'], 'image_sha256': image['image_sha256'],
               'manifest_sha256': image['manifest_sha256'], 'ai_sha256': ai['receipt_sha256'],
               'human_sha256': human['receipt_sha256'], 'action': human['action'],
               'prediction_sha256': pred['prediction_sha256'], 'detector_receipt_sha256': pred['receipt_sha256']}
    bindings.append(binding)
    if both_visible and not both_matched:
      failure_ledger.append({**binding, 'category': cause or 'UNRESOLVED',
                             'basis': 'OBSERVED_Y_SUPPORT_GEOMETRY_ASSIGNMENT_ONLY_NOT_SEMANTIC_MISS_TRUTH',
                             'missing_sides': missing, 'lane_count': len(lanes),
                             'confidence_bucket': bucket, 'matched_lane_indices': {k: v[0] for k, v in matched.items()},
                             'semantic_wrong_association': 'NOT_ADJUDICATED',
                             'extra_false_positive': 'NOT_ADJUDICATED'})
    changed = [side for side in ('left', 'right') if ai[side] != human[side]]
    if human['action'] == 'MODIFY_AI':
      state_changes += ai['state'] != human['state']
      kind = 'BOTH' if len(changed) == 2 else 'LEFT_ONLY' if changed == ['left'] else 'RIGHT_ONLY' if changed else 'STATE_ONLY'
      changes[kind] += 1
      for side in changed:
        added += not ai[side] and bool(human[side])
        removed += bool(ai[side]) and not human[side]
        if ai[side] and human[side]:
          ys = h.common_rows(ai[side], human[side], integer=True)
          no_common += not bool(ys)
          magnitudes.extend(abs(l - r) for l, r in zip(h.interpolate(ai[side], ys), h.interpolate(human[side], ys), strict=True))
    rows.append({**binding, 'both_visible': both_visible, 'both_matched': both_matched, 'errors': errors,
                 'human_pixel_center': hc, 'center_errors': ce, 'missing_sides': missing,
                 'confidence_bucket': bucket, 'mean_lane_confidence': mean_score, 'state': human['state']})
  groups = {action: group_summary([r for r in rows if r['action'] == action]) for action in a.ACTIONS}
  confidence = {'buckets': {}, 'threshold_optimization': False}
  for bucket in CONFIDENCE_BINS:
    selected = [r for r in rows if r['confidence_bucket'] == bucket]
    confidence['buckets'][bucket] = {**group_summary(selected),
                                    'left_unavailable': sum('left' in r['missing_sides'] for r in selected),
                                    'right_unavailable': sum('right' in r['missing_sides'] for r in selected),
                                    'evaluable_frames': sum(bool(r['errors']['left'] or r['errors']['right'] or r['missing_sides']) for r in selected)}
  both_count = reference['state_counts']['BOTH_EGO_BOUNDARIES_VISIBLE']
  return h.seal({
    'schema': 'PRIVATE_ASSISTED_HOLDOUT_FINAL_ANALYSIS_V1',
    'status': 'PRIVATE_ASSISTED_HUMAN_HOLDOUT_COMPLETE', 'evaluation_status': 'PRIVATE_PIXEL_HOLDOUT_EVALUATION_COMPLETE',
    'total_frames': h.EXPECTED, 'ai_generated': len(ai_rows), 'human_verified': len(reference['annotations']),
    'reference_sha256': reference['receipt_sha256'], 'evaluation_sha256': evaluation['receipt_sha256'],
    'materialization_sha256': package['receipt_sha256'], 'authorization_sha256': auth['receipt_sha256'],
    'detector_authorization_sha256': detector_auth['receipt_sha256'],
    'original_ai_set_sha256': h.digest(h.canonical([r['receipt_sha256'] for r in ai_rows])),
    'human_final_set_sha256': h.digest(h.canonical([r['receipt_sha256'] for r in reference['annotations']])),
    'bindings': bindings, 'binding_set_sha256': h.digest(h.canonical(bindings)),
    'analysis_source_sha256': h.digest(Path(__file__).read_bytes()),
    'policy': POLICY, 'policy_sha256': h.digest(h.canonical(POLICY)),
    'groups': groups, 'rows': rows, 'failure_ledger': failure_ledger,
    'failure_counts': {name: sum(r['category'] == name for r in failure_ledger) for name in FAILURES},
    'failure_scope': 'BOTH_VISIBLE_UNMATCHED_FRAMES_ONLY;OTHER_CATEGORIES_NOT_AUTOMATICALLY_ADJUDICATED',
    'modifications': {'geometry_change_counts': {k: changes[k] for k in ('LEFT_ONLY', 'RIGHT_ONLY', 'BOTH', 'STATE_ONLY')},
                      'state_changes': state_changes, 'added_boundary_count': added, 'removed_boundary_count': removed,
                      'changed_boundary_no_common_span': no_common,
                      'original_to_final_px': math.distribution(magnitudes),
                      'semantics': 'AI_DRAFT_CORRECTION_NOT_DETECTOR_ERROR;ADDED_BOUNDARY_HAS_NO_DISTANCE'},
    'combined': evaluation['combined'],
    'center': {**math.distribution(center_errors), 'both_visible_denominator': both_count,
               'available_frames': center_available, 'unavailable_frames': both_count - center_available,
               'units': 'ORIGINAL_IMAGE_PIXELS', 'schema': 'HUMAN_PIXEL_EGO_CENTER_REFERENCE'},
    'confidence': confidence,
    'prediction_only': {'frames': h.EXPECTED, 'lane_count_distribution': {str(k): v for k, v in sorted(lane_counts.items())},
                        'no_output_count': lane_counts[0], 'no_output_rate': lane_counts[0] / h.EXPECTED,
                        'unknown_confidence_lanes': unknown_scores, 'empty_geometry_lanes': empty_geometry,
                        'per_frame_mean_confidence': math.distribution(frame_scores),
                        'per_lane_confidence': math.distribution(all_scores),
                        'per_lane_normalized_vertical_extent': math.distribution(extents)},
    'blockers': {name: {'status': 'BLOCKED', 'dependencies': dependencies, 'resolution_condition': condition,
                        'evidence_sha256': evaluation['receipt_sha256']} for name, dependencies, condition in CRITICAL_PATH},
    'detector_status': 'PRIVATE_REFERENCE_CANDIDATE_DIAGNOSTIC_ONLY',
    'next_priority': 'PHYSICAL_CALIBRATION_AND_PIXEL_TO_METER_UNCERTAINTY;NO_HOLDOUT_BASED_DETECTOR_TUNING',
    'qualification_threshold': 'UNJUSTIFIED_NO_PASS_FAIL',
    'sealed_reference': 'NOT_GENERATED', 'vehicle_status': ['NOT_READY', 'REAL_VEHICLE_UNVERIFIED', 'VEHICLE_ACTIVATION_BLOCKED'],
    'blind_human': False, 'assisted_human': True, **h.FIREWALL,
  })


# Deliberate publication allowlist: never copy per-frame or human-provided material.
PUBLIC_KEYS = (
  'status', 'evaluation_status', 'total_frames', 'ai_generated', 'human_verified', 'reference_sha256',
  'evaluation_sha256', 'materialization_sha256', 'authorization_sha256', 'detector_authorization_sha256',
  'original_ai_set_sha256', 'human_final_set_sha256', 'binding_set_sha256', 'analysis_source_sha256',
  'policy', 'policy_sha256', 'groups', 'failure_counts', 'failure_scope', 'modifications', 'combined',
  'center', 'confidence', 'prediction_only', 'blockers', 'detector_status', 'next_priority',
  'qualification_threshold', 'sealed_reference', 'vehicle_status', 'blind_human', 'assisted_human',
)


def publication(report):
  h.unseal(report)
  if report.get('schema') != 'PRIVATE_ASSISTED_HOLDOUT_FINAL_ANALYSIS_V1' or report['policy'] != POLICY:
    raise ValueError('EXACT_ANALYSIS_POLICY_REQUIRED')
  if any(report.get(k) is not value for k, value in h.FIREWALL.items()) or report['blind_human'] is not False or report['assisted_human'] is not True:
    raise ValueError('NO_PROMOTION_ALLOWED')
  _require_public_shape(report)
  return h.seal({'schema': 'PRIVATE_ASSISTED_HOLDOUT_AGGREGATE_PUBLIC_V1',
                 'local_analysis_sha256': report['receipt_sha256'],
                 **{k: report[k] for k in PUBLIC_KEYS}, **h.FIREWALL})


def _counts(value, keys):
  h.c.exact(value, keys)
  if any(type(n) is not int or n < 0 for n in value.values()):
    raise ValueError('NONNEGATIVE_INTEGER_COUNTS_REQUIRED')


def _distribution(value):
  h.c.exact(value, ('count', 'median', 'p90', 'p95', 'maximum'))
  _counts({'count': value['count']}, ('count',))
  numbers = [value[k] for k in ('median', 'p90', 'p95', 'maximum')]
  if value['count'] == 0:
    if any(n is not None for n in numbers):
      raise ValueError('EMPTY_DISTRIBUTION_REQUIRES_NULL')
  elif any(type(n) not in (int, float) or h.finite(n) < 0 for n in numbers) or numbers != sorted(numbers):
    raise ValueError('FINITE_ORDERED_PIXEL_DISTRIBUTION_REQUIRED')


def _group(value, *, confidence=False):
  keys = ('frames', 'left', 'right', 'both_visible_frames', 'both_matched_frames', 'both_boundary_matching_rate')
  h.c.exact(value, keys + (('left_unavailable', 'right_unavailable', 'evaluable_frames') if confidence else ()))
  count_keys = ('frames', 'both_visible_frames', 'both_matched_frames')
  _counts({k: value[k] for k in count_keys}, count_keys)
  if not 0 <= value['both_matched_frames'] <= value['both_visible_frames'] <= value['frames'] <= h.EXPECTED:
    raise ValueError('FRAME_ACCOUNTING')
  expected = value['both_matched_frames'] / value['both_visible_frames'] if value['both_visible_frames'] else None
  if value['both_boundary_matching_rate'] != expected:
    raise ValueError('MATCH_RATE_ACCOUNTING')
  if confidence:
    _counts({k: value[k] for k in ('left_unavailable', 'right_unavailable', 'evaluable_frames')},
            ('left_unavailable', 'right_unavailable', 'evaluable_frames'))
  for side in ('left', 'right'):
    _distribution(value[side])


def _require_public_shape(r):
  for k in PUBLIC_KEYS:
    if k.endswith('_sha256'):
      h.c.sha(r[k])
  _counts({k: r[k] for k in ('total_frames', 'ai_generated', 'human_verified')}, ('total_frames', 'ai_generated', 'human_verified'))
  fixed = {'status': 'PRIVATE_ASSISTED_HUMAN_HOLDOUT_COMPLETE',
           'evaluation_status': 'PRIVATE_PIXEL_HOLDOUT_EVALUATION_COMPLETE',
           'total_frames': h.EXPECTED, 'ai_generated': h.EXPECTED, 'human_verified': h.EXPECTED,
           'policy_sha256': h.digest(h.canonical(POLICY)),
           'detector_status': 'PRIVATE_REFERENCE_CANDIDATE_DIAGNOSTIC_ONLY',
           'next_priority': 'PHYSICAL_CALIBRATION_AND_PIXEL_TO_METER_UNCERTAINTY;NO_HOLDOUT_BASED_DETECTOR_TUNING',
           'qualification_threshold': 'UNJUSTIFIED_NO_PASS_FAIL', 'sealed_reference': 'NOT_GENERATED',
           'failure_scope': 'BOTH_VISIBLE_UNMATCHED_FRAMES_ONLY;OTHER_CATEGORIES_NOT_AUTOMATICALLY_ADJUDICATED',
           'vehicle_status': ['NOT_READY', 'REAL_VEHICLE_UNVERIFIED', 'VEHICLE_ACTIVATION_BLOCKED']}
  if any(r[k] != v for k, v in fixed.items()):
    raise ValueError('FIXED_NONQUALIFYING_STATES_REQUIRED')
  expected_blockers = {name: {'status': 'BLOCKED', 'dependencies': dependencies, 'resolution_condition': condition,
                             'evidence_sha256': r['evaluation_sha256']} for name, dependencies, condition in CRITICAL_PATH}
  if r['blockers'] != expected_blockers:
    raise ValueError('BLOCKERS_CANNOT_CLEAR')
  h.c.exact(r['groups'], a.ACTIONS)
  for value in r['groups'].values():
    _group(value)
  if sum(v['frames'] for v in r['groups'].values()) != h.EXPECTED:
    raise ValueError('SIXTY_GROUP_ACCOUNTING_REQUIRED')
  _counts(r['failure_counts'], FAILURES)
  missing = sum(g['both_visible_frames'] - g['both_matched_frames'] for g in r['groups'].values())
  if sum(r['failure_counts'].values()) != missing:
    raise ValueError('FAILURE_LEDGER_ACCOUNTING')
  if any(r['failure_counts'][key] for key in FAILURES if key not in ('LEFT_MISS', 'RIGHT_MISS', 'BOTH_MISS')):
    raise ValueError('SEMANTIC_CAUSES_NOT_ADJUDICATED')
  _distribution(r['combined'])
  center = dict(r['center'])
  h.c.exact(center, ('count', 'median', 'p90', 'p95', 'maximum', 'both_visible_denominator', 'available_frames',
                     'unavailable_frames', 'units', 'schema'))
  if center.pop('schema') != 'HUMAN_PIXEL_EGO_CENTER_REFERENCE' or center.pop('units') != 'ORIGINAL_IMAGE_PIXELS':
    raise ValueError('PIXEL_CENTER_ONLY')
  counts = {k: center.pop(k) for k in ('both_visible_denominator', 'available_frames', 'unavailable_frames')}
  _counts(counts, counts.keys())
  if counts['available_frames'] + counts['unavailable_frames'] != counts['both_visible_denominator']:
    raise ValueError('CENTER_FRAME_ACCOUNTING')
  if counts['both_visible_denominator'] != sum(g['both_visible_frames'] for g in r['groups'].values()):
    raise ValueError('CENTER_DENOMINATOR_MUST_MATCH_GROUPS')
  if counts['available_frames'] > sum(g['both_matched_frames'] for g in r['groups'].values()):
    raise ValueError('CENTER_REQUIRES_BOTH_MATCHED')
  _distribution(center)
  if bool(center['count']) != bool(counts['available_frames']):
    raise ValueError('CENTER_POINT_FRAME_ACCOUNTING')
  modification = r['modifications']
  h.c.exact(modification, ('geometry_change_counts', 'state_changes', 'added_boundary_count', 'removed_boundary_count',
                           'changed_boundary_no_common_span', 'original_to_final_px', 'semantics'))
  _counts(modification['geometry_change_counts'], ('LEFT_ONLY', 'RIGHT_ONLY', 'BOTH', 'STATE_ONLY'))
  _counts({k: modification[k] for k in ('state_changes', 'added_boundary_count', 'removed_boundary_count',
                                       'changed_boundary_no_common_span')},
          ('state_changes', 'added_boundary_count', 'removed_boundary_count', 'changed_boundary_no_common_span'))
  if sum(modification['geometry_change_counts'].values()) != r['groups']['MODIFY_AI']['frames']:
    raise ValueError('MODIFICATION_ACCOUNTING')
  if modification['semantics'] != 'AI_DRAFT_CORRECTION_NOT_DETECTOR_ERROR;ADDED_BOUNDARY_HAS_NO_DISTANCE':
    raise ValueError('MODIFICATION_SEMANTICS')
  _distribution(modification['original_to_final_px'])
  h.c.exact(r['confidence'], ('buckets', 'threshold_optimization'))
  if r['confidence']['threshold_optimization'] is not False:
    raise ValueError('NO_CONFIDENCE_TUNING')
  h.c.exact(r['confidence']['buckets'], CONFIDENCE_BINS)
  for value in r['confidence']['buckets'].values():
    _group(value, confidence=True)
  if sum(v['frames'] for v in r['confidence']['buckets'].values()) != h.EXPECTED:
    raise ValueError('CONFIDENCE_FRAME_ACCOUNTING')
  for k in ('both_visible_frames', 'both_matched_frames'):
    if sum(g[k] for g in r['groups'].values()) != sum(g[k] for g in r['confidence']['buckets'].values()):
      raise ValueError('CONFIDENCE_GROUP_ACCOUNTING')
  prediction = r['prediction_only']
  h.c.exact(prediction, ('frames', 'lane_count_distribution', 'no_output_count', 'no_output_rate',
                         'per_frame_mean_confidence', 'per_lane_confidence', 'per_lane_normalized_vertical_extent',
                         'unknown_confidence_lanes', 'empty_geometry_lanes'))
  lane_counts = prediction['lane_count_distribution']
  if any(not isinstance(k, str) or not k.isdigit() or len(k) > 3 for k in lane_counts):
    raise ValueError('NUMERIC_LANE_COUNT_KEYS_ONLY')
  _counts(lane_counts, lane_counts.keys())
  if sum(lane_counts.values()) != h.EXPECTED or prediction['frames'] != h.EXPECTED:
    raise ValueError('PREDICTION_ACCOUNTING')
  if prediction['no_output_count'] != lane_counts.get('0', 0) or prediction['no_output_rate'] != lane_counts.get('0', 0) / h.EXPECTED:
    raise ValueError('NO_OUTPUT_ACCOUNTING')
  _counts({k: prediction[k] for k in ('unknown_confidence_lanes', 'empty_geometry_lanes')},
          ('unknown_confidence_lanes', 'empty_geometry_lanes'))
  for k in ('per_frame_mean_confidence', 'per_lane_confidence', 'per_lane_normalized_vertical_extent'):
    _distribution(prediction[k])
