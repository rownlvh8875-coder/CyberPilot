"""Input-contract preflight only; no model, execution readiness or origin proof."""

from pathlib import Path

from .scenario_input import ScenarioError, read_scenario
from .scenario_output import GATES


def validate_scenario(input_path: Path) -> dict:
    """Describe a bounded validated snapshot, or an original reader rejection."""
    result = {
        'schema_version': 1, 'contract_id': 'F70UGZ_R37_SCENARIO_INPUT_VALIDATION_V1',
        'status': 'SCENARIO_INPUT_REJECTED', 'accepted': False, 'rejection_code': None,
        'validation_scope': 'INPUT_SCHEMA_AND_DOMAIN_ONLY_NOT_MODEL_RUNTIME_OR_ORIGIN',
        'input_origin': 'CALLER_DECLARATION_NOT_AUTHENTICATED',
        'time_semantics': 'INVOCATION_ORDER_ONLY_NOT_ELAPSED_TIME', 'model_executions': 0,
        'input_raw_sha256': None, 'scenario_id': None, 'sample_count': None,
        'first_index': None, 'last_index': None, 'gates': dict(GATES),
    }
    try:
        spec = read_scenario(input_path)
    except ScenarioError as error:
        result['rejection_code'] = error.code
        return result
    result.update(status='SCENARIO_INPUT_VALID', accepted=True, input_raw_sha256=spec.raw_sha256,
                  scenario_id=spec.scenario_id, sample_count=len(spec.samples),
                  first_index=spec.samples[0].index, last_index=spec.samples[-1].index)
    return result
