"""Authority-free admission of aggregate plant-calibration evidence.

No log loading, fitting, threshold selection, plant execution, controller callback,
profile write, CAN transport or vehicle-use authority exists in this module.
"""
from dataclasses import asdict, dataclass, field
import hashlib
import json
import re

from openpilot.tools.cyber_autotune.contracts import finite_number, is_sha256


TARGET_VEHICLE = 'HYUNDAI_SANTA_FE_2022'
MODEL_FAMILY = 'YR_AR1_SPEED_FIXED'
MODEL_FEATURES = ('r1', 'u0', 'u0_inv_v', 'u0_v', 'roll')
REQUIRED_HORIZONS_S = (1.0, 5.0, 10.0)


@dataclass(frozen=True)
class CalibrationHorizon:
  horizon_s: float
  sample_count: int
  window_count: int
  yaw_rate_rmse_rad_s: float
  yaw_rate_correlation: float
  heading_endpoint_rmse_rad: float
  path_endpoint_rmse_m: float
  path_xy_rmse_m: float


@dataclass(frozen=True)
class PlantCalibrationEvidence:
  target_vehicle: str
  model_family: str
  feature_names: tuple[str, ...]
  delay_frames: int
  model_source_commit: str
  model_canonical_sha256: str
  assurance_contract_sha256: str
  precommit_sha256: str
  development_sha256: str
  frozen_sha256: str
  validation_sha256: str
  smoke_sha256: str
  adapter_sha256: str
  plant_builder_sha256: str
  validation_runner_sha256: str
  development_route_count: int
  validation_route_count: int
  validation_sequence_count: int
  eligible_pose_samples: int
  stability_radius: float
  development_validation_disjoint: bool
  model_structure_fixed_before_validation: bool
  validation_refit_performed: bool
  candidate_outputs_used_for_model_selection: bool
  deterministic_trace: bool
  deterministic_pose: bool
  acceptance_threshold_precommitted: bool
  descriptive_validation_only: bool
  primary_position_truth_independent: bool
  external_reproduction_established: bool
  current_platform_revalidated: bool
  real_vehicle_write: bool
  performance_acceptance: bool
  recommendation_authorized: bool
  horizons: tuple[CalibrationHorizon, ...]


@dataclass(frozen=True)
class PlantCalibrationAssessment:
  status: str
  blockers: tuple[str, ...]
  evidence_sha256: str | None = None
  development_route_count: int = 0
  validation_route_count: int = 0
  validation_sequence_count: int = 0
  eligible_pose_samples: int = 0
  stability_radius: float | None = None
  evidence_chain_verified: bool = False
  descriptive_validation_verified: bool = False
  plant_calibration_qualified: bool = field(default=False, init=False)
  runtime_accepted: bool = field(default=False, init=False)
  promotable: bool = field(default=False, init=False)


def _blocked(reason: str) -> PlantCalibrationAssessment:
  return PlantCalibrationAssessment('BLOCKED', (reason,))


def _canonical_sha256(value) -> str:
  payload = json.dumps(
    value, sort_keys=True, separators=(',', ':'), allow_nan=False,
  ).encode()
  return hashlib.sha256(payload).hexdigest()


def _horizon_valid(item) -> bool:
  return (
    type(item) is CalibrationHorizon
    and finite_number(item.horizon_s) and item.horizon_s > 0.0
    and type(item.sample_count) is int and item.sample_count > 0
    and type(item.window_count) is int and item.window_count > 0
    and all(finite_number(value) and value >= 0.0 for value in (
      item.yaw_rate_rmse_rad_s,
      item.heading_endpoint_rmse_rad,
      item.path_endpoint_rmse_m,
      item.path_xy_rmse_m,
    ))
    and finite_number(item.yaw_rate_correlation)
    and -1.0 <= item.yaw_rate_correlation <= 1.0
  )


def _evidence_shape_valid(value) -> bool:
  if type(value) is not PlantCalibrationEvidence:
    return False
  hashes = (
    value.model_canonical_sha256,
    value.assurance_contract_sha256,
    value.precommit_sha256,
    value.development_sha256,
    value.frozen_sha256,
    value.validation_sha256,
    value.smoke_sha256,
    value.adapter_sha256,
    value.plant_builder_sha256,
    value.validation_runner_sha256,
  )
  booleans = (
    value.development_validation_disjoint,
    value.model_structure_fixed_before_validation,
    value.validation_refit_performed,
    value.candidate_outputs_used_for_model_selection,
    value.deterministic_trace,
    value.deterministic_pose,
    value.acceptance_threshold_precommitted,
    value.descriptive_validation_only,
    value.primary_position_truth_independent,
    value.external_reproduction_established,
    value.current_platform_revalidated,
    value.real_vehicle_write,
    value.performance_acceptance,
    value.recommendation_authorized,
  )
  return (
    value.target_vehicle == TARGET_VEHICLE
    and value.model_family == MODEL_FAMILY
    and value.feature_names == MODEL_FEATURES
    and type(value.delay_frames) is int and 0 < value.delay_frames <= 100
    and type(value.model_source_commit) is str
    and re.fullmatch(r'[0-9a-f]{40}', value.model_source_commit) is not None
    and all(is_sha256(item) for item in hashes)
    and all(type(item) is bool for item in booleans)
    and type(value.development_route_count) is int and value.development_route_count > 0
    and type(value.validation_route_count) is int and value.validation_route_count > 0
    and type(value.validation_sequence_count) is int and value.validation_sequence_count > 0
    and type(value.eligible_pose_samples) is int and value.eligible_pose_samples > 0
    and type(value.horizons) is tuple
    and len(value.horizons) == len(REQUIRED_HORIZONS_S)
  )


def assess_plant_calibration(evidence) -> PlantCalibrationAssessment:
  """Verify aggregate evidence structure without granting calibration authority."""
  if not _evidence_shape_valid(evidence):
    return _blocked('INVALID_EVIDENCE')
  if any((
    evidence.real_vehicle_write,
    evidence.performance_acceptance,
    evidence.recommendation_authorized,
  )):
    return _blocked('FORBIDDEN_AUTHORITY')
  if tuple(item.horizon_s for item in evidence.horizons) != REQUIRED_HORIZONS_S:
    return _blocked('INVALID_HORIZON_EVIDENCE')
  if not all(_horizon_valid(item) for item in evidence.horizons):
    return _blocked('INVALID_HORIZON_EVIDENCE')
  if not finite_number(evidence.stability_radius) or not 0.0 <= evidence.stability_radius < 1.0:
    return _blocked('UNSTABLE_MODEL')
  if not evidence.development_validation_disjoint:
    return _blocked('DEVELOPMENT_VALIDATION_NOT_DISJOINT')
  if not evidence.model_structure_fixed_before_validation:
    return _blocked('MODEL_STRUCTURE_NOT_FIXED')
  if evidence.validation_refit_performed:
    return _blocked('VALIDATION_REFIT_DETECTED')
  if evidence.candidate_outputs_used_for_model_selection:
    return _blocked('VALIDATION_SELECTION_LEAKAGE')
  if not evidence.deterministic_trace or not evidence.deterministic_pose:
    return _blocked('NONDETERMINISTIC_SMOKE_EVIDENCE')

  blockers = []
  if not evidence.acceptance_threshold_precommitted:
    blockers.append('ACCEPTANCE_THRESHOLD_NOT_PRECOMMITTED')
  if evidence.descriptive_validation_only:
    blockers.append('DESCRIPTIVE_VALIDATION_ONLY')
  if not evidence.primary_position_truth_independent:
    blockers.append('PRIMARY_POSITION_TRUTH_NOT_INDEPENDENT')
  if not evidence.external_reproduction_established:
    blockers.append('EXTERNAL_REPRODUCTION_NOT_ESTABLISHED')
  if not evidence.current_platform_revalidated:
    blockers.append('CURRENT_PLATFORM_REVALIDATION_REQUIRED')
  blockers.append('QUALIFICATION_AUTHORITY_NOT_GRANTED')

  status = (
    'DESCRIPTIVE_CALIBRATION_EVIDENCE'
    if len(blockers) > 1
    else 'CALIBRATION_EVIDENCE_READY_FOR_REVIEW'
  )
  return PlantCalibrationAssessment(
    status=status,
    blockers=tuple(blockers),
    evidence_sha256=_canonical_sha256(asdict(evidence)),
    development_route_count=evidence.development_route_count,
    validation_route_count=evidence.validation_route_count,
    validation_sequence_count=evidence.validation_sequence_count,
    eligible_pose_samples=evidence.eligible_pose_samples,
    stability_radius=evidence.stability_radius,
    evidence_chain_verified=True,
    descriptive_validation_verified=True,
  )
