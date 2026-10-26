"""Pure pixel lane-marking diagnostics, without ego association or truth claims.

Inputs are explicit row samples in the original mask geometry. No polyline
interpolation, temporal carry, confidence filtering, or model fallback occurs.
A run midpoint is a representation convention, not an annotated ego center.
Distributions describe only supported pairs; missing support is counted separately.
"""

import math
import numpy as np

from openpilot.tools.cyber_autotune.native_protocol import canonical, digest
from openpilot.tools.cyber_autotune.contracts import is_sha256

MAX_PIXELS = 3000 * 2000  # Covers audited public geometries; resource cap, not qualification.
MAX_POINTS = MAX_PIXELS
PALETTE = ((64, 32, 32), (255, 0, 0), (128, 128, 96), (0, 255, 102), (204, 0, 255), (0, 204, 255))


def category2_mask(rgb: np.ndarray) -> np.ndarray:
  if not isinstance(rgb, np.ndarray) or rgb.dtype != np.uint8 or rgb.ndim != 3 or rgb.shape[2] != 3 or not 0 < rgb.shape[0] * rgb.shape[1] <= MAX_PIXELS:
    raise ValueError('INVALID_CATEGORY2_MASK_GEOMETRY')
  allowed = np.zeros(rgb.shape[:2], dtype=bool)
  for color in PALETTE:
    allowed |= np.all(rgb == color, axis=2)
  if not np.all(allowed):
    raise ValueError('UNKNOWN_MASK_COLORS_NO_CANONICALIZATION')
  return np.all(rgb == (255, 0, 0), axis=2)


def _distribution(values):
  return {
    'sample_count': len(values),
    'median': float(np.median(values)) if values else None,
    'p95': float(np.quantile(values, 0.95, method='linear')) if values else None,
    'maximum': max(values) if values else None,
  }


def marking_frame(mask: np.ndarray, points: list) -> dict:
  if (
    not isinstance(mask, np.ndarray)
    or mask.dtype != np.bool_
    or mask.ndim != 2
    or not 0 < mask.size <= MAX_PIXELS
    or type(points) is not list
    or len(points) > MAX_POINTS
  ):
    raise ValueError('INVALID_PIXEL_METRIC_INPUT')
  h, w = mask.shape
  by_row = {}
  seen = set()
  for item in points:
    if (
      type(item) not in (tuple, list)
      or len(item) != 2
      or type(item[0]) not in (int, float)
      or not math.isfinite(item[0])
      or type(item[1]) is not int
      or not 0 <= item[0] <= w - 1
      or not 0 <= item[1] < h
    ):
      raise ValueError('INVALID_ORIGINAL_PIXEL_POINT')
    x, y = item
    if (x, y) in seen:
      raise ValueError('DUPLICATE_PIXEL_POINT')
    seen.add((x, y))
    by_row.setdefault(y, []).append(float(x))
  pred_errors, gt_errors = [], []
  gt_runs = covered = unavailable = unsupported = off_marking = 0
  for y in range(h):
    transitions = np.diff(np.r_[False, mask[y], False].astype(np.int8))
    runs = list(zip(np.where(transitions == 1)[0], np.where(transitions == -1)[0], strict=True))
    centers = [(int(a) + int(b) - 1) / 2 for a, b in runs]
    predicted = by_row.get(y, [])
    gt_runs += len(runs)
    for (a, b), center in zip(runs, centers, strict=True):
      if predicted:
        gt_errors.append(min(abs(x - center) for x in predicted))
      else:
        unavailable += 1
      # Pixel-cell support spans half a pixel around each integer mask center.
      covered += any(a - 0.5 <= x < b - 0.5 for x in predicted)
    for x in predicted:
      if centers:
        pred_errors.append(min(abs(x - center) for center in centers))
      else:
        unsupported += 1
      off_marking += not any(a - 0.5 <= x < b - 0.5 for a, b in runs)
  report = {
    'scope': 'LANE_MARKING_PIXEL_DIAGNOSTIC_NOT_QUALIFICATION',
    'status': 'PIXEL_DIAGNOSTIC' if gt_errors and pred_errors else 'REFERENCE_UNAVAILABLE',
    'unit': 'px',
    'geometry': [h, w],
    'gt_runs': gt_runs,
    'pred_points': len(points),
    'covered_gt_runs': covered,
    'coverage': covered / gt_runs if gt_runs else None,
    'unavailable_gt_runs': unavailable,
    'unsupported_pred_points': unsupported,
    'off_marking_pred_points': off_marking,
    'false_positive_support_rate': off_marking / len(points) if points else None,
    'pred_errors_px': pred_errors,
    'gt_errors_px': gt_errors,
    'pred_to_gt': _distribution(pred_errors),
    'gt_to_pred': _distribution(gt_errors),
    'ego_lane_association_evaluated': False,
    'meter_error': None,
    'reference_promotable': False,
    'input_mask_sha256': digest(mask.tobytes()),
    'input_points_sha256': digest(canonical(points)),
  }
  report['receipt_sha256'] = digest(canonical(report))
  return report


def aggregate(reports: list) -> dict:
  if type(reports) is not list or not reports:
    raise ValueError('NONEMPTY_PIXEL_REPORTS_REQUIRED')
  for report in reports:
    _validate_report(report)
  runs = sum(r['gt_runs'] for r in reports)
  result = {
    'scope': 'PIXEL_AGGREGATE_NOT_QUALIFICATION',
    'unit': 'px',
    'frame_count': len(reports),
    'unavailable_frame_rate': sum(r['status'] == 'REFERENCE_UNAVAILABLE' for r in reports) / len(reports),
    'coverage': sum(r['covered_gt_runs'] for r in reports) / runs if runs else None,
    'gt_runs': runs,
    'unavailable_gt_runs': sum(r['unavailable_gt_runs'] for r in reports),
    'pred_to_gt': _distribution([v for r in reports for v in r['pred_errors_px']]),
    'gt_to_pred': _distribution([v for r in reports for v in r['gt_errors_px']]),
    'source_receipts': [r['receipt_sha256'] for r in reports],
    'ego_lane_association_evaluated': False,
    'meter_error': None,
    'reference_promotable': False,
  }
  result['receipt_sha256'] = digest(canonical(result))
  return result


def _validate_report(report):
  # Necessary structural consistency only, not authentication of pixels/inference.
  keys = {
    'scope',
    'status',
    'unit',
    'geometry',
    'gt_runs',
    'pred_points',
    'covered_gt_runs',
    'coverage',
    'unavailable_gt_runs',
    'unsupported_pred_points',
    'off_marking_pred_points',
    'false_positive_support_rate',
    'pred_errors_px',
    'gt_errors_px',
    'pred_to_gt',
    'gt_to_pred',
    'ego_lane_association_evaluated',
    'meter_error',
    'reference_promotable',
    'input_mask_sha256',
    'input_points_sha256',
    'receipt_sha256',
  }
  if (
    type(report) is not dict
    or set(report) != keys
    or report['receipt_sha256'] != digest(canonical({k: v for k, v in report.items() if k != 'receipt_sha256'}))
    or report['scope'] != 'LANE_MARKING_PIXEL_DIAGNOSTIC_NOT_QUALIFICATION'
    or report['unit'] != 'px'
    or report['reference_promotable'] is not False
    or report['ego_lane_association_evaluated'] is not False
    or report['meter_error'] is not None
  ):
    raise ValueError('PIXEL_REPORT_BINDING_MISMATCH')
  geometry = report['geometry']
  counts = ('gt_runs', 'pred_points', 'covered_gt_runs', 'unavailable_gt_runs', 'unsupported_pred_points', 'off_marking_pred_points')
  if (
    type(geometry) is not list
    or len(geometry) != 2
    or any(type(n) is not int or n <= 0 for n in geometry)
    or geometry[0] * geometry[1] > MAX_PIXELS
    or any(type(report[k]) is not int or not 0 <= report[k] <= MAX_POINTS for k in counts)
    or not is_sha256(report['input_mask_sha256'])
    or not is_sha256(report['input_points_sha256'])
  ):
    raise ValueError('INVALID_PIXEL_REPORT_DOMAIN')
  g, n = report['gt_runs'], report['pred_points']
  if (
    report['covered_gt_runs'] > g
    or report['unavailable_gt_runs'] > g
    or report['unsupported_pred_points'] > n
    or report['off_marking_pred_points'] > n
    or report['coverage'] != (report['covered_gt_runs'] / g if g else None)
    or report['false_positive_support_rate'] != (report['off_marking_pred_points'] / n if n else None)
  ):
    raise ValueError('INVALID_PIXEL_COVERAGE_DENOMINATOR')
  for prefix, expected in (('pred', n - report['unsupported_pred_points']), ('gt', g - report['unavailable_gt_runs'])):
    values = report[prefix + '_errors_px']
    if (
      type(values) is not list
      or len(values) != expected
      or any(type(v) not in (int, float) or not math.isfinite(v) or not 0 <= v < geometry[1] for v in values)
      or report[prefix + '_to_' + ('gt' if prefix == 'pred' else 'pred')] != _distribution(values)
    ):
      raise ValueError('INVALID_PIXEL_DISTANCE_DISTRIBUTION')
  expected_status = 'PIXEL_DIAGNOSTIC' if report['pred_errors_px'] and report['gt_errors_px'] else 'REFERENCE_UNAVAILABLE'
  if report['status'] != expected_status:
    raise ValueError('INVALID_PIXEL_DIAGNOSTIC_STATE')
