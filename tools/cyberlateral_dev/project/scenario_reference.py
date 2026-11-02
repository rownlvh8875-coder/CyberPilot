"""Independent reference sequence; no public model arithmetic or state feedback."""

from dataclasses import asdict


def reference_values(spec) -> dict:
    from integration_tools.scenario_input import validate_spec

    validate_spec(spec)  # Whole input before reference imports/helper initialization.
    from domain import Limits
    from flow_types import State
    from normalized_reference import NormalizedReference
    from output_oracle import project_reference
    from quantization_types import NormalizedSample
    from v1_helpers import ROOT

    reference = NormalizedReference((ROOT / 'reference/carcontroller.py').read_bytes(),
                                    (ROOT / 'reference/lateral.py').read_bytes())
    limits = Limits(**asdict(spec.limits))
    state = State(**asdict(spec.initial_state))
    rows = []
    for sample in spec.samples:
        prepared = {'sample': {'index': sample.index, 'request_hex': sample.request.hex(),
                               'driver_hex': sample.driver.hex(), 'angle_hex': sample.angle_deg.hex(),
                               'lat_active': sample.lat_active, 'limits': list(asdict(limits).values()),
                               'provenance': 'SYNTHETIC_ONLY'}, 'state': asdict(state)}
        item = NormalizedSample(sample.index, sample.request, sample.driver, sample.angle_deg,
                                sample.lat_active, limits, 'SYNTHETIC_ONLY')
        trace = reference.step(state, item)
        next_state = trace.downstream.next_state
        output = {'projection': project_reference(trace.downstream.final_command, limits.STEER_MAX),
                  'steer_request': trace.downstream.steer_request, 'next_state': asdict(next_state), 'trace': asdict(trace)}
        rows.append({'prepared': prepared, 'model_output': output})
        state = next_state  # Never use any recorded model output as reference state.
    return {'rows': rows, 'final_state': asdict(state), 'reference_steps': len(rows), 'helper_counts': reference.counts}
