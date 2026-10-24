"""Deterministic offline Cyber Lateral metrics.

Alignment delay, valid masks, sources and units are caller-owned inputs. This
module never searches for a delay or substitutes missing references with zero.
"""
from bisect import bisect_right
from collections.abc import Mapping
from dataclasses import dataclass
import math
from types import MappingProxyType


@dataclass(frozen=True)
class MetricSeries:
  time_s: tuple[float, ...]
  values: tuple[float, ...]
  unit: str
  source: str

  def __post_init__(self):
    if not isinstance(self.time_s, tuple) or not isinstance(self.values, tuple):
      raise ValueError('Metric series storage must be immutable tuples')
    if not self.time_s or len(self.time_s) != len(self.values):
      raise ValueError('Metric series time and value lengths must match and be nonempty')
    if not isinstance(self.unit, str) or not self.unit.strip():
      raise ValueError('Metric series unit is required')
    if not isinstance(self.source, str) or not self.source.strip():
      raise ValueError('Metric series source is required')
    if not all(type(value) in (int, float) and math.isfinite(value) for value in (*self.time_s, *self.values)):
      raise ValueError('Metric series values must be finite numbers')
    if any(current <= previous for previous, current in zip(self.time_s, self.time_s[1:], strict=False)):
      raise ValueError('Metric series time must be strictly increasing')


@dataclass(frozen=True)
class MetricResult:
  name: str
  valid: bool
  reason: str
  unit: str
  count: int
  signed_mean: float | None
  rmse: float | None
  p95_abs: float | None
  maximum_abs: float | None


@dataclass(frozen=True)
class LateralMetricInput:
  desired_path_offset_m: MetricSeries
  actual_path_offset_m: MetricSeries
  cross_track_error_m: MetricSeries
  requested_curvature_1pm: MetricSeries
  actual_curvature_1pm: MetricSeries
  lane_center_offset_m: MetricSeries | None
  steering_angle_deg: MetricSeries
  saturation: MetricSeries
  driver_intervention: MetricSeries
  declared_alignment_delay_s: float
  curve_phase_labels: tuple[str, ...]
  steering_command: MetricSeries | None = None
  applied_steering_torque: MetricSeries | None = None
  desired_steering_angle_deg: MetricSeries | None = None
  lane_edge_margin_m: MetricSeries | None = None
  steering_zero_crossing_deadband_ratio_per_s: float = 0.

  def __post_init__(self):
    required = (
      self.desired_path_offset_m, self.actual_path_offset_m, self.cross_track_error_m,
      self.requested_curvature_1pm, self.actual_curvature_1pm,
      self.steering_angle_deg, self.saturation, self.driver_intervention,
    )
    if not all(isinstance(value, MetricSeries) for value in required):
      raise ValueError('Every required metric input must be a MetricSeries')
    if self.lane_center_offset_m is not None and not isinstance(self.lane_center_offset_m, MetricSeries):
      raise ValueError('Lane center input must be a MetricSeries or None')
    optional = (
      self.steering_command, self.applied_steering_torque,
      self.desired_steering_angle_deg, self.lane_edge_margin_m,
    )
    if any(value is not None and not isinstance(value, MetricSeries) for value in optional):
      raise ValueError('Optional metric inputs must be MetricSeries or None')
    reference_time = self.desired_path_offset_m.time_s
    aligned = (*required[1:], *(value for value in (self.lane_center_offset_m, *optional) if value is not None))
    if any(value.time_s != reference_time for value in aligned):
      raise ValueError('Metric series must use one pre-aligned time axis')
    if len(reference_time) < 2:
      raise ValueError('At least two aligned samples are required')
    deltas = tuple(current - previous for previous, current in zip(reference_time, reference_time[1:], strict=False))
    if any(not math.isclose(delta, deltas[0], rel_tol=1e-9, abs_tol=1e-12) for delta in deltas[1:]):
      raise ValueError('Metric series require a uniform pre-frozen timestep')
    expected_units = {
      'desired_path_offset_m': 'm',
      'actual_path_offset_m': 'm',
      'cross_track_error_m': 'm',
      'requested_curvature_1pm': '1/m',
      'actual_curvature_1pm': '1/m',
      'steering_angle_deg': 'deg',
      'saturation': 'bool',
      'driver_intervention': 'bool',
    }
    for name, unit in expected_units.items():
      if getattr(self, name).unit != unit:
        raise ValueError(f'{name} must use unit {unit}')
    if self.lane_center_offset_m is not None and self.lane_center_offset_m.unit != 'm':
      raise ValueError('lane_center_offset_m must use unit m')
    optional_units = {
      'steering_command': 'ratio',
      'applied_steering_torque': 'ratio',
      'desired_steering_angle_deg': 'deg',
      'lane_edge_margin_m': 'm',
    }
    for name, unit in optional_units.items():
      value = getattr(self, name)
      if value is not None and value.unit != unit:
        raise ValueError(f'{name} must use unit {unit}')
    if any(value not in (0, 1) for value in (*self.saturation.values, *self.driver_intervention.values)):
      raise ValueError('Saturation and intervention inputs must be binary')
    if (type(self.declared_alignment_delay_s) not in (int, float) or
        not math.isfinite(self.declared_alignment_delay_s) or self.declared_alignment_delay_s < 0):
      raise ValueError('Declared alignment delay must be a finite nonnegative number')
    if (type(self.steering_zero_crossing_deadband_ratio_per_s) not in (int, float) or
        not math.isfinite(self.steering_zero_crossing_deadband_ratio_per_s) or
        self.steering_zero_crossing_deadband_ratio_per_s < 0):
      raise ValueError('Steering zero-crossing deadband must be a finite nonnegative number')
    allowed_phases = {'straight', 'entry', 'apex', 'exit'}
    if (not isinstance(self.curve_phase_labels, tuple) or len(self.curve_phase_labels) != len(reference_time) or
        any(label not in allowed_phases for label in self.curve_phase_labels)):
      raise ValueError('Curve phase labels must be caller-frozen and aligned')


def _percentile_abs(values: tuple[float, ...], fraction: float) -> float:
  ordered = sorted(abs(value) for value in values)
  position = (len(ordered) - 1) * fraction
  lower = math.floor(position)
  upper = math.ceil(position)
  if lower == upper:
    return float(ordered[lower])
  weight = position - lower
  return float(ordered[lower] * (1. - weight) + ordered[upper] * weight)


def _aggregate(name: str, unit: str, values: tuple[float, ...]) -> MetricResult:
  if not values:
    return _invalid(name, unit, 'insufficient_samples')
  return MetricResult(
    name=name,
    valid=True,
    reason='ok',
    unit=unit,
    count=len(values),
    signed_mean=float(sum(values) / len(values)),
    rmse=float(math.sqrt(sum(value * value for value in values) / len(values))),
    p95_abs=_percentile_abs(values, 0.95),
    maximum_abs=float(max(abs(value) for value in values)),
  )


def _invalid(name: str, unit: str, reason: str) -> MetricResult:
  return MetricResult(name, False, reason, unit, 0, None, None, None, None)


def _scalar(name: str, unit: str, value: float, count: int) -> MetricResult:
  return MetricResult(name, True, 'ok', unit, count, value, abs(value), abs(value), abs(value))


def _independent_lane(data: LateralMetricInput) -> MetricSeries | None:
  lane = data.lane_center_offset_m
  if lane is None:
    return None
  dependent_sources = {
    data.desired_path_offset_m.source,
    data.actual_path_offset_m.source,
  }
  return None if lane.source in dependent_sources else lane


def _derivative(series: MetricSeries) -> tuple[float, ...]:
  return tuple(
    (current - previous) / (current_time - previous_time)
    for previous_time, current_time, previous, current in zip(
      series.time_s[:-1], series.time_s[1:], series.values[:-1], series.values[1:], strict=True,
    )
  )


def _dominant_frequency(series: MetricSeries) -> float | None:
  sample_count = len(series.values)
  if sample_count < 4:
    return None
  dt = series.time_s[1] - series.time_s[0]
  mean = sum(series.values) / sample_count
  centered = tuple(value - mean for value in series.values)
  powers = []
  for index in range(1, sample_count // 2 + 1):
    real = sum(value * math.cos(2. * math.pi * index * sample / sample_count)
               for sample, value in enumerate(centered))
    imaginary = -sum(value * math.sin(2. * math.pi * index * sample / sample_count)
                     for sample, value in enumerate(centered))
    powers.append((real * real + imaginary * imaginary, index / (sample_count * dt)))
  power, frequency = max(powers)
  return None if math.isclose(power, 0., abs_tol=1e-24) else float(frequency)


def _interpolate(time_s: tuple[float, ...], values: tuple[float, ...], query: float) -> float | None:
  if query < time_s[0] or query > time_s[-1]:
    return None
  index = bisect_right(time_s, query)
  if index == 0:
    return float(values[0])
  if index == len(time_s):
    return float(values[-1])
  left = index - 1
  if time_s[left] == query:
    return float(values[left])
  ratio = (query - time_s[left]) / (time_s[index] - time_s[left])
  return float(values[left] + ratio * (values[index] - values[left]))


def compute_lateral_metrics(data: LateralMetricInput) -> Mapping[str, MetricResult]:
  """Compute aggregate metrics from a pre-aligned immutable input contract."""
  path_error = tuple(
    actual - desired
    for desired, actual in zip(data.desired_path_offset_m.values, data.actual_path_offset_m.values, strict=True)
  )
  curvature_error = tuple(
    actual - requested
    for requested, actual in zip(data.requested_curvature_1pm.values, data.actual_curvature_1pm.values, strict=True)
  )
  results = {
    'lateral_path_error': _aggregate('lateral_path_error', 'm', path_error),
    'cross_track_error': _aggregate('cross_track_error', 'm', data.cross_track_error_m.values),
    'curvature_tracking_error': _aggregate('curvature_tracking_error', '1/m', curvature_error),
  }

  lane = _independent_lane(data)
  if lane is None:
    results['lane_center_offset'] = _invalid('lane_center_offset', 'm', 'missing_independent_lane_reference')
    results['inside_outside_bias'] = _invalid('inside_outside_bias', 'm', 'missing_independent_lane_reference')
    results['left_curve_lane_center_error'] = _invalid(
      'left_curve_lane_center_error', 'm', 'missing_independent_lane_reference',
    )
    results['right_curve_lane_center_error'] = _invalid(
      'right_curve_lane_center_error', 'm', 'missing_independent_lane_reference',
    )
  else:
    results['lane_center_offset'] = _aggregate('lane_center_offset', 'm', lane.values)
    inside_bias = tuple(
      (1. if curvature > 0. else -1.) * offset if curvature != 0. else 0.
      for offset, curvature in zip(lane.values, data.requested_curvature_1pm.values, strict=True)
    )
    results['inside_outside_bias'] = _aggregate('inside_outside_bias', 'm', inside_bias)
    left_error = tuple(
      offset for offset, curvature in zip(lane.values, data.requested_curvature_1pm.values, strict=True)
      if curvature > 0.
    )
    right_error = tuple(
      offset for offset, curvature in zip(lane.values, data.requested_curvature_1pm.values, strict=True)
      if curvature < 0.
    )
    results['left_curve_lane_center_error'] = _aggregate('left_curve_lane_center_error', 'm', left_error)
    results['right_curve_lane_center_error'] = _aggregate('right_curve_lane_center_error', 'm', right_error)

  times = data.steering_angle_deg.time_s
  angles = data.steering_angle_deg.values
  dt = times[1] - times[0]
  steering_jerk = tuple(
    (angles[index + 3] - 3. * angles[index + 2] + 3. * angles[index + 1] - angles[index]) / dt ** 3
    for index in range(len(angles) - 3)
  )
  results['steering_jerk'] = _aggregate('steering_jerk', 'deg/s^3', steering_jerk)

  span = times[-1] - times[0]
  slope = (angles[-1] - angles[0]) / span
  residual = tuple(angle - (angles[0] + slope * (time - times[0])) for time, angle in zip(times, angles, strict=True))
  results['steering_oscillation_residual'] = _aggregate('steering_oscillation_residual', 'deg', residual)
  results['saturation_duty'] = _aggregate('saturation_duty', 'ratio', data.saturation.values)
  results['torque_saturation_ratio'] = _aggregate('torque_saturation_ratio', 'ratio', data.saturation.values)

  if data.steering_command is None:
    results['steering_command_derivative'] = _invalid('steering_command_derivative', 'ratio/s', 'missing_source')
    results['steering_zero_crossing_frequency'] = _invalid(
      'steering_zero_crossing_frequency', 'Hz', 'missing_source',
    )
    results['steering_oscillation_frequency'] = _invalid(
      'steering_oscillation_frequency', 'Hz', 'missing_source',
    )
  else:
    command_derivative = _derivative(data.steering_command)
    results['steering_command_derivative'] = _aggregate(
      'steering_command_derivative', 'ratio/s', command_derivative,
    )
    deadband = data.steering_zero_crossing_deadband_ratio_per_s
    derivative_signs = tuple(1 if value > deadband else -1 if value < -deadband else 0
                             for value in command_derivative)
    nonzero_signs = tuple(sign for sign in derivative_signs if sign != 0)
    reversals = sum(current != previous for previous, current in zip(
      nonzero_signs, nonzero_signs[1:], strict=False,
    ))
    reversal_frequency = reversals / (2. * span)
    results['steering_zero_crossing_frequency'] = _scalar(
      'steering_zero_crossing_frequency', 'Hz', float(reversal_frequency), len(command_derivative),
    )
    oscillation_frequency = _dominant_frequency(data.steering_command)
    results['steering_oscillation_frequency'] = (
      _invalid('steering_oscillation_frequency', 'Hz', 'no_oscillation_detected')
      if oscillation_frequency is None else
      _scalar('steering_oscillation_frequency', 'Hz', oscillation_frequency, len(data.steering_command.values))
    )

  if data.applied_steering_torque is None:
    results['steering_torque_derivative'] = _invalid('steering_torque_derivative', 'ratio/s', 'missing_source')
  else:
    results['steering_torque_derivative'] = _aggregate(
      'steering_torque_derivative', 'ratio/s', _derivative(data.applied_steering_torque),
    )

  if data.desired_steering_angle_deg is None:
    results['desired_actual_steering_error'] = _invalid(
      'desired_actual_steering_error', 'deg', 'missing_source',
    )
  else:
    steering_error = tuple(
      actual - desired for desired, actual in zip(
        data.desired_steering_angle_deg.values, data.steering_angle_deg.values, strict=True,
      )
    )
    results['desired_actual_steering_error'] = _aggregate(
      'desired_actual_steering_error', 'deg', steering_error,
    )

  edge = data.lane_edge_margin_m
  dependent_edge_sources = {
    data.desired_path_offset_m.source, data.actual_path_offset_m.source,
  }
  if edge is None:
    results['lane_edge_minimum_margin'] = _invalid('lane_edge_minimum_margin', 'm', 'missing_source')
  elif edge.source in dependent_edge_sources:
    results['lane_edge_minimum_margin'] = _invalid(
      'lane_edge_minimum_margin', 'm', 'missing_independent_edge_reference',
    )
  else:
    results['lane_edge_minimum_margin'] = _scalar(
      'lane_edge_minimum_margin', 'm', float(min(edge.values)), len(edge.values),
    )

  previous = 0.
  events = 0
  for value in data.driver_intervention.values:
    if value == 1 and previous == 0:
      events += 1
    previous = value
  results['driver_intervention_count'] = MetricResult(
    'driver_intervention_count', True, 'ok', 'events', len(data.driver_intervention.values),
    float(events), float(events), float(events), float(events),
  )

  delayed_error = []
  delayed_error_by_phase: dict[str, list[float]] = {
    'straight': [], 'entry': [], 'apex': [], 'exit': [],
  }
  request_times = data.requested_curvature_1pm.time_s
  requests = data.requested_curvature_1pm.values
  for time, actual, phase in zip(
    data.actual_curvature_1pm.time_s, data.actual_curvature_1pm.values,
    data.curve_phase_labels, strict=True,
  ):
    requested = _interpolate(request_times, requests, time - data.declared_alignment_delay_s)
    if requested is not None:
      residual = actual - requested
      delayed_error.append(residual)
      delayed_error_by_phase[phase].append(residual)
  results['declared_delay_phase_residual'] = _aggregate(
    'declared_delay_phase_residual', '1/m', tuple(delayed_error),
  )
  for phase, residuals in delayed_error_by_phase.items():
    name = f'declared_delay_phase_residual_{phase}'
    results[name] = _aggregate(name, '1/m', tuple(residuals))
  return MappingProxyType(results)
