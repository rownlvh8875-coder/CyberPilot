"""Fixed three-case synthetic suites; saved checks never import the producer."""

import os
import stat
from contextlib import contextmanager
from pathlib import Path

from .core_sequence_cases import CASE_IDS
from .core_sequence_saved import InspectError, read_saved_sequence_records
from .core_sequence_workflow import WorkflowError, _report, _run_captured
from .scenario_output import GATES

ROOT = Path(__file__).resolve().parents[1]


class SuiteError(ValueError):
    """Fixed role/case diagnostics; no raw caller values or success prefix."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _code(role, detail):
    suffix = '_WORK_MAY_BE_NONZERO' if role == 'GENERATED' else ''
    return 'SUITE_' + role + '_' + detail + suffix


def _path(value: Path, code: str) -> Path:
    if not isinstance(value, Path):
        raise SuiteError(code)
    try:
        path = value.absolute()
        text = str(path)
        text.encode('utf-8', errors='strict')
        if '\0' in text or any(p.is_symlink() for p in (path, *path.parents)):
            raise SuiteError(code)
        return path
    except SuiteError:
        raise
    except (OSError, ValueError, RuntimeError) as error:
        raise SuiteError(code) from error


def _layout(fd, role):
    if set(os.listdir(fd)) != set(CASE_IDS):
        raise SuiteError(_code(role, 'LAYOUT'))
    if any(not stat.S_ISDIR(os.stat(case, dir_fd=fd, follow_symlinks=False).st_mode) for case in CASE_IDS):
        raise SuiteError(_code(role, 'LAYOUT'))


@contextmanager
def _root(path: Path, role: str):
    try:
        target = _path(path, _code(role, 'ROOT'))
        fd = os.open(target, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
        try:
            _layout(fd, role)
            yield target
            _layout(fd, role)
        finally:
            os.close(fd)
    except SuiteError:
        raise
    except (OSError, ValueError, RuntimeError) as error:
        raise SuiteError(_code(role, 'ROOT')) from error


def _capture_suite(path: Path, role: str) -> dict:
    records = {}
    with _root(path, role) as root:
        for case in CASE_IDS:
            try:
                captured = read_saved_sequence_records(root / case)
            except InspectError as error:
                raise SuiteError('SUITE_' + role + ':' + case + ':' + error.code) from error
            if captured['summary']['case_id'] != case:
                raise SuiteError('SUITE_' + role + '_CASE_ID:' + case)
            records[case] = captured
    return records


def _output_root(path: Path) -> Path:
    target = _path(path, 'SUITE_OUTPUT_ROOT')
    try:
        if target.exists():
            raise SuiteError('SUITE_OUTPUT_EXISTS')
        if not target.parent.is_dir():
            raise SuiteError('SUITE_OUTPUT_PARENT')
        if target.resolve().is_relative_to(ROOT.parents[1].resolve()):
            raise SuiteError('SUITE_OUTPUT_LOCATION')
        return target
    except SuiteError:
        raise
    except (OSError, ValueError, RuntimeError) as error:
        raise SuiteError('SUITE_OUTPUT_ROOT') from error


def _summary(mode: str, reports: list, has_baseline: bool) -> dict:
    saved_counts = {status: 0 for status in ('MATCH', 'DIFFERENT', 'REJECTED')}
    comparison_counts = {'NOT_REQUESTED': 0, 'IDENTICAL': 0, 'DIFFERENT': 0}
    differences = {'INPUT': 0, 'RESULT': 0, 'IDENTITY': 0}
    for report in reports:
        saved_counts[report['saved_status']] += 1
        comparison = report['comparison']
        if comparison is None:
            comparison_counts['NOT_REQUESTED'] += 1
        else:
            comparison_counts['DIFFERENT' if comparison['difference_count'] else 'IDENTICAL'] += 1
            for key in differences:
                differences[key] += comparison['difference_counts'][key]
    status = ('SAVED_SUITE_INSPECTED' if not has_baseline else
              'SAVED_SUITE_DIFFERENT' if comparison_counts['DIFFERENT'] else 'SAVED_SUITE_IDENTICAL')
    return {'schema_version': 1, 'contract_id': 'CORE12_CLOSED_SEQUENCE_SUITE_V1', 'mode': mode,
        'execution_requested': mode == 'RUN_CLOSED_SYNTHETIC_SUITE', 'case_ids': list(CASE_IDS), 'case_count': len(reports),
        'all_cases_processed': True, 'suite_status': status, 'baseline_comparison_requested': has_baseline,
        'saved_status_counts': saved_counts, 'comparison_counts': comparison_counts,
        'new_synthetic_model_steps': sum(report['new_synthetic_model_steps'] for report in reports),
        'recorded_model_steps': sum(report['recorded_model_steps'] for report in reports),
        'reader_model_executions': 0, 'reader_reference_executions': 0,
        'difference_count': sum(differences.values()) if has_baseline else None,
        'difference_counts': differences if has_baseline else None,
        'reports': reports, 'gates': dict(GATES), 'source_identity_reauthenticated': False,
        'scope': 'CLOSED_THREE_CASE_SYNTHETIC_SUITE_NOT_VEHICLE_OR_ORIGIN_AUTHORITY'}


def check_closed_suite(input_root: Path, baseline_root: Path | None = None) -> dict:
    """Inspect all three cases with no producer import, file writes or new steps."""
    current = _capture_suite(input_root, 'INPUT')
    baseline = None if baseline_root is None else _capture_suite(baseline_root, 'BASELINE')
    reports = [_report('CHECK_SAVED_ONLY', current[case], None if baseline is None else baseline[case], 0) for case in CASE_IDS]
    return _summary('CHECK_SAVED_SUITE', reports, baseline is not None)


def run_closed_suite(output_root: Path, baseline_root: Path | None = None) -> dict:
    """Preflight the complete baseline before creating output or executing any case."""
    output = _output_root(output_root)
    baseline = None if baseline_root is None else _capture_suite(baseline_root, 'BASELINE')
    if baseline_root is not None:
        try:
            overlaps = output.resolve().is_relative_to(baseline_root.resolve())
        except (OSError, ValueError, RuntimeError) as error:
            raise SuiteError('SUITE_OUTPUT_ROOT') from error
        if overlaps:
            raise SuiteError('SUITE_OUTPUT_BASELINE_OVERLAP_NO_MODEL_EXECUTION')
    try:
        output.mkdir(exist_ok=False)
    except OSError as error:
        raise SuiteError('SUITE_OUTPUT_CREATE_NO_MODEL_EXECUTION') from error
    reports = []
    for case in CASE_IDS:
        try:
            reports.append(_run_captured(case, output / case, None if baseline is None else baseline[case]))
        except WorkflowError as error:
            raise SuiteError('SUITE_RUN:' + case + ':' + error.code + ':WORK_MAY_BE_NONZERO') from error
    # Metadata-only final root closure; never reopen the already captured casefiles.
    with _root(output, 'GENERATED'):
        pass
    return _summary('RUN_CLOSED_SYNTHETIC_SUITE', reports, baseline is not None)


def exit_code(report: dict) -> int:
    return 1 if report['suite_status'] == 'SAVED_SUITE_DIFFERENT' else 0
