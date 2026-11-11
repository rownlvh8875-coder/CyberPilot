"""Explicit synthetic recording input compatibility, never execution or source proof."""

from copy import deepcopy
from dataclasses import dataclass, field
from typing import cast

from .offline_call_recorder import FinishedSyntheticRecordingV1, RecorderError, _validate_finished
from .synthetic_model_input import ModelInputError, SyntheticModelContextV1, prepare_model_input


class RecordingPreflightError(ValueError):
    """Fixed code and optional transition ordinal, never a partial success."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class SyntheticRecordingInputPreflightV1:
    recording: FinishedSyntheticRecordingV1
    contexts: tuple[SyntheticModelContextV1, ...]
    record_count: int = field(init=False)
    validated_transition_count: int = field(init=False)
    contract_id: str = field(default='CORE46_COUNTERFACTUAL_RECORDING_INPUT_PREFLIGHT_V1', init=False)
    status: str = field(default='INPUTS_COMPATIBLE', init=False)
    validation_claim: str = field(default='DECLARED_INPUT_COMPATIBILITY_NOT_OUTPUT_PARITY_OR_SOURCE_PROOF', init=False)
    time_semantics: str = field(default='ORDER_ONLY_NO_DELTA_OR_PERIOD', init=False)
    numeric_validation_work: str = field(default='NONZERO_NOT_AGGREGATED', init=False)
    new_synthetic_model_steps: int = field(default=0, init=False)
    new_reference_steps: int = field(default=0, init=False)
    first_frame_transition_checked: bool = field(default=False, init=False)
    prehistory_checked: bool = field(default=False, init=False)
    source_identity_reauthenticated: bool = field(default=False, init=False)
    model_input_allowed: bool = field(default=False, init=False)
    v4_payload_allowed: bool = field(default=False, init=False)
    f61_input_allowed: bool = field(default=False, init=False)
    actual_activation_allowed: bool = field(default=False, init=False)

    def __new__(cls, recording: object, contexts: object) -> 'SyntheticRecordingInputPreflightV1':
        _need(cls is SyntheticRecordingInputPreflightV1, 'RECORDING_PREFLIGHT_TYPE')
        return object.__new__(cls)

    def __post_init__(self) -> None:
        count = _validate(self)
        object.__setattr__(self, 'record_count', count)
        object.__setattr__(self, 'validated_transition_count', count - 1)

    def __copy__(self) -> 'SyntheticRecordingInputPreflightV1':
        _validate(self)
        return SyntheticRecordingInputPreflightV1(self.recording, self.contexts)

    def __deepcopy__(self, memo: dict[int, object]) -> 'SyntheticRecordingInputPreflightV1':
        _validate(self)
        clone = SyntheticRecordingInputPreflightV1(deepcopy(self.recording, memo), deepcopy(self.contexts, memo))
        memo[id(self)] = clone
        return clone


def _need(condition: bool, code: str) -> None:
    if not condition:
        raise RecordingPreflightError(code)


def _validate(value: SyntheticRecordingInputPreflightV1) -> int:
    _need(type(value) is SyntheticRecordingInputPreflightV1, 'RECORDING_PREFLIGHT_TYPE')
    try:
        recording = _validate_finished(value.recording)
    except RecorderError as error:
        raise RecordingPreflightError('RECORDING_PREFLIGHT_RECORDING:' + error.code) from None
    contexts = value.contexts
    _need(type(contexts) is tuple, 'RECORDING_PREFLIGHT_CONTEXT_CONTAINER')
    _need(len(contexts) == len(recording.records) - 1, 'RECORDING_PREFLIGHT_CONTEXT_COUNT')
    for i, context in enumerate(contexts):
        try:
            prepare_model_input(recording.records[i], recording.records[i + 1], context)
        except ModelInputError as error:
            raise RecordingPreflightError(f'RECORDING_PREFLIGHT_INPUT:{i}:' + error.code) from None
    for i in range(1, len(contexts)):
        _need(contexts[i].model_index == contexts[i - 1].model_index + 1, f'RECORDING_PREFLIGHT_MODEL_ORDER:{i}')
    return len(recording.records)


def preflight_recording_input(recording: object, contexts: object) -> SyntheticRecordingInputPreflightV1:
    """Revalidate explicit declarations; never decode external bytes, infer or replay."""
    return SyntheticRecordingInputPreflightV1(cast(FinishedSyntheticRecordingV1, recording),
                                             cast(tuple[SyntheticModelContextV1, ...], contexts))
