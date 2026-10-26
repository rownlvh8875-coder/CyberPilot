"""User/model priors and algebraic geometry only; no reference/measurement producer."""

import math
from pathlib import Path
import numpy as np
from openpilot.common.transformations import camera, orientation
from openpilot.tools.cyber_autotune import camera_calibration_evidence as c
from openpilot.tools.cyber_autotune import lane_projection_diagnostics as p
from openpilot.tools.cyber_autotune import lane_projection_validation as v
from openpilot.tools.cyber_autotune.lane_tail_report import unseal
from openpilot.tools.cyber_autotune.native_protocol import canonical, digest

ROOT = c.ROOT
F = np.diag([1.0, -1.0, -1.0])  # device/calib FRD -> assumed diagnostic road FLU
MAX_CELLS = 256  # Resource bound including four forward-distance samples, not acceptance threshold.
ROLES = ('INDEPENDENT_PHYSICAL_MEASUREMENT', 'STATIC_HARDWARE_SOURCE', 'USER_DECLARED_APPROX_GEOMETRY', 'VEHICLE_SPEC_PRIOR', 'MODEL_DERIVED_EXTRINSICS_PRIOR')
DISTANCES = v.DISTANCE_BUCKETS_M
FIREWALL = {
  'qualification_allowed': False,
  'reference_promotable': False,
  'sealed_reference_allowed': False,
  'vehicle_activation_allowed': False,
  'private_input_allowed': False,
}


def source_identity():
  paths = [
    'openpilot/common/transformations/camera.py',
    'openpilot/common/transformations/orientation.py',
    'openpilot/common/transformations/transformations.py',
    'openpilot/selfdrive/locationd/calibrationd.py',
    'openpilot/common/transformations/model.py',
  ]
  return {name: digest((ROOT / name).read_bytes()) for name in paths}


EXECUTED_SOURCE_SHA = digest(Path(__file__).read_bytes())
EXECUTION_SOURCES = source_identity()


def identity():
  if digest(Path(__file__).read_bytes()) != EXECUTED_SOURCE_SHA or source_identity() != EXECUTION_SOURCES:
    raise ValueError('RUNNING_DIAGNOSTIC_SOURCE_CHANGED')
  return digest(
    canonical(
      {
        'source': digest(Path(__file__).read_bytes()),
        'convention_sources': source_identity(),
        'projection': digest(Path(p.__file__).read_bytes()),
        'admission': c.identity(),
      }
    )
  )


def angles(rpy):
  if type(rpy) not in (tuple, list) or len(rpy) != 3:
    raise ValueError('THREE_EXPLICIT_RPY_REQUIRED')
  for k, x in enumerate(rpy):
    c.number(x)
    if abs(x) >= (math.pi / 2 if k == 1 else math.pi):
      raise ValueError('NONSINGULAR_RPY_DOMAIN_REQUIRED')
  return list(rpy)


def degrees(rpy):
  angles([math.radians(c.number(x)) for x in rpy])
  return [math.radians(x) for x in rpy]


def rotation(rpy):
  """Invert calib->device, then FRD->FLU. No direct independent Euler reuse."""
  return F @ orientation.rot_from_euler(angles(rpy)).T @ camera.device_frame_from_view_frame


def physical_euler(rpy):
  relative = F @ orientation.rot_from_euler(angles(rpy)).T @ F
  return orientation.euler_from_rot(relative).tolist()


def prior():
  return c.seal(
    {
      'schema': 'APPROX_GEOMETRY_DIAGNOSTIC_V1',
      'status': 'PARTIAL_APPROX_GEOMETRY',
      'roles': list(ROLES),
      'source_sha256': identity(),
      'convention_sources_sha256': source_identity(),
      'user_declaration': 'comma4 mounted below interior rear-view mirror; approximately vehicle center plane',
      'user_declaration_sha256': digest(b'USER_REPORT_COMMA4_BELOW_REAR_VIEW_MIRROR_APPROX_CENTER'),
      'camera_family': 'comma4/mici_USER_REPORTED_NOT_PER_UNIT_VERIFIED',
      'actual_sensor': None,
      'orientation': {
        'role': 'MODEL_DERIVED_EXTRINSICS_PRIOR',
        'reported_deg': [0.0, 2.34, 0.2],
        'reported_rounded_rad': [None, 0.0408, 0.00349],
        'converted_rad': [0.0, math.radians(2.34), math.radians(0.2)],
        'conversion_primary': 'USER_REPORTED_DEGREES_APPROXIMATE_NOT_MEASUREMENT_PRECISION',
        'source': 'USER_REPORTED_LIVE_CALIBRATION_NOT_LOG_CAPTURE',
        'observation_timestamp': None,
        'physical_uncertainty': None,
        'independent': False,
        'adapter': 'R_optical_to_diagnostic_road=F*E(device_from_calib)^T*V(optical_to_device)',
        'source_frame': 'CALIB_FRD_X_FORWARD_Y_RIGHT_Z_DOWN',
        'target_frame': 'ASSUMED_ROAD_FLU_X_FORWARD_Y_LEFT_Z_UP_NOT_SURVEYED',
        'road_alignment': 'ASSUMED_FOR_DIAGNOSTIC_NOT_REGISTERED_GROUND_TRUTH',
      },
      'mount_y': {
        'nominal_m': 0.0,
        'role': 'USER_DECLARED_APPROX_GEOMETRY',
        'declaration': 'USER_DECLARED_APPROX_CENTER_MOUNT',
        'physical_uncertainty': None,
        'range': None,
        'range_role': 'DIAGNOSTIC_SENSITIVITY_RANGE_IF_EXPLICITLY_DECLARED',
      },
      'camera_height_m': None,
      'mount_x_m': None,
      'physical_uncertainty': None,
      'static_intrinsics': {
        'role': 'STATIC_HARDWARE_SOURCE',
        'source_sha256': c.CAMERA_SHA,
        'actual_sensor_mapping_pending': True,
        'matrix': None,
        'distortion': 'UNKNOWN_NOT_ASSUMED_ZERO',
      },
      'vehicle': {
        'role': 'VEHICLE_SPEC_PRIOR',
        'status': 'VEHICLE_SPEC_IDENTITY_PENDING',
        'model_identity': None,
        'repository_candidate': 'HYUNDAI_SANTA_FE_2022_FIXED_REPLAY_TEST_TARGET_ONLY',
        'overall_length_m': None,
        'overall_width_m': None,
        'overall_height_m': None,
        'wheelbase_m': None,
        'spec_source_url': None,
        'spec_source_sha256': None,
        'camera_height_estimate_m': None,
      },
      'labels': ['APPROXIMATE_GEOMETRY_DIAGNOSTIC', 'NO_PHYSICAL_HEIGHT_MEASUREMENT', 'NO_METRIC_QUALIFICATION'],
      'independent': False,
      **FIREWALL,
    }
  )


def validate_prior(value):
  unseal(value)
  if value != prior():
    raise ValueError('EXACT_FROZEN_DIAGNOSTIC_PRIOR_REQUIRED')
  return value


def output(fields):
  return c.seal({**fields, **FIREWALL, 'physical_uncertainty': None, 'independent': False})


def ray_relation(rpy, uv):
  if type(uv) not in (tuple, list) or len(uv) != 2:
    raise ValueError('NORMALIZED_OPTICAL_UV_REQUIRED')
  u, vv = (c.number(x) for x in uv)
  ray = rotation(rpy) @ np.array([u, vv, 1.0])
  if ray[2] >= -p.HORIZON_NUMERIC_TOLERANCE:
    raise ValueError('HORIZON_OR_UPWARD_RAY')
  forward, lateral = -ray[:2] / ray[2]
  if forward <= 0 or not np.all(np.isfinite([forward, lateral])):
    raise ValueError('NONFORWARD_OR_NONFINITE_DIAGNOSTIC_RAY')
  return output(
    {
      'scope': 'SYMBOLIC_HEIGHT_RELATION',
      'actual_height_m': None,
      'normalized_optical_uv': list(uv),
      'ray_diagnostic_road': ray.tolist(),
      'forward_per_height': float(forward),
      'lateral_per_height': float(lateral),
      'equations': ['forward_from_camera_footpoint_m=h*forward_per_height', 'lateral_from_vehicle_center_plane_m=declared_mount_y+h*lateral_per_height'],
      'coordinate_origin': 'CAMERA_VERTICAL_FOOTPOINT_X_ZERO_NOT_SURVEYED_VEHICLE_DATUM',
    }
  )


def symbolic_height(value, uv):
  validate_prior(value)
  x = unseal(ray_relation(value['orientation']['converted_rad'], uv))
  return output({**x, 'prior_sha256': value['receipt_sha256'], 'source_sha256': identity()})


def project(value, uv, height_m, *, mount_y_m=None, rpy_deg=None):
  validate_prior(value)
  c.number(height_m, positive=True)
  y = value['mount_y']['nominal_m'] if mount_y_m is None else c.number(mount_y_m)
  rpy = value['orientation']['converted_rad'] if rpy_deg is None else degrees(rpy_deg)
  relation = ray_relation(rpy, uv)
  return output(
    {
      'scope': 'APPROXIMATE_GEOMETRY_DIAGNOSTIC',
      'input_domain': 'SYNTHETIC_NORMALIZED_RAY_NO_PRIVATE_PIXEL',
      'prior_sha256': value['receipt_sha256'],
      'source_sha256': identity(),
      'selected_height_parameter_m': height_m,
      'height_role': 'ALGEBRAIC_PARAMETER_NOT_PHYSICAL_PRIOR',
      'selected_mount_y_parameter_m': y,
      'rpy_input_rad': rpy,
      'forward_m': height_m * relation['forward_per_height'],
      'lateral_left_m': y + height_m * relation['lateral_per_height'],
      'coordinate_origin': relation['coordinate_origin'],
      'ray': relation['ray_diagnostic_road'],
      'pixel_to_meter_truth': False,
    }
  )


def parameter_policy(heights_m, rpy_deg_choices, mount_y_m, *, rationale):
  for values in (heights_m, rpy_deg_choices, mount_y_m):
    if type(values) not in (list, tuple) or not values or len(values) > MAX_CELLS:
      raise ValueError('EXPLICIT_BOUNDED_NONEMPTY_GRID_REQUIRED')
    encoded = [tuple(float(c.number(t)) for t in x) if type(x) in (list, tuple) else float(c.number(x)) for x in values]
    if len(set(encoded)) != len(encoded):
      raise ValueError('DUPLICATE_GRID_CELL')
  if len(heights_m) * len(rpy_deg_choices) * len(mount_y_m) * len(DISTANCES) > MAX_CELLS:
    raise ValueError('BOUNDED_RESOURCE_MATRIX_REQUIRED')
  for h in heights_m:
    c.number(h, positive=True)
  for y in mount_y_m:
    c.number(y)
  for rpy in rpy_deg_choices:
    degrees(rpy)
  if type(rationale) is not str or not rationale.strip():
    raise ValueError('PARAMETRIC_DOMAIN_RATIONALE_REQUIRED')
  return output(
    {
      'schema': 'APPROX_GEOMETRY_PARAMETER_POLICY_V1',
      'heights_m': list(heights_m),
      'rpy_deg_choices': list(rpy_deg_choices),
      'mount_y_m': list(mount_y_m),
      'forward_distances_m': list(DISTANCES),
      'rationale': rationale,
      'range_role': 'DIAGNOSTIC_SENSITIVITY_RANGE_NOT_PHYSICAL_UNCERTAINTY',
      'height_role': 'ALGEBRAIC_PARAMETER_NOT_COARSE_VEHICLE_PRIOR',
      'enumeration': 'HEIGHT_ORIENTATION_MOUNT_DISTANCE_STABLE_ORDER',
      'source_sha256': identity(),
    }
  )


def sensitivity(value, policy):
  validate_prior(value)
  unseal(policy)
  expected = parameter_policy(policy['heights_m'], policy['rpy_deg_choices'], policy['mount_y_m'], rationale=policy['rationale'])
  if expected != policy:
    raise ValueError('FROZEN_PARAMETER_POLICY_BINDING_MISMATCH')
  rows = []
  for h in policy['heights_m']:
    for rpy in policy['rpy_deg_choices']:
      r = rotation(degrees(rpy))
      for y in policy['mount_y_m']:
        for distance in DISTANCES:
          center = np.array([0.0, y, h])  # Explicit camera-footpoint origin, NOT surveyed vehicle mount_x.
          target = np.array([distance, 0.0, 0.0])
          q = r.T @ (target - center)
          if q[2] <= 0:
            raise ValueError('TARGET_BEHIND_CAMERA')
          uv = (q[:2] / q[2]).tolist()
          projected = p.ground_projection(np.eye(3), r, center, uv)
          j = projected['jacobian']
          rows.append(
            {
              'height_parameter_m': h,
              'rpy_deg': list(rpy),
              'mount_y_parameter_m': y,
              'forward_distance_m': distance,
              'normalized_optical_uv': uv,
              'forward_m': projected['forward_m'],
              'lateral_left_m': projected['lateral_left_m'],
              'lateral_sensitivity_m_per_normalized_u': j['u_px'],
              'lateral_pixel_sensitivity_symbolic': 'lateral_sensitivity_m_per_normalized_u / actual_fx_px',
              'height_sensitivity_at_fixed_ray_m_per_m': j['camera_height_m'],
              'world_roll_sensitivity_m_per_rad': j['roll_world_x_rad'],
              'world_pitch_sensitivity_m_per_rad': j['pitch_world_y_rad'],
              'world_yaw_sensitivity_m_per_rad': j['yaw_world_z_rad'],
            }
          )
  return output(
    {
      'scope': 'PARAMETRIC_LOOKAHEAD_DIAGNOSTIC_NOT_MEASURED_ERROR',
      'prior_sha256': value['receipt_sha256'],
      'policy_sha256': policy['receipt_sha256'],
      'source_sha256': identity(),
      'coordinate_origin': 'CAMERA_VERTICAL_FOOTPOINT_X_ZERO_NOT_SURVEYED_VEHICLE_DATUM',
      'geometry_assumptions': ['UNDISTORTED_PINHOLE', 'FLAT_GROUND', 'CALIB_ALIGNED_DIAGNOSTIC_ROAD'],
      'sensitivity_comparison': 'EACH_LOOKAHEAD_REPROJECTS_TARGET; DERIVATIVES_HOLD_ITS_RESULTING_RAY_FIXED',
      'rows': rows,
      'actual_fx_px': None,
      'measured_meter_error': None,
      'total_conservative_uncertainty_m': None,
    }
  )


def vehicle_sanity(value, spec, height_parameter_m):
  validate_prior(value)
  c.exact(
    spec,
    (
      'schema',
      'role',
      'model_identity',
      'overall_length_m',
      'overall_width_m',
      'overall_height_m',
      'wheelbase_m',
      'source_url',
      'source_sha256',
      'assumptions',
    ),
  )
  if spec['schema'] != 'VEHICLE_SPEC_PRIOR_V1' or spec['role'] != 'VEHICLE_SPEC_PRIOR':
    raise ValueError('DECLARED_VEHICLE_SPEC_PRIOR_REQUIRED')
  for k in ('model_identity', 'assumptions', 'source_url'):
    if type(spec[k]) is not str or not spec[k].strip():
      raise ValueError('SPEC_PROVENANCE_REQUIRED')
  if not spec['source_url'].startswith('https://'):
    raise ValueError('EXPLICIT_DOCUMENT_SOURCE_URL_REQUIRED')
  c.sha(spec['source_sha256'])
  for k in ('overall_length_m', 'overall_width_m', 'overall_height_m', 'wheelbase_m'):
    c.number(spec[k], positive=True)
  if spec['wheelbase_m'] >= spec['overall_length_m']:
    raise ValueError('IMPOSSIBLE_DECLARED_SPEC')
  c.number(height_parameter_m, positive=True)
  return output(
    {
      'scope': 'DECLARED_SPEC_SANITY_ONLY_SOURCE_AND_VEHICLE_MATCH_UNVERIFIED',
      'status': 'OUTSIDE_DECLARED_SPEC_SANITY_DOMAIN' if height_parameter_m > spec['overall_height_m'] else 'WITHIN_DECLARED_SPEC_SANITY_DOMAIN',
      'spec_sha256': digest(canonical(spec)),
      'actual_vehicle_match_verified': False,
      'camera_height_estimate_m': None,
      'assumptions': spec['assumptions'],
      'height_parameter_m': height_parameter_m,
      'independent_calibration_status': 'PENDING',
    }
  )


def compare_physical(value, calibration, *, discrepancy_bound_rad=None):
  validate_prior(value)
  if discrepancy_bound_rad is not None:
    c.number(discrepancy_bound_rad, positive=True)
  fields = {
    'scope': 'APPROX_PHYSICAL_CONSISTENCY_DIAGNOSTIC',
    'prior_sha256': value['receipt_sha256'],
    'source_sha256': identity(),
    'live_calibration_validated': False,
    'automatic_discrepancy_threshold_rad': None,
    'declared_diagnostic_discrepancy_bound_rad': discrepancy_bound_rad,
  }
  if calibration is None:
    return output({**fields, 'status': 'PHYSICAL_MEASUREMENT_COMPARISON_PENDING', 'physical_receipt_sha256': None, 'orientation': None, 'height': None})
  c.validate_admitted(calibration)
  m = calibration['measurement']
  o = m['observations']
  effective = physical_euler(value['orientation']['converted_rad'])
  rows = {}
  for name, approx in zip(('roll', 'pitch', 'yaw'), effective, strict=True):
    actual = o[name + '_rad']['value']
    delta = math.atan2(math.sin(actual - approx), math.cos(actual - approx))
    rows[name] = {
      'approximate_rad': approx,
      'approximate_deg': math.degrees(approx),
      'physical_rad': actual,
      'delta_physical_minus_approx_rad': delta,
      'outside_declared_diagnostic_bound': None if discrepancy_bound_rad is None else abs(delta) > discrepancy_bound_rad,
    }
  return output(
    {
      **fields,
      'status': 'CONSISTENCY_DIAGNOSTIC_AVAILABLE_NOT_VALIDATION',
      'physical_receipt_sha256': calibration['receipt_sha256'],
      'physical_scope': m['scope'],
      'cross_device_matching': 'UNVERIFIED_NO_PRIOR_PER_UNIT_IDENTITY',
      'orientation': rows,
      'height': {'approximate_m': None, 'physical_m': o['height_m']['value']},
      'possible_discrepancy_causes': [
        'SIGN_OR_FRAME_MISMATCH',
        'GROUND_SLOPE',
        'MOUNT_REFERENCE_MISMATCH',
        'MODEL_DERIVED_CALIBRATION_DISCREPANCY',
        'PHYSICAL_MEASUREMENT_ERROR',
      ],
      'truth_selected_automatically': False,
    }
  )


def readiness(value):
  validate_prior(value)
  old = ROOT / 'docs/cyberpilot/changes/independent-reference-next-blocker-plan-v2.json'
  return output(
    {
      'schema': 'APPROX_GEOMETRY_ADDITIVE_BLOCKER_SNAPSHOT_V1',
      'prior_sha256': value['receipt_sha256'],
      'existing_blocker_plan_sha256': digest(old.read_bytes()),
      'diagnostic_status': 'APPROX_GEOMETRY_DIAGNOSTIC_AVAILABLE',
      'diagnostic_node': {
        'code': 'APPROX_GEOMETRY_DIAGNOSTIC_AVAILABLE',
        'status': 'PASS_DIAGNOSTIC_ONLY',
        'resolves_independent_dependencies': False,
        'evidence_sha256': value['receipt_sha256'],
      },
      'calibration_status': 'CALIBRATION_MEASUREMENT_PENDING',
      'independent_validation_status': 'INDEPENDENT_CALIBRATION_VALIDATION_PENDING',
      'metric_calibration_status': 'METRIC_CALIBRATION_UNAVAILABLE',
      'independent_reference_status': 'BLOCKED: INDEPENDENT_REFERENCE_UNAVAILABLE',
      'private_comma4': 'NOT_OPENED',
      'sealed_reference': 'NOT_GENERATED',
      'vehicle_status': ['NOT_READY', 'REAL_VEHICLE_UNVERIFIED', 'VEHICLE_ACTIVATION_BLOCKED'],
    }
  )
