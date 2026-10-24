"""Immutable observational contracts. No actuator handle or active policy mode."""
from dataclasses import dataclass
from enum import StrEnum


class CyberLongMode(StrEnum):
  DISABLED = 'disabled'
  OBSERVE_ONLY = 'observe_only'


@dataclass(frozen=True)
class CyberLongConfig:
  mode: CyberLongMode = CyberLongMode.DISABLED
  configuration_epoch: int = 0

  def __post_init__(self):
    if not isinstance(self.mode, CyberLongMode):
      raise ValueError('Only disabled and observe-only modes are available')
    if type(self.configuration_epoch) is not int or self.configuration_epoch < 0:
      raise ValueError('Configuration epoch must be a nonnegative identity counter')


@dataclass(frozen=True)
class ParameterBinding:
  # None means unknown, not a claim of matching firmware/model provenance.
  vehicle: str | None = None
  firmware: str | None = None
  model: str | None = None
  configuration_epoch: int = 0

  @property
  def complete(self) -> bool:
    return (all(isinstance(value, str) and bool(value.strip()) for value in (self.vehicle, self.firmware, self.model)) and
            type(self.configuration_epoch) is int and self.configuration_epoch >= 0)


@dataclass(frozen=True)
class StockCandidate:
  accel_mps2: float
  source: str
  should_stop: bool


@dataclass(frozen=True)
class LongContext:
  candidates: tuple[StockCandidate, ...]
  input_valid: bool
  reset_state: bool
  brake_pressed: bool
  gas_pressed: bool
  long_active: bool
  model_mono_time_ns: int
  car_state_mono_time_ns: int
  radar_mono_time_ns: int
  v_ego_mps: float
  a_ego_mps2: float
  v_cruise_mps: float
  force_decel: bool
  personality: str
  binding: ParameterBinding

  def __post_init__(self):
    # Prevent a mutable list being smuggled into a frozen snapshot.
    if not isinstance(self.candidates, tuple) or not all(isinstance(c, StockCandidate) for c in self.candidates):
      raise ValueError('Candidates must be an immutable tuple of StockCandidate')
    if not isinstance(self.binding, ParameterBinding):
      raise ValueError('Binding must be an immutable ParameterBinding')


@dataclass(frozen=True)
class LongObservation:
  context: LongContext
  winner_source: str
  winner_accel_mps2: float
  stock_should_stop: bool
  mode: CyberLongMode
  reason: str
  provenance_complete: bool


@dataclass(frozen=True)
class ParameterMetadata:
  name: str
  unit: str
  source: str
  default: float | None
  vehicle_specific: bool
  category: tuple[str, ...]
  online_allowed: bool = False
  offline_allowed: bool = False
  min: float | None = None
  max: float | None = None
  rate_of_change_limit: float | None = None
  confidence_requirement: float | None = None
  safety_related: bool = False
  read_only: bool = True


@dataclass(frozen=True)
class ParameterProposal:
  name: str
  value: float
  unit: str
  binding: ParameterBinding
  evidence_id: str
  confidence: float


@dataclass(frozen=True)
class ProposalAssessment:
  accepted: bool
  reason: str
