"""Explicit binary64 arithmetic and binary32 schema simulation, no wire codec."""
import struct
from math import isfinite

from .output_types import Float32Projection, OutputProjection


class OutputError(ValueError):
    """Outside the declared synthetic output/projection domain."""


def simulate_float32(value: float) -> Float32Projection:
    if type(value) is not float or not isfinite(value) or abs(value) > 2048:
        raise OutputError("BOUNDED_BUILTIN_FLOAT_REQUIRED")
    word = struct.pack(">f", value)
    decoded = struct.unpack(">f", word)[0]
    return Float32Projection(word.hex(), decoded.hex())


def project_output(command: int, scale: int) -> OutputProjection:
    if type(command) is not int or not -2048 <= command <= 2048:
        raise OutputError("EXPLICIT_INTEGER_COMMAND_REQUIRED")
    if type(scale) is not int or not 1 <= scale <= 2048:
        raise OutputError("EXPLICIT_SYNTHETIC_SCALE_REQUIRED")
    normalized = command / scale
    return OutputProjection(command, scale, normalized, float(normalized).hex(),
                            simulate_float32(normalized), simulate_float32(float(command)),
                            "SCHEMA_SIMULATION_NOT_CAPNP_OR_CAN_WIRE")
