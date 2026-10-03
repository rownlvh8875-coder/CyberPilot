"""Versioned offline metric bindings, not an evidence authenticator or evaluator.

No raw log loading, unit guessing, parameter writes or controller callbacks.
The caller must independently verify the frozen hashes before qualification.
"""
from dataclasses import dataclass, replace
import math
import re
from types import MappingProxyType

from openpilot.selfdrive.controls.lib.cyber_lateral.command_domain import OfflineTorqueCommandContract
from openpilot.selfdrive.controls.lib.cyber_lateral.metrics import LateralMetricInput, MetricResult, compute_lateral_metrics


PARAMETER_UNITS = MappingProxyType({
  'lat_accel_factor': 'm/s^2/normalized_command',
  'friction': 'normalized_command',
})


def finite_number(value) -> bool:
  try:
    return type(value) in (int, float) and math.isfinite(value)
  except OverflowError:
    return False


def is_sha256(value) -> bool:
  return isinstance(value, str) and re.fullmatch(r'[0-9a-f]{64}', value) is not None


def validate_parameter_unit(name: str, unit: str) -> None:
  """Only two physically defined families are representable; neither is enabled."""
  if not isinstance(name, str) or name not in PARAMETER_UNITS or unit != PARAMETER_UNITS[name]:
    raise ValueError('Unknown parameter or noncanonical unit; implicit Nm conversion is forbidden')


@dataclass(frozen=True)
class MetricContract:
  pipeline_sha256: str
  configuration_sha256: str
  inputs_sha256: str
  mask_sha256: str
  reset_policy_sha256: str
  reference_evidence_sha256: str
  command: OfflineTorqueCommandContract
  alignment_delay_s: float
  reversal_deadband_ratio_per_s: float
  version: int = 2

  def __post_init__(self):
    hashes = (self.pipeline_sha256, self.configuration_sha256, self.inputs_sha256,
              self.mask_sha256, self.reset_policy_sha256, self.reference_evidence_sha256)
    if type(self.version) is not int or self.version != 2 or not all(is_sha256(value) for value in hashes):
      raise ValueError('Metric v2 requires explicit SHA-256 bindings')
    if not isinstance(self.command, OfflineTorqueCommandContract):
      raise ValueError('Explicit normalized command scale and raw rate contract required')
    try:
      rates = (self.command.max_magnitude_increase_per_s, self.command.max_magnitude_decrease_per_s)
    except OverflowError as exc:
      raise ValueError('Derived command rates must be representable') from exc
    if any(not finite_number(rate) or rate <= 0 for rate in rates):
      raise ValueError('Derived command rates must be finite and positive')
    if any(not finite_number(value) or value < 0 for value in (self.alignment_delay_s, self.reversal_deadband_ratio_per_s)):
      raise ValueError('Delay and derivative deadband must be finite and nonnegative')


@dataclass(frozen=True)
class MetricBatch:
  contract: MetricContract
  metrics: tuple[MetricResult, ...]

  def __post_init__(self):
    if not isinstance(self.contract, MetricContract):
      raise ValueError('Metric contract required')
    if not isinstance(self.metrics, tuple) or not self.metrics or not all(isinstance(item, MetricResult) for item in self.metrics):
      raise ValueError('Metric records must be a nonempty immutable tuple')
    names = tuple(item.name for item in self.metrics)
    if not all(isinstance(name, str) for name in names) or len(set(names)) != len(names):
      raise ValueError('Metric names must be unique strings')


def compute_metrics_v2(data: LateralMetricInput, contract: MetricContract) -> MetricBatch:
  """Reuse public metrics, with explicit naming of reversal events and cycle proxy.

This adapter binds one pre-aligned window. It does not pool windows, invent
independent lane truth or convert a diagnostic correlation lag into alignment.
"""
  if not isinstance(data, LateralMetricInput) or not isinstance(contract, MetricContract):
    raise ValueError('Typed metric input and contract required')
  if (data.declared_alignment_delay_s != contract.alignment_delay_s or
      data.steering_zero_crossing_deadband_ratio_per_s != contract.reversal_deadband_ratio_per_s):
    raise ValueError('Metric delay/deadband differs from frozen contract')
  metrics = dict(compute_lateral_metrics(data))
  proxy = metrics.pop('steering_zero_crossing_frequency')
  metrics['command_reversal_cycle_proxy'] = replace(proxy, name='command_reversal_cycle_proxy')
  scaled = {name: None if getattr(proxy, name) is None else 2. * getattr(proxy, name)
            for name in ('signed_mean', 'rmse', 'p95_abs', 'maximum_abs')}
  metrics['command_reversal_events_per_s'] = replace(proxy, name='command_reversal_events_per_s', unit='events/s', **scaled)
  return MetricBatch(contract, tuple(metrics.values()))
