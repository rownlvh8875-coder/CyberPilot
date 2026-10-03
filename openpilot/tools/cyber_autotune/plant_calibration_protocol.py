"""Prospective plant-calibration protocol and fail-closed assessment.

The module evaluates aggregate receipts collected after a frozen protocol. It
never opens logs, fits models, chooses thresholds, writes profiles, accesses CAN,
or grants qualification, runtime, promotion, or vehicle authority.
"""
from dataclasses import asdict, dataclass, field
from datetime import datetime, UTC
import hashlib
import json
import re

from openpilot.tools.cyber_autotune.contracts import finite_number, is_sha256


REQUIRED_HORIZONS_S = (1.0, 5.0, 10.0)


@dataclass(frozen=True)
class HorizonAcceptance:
  horizon_s: float
  minimum_window_count: int
  minimum_sample_count: int
  maximum_yaw_rate_rmse_rad_s: float
  minimum_yaw_rate_correlation: float
  maximum_heading_endpoint_rmse_rad: float
  maximum_path_endpoint_rmse_m: float
  maximum_path_xy_rmse_m: float


@dataclass(frozen=True)
class ProspectiveCalibrationProtocol:
  schema_version: int
  protocol_id: str
  frozen_at_utc: str
  target_vehicle: str
  model_family: str
  expected_model_sha256: str
  expected_adapter_sha256: str
  expected_plant_builder_sha256: str
  expected_validation_runner_sha256: str
  minimum_validation_routes: int
  minimum_validation_sequences: int
  minimum_eligible_pose_samples: int
  maximum_stability_radius: float
  require_independent_primary_position_truth: bool
  require_external_reproduction_for_review: bool
  horizons: tuple[HorizonAcceptance, ...]


@dataclass(frozen=True)
class ProspectiveHorizonEvidence:
  horizon_s: float
  window_count: int
  sample_count: int
  yaw_rate_rmse_rad_s: float
  yaw_rate_correlation: float
  heading_endpoint_rmse_rad: float
  path_endpoint_rmse_m: float
  path_xy_rmse_m: float


@dataclass(frozen=True)
class ProspectiveCalibrationEvidence:
  protocol_sha256: str
  data_manifest_sha256: str
  source_commit: str
  target_vehicle: str
  model_family: str
  model_sha256: str
  adapter_sha256: str
  plant_builder_sha256: str
  validation_runner_sha256: str
  collection_started_at_utc: str
  collection_ended_at_utc: str
  manifest_frozen_at_utc: str
  evaluation_started_at_utc: str
  semantic_content_opened_before_manifest: bool
  validation_route_count: int
  validation_sequence_count: int
  eligible_pose_samples: int
  stability_radius: float
  independent_primary_position_truth: bool
  external_reproduction_established: bool
  validation_refit_performed: bool
  candidate_outputs_used_for_model_selection: bool
  real_vehicle_write: bool
  performance_acceptance: bool
  recommendation_authorized: bool
  horizons: tuple[ProspectiveHorizonEvidence, ...]


@dataclass(frozen=True)
class ProspectiveCalibrationAssessment:
  status: str
  blockers: tuple[str, ...]
  protocol_sha256: str | None = None
  evidence_sha256: str | None = None
  failed_horizons: tuple[float, ...] = ()
  protocol_verified: bool = False
  prospective_revalidation_pass: bool = False
  plant_calibration_qualified: bool = field(default=False, init=False)
  runtime_accepted: bool = field(default=False, init=False)
  promotable: bool = field(default=False, init=False)


def _canonical_sha256(value) -> str:
  raw = json.dumps(
    value, sort_keys=True, separators=(',', ':'), allow_nan=False,
  ).encode()
  return hashlib.sha256(raw).hexdigest()


def protocol_sha256(protocol: ProspectiveCalibrationProtocol) -> str:
  return _canonical_sha256(asdict(protocol))


def _parse_utc(value) -> datetime | None:
  if type(value) is not str:
    return None
  try:
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
  except ValueError:
    return None
  if parsed.tzinfo is None:
    return None
  return parsed.astimezone(UTC)


def _threshold_valid(item) -> bool:
  return (
    type(item) is HorizonAcceptance
    and finite_number(item.horizon_s) and item.horizon_s > 0.0
    and type(item.minimum_window_count) is int and item.minimum_window_count > 0
    and type(item.minimum_sample_count) is int and item.minimum_sample_count > 0
    and all(finite_number(value) and value >= 0.0 for value in (
      item.maximum_yaw_rate_rmse_rad_s,
      item.maximum_heading_endpoint_rmse_rad,
      item.maximum_path_endpoint_rmse_m,
      item.maximum_path_xy_rmse_m,
    ))
    and finite_number(item.minimum_yaw_rate_correlation)
    and -1.0 <= item.minimum_yaw_rate_correlation <= 1.0
  )


def _policy_valid(policy) -> bool:
  return (
    type(policy) is ProspectiveCalibrationProtocol
    and type(policy.schema_version) is int and policy.schema_version == 1
    and type(policy.protocol_id) is str
    and re.fullmatch(r'[A-Z0-9_]{3,64}', policy.protocol_id) is not None
    and _parse_utc(policy.frozen_at_utc) is not None
    and type(policy.target_vehicle) is str and bool(policy.target_vehicle)
    and type(policy.model_family) is str and bool(policy.model_family)
    and all(is_sha256(value) for value in (
      policy.expected_model_sha256,
      policy.expected_adapter_sha256,
      policy.expected_plant_builder_sha256,
      policy.expected_validation_runner_sha256,
    ))
    and type(policy.minimum_validation_routes) is int
    and policy.minimum_validation_routes > 0
    and type(policy.minimum_validation_sequences) is int
    and policy.minimum_validation_sequences > 0
    and type(policy.minimum_eligible_pose_samples) is int
    and policy.minimum_eligible_pose_samples > 0
    and finite_number(policy.maximum_stability_radius)
    and 0.0 < policy.maximum_stability_radius < 1.0
    and type(policy.require_independent_primary_position_truth) is bool
    and policy.require_independent_primary_position_truth
    and type(policy.require_external_reproduction_for_review) is bool
    and policy.require_external_reproduction_for_review
    and type(policy.horizons) is tuple
    and len(policy.horizons) == len(REQUIRED_HORIZONS_S)
    and tuple(item.horizon_s for item in policy.horizons) == REQUIRED_HORIZONS_S
    and all(_threshold_valid(item) for item in policy.horizons)
  )


def _horizon_evidence_valid(item) -> bool:
  return (
    type(item) is ProspectiveHorizonEvidence
    and finite_number(item.horizon_s) and item.horizon_s > 0.0
    and type(item.window_count) is int and item.window_count > 0
    and type(item.sample_count) is int and item.sample_count > 0
    and all(finite_number(value) and value >= 0.0 for value in (
      item.yaw_rate_rmse_rad_s,
      item.heading_endpoint_rmse_rad,
      item.path_endpoint_rmse_m,
      item.path_xy_rmse_m,
    ))
    and finite_number(item.yaw_rate_correlation)
    and -1.0 <= item.yaw_rate_correlation <= 1.0
  )


def _evidence_valid(evidence) -> bool:
  if type(evidence) is not ProspectiveCalibrationEvidence:
    return False
  timestamps = (
    evidence.collection_started_at_utc,
    evidence.collection_ended_at_utc,
    evidence.manifest_frozen_at_utc,
    evidence.evaluation_started_at_utc,
  )
  booleans = (
    evidence.semantic_content_opened_before_manifest,
    evidence.independent_primary_position_truth,
    evidence.external_reproduction_established,
    evidence.validation_refit_performed,
    evidence.candidate_outputs_used_for_model_selection,
    evidence.real_vehicle_write,
    evidence.performance_acceptance,
    evidence.recommendation_authorized,
  )
  return (
    is_sha256(evidence.protocol_sha256)
    and is_sha256(evidence.data_manifest_sha256)
    and type(evidence.source_commit) is str
    and re.fullmatch(r'[0-9a-f]{40}', evidence.source_commit) is not None
    and type(evidence.target_vehicle) is str and bool(evidence.target_vehicle)
    and type(evidence.model_family) is str and bool(evidence.model_family)
    and all(is_sha256(value) for value in (
      evidence.model_sha256,
      evidence.adapter_sha256,
      evidence.plant_builder_sha256,
      evidence.validation_runner_sha256,
    ))
    and all(_parse_utc(value) is not None for value in timestamps)
    and all(type(value) is bool for value in booleans)
    and type(evidence.validation_route_count) is int
    and evidence.validation_route_count > 0
    and type(evidence.validation_sequence_count) is int
    and evidence.validation_sequence_count > 0
    and type(evidence.eligible_pose_samples) is int
    and evidence.eligible_pose_samples > 0
    and finite_number(evidence.stability_radius)
    and type(evidence.horizons) is tuple
    and len(evidence.horizons) == len(REQUIRED_HORIZONS_S)
    and tuple(item.horizon_s for item in evidence.horizons) == REQUIRED_HORIZONS_S
    and all(_horizon_evidence_valid(item) for item in evidence.horizons)
  )


def _blocked(reason: str, *, protocol_digest: str | None = None,
             failed_horizons: tuple[float, ...] = ()) -> ProspectiveCalibrationAssessment:
  return ProspectiveCalibrationAssessment(
    status='BLOCKED',
    blockers=(reason,),
    protocol_sha256=protocol_digest,
    failed_horizons=failed_horizons,
    protocol_verified=protocol_digest is not None,
  )


def _horizon_pass(threshold: HorizonAcceptance,
                  evidence: ProspectiveHorizonEvidence) -> bool:
  return (
    evidence.horizon_s == threshold.horizon_s
    and evidence.window_count >= threshold.minimum_window_count
    and evidence.sample_count >= threshold.minimum_sample_count
    and evidence.yaw_rate_rmse_rad_s
      <= threshold.maximum_yaw_rate_rmse_rad_s
    and evidence.yaw_rate_correlation
      >= threshold.minimum_yaw_rate_correlation
    and evidence.heading_endpoint_rmse_rad
      <= threshold.maximum_heading_endpoint_rmse_rad
    and evidence.path_endpoint_rmse_m
      <= threshold.maximum_path_endpoint_rmse_m
    and evidence.path_xy_rmse_m <= threshold.maximum_path_xy_rmse_m
  )


def assess_prospective_calibration(
  protocol: ProspectiveCalibrationProtocol,
  evidence: ProspectiveCalibrationEvidence,
) -> ProspectiveCalibrationAssessment:
  """Evaluate future aggregate evidence against a pre-frozen protocol."""
  if not _policy_valid(protocol):
    return _blocked('INVALID_POLICY')
  protocol_digest = protocol_sha256(protocol)
  if not _evidence_valid(evidence):
    return _blocked('INVALID_EVIDENCE', protocol_digest=protocol_digest)

  if (
    evidence.protocol_sha256 != protocol_digest
    or evidence.target_vehicle != protocol.target_vehicle
    or evidence.model_family != protocol.model_family
    or evidence.model_sha256 != protocol.expected_model_sha256
    or evidence.adapter_sha256 != protocol.expected_adapter_sha256
    or evidence.plant_builder_sha256 != protocol.expected_plant_builder_sha256
    or evidence.validation_runner_sha256
      != protocol.expected_validation_runner_sha256
  ):
    return _blocked(
      'EVIDENCE_BINDING_MISMATCH', protocol_digest=protocol_digest,
    )

  frozen = _parse_utc(protocol.frozen_at_utc)
  started = _parse_utc(evidence.collection_started_at_utc)
  ended = _parse_utc(evidence.collection_ended_at_utc)
  manifest = _parse_utc(evidence.manifest_frozen_at_utc)
  evaluation = _parse_utc(evidence.evaluation_started_at_utc)
  assert frozen is not None and started is not None and ended is not None
  assert manifest is not None and evaluation is not None

  if started <= frozen:
    return _blocked(
      'DATA_PREDATES_PROTOCOL_FREEZE', protocol_digest=protocol_digest,
    )
  if not started <= ended <= manifest <= evaluation:
    return _blocked(
      'INVALID_EVIDENCE_TIMELINE', protocol_digest=protocol_digest,
    )
  if evidence.semantic_content_opened_before_manifest:
    return _blocked(
      'CONTENT_OPENED_BEFORE_MANIFEST_FREEZE',
      protocol_digest=protocol_digest,
    )
  if any((
    evidence.real_vehicle_write,
    evidence.performance_acceptance,
    evidence.recommendation_authorized,
  )):
    return _blocked('FORBIDDEN_AUTHORITY', protocol_digest=protocol_digest)
  if evidence.validation_refit_performed:
    return _blocked(
      'VALIDATION_REFIT_DETECTED', protocol_digest=protocol_digest,
    )
  if evidence.candidate_outputs_used_for_model_selection:
    return _blocked(
      'VALIDATION_SELECTION_LEAKAGE', protocol_digest=protocol_digest,
    )
  if (
    evidence.validation_route_count < protocol.minimum_validation_routes
    or evidence.validation_sequence_count
      < protocol.minimum_validation_sequences
    or evidence.eligible_pose_samples
      < protocol.minimum_eligible_pose_samples
  ):
    return _blocked(
      'INSUFFICIENT_VALIDATION_COVERAGE', protocol_digest=protocol_digest,
    )
  if not 0.0 <= evidence.stability_radius <= protocol.maximum_stability_radius:
    return _blocked('UNSTABLE_MODEL', protocol_digest=protocol_digest)
  if (
    protocol.require_independent_primary_position_truth
    and not evidence.independent_primary_position_truth
  ):
    return _blocked(
      'PRIMARY_POSITION_TRUTH_NOT_INDEPENDENT',
      protocol_digest=protocol_digest,
    )

  failed_horizons = tuple(
    threshold.horizon_s
    for threshold, observed in zip(
      protocol.horizons, evidence.horizons, strict=True,
    )
    if not _horizon_pass(threshold, observed)
  )
  if failed_horizons:
    return _blocked(
      'HORIZON_THRESHOLD_FAILED',
      protocol_digest=protocol_digest,
      failed_horizons=failed_horizons,
    )

  evidence_digest = _canonical_sha256(asdict(evidence))
  if (
    protocol.require_external_reproduction_for_review
    and not evidence.external_reproduction_established
  ):
    return ProspectiveCalibrationAssessment(
      status='PROSPECTIVE_INTERNAL_REVALIDATION_PASS',
      blockers=(
        'EXTERNAL_REPRODUCTION_NOT_ESTABLISHED',
        'QUALIFICATION_AUTHORITY_NOT_GRANTED',
      ),
      protocol_sha256=protocol_digest,
      evidence_sha256=evidence_digest,
      failed_horizons=(),
      protocol_verified=True,
      prospective_revalidation_pass=True,
    )
  return ProspectiveCalibrationAssessment(
    status='CALIBRATION_EVIDENCE_READY_FOR_REVIEW',
    blockers=('QUALIFICATION_AUTHORITY_NOT_GRANTED',),
    protocol_sha256=protocol_digest,
    evidence_sha256=evidence_digest,
    failed_horizons=(),
    protocol_verified=True,
    prospective_revalidation_pass=True,
  )
