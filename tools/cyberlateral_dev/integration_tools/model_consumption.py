"""Exactly one pure DEV step only after a complete preregistered input match."""

import json
from dataclasses import fields
from math import isfinite

import cyberlateral_dev as p
from cyberlateral_dev._r4.flow_types import Clip, Scalar, StepResult
from cyberlateral_dev._r4.quantization_types import NormalizedStep, Quantization
from cyberlateral_dev.output_types import Float32Projection, OutputProjection

from . import fixed_model_reference as reference


class ConsumptionError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def _case(case_id: str) -> None:
    if type(case_id) is not str or case_id not in reference.CASE_IDS:
        raise ConsumptionError('CONSUMPTION_CASE')


def _hex(value: float) -> str:
    if type(value) is not float:
        raise ConsumptionError('CONSUMPTION_INPUT_TYPE')
    return value.hex()


def project_input(sample: p.LateralInput, state: p.LateralState) -> dict:
    if type(sample) is not p.LateralInput or type(state) is not p.LateralState or type(sample.limits) is not p.Limits:
        raise ConsumptionError('CONSUMPTION_INPUT_TYPE')
    limits = [getattr(sample.limits, field.name) for field in fields(sample.limits)]
    if (any(type(v) is not int for v in [sample.index, state.index, state.previous_applied, state.angle_counter, *limits])
            or (state.previous_requested is not None and type(state.previous_requested) is not int)
            or type(sample.lat_active) is not bool or type(sample.provenance) is not str):
        raise ConsumptionError('CONSUMPTION_INPUT_TYPE')
    return {'sample': {'index': sample.index, 'request_hex': _hex(sample.request), 'driver_hex': _hex(sample.driver),
                       'angle_hex': _hex(sample.angle_deg), 'lat_active': sample.lat_active, 'limits': limits,
                       'provenance': sample.provenance},
            'state': {'index': state.index, 'previous_requested': state.previous_requested,
                      'previous_applied': state.previous_applied, 'angle_counter': state.angle_counter}}


def _plain_output(value):
    if any(type(value) is cls for cls in (str, int, bool, type(None))):
        return value
    if type(value) is float:
        if not isfinite(value):
            raise ConsumptionError('CONSUMPTION_OUTPUT_TYPE')
        return value
    if any(type(value) is cls for cls in (p.LateralOutput, p.LateralState, OutputProjection, Float32Projection,
                                          NormalizedStep, Quantization, StepResult, Clip, Scalar)):
        return {field.name: _plain_output(getattr(value, field.name)) for field in fields(value)}
    raise ConsumptionError('CONSUMPTION_OUTPUT_TYPE')


def verify_output(case_id: str, output: p.LateralOutput) -> None:
    _case(case_id)
    if type(output) is not p.LateralOutput:
        raise ConsumptionError('CONSUMPTION_OUTPUT_TYPE')
    if _canonical(_plain_output(output)) != _canonical(reference.expected_output(case_id)):
        raise ConsumptionError('CONSUMPTION_OUTPUT_MISMATCH')


def consume_closed_case(case_id: str, sample: p.LateralInput, state: p.LateralState) -> p.LateralOutput:
    _case(case_id)
    if type(p.__version__) is not str or p.__version__ != '0.3.0':
        raise ConsumptionError('CONSUMPTION_PACKAGE_VERSION')
    if _canonical(project_input(sample, state)) != _canonical(reference.expected_input(case_id)):
        raise ConsumptionError('CONSUMPTION_INPUT_MISMATCH')
    output = p.step(sample, state)
    verify_output(case_id, output)
    return output
