"""Immutable arithmetic/schema-simulation outputs, NOT actual actuator messages."""
from dataclasses import dataclass

from ._r4.flow_types import State
from ._r4.quantization_types import NormalizedStep


@dataclass(frozen=True, slots=True)
class Float32Projection:
    bits_hex: str
    value_hex: str


@dataclass(frozen=True, slots=True)
class OutputProjection:
    integer_command: int
    scale: int
    normalized_expression: float
    normalized_expression_hex: str
    torque_float32: Float32Projection
    torque_output_can_float32: Float32Projection
    status: str


@dataclass(frozen=True, slots=True)
class LateralOutput:
    projection: OutputProjection
    steer_request: bool
    next_state: State
    trace: NormalizedStep
