"""One explicit counterfactual model input, not a computed or captured transition."""

import struct
from dataclasses import dataclass, field
from math import isfinite
from typing import cast

import cyberlateral_dev as model
from cyberlateral_dev._r4.request_quantizer import quantize

from .limiter_snapshot import (
    LimiterSnapshotError,
    PreparedSyntheticLimiterPairV1,
    SyntheticLimiterSnapshotV1,
    prepare_limiter_pair,
)


class ModelInputError(ValueError):
    """Fixed rejection code without raw input or a partial derived result."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class SyntheticModelContextV1:
    scope: str
    model_index: int
    previous_integer_request: int
    current_driver: float
    current_angle_deg: float


@dataclass(frozen=True, slots=True)
class PreparedSyntheticModelInputV1:
    previous: SyntheticLimiterSnapshotV1
    current: SyntheticLimiterSnapshotV1
    context: SyntheticModelContextV1
    limiter_pair: PreparedSyntheticLimiterPairV1 = field(init=False)
    model_state: model.LateralState = field(init=False)
    model_input: model.LateralInput = field(init=False)
    contract_id: str = field(default='CORE5_COUNTERFACTUAL_CURRENT_MODEL_INPUT_V1', init=False)
    validation_claim: str = field(default='CURRENT_INPUT_COMPATIBILITY_NOT_DECLARED_OUTPUT_PARITY', init=False)
    synthetic_model_input_allowed: bool = field(default=True, init=False)
    source_identity_reauthenticated: bool = field(default=False, init=False)
    v4_payload_allowed: bool = field(default=False, init=False)
    f61_input_allowed: bool = field(default=False, init=False)
    actual_activation_allowed: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        pair, state, sample = _prepare(self)
        object.__setattr__(self, 'limiter_pair', pair)
        object.__setattr__(self, 'model_state', state)
        object.__setattr__(self, 'model_input', sample)


def _need(condition: bool, code: str) -> None:
    if not condition:
        raise ModelInputError(code)


def _integer(value: object, low: int, high: int) -> bool:
    return type(value) is int and low <= value <= high


def _dyadic(value: object, bound: float) -> bool:
    return type(value) is float and isfinite(value) and abs(value) <= bound and value.as_integer_ratio()[1] <= 256


def _prepare(value: PreparedSyntheticModelInputV1) -> tuple[PreparedSyntheticLimiterPairV1, model.LateralState, model.LateralInput]:
    _need(type(value) is PreparedSyntheticModelInputV1, 'MODEL_INPUT_TYPE')
    try:
        pair = prepare_limiter_pair(value.previous, value.current)
    except LimiterSnapshotError as error:
        raise ModelInputError('MODEL_LIMITER:' + error.code) from error
    context = value.context
    _need(type(context) is SyntheticModelContextV1, 'MODEL_CONTEXT_TYPE')
    _need(type(context.scope) is str and context.scope == 'COUNTERFACTUAL_MODEL_INPUT_ONLY', 'MODEL_SCOPE')
    _need(_integer(context.model_index, 1, 4095), 'MODEL_INDEX')
    _need(_integer(context.previous_integer_request, -2048, 2048), 'MODEL_PREVIOUS_REQUEST')
    _need(_dyadic(context.current_driver, 1024.0), 'MODEL_DRIVER')
    _need(_dyadic(context.current_angle_deg, 180.0), 'MODEL_ANGLE')
    previous, current = pair.previous, pair.current
    _need(not previous.request.request_override and not current.request.request_override, 'MODEL_OVERRIDE')
    _need(previous.request.request_active == previous.inactive_gate_active
          and current.request.request_active == current.inactive_gate_active, 'MODEL_ACTIVE_READS')
    _need(type(model.__version__) is str and model.__version__ == '0.3.0', 'MODEL_VERSION')
    previous_request = struct.unpack('>f', previous.request.requested_binary32)[0]
    current_request = struct.unpack('>f', current.request.requested_binary32)[0]
    _need(context.previous_integer_request == quantize(previous_request, previous.settings.request_scale).integer_command,
          'MODEL_PREVIOUS_REQUEST_MISMATCH')
    settings = current.settings
    limits = model.Limits(settings.limiter_scale, settings.delta_up, settings.delta_down,
                          settings.driver_allowance, settings.driver_factor, settings.driver_multiplier)
    state = model.LateralState(context.model_index, context.previous_integer_request,
                               current.limited_state_at_entry, current.angle_counter_at_entry)
    sample = model.LateralInput(context.model_index, current_request, context.current_driver,
                                context.current_angle_deg, current.inactive_gate_active, limits, 'SYNTHETIC_ONLY')
    return pair, state, sample


def prepare_model_input(previous: object, current: object, context: object) -> PreparedSyntheticModelInputV1:
    """Validate explicit roles; no transition, time delta, rate policy or F61 work."""
    return PreparedSyntheticModelInputV1(cast(SyntheticLimiterSnapshotV1, previous),
                                        cast(SyntheticLimiterSnapshotV1, current), cast(SyntheticModelContextV1, context))
