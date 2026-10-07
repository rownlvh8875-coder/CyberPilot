"""Frozen evidence coordinator for distinct curvature/yaw three-arm experiments.

This layer binds distinct arm declarations to one sealed independent-reference
file before any native worker starts. It does not authenticate reviewers, create
candidate profiles, tune thresholds, or grant runtime/vehicle authority.
"""
from dataclasses import asdict, dataclass, field
import hashlib
import json

from openpilot.tools.cyber_autotune.comparison import ARMS
from openpilot.tools.cyber_autotune.contracts import is_sha256
from openpilot.tools.cyber_autotune.curvature_yaw_comparison import declared_run_binding
from openpilot.tools.cyber_autotune.curvature_yaw_native_protocol import (
  decode_request,
  encode_request,
)
from openpilot.tools.cyber_autotune.curvature_yaw_native_runner import closed_loop_frames
from openpilot.tools.cyber_autotune.curvature_yaw_reference_input import (
  ReferenceEvidenceAdmission,
  ReferenceEvidenceGrant,
  retain_reference_evidence,
)
from openpilot.tools.cyber_autotune.curvature_yaw_three_arm import (
  CurvatureYawThreeArmExperiment,
  CurvatureYawThreeArmResult,
  run_three_arm_experiment,
)
from openpilot.tools.cyber_autotune.native_protocol import finite


@dataclass(frozen=True)
class ArmEvidenceDeclaration:
  arm: str
  request_sha256: str
  software_sha256: str
  profile_sha256: str
  configuration_sha256: str
  source_head: str
  opendbc_head: str


@dataclass(frozen=True)
class ThreeArmDeclarationManifest:
  version: int
  group_sha256: str
  review_sha256: str
  metric_pipeline_sha256: str
  metric_mask_sha256: str
  reference_evidence_sha256: str
  domain_sha256: str
  environment_sha256: str
  plant_calibration_sha256: str
  arms: tuple[ArmEvidenceDeclaration, ...]


@dataclass(frozen=True)
class FrozenThreeArmEvidenceContract:
  version: int
  declaration_manifest_sha256: str
  reference_file_sha256: str
  reference_evidence_sha256: str
  reference_manifest_sha256: str
  review_sha256: str
  require_distinct_arm_identities: bool = True


@dataclass(frozen=True)
class FrozenThreeArmRunResult:
  status: str
  blockers: tuple[str, ...]
  declaration_manifest_sha256: str | None = None
  reference_admission: ReferenceEvidenceAdmission | None = None
  three_arm_result: CurvatureYawThreeArmResult | None = None
  executed_runs: int = 0
  runtime_accepted: bool = field(default=False, init=False)
  promotable: bool = field(default=False, init=False)
  vehicle_activation_allowed: bool = field(default=False, init=False)


def _canonical(value) -> bytes:
  return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def _digest(value) -> str:
  return hashlib.sha256(_canonical(value)).hexdigest()


def declaration_manifest_sha256(manifest: ThreeArmDeclarationManifest) -> str:
  if type(manifest) is not ThreeArmDeclarationManifest:
    raise ValueError('INVALID_DECLARATION_MANIFEST')
  return _digest(asdict(manifest))


def _request_sha256(payload: bytes) -> str:
  return hashlib.sha256(payload).hexdigest()


def build_declaration_manifest(
  experiment: CurvatureYawThreeArmExperiment,
) -> ThreeArmDeclarationManifest:
  if type(experiment) is not CurvatureYawThreeArmExperiment:
    raise ValueError('INVALID_THREE_ARM_EXPERIMENT')
  declarations = {}
  for arm in experiment.arms:
    if arm.arm in declarations:
      raise ValueError('DUPLICATE_ARM_DECLARATION')
    request = decode_request(arm.request)
    payload = encode_request(request)
    if payload != arm.request:
      raise ValueError('NONCANONICAL_ARM_REQUEST')
    binding = declared_run_binding(
      request,
      experiment.domain,
      experiment.metric_contract,
      environment_sha256=experiment.environment_sha256,
    )
    declarations[arm.arm] = ArmEvidenceDeclaration(
      arm=arm.arm,
      request_sha256=_request_sha256(payload),
      software_sha256=binding.software_sha256,
      profile_sha256=binding.profile_sha256,
      configuration_sha256=binding.configuration_sha256,
      source_head=request['native']['source']['head'],
      opendbc_head=request['native']['source']['opendbc_head'],
    )
  if set(declarations) != set(ARMS):
    raise ValueError('INVALID_ARM_MATRIX')
  return ThreeArmDeclarationManifest(
    version=1,
    group_sha256=experiment.group_sha256,
    review_sha256=experiment.review_sha256,
    metric_pipeline_sha256=experiment.metric_contract.pipeline_sha256,
    metric_mask_sha256=experiment.metric_contract.mask_sha256,
    reference_evidence_sha256=experiment.metric_contract.reference_evidence_sha256,
    domain_sha256=experiment.domain.identity_sha256,
    environment_sha256=experiment.environment_sha256,
    plant_calibration_sha256=experiment.plant_calibration_sha256,
    arms=tuple(declarations[arm] for arm in ARMS),
  )


def _distinct_arm_identities(manifest: ThreeArmDeclarationManifest) -> bool:
  requests = {arm.request_sha256 for arm in manifest.arms}
  identities = {
    (
      arm.software_sha256,
      arm.profile_sha256,
      arm.configuration_sha256,
    )
    for arm in manifest.arms
  }
  configurations = {arm.configuration_sha256 for arm in manifest.arms}
  return (
    len(requests) == len(ARMS)
    and len(identities) == len(ARMS)
    and len(configurations) == len(ARMS)
  )


def _contract_valid(contract) -> bool:
  return (
    type(contract) is FrozenThreeArmEvidenceContract
    and type(contract.version) is int
    and contract.version == 1
    and all(is_sha256(value) for value in (
      contract.declaration_manifest_sha256,
      contract.reference_file_sha256,
      contract.reference_evidence_sha256,
      contract.reference_manifest_sha256,
      contract.review_sha256,
    ))
    and type(contract.require_distinct_arm_identities) is bool
  )


def _blocked(
  reason: str,
  *,
  manifest_sha256: str | None = None,
  reference_admission: ReferenceEvidenceAdmission | None = None,
  executed_runs: int = 0,
) -> FrozenThreeArmRunResult:
  return FrozenThreeArmRunResult(
    status='BLOCKED',
    blockers=(reason,),
    declaration_manifest_sha256=manifest_sha256,
    reference_admission=reference_admission,
    executed_runs=executed_runs,
  )


def run_frozen_three_arm_experiment(
  experiment: CurvatureYawThreeArmExperiment,
  evidence_contract: FrozenThreeArmEvidenceContract,
  reference_grant: ReferenceEvidenceGrant,
  *,
  timeout_s: float,
) -> FrozenThreeArmRunResult:
  """Run only after frozen distinct-arm and sealed-reference checks pass."""
  if not finite(timeout_s) or not 0 < timeout_s <= 60.0:
    raise ValueError('INVALID_TIMEOUT')
  if not _contract_valid(evidence_contract):
    return _blocked('INVALID_EVIDENCE_CONTRACT')
  try:
    manifest = build_declaration_manifest(experiment)
    manifest_digest = declaration_manifest_sha256(manifest)
  except ValueError as exc:
    return _blocked(str(exc))

  if manifest_digest != evidence_contract.declaration_manifest_sha256:
    return _blocked(
      'DECLARATION_MANIFEST_BINDING_MISMATCH',
      manifest_sha256=manifest_digest,
    )
  if (
    evidence_contract.require_distinct_arm_identities
    and not _distinct_arm_identities(manifest)
  ):
    return _blocked(
      'ARM_IDENTITIES_NOT_DISTINCT',
      manifest_sha256=manifest_digest,
    )
  if (
    reference_grant.file_sha256 != evidence_contract.reference_file_sha256
    or reference_grant.evidence_sha256
      != evidence_contract.reference_evidence_sha256
    or reference_grant.manifest_sha256
      != evidence_contract.reference_manifest_sha256
    or reference_grant.review_sha256 != evidence_contract.review_sha256
  ):
    return _blocked(
      'REFERENCE_GRANT_BINDING_MISMATCH',
      manifest_sha256=manifest_digest,
    )
  if (
    experiment.metric_contract.reference_evidence_sha256
      != evidence_contract.reference_evidence_sha256
    or experiment.coverage_policy.review_sha256
      != evidence_contract.review_sha256
    or experiment.review_sha256 != manifest.review_sha256
  ):
    return _blocked(
      'REFERENCE_OR_REVIEW_CONTRACT_MISMATCH',
      manifest_sha256=manifest_digest,
    )

  sample_count = len(closed_loop_frames(decode_request(experiment.arms[0].request)))
  try:
    with retain_reference_evidence(
      reference_grant,
      sample_count=sample_count,
      coverage_policy=experiment.coverage_policy,
    ) as (reference, admission):
      if (
        admission.evidence_sha256
          != evidence_contract.reference_evidence_sha256
        or admission.manifest_sha256
          != evidence_contract.reference_manifest_sha256
        or admission.review_sha256 != evidence_contract.review_sha256
        or not admission.sealed
      ):
        return _blocked(
          'REFERENCE_ADMISSION_BINDING_MISMATCH',
          manifest_sha256=manifest_digest,
          reference_admission=admission,
        )
      result = run_three_arm_experiment(
        experiment,
        reference,
        timeout_s=timeout_s,
      )
  except (OSError, ValueError):
    return _blocked(
      'REFERENCE_EVIDENCE_ADMISSION_FAILED',
      manifest_sha256=manifest_digest,
    )

  if result.status != 'COMPARISON_EVALUATED':
    return FrozenThreeArmRunResult(
      status='BLOCKED',
      blockers=result.blockers,
      declaration_manifest_sha256=manifest_digest,
      reference_admission=admission,
      three_arm_result=result,
      executed_runs=result.executed_runs,
    )
  return FrozenThreeArmRunResult(
    status='COMPARISON_EVALUATED',
    blockers=result.blockers,
    declaration_manifest_sha256=manifest_digest,
    reference_admission=admission,
    three_arm_result=result,
    executed_runs=result.executed_runs,
  )
