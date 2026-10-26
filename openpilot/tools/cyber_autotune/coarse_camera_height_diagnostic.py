"""Frozen user-approved geometry estimate; no measurement or reference producer."""

import math
from pathlib import Path
import numpy as np
from openpilot.tools.cyber_autotune import approximate_geometry_diagnostic as a
from openpilot.tools.cyber_autotune import lane_projection_diagnostics as p
from openpilot.tools.cyber_autotune.lane_tail_report import unseal
from openpilot.tools.cyber_autotune.native_protocol import canonical, digest

# User approval, not derived from vehicle/tire dimensions or physical metrology.
HEIGHT_NOMINAL_M = 1.40
HEIGHT_GRID_M = (1.33, 1.35, 1.375, 1.40, 1.425, 1.45, 1.47)
# Bounded algebraic probes chosen before execution, not plausible physical bounds.
PITCH_GRID_DEG = (1.84, 2.34, 2.84)
ROLL_GRID_DEG = (-0.5, 0.0, 0.5)
YAW_GRID_DEG = (-0.3, 0.2, 0.7)
DERIVATIVE_STEP_RAD = 1e-6  # Central difference in reported calibration Euler input, not world-axis Jacobian.
LATERAL_PROBE_M = 1.0  # Synthetic lateral point, not actual lane width or boundary.
EXECUTED_SOURCE_SHA = digest(Path(__file__).read_bytes())
DEPENDENCIES = {'approximate': a.identity(), 'projection': digest(Path(p.__file__).read_bytes())}
OFFICIAL_SOURCE = {
  'url': 'https://www.hyundai.com/kr/ko/brand/brandstory/model/santafe-history/2021-santafe',
  'retrieved_utc_date': '2026-10-08',
  'html_sha256': '3c5beb191acf89c114b2345279b6f42e7365a7140a854289ea3bc742cc86c5e4',
  'page_variant': '2021.12 Smartstream D2.2 2WD/FWD',
  'meaning': 'OFFICIAL_VARIANT_SPEC_CONTEXT_NOT_THIS_VEHICLE_PER_UNIT_VERIFICATION',
}


def identity():
  if (
    digest(Path(__file__).read_bytes()) != EXECUTED_SOURCE_SHA
    or a.identity() != DEPENDENCIES['approximate']
    or digest(Path(p.__file__).read_bytes()) != DEPENDENCIES['projection']
  ):
    raise ValueError('RUNNING_COARSE_DIAGNOSTIC_SOURCE_CHANGED')
  return digest(canonical({'source': EXECUTED_SOURCE_SHA, 'dependencies': DEPENDENCIES}))


def output(fields):
  return a.output({**fields, 'coarse_source_sha256': identity(), 'physical_measurement': False})


def vehicle_context():
  sidewall_mm = 235.0 * 0.60
  wheel_mm = 18.0 * 25.4
  diameter_m = (wheel_mm + 2 * sidewall_mm) / 1000
  return output({
    'schema': 'SANTA_FE_VEHICLE_GEOMETRY_SANITY_CONTEXT_V1',
    'role': 'VEHICLE_SPEC_PRIOR',
    'status': 'VEHICLE_SPEC_PROVENANCE_PARTIAL',
    'user_vehicle_identity': 'THE_NEW_SANTA_FE_TM',
    'user_vehicle_model_year': 2021,
    'user_identity_source': 'USER_DECLARATION_NOT_VIN_OR_TRIM_VERIFICATION',
    'actual_trim_verified': False,
    'official_source': OFFICIAL_SOURCE,
    'overall_length_m': 4.785,
    'overall_width_m': 1.900,
    'overall_height_m': 1.685,
    'wheelbase_m': 2.765,
    'derived_camera_height_m': None,
    'tire_geometry': {
      'specification': '235/60 R18',
      'sidewall_mm': sidewall_mm,
      'wheel_diameter_mm': wheel_mm,
      'outer_diameter_m': diameter_m,
      'unloaded_nominal_radius_m': diameter_m / 2,
      'calculation': '18*25.4 + 2*(235*0.60) millimeters',
      'loaded_radius_m': None,
      'camera_height_measurement': False,
      'scope': 'NOMINAL_TIRE_SIZE_ARITHMETIC_NOT_LOADED_WHEEL_CENTER_SURVEY',
    },
  })


def height_prior():
  return output({
    'schema': 'COARSE_CAMERA_HEIGHT_PRIOR_V1',
    'status': 'COARSE_CAMERA_HEIGHT_PRIOR_AVAILABLE',
    'nominal_height_m': HEIGHT_NOMINAL_M,
    'sweep_min_m': HEIGHT_GRID_M[0],
    'sweep_max_m': HEIGHT_GRID_M[-1],
    'source_role': 'USER_APPROVED_DIAGNOSTIC_ESTIMATE',
    'parameter_role': 'USER_APPROVED_COARSE_GEOMETRY_PRIOR',
    'derivation': 'EXPLICIT_USER_APPROVAL_NOT_VEHICLE_HEIGHT_RATIO_OR_TIRE_DERIVATION',
    'approval_sha256': digest(b'USER_APPROVED_SANTA_FE_TM_2021_CAMERA_HEIGHT_NOMINAL_1.40_SWEEP_1.33_1.47_DIAGNOSTIC_ONLY'),
    'vehicle_context_sha256': vehicle_context()['receipt_sha256'],
    'diagnostic_sensitivity_range': [HEIGHT_GRID_M[0], HEIGHT_GRID_M[-1]],
    'range_role': 'DIAGNOSTIC_SENSITIVITY_RANGE',
    'measurement_uncertainty': None,
    'physical_height_measured': False,
  })


def validate_prior(value):
  unseal(value)
  if value != height_prior():
    raise ValueError('EXACT_FROZEN_COARSE_HEIGHT_PRIOR_REQUIRED')


def frozen_policy():
  return output({
    'schema': 'COARSE_CAMERA_HEIGHT_SENSITIVITY_POLICY_V1',
    'height_prior_sha256': height_prior()['receipt_sha256'],
    'orientation_mount_prior_sha256': a.prior()['receipt_sha256'],
    'heights_m': list(HEIGHT_GRID_M),
    'pitches_deg': list(PITCH_GRID_DEG),
    'rolls_deg': list(ROLL_GRID_DEG),
    'yaws_deg': list(YAW_GRID_DEG),
    'distances_m': list(a.DISTANCES),
    'range_role': 'DIAGNOSTIC_SENSITIVITY_RANGE_NOT_PHYSICAL_UNCERTAINTY',
    'orientation_range_role': 'MODEL_PRIOR_SENSITIVITY_NOT_PHYSICAL_UNCERTAINTY',
    'orientation_range_rationale': 'PLUS_MINUS_0.5_DEG_ALGEBRAIC_PROBES_NOT_EMPIRICAL_PLAUSIBILITY_OR_UNCERTAINTY',
    'ray_policy': 'HOLD_NOMINAL_RAYS_FIXED_ACROSS_HEIGHT_AND_ORIENTATION',
    'synthetic_lateral_probe_left_m': LATERAL_PROBE_M,
    'derivative_step_rad': DERIVATIVE_STEP_RAD,
    'enumeration': 'HEIGHT_PITCH_DISTANCE_THEN_ROLL_YAW_DISTANCE',
    'matrix_rows': len(HEIGHT_GRID_M) * len(PITCH_GRID_DEG) * len(a.DISTANCES),
    'orientation_1d_rows': (len(ROLL_GRID_DEG) + len(YAW_GRID_DEG)) * len(a.DISTANCES),
    'geometry_assumptions': ['UNDISTORTED_PINHOLE', 'FLAT_GROUND', 'CALIB_ALIGNED_ASSUMED_ROAD_NOT_SURVEYED'],
    'coordinate_origin': 'CAMERA_VERTICAL_FOOTPOINT_X_ZERO_NOT_SURVEYED_VEHICLE_DATUM',
    'qualification_thresholds': None,
  })


def nominal_rays(prior):
  r = a.rotation(prior['orientation']['converted_rad'])
  center = np.array([0.0, prior['mount_y']['nominal_m'], HEIGHT_NOMINAL_M])
  rays = []
  for distance in a.DISTANCES:
    pair = []
    for lateral in (0.0, LATERAL_PROBE_M):
      optical = r.T @ (np.array([distance, lateral, 0.0]) - center)
      if optical[2] <= 0:
        raise ValueError('NOMINAL_TARGET_BEHIND_CAMERA')
      pair.append((optical[:2] / optical[2]).tolist())
    rays.append((distance, pair))
  return rays


def row(prior, distance, uv, height, rpy_deg):
  projected = [a.project(prior, pixel, height, rpy_deg=rpy_deg) for pixel in uv]
  rotation = a.rotation(a.degrees(rpy_deg))
  center = [0.0, prior['mount_y']['nominal_m'], height]
  jac = p.ground_projection(np.eye(3), rotation, center, uv[1])['jacobian']
  pitch_minus, pitch_plus = list(rpy_deg), list(rpy_deg)
  pitch_minus[1] -= math.degrees(DERIVATIVE_STEP_RAD)
  pitch_plus[1] += math.degrees(DERIVATIVE_STEP_RAD)
  minus = a.project(prior, uv[1], height, rpy_deg=pitch_minus)
  plus = a.project(prior, uv[1], height, rpy_deg=pitch_plus)
  return {
    'height_m': height,
    'pitch_deg': rpy_deg[1],
    'source_rpy_deg': list(rpy_deg),
    'nominal_forward_distance_m': distance,
    'fixed_normalized_optical_uv': uv,
    'forward_m': projected[0]['forward_m'],
    'center_lateral_left_m': projected[0]['lateral_left_m'],
    'lateral_probe_forward_m': projected[1]['forward_m'],
    'lateral_probe_left_m': projected[1]['lateral_left_m'],
    'forward_delta_from_nominal_m': projected[0]['forward_m'] - distance,
    'lateral_probe_delta_from_nominal_m': projected[1]['lateral_left_m'] - LATERAL_PROBE_M,
    'lateral_sensitivity_m_per_normalized_u': jac['u_px'],
    'pixel_sensitivity_symbolic': 'lateral_sensitivity_m_per_normalized_u / actual_fx_px',
    'fixed_ray_lateral_height_sensitivity_m_per_m': jac['camera_height_m'],
    'reported_pitch_forward_sensitivity_m_per_rad': (plus['forward_m'] - minus['forward_m']) / (2 * DERIVATIVE_STEP_RAD),
    'reported_pitch_lateral_sensitivity_m_per_rad': (plus['lateral_left_m'] - minus['lateral_left_m']) / (2 * DERIVATIVE_STEP_RAD),
    'world_axis_jacobian_m_per_rad': {name: jac[name] for name in ('roll_world_x_rad', 'pitch_world_y_rad', 'yaw_world_z_rad')},
  }


def evaluate(value, policy):
  validate_prior(value)
  unseal(policy)
  if policy != frozen_policy():
    raise ValueError('EXACT_FROZEN_COARSE_SENSITIVITY_POLICY_REQUIRED')
  prior = a.prior()
  rays = nominal_rays(prior)
  original = prior['orientation']['reported_deg']
  nominal = [row(prior, d, uv, HEIGHT_NOMINAL_M, original) for d, uv in rays]
  matrix = [
    row(prior, d, uv, height, [original[0], pitch, original[2]])
    for height in policy['heights_m'] for pitch in policy['pitches_deg'] for d, uv in rays
  ]
  one_d = []
  for axis, index, grid in (('roll', 0, policy['rolls_deg']), ('yaw', 2, policy['yaws_deg'])):
    for parameter in grid:
      rpy = list(original)
      rpy[index] = parameter
      for d, uv in rays:
        one_d.append({'axis': axis, 'axis_value_deg': parameter, **row(prior, d, uv, HEIGHT_NOMINAL_M, rpy)})
  envelopes = []
  for d in a.DISTANCES:
    cells = [x for x in matrix if x['nominal_forward_distance_m'] == d]
    envelopes.append({
      'nominal_forward_distance_m': d,
      **{k: [min(x[k] for x in cells), max(x[k] for x in cells)] for k in (
        'forward_m', 'center_lateral_left_m', 'lateral_probe_left_m', 'lateral_sensitivity_m_per_normalized_u',
        'reported_pitch_forward_sensitivity_m_per_rad',
      )},
      'scope': 'SAMPLED_GRID_ENVELOPE_NOT_CONTINUOUS_OR_PHYSICAL_UNCERTAINTY_BOUND',
    })
  binding = {
    'height_prior_sha256': value['receipt_sha256'],
    'orientation_mount_prior_sha256': prior['receipt_sha256'],
    'policy_sha256': policy['receipt_sha256'],
    'actual_fx_px': None,
    'measured_meter_error': None,
    'total_conservative_uncertainty_m': None,
  }
  return output({
    'schema': 'COARSE_APPROXIMATE_GEOMETRY_DIAGNOSTIC_RESULT_V1',
    **binding,
    'nominal_result': output({
      'schema': 'NOMINAL_APPROX_GEOMETRY_RESULT_V1',
      **binding,
      'source_orientation_deg': original,
      'rotation_optical_to_diagnostic_road': a.rotation(prior['orientation']['converted_rad']).tolist(),
      'parameter_roles': {
        'height': 'USER_APPROVED_COARSE_GEOMETRY_PRIOR',
        'mount_y': 'USER_DECLARED_APPROX_CENTER_MOUNT',
        'orientation': 'MODEL_DERIVED_EXTRINSICS_PRIOR',
      },
      'rows': nominal,
    }),
    'sensitivity_envelope': output({
      'schema': 'DIAGNOSTIC_SENSITIVITY_ENVELOPE_V1',
      **binding,
      'range_role': 'MODEL_PRIOR_SENSITIVITY_NOT_PHYSICAL_UNCERTAINTY',
      'matrix': matrix,
      'orientation_1d': one_d,
      'distance_envelopes': envelopes,
      'continuous_bound_claimed': False,
    }),
  })


def compare_physical(value, calibration):
  validate_prior(value)
  base = a.compare_physical(a.prior(), calibration)
  physical = None if calibration is None else calibration['measurement']['observations']['height_m']['value']
  return output({
    'schema': 'COARSE_APPROX_PHYSICAL_CONSISTENCY_DIAGNOSTIC_V1',
    'status': base['status'],
    'height_prior_sha256': value['receipt_sha256'],
    'orientation_comparison_sha256': base['receipt_sha256'],
    'physical_receipt_sha256': base.get('physical_receipt_sha256'),
    'physical_scope': base.get('physical_scope'),
    'cross_device_identity_verified': False,
    'automatic_reference_selection': False,
    'independent_validation_complete': False,
    'height': {
      'coarse_nominal_m': value['nominal_height_m'],
      'physical_m': physical,
      'delta_physical_minus_coarse_m': None if physical is None else physical - value['nominal_height_m'],
      'within_diagnostic_range': None if physical is None else value['sweep_min_m'] <= physical <= value['sweep_max_m'],
      'provenance_precedence': 'PHYSICAL_RECEIPT_OVER_COARSE_FOR_FUTURE_MATCHED_DEVICE',
      'outside_range_does_not_reject_physical_receipt': True,
      'coarse_prior_preserved': True,
    },
  })


def readiness(value):
  validate_prior(value)
  old = unseal(a.readiness(a.prior()))
  return output({
    **old,
    'schema': 'COARSE_HEIGHT_ADDITIVE_BLOCKER_SNAPSHOT_V1',
    'coarse_height_status': 'COARSE_CAMERA_HEIGHT_PRIOR_AVAILABLE',
    'coarse_height_node': {
      'code': 'COARSE_CAMERA_HEIGHT_PRIOR_AVAILABLE',
      'status': 'PASS_DIAGNOSTIC_ONLY',
      'evidence_sha256': value['receipt_sha256'],
      'resolves_independent_dependencies': False,
    },
    'independent_extrinsics_status': 'INDEPENDENT_EXTRINSICS_UNAVAILABLE',
  })
