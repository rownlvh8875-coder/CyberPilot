"""Closed synthetic sequence catalog; not samples from a vehicle or prior results."""
from dataclasses import dataclass
from itertools import product

from domain import Limits
from flow_types import Sample


@dataclass(frozen=True, slots=True)
class Scenario:
    id: str
    samples: tuple[Sample, ...]


def _scenario(name, requests, limits, actives, angles, drivers):
    samples = tuple(Sample(i, requested, drivers[i % len(drivers)], angles[i % len(angles)],
                           actives[i % len(actives)], limits, "SYNTHETIC_ONLY") for i, requested in enumerate(requests))
    return Scenario(name, samples)


def catalog() -> list[Scenario]:
    base = Limits(16, 2, 5, 7, 1, 3)
    one = (True,)
    zero = (0.0,)
    cases = [
        _scenario("H-ramp", (20,) * 3, base, one, zero, zero),
        _scenario("H-reversal", (-20, -20, 20, 20), base, one, zero, zero),
        _scenario("H-inactive", (20,) * 4, base, (True, False, False, True), (90.0,), zero),
        _scenario("H-fault-cycle", (20,) * 94, base, one, (90.0,), zero),
        _scenario("H-fault-drop", (20,) * 93, base, one, (90.0,) * 90 + (0.0,) * 3, zero),
        _scenario("H-fault-inactive", (20,) * 93, base, (True,) * 90 + (False, True, True), (90.0,), zero),
        _scenario("H-round-even", (20,) * 6, Limits(16, 2, 5, 7, 1, 1), one, zero, (0.0,) * 5 + (-12.5,)),
        _scenario("H-round-even-negative", (-20,) * 6, Limits(16, 2, 5, 7, 1, 1), one, zero, (0.0,) * 5 + (12.5,)),
        _scenario("H-angle-thresholds", (20,) * 6, base, one, (85.0, -85.0, 84.99609375, -84.99609375, 0.0, -0.0), zero),
        _scenario("H-driver-flips", (-20, 20) * 4, base, one, zero, (64.0, -64.0)),
        _scenario("H-zero-invocation-steps", (20, -20, 0, 20), Limits(16, 0, 0, 0, 1, 1), (True, False, True, True), (90.0,), zero),
    ]
    grids = product([base, Limits(8, 1, 3, 0, 2, 1), Limits(32, 3, 7, 4, 2, 2)],
                    [(20,) * 12, (-20,) * 12, (20, -20) * 6, (0, 20, 0, -20) * 3],
                    [(True,), (True, False), (False,) * 4 + (True,) * 8],
                    [(0.0,), (90.0,), (84.99609375, 85.0, -85.0, 0.0)],
                    [(0.0,), (-64.0, -8.5, 8.5, 64.0)])
    for i, (limits, requests, actives, angles, drivers) in enumerate(grids):
        cases.append(_scenario(f"G{i:03d}", requests, limits, actives, angles, drivers))
    return cases
