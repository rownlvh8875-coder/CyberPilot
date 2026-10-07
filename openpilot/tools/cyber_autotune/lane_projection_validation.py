"""Known-by-construction camera checks, never measured calibration certification."""

import math

import numpy as np

from openpilot.tools.cyber_autotune import lane_projection_diagnostics as p
from openpilot.tools.cyber_autotune.native_protocol import canonical, digest

DISTANCE_BUCKETS_M = (5.0, 10.0, 20.0, 30.0)
PIXEL_STEP = 1e-3
ROTATION_STEP_RAD = 1e-6
HEIGHT_STEP_M = 1e-5


def _rotation(axis, angle):
  direction = np.eye(3)[axis]
  x, y, z = direction
  skew = np.array([[0., -z, y], [z, 0., -x], [-y, x, 0.]])
  return np.eye(3) + np.sin(angle) * skew + (1 - np.cos(angle)) * (skew @ skew)


def distance_validation(intrinsics, camera_to_road, camera_center, distances, lateral):
  if (type(distances) not in (list, tuple) or not distances
      or any(type(d) not in (int, float) or not math.isfinite(d) or d <= 0 for d in distances)
      or type(lateral) not in (int, float) or not math.isfinite(lateral)):
    raise ValueError('KNOWN_POINT_DOMAIN_REQUIRED')
  k, r, c = (np.asarray(value, dtype=float) for value in (intrinsics, camera_to_road, camera_center))
  if k.shape != (3, 3) or r.shape != (3, 3) or c.shape != (3,):
    raise ValueError('CAMERA_GEOMETRY_SHAPE_REQUIRED')
  rows = []
  for distance in distances:
    point = np.array([distance, lateral, 0.])
    camera = r.T @ (point - c)
    image = k @ camera
    if not np.all(np.isfinite(image)) or image[2] <= 0:
      raise ValueError('KNOWN_POINT_NOT_VISIBLE')
    uv = image[:2] / image[2]
    projected = p.ground_projection(k, r, c, uv)  # Validates intrinsics/rotation/ray.
    sensitivities = {}
    for key in ('u_px', 'fx_px', 'pitch_world_y_rad', 'camera_height_m', 'roll_world_x_rad'):
      plus_k, minus_k = k.copy(), k.copy()
      plus_r, minus_r = r.copy(), r.copy()
      plus_c, minus_c = c.copy(), c.copy()
      plus_uv, minus_uv = uv.copy(), uv.copy()
      if key == 'u_px':
        step = PIXEL_STEP
        plus_uv[0] += step
        minus_uv[0] -= step
      elif key == 'fx_px':
        step = PIXEL_STEP
        plus_k[0, 0] += step
        minus_k[0, 0] -= step
      elif key == 'camera_height_m':
        step = HEIGHT_STEP_M
        plus_c[2] += step
        minus_c[2] -= step
      else:
        step = ROTATION_STEP_RAD
        axis = 1 if key == 'pitch_world_y_rad' else 0
        plus_r = _rotation(axis, step) @ r
        minus_r = _rotation(axis, -step) @ r
      central = (p.ground_projection(plus_k, plus_r, plus_c, plus_uv)['lateral_left_m']
                 - p.ground_projection(minus_k, minus_r, minus_c, minus_uv)['lateral_left_m']) / (2 * step)
      sensitivities[key] = {'analytic': projected['jacobian'][key], 'central_difference': central, 'step': step,
                            'absolute_difference': abs(central - projected['jacobian'][key])}
    rows.append({
      'distance_m': distance, 'known_lateral_m': lateral, 'pixel': uv.tolist(),
      'forward_back_error_m': float(np.hypot(projected['forward_m'] - distance, projected['lateral_left_m'] - lateral)),
      'sensitivities': sensitivities, 'maximum_jacobian_difference': max(v['absolute_difference'] for v in sensitivities.values()),
      'symbolic_first_order_error_m': 'sum(abs(J_i(distance))*independently_measured_bound_i) + certified_projection_remainder',
    })
  report = {
    'schema': 'KNOWN_CAMERA_GEOMETRY_JACOBIAN_CHECK_V1',
    'scope': 'KNOWN_BY_CONSTRUCTION_GEOMETRY_NOT_MEASURED_CALIBRATION',
    'intrinsics': k.tolist(), 'camera_to_road': r.tolist(), 'camera_center': c.tolist(), 'rows': rows,
    'total_conservative_uncertainty_m': None, 'calibration_measured': False, 'reference_promotable': False,
  }
  report['receipt_sha256'] = digest(canonical(report))
  return report


def calibration_blockers():
  return {
    'CAMERA_INTRINSICS_AVAILABLE': {
      'status': 'NOMINAL_ONLY',
      'effect': 'Sensor-dependent nominal focal/principal point; actual sensor and per-unit uncertainty unverified.'},
    'CAMERA_EXTRINSICS_MODEL_DERIVED': {
      'status': 'BLOCKED',
      'effect': 'cameraOdometry/live calibration depends on driving model; cannot certify independent pose.'},
    'CAMERA_HEIGHT_UNVERIFIED': {
      'status': 'BLOCKED',
      'effect': 'Ground scale and lateral scale depend on measured camera height; default 1.22m is not a survey.'},
    'CAMERA_MOUNT_PITCH_UNVERIFIED': {
      'status': 'BLOCKED',
      'effect': 'Near-horizon range/lateral sensitivity grows with pitch error; independent stationary target pose missing.'},
    'CAMERA_MOUNT_ROLL_YAW_UNVERIFIED': {
      'status': 'BLOCKED',
      'effect': 'Cross-axis errors affect boundary position; model roll=0 is not a measurement.'},
    'ROAD_PLANE_ASSUMPTION_UNVERIFIED': {
      'status': 'BLOCKED',
      'effect': 'Grade/camber/nonplanarity creates projection error not bounded by nominal Jacobian.'},
    'DISTORTION_UNCERTAINTY_UNVERIFIED': {
      'status': 'BLOCKED',
      'effect': 'Nominal pinhole projection omits audited per-sensor distortion and its uncertainty.'},
    'CALIBRATION_MEASUREMENT_PENDING': {
      'status': 'BLOCKED',
      'effect': 'Independent stationary measurements and uncertainty review require physical observations.'},
  }
