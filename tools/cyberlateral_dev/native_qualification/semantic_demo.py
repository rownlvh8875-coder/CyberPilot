"""Eight internally produced native frames, data-only bridge/oracle comparison."""

from dataclasses import asdict

import cyberlateral_dev as p
from integration_tools.semantic_bridge import SemanticBridgeError, prepare_semantic_input
from integration_tools.semantic_oracle import OracleRejection, oracle_prepare
from integration_tools.semantic_types import ScalarReadback
from native_qualification.owned_demo import _make
from native_qualification.worker import canonical, number


def project_preparation(sample: p.LateralInput, state: p.LateralState) -> dict:
    if (type(sample) is not p.LateralInput or type(sample.limits) is not p.Limits or type(state) is not p.LateralState
            or any(type(value) is not float for value in (sample.request, sample.driver, sample.angle_deg))):
        raise ValueError('SEMANTIC_ORACLE_PARITY_TYPE')
    return {'sample': {'index': sample.index, 'request_hex': number(sample.request)['hex'], 'driver_hex': number(sample.driver)['hex'],
                       'angle_hex': number(sample.angle_deg)['hex'], 'lat_active': sample.lat_active,
                       'limits': list(asdict(sample.limits).values()), 'provenance': sample.provenance}, 'state': asdict(state)}


def compare_preparation(sample, state, oracle_sample, oracle_state) -> None:
    if canonical(project_preparation(sample, state)) != canonical(project_preparation(oracle_sample, oracle_state)):
        raise ValueError('SEMANTIC_ORACLE_PARITY')


def demonstrate(car) -> dict:
    rows = []
    fixtures = [
        ('zero', 0.0, False, False, 0.0, 0.0),
        ('rounded_request', 0.3, True, False, 1.5, -7.25),
        ('signed_zero', -0.0, False, False, -0.0, -0.0),
        ('resumed', 0.25, True, True, 2.0, 8.0),
        ('driver_precision_reject', 0.25, True, False, 0.3, 0.0),
        ('angle_precision_reject', 0.25, True, False, 0.0, 0.3),
        ('request_range_reject', 2.0, True, False, 0.0, 0.0),
        ('smallest_subnormal', float.fromhex('0x1p-149'), True, False, 0.0, 0.0),
    ]
    for name, request, active, resumed, driver, angle in fixtures:
        frame, _ = _make(car, name, request, active, resumed, driver=driver, angle=angle)
        with car.CarControl.from_bytes(frame.cc.payload) as cc, car.CarState.from_bytes(frame.cs.payload) as cs:
            readback = ScalarReadback(frame.stamp, frame.cc.payload_sha256, frame.cs.payload_sha256,
                                      'NATIVE_FLOAT32_DECLARATION', cc.actuators.torque, cs.steeringTorque, cs.steeringAngleDeg, cc.latActive)
        row = {'id': name, 'cc_sha256': readback.cc_sha256, 'cs_sha256': readback.cs_sha256}
        try:
            prepared = prepare_semantic_input(frame, readback)
        except SemanticBridgeError as error:
            try:
                oracle_prepare(frame, readback)
            except OracleRejection as other:
                if error.code != other.code:
                    raise ValueError('SEMANTIC_ORACLE_REJECTION_PARITY') from other
                row.update(accepted=False, rejection_code=error.code, oracle_rejection_code=other.code, oracle_parity=True)
            else:
                raise ValueError('SEMANTIC_ORACLE_ACCEPTANCE_PARITY') from error
        else:
            oracle_sample, oracle_state = oracle_prepare(frame, readback)
            compare_preparation(prepared.sample, prepared.state, oracle_sample, oracle_state)
            row.update(accepted=True, prepared=project_preparation(prepared.sample, prepared.state), oracle_parity=True,
                       custody_claim=prepared.custody_claim, precision_claim=prepared.precision_claim)
        rows.append(row)
    return {'schema_version': 1, 'scope': 'CLOSED_SYNTHETIC_SEMANTIC_PREPARATION_NO_MODEL_EXECUTION', 'cases': rows,
            'package_version': p.__version__, 'model_execution': 0, 'F61_execution': 0,
            'actual_call_custody': 'NOT_QUALIFIED', 'actual_activation': 'NOT_ALLOWED',
            'R_BUDGET': 'UNRESOLVED', 'STATIC_EVIDENCE_GATE': 'FAIL',
            'oracle_algorithm': 'INDEPENDENT_INTEGER_SIGNIFICAND_EXPONENT_NOT_STRUCT_ROUNDTRIP',
            'input_structure_only_not_F61': True}
