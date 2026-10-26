"""Conditional pinhole arithmetic, deliberately separate from metric admission.

No image/log/inference/controller I/O. Historical grids are loaded, not regenerated.
Full native rectangle and identity orientation are ASSUMPTIONS for every mapping.
"""

import json
from pathlib import Path

import numpy as np

from openpilot.tools.cyber_autotune import approximate_geometry_diagnostic as a
from openpilot.tools.cyber_autotune import camera_calibration_evidence as c
from openpilot.tools.cyber_autotune import qcamera_pixel_registration as q
from openpilot.tools.cyber_autotune.lane_tail_report import unseal

DISTANCES = (5, 10, 15, 20, 25, 30)  # User-declared fixed query domain, not observed distances.
BIN_EDGES = (0.0, 7.5, 12.5, 17.5, 22.5, 27.5, 32.5)
K_NATIVE = a.camera.DEVICE_CAMERAS[('mici', 'os04c10')].narrow_road.intrinsics.copy()
POLICY_RECEIPT = '35ada2dfa0822088ce455a09cb54e715d23916256d8875d398594d26adff6c9a'
HEIGHT_RECEIPT = 'bc6eada2f78d371aaacc34b4c0ce86f46c89056a0574e3f981f32b9807fe7802'
OPEN_TERMS = (
  'DISTORTION_CONTRIBUTION_UNBOUNDED_OR_PENDING',
  'HARDWARE_CROP_AND_PHASE_UNVALIDATED',
  'MAPPING_HYPOTHESES_NOT_EXHAUSTIVE',
  'PHYSICAL_POSE_AND_HEIGHT_UNCERTAINTY_PENDING',
  'GROUND_GRADE_CAMBER_NONPLANARITY_UNBOUNDED',
  'STATIC_INTRINSICS_APPLICABILITY_PENDING',
  'ASSISTED_ANNOTATION_UNCERTAINTY_UNQUANTIFIED',
  'MAPPING_RESIDUAL_BOUND_PENDING',
)
FIREWALL = {**q.FLAGS, 'modelv2_usage': False, 'candidate_usage': False, 'detector_retuned': False}
ROOT = c.ROOT / 'docs/cyberpilot/changes'
EXECUTED_SOURCE_SHA = q.digest(Path(__file__).read_bytes())


def frozen(name, receipt):
  x = json.loads((ROOT / name).read_bytes())
  unseal(x)
  if x['receipt_sha256'] != receipt:
    raise ValueError('HISTORICAL_INPUT_IDENTITY_CHANGED')
  return x


def output(fields):
  return c.seal(
    {
      **fields,
      **FIREWALL,
      'hypotheses_exhaustive': False,
      'total_physical_bound_m': None,
      'independent_meter_result': None,
      'actual_forward_mapping': None,
      'actual_qcamera_intrinsics': None,
      'pixel_mapping_bound_native_px': None,
      'distortion_contribution_m': None,
      'sealed_reference': 'NOT_GENERATED',
    }
  )


def policy():
  if q.digest(Path(__file__).read_bytes()) != EXECUTED_SOURCE_SHA:
    raise ValueError('RUNNING_METER_MATH_SOURCE_CHANGED')
  old = frozen('coarse-height-sensitivity-policy-v1.json', POLICY_RECEIPT)
  height = frozen('physical-height-observation-v1.json', HEIGHT_RECEIPT)
  a.identity()
  q.audit()  # Enforces existing source/static-camera and detector/annotation source binding.
  return output(
    {
      'schema': 'DECLARED_METER_DIAGNOSTIC_POLICY_V1',
      'historical_policy_sha256': POLICY_RECEIPT,
      'height_observation_sha256': HEIGHT_RECEIPT,
      'height_grid_m': old['heights_m'],
      'pitches_deg': old['pitches_deg'],
      'rolls_deg': old['rolls_deg'],
      'yaws_deg': old['yaws_deg'],
      'original_distances_m': old['distances_m'],
      'original_matrix_rows': old['matrix_rows'],
      'original_orientation_rows': old['orientation_1d_rows'],
      'physical_observation_height_m': height['value_m'],
      'measurement_uncertainty': None,
      'height_range_role': 'HISTORICAL_DIAGNOSTIC_HEIGHT_SENSITIVITY_RANGE',
      'orientation_role': 'MODEL_DERIVED_EXTRINSICS_PRIOR_PLUS_DIAGNOSTIC_SENSITIVITY_PROBES',
      'distances_m': list(DISTANCES),
      'distance_bin_edges_m': list(BIN_EDGES),
      'domain_m': [5, 30],
      'bin_assignment': 'HUMAN_FORWARD_DISTANCE_HALF_OPEN_LAST_INCLUSIVE;DOMAIN_5_TO_30',
      'fixed_query': 'PHYSICAL_MEAN_HEIGHT_NOMINAL_POSE_CENTER_RAYS_FIXED_ACROSS_SCENARIOS',
      'fixed_residual': 'ABSOLUTE_X_MAGNITUDE_BOTH_SIGNS_MAX_PINHOLE_CONDITIONAL',
      'mapping_rules': list(q.RULES),
      'assumed_crop': [0, 0, 1344, 760],
      'assumed_orientation': 'IDENTITY',
      'intrinsics_role': 'STATIC_INTRINSICS_PRIOR',
      'intrinsics_candidate': 'OS04C10_MICi_VISIONIPC_SOURCE_PRIOR',
      'native_k': K_NATIVE.tolist(),
      'static_source_sha256': c.CAMERA_SHA,
      'road_axes': 'X_FORWARD_Y_LEFT_Z_UP_ASSUMED_FLAT',
      'origin': 'CAMERA_VERTICAL_FOOTPOINT_X_ZERO_NOT_SURVEYED_VEHICLE_DATUM',
      'bound_scope': 'CONSERVATIVE_ACROSS_DECLARED_SAMPLED_HYPOTHESES_ONLY',
      'continuous_bound': False,
      'open_terms': list(OPEN_TERMS),
      'qualification_threshold': None,
    }
  )


def nominal():
  return {'height_m': 1.385, 'rpy_deg': [0.0, 2.34, 0.2], 'role': 'PHYSICAL_HEIGHT_OBSERVATION_UNCERTAINTY_PENDING_MODEL_POSE'}


def scenarios():
  p = policy()
  old_pose = [0.0, 2.34, 0.2]
  cells = [{'height_m': h, 'rpy_deg': [0.0, pitch, 0.2], 'role': 'HISTORICAL_HEIGHT_PITCH_PROBE'} for h in p['height_grid_m'] for pitch in p['pitches_deg']]
  for axis, index in (('rolls_deg', 0), ('yaws_deg', 2)):
    for v in p[axis]:
      pose = list(old_pose)
      pose[index] = v
      if not any(s['height_m'] == 1.4 and s['rpy_deg'] == pose for s in cells):
        cells.append({'height_m': 1.4, 'rpy_deg': pose, 'role': 'HISTORICAL_ROLL_YAW_PROBE'})
  cells.append(nominal())
  for i, s in enumerate(cells):
    s['scenario_id'] = f'S{i:02d}'
  return cells


def transforms():
  return {rule: {'affine': (af := q.affine([1344, 760], [526, 330], [0, 0, 1344, 760], rule)), 'kq': q.intrinsics(K_NATIVE.tolist(), af)} for rule in q.RULES}


def _points(values, columns):
  if any(type(v) is bool or isinstance(v, np.bool_) for row in values for v in row):
    raise ValueError("BOOLEAN_PIXEL_COORDINATE")
  x = np.asarray(values)
  if x.size == 0:
    return np.empty((0, columns), dtype=float)
  if x.ndim != 2 or x.shape[1] != columns or x.dtype.kind not in 'fi' or not np.isfinite(x).all():
    raise ValueError('FINITE_NUMERIC_PIXEL_POINTS_REQUIRED')
  x = x.astype(float)
  for start in range(0, columns, 2):
    if np.any(x[:, start] < 0) or np.any(x[:, start] >= 526) or np.any(x[:, start + 1] < 0) or np.any(x[:, start + 1] >= 330):
      raise ValueError('ORIGINAL_QCAMERA_POINTS_OUTSIDE_IMAGE')
  return x


def _geometry(scenario, rule):
  if rule not in q.RULES:
    raise ValueError('EXPLICIT_DECLARED_MAPPING_REQUIRED')
  h = c.number(scenario['height_m'], positive=True)
  if h > 10:
    raise ValueError('DIAGNOSTIC_HEIGHT_RESOURCE_DOMAIN')
  r = a.rotation(a.degrees(scenario['rpy_deg']))
  k = np.array(transforms()[rule]['kq']['matrix'])
  return h, r, k


def _project(x, h, r, k):
  rays = np.c_[(x[:, 0] - k[0, 2]) / k[0, 0], (x[:, 1] - k[1, 2]) / k[1, 1], np.ones(len(x))] @ r.T
  down = rays[:, 2] < -1e-12
  scale = np.full(len(x), np.nan)
  np.divide(-h, rays[:, 2], out=scale, where=down)
  forward, lateral = rays[:, 0] * scale, rays[:, 1] * scale
  valid = down & (forward > 0) & np.isfinite(forward) & np.isfinite(lateral)
  return np.where(valid, forward, np.nan), np.where(valid, lateral, np.nan), valid


def project(points, scenario, rule):
  x = _points(points, 2)
  f, l, valid = _project(x, *_geometry(scenario, rule))
  return f, l, np.where(valid, 'VALID', 'NONFORWARD_OR_HORIZON')


def fixed_query(distance, rule):
  if distance not in DISTANCES:
    raise ValueError('DECLARED_FIXED_DISTANCE_REQUIRED')
  h, r, k = _geometry(nominal(), rule)
  ray = r.T @ np.array([distance, 0.0, -h])
  if ray[2] <= 0:
    raise ValueError('QUERY_BEHIND_CAMERA')
  return np.array([k[0, 0] * ray[0] / ray[2] + k[0, 2], k[1, 1] * ray[1] / ray[2] + k[1, 2]])


def project_pairs(pairs, scenario, rule):
  x = _points(pairs, 4)
  geometry = _geometry(scenario, rule)
  hf, hl, hv = _project(x[:, :2], *geometry)
  df, dl, dv = _project(x[:, 2:], *geometry)
  valid = hv & dv
  return {'human_forward_m': hf, 'detector_forward_m': df, 'lateral_residual_m': np.where(valid, np.abs(hl - dl), np.nan), 'valid': valid}


def distance_bins(forward):
  f = np.asarray(forward, dtype=float)
  out = np.searchsorted(BIN_EDGES, f, side='right') - 1
  return np.where(np.isfinite(f) & (f >= 5) & (f <= 30), out, -1)


def distribution(values):
  x = np.asarray(values, dtype=float)
  if x.ndim != 1 or not np.isfinite(x).all() or np.any(x < 0):
    raise ValueError('FINITE_NONNEGATIVE_RESIDUALS_REQUIRED')
  return {
    'count': len(x),
    **{key: float(np.quantile(x, v, method='linear')) if len(x) else None for key, v in (('median', 0.5), ('p90', 0.9), ('p95', 0.95), ('maximum', 1.0))},
  }


def analytic(residuals_px, distance, scenario, rule):
  errors = np.asarray(residuals_px, dtype=float)
  distribution(errors)
  uv = fixed_query(distance, rule)
  # Queries are synthetic continuous pinhole coordinates, not observed annotations.
  h, r, k = _geometry(scenario, rule)
  base = np.array([uv])
  ff, ll, ok = _project(base, h, r, k)
  values = []
  valid = np.full(len(errors), bool(ok[0]))
  for sign in (-1, 1):
    moved = np.c_[uv[0] + sign * errors, np.full(len(errors), uv[1])]
    _, l, good = _project(moved, h, r, k)
    valid &= good
    values.append(np.abs(l - ll[0]))
  result = np.maximum(*values)[valid]
  return {
    'distance_query_m': distance,
    'projected_query_forward_m': float(ff[0]) if ok[0] else None,
    'total_residual_samples': len(errors),
    'valid_samples': int(valid.sum()),
    'unavailable_samples': int((~valid).sum()),
    'lateral_m': distribution(result),
    'synthetic_query_outside_image': not (0 <= uv[0] < 526 and 0 <= uv[1] < 330),
    'residual_semantics': 'ABSOLUTE_X_MAGNITUDE_BOTH_SIGNS_MAX_PINHOLE_CONDITIONAL',
  }


def summarize(projected):
  valid = projected['valid']
  bins = distance_bins(projected['human_forward_m'])
  inside = valid & (bins >= 0)
  total = len(valid)
  return {
    'total_candidate_points': total,
    'projected_forward_valid': int(valid.sum()),
    'mapping_unavailable': 0,
    'nonforward_horizon': int((~valid).sum()),
    'out_of_domain': int((valid & (bins < 0)).sum()),
    'valid_in_domain': int(inside.sum()),
    'unavailable_count': int((~inside).sum()),
    'unavailable_rate': float((~inside).sum() / total) if total else None,
    'lateral_m': distribution(projected['lateral_residual_m'][inside]),
    'bins': [
      {
        'distance_m': d,
        'bin_edges_m': list(BIN_EDGES[i : i + 2]),
        'candidate_count': int((bins == i).sum()),
        'unavailable_count': int(((bins == i) & ~valid).sum()),
        'unavailable_rate': float(((bins == i) & ~valid).sum() / (bins == i).sum()) if (bins == i).any() else None,
        'lateral_m': distribution(projected['lateral_residual_m'][inside & (bins == i)]),
        'small_sample': int((inside & (bins == i)).sum()) < 30,
      }
      for i, d in enumerate(DISTANCES)
    ],
    'coverage_semantics': 'MATCHED_POINT_PROJECTION_COUNTS;FRAME_MATCHING_REPORTED_SEPARATELY',
  }


def readiness(report, previous):
  unseal(report)
  unseal(previous)
  return output(
    {
      'schema': 'DECLARED_HYPOTHESIS_METER_READINESS_V1',
      'status': 'APPROX_METER_DIAGNOSTIC_AVAILABLE',
      'diagnostic_sha256': report['receipt_sha256'],
      'previous_readiness_sha256': previous['receipt_sha256'],
      'blockers': previous['blockers'],
      'pixel_registration_status': 'PIXEL_GEOMETRY_REGISTRATION_PARTIAL',
      'independent_meter_validation': 'NOT_RUN',
      'total_physical_bound_status': 'TOTAL_PHYSICAL_BOUND_UNAVAILABLE',
      'vehicle_status': ['NOT_READY', 'REAL_VEHICLE_UNVERIFIED', 'VEHICLE_ACTIVATION_BLOCKED'],
    }
  )
