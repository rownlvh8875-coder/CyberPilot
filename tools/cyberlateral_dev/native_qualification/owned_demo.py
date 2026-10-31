"""Closed synthetic native producer only; no external object/data input reader."""

from dataclasses import asdict, replace

from integration_tools import owned_message_boundary as b
from native_qualification.worker import SCHEMA_SHA, canonical, number, sha


def _read(car, cc: bytes, cs: bytes) -> dict:
    with car.CarControl.from_bytes(cc) as a, car.CarState.from_bytes(cs) as c:
        return {'torque': number(a.actuators.torque), 'latActive': a.latActive,
                'steeringAngleDeg': number(c.steeringAngleDeg), 'steeringTorque': number(c.steeringTorque)}


def _make(car, name: str, torque: float, active: bool, resumed: bool) -> tuple[b.OwnedFrame, dict]:
    stamp = b.Stamp(name, 1 if resumed else 0, name + '_entry')
    cc, cs = car.CarControl.new_message(), car.CarState.new_message()
    writes = []
    cc.actuators.torque = torque
    writes.append('CC.actuators.torque')
    cc.latActive = active
    writes.append('CC.latActive')
    cs.steeringAngleDeg = 0.0
    writes.append('CS.out.steeringAngleDeg')
    cs.steeringTorque = 0.0
    writes.append('CS.out.steeringTorque')
    cc_raw, cs_raw = cc.to_bytes(), cs.to_bytes()
    cc_sha, cs_sha = sha(cc_raw), sha(cs_raw)
    frame = b.OwnedFrame(
        'SYNTHETIC_OWNED_MESSAGES_ONLY', 'R11_C8FB9068_4134C0D1_V1', SCHEMA_SHA,
        'SYNTHETIC_CONTEXT_NOT_VEHICLE_AUTHORITY', stamp,
        b.OwnedPayload(stamp, cc.schema.node.id, cc_raw, cc_sha), b.OwnedPayload(stamp, cs.schema.node.id, cs_raw, cs_sha),
        b.FieldLedger(stamp, cc_sha, cs_sha, tuple(sorted(writes))), b.SettingsSnapshot(stamp, 16, 2, 5, 7, 1, 3),
        b.PreviousSnapshot(stamp, 0 if resumed else None, 3 if resumed else 0, 1 if resumed else 0,
                           3 if resumed else 0, 1 if resumed else 0, 5 if resumed else None, 'ENTRY_BEFORE_CURRENT_LIMITER'),
    )
    prepared = b.prepare_owned_frame(frame)
    before = _read(car, frame.cc.payload, frame.cs.payload)
    # Both mutable builders remain local. Their later mutations cannot change
    # owned immutable bytes; no borrowed reader or builder escapes this function.
    cc.actuators.torque = -1.0
    cc.latActive = not active
    cs.steeringTorque = -4.0
    cs.steeringAngleDeg = 8.0
    builder_after = {'torque': number(cc.actuators.torque), 'latActive': cc.latActive,
                     'steeringTorque': number(cs.steeringTorque), 'steeringAngleDeg': number(cs.steeringAngleDeg)}
    commitment = asdict(frame)
    # Digest the whole metadata envelope plus payload hashes. This is integrity
    # bookkeeping, not authentication; the pure validator never decodes bytes.
    commitment['cc']['payload'] = cc_raw.hex()
    commitment['cs']['payload'] = cs_raw.hex()
    row = {'id': name, 'stamp': asdict(stamp), 'owned_before': before,
           'builder_after': builder_after, 'owned_after': _read(car, frame.cc.payload, frame.cs.payload),
           'cc_payload_sha256': cc_sha, 'cs_payload_sha256': cs_sha, 'envelope_sha256': sha(canonical(commitment)),
           'payload_hashes_unchanged': (cc_sha, cs_sha) == (sha(frame.cc.payload), sha(frame.cs.payload)),
           'written_fields': list(frame.ledger.written_fields), 'settings': asdict(frame.settings),
           'previous': {**asdict(frame.previous), 'origin': 'EXPLICIT_SYNTHETIC_DECLARATION_NOT_REPLAY_VALIDATED'},
           'custody_claim': prepared.custody_claim, 'precision_claim': prepared.precision_claim, 'time_semantics': prepared.time_semantics}
    return frame, row


def _rejection(frame: b.OwnedFrame) -> str:
    try:
        b.prepare_owned_frame(frame)
    except b.OwnedBoundaryError as error:
        return error.code
    raise AssertionError('OWNED_NEGATIVE_CASE_UNEXPECTEDLY_ACCEPTED')


def demonstrate(car) -> dict:
    """Only fixed internal fixtures; car is supplied by the verified worker."""
    frames, rows = [], []
    for args in [('explicit_zero', 0.0, False, False), ('rounded_point_three', 0.3, True, False),
                 ('negative_zero', -0.0, False, False), ('resumed_declaration', 0.25, True, True)]:
        frame, row = _make(car, *args)
        frames.append(frame)
        rows.append(row)
    first, resumed = frames[0], frames[3]
    other_stamp = replace(first.stamp, capture_id='OTHER_CAPTURE')
    cases = {
        'missing_ledger': replace(first, ledger=replace(first.ledger, written_fields=())),
        'wrong_schema': replace(first, cc=first.cs),
        'crossed_settings': replace(first, settings=replace(first.settings, stamp=other_stamp)),
        'crossed_previous': replace(first, previous=replace(first.previous, stamp=other_stamp)),
        'mutated_payload': replace(first, cc=replace(first.cc, payload=first.cc.payload + b'x')),
        'mutable_payload': replace(first, cc=replace(first.cc, payload=bytearray(first.cc.payload))),
        'wrong_previous_index': replace(resumed, previous=replace(resumed.previous, previous_invocation_index=1)),
        'source_model_state_mismatch': replace(resumed, previous=replace(resumed.previous, previous_applied=4)),
        'wrong_stage': replace(first, previous=replace(first.previous, stage='AFTER_LIMITER')),
    }
    omitted = car.CarControl.new_message()
    omitted.init('actuators')
    raw = omitted.to_bytes()
    return {
        'schema_version': 1, 'scope': 'CLOSED_SYNTHETIC_OWNED_NATIVE_DEMONSTRATION',
        'cases': rows, 'rejections': {name: _rejection(frame) for name, frame in sorted(cases.items())},
        'default_ambiguity': {'omitted_wire_sha256': sha(raw), 'explicit_wire_sha256': first.cc.payload_sha256,
                              'wire_equal': raw == first.cc.payload, 'missing_ledger_rejection': _rejection(cases['missing_ledger'])},
        'native_reader': 'NOT_IMPLEMENTED', 'actual_call_custody': 'NOT_QUALIFIED', 'model_execution': 0,
        'repository_import_cache_policy': 'PRIVATE_EMPTY_PREFIX_NO_WRITES',
        'R_BUDGET': 'UNRESOLVED', 'STATIC_EVIDENCE_GATE': 'FAIL', 'actual_activation': 'NOT_ALLOWED',
    }
