"""Immutable synthetic flow data and representation conversion, no state logic."""
from dataclasses import dataclass

from domain import Limits


@dataclass(frozen=True, slots=True)
class State:
    index: int
    previous_requested: int | None
    previous_applied: int
    angle_counter: int


@dataclass(frozen=True, slots=True)
class Sample:
    index: int
    requested: int
    driver: float
    angle_deg: float
    lat_active: bool
    limits: Limits
    provenance: str


@dataclass(frozen=True, slots=True)
class Scalar:
    kind: str
    value: int | str


@dataclass(frozen=True, slots=True)
class Clip:
    x: Scalar
    lower: Scalar
    upper: Scalar
    result: Scalar


@dataclass(frozen=True, slots=True)
class StepResult:
    limiter_previous: int
    driver_clip: Clip
    rate_clip: Clip
    limited_command: int
    fault_condition: bool
    steer_request: bool
    final_command: int
    next_state: State


def clip_record(record: dict) -> Clip:
    return Clip(*(Scalar(record[key]["kind"], record[key]["value"]) for key in ("x", "lower", "upper", "result")))
