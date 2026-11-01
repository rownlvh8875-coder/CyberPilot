"""Independent selected-source wiring for already validated synthetic fixtures.

Not a general input-validation API, Controller execution or runtime binding proof.
Never imports the model, its validator or the rational arithmetic backend.
"""
from domain import FaultCase, LimiterCase
from flow_types import Sample, State, StepResult, clip_record
from kernel import Kernel
from source_contract import derive_contract


class SourceReference:
    def __init__(self, controller: bytes, helper: bytes):
        self.contract = derive_contract(controller, helper)
        thresholds = self.contract["thresholds"]
        self._angle = thresholds["MAX_ANGLE"]["value"]
        self._maximum = thresholds["MAX_ANGLE_FRAMES"]["value"]
        self._mismatch = thresholds["MAX_ANGLE_CONSECUTIVE_FRAMES"]["value"]
        self._kernel = Kernel(helper)

    @property
    def counts(self) -> dict:
        return self._kernel.counts

    def step(self, state: State, sample: Sample) -> StepResult:
        # Independently transcribed wiring, not extracted/executed Controller code.
        limited = self._kernel.limiter(LimiterCase(sample.requested, state.previous_applied,
                                                   sample.driver, sample.limits), traced=True)
        fault_condition = abs(sample.angle_deg) >= self._angle
        counter, steer_req = self._kernel.fault(FaultCase(fault_condition, sample.lat_active,
                                                         state.angle_counter, self._maximum, self._mismatch))
        output_command = limited["result"]
        if not sample.lat_active:
            output_command = 0
        next_history = State(state.index + 1, sample.requested, output_command, counter)
        return StepResult(limiter_previous=state.previous_applied,
                          driver_clip=clip_record(limited["clips"][0]), rate_clip=clip_record(limited["clips"][1]),
                          limited_command=limited["result"], fault_condition=fault_condition,
                          steer_request=steer_req, final_command=output_command, next_state=next_history)
