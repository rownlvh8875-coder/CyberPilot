"""Counterfactual computed-state chain, not repaired declarations or actual replay."""

from dataclasses import dataclass, field
from typing import cast

import cyberlateral_dev as model

from .limiter_snapshot import SyntheticLimiterSnapshotV1
from .synthetic_model_input import ModelInputError, PreparedSyntheticModelInputV1, SyntheticModelContextV1, prepare_model_input
from .synthetic_transition_check import TransitionCheckError, _next_state


class SequenceRolloutError(ValueError):
    """Fixed ordinal diagnostics; a failed model call may have nonzero work."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class SyntheticRolloutDifferenceV1:
    field: str
    declared: int
    computed: int


@dataclass(frozen=True, slots=True)
class SyntheticRolloutStepV1:
    prepared: PreparedSyntheticModelInputV1
    entry_state: model.LateralState
    output: model.LateralOutput
    entry_differences: tuple[SyntheticRolloutDifferenceV1, ...]
    output_differences: tuple[SyntheticRolloutDifferenceV1, ...]
    status: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, 'status', 'DIFFERENT' if self.entry_differences or self.output_differences else 'MATCH')


@dataclass(frozen=True, slots=True)
class SyntheticSequenceRolloutV1:
    frames: tuple[SyntheticLimiterSnapshotV1, ...]
    contexts: tuple[SyntheticModelContextV1, ...]
    steps: tuple[SyntheticRolloutStepV1, ...] = field(init=False)
    initial_declared_state: model.LateralState = field(init=False)
    final_computed_state: model.LateralState = field(init=False)
    status: str = field(init=False)
    entry_differing_transition_indices: tuple[int, ...] = field(init=False)
    output_differing_transition_indices: tuple[int, ...] = field(init=False)
    differing_transition_indices: tuple[int, ...] = field(init=False)
    checked_transition_count: int = field(init=False)
    synthetic_model_steps: int = field(init=False)
    contract_id: str = field(default='CORE27_COUNTERFACTUAL_COMPUTED_STATE_ROLLOUT_V1', init=False)
    validation_claim: str = field(default='COUNTERFACTUAL_COMPUTED_STATE_CHAIN_NOT_SOURCE_OR_PREHISTORY_PROOF', init=False)
    state_feed_rule: str = field(default='FIRST_DECLARED_ENTRY_THEN_COMPUTED_NEXT_STATE_NO_RESEED', init=False)
    computed_state_fed: bool = field(default=True, init=False)
    first_frame_transition_checked: bool = field(default=False, init=False)
    prehistory_checked: bool = field(default=False, init=False)
    source_identity_reauthenticated: bool = field(default=False, init=False)
    v4_payload_allowed: bool = field(default=False, init=False)
    f61_input_allowed: bool = field(default=False, init=False)
    actual_activation_allowed: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        steps = _run(self)
        entries = tuple(i for i, row in enumerate(steps) if row.entry_differences)
        outputs = tuple(i for i, row in enumerate(steps) if row.output_differences)
        differences = tuple(i for i, row in enumerate(steps) if row.status == 'DIFFERENT')
        for name, value in (('steps', steps), ('initial_declared_state', steps[0].entry_state),
                            ('final_computed_state', steps[-1].output.next_state),
                            ('entry_differing_transition_indices', entries), ('output_differing_transition_indices', outputs),
                            ('differing_transition_indices', differences), ('status', 'DIFFERENT' if differences else 'MATCH'),
                            ('checked_transition_count', len(steps)), ('synthetic_model_steps', len(steps))):
            object.__setattr__(self, name, value)


def _need(condition: bool, code: str) -> None:
    if not condition:
        raise SequenceRolloutError(code)


def _differences(fields: tuple[tuple[str, int, int], ...]) -> tuple[SyntheticRolloutDifferenceV1, ...]:
    return tuple(SyntheticRolloutDifferenceV1(name, declared, computed) for name, declared, computed in fields if declared != computed)


def _run(value: SyntheticSequenceRolloutV1) -> tuple[SyntheticRolloutStepV1, ...]:
    _need(type(value) is SyntheticSequenceRolloutV1, 'ROLLOUT_TYPE')
    frames, contexts = value.frames, value.contexts
    _need(type(frames) is tuple and type(contexts) is tuple, 'ROLLOUT_CONTAINER')
    _need(2 <= len(frames) <= 4096 and len(contexts) == len(frames) - 1, 'ROLLOUT_COUNT')
    prepared = []
    for i, context in enumerate(contexts):
        try:
            prepared.append(prepare_model_input(frames[i], frames[i + 1], context))
        except ModelInputError as error:
            raise SequenceRolloutError(f'ROLLOUT_INPUT:{i}:' + error.code) from error
    for i in range(1, len(contexts)):
        _need(contexts[i].model_index == contexts[i - 1].model_index + 1, f'ROLLOUT_MODEL_ORDER:{i}')
    state, steps = prepared[0].model_state, []
    for i, item in enumerate(prepared):
        try:
            output = model.step(item.model_input, state)
        except (ValueError, ArithmeticError) as error:
            raise SequenceRolloutError(f'ROLLOUT_MODEL_FAILURE:{i}:WORK_MAY_BE_NONZERO') from error
        try:
            next_state = _next_state(output, item.context.model_index)
        except TransitionCheckError as error:
            raise SequenceRolloutError(f'ROLLOUT_MODEL_RESULT:{i}:' + error.code + ':WORK_MAY_BE_NONZERO') from error
        declared = item.model_state
        entries = _differences((('entry_previous_requested', cast(int, declared.previous_requested), cast(int, state.previous_requested)),
                                ('entry_previous_applied', declared.previous_applied, state.previous_applied),
                                ('entry_angle_counter', declared.angle_counter, state.angle_counter)))
        outputs = _differences((('saved_limited_state', item.current.saved_limited_state, next_state.previous_applied),
                                ('saved_angle_counter', item.current.saved_angle_counter, next_state.angle_counter)))
        steps.append(SyntheticRolloutStepV1(item, state, output, entries, outputs))
        state = next_state
    return tuple(steps)


def rollout_synthetic_sequence(frames: object, contexts: object) -> SyntheticSequenceRolloutV1:
    """Preflight all declarations, then seed once and feed computed state only."""
    return SyntheticSequenceRolloutV1(cast(tuple[SyntheticLimiterSnapshotV1, ...], frames),
                                      cast(tuple[SyntheticModelContextV1, ...], contexts))
