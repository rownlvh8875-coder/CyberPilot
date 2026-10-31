"""One exact registered negative-angle/driver step, not a generic vehicle API."""

import cyberlateral_dev as p

from . import driver_reference as reference
from .model_consumption import ConsumptionError, _canonical, _plain_output, project_input


def consume_driver_step(index: int, sample: p.LateralInput, state: p.LateralState) -> p.LateralOutput:
    expected = reference.expected_input(index)
    if type(p.__version__) is not str or p.__version__ != '0.3.0':
        raise ConsumptionError('CONSUMPTION_PACKAGE_VERSION')
    if _canonical(project_input(sample, state)) != _canonical(expected):
        raise ConsumptionError('DRIVER_INPUT_MISMATCH')
    output = p.step(sample, state)
    if type(output) is not p.LateralOutput:
        raise ConsumptionError('CONSUMPTION_OUTPUT_TYPE')
    if _canonical(_plain_output(output)) != _canonical(reference.expected_output(index)):
        raise ConsumptionError('DRIVER_OUTPUT_MISMATCH')
    return output
