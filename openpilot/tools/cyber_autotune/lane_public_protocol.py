"""Frozen public representation helpers; no images/logs opened by this module."""

import numpy as np

from openpilot.tools.cyber_autotune.contracts import is_sha256
from openpilot.tools.cyber_autotune.native_protocol import canonical, digest
from openpilot.tools.cyber_autotune.lane_marking_metrics import category2_mask, marking_frame, MAX_PIXELS

METRIC_REQUIRED_FIELDS = {'intrinsics_sha256', 'extrinsics_sha256', 'metric_lane_gt_sha256', 'camera_road_transform_sha256',
                          'timestamp_association_sha256', 'gt_provenance_sha256', 'license_sha256', 'coordinate_conventions_sha256'}


def region_reports(mask, points):
  marking_frame(mask, points)  # Validate before splitting; never silently lose bad points.
  h, _ = mask.shape
  if h < 3:
    raise ValueError('THREE_IMAGE_REGIONS_REQUIRED')
  cuts = (0, h // 3, 2 * h // 3, h)
  return {name: marking_frame(mask[a:b], [[x, y - a] for x, y in points if a <= y < b])
          for name, a, b in zip(('far', 'mid', 'near'), cuts[:-1], cuts[1:], strict=True)}


def category2_regions(rgb, points):
  return region_reports(category2_mask(rgb), points)


def sample_detector_lanes(lanes, *, width, height):
  return sample_detector_lane_diagnostics(lanes, width=width, height=height)['points']


def sample_detector_lane_diagnostics(lanes, *, width, height):
  """Spatial spline sampling only; no missing frame/GT interpolation.

  -2 is Lane's invalid-y sentinel. Finite off-canvas spline samples are counted
  and excluded, following the official x-domain filtering. They do not make
  valid lanes in the same frame unavailable. Nonfinite/malformed lanes reject
  the frame. The original pixel kernel uses the center domain [0, width-1].
  """
  if (type(lanes) is not list or type(width) is not int or type(height) is not int
      or width <= 0 or height <= 0 or width * height > MAX_PIXELS):
    raise ValueError('INVALID_ORIGINAL_IMAGE_GEOMETRY')
  rows = np.arange(height, dtype=np.float64) / height
  points = set()
  outside_y = outside_image = overlapping = 0
  for lane in lanes:
    xs = np.asarray(lane(rows))
    if xs.shape != rows.shape or not np.all(np.isfinite(xs)):
      raise ValueError('UNSUPPORTED_LANE_GEOMETRY')
    for y, x in enumerate(xs):
      if x == -2.:
        outside_y += 1
        continue
      pixel_x = float(x * width)
      if not 0 <= pixel_x <= width - 1:
        outside_image += 1
        continue
      overlapping += (pixel_x, y) in points
      points.add((pixel_x, y))
  return {'points': [[x, y] for x, y in sorted(points, key=lambda point: (point[1], point[0]))],
          'outside_y_support_points': outside_y, 'outside_image_points': outside_image,
          'overlapping_points': overlapping, 'source_points': height * len(lanes)}


def human_holdout_manifest(metadata, *, stride):
  """Pure metadata selection. Caller must pass public gate before private I/O."""
  if type(metadata) is not list or not metadata or len(metadata) > 1000000 or type(stride) is not int or stride <= 0:
    raise ValueError('NONEMPTY_BOUNDED_METADATA_REQUIRED')
  for item in metadata:
    if (type(item) is not dict or set(item) != {'route_sha256', 'segment', 'frame_index', 'frame_sha256'}
        or not is_sha256(item['route_sha256']) or not is_sha256(item['frame_sha256'])
        or any(type(item[k]) is not int or item[k] < 0 for k in ('segment', 'frame_index'))):
      raise ValueError('INDEPENDENT_METADATA_ONLY_NO_DETECTOR_MODEL_INPUTS')
  ordered = sorted(metadata, key=lambda item: (item['route_sha256'], item['segment'], item['frame_index']))
  if len({(i['route_sha256'], i['segment'], i['frame_index']) for i in ordered}) != len(ordered):
    raise ValueError('DUPLICATE_FRAME_IDENTITY')
  result = {'schema': 'HUMAN_HOLDOUT_METADATA_SELECTION_V1', 'status': 'PRIVATE_HUMAN_LABEL_PENDING',
            'metadata_sha256': digest(canonical(ordered)), 'stride': stride, 'selected': ordered[::stride],
            'selection_uses_detector_outputs': False, 'selection_uses_model_outputs': False, 'images_opened': False,
            'labels_generated': False, 'reference_promotable': False}
  result['receipt_sha256'] = digest(canonical(result))
  return result


def metric_dataset_availability(evidence):
  if type(evidence) is not dict or set(evidence) != METRIC_REQUIRED_FIELDS:
    raise ValueError('EXACT_METRIC_DATASET_PROVENANCE_REQUIRED')
  if any(v is not None and not is_sha256(v) for v in evidence.values()):
    raise ValueError('INVALID_METRIC_DATASET_PROVENANCE')
  missing = sorted(k for k, v in evidence.items() if v is None)
  return {'status': 'METRIC_PUBLIC_GT_UNAVAILABLE' if missing else 'METRIC_DATASET_STRUCTURALLY_PRESENT_NOT_QUALIFIED',
          'missing': missing, 'evidence_sha256': digest(canonical(evidence)),
          'meter_evaluation_allowed': False, 'reference_promotable': False}
