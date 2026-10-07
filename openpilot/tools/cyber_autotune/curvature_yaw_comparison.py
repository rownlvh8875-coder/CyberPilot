"""Bridge admitted curvature/yaw native runs into the frozen three-arm comparator.

Independent path/lane evidence is mandatory and caller-owned. This module never
invents lane truth, coverage, thresholds, or controller outputs. Successful
assembly remains an offline comparison input only; comparison.py retains its
existing evidence-authenticity and uncertainty blockers.
"""
from dataclasses import asdict, dataclass
import hashlib
import json
import math

from openpilot.selfdrive.controls.lib.cyber_lateral.metrics import LateralMetricInput, MetricSeries
from openpilot.tools.cyber_autotune.comparison import ArmSpec, ComparisonGroup, RunBinding, RunReceipt
from openpilot.tools.cyber_autotune.contracts import MetricBatch, MetricContract, compute_metrics_v2, finite_number, is_sha256
from openpilot.tools.cyber_autotune.curvature_yaw_closed_loop import CurvatureYawRunResult, closed_loop_state_sha256
from openpilot.tools.cyber_autotune.curvature_yaw_native_protocol import (
  ADAPTER_PATH,
  PLANT_PATH,
  producer_identity_sha256,
)
from openpilot.tools.cyber_autotune.curvature_yaw_native_runner import (
  closed_loop_frames,
  initial_state,
  validate_response,
)
from openpilot.tools.cyber_autotune.lateral_closed_loop import ClosedLoopBinding, ClosedLoopDomain, frames_sha256, timebase_sha256
from openpilot.tools.cyber_autotune.preflight import CoveragePolicy, REQUIRED_STRATA


@dataclass(frozen=True)
class CurvatureYawReferenceEvidence:
  desired_path_offset_m: tuple[float, ...]
  lane_center_offset_m: tuple[float, ...]
  lane_edge_margin_m: tuple[float, ...]
  curve_phase_labels: tuple[str, ...]
  coverage: tuple[tuple[str, int], ...]
  desired_path_source_sha256: str
  lane_center_source_sha256: str
  lane_edge_source_sha256: str
  coverage_review_sha256: str


def _canonical(value) -> bytes:
  return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def _digest(value) -> str:
  return hashlib.sha256(_canonical(value)).hexdigest()


def reference_evidence_sha256(evidence: CurvatureYawReferenceEvidence) -> str:
  if type(evidence) is not CurvatureYawReferenceEvidence:
    raise ValueError('INVALID_REFERENCE_EVIDENCE')
  return _digest(asdict(evidence))


def _reference_valid(evidence, sample_count: int, coverage_policy: CoveragePolicy) -> bool:
  if (
    type(evidence) is not CurvatureYawReferenceEvidence
    or type(sample_count) is not int
    or sample_count < 2
    or type(coverage_policy) is not CoveragePolicy
  ):
    return False
  series = (
    evidence.desired_path_offset_m,
    evidence.lane_center_offset_m,
    evidence.lane_edge_margin_m,
  )
  if any(type(values) is not tuple or len(values) != sample_count for values in series):
    return False
  if not all(finite_number(value) for values in series for value in values):
    return False
  if (
    type(evidence.curve_phase_labels) is not tuple
    or len(evidence.curve_phase_labels) != sample_count
    or any(label not in {'straight', 'entry', 'apex', 'exit'} for label in evidence.curve_phase_labels)
  ):
    return False
  hashes = (
    evidence.desired_path_source_sha256,
    evidence.lane_center_source_sha256,
    evidence.lane_edge_source_sha256,
    evidence.coverage_review_sha256,
  )
  if not all(is_sha256(value) for value in hashes):
    return False
  if (
    evidence.lane_center_source_sha256 == evidence.desired_path_source_sha256
    or evidence.lane_edge_source_sha256 == evidence.desired_path_source_sha256
    or evidence.coverage_review_sha256 != coverage_policy.review_sha256
  ):
    return False
  coverage = evidence.coverage
  if type(coverage) is not tuple or len(coverage) != len(REQUIRED_STRATA):
    return False
  counts = {}
  for item in coverage:
    if (
      type(item) is not tuple
      or len(item) != 2
      or type(item[0]) is not str
      or item[0] not in REQUIRED_STRATA
      or type(item[1]) is not int
      or not 0 < item[1] <= sample_count
      or item[0] in counts
    ):
      return False
    counts[item[0]] = item[1]
  if set(counts) != REQUIRED_STRATA:
    return False
  return all(counts[name] >= minimum for name, minimum in coverage_policy.minimum_counts)


def run_binding_for_native(
  request: dict,
  producer_result: dict,
  domain: ClosedLoopDomain,
  contract: MetricContract,
  *,
  environment_sha256: str,
) -> RunBinding:
  validate_response(request, producer_result)
  if type(domain) is not ClosedLoopDomain or type(contract) is not MetricContract or not is_sha256(environment_sha256):
    raise ValueError('INVALID_RUN_BINDING_INPUT')
  frames = closed_loop_frames(request)
  if contract.inputs_sha256 != frames_sha256(frames):
    raise ValueError('METRIC_INPUT_BINDING_MISMATCH')
  state_hash = closed_loop_state_sha256(initial_state(request))
  if contract.reset_policy_sha256 != state_hash:
    raise ValueError('METRIC_RESET_BINDING_MISMATCH')
  return RunBinding(
    software_sha256=producer_identity_sha256(request),
    profile_sha256=producer_result['car_params_sha256'],
    configuration_sha256=producer_result['controller_identity_sha256'],
    inputs_sha256=frames_sha256(frames),
    reset_sha256=state_hash,
    mask_sha256=contract.mask_sha256,
    adapter_sha256=request['support_files'][ADAPTER_PATH],
    metric_sha256=contract.pipeline_sha256,
    plant_sha256=request['support_files'][PLANT_PATH],
    domain_sha256=domain.identity_sha256,
    environment_sha256=environment_sha256,
    timebase_sha256=timebase_sha256(frames),
  )


def closed_loop_binding_for_comparison(
  run_binding: RunBinding,
  producer_result: dict,
  *,
  plant_calibration_sha256: str,
) -> ClosedLoopBinding:
  if type(run_binding) is not RunBinding or not is_sha256(plant_calibration_sha256):
    raise ValueError('INVALID_CLOSED_LOOP_BINDING_INPUT')
  if producer_result.get('controller_identity_sha256') != run_binding.configuration_sha256:
    raise ValueError('CONTROLLER_CONFIGURATION_BINDING_MISMATCH')
  return ClosedLoopBinding(
    software_sha256=run_binding.software_sha256,
    controller_sha256=producer_result['controller_identity_sha256'],
    adapter_sha256=run_binding.adapter_sha256,
    plant_sha256=run_binding.plant_sha256,
    plant_calibration_sha256=plant_calibration_sha256,
    domain_sha256=run_binding.domain_sha256,
    inputs_sha256=run_binding.inputs_sha256,
    reset_sha256=run_binding.reset_sha256,
    metric_sha256=run_binding.metric_sha256,
    environment_sha256=run_binding.environment_sha256,
    timebase_sha256=run_binding.timebase_sha256,
  )


def _series(times, values, unit, source):
  return MetricSeries(times, tuple(float(value) for value in values), unit, source)


def metric_batch_from_native(
  request: dict,
  producer_result: dict,
  admitted: CurvatureYawRunResult,
  contract: MetricContract,
  reference: CurvatureYawReferenceEvidence,
  coverage_policy: CoveragePolicy,
) -> MetricBatch:
  validate_response(request, producer_result)
  if (
    type(admitted) is not CurvatureYawRunResult
    or admitted.status != 'STRUCTURAL_ADMISSION'
    or not admitted.structural_admission_pass
    or admitted.receipt is None
  ):
    raise ValueError('CLOSED_LOOP_NOT_STRUCTURALLY_ADMITTED')
  frames = closed_loop_frames(request)
  samples = admitted.receipt.samples
  count = len(frames)
  if len(samples) != count or not _reference_valid(reference, count, coverage_policy):
    raise ValueError('INDEPENDENT_REFERENCE_REQUIRED')
  reference_hash = reference_evidence_sha256(reference)
  if contract.reference_evidence_sha256 != reference_hash:
    raise ValueError('REFERENCE_EVIDENCE_BINDING_MISMATCH')
  if (
    contract.inputs_sha256 != frames_sha256(frames)
    or contract.reset_policy_sha256 != admitted.receipt.binding.reset_sha256
  ):
    raise ValueError('METRIC_BASIS_BINDING_MISMATCH')
  if (
    reference.lane_center_source_sha256 == admitted.receipt.trace_sha256
    or reference.lane_edge_source_sha256 == admitted.receipt.trace_sha256
  ):
    raise ValueError('REFERENCE_NOT_INDEPENDENT_OF_CLOSED_LOOP_TRACE')

  observations = producer_result['metric_observations']
  if len(observations) != count:
    raise ValueError('METRIC_OBSERVATION_COUNT_MISMATCH')
  times = tuple(frame.time_s for frame in frames)
  actual_path = tuple(sample.pose_y_m for sample in samples)
  desired_path = reference.desired_path_offset_m
  cross_track = tuple(actual - desired for actual, desired in zip(actual_path, desired_path, strict=True))
  actual_curvature = tuple(
    sample.yaw_rate_rps / frame.speed_mps
    for sample, frame in zip(samples, frames, strict=True)
  )
  if not all(math.isfinite(value) for value in (*actual_path, *cross_track, *actual_curvature)):
    raise ValueError('DERIVED_METRIC_INPUT_INVALID')

  observation_source = f'native_metric_observation:{producer_result["metric_observations_sha256"]}'
  data = LateralMetricInput(
    desired_path_offset_m=_series(
      times, desired_path, 'm', f'desired_path:{reference.desired_path_source_sha256}',
    ),
    actual_path_offset_m=_series(
      times, actual_path, 'm', f'closed_loop_pose:{admitted.receipt.trace_sha256}',
    ),
    cross_track_error_m=_series(times, cross_track, 'm', 'derived_cross_track'),
    requested_curvature_1pm=_series(
      times, tuple(frame.desired_curvature for frame in frames), '1/m', 'frozen_controller_input',
    ),
    actual_curvature_1pm=_series(times, actual_curvature, '1/m', 'closed_loop_yaw_over_speed'),
    lane_center_offset_m=_series(
      times,
      reference.lane_center_offset_m,
      'm',
      f'independent_lane:{reference.lane_center_source_sha256}',
    ),
    steering_angle_deg=_series(
      times,
      tuple(row['steering_angle_deg'] for row in observations),
      'deg',
      observation_source,
    ),
    saturation=_series(
      times,
      tuple(1.0 if row['saturated'] else 0.0 for row in observations),
      'bool',
      observation_source,
    ),
    driver_intervention=_series(
      times,
      tuple(1.0 if frame.steering_pressed else 0.0 for frame in frames),
      'bool',
      'frozen_controller_input',
    ),
    declared_alignment_delay_s=contract.alignment_delay_s,
    curve_phase_labels=reference.curve_phase_labels,
    steering_command=_series(
      times,
      tuple(sample.requested_torque for sample in samples),
      'ratio',
      'closed_loop_requested_torque',
    ),
    applied_steering_torque=_series(
      times,
      tuple(sample.applied_normalized_torque for sample in samples),
      'ratio',
      'closed_loop_applied_torque',
    ),
    desired_steering_angle_deg=_series(
      times,
      tuple(row['desired_steering_angle_deg'] for row in observations),
      'deg',
      observation_source,
    ),
    lane_edge_margin_m=_series(
      times,
      reference.lane_edge_margin_m,
      'm',
      f'independent_edge:{reference.lane_edge_source_sha256}',
    ),
    steering_zero_crossing_deadband_ratio_per_s=contract.reversal_deadband_ratio_per_s,
  )
  return compute_metrics_v2(data, contract)


def build_comparison_receipt(
  request: dict,
  producer_result: dict,
  admitted: CurvatureYawRunResult,
  group: ComparisonGroup,
  arm_spec: ArmSpec,
  repetition: int,
  reference: CurvatureYawReferenceEvidence,
  coverage_policy: CoveragePolicy,
) -> RunReceipt:
  if (
    type(group) is not ComparisonGroup
    or type(arm_spec) is not ArmSpec
    or arm_spec.arm not in {item.arm for item in group.arms}
    or type(repetition) is not int
    or repetition not in (0, 1)
  ):
    raise ValueError('INVALID_COMPARISON_RUN_DECLARATION')
  if admitted.receipt is None or admitted.receipt.arm != arm_spec.arm:
    raise ValueError('CLOSED_LOOP_ARM_MISMATCH')
  closed = admitted.receipt.binding
  run = arm_spec.binding
  checks = (
    (closed.software_sha256, run.software_sha256),
    (closed.controller_sha256, run.configuration_sha256),
    (closed.adapter_sha256, run.adapter_sha256),
    (closed.plant_sha256, run.plant_sha256),
    (closed.domain_sha256, run.domain_sha256),
    (closed.inputs_sha256, run.inputs_sha256),
    (closed.reset_sha256, run.reset_sha256),
    (closed.metric_sha256, run.metric_sha256),
    (closed.environment_sha256, run.environment_sha256),
    (closed.timebase_sha256, run.timebase_sha256),
    (producer_result.get('car_params_sha256'), run.profile_sha256),
  )
  if any(left != right for left, right in checks):
    raise ValueError('COMPARISON_RUN_BINDING_MISMATCH')
  metrics = metric_batch_from_native(
    request, producer_result, admitted, group.contract, reference, coverage_policy,
  )
  return RunReceipt(
    group_sha256=group.group_sha256,
    arm=arm_spec.arm,
    repetition=repetition,
    binding=run,
    trace_sha256=admitted.receipt.trace_sha256,
    outcome='COMPLETED',
    metrics=metrics,
    coverage=reference.coverage,
    hard_violations=(),
  )