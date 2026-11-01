"""Independent ratio-based oracle. Precondition: structurally valid R20 envelope."""

import math

import cyberlateral_dev as p

from .owned_message_boundary import OwnedFrame, Stamp
from .semantic_types import ScalarReadback


class OracleRejection(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _binary32_exact(value: float) -> bool:
    numerator, denominator = value.as_integer_ratio()
    magnitude = abs(numerator)
    if magnitude == 0:
        return True
    zeros = (magnitude & -magnitude).bit_length() - 1
    significand = magnitude >> zeros
    least_exponent = zeros - (denominator.bit_length() - 1)
    highest_exponent = magnitude.bit_length() - denominator.bit_length()
    return significand.bit_length() <= 24 and least_exponent >= -149 and highest_exponent <= 127


def oracle_prepare(frame: OwnedFrame, readback: ScalarReadback) -> tuple[p.LateralInput, p.LateralState]:
    if type(readback) is not ScalarReadback or type(readback.stamp) is not Stamp:
        raise OracleRejection('SEMANTIC_READBACK_TYPE')
    stamp = readback.stamp
    for label in (stamp.sequence_id, stamp.capture_id):
        if type(label) is not str or not 1 <= len(label) <= 64 or not all(
                'A' <= c <= 'Z' or 'a' <= c <= 'z' or '0' <= c <= '9' or c in '_-' for c in label):
            raise OracleRejection('SEMANTIC_BINDING')
    if type(stamp.invocation_index) is not int or not 0 <= stamp.invocation_index <= 4095:
        raise OracleRejection('SEMANTIC_BINDING')
    if (stamp.sequence_id, stamp.invocation_index, stamp.capture_id) != (
            frame.stamp.sequence_id, frame.stamp.invocation_index, frame.stamp.capture_id):
        raise OracleRejection('SEMANTIC_BINDING')
    if (type(readback.cc_sha256) is not str or type(readback.cs_sha256) is not str
            or readback.cc_sha256 != frame.cc.payload_sha256 or readback.cs_sha256 != frame.cs.payload_sha256
            or type(readback.representation) is not str or readback.representation != 'NATIVE_FLOAT32_DECLARATION'):
        raise OracleRejection('SEMANTIC_BINDING')
    values = (readback.request, readback.driver, readback.angle_deg)
    if any(type(v) is not float for v in values) or type(readback.lat_active) is not bool:
        raise OracleRejection('SEMANTIC_DOMAIN')
    if not all(math.isfinite(v) for v in values):
        raise OracleRejection('SEMANTIC_DOMAIN')
    if not -1 <= readback.request <= 1 or not -1024 <= readback.driver <= 1024 or not -180 <= readback.angle_deg <= 180:
        raise OracleRejection('SEMANTIC_DOMAIN')
    if readback.driver.as_integer_ratio()[1] > 256 or readback.angle_deg.as_integer_ratio()[1] > 256:
        raise OracleRejection('SEMANTIC_DOMAIN')
    if not all(_binary32_exact(v) for v in values):
        raise OracleRejection('SEMANTIC_PRECISION')
    if type(p.__version__) is not str or p.__version__ != '0.3.0':
        raise OracleRejection('SEMANTIC_TARGET_VERSION')
    return (
        p.LateralInput(index=frame.stamp.invocation_index, request=readback.request, driver=readback.driver,
                       angle_deg=readback.angle_deg, lat_active=readback.lat_active,
                       limits=p.Limits(STEER_MAX=frame.settings.steer_max, STEER_DELTA_UP=frame.settings.delta_up,
                                       STEER_DELTA_DOWN=frame.settings.delta_down, STEER_DRIVER_ALLOWANCE=frame.settings.driver_allowance,
                                       STEER_DRIVER_FACTOR=frame.settings.driver_factor, STEER_DRIVER_MULTIPLIER=frame.settings.driver_multiplier),
                       provenance='SYNTHETIC_ONLY'),
        p.LateralState(index=frame.stamp.invocation_index, previous_requested=frame.previous.previous_requested,
                       previous_applied=frame.previous.previous_applied, angle_counter=frame.previous.angle_counter),
    )
