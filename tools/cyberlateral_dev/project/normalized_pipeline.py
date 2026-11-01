"""Pure synthetic normalized request -> quantization -> R3 state transition."""
from domain import Limits
from flow_types import Sample, State
from quantization_types import NormalizedSample, NormalizedStep
from request_quantizer import QuantizationError, quantize
from state_model import step


def step_normalized(state: State, sample: NormalizedSample) -> NormalizedStep:
    if type(sample) is not NormalizedSample or type(sample.limits) is not Limits:
        raise QuantizationError("EXACT_SYNTHETIC_SAMPLE_AND_LIMITS_REQUIRED")
    if type(sample.provenance) is not str or sample.provenance != "SYNTHETIC_ONLY":
        raise QuantizationError("SYNTHETIC_SCOPE_REQUIRED")
    conversion = quantize(sample.request, sample.limits.STEER_MAX)
    integer_sample = Sample(sample.index, conversion.integer_command, sample.driver,
                            sample.angle_deg, sample.lat_active, sample.limits, sample.provenance)
    return NormalizedStep(conversion, step(state, integer_sample))
