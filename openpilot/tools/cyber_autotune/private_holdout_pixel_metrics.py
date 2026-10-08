"""Predeclared post-freeze pixel diagnostic math, never meter qualification.

Actual holdout inference is NOT performed by this module. Caller must execute
the frozen detector after the entire immutable human-reference freeze. Receipt
binding records declared execution, not proof that a model generated points.
"""
from itertools import product
from pathlib import Path

import numpy as np

from openpilot.tools.cyber_autotune import private_holdout_contract as h
from openpilot.tools.cyber_autotune import private_pixel_execution as p
from openpilot.tools.cyber_autotune.lane_tail_report import seal, unseal
from openpilot.tools.cyber_autotune.native_protocol import canonical, digest


def prediction_receipt(package, reference, ordinal, lanes, timestamp):
  h.require_detector_gate(package, reference)
  if h.c.utc(timestamp) < h.c.utc(reference['frozen_at']):
    raise ValueError('DETECTOR_EXECUTION_MUST_FOLLOW_ENTIRE_HUMAN_FREEZE')
  if type(ordinal) is not int or not 0 <= ordinal < h.EXPECTED:
    raise ValueError('EXACT_HOLDOUT_ORDINAL_REQUIRED')
  image = package['images'][ordinal]
  union = sorted({tuple(point) for lane in lanes for point in lane['points']}, key=lambda point: (point[1], point[0]))
  record = {'image_geometry': [image['height'], image['width']], 'lane_count': len(lanes),
            'points': [list(point) for point in union], 'lanes': lanes}
  p.validate_prediction(record, record['image_geometry'])
  for lane in lanes:
    if len({y for _, y in lane['points']}) != len(lane['points']):
      raise ValueError('UNIQUE_Y_PER_DETECTOR_POLYLINE_REQUIRED')
  return seal({
    'schema': 'PRIVATE_POST_FREEZE_PIXEL_PREDICTION_DECLARATION_V1',
    'sample_id': image['sample_id'], 'image_sha256': image['image_sha256'],
    'human_reference_sha256': reference['receipt_sha256'], 'detector': package['authorization']['detector'],
    'evaluation_policy_sha256': digest(canonical(h.EVALUATION_POLICY)),
    'metric_source_sha256': digest(Path(__file__).read_bytes()),
    'executed_at': timestamp, 'prediction': record, **h.FIREWALL,
  })


def distribution(values):
  return {'count': len(values), **{key: float(np.quantile(values, quantile, method='linear')) if values else None
                                for key, quantile in (('median', .5), ('p90', .9), ('p95', .95), ('maximum', 1.))}}


def assignment(human, lanes):
  sides = [side for side in ('left', 'right') if human[side]]
  edges = {}
  for side in sides:
    for index, lane in enumerate(lanes):
      rows = h.common_rows(human[side], lane['points'], integer=True)
      if rows:
        errors = [abs(l - r) for l, r in zip(h.interpolate(human[side], rows), h.interpolate(lane['points'], rows), strict=True)]
        edges[side, index] = (float(np.mean(errors)), rows, errors)
  choices = []
  for indices in product(range(-1, len(lanes)), repeat=len(sides)):
    selected = [i for i in indices if i >= 0]
    if len(set(selected)) != len(selected) or any((side, i) not in edges for side, i in zip(sides, indices, strict=True) if i >= 0):
      continue
    # Prefer greatest observed-support match count, then total geometry cost.
    cost = sum(edges[side, i][0] for side, i in zip(sides, indices, strict=True) if i >= 0)
    choices.append(((-len(selected), cost, indices), dict(zip(sides, indices, strict=True))))
  selected = min(choices, key=lambda row: row[0])[1] if choices else {}
  return {side: (index, edges[side, index]) for side, index in selected.items() if index >= 0}


def evaluate(package, reference, predictions):
  h.require_detector_gate(package, reference)
  if type(predictions) is not list or len(predictions) != h.EXPECTED:
    raise ValueError('ALL_SIXTY_POST_FREEZE_PREDICTIONS_REQUIRED')
  left, right, center = [], [], []
  unavailable = {'left': 0, 'right': 0}
  both, evaluable, unsupported, unmatched = 0, 0, 0, 0
  states = dict.fromkeys(h.STATES, 0)
  for ordinal, (human, prediction) in enumerate(zip(reference['annotations'], predictions, strict=True)):
    unseal(prediction)
    expected = prediction_receipt(package, reference, ordinal, prediction['prediction']['lanes'], prediction['executed_at'])
    if canonical(prediction) != canonical(expected):
      raise ValueError('EXACT_POST_FREEZE_DETECTOR_DECLARATION_REQUIRED')
    states[human['state']] += 1
    lanes = prediction['prediction']['lanes']
    if not human['left'] and not human['right']:
      continue  # Count ambiguity/unreviewable but never invent localization GT.
    evaluable += 1
    matched = assignment(human, lanes)
    unmatched += len(lanes) - len(matched)
    unsupported += sum(not any(h.common_rows(human[side], lane['points'], integer=True) for side in ('left', 'right') if human[side])
                       for lane in lanes)
    for side, errors in (('left', left), ('right', right)):
      if human[side]:
        if side in matched:
          errors.extend(matched[side][1][2])
        else:
          unavailable[side] += 1
    if human['state'] == 'BOTH_EGO_BOUNDARIES_VISIBLE' and set(matched) == {'left', 'right'}:
      both += 1
      detector_center = []
      lane_left, lane_right = [lanes[matched[side][0]]['points'] for side in ('left', 'right')]
      rows = h.common_rows(lane_left, lane_right, integer=True)
      if rows:
        detector_center = [[(l + r) / 2, y] for l, r, y in
                           zip(h.interpolate(lane_left, rows), h.interpolate(lane_right, rows), rows, strict=True)]
      human_center = h.pixel_center(human)
      ys = h.common_rows(human_center, detector_center, integer=True)
      if ys:
        center.extend(abs(l - r) for l, r in zip(h.interpolate(human_center, ys), h.interpolate(detector_center, ys), strict=True))
  return seal({
    'schema': 'PRIVATE_PIXEL_HUMAN_HOLDOUT_DIAGNOSTIC_V1',
    'status': 'DIAGNOSTIC_COMPLETE_QUALIFICATION_BLOCKED', 'total_frames': h.EXPECTED,
    'human_reference_sha256': reference['receipt_sha256'], 'state_counts': states,
    'evaluable_visible_boundary_frames': evaluable,
    'both_boundary_geometry_match_frames': both, 'left_unavailable_visible_frames': unavailable['left'],
    'right_unavailable_visible_frames': unavailable['right'], 'unsupported_no_y_overlap_lanes': unsupported,
    'unmatched_detector_lanes_not_false_positive_truth': unmatched,
    'left': distribution(left), 'right': distribution(right), 'combined': distribution(left + right),
    'center': distribution(center), 'pooling': 'OBSERVED_COMMON_INTEGER_ROWS_POINT_WEIGHTED',
    'matching_limitation': 'Y_OVERLAP_GEOMETRY_ASSIGNMENT_NOT_SEMANTIC_ASSOCIATION_QUALIFICATION',
    'public_comparison': 'SEPARATE_TARGET_PUBLIC_ALL_MARKINGS_PRIVATE_HUMAN_EGO_BOUNDARIES',
    'threshold': 'UNJUSTIFIED_NO_ACCEPT_REJECT_VERDICT', **h.FIREWALL,
  })
