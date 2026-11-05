"""Explicit closed synthetic execution or saved-only inspection, never vehicle IO."""

from pathlib import Path

from .core_sequence_cases import CASE_IDS
from .core_sequence_compare import _compare_captured
from .core_sequence_saved import InspectError, read_saved_sequence_records
from .scenario_output import GATES, canonical


class WorkflowError(ValueError):
    """Fixed diagnostic, conservatively retaining possibly completed run work."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _read(path: Path, role: str) -> dict:
    try:
        return read_saved_sequence_records(path)
    except InspectError as error:
        suffix = ':WORK_MAY_BE_NONZERO' if role == 'GENERATED' else ''
        raise WorkflowError('WORKFLOW_' + role + ':' + error.code + suffix) from error


def _report(mode, current, baseline, new_steps) -> dict:
    comparison = None if baseline is None else _compare_captured(baseline, current)
    summary = current['summary']
    return {'schema_version': 1, 'contract_id': 'CORE11_CLOSED_SEQUENCE_WORKFLOW_V1', 'mode': mode,
        'execution_requested': mode == 'RUN_CLOSED_SYNTHETIC',
        'workflow_status': 'SAVED_RECORDS_INSPECTED' if comparison is None else comparison['comparison_status'],
        'case_id': summary['case_id'], 'saved_status': summary['saved_status'], 'saved_rejection_code': summary['saved_rejection_code'],
        'recorded_model_steps': summary['recorded_model_steps'], 'new_synthetic_model_steps': new_steps,
        'reader_model_executions': 0, 'reader_reference_executions': 0,
        'inspection': summary, 'baseline_inspection': None if baseline is None else baseline['summary'], 'comparison': comparison,
        'gates': dict(GATES), 'source_identity_reauthenticated': False,
        'scope': 'INTEGRATED_CLOSED_SYNTHETIC_WORKFLOW_NOT_VEHICLE_OR_ORIGIN_AUTHORITY'}


def check_saved_sequence(input_path: Path, baseline: Path | None = None) -> dict:
    """Read each role once with no producer import, new calculation or publication."""
    current = _read(input_path, 'INPUT')
    captured_baseline = None if baseline is None else _read(baseline, 'BASELINE')
    return _report('CHECK_SAVED_ONLY', current, captured_baseline, 0)


def run_closed_sequence(case_id: object, output: Path, baseline: Path | None = None) -> dict:
    """Run one named fixture only after baseline validation, then inspect saved bytes."""
    if type(case_id) is not str or case_id not in CASE_IDS:
        raise WorkflowError('WORKFLOW_CASE')
    captured_baseline = None if baseline is None else _read(baseline, 'BASELINE')
    if baseline is not None and isinstance(output, Path):
        try:
            overlaps = output.resolve().is_relative_to(baseline.resolve())
        except (OSError, ValueError, RuntimeError) as error:
            raise WorkflowError('WORKFLOW_OUTPUT_PATH_NO_MODEL_EXECUTION') from error
        if overlaps:
            raise WorkflowError('WORKFLOW_OUTPUT_BASELINE_OVERLAP_NO_MODEL_EXECUTION')
    # Only explicit run imports this execution path. CORE8 retains output guards.
    from .core_sequence_run import DemoError, run_sequence_case

    try:
        produced = run_sequence_case(case_id, output)
    except DemoError as error:
        raise WorkflowError('WORKFLOW_RUN:' + error.code + ':WORK_MAY_BE_NONZERO') from error
    current = _read(output, 'GENERATED')
    if current['summary']['case_id'] != case_id or canonical(produced) != canonical(current['result_record']):
        raise WorkflowError('WORKFLOW_GENERATED_RECORD_MISMATCH_WORK_MAY_BE_NONZERO')
    return _report('RUN_CLOSED_SYNTHETIC', current, captured_baseline, current['summary']['recorded_model_steps'])


def exit_code(report: dict) -> int:
    """Orchestration/baseline comparison status, not the saved numerical outcome."""
    return 1 if report['workflow_status'] == 'SAVED_PACKAGES_DIFFERENT' else 0
