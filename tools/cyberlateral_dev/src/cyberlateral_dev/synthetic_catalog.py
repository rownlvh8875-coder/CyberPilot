"""Closed development fixtures; constants are NOT vehicle settings or policy."""
from dataclasses import dataclass

from ._r4.domain import Limits
from ._r4.flow_types import State
from ._r4.quantization_types import NormalizedSample
from ._r4.state_model import initial_state


@dataclass(frozen=True, slots=True)
class SyntheticScenario:
    id: str
    initial_state: State
    samples: tuple[NormalizedSample, ...]


def _scenario(name, requests, limits, state, actives=(True,), angle=0.0):
    samples = tuple(NormalizedSample(state.index + i, q, 0.0, angle, actives[i % len(actives)], limits, 'SYNTHETIC_ONLY')
                    for i, q in enumerate(requests))
    return SyntheticScenario(name, state, samples)


def fixed_catalog() -> tuple[SyntheticScenario, ...]:
    small, ramp = Limits(5, 5, 5, 0, 1, 1), Limits(16, 2, 5, 7, 1, 3)
    return (
        _scenario('decimal-ties', (0.1, 0.3, -0.1, -0.3), small, initial_state()),
        _scenario('ramp', (1.0,) * 3, ramp, initial_state()),
        _scenario('reversal', (-1.0, -1.0, 1.0, 1.0), ramp, initial_state()),
        _scenario('inactive', (1.0,) * 4, ramp, initial_state(), (True, False, False, True)),
        _scenario('fault-cycle', (1.0,) * 94, ramp, initial_state(), angle=90.0),
        _scenario('signed-zero', (-0.0, 0.0), small, initial_state()),
        _scenario('history-scale', (0.0,), small, State(1, 100, 100, 0)),
    )
