"""Development-only independent batch/output expectation; never shipped."""
from dataclasses import asdict, astuple

from domain import Limits
from flow_types import State
from output_oracle import project_reference
from quantization_types import NormalizedSample


def expected_simulation(scenario, reference):
    state = State(**asdict(scenario.initial_state))
    outputs = []
    for sample in scenario.samples:
        old = NormalizedSample(sample.index, sample.request, sample.driver, sample.angle_deg,
                               sample.lat_active, Limits(*astuple(sample.limits)), sample.provenance)
        trace = reference.step(state, old)
        outputs.append({'projection': project_reference(trace.downstream.final_command, sample.limits.STEER_MAX),
                        'steer_request': trace.downstream.steer_request, 'next_state': asdict(trace.downstream.next_state),
                        'trace': asdict(trace)})
        state = trace.downstream.next_state
    return {'outputs': tuple(outputs), 'next_state': asdict(state)}
