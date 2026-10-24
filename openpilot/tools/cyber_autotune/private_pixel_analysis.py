"""Prediction behavior and hypothetical projection, never private GT error."""
from collections import Counter
from pathlib import Path

import numpy as np
from openpilot.common.transformations.camera import DEVICE_CAMERAS
from openpilot.tools.cyber_autotune import approximate_geometry_diagnostic as geometry
from openpilot.tools.cyber_autotune import coarse_camera_height_diagnostic as coarse
from openpilot.tools.cyber_autotune import camera_calibration_evidence as calibration
from openpilot.tools.cyber_autotune import private_pixel_execution as execution
from openpilot.tools.cyber_autotune.native_protocol import digest
from openpilot.tools.cyber_autotune.lane_tail_report import seal, unseal


def projection_policy():
  if digest((calibration.ROOT / calibration.CAMERA_SOURCE).read_bytes()) != calibration.CAMERA_SHA:
    raise ValueError('PINNED_STATIC_SOURCE_REQUIRED')
  return seal({
    'schema': 'PRIVATE_HYPOTHETICAL_PROJECTION_POLICY_V1', 'source_sha256': digest(Path(__file__).read_bytes()),
    'coarse_prior_sha256': coarse.height_prior()['receipt_sha256'], 'orientation_prior_sha256': geometry.prior()['receipt_sha256'],
    'heights_m': [1.33, 1.35, 1.375, 1.4, 1.425, 1.45, 1.47], 'nominal_height_m': 1.4,
    'height_role': 'USER_APPROVED_COARSE_DIAGNOSTIC_SENSITIVITY_NOT_PHYSICAL_UNCERTAINTY',
    'sensor_hypotheses': ['ar0231', 'os04c10'], 'actual_sensor_identified': False,
    'static_source_sha256': calibration.CAMERA_SHA, 'distortion': 'UNKNOWN_NOT_ASSUMED_ZERO',
    'image_mapping': 'HYPOTHETICAL_FULL_SENSOR_IMAGE_LINEAR_RESIZE_NO_CROP_NOT_OBSERVED_MAPPING',
    'assumptions': ['UNDISTORTED_PINHOLE_PROBE_ONLY', 'FLAT_GROUND_NOT_SURVEYED', 'CALIB_ALIGNED_ASSUMED_ROAD'],
    'qualified_pixel_to_meter_conversion': False,
    'forward_reporting_domain_m': [5., 30.], 'distance_bucket_edges_m': [5., 7.5, 15., 25., 30.],
    'distance_bucket_centers_m': [5., 10., 20., 30.], **execution.FIREWALL,
  })


def projection_sensitivity(records, policy):
  unseal(policy)
  if policy != projection_policy():
    raise ValueError('EXACT_FROZEN_PROJECTION_HYPOTHESES_REQUIRED')
  prior = geometry.prior()
  rotation = geometry.rotation(prior['orientation']['converted_rad'])
  hypotheses = []
  for sensor in policy['sensor_hypotheses']:
    camera = DEVICE_CAMERAS[('mici', sensor)].narrow_road
    points = []
    invalid, outside = 0, 0
    for record in records:
      h, w = record['image_geometry']
      for x, y in record['points']:
        u = (x / w * camera.width - camera.intrinsics[0, 2]) / camera.intrinsics[0, 0]
        v = (y / h * camera.height - camera.intrinsics[1, 2]) / camera.intrinsics[1, 1]
        ray = rotation @ [u, v, 1.]
        if ray[2] >= -1e-9:
          invalid += 1
          continue
        forward, lateral = -1.4 * ray[:2] / ray[2]
        if not 5 <= forward <= 30:
          outside += 1
          continue
        points.append([float(forward), float(lateral)])
    buckets = []
    for index, center in enumerate(policy['distance_bucket_centers_m']):
      lo, hi = policy['distance_bucket_edges_m'][index:index + 2]
      group = [point for point in points if lo <= point[0] < hi or (index == 3 and point[0] == hi)]
      envelopes = [{
        'height_m': height,
        'forward_m': execution.distribution([p[0] * height / 1.4 for p in group]),
        'lateral_left_m': execution.distribution([p[1] * height / 1.4 for p in group]),
      } for height in policy['heights_m']]
      buckets.append({'nominal_distance_bucket_m': center, 'nominal_point_count': len(group),
                      'sampled_height_sensitivity': envelopes})
    hypotheses.append({
      'sensor_hypothesis': sensor, 'projected_points_in_reporting_domain': len(points),
      'horizon_or_upward_unavailable_points': invalid, 'outside_declared_domain_points': outside,
      'forward_height_ratio_min': .95, 'forward_height_ratio_max': 1.05,
      'nominal_forward_m': execution.distribution([p[0] for p in points]),
      'nominal_lateral_left_m': execution.distribution([p[1] for p in points]),
      'height_extreme_forward_span_m': execution.distribution([p[0] * .1 for p in points]),
      'height_extreme_lateral_span_m': execution.distribution([abs(p[1]) * .1 for p in points]),
      'distance_buckets': buckets, **execution.FIREWALL,
    })
  return seal({
    'schema': 'APPROX_PROJECTED_GEOMETRY_DIAGNOSTIC_V1',
    'label': 'APPROXIMATE / NON-QUALIFYING / SENSOR_AND_IMAGE_MAPPING_UNVERIFIED',
    'projection_policy_sha256': policy['receipt_sha256'], 'hypotheses': hypotheses,
    'physical_height': 'NOT_MEASURED', 'metric_calibration': 'UNAVAILABLE',
    'range_semantics': 'SAMPLED_SENSITIVITY_NOT_UNCERTAINTY_OR_TRUTH', **execution.FIREWALL,
  })


def comparable_behavior(records):
  counts, confidence, frame_confidence, x_means, y_means, extents = [], [], [], [], [], []
  empty = 0
  for record in records:
    counts.append(record['lane_count'])
    h, w = record['image_geometry']
    scores = [lane['confidence'] for lane in record['lanes'] if lane['confidence'] is not None]
    confidence.extend(scores)
    if scores:
      frame_confidence.append(float(np.mean(scores)))
    if not record['points']:
      empty += 1
    else:
      x_means.append(float(np.mean([x / w for x, _ in record['points']])))
      y_means.append(float(np.mean([y / h for _, y in record['points']])))
    for lane in record['lanes']:
      if lane['points']:
        extents.append((max(y for _, y in lane['points']) - min(y for _, y in lane['points'])) / h)
  return {
    'frames': len(counts), 'no_output_count': empty, 'no_output_rate': empty / len(counts) if counts else None,
    'lane_count_distribution': dict(sorted(Counter(counts).items())),
    'per_lane_confidence': execution.distribution(confidence),
    'per_frame_mean_confidence': execution.distribution(frame_confidence),
    'per_frame_normalized_centroid_x': execution.distribution(x_means),
    'per_frame_normalized_centroid_y': execution.distribution(y_means),
    'per_lane_normalized_vertical_extent': execution.distribution(extents),
    'geometry_semantics': 'PREDICTION_ONLY_IMAGE_WIDTH_HEIGHT_FRACTIONS_NOT_TRUTH_ERROR',
  }
