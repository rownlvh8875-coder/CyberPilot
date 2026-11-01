"""Pure synthetic transition. Not an installed controller or runtime adapter."""
from math import isfinite

from domain import DomainError, FaultCase, LimiterCase, validate_limiter
from flow_types import Sample, State, StepResult, clip_record
from oracle import oracle_fault, oracle_limiter


class FlowError(ValueError):
    """Outside the explicit synthetic model domain/order, not a source rejection API."""


def initial_state() -> State:
    return State(0, None, 0, 0)


def _integer(value, low, high):
    if type(value) is not int or not low <= value <= high:
        raise FlowError("SYNTHETIC_STATE_INTEGER_REQUIRED")


def validate(state: State, sample: Sample) -> None:
    if type(state) is not State or type(sample) is not Sample:
        raise FlowError("EXACT_SYNTHETIC_MODELS_REQUIRED")
    if type(sample.provenance) is not str or sample.provenance != "SYNTHETIC_ONLY":
        raise FlowError("SYNTHETIC_SCOPE_REQUIRED")
    _integer(state.index, 0, 4096)
    _integer(sample.index, 0, 4095)
    if sample.index != state.index:
        raise FlowError("ADJACENT_MODEL_INVOCATION_REQUIRED")
    _integer(state.previous_applied, -2048, 2048)
    _integer(state.angle_counter, 0, 90)
    if state.index == 0:
        if state.previous_requested is not None or state.previous_applied != 0 or state.angle_counter != 0:
            raise FlowError("CANONICAL_INITIAL_STATE_REQUIRED")
    else:
        _integer(state.previous_requested, -2048, 2048)
    if type(sample.lat_active) is not bool:
        raise FlowError("BUILTIN_ACTIVE_BOOL_REQUIRED")
    if type(sample.angle_deg) is not float or not isfinite(sample.angle_deg) or abs(sample.angle_deg) > 180:
        raise FlowError("SYNTHETIC_ANGLE_REQUIRED")
    if sample.angle_deg.as_integer_ratio()[1] > 256:
        raise FlowError("SYNTHETIC_DYADIC_ANGLE_REQUIRED")
    try:
        validate_limiter(LimiterCase(sample.requested, state.previous_applied, sample.driver, sample.limits))
    except DomainError as error:
        raise FlowError("SYNTHETIC_LIMITER_SUBSET_REQUIRED") from error


def step(state: State, sample: Sample) -> StepResult:
    validate(state, sample)
    arithmetic = oracle_limiter(LimiterCase(sample.requested, state.previous_applied, sample.driver, sample.limits))
    condition = abs(sample.angle_deg) >= 85
    counter, request = oracle_fault(FaultCase(condition, sample.lat_active, state.angle_counter, 89, 2))
    limited = arithmetic["result"]
    final = limited if sample.lat_active else 0
    next_state = State(state.index + 1, sample.requested, final, counter)
    return StepResult(state.previous_applied, clip_record(arithmetic["clips"][0]),
                      clip_record(arithmetic["clips"][1]), limited, condition, request, final, next_state)
