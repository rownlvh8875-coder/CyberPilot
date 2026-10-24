"""Frozen relative gate for synthetic lateral candidate comparisons.

A pass is an offline development diagnostic only. This module cannot qualify
physical performance, generate a candidate, promote shadow, or authorize runtime.
"""
from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path

from openpilot.tools.cyber_autotune.contracts import finite_number, is_sha256
from openpilot.tools.cyber_autotune.synthetic_lateral_closed_loop import (
  SyntheticClosedLoopMatrixReport,
  SyntheticClosedLoopScenarioResult,
)


LOWER_IS_BETTER_METRICS = (
  'lateral_error_rmse_m',
  'maximum_abs_lateral_error_m',
  'maximum_abs_heading_error_rad',
  'steering_jerk_rmse_deg_s3',
  'saturation_ratio',
  'maximum_abs_requested_torque',
)
SYMMETRY_METRICS = LOWER_IS_BETTER_METRICS
FAULT_IDS = frozenset({'sensor_dropout', 'timebase_gap'})


@dataclass(frozen=True)
class SyntheticGatePolicy:
  policy_sha256: str
  baseline_artifact_sha256: str
  baseline_internal_report_sha256: str
  required_scenario_ids: tuple[str, ...]
  stress_scenario_ids: tuple[str, ...]
  symmetry_pairs: tuple[tuple[str, str], ...]
  maximum_relative_lateral_rmse_regression: float
  maximum_absolute_lateral_rmse_regression_m: float
  maximum_relative_lateral_max_regression: float
  maximum_absolute_lateral_max_regression_m: float
  maximum_relative_heading_error_regression: float
  maximum_absolute_heading_error_regression_rad: float
  maximum_relative_jerk_regression: float
  maximum_absolute_jerk_regression_deg_s3: float
  maximum_absolute_saturation_regression: float
  maximum_absolute_requested_torque_regression: float
  maximum_command_reversal_increase: int
  maximum_inactive_requested_torque_abs: float
  left_right_symmetry_absolute_tolerance: float
  minimum_stress_improvement_fraction: float
  require_every_stress_scenario_improved: bool
  improvement_metrics: tuple[str, ...]


@dataclass(frozen=True)
class SyntheticCandidateGateResult:
  status: str
  blockers: tuple[str, ...]
  regressions: tuple[str, ...] = ()
  policy_sha256: str | None = None
  compared_scenario_count: int = 0
  no_regression_pass: bool = False
  improvement_pass: bool = False
  improved_stress_scenarios: tuple[str, ...] = ()
  symmetry_pass: bool = False
  fault_identity_pass: bool = False
  performance_qualified: bool = field(default=False, init=False)
  candidate_generation_allowed: bool = field(default=False, init=False)
  shadow_promotion_allowed: bool = field(default=False, init=False)
  runtime_accepted: bool = field(default=False, init=False)
  promotable: bool = field(default=False, init=False)


def _blocked(reason: str, policy_sha256: str | None = None) -> SyntheticCandidateGateResult:
  return SyntheticCandidateGateResult('BLOCKED', (reason,), policy_sha256=policy_sha256)


def _canonical_policy_valid(policy) -> bool:
  if type(policy) is not SyntheticGatePolicy:
    return False
  floats = (
    policy.maximum_relative_lateral_rmse_regression,
    policy.maximum_absolute_lateral_rmse_regression_m,
    policy.maximum_relative_lateral_max_regression,
    policy.maximum_absolute_lateral_max_regression_m,
    policy.maximum_relative_heading_error_regression,
    policy.maximum_absolute_heading_error_regression_rad,
    policy.maximum_relative_jerk_regression,
    policy.maximum_absolute_jerk_regression_deg_s3,
    policy.maximum_absolute_saturation_regression,
    policy.maximum_absolute_requested_torque_regression,
    policy.maximum_inactive_requested_torque_abs,
    policy.left_right_symmetry_absolute_tolerance,
    policy.minimum_stress_improvement_fraction,
  )
  return (
    is_sha256(policy.policy_sha256)
    and is_sha256(policy.baseline_artifact_sha256)
    and is_sha256(policy.baseline_internal_report_sha256)
    and type(policy.required_scenario_ids) is tuple
    and len(policy.required_scenario_ids) == len(set(policy.required_scenario_ids))
    and type(policy.stress_scenario_ids) is tuple
    and set(policy.stress_scenario_ids) <= set(policy.required_scenario_ids)
    and type(policy.symmetry_pairs) is tuple
    and all(type(pair) is tuple and len(pair) == 2 for pair in policy.symmetry_pairs)
    and all(set(pair) <= set(policy.required_scenario_ids) for pair in policy.symmetry_pairs)
    and all(finite_number(value) and value >= 0.0 for value in floats)
    and 0.0 < policy.minimum_stress_improvement_fraction < 1.0
    and type(policy.maximum_command_reversal_increase) is int
    and policy.maximum_command_reversal_increase >= 0
    and type(policy.require_every_stress_scenario_improved) is bool
    and type(policy.improvement_metrics) is tuple
    and set(policy.improvement_metrics) <= set(LOWER_IS_BETTER_METRICS)
  )


def load_policy(path: Path, *, expected_sha256: str) -> SyntheticGatePolicy:
  if not isinstance(path, Path) or not is_sha256(expected_sha256):
    raise ValueError('INVALID_POLICY_BINDING')
  try:
    raw = path.read_bytes()
  except OSError as error:
    raise ValueError('POLICY_UNAVAILABLE') from error
  if hashlib.sha256(raw).hexdigest() != expected_sha256:
    raise ValueError('POLICY_DIGEST_MISMATCH')
  try:
    data = json.loads(raw)
  except (json.JSONDecodeError, UnicodeError) as error:
    raise ValueError('INVALID_POLICY_JSON') from error

  required = {
    'schema_version', 'status', 'purpose', 'baseline_artifact_sha256',
    'baseline_internal_report_sha256', 'required_scenario_ids',
    'stress_scenario_ids', 'symmetry_pairs', 'thresholds',
    'improvement_metrics', 'identity_requirements', 'authority',
  }
  threshold_keys = {
    'maximum_relative_lateral_rmse_regression',
    'maximum_absolute_lateral_rmse_regression_m',
    'maximum_relative_lateral_max_regression',
    'maximum_absolute_lateral_max_regression_m',
    'maximum_relative_heading_error_regression',
    'maximum_absolute_heading_error_regression_rad',
    'maximum_relative_jerk_regression',
    'maximum_absolute_jerk_regression_deg_s3',
    'maximum_absolute_saturation_regression',
    'maximum_absolute_requested_torque_regression',
    'maximum_command_reversal_increase',
    'maximum_inactive_requested_torque_abs',
    'left_right_symmetry_absolute_tolerance',
    'minimum_stress_improvement_fraction',
    'require_every_stress_scenario_improved',
  }
  if (
    type(data) is not dict
    or set(data) != required
    or data['schema_version'] != 1
    or data['status'] != 'FROZEN_BEFORE_CANDIDATE_EXECUTION'
    or data['purpose'] != 'SYNTHETIC_LATERAL_CANDIDATE_NONREGRESSION_AND_IMPROVEMENT_GATE'
    or type(data['thresholds']) is not dict
    or set(data['thresholds']) != threshold_keys
    or type(data['identity_requirements']) is not dict
    or not data['identity_requirements']
    or any(value is not True for value in data['identity_requirements'].values())
    or type(data['authority']) is not dict
    or not data['authority']
    or any(value is not False for value in data['authority'].values())
  ):
    raise ValueError('INVALID_POLICY_FIELDS')
  thresholds = data['thresholds']
  policy = SyntheticGatePolicy(
    policy_sha256=expected_sha256,
    baseline_artifact_sha256=data['baseline_artifact_sha256'],
    baseline_internal_report_sha256=data['baseline_internal_report_sha256'],
    required_scenario_ids=tuple(data['required_scenario_ids']),
    stress_scenario_ids=tuple(data['stress_scenario_ids']),
    symmetry_pairs=tuple(tuple(pair) for pair in data['symmetry_pairs']),
    maximum_relative_lateral_rmse_regression=thresholds['maximum_relative_lateral_rmse_regression'],
    maximum_absolute_lateral_rmse_regression_m=thresholds['maximum_absolute_lateral_rmse_regression_m'],
    maximum_relative_lateral_max_regression=thresholds['maximum_relative_lateral_max_regression'],
    maximum_absolute_lateral_max_regression_m=thresholds['maximum_absolute_lateral_max_regression_m'],
    maximum_relative_heading_error_regression=thresholds['maximum_relative_heading_error_regression'],
    maximum_absolute_heading_error_regression_rad=thresholds['maximum_absolute_heading_error_regression_rad'],
    maximum_relative_jerk_regression=thresholds['maximum_relative_jerk_regression'],
    maximum_absolute_jerk_regression_deg_s3=thresholds['maximum_absolute_jerk_regression_deg_s3'],
    maximum_absolute_saturation_regression=thresholds['maximum_absolute_saturation_regression'],
    maximum_absolute_requested_torque_regression=thresholds['maximum_absolute_requested_torque_regression'],
    maximum_command_reversal_increase=thresholds['maximum_command_reversal_increase'],
    maximum_inactive_requested_torque_abs=thresholds['maximum_inactive_requested_torque_abs'],
    left_right_symmetry_absolute_tolerance=thresholds['left_right_symmetry_absolute_tolerance'],
    minimum_stress_improvement_fraction=thresholds['minimum_stress_improvement_fraction'],
    require_every_stress_scenario_improved=thresholds['require_every_stress_scenario_improved'],
    improvement_metrics=tuple(data['improvement_metrics']),
  )
  if not _canonical_policy_valid(policy):
    raise ValueError('INVALID_POLICY_VALUES')
  return policy


def _report_core_valid(report) -> bool:
  if type(report) is not SyntheticClosedLoopMatrixReport:
    return False
  if (
    report.status != 'SYNTHETIC_CLOSED_LOOP_DIAGNOSTIC'
    or not is_sha256(report.catalog_sha256)
    or not is_sha256(report.car_params_sha256)
    or not is_sha256(report.result_sha256)
    or type(report.scenarios) is not tuple
    or not report.scenarios
    or report.scenario_count != len(report.scenarios)
    or report.completed_count + report.rejected_input_count != len(report.scenarios)
    or report.blocked_count != 0
    or not report.all_nominal_completed
    or not report.fault_inputs_rejected
    or any((
      report.qualified_closed_loop,
      report.performance_qualified,
      report.candidate_generation_allowed,
      report.vehicle_or_can_write,
      report.runtime_accepted,
      report.promotable,
    ))
  ):
    return False
  ids = tuple(item.scenario_id for item in report.scenarios if type(item) is SyntheticClosedLoopScenarioResult)
  return (
    len(ids) == len(report.scenarios)
    and len(ids) == len(set(ids))
    and all(
      not any((
        item.performance_qualified,
        item.candidate_generation_allowed,
        item.vehicle_or_can_write,
        item.runtime_accepted,
        item.promotable,
      ))
      for item in report.scenarios
    )
  )


def _nominal_metrics_valid(item: SyntheticClosedLoopScenarioResult) -> bool:
  numeric = (
    item.lateral_error_rmse_m,
    item.maximum_abs_lateral_error_m,
    item.maximum_abs_heading_error_rad,
    item.steering_jerk_rmse_deg_s3,
    item.saturation_ratio,
    item.signed_mean_desired_curvature_1pm,
    item.signed_mean_actual_curvature_1pm,
    item.maximum_abs_requested_torque,
    item.inactive_requested_torque_max_abs,
    item.inactive_applied_command_max_abs,
  )
  return (
    item.status == 'COMPLETED_DIAGNOSTIC'
    and item.sample_count > 0
    and is_sha256(item.trace_sha256)
    and is_sha256(item.car_params_sha256)
    and item.controller_executed
    and item.plant_executed
    and item.physical_delay_owner == 'PLANT'
    and not item.controller_delay_queue_present
    and all(finite_number(value) for value in numeric)
    and all(value >= 0.0 for value in numeric[:5])
    and 0.0 <= item.saturation_ratio <= 1.0
    and 0.0 <= item.maximum_abs_requested_torque <= 1.0
    and type(item.command_reversal_events) is int
    and item.command_reversal_events >= 0
    and type(item.driver_intervention_frames) is int
    and 0 <= item.driver_intervention_frames <= item.sample_count
  )


def _fault_metrics_valid(item: SyntheticClosedLoopScenarioResult) -> bool:
  return (
    item.status == 'REJECTED_INPUT'
    and item.sample_count == 0
    and item.trace_sha256 is None
    and item.car_params_sha256 is None
    and not item.controller_executed
    and not item.plant_executed
    and item.physical_delay_owner is None
    and not item.controller_delay_queue_present
  )


def _identity_error(
  baseline: SyntheticClosedLoopMatrixReport,
  candidate: SyntheticClosedLoopMatrixReport,
  policy: SyntheticGatePolicy,
) -> str | None:
  if not _report_core_valid(baseline):
    return 'INVALID_BASELINE_REPORT'
  if not _report_core_valid(candidate):
    return 'INVALID_CANDIDATE_REPORT'
  if baseline.result_sha256 != policy.baseline_internal_report_sha256:
    return 'BASELINE_POLICY_BINDING_MISMATCH'
  baseline_ids = tuple(item.scenario_id for item in baseline.scenarios)
  candidate_ids = tuple(item.scenario_id for item in candidate.scenarios)
  if baseline_ids != policy.required_scenario_ids or candidate_ids != baseline_ids:
    return 'SCENARIO_IDENTITY_MISMATCH'
  if baseline.catalog_sha256 != candidate.catalog_sha256:
    return 'CATALOG_IDENTITY_MISMATCH'
  if baseline.car_params_sha256 != candidate.car_params_sha256:
    return 'CAR_PARAMS_IDENTITY_MISMATCH'

  for left, right in zip(baseline.scenarios, candidate.scenarios, strict=True):
    if (
      left.status != right.status
      or left.sample_count != right.sample_count
      or left.physical_delay_owner != right.physical_delay_owner
      or left.controller_delay_queue_present != right.controller_delay_queue_present
      or left.native_to_plant_sign != right.native_to_plant_sign
      or left.controller_executed != right.controller_executed
      or left.plant_executed != right.plant_executed
      or left.driver_intervention_frames != right.driver_intervention_frames
    ):
      return f'SCENARIO_CONTRACT_MISMATCH:{left.scenario_id}'
    expected_fault = left.scenario_id in FAULT_IDS
    if expected_fault != (left.status == 'REJECTED_INPUT'):
      return f'FAULT_OUTCOME_MISMATCH:{left.scenario_id}'
  return None


def _report_metrics_valid(report: SyntheticClosedLoopMatrixReport) -> bool:
  for item in report.scenarios:
    if item.scenario_id in FAULT_IDS:
      if not _fault_metrics_valid(item):
        return False
    elif not _nominal_metrics_valid(item):
      return False
  return True


def _allowed(baseline: float, relative: float, absolute: float) -> float:
  return baseline * (1.0 + relative) + absolute


def _candidate_map(
  report: SyntheticClosedLoopMatrixReport,
) -> dict[str, SyntheticClosedLoopScenarioResult]:
  return {item.scenario_id: item for item in report.scenarios}


def _metric_regressions(
  baseline: dict[str, SyntheticClosedLoopScenarioResult],
  candidate: dict[str, SyntheticClosedLoopScenarioResult],
  policy: SyntheticGatePolicy,
) -> list[str]:
  regressions = []
  for scenario_id in policy.required_scenario_ids:
    if scenario_id in FAULT_IDS:
      continue
    base = baseline[scenario_id]
    observed = candidate[scenario_id]
    checks = (
      (
        'lateral_error_rmse_m',
        policy.maximum_relative_lateral_rmse_regression,
        policy.maximum_absolute_lateral_rmse_regression_m,
      ),
      (
        'maximum_abs_lateral_error_m',
        policy.maximum_relative_lateral_max_regression,
        policy.maximum_absolute_lateral_max_regression_m,
      ),
      (
        'maximum_abs_heading_error_rad',
        policy.maximum_relative_heading_error_regression,
        policy.maximum_absolute_heading_error_regression_rad,
      ),
      (
        'steering_jerk_rmse_deg_s3',
        policy.maximum_relative_jerk_regression,
        policy.maximum_absolute_jerk_regression_deg_s3,
      ),
    )
    for name, relative, absolute in checks:
      if getattr(observed, name) > _allowed(getattr(base, name), relative, absolute):
        regressions.append(f'{scenario_id}:{name}')
    if (
      observed.saturation_ratio
      > base.saturation_ratio + policy.maximum_absolute_saturation_regression
    ):
      regressions.append(f'{scenario_id}:saturation_ratio')
    if (
      observed.maximum_abs_requested_torque
      > base.maximum_abs_requested_torque
      + policy.maximum_absolute_requested_torque_regression
    ):
      regressions.append(f'{scenario_id}:maximum_abs_requested_torque')
    if (
      observed.command_reversal_events
      > base.command_reversal_events + policy.maximum_command_reversal_increase
    ):
      regressions.append(f'{scenario_id}:command_reversal_events')
    if (
      observed.inactive_requested_torque_max_abs
      > policy.maximum_inactive_requested_torque_abs
    ):
      regressions.append(f'{scenario_id}:inactive_requested_torque_max_abs')
  return regressions


def _symmetry_regressions(
  candidate: dict[str, SyntheticClosedLoopScenarioResult],
  policy: SyntheticGatePolicy,
) -> list[str]:
  regressions = []
  tolerance = policy.left_right_symmetry_absolute_tolerance
  for left_id, right_id in policy.symmetry_pairs:
    left = candidate[left_id]
    right = candidate[right_id]
    for metric in SYMMETRY_METRICS:
      if abs(getattr(left, metric) - getattr(right, metric)) > tolerance:
        regressions.append(f'SYMMETRY:{left_id}:{right_id}:{metric}')
    for metric in (
      'signed_mean_desired_curvature_1pm',
      'signed_mean_actual_curvature_1pm',
    ):
      if abs(getattr(left, metric) + getattr(right, metric)) > tolerance:
        regressions.append(f'SYMMETRY:{left_id}:{right_id}:{metric}')
  return regressions


def _improved_stress_scenarios(
  baseline: dict[str, SyntheticClosedLoopScenarioResult],
  candidate: dict[str, SyntheticClosedLoopScenarioResult],
  policy: SyntheticGatePolicy,
) -> tuple[str, ...]:
  improved = []
  fraction = policy.minimum_stress_improvement_fraction
  for scenario_id in policy.stress_scenario_ids:
    base = baseline[scenario_id]
    observed = candidate[scenario_id]
    for metric in policy.improvement_metrics:
      base_value = getattr(base, metric)
      candidate_value = getattr(observed, metric)
      if base_value > 0.0 and candidate_value <= base_value * (1.0 - fraction):
        improved.append(scenario_id)
        break
  return tuple(improved)


def evaluate_candidate(
  baseline,
  candidate,
  policy,
) -> SyntheticCandidateGateResult:
  """Compare one candidate to the frozen synthetic baseline, authority-free."""
  if not _canonical_policy_valid(policy):
    return _blocked('INVALID_POLICY')
  identity_error = _identity_error(baseline, candidate, policy)
  if identity_error is not None:
    return _blocked(identity_error, policy.policy_sha256)
  if not _report_metrics_valid(baseline):
    return _blocked('INVALID_BASELINE_METRICS', policy.policy_sha256)
  if not _report_metrics_valid(candidate):
    return _blocked('INVALID_CANDIDATE_METRICS', policy.policy_sha256)

  baseline_by_id = _candidate_map(baseline)
  candidate_by_id = _candidate_map(candidate)
  regressions = _metric_regressions(baseline_by_id, candidate_by_id, policy)
  symmetry = _symmetry_regressions(candidate_by_id, policy)
  regressions.extend(symmetry)
  improved = _improved_stress_scenarios(
    baseline_by_id, candidate_by_id, policy,
  )
  no_regression = not regressions
  improvement_pass = (
    no_regression
    and (
      not policy.require_every_stress_scenario_improved
      or set(improved) == set(policy.stress_scenario_ids)
    )
  )
  if not no_regression:
    blockers = ['SYNTHETIC_REGRESSION']
    if symmetry:
      blockers.append('LEFT_RIGHT_SYMMETRY_VIOLATION')
    status = 'REJECTED'
  elif improvement_pass:
    blockers = [
      'SYNTHETIC_ONLY_NO_PHYSICAL_QUALIFICATION',
      'CANDIDATE_GENERATION_NOT_AUTHORIZED',
    ]
    status = 'SYNTHETIC_IMPROVEMENT_PASS'
  else:
    blockers = [
      'SYNTHETIC_ONLY_NO_PHYSICAL_QUALIFICATION',
      'STRESS_IMPROVEMENT_INCOMPLETE',
      'CANDIDATE_GENERATION_NOT_AUTHORIZED',
    ]
    status = 'SYNTHETIC_NONREGRESSION_PASS'

  return SyntheticCandidateGateResult(
    status=status,
    blockers=tuple(blockers),
    regressions=tuple(regressions),
    policy_sha256=policy.policy_sha256,
    compared_scenario_count=len(policy.required_scenario_ids),
    no_regression_pass=no_regression,
    improvement_pass=improvement_pass,
    improved_stress_scenarios=improved,
    symmetry_pass=not symmetry,
    fault_identity_pass=True,
  )
