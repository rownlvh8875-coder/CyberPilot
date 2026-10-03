"""Three-arm asserted-receipt comparison, NOT a native execution authenticator.

Reuses the frozen v2 metric gate. No file IO, controller callbacks or promotion.
All-local success remains REVALIDATION_REQUIRED: producer truth, uncertainty and
longitudinal integration are not implemented by this lateral comparison layer.
"""
from dataclasses import dataclass, field, fields
from fractions import Fraction

from openpilot.tools.cyber_autotune.contracts import MetricBatch, MetricContract, finite_number, is_sha256
from openpilot.tools.cyber_autotune.preflight import CoveragePolicy, REQUIRED_STRATA, check_metric_pair


ARMS = ('UPSTREAM_BASELINE', 'CYBER_CURRENT', 'CYBER_CANDIDATE')
SCENARIO_TAGS = frozenset({'straight', 'gentle_curve', 'sharp_curve', 'ramp', 'urban', 'highway', 'stop_and_go', 'cut_in'})
HARD_VIOLATIONS = frozenset({'ACTUATOR_LIMIT', 'INVALID_VEHICLE_STATE', 'PLANT_DOMAIN', 'SAFETY_BOUNDARY'})
MAX_COMPARISON_GROUPS = 64  # Tool resource cap, not a scientific sample threshold.
COMMON_BINDINGS = ('inputs_sha256', 'reset_sha256', 'mask_sha256', 'metric_sha256', 'plant_sha256',
                   'domain_sha256', 'environment_sha256', 'timebase_sha256')


@dataclass(frozen=True)
class RunBinding:
  software_sha256: str
  profile_sha256: str
  configuration_sha256: str
  inputs_sha256: str
  reset_sha256: str
  mask_sha256: str
  adapter_sha256: str
  metric_sha256: str
  plant_sha256: str
  domain_sha256: str
  environment_sha256: str
  timebase_sha256: str


@dataclass(frozen=True)
class ArmSpec:
  arm: str
  binding: RunBinding


@dataclass(frozen=True)
class ComparisonGroup:
  group_sha256: str
  scenario_tags: tuple[str, ...]
  contract: MetricContract
  arms: tuple[ArmSpec, ...]


@dataclass(frozen=True)
class ComparisonPolicy:
  review_sha256: str
  groups: tuple[ComparisonGroup, ...]
  coverage_policy: CoveragePolicy
  primary_minimum_improvement_m: float


@dataclass(frozen=True)
class RunReceipt:
  group_sha256: str
  arm: str
  repetition: int
  binding: RunBinding
  trace_sha256: str | None
  outcome: str
  metrics: MetricBatch | None
  coverage: tuple[tuple[str, int], ...]
  hard_violations: tuple[str, ...]


@dataclass(frozen=True)
class ComparisonIssue:
  code: str
  group_sha256: str | None = None
  arm: str | None = None
  detail: str | None = None


@dataclass(frozen=True)
class ComparisonAssessment:
  status: str
  issues: tuple[ComparisonIssue, ...]
  expected_runs: int
  received_runs: int
  repeatable_groups: int
  local_nonregression_pass: bool
  primary_improvement_pass: bool
  review_sha256: str | None
  group_sha256s: tuple[str, ...]
  source_sha256s: tuple[str, ...]
  offline_evaluable: bool = field(default=False, init=False)
  runtime_accepted: bool = field(default=False, init=False)
  promotable: bool = field(default=False, init=False)


def _hash(value) -> bool:
  return type(value) is str and is_sha256(value)


def _binding_valid(binding) -> bool:
  return type(binding) is RunBinding and all(_hash(getattr(binding, item.name)) for item in fields(binding))


def _group_valid(group) -> bool:
  if (type(group) is not ComparisonGroup or not _hash(group.group_sha256) or type(group.contract) is not MetricContract
      or type(group.scenario_tags) is not tuple or not group.scenario_tags
      or not all(type(tag) is str and tag in SCENARIO_TAGS for tag in group.scenario_tags)
      or len(set(group.scenario_tags)) != len(group.scenario_tags) or type(group.arms) is not tuple or len(group.arms) != len(ARMS)):
    return False
  if not all(type(arm) is ArmSpec and type(arm.arm) is str and arm.arm in ARMS and _binding_valid(arm.binding) for arm in group.arms):
    return False
  if {arm.arm for arm in group.arms} != set(ARMS):
    return False
  reference = group.arms[0].binding
  if any(getattr(arm.binding, name) != getattr(reference, name) for arm in group.arms for name in COMMON_BINDINGS):
    return False
  return (reference.inputs_sha256 == group.contract.inputs_sha256 and reference.reset_sha256 == group.contract.reset_policy_sha256
          and reference.mask_sha256 == group.contract.mask_sha256 and reference.metric_sha256 == group.contract.pipeline_sha256)


def _policy_valid(policy) -> bool:
  return (type(policy) is ComparisonPolicy and _hash(policy.review_sha256) and type(policy.groups) is tuple
          and 0 < len(policy.groups) <= MAX_COMPARISON_GROUPS and type(policy.coverage_policy) is CoveragePolicy
          and finite_number(policy.primary_minimum_improvement_m) and policy.primary_minimum_improvement_m > 0
          and all(_group_valid(group) for group in policy.groups)
          and len({group.group_sha256 for group in policy.groups}) == len(policy.groups))


def _coverage_valid(coverage) -> bool:
  if type(coverage) is not tuple or len(coverage) != len(REQUIRED_STRATA):
    return False
  if not all(type(item) is tuple and len(item) == 2 and type(item[0]) is str and item[0] in REQUIRED_STRATA
             and type(item[1]) is int and finite_number(item[1]) and item[1] >= 0 for item in coverage):
    return False
  return {item[0] for item in coverage} == REQUIRED_STRATA


def _receipt_valid(receipt) -> bool:
  if (type(receipt) is not RunReceipt or not _hash(receipt.group_sha256) or type(receipt.arm) is not str or receipt.arm not in ARMS
      or type(receipt.repetition) is not int or receipt.repetition not in (0, 1) or not _binding_valid(receipt.binding)
      or type(receipt.outcome) is not str or receipt.outcome not in ('COMPLETED', 'FAILED', 'TIMEOUT')
      or type(receipt.hard_violations) is not tuple
      or not all(type(code) is str and code in HARD_VIOLATIONS for code in receipt.hard_violations)
      or len(set(receipt.hard_violations)) != len(receipt.hard_violations)):
    return False
  if receipt.outcome == 'COMPLETED':
    return _hash(receipt.trace_sha256) and type(receipt.metrics) is MetricBatch and _coverage_valid(receipt.coverage)
  return (receipt.trace_sha256 is None or _hash(receipt.trace_sha256)) and receipt.metrics is None and receipt.coverage == ()


def compare_receipts(policy: ComparisonPolicy, receipts: tuple[RunReceipt, ...]) -> ComparisonAssessment:
  """Compare exact declared groups without pooling statistics or opening artifacts.

Policy hashes/labels are assertions. Each group must already have complete metrics
and coverage calculated by its producer. Missing metrics are never zero-filled.
Only primary RMSE improvement in at least one predeclared group is tested here;
uncertainty and corpus qualification remain separate, mandatory missing gates.
"""
  count = len(receipts) if type(receipts) is tuple else 0
  if not _policy_valid(policy):
    return ComparisonAssessment('REVALIDATION_REQUIRED', (ComparisonIssue('INVALID_POLICY'),), 0, count, 0, False, False, None, (), ())
  expected_count = len(policy.groups) * len(ARMS) * 2
  issues = []
  repeatable = 0

  def result(status='REVALIDATION_REQUIRED', local=False, primary=False):
    return ComparisonAssessment(status, tuple(issues), expected_count, count, repeatable, local, primary, policy.review_sha256,
                                tuple(group.group_sha256 for group in policy.groups),
                                tuple(sorted({arm.binding.software_sha256 for group in policy.groups for arm in group.arms})))

  if type(receipts) is not tuple or count != expected_count:
    issues.append(ComparisonIssue('RUN_CARDINALITY_MISMATCH'))
    return result()
  if not all(_receipt_valid(receipt) for receipt in receipts):
    issues.append(ComparisonIssue('INVALID_RECEIPT'))
    return result()
  expected = {(group.group_sha256, arm.arm): (group, arm) for group in policy.groups for arm in group.arms}
  runs = {}
  for receipt in receipts:
    key = (receipt.group_sha256, receipt.arm, receipt.repetition)
    if key[:2] not in expected or key in runs:
      issues.append(ComparisonIssue('UNEXPECTED_OR_DUPLICATE_RUN'))
      return result()
    group, arm = expected[key[:2]]
    if receipt.binding != arm.binding:
      issues.append(ComparisonIssue('RUN_BINDING_MISMATCH', group.group_sha256, arm.arm))
    if receipt.metrics is not None and receipt.metrics.contract != group.contract:
      issues.append(ComparisonIssue('METRIC_CONTRACT_MISMATCH', group.group_sha256, arm.arm))
    runs[key] = receipt
  if issues:
    return result()

  # Exact cardinality, known unique keys and two allowed repetitions ensure no holes.
  ordered = [runs[(group.group_sha256, arm, repetition)] for group in policy.groups for arm in ARMS for repetition in (0, 1)]
  for receipt in ordered:
    for violation in receipt.hard_violations:
      issues.append(ComparisonIssue('HARD_CONSTRAINT_VIOLATION', receipt.group_sha256, receipt.arm, violation))
  if issues:
    return result('FAIL')
  for receipt in ordered:
    if receipt.outcome != 'COMPLETED':
      issues.append(ComparisonIssue(f'RUN_{receipt.outcome}', receipt.group_sha256, receipt.arm))
  if issues:
    return result()
  for receipt in ordered:
    local_check = check_metric_pair(receipt.metrics, receipt.metrics, policy.coverage_policy,
                                   dict(receipt.coverage), dict(receipt.coverage))
    if not local_check.metric_gate_pass:
      issues.extend(ComparisonIssue('INVALID_METRIC_OR_COVERAGE', receipt.group_sha256, receipt.arm, code) for code in local_check.reasons)
  if issues:
    return result()

  for group in policy.groups:
    group_repeatable = True
    for arm in ARMS:
      first, second = (runs[(group.group_sha256, arm, repetition)] for repetition in (0, 1))
      if (first.trace_sha256, first.metrics, first.coverage, first.hard_violations) != (
          second.trace_sha256, second.metrics, second.coverage, second.hard_violations):
        code = 'CANDIDATE_REPEATABILITY_FAILED' if arm == 'CYBER_CANDIDATE' else 'BASELINE_AA_FAILED'
        issues.append(ComparisonIssue(code, group.group_sha256, arm))
        group_repeatable = False
    repeatable += int(group_repeatable)
  if issues:
    return result('FAIL')

  blocked, regressed, improved = False, False, False
  for group in policy.groups:
    upstream, current, candidate = (runs[(group.group_sha256, arm, 0)] for arm in ARMS)
    diagnostic = check_metric_pair(upstream.metrics, current.metrics, policy.coverage_policy, dict(upstream.coverage), dict(current.coverage))
    if diagnostic.status == 'BLOCKED':
      blocked = True
      issues.extend(ComparisonIssue('COMPARISON_BASIS_MISMATCH', group.group_sha256, 'CYBER_CURRENT', code) for code in diagnostic.reasons)
    elif not diagnostic.metric_gate_pass:
      issues.extend(ComparisonIssue('CURRENT_REGRESSION_DIAGNOSTIC', group.group_sha256, 'CYBER_CURRENT', code) for code in diagnostic.reasons)
    for reference in (upstream, current):
      gate = check_metric_pair(reference.metrics, candidate.metrics, policy.coverage_policy, dict(reference.coverage), dict(candidate.coverage))
      if gate.status == 'BLOCKED':
        blocked = True
        code = 'COMPARISON_BASIS_MISMATCH'
      elif gate.status == 'REJECTED':
        regressed = True
        code = 'CANDIDATE_REGRESSION'
      else:
        continue
      issues.extend(ComparisonIssue(code, group.group_sha256, candidate.arm, f'{reference.arm}:{reason}') for reason in gate.reasons)
    center_errors = [next(item.rmse for item in run.metrics.metrics if item.name == 'lane_center_offset')
                     for run in (upstream, current, candidate)]
    candidate_error = Fraction(str(center_errors[-1]))
    minimum_improvement = Fraction(str(policy.primary_minimum_improvement_m))
    improved |= all(Fraction(str(value)) - candidate_error >= minimum_improvement for value in center_errors[:2])
  if blocked:
    return result()
  if regressed:
    return result('FAIL')
  if not improved:
    issues.append(ComparisonIssue('NO_PRIMARY_IMPROVEMENT'))
    return result('FAIL', local=True)
  issues.extend(ComparisonIssue(code) for code in ('EVIDENCE_AUTHENTICITY_PENDING', 'UNCERTAINTY_VALIDATION_PENDING', 'LONGITUDINAL_ADAPTER_PENDING'))
  return result(local=True, primary=True)
