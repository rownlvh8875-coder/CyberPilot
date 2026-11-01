"""Custom declared-synthetic mapping over the unchanged public0.3.0 model."""

from dataclasses import asdict

import cyberlateral_dev as p

from .model_consumption import _plain_output, project_input
from .scenario_input import ScenarioError, ScenarioSpec, validate_spec


def evaluate_scenario(spec: ScenarioSpec) -> dict:
    validate_spec(spec)  # Whole file, not a per-sample prefix simulation.
    if type(p.__version__) is not str or p.__version__ != '0.3.0':
        raise ScenarioError('SCENARIO_MODEL_IDENTITY')
    limits = p.Limits(**asdict(spec.limits))
    initial = p.LateralState(**asdict(spec.initial_state))
    samples = tuple(p.LateralInput(**asdict(sample), limits=limits, provenance='SYNTHETIC_ONLY') for sample in spec.samples)
    try:
        result = p.simulate(samples, initial)
        if (type(result) is not p.SimulationResult or type(result.outputs) is not tuple
                or len(result.outputs) != len(samples) or type(result.next_state) is not p.LateralState):
            raise ScenarioError('SCENARIO_MODEL_RESULT')
        rows, state = [], initial
        for sample, output in zip(samples, result.outputs, strict=True):
            if type(output) is not p.LateralOutput or type(output.next_state) is not p.LateralState:
                raise ScenarioError('SCENARIO_MODEL_RESULT')
            rows.append({'prepared': project_input(sample, state), 'model_output': _plain_output(output)})
            state = output.next_state
        if state != result.next_state:
            raise ScenarioError('SCENARIO_MODEL_RESULT')
        return {'model_steps': len(samples), 'rows': rows, 'final_state': _plain_output(state)}
    except ValueError as error:
        if isinstance(error, ScenarioError):
            raise
        raise ScenarioError('SCENARIO_MODEL_REJECTED') from error
