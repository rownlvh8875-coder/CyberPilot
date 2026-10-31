"""Independent exact-rational model; no target, NumPy or record checker imports.

In the domain the largest intermediate magnitude is below 2**20 and every
denominator <= 2**8. All source binary64 arithmetic is therefore exact. These
claims do not extend to arbitrary floats, arrays or mutable LIMITS objects.
"""
from fractions import Fraction

from domain import FaultCase, LimiterCase, validate_fault, validate_limiter


def _record(value: Fraction, kind: str) -> dict:
    return {"kind": kind, "value": float(value).hex() if "float" in kind else int(value)}


def _saturate(value, lower, upper):
    # Independent piecewise saturation, not NumPy or original-helper execution.
    bounded = value
    if value < lower:
        bounded = lower
    if bounded > upper:
        return upper
    return bounded


def _clip(value, lower, upper, value_kind, lower_kind, upper_kind):
    result = _saturate(value, lower, upper)
    kind = "numpy.float64" if any("float" in item for item in (value_kind, lower_kind, upper_kind)) else "numpy.int64"
    trace = {
        "x": _record(value, value_kind), "lower": _record(lower, lower_kind),
        "upper": _record(upper, upper_kind), "result": _record(result, kind),
    }
    return result, kind, trace


def _nearest_even(value: Fraction) -> int:
    quotient, remainder = divmod(value.numerator, value.denominator)
    doubled = 2 * remainder
    return quotient + int(doubled > value.denominator or (doubled == value.denominator and quotient % 2 != 0))


def oracle_limiter(case: LimiterCase) -> dict:
    validate_limiter(case)
    limits = case.limits
    cap = limits.STEER_MAX if case.override is None else case.override
    driver_term = Fraction(case.driver) * limits.STEER_DRIVER_FACTOR
    upper_raw = cap + (limits.STEER_DRIVER_ALLOWANCE + driver_term) * limits.STEER_DRIVER_MULTIPLIER
    lower_raw = -cap + (driver_term - limits.STEER_DRIVER_ALLOWANCE) * limits.STEER_DRIVER_MULTIPLIER
    if upper_raw >= cap:
        upper, upper_kind = Fraction(cap), "python.int"
    elif upper_raw < 0:
        upper, upper_kind = Fraction(0), "python.int"
    else:
        upper, upper_kind = upper_raw, "python.float"
    if lower_raw <= -cap:
        lower, lower_kind = Fraction(-cap), "python.int"
    elif lower_raw > 0:
        lower, lower_kind = Fraction(0), "python.int"
    else:
        lower, lower_kind = lower_raw, "python.float"
    first, kind, trace1 = _clip(Fraction(case.requested), lower, upper, "python.int", lower_kind, upper_kind)
    previous, up, down = case.previous, limits.STEER_DELTA_UP, limits.STEER_DELTA_DOWN
    # State-conditioned directional envelope, kept separate from driver bounds.
    rate_lower = max(previous - down, -up) if previous > 0 else previous - up
    rate_upper = previous + up if previous > 0 else min(previous + down, up)
    second, _, trace2 = _clip(first, Fraction(rate_lower), Fraction(rate_upper), kind, "python.int", "python.int")
    return {"result": _nearest_even(second), "clips": [trace1, trace2]}


def oracle_fault(case: FaultCase) -> tuple[int, bool]:
    validate_fault(case)
    counted = case.counter + 1 if (case.condition and case.request) else 0
    allowed = case.request and counted <= case.maximum
    remaining = counted if counted < case.maximum + case.mismatch else 0
    return remaining, allowed
