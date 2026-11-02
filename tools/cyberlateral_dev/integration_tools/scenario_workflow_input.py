"""Bounded original capture before any R40 model work or output publication."""

import platform
import sys
from pathlib import Path

from .scenario_batch_input import BatchInput, prepare_batch
from .scenario_batch_reference_run import _snapshot
from .scenario_compare_input import _owned_files, read_batch


class WorkflowError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def prepare_workflow(inputs: list[Path], output: Path, baseline: Path | None, temporary: Path) -> tuple[list[BatchInput], Path | None, dict | None]:
    items = prepare_batch(inputs, output)
    if (platform.python_implementation() != 'CPython' or platform.python_version() != '3.12.13'
            or sys.platform != 'linux' or (sys.float_info.radix, sys.float_info.mant_dig) != (2, 53)):
        raise WorkflowError('WORKFLOW_RUNTIME')
    if any(item.raw is None for item in items):
        raise WorkflowError('WORKFLOW_INPUT_UNAVAILABLE')
    if baseline is None:
        return items, None, None
    try:
        str(baseline.absolute()).encode('utf-8', errors='strict')
        if output.resolve().is_relative_to(baseline.resolve()):
            raise WorkflowError('WORKFLOW_BASELINE_LOCATION')
    except UnicodeError as error:
        raise WorkflowError('WORKFLOW_PATH_ENCODING') from error
    except (OSError, RuntimeError) as error:
        raise WorkflowError('WORKFLOW_BASELINE_LOCATION') from error
    files, directories = _owned_files(baseline)
    owned = temporary / 'baseline'
    _snapshot(owned, files, directories)
    return items, owned, read_batch(owned)
