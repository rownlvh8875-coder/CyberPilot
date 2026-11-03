"""Owned complete-batch snapshot, existing R38 references and deterministic summary."""

import hashlib
import platform
import sys
import tempfile
from pathlib import Path

from . import scenario_reference_run as reference
from .scenario_batch_reference_summary import summary
from .scenario_compare_input import _manifest, _owned_files, read_batch
from .scenario_input import ScenarioError, parse_scenario
from .scenario_output import GATES, canonical
from .scenario_report_data import ReportError

ROOT = Path(__file__).resolve().parents[1]
SOURCE_FILES = ['integration_tools/' + name + '.py' for name in [
    '__init__', 'scenario_batch_reference_run', 'scenario_batch_reference_summary', 'scenario_compare_input']
] + ['tools/scenario_batch_reference_check.py']
COUNT_KEYS = ('compile_calls', 'selected_definitions_compiled', 'limiter_direct', 'limiter_traced',
              'fault_explicit', 'fault_default', 'traced_clip_calls')


class BatchReferenceError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _source_identity() -> dict:
    try:
        return {'reference': reference._identity(ROOT),
                'batch_checker_source_hashes': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in SOURCE_FILES}}
    except OSError as error:
        raise BatchReferenceError('BATCH_REFERENCE_SOURCE_IDENTITY') from error


def _preflight(source: Path, output: Path) -> None:
    if output.exists() or output.is_symlink():
        raise BatchReferenceError('BATCH_REFERENCE_OUTPUT_EXISTS')
    if not output.parent.is_dir():
        raise BatchReferenceError('BATCH_REFERENCE_OUTPUT_PARENT')
    try:
        for value in [source, output, ROOT]:
            str(value.absolute()).encode('utf-8', errors='strict')
        destination = output.resolve()
        if destination.is_relative_to(ROOT.resolve()):
            raise BatchReferenceError('BATCH_REFERENCE_OUTPUT_LOCATION')
    except UnicodeError as error:
        raise BatchReferenceError('BATCH_REFERENCE_PATH_ENCODING') from error
    except (OSError, RuntimeError) as error:
        raise BatchReferenceError('BATCH_REFERENCE_OUTPUT_LOCATION') from error
    try:
        resolved = source.resolve()
    except (OSError, RuntimeError) as error:
        raise BatchReferenceError('BATCH_REFERENCE_INPUT_FILE') from error
    if destination.is_relative_to(resolved):
        raise BatchReferenceError('BATCH_REFERENCE_OUTPUT_LOCATION')
    if (platform.python_implementation() != 'CPython' or platform.python_version() != '3.12.13'
            or sys.platform != 'linux' or (sys.float_info.radix, sys.float_info.mant_dig) != (2, 53)):
        raise BatchReferenceError('BATCH_REFERENCE_RUNTIME')


def _snapshot(path: Path, files: dict[str, bytes], directories: set[str]) -> None:
    try:
        path.mkdir()
        for name in sorted(directories):
            (path / name).mkdir()
        for name, raw in files.items():
            with (path / name).open('xb') as stream:
                stream.write(raw)
    except OSError as error:
        raise BatchReferenceError('BATCH_REFERENCE_SNAPSHOT') from error


def _case(metadata: dict) -> dict:
    return {'case_id': metadata['case_id'], 'scenario_id': metadata['scenario_id'],
            'source_status': metadata['status'], 'status': None,
            'rejection_code': metadata['rejection_code'], 'observed_rejection_code': None,
            'report': None, 'reference_steps': 0, 'difference_count': None, 'first_difference': None, 'error_code': None}


def _rejection(row: dict, raw: bytes | None) -> None:
    if raw is None:
        row['status'] = 'INPUT_REJECTION_UNVERIFIED'
        return
    try:
        parse_scenario(raw)
    except ScenarioError as error:
        row['observed_rejection_code'] = error.code
    row['status'] = 'INPUT_REJECTION_CONFIRMED' if row['observed_rejection_code'] == row['rejection_code'] else 'REJECTION_MISMATCH'


def _status(cases: list[dict]) -> str:
    statuses = {row['status'] for row in cases}
    if 'ERROR' in statuses:
        return 'ERROR'
    if statuses & {'DIFFERENT', 'REJECTION_MISMATCH'}:
        return 'DIFFERENT'
    if 'INPUT_REJECTION_UNVERIFIED' in statuses:
        return 'INCOMPLETE'
    if 'MATCH' not in statuses:
        return 'NO_COMPLETED_CASES'
    return 'MATCH_WITH_INPUT_REJECTIONS' if 'INPUT_REJECTION_CONFIRMED' in statuses else 'MATCH'


def exit_code(record: dict) -> int:
    if record['status'] in {'MATCH', 'MATCH_WITH_INPUT_REJECTIONS'}:
        return 0
    return 2 if record['status'] == 'ERROR' else 1


def _publish(output: Path, files: dict[str, bytes]) -> None:
    files['SHA256SUMS.txt'] = _manifest(files)
    try:
        output.mkdir(exist_ok=False)
        for directory in sorted({str(Path(name).parent) for name in files} - {'.'}):
            (output / directory).mkdir(exist_ok=False)
        # The completion record is written last. A marker alone is never success:
        # require canonical JSON and every root/nested checksum, even on errors.
        order = sorted(set(files) - {'BATCH_REFERENCE_CHECK.json'}) + ['BATCH_REFERENCE_CHECK.json']
        for name in order:
            with (output / name).open('xb') as stream:
                stream.write(files[name])
    except OSError as error:
        raise BatchReferenceError('BATCH_REFERENCE_PUBLICATION_FAILED') from error


def check_batch(input_path: Path, output_path: Path) -> dict:
    try:
        _preflight(input_path, output_path)
    except BatchReferenceError:
        raise
    except (OSError, ValueError) as error:
        raise BatchReferenceError('BATCH_REFERENCE_IO') from error
    owned, directories = _owned_files(input_path)
    with tempfile.TemporaryDirectory(prefix='cyberlateral-r39-owned-') as temporary:
        work = Path(temporary)
        snapshot = work / 'input'
        _snapshot(snapshot, owned, directories)
        batch = read_batch(snapshot)  # Every late case checked before any worker.
        identity = _source_identity()
        cases = []
        published = {}
        successful = []
        for item in batch['cases']:
            metadata = item['metadata']
            row = _case(metadata)
            if metadata['status'] == 'REJECTED':
                _rejection(row, owned.get(metadata['snapshot']))
            else:
                target = work / metadata['case_id']
                try:
                    checked = reference.check_saved(snapshot / metadata['data'], target)
                    child_files = {metadata['case_id'] + '/' + name: (target / name).read_bytes()
                                   for name in ['REFERENCE_CHECK.json', 'SHA256SUMS.txt']}
                    row.update(status=checked['status'], reference_steps=checked['reference_steps'],
                               difference_count=checked['difference_count'], first_difference=checked['first_difference'],
                               report=metadata['case_id'] + '/REFERENCE_CHECK.json')
                    published.update(child_files)
                    successful.append(checked)
                except (reference.ReferenceCheckError, ReportError, OSError) as error:
                    row.update(status='ERROR', reference_steps=None, report=None, difference_count=None, first_difference=None,
                               error_code='REFERENCE_IO' if isinstance(error, OSError) else error.code)
            cases.append(row)
        if _source_identity() != identity:
            raise BatchReferenceError('BATCH_REFERENCE_SOURCE_CHANGED')
        first = next(({'case_id': row['case_id'], **row['first_difference']}
                      for row in cases if row['first_difference'] is not None), None)
        result = {'schema_version': 1, 'contract_id': 'F70UGZ_R39_SAVED_BATCH_REFERENCE_CHECK_V1',
                  'status': _status(cases), 'input_count': len(cases), 'completed_cases': batch['record']['completed'],
                  'matched_cases': sum(row['status'] == 'MATCH' for row in cases),
                  'different_cases': sum(row['status'] == 'DIFFERENT' for row in cases),
                  'error_cases': sum(row['status'] == 'ERROR' for row in cases),
                  'input_rejections_confirmed': sum(row['status'] == 'INPUT_REJECTION_CONFIRMED' for row in cases),
                  'input_rejections_unverified': sum(row['status'] == 'INPUT_REJECTION_UNVERIFIED' for row in cases),
                  'rejection_mismatch_cases': sum(row['status'] == 'REJECTION_MISMATCH' for row in cases),
                  'numerical_difference_count': sum(row['difference_count'] for row in successful),
                  'first_difference': first, 'reference_steps': sum(row['reference_steps'] for row in successful),
                  'reference_helper_counts': {key: sum(row['reference_helper_counts'][key] for row in successful) for key in COUNT_KEYS},
                  'reference_steps_accounting': 'SUCCESSFUL_REPORTS_ONLY_FAILED_WORK_MAY_BE_NONZERO',
                  'reference_identity': identity, 'input_root_manifest_sha256': batch['root_manifest_sha256'],
                  'input_portable_manifest_sha256': batch['portable_manifest_sha256'],
                  'new_model_executions': 0, 'cases': cases, 'gates': dict(GATES),
                  'claim': 'BOUNDED_SYNTHETIC_SELECTED_SOURCE_PARITY_NOT_WHOLE_CONTROLLER_VEHICLE_OR_ORIGIN_APPROVAL',
                  'initial_history': 'INDEPENDENT_PER_CASE_DECLARED_NOT_AUTHENTICATED',
                  'input_observation': 'BOUNDED_OWNED_BYTES_NOT_ATOMIC_OS_SNAPSHOT',
                  'exactness': 'TYPED_CANONICAL_AND_HEX_NO_TOLERANCE',
                  'time_semantics': 'INVOCATION_ORDER_ONLY_NOT_ELAPSED_TIME'}
        published.update({'BATCH_REFERENCE_CHECK.json': canonical(result), 'SUMMARY_KO.md': summary(result)})
        _publish(output_path, published)
    return result
