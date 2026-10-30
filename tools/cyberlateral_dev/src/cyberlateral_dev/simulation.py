"""Pure bounded synthetic batch consumer of the existing single-step API."""
from dataclasses import dataclass

from .api import LateralInput, LateralState, step
from .output_types import LateralOutput


class SimulationError(ValueError):
    """Batch container outside the declared bounded synthetic interface."""


@dataclass(frozen=True, slots=True)
class SimulationResult:
    outputs: tuple[LateralOutput, ...]
    next_state: LateralState


def simulate(samples: tuple[LateralInput, ...], state: LateralState) -> SimulationResult:
    if type(samples) is not tuple or not 1 <= len(samples) <= 4096:
        raise SimulationError('EXPLICIT_BOUNDED_SYNTHETIC_TUPLE_REQUIRED')
    outputs = []
    current = state
    for sample in samples:
        output = step(sample, current)
        outputs.append(output)
        current = output.next_state
    return SimulationResult(tuple(outputs), current)
