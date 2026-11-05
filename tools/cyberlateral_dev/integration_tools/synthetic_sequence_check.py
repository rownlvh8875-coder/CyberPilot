"""Bounded adjacent declared diagnostics, never repair or computed-state rollout."""

from dataclasses import dataclass, field
from typing import cast

from .limiter_snapshot import SyntheticLimiterSnapshotV1
from .synthetic_model_input import ModelInputError, SyntheticModelContextV1, prepare_model_input
from .synthetic_transition_check import SyntheticTransitionCheckV1, TransitionCheckError, check_synthetic_transition


class SequenceCheckError(ValueError):
    """Fixed code and optional transition ordinal, never a partial success."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class SyntheticSequenceCheckV1:
    frames: tuple[SyntheticLimiterSnapshotV1, ...]
    contexts: tuple[SyntheticModelContextV1, ...]
    checks: tuple[SyntheticTransitionCheckV1, ...] = field(init=False)
    status: str = field(init=False)
    differing_transition_indices: tuple[int, ...] = field(init=False)
    checked_transition_count: int = field(init=False)
    synthetic_model_steps: int = field(init=False)
    contract_id: str = field(default='CORE7_COUNTERFACTUAL_DECLARED_SEQUENCE_V1', init=False)
    validation_claim: str = field(default='ADJACENT_DECLARED_CURRENT_TRANSITIONS_ONLY_NOT_COMPUTED_ROLLOUT', init=False)
    state_feed_rule: str = field(default='DECLARED_ENTRY_EACH_STEP_NO_REPAIR_OR_COMPUTED_ROLLOUT', init=False)
    first_frame_transition_checked: bool = field(default=False, init=False)
    prehistory_checked: bool = field(default=False, init=False)
    source_identity_reauthenticated: bool = field(default=False, init=False)
    v4_payload_allowed: bool = field(default=False, init=False)
    f61_input_allowed: bool = field(default=False, init=False)
    actual_activation_allowed: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        checks = _check(self)
        differences = tuple(i for i, check in enumerate(checks) if check.status == 'DIFFERENT')
        object.__setattr__(self, 'checks', checks)
        object.__setattr__(self, 'differing_transition_indices', differences)
        object.__setattr__(self, 'status', 'DIFFERENT' if differences else 'MATCH')
        object.__setattr__(self, 'checked_transition_count', len(checks))
        object.__setattr__(self, 'synthetic_model_steps', sum(check.synthetic_model_steps for check in checks))


def _need(condition: bool, code: str) -> None:
    if not condition:
        raise SequenceCheckError(code)


def _check(value: SyntheticSequenceCheckV1) -> tuple[SyntheticTransitionCheckV1, ...]:
    _need(type(value) is SyntheticSequenceCheckV1, 'SEQUENCE_TYPE')
    frames, contexts = value.frames, value.contexts
    _need(type(frames) is tuple and type(contexts) is tuple, 'SEQUENCE_CONTAINER')
    _need(2 <= len(frames) <= 4096 and len(contexts) == len(frames) - 1, 'SEQUENCE_COUNT')
    for i, context in enumerate(contexts):
        try:
            prepare_model_input(frames[i], frames[i + 1], context)
        except ModelInputError as error:
            raise SequenceCheckError(f'SEQUENCE_INPUT:{i}:' + error.code) from error
    for i in range(1, len(contexts)):
        _need(contexts[i].model_index == contexts[i - 1].model_index + 1, f'SEQUENCE_MODEL_ORDER:{i}')
    checks = []
    for i, context in enumerate(contexts):
        try:
            checks.append(check_synthetic_transition(frames[i], frames[i + 1], context))
        except TransitionCheckError as error:
            raise SequenceCheckError(f'SEQUENCE_TRANSITION:{i}:' + error.code) from error
    return tuple(checks)


def check_synthetic_sequence(frames: object, contexts: object) -> SyntheticSequenceCheckV1:
    """Preflight all inputs, then diagnose every adjacent declared transition."""
    return SyntheticSequenceCheckV1(cast(tuple[SyntheticLimiterSnapshotV1, ...], frames),
                                   cast(tuple[SyntheticModelContextV1, ...], contexts))
