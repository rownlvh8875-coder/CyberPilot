"""Compare two current saved declarations to one pure synthetic model step."""

from dataclasses import dataclass, field
from typing import cast

import cyberlateral_dev as model

from .limiter_snapshot import SyntheticLimiterSnapshotV1
from .synthetic_model_input import (
    ModelInputError,
    PreparedSyntheticModelInputV1,
    SyntheticModelContextV1,
    prepare_model_input,
)


class TransitionCheckError(ValueError):
    """Fixed code; model work may be nonzero on a failed model call."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class SyntheticTransitionDifferenceV1:
    field: str
    declared: int
    computed: int


@dataclass(frozen=True, slots=True)
class SyntheticTransitionCheckV1:
    previous: SyntheticLimiterSnapshotV1
    current: SyntheticLimiterSnapshotV1
    context: SyntheticModelContextV1
    prepared: PreparedSyntheticModelInputV1 = field(init=False)
    computed_next_state: model.LateralState = field(init=False)
    differences: tuple[SyntheticTransitionDifferenceV1, ...] = field(init=False)
    status: str = field(init=False)
    contract_id: str = field(default='CORE6_COUNTERFACTUAL_CURRENT_TRANSITION_V1', init=False)
    validation_claim: str = field(default='CURRENT_SAVED_STATE_COUNTER_ONLY_NOT_PREHISTORY_OR_SOURCE_PROOF', init=False)
    checked_fields: tuple[str, ...] = field(default=('saved_limited_state', 'saved_angle_counter'), init=False)
    synthetic_model_steps: int = field(default=1, init=False)
    previous_transition_checked: bool = field(default=False, init=False)
    prehistory_checked: bool = field(default=False, init=False)
    source_identity_reauthenticated: bool = field(default=False, init=False)
    v4_payload_allowed: bool = field(default=False, init=False)
    f61_input_allowed: bool = field(default=False, init=False)
    actual_activation_allowed: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        prepared, state, differences = _check(self)
        object.__setattr__(self, 'prepared', prepared)
        object.__setattr__(self, 'computed_next_state', state)
        object.__setattr__(self, 'differences', differences)
        object.__setattr__(self, 'status', 'DIFFERENT' if differences else 'MATCH')


def _need(condition: bool, code: str) -> None:
    if not condition:
        raise TransitionCheckError(code)


def _integer(value: object, low: int, high: int) -> bool:
    return type(value) is int and low <= value <= high


def _next_state(output: model.LateralOutput, index: int) -> model.LateralState:
    _need(type(output) is model.LateralOutput, 'TRANSITION_MODEL_RESULT')
    state = output.next_state
    _need(type(state) is model.LateralState, 'TRANSITION_MODEL_RESULT')
    _need(type(state.index) is int and state.index == index + 1
          and _integer(state.previous_requested, -2048, 2048)
          and _integer(state.previous_applied, -2048, 2048)
          and _integer(state.angle_counter, 0, 90), 'TRANSITION_MODEL_RESULT')
    return state


def _check(value: SyntheticTransitionCheckV1) -> tuple[
    PreparedSyntheticModelInputV1, model.LateralState, tuple[SyntheticTransitionDifferenceV1, ...]
]:
    _need(type(value) is SyntheticTransitionCheckV1, 'TRANSITION_TYPE')
    try:
        prepared = prepare_model_input(value.previous, value.current, value.context)
    except ModelInputError as error:
        raise TransitionCheckError('TRANSITION_INPUT:' + error.code) from error
    try:
        output = model.step(prepared.model_input, prepared.model_state)
    except (ValueError, ArithmeticError) as error:
        raise TransitionCheckError('TRANSITION_MODEL_FAILURE') from error
    state = _next_state(output, prepared.context.model_index)
    current = prepared.current
    differences = tuple(SyntheticTransitionDifferenceV1(name, declared, computed)
                        for name, declared, computed in (
                            ('saved_limited_state', current.saved_limited_state, state.previous_applied),
                            ('saved_angle_counter', current.saved_angle_counter, state.angle_counter),
                        ) if declared != computed)
    return prepared, state, differences


def check_synthetic_transition(previous: object, current: object, context: object) -> SyntheticTransitionCheckV1:
    """Compute once after CORE5 preflight; no repair, history or actual authority."""
    return SyntheticTransitionCheckV1(cast(SyntheticLimiterSnapshotV1, previous),
                                     cast(SyntheticLimiterSnapshotV1, current), cast(SyntheticModelContextV1, context))
