"""Closed synthetic request vectors and trajectories, never vehicle observations."""
import math
from dataclasses import dataclass
from itertools import product

from domain import Limits
from quantization_types import NormalizedSample


def quantization_vectors() -> list[tuple[str, float, int]]:
    base = [-1.0, -0.75, -0.5, -0.3, -0.25, -0.1, -1 / 3, -0.0,
            0.0, 1 / 3, 0.1, 0.25, 0.3, 0.5, 0.75, 1.0]
    base += [math.nextafter(0.5, 0.0), math.nextafter(0.5, 1.0),
             math.nextafter(-0.5, 0.0), math.nextafter(-0.5, -1.0),
             math.nextafter(1.0, 0.0), math.nextafter(-1.0, 0.0)]
    for text in ["0x0.0000000000001p-1022", "0x0.fffffffffffffp-1022",
                 "0x1.0000000000000p-1022", "0x1.5555555555555p-1"]:
        value = float.fromhex(text)
        base.extend([value, -value])
    cases, seen = [], set()
    for scale in [1, 2, 3, 5, 7, 8, 16, 31, 64, 127, 256, 1024, 2048]:
        values = list(base)
        for whole in sorted({-scale, -2, -1, 0, 1, 2, scale - 1}):
            q = (whole + 0.5) / scale
            if -1 <= q <= 1:
                values.extend([math.nextafter(q, -math.inf), q, math.nextafter(q, math.inf)])
        for value in values:
            key = (float(value).hex(), scale)
            if -1 <= value <= 1 and key not in seen:
                seen.add(key)
                cases.append((f"Q{len(cases):04d}", value, scale))
    return cases


@dataclass(frozen=True, slots=True)
class NormalizedScenario:
    id: str
    samples: tuple[NormalizedSample, ...]


def _scenario(name, requests, limits, actives, angles, drivers):
    return NormalizedScenario(name, tuple(NormalizedSample(i, q, drivers[i % len(drivers)], angles[i % len(angles)],
                                                          actives[i % len(actives)], limits, "SYNTHETIC_ONLY")
                                          for i, q in enumerate(requests)))


def normalized_scenarios() -> list[NormalizedScenario]:
    base, zero, active = Limits(16, 2, 5, 7, 1, 3), (0.0,), (True,)
    cases = [
        _scenario("N-decimal-ties", (0.1, 0.3, -0.1, -0.3), Limits(5, 5, 5, 0, 1, 1), active, zero, zero),
        _scenario("N-ramp", (1.0,) * 3, base, active, zero, zero),
        _scenario("N-reversal", (-1.0, -1.0, 1.0, 1.0), base, active, zero, zero),
        _scenario("N-inactive", (1.0,) * 4, base, (True, False, False, True), (90.0,), zero),
        _scenario("N-fault-cycle", (1.0,) * 94, base, active, (90.0,), zero),
        _scenario("N-fault-drop", (1.0,) * 93, base, active, (90.0,) * 90 + (0.0,) * 3, zero),
        _scenario("N-signed-zero", (0.0, -0.0), Limits(5, 1, 3, 0, 1, 1), active, zero, zero),
        _scenario("N-half-neighbors", (math.nextafter(0.5, 0.0), 0.5, math.nextafter(0.5, 1.0),
                                          math.nextafter(-0.5, -1.0), -0.5, math.nextafter(-0.5, 0.0)),
                  Limits(1, 1, 1, 0, 1, 1), active, zero, zero),
    ]
    grid = product([Limits(5, 1, 3, 0, 1, 1), base, Limits(31, 3, 7, 4, 2, 2), Limits(2048, 64, 64, 7, 1, 3)],
                   [(1.0,) * 12, (-1.0, 1.0) * 6, (0.1, 0.3, -0.1, -0.3) * 3],
                   [(True,), (True, False), (False,) * 4 + (True,) * 8],
                   [(0.0,), (90.0,), (84.99609375, 85.0, -85.0, 0.0)], [(0.0,), (-64.0, -8.5, 8.5, 64.0)])
    for i, (limits, requests, actives, angles, drivers) in enumerate(grid):
        cases.append(_scenario(f"NG{i:03d}", requests, limits, actives, angles, drivers))
    return cases
