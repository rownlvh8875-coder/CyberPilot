"""Fail-closed *local* contract checks. No candidate generation or promotion.

Coverage counts and digests here are caller assertions, not verified evidence.
Passing this necessary check is insufficient for development qualification:
manifest authentication, corpus aggregation, A/A, uncertainty and minimum
primary improvement checks belong to later stages. No runtime writer exists.
"""
from collections.abc import Mapping
from dataclasses import dataclass, field

from openpilot.selfdrive.controls.lib.cyber_lateral.metrics import MetricResult
from openpilot.tools.cyber_autotune.contracts import MetricBatch, finite_number, is_sha256, validate_parameter_unit


REQUIRED_STRATA = frozenset({
  'straight', 'left_curve', 'right_curve', 'gentle_curve', 'tight_curve',
  'low_speed', 'medium_speed', 'high_speed', 'entry', 'apex', 'exit',
  'lane_change', 'driver_override', 'steering_release', 'reengagement', 'saturation',
})

# Strict no-worse comparisons, not a tunable weighted objective. The last
# element selects direction: lane-edge margin alone must not decrease.
METRIC_CHECKS = (
  ('lane_center_offset', 'm', ('rmse', 'p95_abs', 'maximum_abs'), False),
  ('lateral_path_error', 'm', ('rmse', 'p95_abs', 'maximum_abs'), False),
  ('cross_track_error', 'm', ('rmse', 'p95_abs', 'maximum_abs'), False),
  ('curvature_tracking_error', '1/m', ('rmse', 'p95_abs', 'maximum_abs'), False),
  ('left_curve_lane_center_error', 'm', ('rmse', 'p95_abs', 'maximum_abs'), False),
  ('right_curve_lane_center_error', 'm', ('rmse', 'p95_abs', 'maximum_abs'), False),
  ('steering_jerk', 'deg/s^3', ('rmse', 'p95_abs', 'maximum_abs'), False),
  ('steering_oscillation_residual', 'deg', ('rmse', 'p95_abs', 'maximum_abs'), False),
  ('torque_saturation_ratio', 'ratio', ('signed_mean',), False),
  ('steering_command_derivative', 'ratio/s', ('rmse', 'p95_abs', 'maximum_abs'), False),
  ('steering_torque_derivative', 'ratio/s', ('rmse', 'p95_abs', 'maximum_abs'), False),
  ('desired_actual_steering_error', 'deg', ('rmse', 'p95_abs', 'maximum_abs'), False),
  ('lane_edge_minimum_margin', 'm', ('signed_mean',), True),
  ('driver_intervention_count', 'events', ('signed_mean',), False),
  ('command_reversal_events_per_s', 'events/s', ('signed_mean',), False),
  ('declared_delay_phase_residual', '1/m', ('rmse', 'p95_abs', 'maximum_abs'), False),
) + tuple((f'declared_delay_phase_residual_{phase}', '1/m', ('rmse', 'p95_abs', 'maximum_abs'), False)
          for phase in ('straight', 'entry', 'apex', 'exit'))
# PSD peak frequency is diagnostic, not a monotonic loss. Moving a peak down
# is not necessarily improvement; oscillation amplitude is checked above.


@dataclass(frozen=True)
class CoveragePolicy:
  review_sha256: str
  minimum_counts: tuple[tuple[str, int], ...]

  def __post_init__(self):
    if not is_sha256(self.review_sha256) or not isinstance(self.minimum_counts, tuple):
      raise ValueError('Frozen coverage review and immutable requirements required')
    if any(not isinstance(item, tuple) or len(item) != 2 or not isinstance(item[0], str) or
           type(item[1]) is not int or item[1] <= 0 for item in self.minimum_counts):
      raise ValueError('Coverage minimums must be explicit positive integer counts')
    names = tuple(name for name, _ in self.minimum_counts)
    if len(names) != len(set(names)) or set(names) != REQUIRED_STRATA:
      raise ValueError('All required corpus regression conditions must be specified exactly once')


@dataclass(frozen=True)
class MetricGateResult:
  status: str
  reasons: tuple[str, ...]
  exact_zero_pairs: tuple[str, ...]
  development_gate_pass: bool = field(default=False, init=False)
  runtime_accepted: bool = field(default=False, init=False)

  @property
  def metric_gate_pass(self) -> bool:
    return self.status == 'LOCAL_NONREGRESSION_PASS'


def _valid_record(item: MetricResult | None, unit: str) -> bool:
  if (item is None or item.valid is not True or type(item.count) is not int or item.count <= 0 or item.unit != unit):
    return False
  values = (item.signed_mean, item.rmse, item.p95_abs, item.maximum_abs)
  if not all(finite_number(value) for value in values) or min(values[1:]) < 0:
    return False
  if unit == 'ratio' and not all(0 <= value <= 1 for value in values):
    return False
  if unit == 'events' and not all(0 <= value <= item.count and value == int(value) for value in values):
    return False
  return True


def check_metric_pair(baseline: MetricBatch, candidate: MetricBatch, policy: CoveragePolicy,
                      baseline_coverage: Mapping[str, int], candidate_coverage: Mapping[str, int]) -> MetricGateResult:
  """Compare complete local summaries with exactly the same frozen evaluation basis.

Configuration is the common baseline configuration; future candidate deltas need
a separate authenticated binding, not a changed mask, baseline config or delay.
Never pools per-window percentiles/RMSE or infers coverage from repeated runs.
"""
  blocked, rejected, zero_pairs = [], [], []
  if not isinstance(baseline, MetricBatch) or not isinstance(candidate, MetricBatch) or not isinstance(policy, CoveragePolicy):
    return MetricGateResult('BLOCKED', ('INVALID_TYPED_INPUT',), ())
  if baseline.contract != candidate.contract:
    blocked.append('METRIC_CONTRACT_MISMATCH')
  if not isinstance(baseline_coverage, Mapping) or not isinstance(candidate_coverage, Mapping):
    return MetricGateResult('BLOCKED', ('INVALID_COVERAGE',), ())
  for name, minimum in policy.minimum_counts:
    b_count, c_count = baseline_coverage.get(name), candidate_coverage.get(name)
    if type(b_count) is not int or type(c_count) is not int or min(b_count, c_count) < minimum:
      blocked.append(f'REQUIRED_COVERAGE_MISSING:{name}')
    elif b_count != c_count:
      blocked.append(f'COVERAGE_MASK_MISMATCH:{name}')

  b_metrics = {item.name: item for item in baseline.metrics}
  c_metrics = {item.name: item for item in candidate.metrics}
  for name, unit, statistics, higher_is_better in METRIC_CHECKS:
    pair = b_metrics.get(name), c_metrics.get(name)
    if any(not _valid_record(item, unit) for item in pair):
      blocked.append('PRIMARY_METRIC_UNAVAILABLE' if name == 'lane_center_offset' else f'INVALID_METRIC:{name}')
      continue
    b_metric, c_metric = pair
    if b_metric.count != c_metric.count:
      blocked.append(f'METRIC_COUNT_MISMATCH:{name}')
    for statistic in statistics:
      b_value, c_value = getattr(b_metric, statistic), getattr(c_metric, statistic)
      if (not finite_number(b_value) or not finite_number(c_value) or
          (not higher_is_better and min(b_value, c_value) < 0)):
        blocked.append(f'INVALID_VALUE:{name}:{statistic}')
        continue
      if b_value == 0 and c_value == 0:
        zero_pairs.append(f'{name}:{statistic}')
      # Direct comparison avoids undefined 0/0 and silently forgiving 0->positive.
      if (c_value < b_value) if higher_is_better else (c_value > b_value):
        rejected.append(f'REGRESSION:{name}:{statistic}')
  status = 'BLOCKED' if blocked else 'REJECTED' if rejected else 'LOCAL_NONREGRESSION_PASS'
  return MetricGateResult(status, tuple(blocked + rejected), tuple(zero_pairs))


@dataclass(frozen=True)
class ParameterReview:
  name: str
  unit: str
  owner: str
  stage: str
  source_sha256: str
  configuration_sha256: str
  baseline_value: float
  minimum: float | None
  maximum: float | None
  step: float | None
  max_rate_per_s: float | None
  minimum_confidence: float | None
  review_sha256: str | None


@dataclass(frozen=True)
class ReadinessResult:
  contracts_ready: bool
  blockers: tuple[str, ...]
  offline_evaluable: bool = field(default=False, init=False)
  candidate_generation_allowed: bool = field(default=False, init=False)
  runtime_accepted: bool = field(default=False, init=False)


def check_readiness(review: ParameterReview, *, expected_source_sha256: str, expected_configuration_sha256: str) -> ReadinessResult:
  """Check structural search metadata; no self-attested review grants authority.

Only factor/friction are representable at this stage, with upstream torqued
ownership. No online writer is disabled or replaced. Rate uses canonical unit/s.
Confidence is a required criterion, not a measured confidence claim.
"""
  blockers = []
  if not isinstance(review, ParameterReview):
    return ReadinessResult(False, ('INVALID_REVIEW', 'EVIDENCE_VALIDATION_PENDING'))
  try:
    validate_parameter_unit(review.name, review.unit)
  except ValueError:
    blockers.append('UNKNOWN_PARAMETER_OR_UNIT')
  if review.owner != 'torqued' or review.stage != 'torque_from_lateral_accel':
    blockers.append('PARAMETER_OWNER_OR_STAGE_MISMATCH')
  if (not is_sha256(expected_source_sha256) or not is_sha256(expected_configuration_sha256) or
      review.source_sha256 != expected_source_sha256 or review.configuration_sha256 != expected_configuration_sha256):
    blockers.append('SOURCE_OR_CONFIGURATION_MISMATCH')
  numbers = (review.baseline_value, review.minimum, review.maximum, review.step, review.max_rate_per_s, review.minimum_confidence)
  if not all(finite_number(value) for value in numbers) or not is_sha256(review.review_sha256):
    blockers.append('NO_REVIEWED_SEARCH_SPACE')
  elif (not 0 <= review.minimum <= review.baseline_value <= review.maximum or review.minimum >= review.maximum or
        (review.name == 'lat_accel_factor' and review.minimum == 0) or
        not 0 < review.step <= review.maximum - review.minimum or not review.max_rate_per_s > 0 or
        not 0 < review.minimum_confidence <= 1):
    blockers.append('INVALID_REVIEWED_SEARCH_SPACE')
  contracts_ready = not blockers
  blockers.append('EVIDENCE_VALIDATION_PENDING')
  return ReadinessResult(contracts_ready, tuple(blockers))
