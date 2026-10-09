"""Reported physical mean, separate from metrology admission and prior history.

No log/frame inputs, pose fitting, uncertainty inference, or reference production.
"""
import json
from pathlib import Path

from openpilot.tools.cyber_autotune import approximate_geometry_diagnostic as a
from openpilot.tools.cyber_autotune import camera_calibration_evidence as c
from openpilot.tools.cyber_autotune import coarse_camera_height_diagnostic as coarse
from openpilot.tools.cyber_autotune.lane_tail_report import unseal
from openpilot.tools.cyber_autotune.native_protocol import canonical, digest

OBSERVED_MEAN_M = 1.385  # Exact user-reported repeated optical-center height mean, not a fitted value.
NOTICE = '1.385 m physical mean recorded; conservative uncertainty still required'
BASELINE_SHA = '99670290150be22de2bd65c88490d7d263ece175'
HISTORY = {
  'santa-fe-coarse-height-prior-v1.json': 'ce1068920a1964e3bdca620d357fc601ca6c03024118d711758553068a474a16',
  'coarse-height-diagnostic-result-v1.json': '7f86e9202d89c6f8f95e291170ed00d3018b26492f292d88e67be5883b7bb183',
  'qcamera-pixel-registration-v1.json': '066d339a2ee006db43ab8ab735e9806050c228112223b1a80f76e2c05021110f',
}


EXECUTED_SOURCE_SHA = digest(Path(__file__).read_bytes())


def identity():
  if digest(Path(__file__).read_bytes()) != EXECUTED_SOURCE_SHA:
    raise ValueError('RUNNING_HEIGHT_OBSERVATION_SOURCE_CHANGED')
  return digest(canonical({'source': digest(Path(__file__).read_bytes()), 'coarse_dependency': coarse.identity(), 'admission': c.identity()}))


def output(fields):
  return c.seal({**fields, **a.FIREWALL, 'independent_calibration_validated': False})


def historical(name):
  """Exact immutable baseline bytes; never recalculate or migrate historical results."""
  data = (c.ROOT / 'docs/cyberpilot/changes' / name).read_bytes()
  if digest(data) != HISTORY[name]:
    raise ValueError('HISTORICAL_HEIGHT_OR_REGISTRATION_EVIDENCE_CHANGED')
  value = json.loads(data)
  unseal(value)
  return value


def observation():
  return output({
    'schema': 'PHYSICAL_HEIGHT_OBSERVATION_V1',
    'status': 'PHYSICAL_HEIGHT_OBSERVATION_RECORDED',
    'availability': 'PHYSICAL_HEIGHT_OBSERVATION_AVAILABLE',
    'baseline_sha': BASELINE_SHA,
    'source_sha256': identity(),
    'source': 'USER_REPORTED_REPEATED_PHYSICAL_MEASUREMENT',
    'user_report_sha256': digest(b'USER_REPORT_REPEATED_GROUND_TO_COMMA4_ROAD_CAMERA_OPTICAL_CENTER_MEAN_1.385_M_UNCERTAINTY_NOT_PROVIDED'),
    'camera_family': 'comma4/mici_USER_REPORTED_NOT_PER_UNIT_VERIFIED',
    'device_binding_status': 'PER_UNIT_IDENTITY_PENDING',
    'definition': 'GROUND_PLANE_TO_ROAD_CAMERA_OPTICAL_CENTER_VERTICAL_HEIGHT',
    'value_m': OBSERVED_MEAN_M,
    'physical_measurement': True,
    'coarse_prior': False,
    'model_derived': False,
    'liveCalibration_derived': False,
    'candidate_derived': False,
    'measurement_uncertainty': None,
    'uncertainty_status': 'CALIBRATION_UNCERTAINTY_PENDING',
    'individual_measurements_m': None,
    'repetition_count': None,
    'instrument': None,
    'measurement_method': None,
    'measurement_timestamp': None,
    'operator_id': None,
    'ground_survey': None,
    'independent': False,
    'admitted_calibration_receipt': False,
  })


def validate(value):
  unseal(value)
  if value != observation():
    raise ValueError('EXACT_RECORDED_HEIGHT_OBSERVATION_REQUIRED')


def consistency(value):
  validate(value)
  old = historical('santa-fe-coarse-height-prior-v1.json')
  return output({
    'schema': 'APPROX_PHYSICAL_CONSISTENCY_DIAGNOSTIC_HEIGHT_V1',
    'status': 'HEIGHT_COMPARISON_ONLY_UNCERTAINTY_PENDING',
    'observation_sha256': value['receipt_sha256'],
    'coarse_prior_sha256': old['receipt_sha256'],
    'coarse_prior_file_sha256': HISTORY['santa-fe-coarse-height-prior-v1.json'],
    'coarse_nominal_m': old['nominal_height_m'],
    'physical_observed_mean_m': value['value_m'],
    'delta_physical_minus_coarse_m': value['value_m'] - old['nominal_height_m'],
    'within_historical_diagnostic_range': old['sweep_min_m'] <= value['value_m'] <= old['sweep_max_m'],
    'diagnostic_range_role': 'HISTORICAL_DIAGNOSTIC_SENSITIVITY_RANGE_NOT_MEASUREMENT_UNCERTAINTY',
    'coarse_prior_validated': False,
    'coarse_prior_preserved': True,
    'outside_range_does_not_reject_physical_observation': True,
    'orientation_comparison': None,
    'live_calibration_validated': False,
  })


def geometry_context(value):
  validate(value)
  prior = a.prior()
  return output({
    'schema': 'PHYSICAL_HEIGHT_APPROXIMATE_POSE_CONTEXT_V1',
    'status': 'MIXED_PROVENANCE_DIAGNOSTIC_ONLY',
    'observation_sha256': value['receipt_sha256'],
    'orientation_mount_prior_sha256': prior['receipt_sha256'],
    'selected_height_m': value['value_m'],
    'height_role': 'PHYSICAL_HEIGHT_OBSERVATION',
    'height_selection': 'REPORTED_PHYSICAL_MEAN_OVER_COARSE_FOR_DIAGNOSTIC_ONLY_NOT_STRICT_ADMISSION',
    'per_unit_device_match_verified': False,
    'measurement_uncertainty': None,
    'orientation': prior['orientation'],
    'mount_y': prior['mount_y'],
    'coarse_nominal_historical_m': historical('santa-fe-coarse-height-prior-v1.json')['nominal_height_m'],
    'intrinsics_applicability': 'PENDING',
    'distortion_status': 'DISTORTION_UNVERIFIED',
  })


def sensitivity(value):
  """Add the physical mean as a parameter to the original synthetic fixed rays.

  These normalized rays are not private pixels; numbers are algebraic diagnostics
  with model-derived orientation, no camera intrinsics or physical error budget.
  """
  validate(value)
  old = historical('coarse-height-diagnostic-result-v1.json')
  prior = a.prior()
  original = old['nominal_result']['rows']
  rows = [coarse.row(prior, r['nominal_forward_distance_m'], r['fixed_normalized_optical_uv'], value['value_m'], r['source_rpy_deg']) for r in original]
  return output({
    'schema': 'PHYSICAL_HEIGHT_SYNTHETIC_SENSITIVITY_DERIVATIVE_V1',
    'status': 'NON_QUALIFYING_DIAGNOSTIC_ONLY',
    'source_sha256': identity(),
    'observation_sha256': value['receipt_sha256'],
    'historical_result_sha256': old['receipt_sha256'],
    'historical_result_file_sha256': HISTORY['coarse-height-diagnostic-result-v1.json'],
    'context_sha256': geometry_context(value)['receipt_sha256'],
    'input_domain': 'SYNTHETIC_NORMALIZED_OPTICAL_RAYS_NOT_QCAMERA_PIXELS',
    'ray_anchor': 'HISTORICAL_COARSE_NOMINAL_1.40_M_FIXED_RAYS',
    'new_nominal_reference_m': value['value_m'],
    'historical_height_grid_m': list(coarse.HEIGHT_GRID_M),
    'range_role': 'HISTORICAL_DIAGNOSTIC_SENSITIVITY_RANGE_NOT_PHYSICAL_UNCERTAINTY',
    'coarse_nominal_rows': original,
    'observed_mean_rows': rows,
    'measurement_uncertainty': None,
    'detector_meter_error': None,
    'total_conservative_uncertainty_m': None,
    'geometry_assumptions': ['UNDISTORTED_PINHOLE', 'FLAT_GROUND', 'MODEL_PRIOR_ROAD_ALIGNMENT_NOT_SURVEYED'],
  })


def target_height_consistency(value, solved_height_m, *, discrepancy_bound_m=None):
  """Future caller supplies a diagnostic bound; never force a solver to the mean."""
  validate(value)
  c.number(solved_height_m, positive=True)
  if discrepancy_bound_m is not None:
    c.number(discrepancy_bound_m, positive=True)
  delta = solved_height_m - value['value_m']
  return output({
    'schema': 'TARGET_PHYSICAL_HEIGHT_CONSISTENCY_DIAGNOSTIC_V1',
    'observation_sha256': value['receipt_sha256'],
    'physical_observed_mean_m': value['value_m'],
    'solved_height_m': solved_height_m,
    'delta_solved_minus_observed_m': delta,
    'declared_diagnostic_discrepancy_bound_m': discrepancy_bound_m,
    'warning': 'HEIGHT_POSE_CONSISTENCY_WARNING' if discrepancy_bound_m is not None and abs(delta) > discrepancy_bound_m else None,
    'assessment': 'BOUND_NOT_DECLARED' if discrepancy_bound_m is None else 'DIAGNOSTIC_COMPARISON_ONLY',
    'measurement_uncertainty': None,
    'solver_constrained': False,
    'truth_selected_automatically': False,
  })


def readiness(value):
  validate(value)
  registration = historical('qcamera-pixel-registration-v1.json')
  blockers = [
    'CALIBRATION_UNCERTAINTY_PENDING', 'INDEPENDENT_CALIBRATION_VALIDATION_PENDING',
    'PIXEL_GEOMETRY_REGISTRATION_PENDING', 'METRIC_CALIBRATION_UNAVAILABLE', 'INDEPENDENT_REFERENCE_UNAVAILABLE',
  ]
  return output({
    'schema': 'PHYSICAL_HEIGHT_ADDITIVE_READINESS_V1',
    'source_sha256': identity(),
    'height_status': 'PHYSICAL_HEIGHT_OBSERVATION_AVAILABLE',
    'height_observation_sha256': value['receipt_sha256'],
    'full_calibration_status': 'CALIBRATION_MEASUREMENT_PENDING',
    'uncertainty_status': 'CALIBRATION_UNCERTAINTY_PENDING',
    'pixel_registration_status': registration['status'],
    'pixel_registration_sha256': registration['receipt_sha256'],
    'blockers': blockers,
    'pending_components': ['FORMAL_HEIGHT_UNCERTAINTY', 'PHYSICAL_PITCH', 'PHYSICAL_ROLL', 'PHYSICAL_YAW',
                           'TARGET_POSE_VALIDATION', 'INTRINSICS_APPLICABILITY', 'DISTORTION', 'QCAMERA_MAPPING_RESIDUAL'],
    'meter_result_required_gates': ['PIXEL_GEOMETRY_REGISTRATION_VALIDATED', 'INDEPENDENT_CALIBRATION_VALIDATION'],
    'meter_results': None,
    'sealed_reference': 'NOT_GENERATED',
    'private_input_access_this_increment': 'NOT_OPENED',
    'vehicle': ['NOT_READY', 'REAL_VEHICLE_UNVERIFIED', 'VEHICLE_ACTIVATION_BLOCKED'],
    'nodes': [{'code': 'PHYSICAL_HEIGHT_OBSERVATION_AVAILABLE', 'status': 'RECORDED_NOT_ADMITTED',
               'evidence_sha256': value['receipt_sha256'], 'resolves_calibration_dependencies': False}],
  })
