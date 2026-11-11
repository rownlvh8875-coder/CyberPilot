"""Bounded counterfactual call transactions, not actual source capture or replay."""

from dataclasses import dataclass, field, fields
from typing import cast

from .limiter_snapshot import (
    LimiterSnapshotError,
    SyntheticLimiterSnapshotV1,
    _validate_frame,
    prepare_limiter_pair,
)
from .request_snapshot import (
    RequestSnapshotError,
    SyntheticRequestSnapshotV1,
    _validate_snapshot,
    prepare_request_pair,
)


class RecorderError(ValueError):
    """Fixed rejection code; never forwards input or foreign exception text."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _need(condition: bool, code: str) -> None:
    if not condition:
        raise RecorderError(code)


def _request(value: object) -> SyntheticRequestSnapshotV1:
    _need(type(value) is SyntheticRequestSnapshotV1, 'RECORDER_REQUEST_TYPE')
    request = cast(SyntheticRequestSnapshotV1, value)
    try:
        _validate_snapshot(request)
    except RequestSnapshotError as error:
        raise RecorderError('RECORDER_REQUEST:' + error.code) from None
    return request


def _frame(value: object) -> SyntheticLimiterSnapshotV1:
    _need(type(value) is SyntheticLimiterSnapshotV1, 'RECORDER_FRAME_TYPE')
    frame = cast(SyntheticLimiterSnapshotV1, value)
    _request(frame.request)
    try:
        _validate_frame(frame)
    except LimiterSnapshotError as error:
        raise RecorderError('RECORDER_LIMITER:' + error.code) from None
    return frame


def _pair(previous: SyntheticLimiterSnapshotV1, current: SyntheticLimiterSnapshotV1) -> None:
    try:
        prepare_limiter_pair(previous, current)
    except LimiterSnapshotError as error:
        raise RecorderError('RECORDER_LIMITER:' + error.code) from None


@dataclass(frozen=True, slots=True)
class FinishedSyntheticRecordingV1:
    records: tuple[SyntheticLimiterSnapshotV1, ...]
    schema_version: int = field(default=1, init=False)
    contract_id: str = field(default='CORE41_COUNTERFACTUAL_CALL_RECORDING_V1', init=False)
    scope: str = field(default='COUNTERFACTUAL_RECORDING_ONLY', init=False)
    time_semantics: str = field(default='ORDER_ONLY_NO_DELTA_OR_PERIOD', init=False)
    source_identity_reauthenticated: bool = field(default=False, init=False)
    model_input_allowed: bool = field(default=False, init=False)
    v4_payload_allowed: bool = field(default=False, init=False)
    f61_input_allowed: bool = field(default=False, init=False)
    actual_activation_allowed: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        _validate_finished(self)


def _validate_finished(value: object) -> FinishedSyntheticRecordingV1:
    _need(type(value) is FinishedSyntheticRecordingV1, 'RECORDER_RECORDING_TYPE')
    result = cast(FinishedSyntheticRecordingV1, value)
    for item in fields(FinishedSyntheticRecordingV1):
        if not item.init:
            actual = getattr(result, item.name)
            _need(type(actual) is type(item.default) and actual == item.default, 'RECORDER_METADATA')
    _need(type(result.records) is tuple and 2 <= len(result.records) <= 128, 'RECORDER_RECORDS')
    previous = None
    for record in result.records:
        _frame(record)
        if previous is not None:
            _pair(previous, record)
        previous = record
    return result


class SyntheticCallRecorderV1:
    """Single-thread cooperative declarations; failures permanently close history."""

    __slots__ = ('_capacity', '_pending', '_records', '_state')

    def __init__(self, capacity: int):
        _need(type(capacity) is int and 2 <= capacity <= 128, 'RECORDER_CAPACITY')
        self._capacity = capacity
        self._pending: SyntheticRequestSnapshotV1 | None = None
        self._records: list[SyntheticLimiterSnapshotV1] = []
        self._state = 'OPEN'

    def _guard(self) -> None:
        if self._state != 'OPEN':
            raise RecorderError('RECORDER_' + self._state)

    def begin(self, request: object) -> None:
        self._guard()
        try:
            _need(self._pending is None, 'RECORDER_PENDING')
            _need(len(self._records) < self._capacity, 'RECORDER_OVERFLOW')
            checked = _request(request)
            if self._records:
                try:
                    prepare_request_pair(self._records[-1].request, checked)
                except RequestSnapshotError as error:
                    raise RecorderError('RECORDER_REQUEST:' + error.code) from None
            self._pending = checked
        except RecorderError:
            self._state = 'FAILED'
            raise

    def complete(self, frame: object) -> None:
        self._guard()
        try:
            _need(self._pending is not None, 'RECORDER_NOT_PENDING')
            checked = _frame(frame)
            _need(checked.request == self._pending, 'RECORDER_REQUEST_CHANGED')
            if self._records:
                _pair(self._records[-1], checked)
            self._records.append(checked)
            self._pending = None
        except RecorderError:
            self._state = 'FAILED'
            raise

    def abort(self) -> None:
        self._guard()
        self._state = 'ABORTED'
        self._pending = None

    def finish(self) -> FinishedSyntheticRecordingV1:
        self._guard()
        try:
            _need(self._pending is None, 'RECORDER_INCOMPLETE')
            _need(len(self._records) >= 2, 'RECORDER_TOO_SHORT')
            result = FinishedSyntheticRecordingV1(tuple(self._records))
            self._state = 'CLOSED'
            return result
        except RecorderError:
            self._state = 'FAILED'
            raise
