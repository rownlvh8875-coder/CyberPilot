"""Independent bit-quantizer and original-helper wiring for validated fixtures."""
from flow_types import Sample, State
from quantization_contract import derive_quantization_contract
from quantization_oracle import quantize_reference
from quantization_types import NormalizedSample, NormalizedStep
from source_reference import SourceReference


class NormalizedReference:
    def __init__(self, controller: bytes, helper: bytes):
        self.contract = derive_quantization_contract(controller, helper)
        self._source = SourceReference(controller, helper)

    @property
    def counts(self) -> dict:
        return self._source.counts

    def step(self, state: State, sample: NormalizedSample) -> NormalizedStep:
        integer_trace = quantize_reference(sample.request, sample.limits.STEER_MAX)
        source_sample = Sample(index=sample.index, requested=integer_trace.integer_command,
                               driver=sample.driver, angle_deg=sample.angle_deg, lat_active=sample.lat_active,
                               limits=sample.limits, provenance=sample.provenance)
        original_helper_result = self._source.step(state, source_sample)
        return NormalizedStep(quantization=integer_trace, downstream=original_helper_result)
