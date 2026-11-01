"""One exact registered R24 step, not a generic fault/history or vehicle API."""

import cyberlateral_dev as p

from . import fault_reference as reference
from .model_consumption import ConsumptionError, _canonical, _plain_output, project_input


def consume_fault_step(index: int, sample: p.LateralInput, state: p.LateralState) -> p.LateralOutput:
    expected = reference.expected_input(index)
    if type(p.__version__) is not str or p.__version__ != '0.3.0':
        raise ConsumptionError('CONSUMPTION_PACKAGE_VERSION')
    if _canonical(project_input(sample, state)) != _canonical(expected):
        raise ConsumptionError('FAULT_INPUT_MISMATCH')
    output = p.step(sample, state)
    if type(output) is not p.LateralOutput:
        raise ConsumptionError('CONSUMPTION_OUTPUT_TYPE')
    if _canonical(_plain_output(output)) != _canonical(reference.expected_output(index)):
        raise ConsumptionError('FAULT_OUTPUT_MISMATCH')
    return output
