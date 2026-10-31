"""Copy declared Float32-origin scalars to synthetic input records, never compute."""

import re
import struct
from math import isfinite

import cyberlateral_dev as p

from .owned_message_boundary import OwnedBoundaryError, OwnedFrame, Stamp, prepare_owned_frame
from .semantic_types import PreparedSemanticInput, ScalarReadback


class SemanticBridgeError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise SemanticBridgeError(code)


def prepare_semantic_input(frame: OwnedFrame, readback: ScalarReadback) -> PreparedSemanticInput:
    try:
        prepare_owned_frame(frame)
    except OwnedBoundaryError as error:
        raise SemanticBridgeError('SEMANTIC_ENVELOPE:' + error.code) from error
    _require(type(readback) is ScalarReadback and type(readback.stamp) is Stamp, 'SEMANTIC_READBACK_TYPE')
    stamp = readback.stamp
    _require(type(stamp.sequence_id) is str and re.fullmatch('[A-Za-z0-9_-]{1,64}', stamp.sequence_id) is not None
             and type(stamp.capture_id) is str and re.fullmatch('[A-Za-z0-9_-]{1,64}', stamp.capture_id) is not None
             and type(stamp.invocation_index) is int and 0 <= stamp.invocation_index <= 4095
             and stamp == frame.stamp
             and type(readback.cc_sha256) is str and readback.cc_sha256 == frame.cc.payload_sha256
             and type(readback.cs_sha256) is str and readback.cs_sha256 == frame.cs.payload_sha256
             and type(readback.representation) is str and readback.representation == 'NATIVE_FLOAT32_DECLARATION', 'SEMANTIC_BINDING')
    for value, bound, dyadic in [(readback.request, 1, False), (readback.driver, 1024, True), (readback.angle_deg, 180, True)]:
        _require(type(value) is float and isfinite(value) and abs(value) <= bound
                 and (not dyadic or value.as_integer_ratio()[1] <= 256), 'SEMANTIC_DOMAIN')
    _require(type(readback.lat_active) is bool, 'SEMANTIC_DOMAIN')
    for value in (readback.request, readback.driver, readback.angle_deg):
        if type(value) is not float:
            raise SemanticBridgeError('SEMANTIC_DOMAIN')
        _require(struct.unpack('!f', struct.pack('!f', value))[0].hex() == value.hex(), 'SEMANTIC_PRECISION')
    _require(type(p.__version__) is str and p.__version__ == '0.3.0', 'SEMANTIC_TARGET_VERSION')
    settings, previous = frame.settings, frame.previous
    limits = p.Limits(settings.steer_max, settings.delta_up, settings.delta_down, settings.driver_allowance,
                      settings.driver_factor, settings.driver_multiplier)
    sample = p.LateralInput(stamp.invocation_index, readback.request, readback.driver, readback.angle_deg,
                            readback.lat_active, limits, 'SYNTHETIC_ONLY')
    state = p.LateralState(stamp.invocation_index, previous.previous_requested, previous.previous_applied, previous.angle_counter)
    return PreparedSemanticInput('F70UGZ_R21_SYNTHETIC_SEMANTIC_BRIDGE_V1', frame.stamp, sample, state,
                                 'DECLARED_READBACK_BINDING_NOT_AUTHENTICATED_NATIVE_CUSTODY',
                                 'EXACT_SUPPLIED_FLOAT32_PROMOTED_TO_PYTHON_FLOAT', 'INVOCATION_ORDER_ONLY_NOT_ELAPSED_TIME')
