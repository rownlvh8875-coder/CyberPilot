"""Single pure development API. No controller, IO, original helpers or wire output."""
from ._r4.flow_types import State as LateralState
from ._r4.normalized_pipeline import step_normalized
from ._r4.quantization_types import NormalizedSample as LateralInput
from .output_projection import project_output
from .output_types import LateralOutput


def step(sample: LateralInput, state: LateralState) -> LateralOutput:
    trace = step_normalized(state, sample)
    downstream = trace.downstream
    projection = project_output(downstream.final_command, sample.limits.STEER_MAX)
    return LateralOutput(projection, downstream.steer_request, downstream.next_state, trace)
