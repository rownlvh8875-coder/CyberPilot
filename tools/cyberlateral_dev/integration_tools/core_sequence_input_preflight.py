"""Revalidate captured synthetic input semantics, never replay saved outputs."""

from pathlib import Path

from .core_sequence_saved import InspectError, read_saved_sequence_records
from .limiter_snapshot import SyntheticConsumedSettingsV1, SyntheticLimiterSnapshotV1
from .request_snapshot import SyntheticRequestContextV1, SyntheticRequestSnapshotV1
from .synthetic_model_input import ModelInputError, SyntheticModelContextV1, prepare_model_input


class InputPreflightError(ValueError):
    """Saved capture/schema failure; no input verdict or partial prepared data."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _frames(records: list) -> tuple[SyntheticLimiterSnapshotV1, ...]:
    frames = []
    for record in records:
        request = record['request']
        snapshot = SyntheticRequestSnapshotV1(
            SyntheticRequestContextV1(**request['context']), request['sequence'], request['sample_time_ns'],
            bytes.fromhex(request['requested_binary32_be_hex']), request['request_active'],
            request['request_override'], request['reset_since_previous'])
        frames.append(SyntheticLimiterSnapshotV1(snapshot, SyntheticConsumedSettingsV1(**record['settings']),
            **{k: v for k, v in record.items() if k not in ('request', 'settings')}))
    return tuple(frames)


def _receipt(captured: dict, code: str | None, validated: int) -> dict:
    saved = captured['summary']
    return {'schema_version': 1, 'contract_id': 'CORE19_SAVED_SYNTHETIC_INPUT_PREFLIGHT_V1',
        'case_id': saved['case_id'], 'preflight_status': 'INPUTS_COMPATIBLE' if code is None else 'INPUTS_REJECTED',
        'rejection_code': code, 'validated_transition_count': validated, 'declared_transition_count': 3,
        'saved_status': saved['saved_status'], 'saved_rejection_code': saved['saved_rejection_code'],
        'recorded_model_steps': saved['recorded_model_steps'], 'captured_sha256': dict(saved['captured_sha256']),
        'new_synthetic_model_steps': 0, 'new_reference_steps': 0, 'numeric_validation_work': 'NONZERO_NOT_AGGREGATED',
        'source_identity_reauthenticated': False, 'arithmetic_recomputed': False, 'prehistory_checked': False,
        'v4_payload_allowed': False, 'f61_input_allowed': False, 'actual_activation_allowed': False,
        'gates': dict(saved['gates'])}


def preflight_saved_sequence(input_path: Path) -> dict:
    """One bounded CORE9 capture, owned declarations, CORE5 validation; no step."""
    try:
        captured = read_saved_sequence_records(input_path)
    except InspectError as error:
        raise InputPreflightError('INPUT_PREFLIGHT_SAVED:' + error.code) from error
    source = captured['input_record']
    frames = _frames(source['frames'])
    contexts = []
    for i, record in enumerate(source['contexts']):
        texts = (record['current_driver_hex'], record['current_angle_deg_hex'])
        try:
            driver, angle = (float.fromhex(text) for text in texts)
        except (ValueError, OverflowError):
            return _receipt(captured, f'INPUT_PREFLIGHT_FLOAT_ENCODING:{i}', 0)
        if (driver.hex(), angle.hex()) != texts:
            return _receipt(captured, f'INPUT_PREFLIGHT_FLOAT_ENCODING:{i}', 0)
        contexts.append(SyntheticModelContextV1(record['scope'], record['model_index'],
            record['previous_integer_request'], driver, angle))
    for i, context in enumerate(contexts):
        try:
            prepare_model_input(frames[i], frames[i + 1], context)
        except ModelInputError as error:
            return _receipt(captured, f'SEQUENCE_INPUT:{i}:' + error.code, i)
    return _receipt(captured, None, len(contexts))
