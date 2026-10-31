"""Explicit synthetic test subset, NOT validation imposed by original helpers."""
from dataclasses import dataclass
from math import isfinite


class DomainError(ValueError):
    """Input lies outside the explicitly tested synthetic subset."""


@dataclass(frozen=True, slots=True)
class Limits:
    STEER_MAX: int
    STEER_DELTA_UP: int
    STEER_DELTA_DOWN: int
    STEER_DRIVER_ALLOWANCE: int
    STEER_DRIVER_FACTOR: int
    STEER_DRIVER_MULTIPLIER: int


@dataclass(frozen=True, slots=True)
class LimiterCase:
    requested: int
    previous: int
    driver: float
    limits: Limits
    override: int | None = None


@dataclass(frozen=True, slots=True)
class FaultCase:
    condition: bool
    request: bool
    counter: int
    maximum: int
    mismatch: int = 1


def _integer(value, low, high):
    if type(value) is not int or not low <= value <= high:
        raise DomainError("SYNTHETIC_INTEGER_DOMAIN")


def validate_limiter(case: LimiterCase) -> None:
    if type(case) is not LimiterCase or type(case.limits) is not Limits:
        raise DomainError("SYNTHETIC_MODEL_REQUIRED")
    _integer(case.requested, -2048, 2048)
    _integer(case.previous, -2048, 2048)
    if type(case.driver) is not float or not isfinite(case.driver) or abs(case.driver) > 1024:
        raise DomainError("SYNTHETIC_DRIVER_DOMAIN")
    if case.driver.as_integer_ratio()[1] > 256:
        raise DomainError("SYNTHETIC_DYADIC_DOMAIN")
    _integer(case.limits.STEER_MAX, 1, 4096)
    for value in (case.limits.STEER_DELTA_UP, case.limits.STEER_DELTA_DOWN, case.limits.STEER_DRIVER_ALLOWANCE):
        _integer(value, 0, 64)
    for value in (case.limits.STEER_DRIVER_FACTOR, case.limits.STEER_DRIVER_MULTIPLIER):
        _integer(value, 0, 8)
    if case.override is not None:
        _integer(case.override, 1, 4096)


def validate_fault(case: FaultCase) -> None:
    if type(case) is not FaultCase or type(case.condition) is not bool or type(case.request) is not bool:
        raise DomainError("SYNTHETIC_BOOL_MODEL_REQUIRED")
    _integer(case.counter, 0, 256)
    _integer(case.maximum, 0, 128)
    _integer(case.mismatch, 1, 8)
