"""One internally produced four-step native sequence, no external input reader."""

from dataclasses import asdict

import cyberlateral_dev as p
from integration_tools import owned_message_boundary as b
from integration_tools.semantic_bridge import prepare_semantic_input
from integration_tools.semantic_oracle import oracle_prepare
from integration_tools.semantic_types import ScalarReadback
from integration_tools.sequence_consumption import consume_fixed_step
from integration_tools.sequence_reference import REFERENCE_SHA256
from native_qualification.semantic_demo import compare_preparation, project_preparation
from native_qualification.worker import SCHEMA_SHA, sha


def _frame(car, index: int, state: p.LateralState) -> tuple[b.OwnedFrame, ScalarReadback]:
    stamp = b.Stamp('R23_FIXED_SEQUENCE', index, 'entry_' + str(index))
    cc, cs = car.CarControl.new_message(), car.CarState.new_message()
    cc.actuators.torque = (0.3, -0.25, 0.25, 0.25)[index]
    cc.latActive = (True, True, False, True)[index]
    cs.steeringTorque = 0.0
    cs.steeringAngleDeg = 0.0
    cc_raw, cs_raw = cc.to_bytes(), cs.to_bytes()
    cc_sha, cs_sha = sha(cc_raw), sha(cs_raw)
    frame = b.OwnedFrame(
        'SYNTHETIC_OWNED_MESSAGES_ONLY', 'R11_C8FB9068_4134C0D1_V1', SCHEMA_SHA,
        'SYNTHETIC_CONTEXT_NOT_VEHICLE_AUTHORITY', stamp,
        b.OwnedPayload(stamp, cc.schema.node.id, cc_raw, cc_sha), b.OwnedPayload(stamp, cs.schema.node.id, cs_raw, cs_sha),
        b.FieldLedger(stamp, cc_sha, cs_sha, ('CC.actuators.torque', 'CC.latActive', 'CS.out.steeringAngleDeg', 'CS.out.steeringTorque')),
        b.SettingsSnapshot(stamp, 16, 2, 5, 7, 1, 3),
        b.PreviousSnapshot(stamp, index - 1 if index else None, state.previous_applied, state.angle_counter,
                           state.previous_applied, state.angle_counter, state.previous_requested, 'ENTRY_BEFORE_CURRENT_LIMITER'))
    with car.CarControl.from_bytes(cc_raw) as a, car.CarState.from_bytes(cs_raw) as c:
        readback = ScalarReadback(stamp, cc_sha, cs_sha, 'NATIVE_FLOAT32_DECLARATION',
                                  a.actuators.torque, c.steeringTorque, c.steeringAngleDeg, a.latActive)
    return frame, readback


def demonstrate(car) -> dict:
    rows = []
    state = p.LateralState(0, None, 0, 0)  # Explicit fixed data, not initialization/model work.
    model_steps = 0
    for index in range(4):
        frame, readback = _frame(car, index, state)
        prepared = prepare_semantic_input(frame, readback)
        oracle_sample, oracle_state = oracle_prepare(frame, readback)
        compare_preparation(prepared.sample, prepared.state, oracle_sample, oracle_state)
        output = consume_fixed_step(index, prepared.sample, prepared.state)
        model_steps += 1
        rows.append({'index': index, 'accepted': True, 'prepared': project_preparation(prepared.sample, prepared.state),
                     'model_output': asdict(output), 'model_steps': 1, 'model_expected_match': True, 'oracle_parity': True,
                     'cc_sha256': readback.cc_sha256, 'cs_sha256': readback.cs_sha256,
                     'stamp': asdict(frame.stamp),
                     'state_binding': 'EXPLICIT_FIXED_INITIAL_DATA' if index == 0 else 'PREVIOUS_VERIFIED_MODEL_OUTPUT_NOT_ACTUAL_HISTORY'})
        state = output.next_state
    return {'schema_version': 1, 'scope': 'FOUR_FIXED_SYNTHETIC_NATIVE_MODEL_STEPS_NOT_ACTUAL_HISTORY',
            'cases': rows, 'package_version': p.__version__, 'model_execution': model_steps,
            'model_reference_sha256': REFERENCE_SHA256, 'F61_execution': 0,
            'actual_call_custody': 'NOT_QUALIFIED', 'actual_activation': 'NOT_ALLOWED',
            'R_BUDGET': 'UNRESOLVED', 'STATIC_EVIDENCE_GATE': 'FAIL',
            'time_semantics': 'INVOCATION_ORDER_ONLY_NOT_ELAPSED_TIME'}
