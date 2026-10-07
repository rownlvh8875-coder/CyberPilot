"""Exact three-arm coordinator for isolated curvature/yaw native experiments.

All arm declarations and common-basis identities are frozen before execution.
Each arm executes exactly twice in fresh child processes. Missing independent
reference evidence blocks before worker launch. This module has no vehicle,
CAN, Params, profile-write, shadow, or runtime activation authority.
"""
from dataclasses import dataclass, field

from openpilot.tools.cyber_autotune.comparison import (
  ARMS,
  ArmSpec,
  ComparisonAssessment,
  ComparisonGroup,
  ComparisonPolicy,
  RunReceipt,
  compare_receipts,
)
from openpilot.tools.cyber_autotune.contracts import MetricContract, finite_number, is_sha256
from openpilot.tools.cyber_autotune.curvature_yaw_comparison import (
  CurvatureYawReferenceEvidence,
  build_comparison_receipt,
  closed_loop_binding_for_comparison,
  declared_run_binding,
  reference_evidence_sha256,
  validate_reference_evidence,
)
from openpilot.tools.cyber_autotune.curvature_yaw_native_protocol import decode_request, encode_request
from openpilot.tools.cyber_autotune.curvature_yaw_native_runner import admit_native_transcript, closed_loop_frames, run_native_transcript
from openpilot.tools.cyber_autotune.lateral_closed_loop import ClosedLoopDomain
from openpilot.tools.cyber_autotune.native_runner import MAX_TIMEOUT_S
from openpilot.tools.cyber_autotune.preflight import CoveragePolicy


@dataclass(frozen=True)
class CurvatureYawArmDeclaration:
  arm: str
  request: bytes


@dataclass(frozen=True)
class CurvatureYawThreeArmExperiment:
  group_sha256: str
  review_sha256: str
  scenario_tags: tuple[str, ...]
  arms: tuple[CurvatureYawArmDeclaration, ...]
  domain: ClosedLoopDomain
  metric_contract: MetricContract
  coverage_policy: CoveragePolicy
  environment_sha256: str
  plant_calibration_sha256: str
  primary_minimum_improvement_m: float


@dataclass(frozen=True)
class CurvatureYawThreeArmResult:
  status: str
  blockers: tuple[str, ...]
  executed_runs: int = 0
  native_repeatable: bool = False
  receipts: tuple[RunReceipt, ...] = ()
  comparison: ComparisonAssessment | None = None
  runtime_accepted: bool = field(default=False, init=False)
  promotable: bool = field(default=False, init=False)
  vehicle_activation_allowed: bool = field(default=False, init=False)


def _blocked(reason: str, *, executed_runs: int = 0) -> CurvatureYawThreeArmResult:
  return CurvatureYawThreeArmResult('BLOCKED', (reason,), executed_runs=executed_runs)


def _prepare(
  experiment: CurvatureYawThreeArmExperiment,
  reference: CurvatureYawReferenceEvidence | None,
):
  if (
    type(experiment) is not CurvatureYawThreeArmExperiment
    or not is_sha256(experiment.group_sha256)
    or not is_sha256(experiment.review_sha256)
    or type(experiment.scenario_tags) is not tuple
    or not experiment.scenario_tags
    or type(experiment.arms) is not tuple
    or len(experiment.arms) != len(ARMS)
    or type(experiment.domain) is not ClosedLoopDomain
    or type(experiment.metric_contract) is not MetricContract
    or type(experiment.coverage_policy) is not CoveragePolicy
    or not is_sha256(experiment.environment_sha256)
    or not is_sha256(experiment.plant_calibration_sha256)
    or not finite_number(experiment.primary_minimum_improvement_m)
    or experiment.primary_minimum_improvement_m <= 0.0
  ):
    raise ValueError('INVALID_THREE_ARM_EXPERIMENT')
  if reference is None:
    raise ValueError('REFERENCE_EVIDENCE_REQUIRED')

  prepared = {}
  bindings = {}
  sample_count = None
  for declaration in experiment.arms:
    if (
      type(declaration) is not CurvatureYawArmDeclaration
      or type(declaration.arm) is not str
      or declaration.arm not in ARMS
      or declaration.arm in prepared
      or type(declaration.request) is not bytes
    ):
      raise ValueError('INVALID_ARM_DECLARATION')
    request = decode_request(declaration.request)
    payload = encode_request(request)
    if payload != declaration.request:
      raise ValueError('NONCANONICAL_ARM_REQUEST')
    frames = closed_loop_frames(request)
    if sample_count is None:
      sample_count = len(frames)
    elif len(frames) != sample_count:
      raise ValueError('COMMON_BASIS_MISMATCH')
    binding = declared_run_binding(
      request,
      experiment.domain,
      experiment.metric_contract,
      environment_sha256=experiment.environment_sha256,
    )
    prepared[declaration.arm] = request
    bindings[declaration.arm] = binding

  if set(prepared) != set(ARMS):
    raise ValueError('INVALID_ARM_MATRIX')
  validate_reference_evidence(reference, sample_count, experiment.coverage_policy)
  if experiment.metric_contract.reference_evidence_sha256 != reference_evidence_sha256(reference):
    raise ValueError('REFERENCE_EVIDENCE_BINDING_MISMATCH')

  common = (
    'inputs_sha256', 'reset_sha256', 'mask_sha256', 'metric_sha256',
    'plant_sha256', 'domain_sha256', 'environment_sha256', 'timebase_sha256',
  )
  baseline = bindings[ARMS[0]]
  if any(getattr(bindings[arm], name) != getattr(baseline, name) for arm in ARMS[1:] for name in common):
    raise ValueError('COMMON_BASIS_MISMATCH')

  arms = tuple(ArmSpec(arm, bindings[arm]) for arm in ARMS)
  group = ComparisonGroup(
    experiment.group_sha256,
    experiment.scenario_tags,
    experiment.metric_contract,
    arms,
  )
  policy = ComparisonPolicy(
    experiment.review_sha256,
    (group,),
    experiment.coverage_policy,
    experiment.primary_minimum_improvement_m,
  )
  policy_check = compare_receipts(policy, ())
  if any(issue.code == 'INVALID_POLICY' for issue in policy_check.issues):
    raise ValueError('INVALID_COMPARISON_POLICY')
  return prepared, group, policy


def run_three_arm_experiment(
  experiment: CurvatureYawThreeArmExperiment,
  reference: CurvatureYawReferenceEvidence | None,
  *,
  timeout_s: float,
) -> CurvatureYawThreeArmResult:
  """Run exact 3 arms x 2 repetitions and evaluate through compare_receipts."""
  if not finite_number(timeout_s) or not 0 < timeout_s <= MAX_TIMEOUT_S:
    raise ValueError('INVALID_TIMEOUT')
  try:
    prepared, group, policy = _prepare(experiment, reference)
  except ValueError as exc:
    return _blocked(str(exc))

  receipts = []
  executed = 0
  for arm_spec in group.arms:
    request = prepared[arm_spec.arm]
    pair = []
    for _repetition in (0, 1):
      result = run_native_transcript(request, timeout_s=timeout_s)
      executed += 1
      if type(result) is not dict or result.get('status') != 'COMPLETED':
        return _blocked(f'{arm_spec.arm}_NATIVE_EXECUTION_INCOMPLETE', executed_runs=executed)
      pair.append(result)
    if pair[0] != pair[1]:
      return _blocked(f'{arm_spec.arm}_NATIVE_REPEATABILITY_FAILED', executed_runs=executed)

    for repetition, result in enumerate(pair):
      try:
        closed_binding = closed_loop_binding_for_comparison(
          arm_spec.binding,
          result,
          plant_calibration_sha256=experiment.plant_calibration_sha256,
        )
        admitted = admit_native_transcript(
          request,
          result,
          experiment.domain,
          closed_binding,
          arm=arm_spec.arm,
        )
        if admitted.status != 'STRUCTURAL_ADMISSION' or not admitted.structural_admission_pass:
          return _blocked(f'{arm_spec.arm}_CLOSED_LOOP_ADMISSION_FAILED', executed_runs=executed)
        receipts.append(build_comparison_receipt(
          request,
          result,
          admitted,
          group,
          arm_spec,
          repetition,
          reference,
          experiment.coverage_policy,
        ))
      except ValueError:
        return _blocked(f'{arm_spec.arm}_COMPARISON_RECEIPT_FAILED', executed_runs=executed)

  comparison = compare_receipts(policy, tuple(receipts))
  return CurvatureYawThreeArmResult(
    status='COMPARISON_EVALUATED',
    blockers=tuple(issue.code for issue in comparison.issues),
    executed_runs=executed,
    native_repeatable=True,
    receipts=tuple(receipts),
    comparison=comparison,
  )
