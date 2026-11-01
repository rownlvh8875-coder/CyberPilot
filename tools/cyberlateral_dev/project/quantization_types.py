"""Frozen records only; no quantization or state logic shared with the oracle."""
from dataclasses import dataclass

from domain import Limits
from flow_types import StepResult


@dataclass(frozen=True, slots=True)
class Quantization:
    request_hex: str
    scale: int
    product_hex: str
    rounded_integer: int
    integer_command: int


@dataclass(frozen=True, slots=True)
class NormalizedSample:
    index: int
    request: float
    driver: float
    angle_deg: float
    lat_active: bool
    limits: Limits
    provenance: str


@dataclass(frozen=True, slots=True)
class NormalizedStep:
    quantization: Quantization
    downstream: StepResult
