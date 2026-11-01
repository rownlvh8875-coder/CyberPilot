"""Fixed synthetic catalogs; not vehicle values, policy values or observations."""
from itertools import product

from domain import FaultCase, LimiterCase, Limits


def limiter_cases() -> list[tuple[str, LimiterCase]]:
    limits = [Limits(16, 2, 5, 7, 1, 3), Limits(8, 1, 3, 0, 2, 1),
              Limits(32, 3, 7, 4, 2, 2), Limits(16, 0, 0, 0, 1, 1)]
    inputs = product([-20, -8, -2, 0, 2, 8, 20], [-12, -3, -1, 0, 1, 3, 12],
                     [-64.0, -8.5, -0.5, -0.0, 0.0, 0.5, 8.5, 64.0], limits, [None, 9])
    return [(f"L{index:04d}", LimiterCase(*args)) for index, args in enumerate(inputs)]


def fault_cases() -> list[tuple[str, FaultCase]]:
    cases = []
    for condition, request, maximum, mismatch in product([False, True], [False, True], [0, 1, 2, 4, 89], [1, 2, 3]):
        for counter in range(maximum + mismatch + 2):
            cases.append((f"F{len(cases):04d}", FaultCase(condition, request, counter, maximum, mismatch)))
    return cases
