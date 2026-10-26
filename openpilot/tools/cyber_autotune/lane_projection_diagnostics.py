"""Nominal flat-ground ray/Jacobian diagnostics; no calibrated reference producer.

Camera optical axes are x-right/y-down/z-forward. R maps optical rays into a
road frame x-forward/y-left/z-up; C is camera center in that frame. Rotation
derivatives are infinitesimal left perturbations about world axes, in radians.
No distortion correction or geometric certification is implicitly supplied.
"""

import math
import numpy as np

ROTATION_NUMERIC_TOLERANCE = 1e-9
HORIZON_NUMERIC_TOLERANCE = 1e-12
JACOBIAN_KEYS = frozenset(
  ('u_px', 'v_px', 'fx_px', 'fy_px', 'cx_px', 'cy_px', 'camera_height_m', 'camera_lateral_m', 'roll_world_x_rad', 'pitch_world_y_rad', 'yaw_world_z_rad')
)


def _array(value, shape):
  a = np.asarray(value)
  if a.shape != shape or a.dtype.kind not in 'fi' or not np.all(np.isfinite(a)):
    raise ValueError('INVALID_FINITE_GEOMETRY')
  return a.astype(float)


def ground_projection(k, rotation, center, pixel) -> dict:
  k, r, c, uv = _array(k, (3, 3)), _array(rotation, (3, 3)), _array(center, (3,)), _array(pixel, (2,))
  if (
    k[0, 0] <= 0
    or k[1, 1] <= 0
    or not np.array_equal(k[2], [0, 0, 1])
    or k[0, 1] != 0
    or k[1, 0] != 0
    or k[0, 2] < 0
    or k[1, 2] < 0
    or not np.allclose(r @ r.T, np.eye(3), atol=ROTATION_NUMERIC_TOLERANCE, rtol=0)
    or abs(np.linalg.det(r) - 1) > ROTATION_NUMERIC_TOLERANCE
    or c[2] <= 0
  ):
    raise ValueError('INVALID_PINHOLE_OR_ROTATION')
  fx, fy, cx, cy = k[0, 0], k[1, 1], k[0, 2], k[1, 2]
  ray = r @ np.array([(uv[0] - cx) / fx, (uv[1] - cy) / fy, 1.0])
  if ray[2] >= -HORIZON_NUMERIC_TOLERANCE:
    raise ValueError('HORIZON_OR_BEHIND_CAMERA_GROUND_INTERSECTION')
  scale = -c[2] / ray[2]
  point = c + scale * ray
  if point[0] <= 0 or not np.all(np.isfinite(point)):
    raise ValueError('NON_FORWARD_GROUND_INTERSECTION')

  def dy(dr):
    return float(-c[2] * (dr[1] * ray[2] - ray[1] * dr[2]) / ray[2] ** 2)

  jac = {
    'u_px': dy(r[:, 0] / fx),
    'v_px': dy(r[:, 1] / fy),
    'fx_px': dy(-r[:, 0] * (uv[0] - cx) / fx**2),
    'fy_px': dy(-r[:, 1] * (uv[1] - cy) / fy**2),
    'cx_px': dy(-r[:, 0] / fx),
    'cy_px': dy(-r[:, 1] / fy),
    'camera_height_m': float(-ray[1] / ray[2]),
    'camera_lateral_m': 1.0,
    'roll_world_x_rad': dy(np.cross([1.0, 0, 0], ray)),
    'pitch_world_y_rad': dy(np.cross([0.0, 1, 0], ray)),
    'yaw_world_z_rad': dy(np.cross([0.0, 0, 1], ray)),
  }
  if not all(math.isfinite(v) for v in jac.values()):
    raise ValueError('NONFINITE_PROJECTION_JACOBIAN')
  return {
    'scope': 'DIAGNOSTIC_GEOMETRY_ONLY_NOT_REFERENCE',
    'forward_m': float(point[0]),
    'lateral_left_m': float(point[1]),
    'jacobian': jac,
    'reference_promotable': False,
  }


def first_order_budget(jacobian: dict, bounds: dict | None) -> dict:
  """First-order L1 contributions, never a conservative uncertainty certificate.

  The nonlinear/distortion/ground-plane remainder is unknown, so total conservative
  uncertainty stays null even when caller supplies every local perturbation bound.
  """
  if type(jacobian) is not dict or set(jacobian) != JACOBIAN_KEYS or not all(type(v) in (int, float) and math.isfinite(v) for v in jacobian.values()):
    raise ValueError('FINITE_JACOBIAN_REQUIRED')
  detector = calibration = None
  if bounds is not None:
    if type(bounds) is not dict or set(bounds) != set(jacobian) or not all(type(v) in (int, float) and math.isfinite(v) and v >= 0 for v in bounds.values()):
      raise ValueError('EXACT_NONNEGATIVE_UNCERTAINTY_BOUNDS_REQUIRED')
    terms = {name: abs(jacobian[name]) * bounds[name] for name in bounds}
    detector = sum(terms[name] for name in ('u_px', 'v_px'))
    calibration = sum(value for name, value in terms.items() if name not in ('u_px', 'v_px'))
    if not math.isfinite(detector + calibration):
      raise ValueError('NONFINITE_UNCERTAINTY_CONTRIBUTION')
  return {
    'status': 'BLOCKED',
    'scope': 'FIRST_ORDER_CONTRIBUTIONS_NOT_CONSERVATIVE_CERTIFICATION',
    'detector_error_m': detector,
    'calibration_error_m': calibration,
    'projection_error_m': None,
    'total_conservative_uncertainty_m': None,
    'blocker': 'PROJECTION_REMAINDER_UNVALIDATED' if bounds is not None else 'UNCERTAINTY_BOUNDS_UNAVAILABLE',
    'reference_promotable': False,
  }


def nominal_sensitivity(focal_px: float, distances_m: tuple) -> dict:
  if (
    type(focal_px) not in (float, int)
    or not math.isfinite(focal_px)
    or focal_px <= 0
    or type(distances_m) is not tuple
    or not distances_m
    or any(type(v) not in (int, float) or not math.isfinite(v) or v <= 0 for v in distances_m)
  ):
    raise ValueError('POSITIVE_NOMINAL_FOCAL_AND_DISTANCES_REQUIRED')
  rows = [{'forward_distance_m': x, 'absolute_lateral_sensitivity_m_per_px': x / focal_px} for x in distances_m]
  if any(not math.isfinite(row['absolute_lateral_sensitivity_m_per_px']) for row in rows):
    raise ValueError('NONFINITE_NOMINAL_SENSITIVITY')
  return {'scope': 'ALIGNED_PINHOLE_SENSITIVITY_NOT_MEASURED_ERROR', 'rows': rows, 'measured_meter_error': None, 'reference_promotable': False}
