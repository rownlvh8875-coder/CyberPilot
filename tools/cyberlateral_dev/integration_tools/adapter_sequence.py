"""Two registered synthetic adapter→DEV model chains, never arbitrary history."""

from dataclasses import asdict

import cyberlateral_dev as p

from . import negative_cycle_reference, sequence_reference
from .model_consumption import project_input
from .native_adapter import PreparedNativeInput, SyntheticSpec, _SyntheticAdapter
from .negative_cycle_consumption import consume_negative_cycle_step
from .owned_message_boundary import PreviousSnapshot, SettingsSnapshot, Stamp
from .semantic_types import PreparedSemanticInput
from .sequence_consumption import consume_fixed_step


class SequenceError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _profile(profile_id: str):
    if type(profile_id) is not str:
        raise SequenceError('CHAIN_PROFILE')
    if profile_id == 'SIGN_CHANGE_4':
        return 4, sequence_reference, consume_fixed_step
    if profile_id == 'NEGATIVE_CYCLE_99':
        return 99, negative_cycle_reference, consume_negative_cycle_step
    raise SequenceError('CHAIN_PROFILE')


def profile_count(profile_id: str) -> int:
    return _profile(profile_id)[0]


def consume_prepared(profile_id: str, index: int, prepared: PreparedNativeInput) -> p.LateralOutput:
    count, _, consume = _profile(profile_id)
    if type(index) is not int or not 0 <= index < count:
        raise SequenceError('CHAIN_INDEX')
    if type(prepared) is not PreparedNativeInput or type(prepared.prepared) is not PreparedSemanticInput:
        raise SequenceError('CHAIN_PREPARATION')
    inner = prepared.prepared
    metadata = [(prepared.read_claim, 'INTERNALLY_CONSTRUCTED_OWNED_SYNTHETIC_BYTES_READ_WITHIN_CONTEXT'),
                (inner.contract_id, 'F70UGZ_R21_SYNTHETIC_SEMANTIC_BRIDGE_V1'),
                (inner.custody_claim, 'DECLARED_READBACK_BINDING_NOT_AUTHENTICATED_NATIVE_CUSTODY'),
                (inner.precision_claim, 'EXACT_SUPPLIED_FLOAT32_PROMOTED_TO_PYTHON_FLOAT'),
                (inner.time_semantics, 'INVOCATION_ORDER_ONLY_NOT_ELAPSED_TIME')]
    if any(type(value) is not str or value != expected for value, expected in metadata):
        raise SequenceError('CHAIN_PREPARATION')
    stamp = inner.stamp
    if (type(stamp) is not Stamp or type(stamp.sequence_id) is not str or stamp.sequence_id != 'R29_' + profile_id
            or type(stamp.invocation_index) is not int or stamp.invocation_index != index
            or type(stamp.capture_id) is not str or stamp.capture_id != 'entry_' + str(index)):
        raise SequenceError('CHAIN_STAMP')
    # Existing consumers enforce the entire pinned input before p.step and the
    # entire pinned output afterwards. No fallback, retry or second invocation.
    return consume(index, inner.sample, inner.state)


def _spec(profile_id: str, index: int, state: p.LateralState) -> SyntheticSpec:
    stamp = Stamp('R29_' + profile_id, index, 'entry_' + str(index))
    settings = SettingsSnapshot(stamp, 16, 2, 5, 7, 1, 3)
    previous = PreviousSnapshot(stamp, index - 1 if index else None, state.previous_applied, state.angle_counter,
                                state.previous_applied, state.angle_counter, state.previous_requested, 'ENTRY_BEFORE_CURRENT_LIMITER')
    if profile_id == 'SIGN_CHANGE_4':
        requests = (float.fromhex('0x1.333334p-2'), -0.25, 0.25, 0.25)
        return SyntheticSpec(stamp, settings, previous, requests[index], 0.0, 0.0, index != 2)
    return SyntheticSpec(stamp, settings, previous, -1.0, 8.5, -84.5 if index == 92 else -85.0, index != 94)


def run_registered_sequence(adapter: _SyntheticAdapter, profile_id: str) -> dict:
    count, reference, _ = _profile(profile_id)
    if type(adapter) is not _SyntheticAdapter:
        raise SequenceError('CHAIN_ADAPTER_TYPE')
    from native_qualification.adapter_oracle import expected
    from native_qualification.worker import canonical
    state = p.LateralState(0, None, 0, 0)
    rows = []
    for index in range(count):
        spec = _spec(profile_id, index, state)
        handle = adapter.construct(spec)
        frame = adapter.inspect(handle)
        prepared = adapter.prepare(handle)
        oracle_sample, oracle_state = expected(frame, spec.request, spec.driver, spec.angle_deg, spec.lat_active)
        actual = project_input(prepared.prepared.sample, prepared.prepared.state)
        if canonical(actual) != canonical(project_input(oracle_sample, oracle_state)):
            raise SequenceError('CHAIN_CONVERSION_ORACLE')
        output = consume_prepared(profile_id, index, prepared)
        rows.append({'index': index, 'stamp': asdict(frame.stamp), 'prepared': actual,
                     'model_output': asdict(output), 'model_steps': 1, 'oracle_parity': True,
                     'cc_sha256': frame.cc.payload_sha256, 'cs_sha256': frame.cs.payload_sha256,
                     'read_claim': prepared.read_claim,
                     'state_binding': 'EXPLICIT_FIXED_INITIAL_DATA' if index == 0 else 'PREVIOUS_VERIFIED_MODEL_OUTPUT_NOT_ACTUAL_HISTORY'})
        state = output.next_state
    return {'profile_id': profile_id, 'reference_sha256': reference.REFERENCE_SHA256,
            'model_execution': len(rows), 'initial_state': {'index': 0, 'previous_requested': None, 'previous_applied': 0, 'angle_counter': 0},
            'final_state': asdict(state), 'cases': rows}
