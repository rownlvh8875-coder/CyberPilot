"""Post-result public marking diagnostics. No qualification, ego identity or meters.

Legacy horizontal row-midpoint distances stay unchanged. Spatial nearest-midpoint
distances are an explicit counterfactual, not a replacement metric. Paint
components use 8-connectivity; exact pixel-cell support is many-to-many because
one continuous lane can span several painted dashes. Components are not lanes.
"""

import math
import numpy as np

from openpilot.tools.cyber_autotune.lane_marking_metrics import marking_frame
from openpilot.tools.cyber_autotune.native_protocol import canonical, digest


def policy():
  return {
    'version': 'POST_RESULT_COMMA10K_TAIL_V1',
    'unit': 'px',
    'scope': 'DIAGNOSTIC_PUBLIC_GT',
    'directional_metric': 'UNCHANGED_SAME_ROW_RUN_MIDPOINT',
    'spatial_metric': 'EUCLIDEAN_NEAREST_ROW_RUN_MIDPOINT_NO_FILL',
    'symmetric_metric': 'POOLED_DIRECTIONAL_SAMPLES_NOT_BALANCED_F1',
    'components': '8_CONNECTED_PAINT_EXACT_CELL_SUPPORT_MANY_TO_MANY',
    'y_bins': 'far=[0,H//3);mid=[H//3,2H//3);near=[2H//3,H)',
    'confidence_edges': [0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
    'tail_width_fraction': 0.25,
    'spatial_resolved_width_fraction': 0.05,
    'tail_cut_rationale': 'DIAGNOSTIC_GEOMETRY_BIN_ONLY_NOT_ACCEPTANCE_THRESHOLD',
    'ego_lane_identity': False,
    'meter_conversion': False,
    'reference_promotable': False,
    'private_input_allowed': False,
  }


def policy_sha(value):
  return digest(canonical(value))


def validate_policy(value):
  if value != policy():
    raise ValueError('FROZEN_TAIL_POLICY_MISMATCH')


def distribution(values):
  a = np.asarray(values, dtype=float)
  if a.ndim != 1 or not np.all(np.isfinite(a)) or np.any(a < 0):
    raise ValueError('INVALID_DISTANCE_VECTOR')
  return {
    'sample_count': len(a),
    **{
      name: float(np.quantile(a, q, method='linear')) if len(a) else None
      for name, q in (('median', 0.5), ('p90', 0.9), ('p95', 0.95), ('p99', 0.99), ('maximum', 1.0))
    },
  }


def _rows(mask):
  rows = []
  for row in mask:
    delta = np.diff(np.r_[False, row, False].astype(np.int8))
    rows.append([(int(a), int(b)) for a, b in zip(np.where(delta == 1)[0], np.where(delta == -1)[0], strict=True)])
  return rows


def paint_components(mask):
  if not isinstance(mask, np.ndarray) or mask.dtype != np.bool_ or mask.ndim != 2 or not 0 < mask.size <= 6_000_000:
    raise ValueError('INVALID_COMPONENT_MASK')
  rows = _rows(mask)
  parents, indexed, previous = [], [], []

  def root(i):
    while parents[i] != i:
      parents[i] = parents[parents[i]]
      i = parents[i]
    return i

  for runs in rows:
    current = []
    for a, b in runs:
      i = len(parents)
      parents.append(i)
      for c, d, j in previous:
        if a <= d and c <= b:  # Adjacent columns connect diagonally across rows.
          ri, rj = root(i), root(j)
          parents[max(ri, rj)] = min(ri, rj)
      current.append((a, b, i))
    indexed.append(current)
    previous = current
  roots = sorted({root(i) for i in range(len(parents))})
  labels = {r: i for i, r in enumerate(roots)}
  return {'count': len(roots), 'rows': [[(a, b, labels[root(i)]) for a, b, i in runs] for runs in indexed]}


def spatial_distances(source, target):
  if not source or not target:
    return []
  if len(source) * len(target) > 25_000_000:
    raise ValueError('SPATIAL_PAIR_RESOURCE_BUDGET_EXCEEDED')
  s, t = np.asarray(source, dtype=float), np.asarray(target, dtype=float)
  if s.ndim != 2 or t.ndim != 2 or s.shape[1] != 2 or t.shape[1] != 2 or not np.all(np.isfinite(s)) or not np.all(np.isfinite(t)):
    raise ValueError('INVALID_SPATIAL_POINTS')
  # Chunked brute-force reference: bounded memory and no backend-dependent EDT approximation.
  result = []
  for start in range(0, len(s), 128):
    squared = np.sum((s[start : start + 128, None, :] - t[None, :, :]) ** 2, axis=2)
    result.extend(np.sqrt(np.min(squared, axis=1)).tolist())
  return result


def confidence_bucket(score):
  if type(score) not in (float, int) or not math.isfinite(score) or not 0 <= score <= 1:
    raise ValueError('INVALID_CONFIDENCE')
  edges = policy()['confidence_edges']
  i = min(int(score * 5), 4)
  return f'{edges[i]:.1f}:{edges[i + 1]:.1f}'


def original_to_network(x, y, width, height):
  # Geometry coordinates, not intensity resampling or recovered camera calibration.
  return x / width * 800, (y / height * 590 - 270) / 320 * 320


def network_to_original(u, v, width, height):
  return u / 800 * width, (v + 270) / 590 * height


def _direction_samples(mask, points):
  rows = _rows(mask)
  gt = [[(a + b - 1) / 2, y] for y, runs in enumerate(rows) for a, b in runs]
  by_row = {}
  for x, y in points:
    by_row.setdefault(y, []).append(x)
  pred_pairs, gt_pairs = [], []
  for x, y in points:
    centers = [(a + b - 1) / 2 for a, b in rows[y]]
    if centers:
      pred_pairs.append((x, y, min(abs(x - c) for c in centers)))
  for x, y in gt:
    if y in by_row:
      gt_pairs.append((x, y, min(abs(x - p) for p in by_row[y])))
  return gt, pred_pairs, gt_pairs


def _validate_lane_points(mask, lane):
  # Same domain as legacy marking_frame without recomputing every empty row.
  if (
    not isinstance(mask, np.ndarray)
    or mask.dtype != np.bool_
    or mask.ndim != 2
    or not 0 < mask.size <= 6_000_000
    or type(lane) is not list
    or len(lane) > 6_000_000
  ):
    raise ValueError('INVALID_PIXEL_METRIC_INPUT')
  seen = set()
  h, w = mask.shape
  for point in lane:
    if (
      type(point) not in (tuple, list)
      or len(point) != 2
      or type(point[0]) not in (int, float)
      or not math.isfinite(point[0])
      or type(point[1]) is not int
      or not 0 <= point[0] <= w - 1
      or not 0 <= point[1] < h
    ):
      raise ValueError('INVALID_ORIGINAL_PIXEL_POINT')
    if tuple(point) in seen:
      raise ValueError('DUPLICATE_PIXEL_POINT')
    seen.add(tuple(point))


def analyze_frame(mask, lanes, confidence):
  if type(lanes) is not list or type(confidence) is not list or len(lanes) != len(confidence):
    raise ValueError('EXACT_LANE_CONFIDENCE_BINDING_REQUIRED')
  for lane, score in zip(lanes, confidence, strict=True):
    confidence_bucket(score)
    if type(lane) is not list or not lane:
      raise ValueError('NONEMPTY_OBSERVABLE_LANE_REQUIRED')
    _validate_lane_points(mask, lane)  # Same strict domain, never clip or fill.
  points = [list(p) for p in sorted({tuple(p) for lane in lanes for p in lane}, key=lambda p: (p[1], p[0]))]
  legacy = marking_frame(mask, points)
  components = paint_components(mask)
  gt, pp, gp = _direction_samples(mask, points)
  edges = set()
  for i, lane in enumerate(lanes):
    for x, y in lane:
      for a, b, c in components['rows'][y]:
        if a - 0.5 <= x < b - 0.5:
          edges.add((i, c))
  supported = {i for i, _ in edges}
  covered = {c for _, c in edges}
  spatial = spatial_distances(points, gt)
  row_spatial = spatial_distances([[x, y] for x, y, _ in pp], gt)
  w, h = mask.shape[1], mask.shape[0]
  cutoff, resolved = w * policy()['tail_width_fraction'], w * policy()['spatial_resolved_width_fraction']
  tails = [(p, d) for p, d in zip(pp, row_spatial, strict=True) if p[2] > cutoff]
  row_resolved = sum(d <= resolved for _, d in tails)
  category = (
    'GT_UNAVAILABLE'
    if not gt
    else 'NO_PREDICTION'
    if not points
    else 'MIXED_ROW_AND_SPATIAL_TAIL'
    if tails and 0 < row_resolved < len(tails)
    else 'ROW_ASSOCIATION_SENSITIVE'
    if tails and row_resolved == len(tails)
    else 'SPATIALLY_REMOTE_PREDICTION'
    if tails
    else 'NO_LARGE_ROW_TAIL'
  )
  regions = {}
  for name, lo, hi in (('far', 0, h // 3), ('mid', h // 3, 2 * h // 3), ('near', 2 * h // 3, h)):
    sub = marking_frame(mask[lo:hi], [[x, y - lo] for x, y in points if lo <= y < hi])
    regions[name] = {
      k: sub[k]
      for k in ('pred_to_gt', 'gt_to_pred', 'coverage', 'pred_points', 'gt_runs', 'unsupported_pred_points', 'unavailable_gt_runs', 'off_marking_pred_points')
    }
  result = {
    'unit': 'px',
    'geometry': [h, w],
    'policy_sha256': policy_sha(policy()),
    'prediction_count': len(lanes),
    'gt_components': components['count'],
    'pred_points': len(points),
    'pred_to_gt': distribution(legacy['pred_errors_px']),
    'gt_to_pred': distribution(legacy['gt_errors_px']),
    'symmetric': distribution(legacy['pred_errors_px'] + legacy['gt_errors_px']),
    'spatial_pred_to_gt': distribution(spatial),
    'spatial_gt_to_pred': distribution(spatial_distances(gt, points)),
    'coverage': legacy['coverage'],
    'supported_prediction_ratio': 1 - legacy['false_positive_support_rate'] if points else None,
    'unsupported_prediction_ratio': legacy['false_positive_support_rate'],
    'missed_gt_ratio': 1 - legacy['coverage'] if gt else None,
    'support_edges': [list(edge) for edge in sorted(edges)],
    'false_positive_components': len(lanes) - len(supported),
    'missed_gt_components': components['count'] - len(covered),
    'unmatched_component_count': len(lanes) - len(supported) + components['count'] - len(covered),
    'row_tail_points': len(tails),
    'row_tail_spatially_resolved_points': row_resolved,
    'row_tail_still_spatially_remote_points': len(tails) - row_resolved,
    'failure_category': category,
    'regions': regions,
    'confidence': {
      'minimum': min(confidence) if confidence else None,
      'maximum': max(confidence) if confidence else None,
      'median': float(np.median(confidence)) if confidence else None,
    },
    'legacy_receipt_sha256': legacy['receipt_sha256'],
    'reference_promotable': False,
    'ego_lane_association_evaluated': False,
    'meter_error': None,
  }
  result['receipt_sha256'] = digest(canonical(result))
  return result


def validate_raw_lanes(record, mask):
  if (
    type(record) is not dict
    or type(record.get('lanes')) is not list
    or type(record.get('scores')) is not list
    or type(record.get('lane_count')) is not int
    or not 0 <= record['lane_count'] <= 4
    or record['lane_count'] != len(record['lanes'])
    or len(record['lanes']) != len(record['scores'])
  ):
    raise ValueError('RAW_LANE_COUNT_BINDING_MISMATCH')
  for lane, score in zip(record['lanes'], record['scores'], strict=True):
    confidence_bucket(score)
    _validate_lane_points(mask, lane)
  union = [list(p) for p in sorted({tuple(p) for lane in record['lanes'] for p in lane}, key=lambda p: (p[1], p[0]))]
  if union != record['points']:
    raise ValueError('LANE_UNION_MISMATCH')


def promotion_gate(*, metric_correct, deterministic, tail_complete, full_complete, official_reproduced):
  values = (metric_correct, deterministic, tail_complete, full_complete, official_reproduced)
  if any(type(v) is not bool for v in values):
    raise ValueError('EXACT_GATE_BOOLEANS_REQUIRED')
  required = ('METRIC_CORRECTNESS', 'DETERMINISM', 'TAIL_ATTRIBUTION', 'FULL_PUBLIC_EVALUATION', 'OFFICIAL_REPRODUCTION')
  missing = [name for name, ok in zip(required, values, strict=True) if not ok]
  # Even all structural checks do not define the unjustified pixel qualification threshold.
  return {
    'status': 'BLOCKED',
    'missing': missing + ['PUBLIC_PIXEL_QUALIFICATION_THRESHOLD_UNJUSTIFIED'],
    'private_input_allowed': False,
    'reference_promotable': False,
    'qualification': 'INDEPENDENT_REFERENCE_UNAVAILABLE',
  }


def semantic_tail(rgb, points, historical_p95):
  """Attribute retained supported-row samples by the existing public semantic mask.

  This is not a filter: car/occlusion/undrivable samples remain in the original
  distribution. The historical cut is diagnostic, not an acceptance threshold.
  """
  from openpilot.tools.cyber_autotune.lane_marking_metrics import category2_mask, PALETTE

  if type(historical_p95) not in (int, float) or not math.isfinite(historical_p95) or historical_p95 < 0:
    raise ValueError('INVALID_HISTORICAL_DIAGNOSTIC_CUT')
  mask = category2_mask(rgb)
  marking_frame(mask, points)
  _, pp, _ = _direction_samples(mask, points)
  groups = {name: [] for name in ('road', 'lane_marking', 'undrivable', 'movable', 'my_car', 'movable_in_car')}
  names = dict(zip(PALETTE, groups, strict=True))
  for x, y, error in pp:
    color = tuple(int(c) for c in rgb[y, int(math.floor(x + 0.5))])
    groups[names[color]].append(error)
  return {
    name: {'distribution': distribution(values), 'historic_p95_tail_count': sum(v >= historical_p95 for v in values), 'samples': values}
    for name, values in groups.items()
  }
