"""Check complete saved R31 results against a separate selected-source reference."""

import hashlib
import platform
import subprocess
import sys
import tempfile
from pathlib import Path

from .scenario_compare_data import DETAIL_LIMIT, _changes
from .scenario_output import GATES, canonical, render_outputs
from .scenario_report_data import IMPORTED, ReportError, _files, _json, _spec, decode_report

ROOT = Path(__file__).resolve().parents[1]
OBSERVED = ['project/scenario_reference.py', 'tools/scenario_reference_worker.py',
            'tools/scenario_reference_check.py',
            'integration_tools/scenario_reference_run.py', 'integration_tools/scenario_report_data.py',
            'integration_tools/scenario_input.py', 'integration_tools/scenario_output.py',
            'integration_tools/scenario_compare_data.py', 'integration_tools/verify.py', 'IMPORTED_ARTIFACT.json']


class ReferenceCheckError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _identity(root: Path) -> dict:
    from .verify import verify_imports

    try:
        record = _json((root / 'IMPORTED_ARTIFACT.json').read_bytes())
        if type(record) is not dict or type(record.get('imported_files')) is not dict:
            raise ValueError('IMPORTED_MANIFEST_SHAPE')
        imported = verify_imports(root)
        if canonical(imported) != canonical(IMPORTED):
            raise ValueError('IMPORTED_REFERENCE_IDENTITY')
        # Include every exact imported hash as well as the new/reused orchestration.
        paths = sorted(set(record['imported_files']) | set(OBSERVED))
        return {'imported': imported, 'observed_source_hashes': {name: _sha((root / name).read_bytes()) for name in paths}}
    except (OSError, ValueError, KeyError) as error:
        raise ReferenceCheckError('REFERENCE_SOURCE_IDENTITY') from error


def _launch(raw: bytes) -> dict:
    try:
        with tempfile.TemporaryDirectory(prefix='cyberlateral-r38-cwd-') as cwd:
            process = subprocess.run([sys.executable, '-I', '-B', ROOT / 'tools/scenario_reference_worker.py'],
                                     input=raw, capture_output=True, timeout=60, cwd=cwd, check=False)
        if process.returncode or process.stderr:
            raise ReferenceCheckError('REFERENCE_WORKER_FAILED')
        if len(process.stdout) > 32 * 1024 * 1024:
            raise ReferenceCheckError('REFERENCE_WORKER_RESULT')
        try:
            return _json(process.stdout)
        except ValueError as error:
            raise ReferenceCheckError('REFERENCE_WORKER_RESULT') from error
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ReferenceCheckError('REFERENCE_WORKER_FAILED') from error


def _validate_reference(expected, count: int, counts: dict, spec, producer_identity: dict, receipt: dict) -> None:
    if (type(expected) is not dict or expected.keys() != {'rows', 'final_state', 'reference_steps', 'helper_counts',
                                                        'numpy_version', 'forbidden_modules_loaded'}
            or canonical(expected['helper_counts']) != canonical(counts) or type(expected['reference_steps']) is not int
            or expected['reference_steps'] != count or expected['numpy_version'] != '2.5.3'
            or expected['forbidden_modules_loaded'] != [] or type(expected['rows']) is not list
            or len(expected['rows']) != count):
        raise ReferenceCheckError('REFERENCE_WORKER_RESULT')
    try:
        # Reuse exact complete-row/schema/carry validation, without opening paths or
        # computing model arithmetic. In particular prepared sample and state must
        # match the validated input and the reference's own preceding next_state.
        reference_record = {key: expected[key] for key in ['rows', 'final_state']}
        reference_record['model_steps'] = count
        decode_report(render_outputs(spec, reference_record, producer_identity, receipt))
    except (ValueError, TypeError, KeyError) as error:
        raise ReferenceCheckError('REFERENCE_WORKER_RESULT') from error


def _preflight(input_path: Path, output_path: Path) -> None:
    if output_path.exists() or output_path.is_symlink():
        raise ReferenceCheckError('REFERENCE_OUTPUT_EXISTS')
    if not output_path.parent.is_dir():
        raise ReferenceCheckError('REFERENCE_OUTPUT_PARENT')
    try:
        output = output_path.resolve()
        if output.is_relative_to(ROOT.resolve()):
            raise ReferenceCheckError('REFERENCE_OUTPUT_LOCATION')
    except (OSError, RuntimeError) as error:
        raise ReferenceCheckError('REFERENCE_OUTPUT_LOCATION') from error
    try:
        resolved_input = input_path.resolve()
    except (OSError, RuntimeError) as error:
        raise ReportError('REPORT_INPUT_FILE') from error
    if output.is_relative_to(resolved_input):
        raise ReferenceCheckError('REFERENCE_OUTPUT_LOCATION')
    if (platform.python_implementation() != 'CPython' or platform.python_version() != '3.12.13'
            or sys.platform != 'linux' or (sys.float_info.radix, sys.float_info.mant_dig) != (2, 53)):
        raise ReferenceCheckError('REFERENCE_RUNTIME')


def check_saved(input_path: Path, output_path: Path) -> dict:
    try:
        _preflight(input_path, output_path)
    except (ReferenceCheckError, ReportError):
        raise
    except (OSError, ValueError) as error:
        raise ReferenceCheckError('REFERENCE_IO') from error
    owned = _files(input_path)
    data = decode_report(owned)  # Full late-input/cross-record checks, no reference/model work.
    source, saved = _json(owned['INPUT.json']), _json(owned['RESULTS.json'])
    spec = _spec(source)
    identity = _identity(ROOT)
    expected = _launch(owned['INPUT.json'])
    if _identity(ROOT) != identity:
        raise ReferenceCheckError('REFERENCE_SOURCE_CHANGED')
    count = len(spec.samples)
    counts = {'compile_calls': 1, 'selected_definitions_compiled': 2, 'limiter_direct': 0,
              'limiter_traced': count, 'fault_explicit': count, 'fault_default': 0, 'traced_clip_calls': 2 * count}
    _validate_reference(expected, count, counts, spec, saved['identity'], _json(owned['RECEIPT.json']))
    differences = []
    total = 0
    for change in _changes({key: expected[key] for key in ['rows', 'final_state']},
                           {key: saved[key] for key in ['rows', 'final_state']}, ''):
        total += 1
        change['field'] = change['field'].removeprefix('.')
        if len(differences) < DETAIL_LIMIT:
            differences.append(change)
    result = {'schema_version': 1, 'contract_id': 'F70UGZ_R38_SAVED_SCENARIO_REFERENCE_CHECK_V1',
              'status': 'DIFFERENT' if total else 'MATCH', 'scenario_id': spec.scenario_id,
              'claim': 'BOUNDED_DECLARED_SYNTHETIC_SELECTED_SOURCE_PARITY_NOT_WHOLE_CONTROLLER_VEHICLE_OR_ORIGIN_APPROVAL',
              'input_source_hashes': data['source_hashes'], 'reference_identity': identity,
              'reference_expected_sha256': _sha(canonical({key: expected[key] for key in ['rows', 'final_state']})),
              'reference_steps': count, 'reference_helper_counts': counts,
              'reference_forbidden_modules_loaded': expected['forbidden_modules_loaded'],
              'reference_runtime': {'python': platform.python_version(), 'numpy': expected['numpy_version']},
              'initial_history': 'EXPLICIT_SYNTHETIC_DECLARATION_NOT_AUTHENTICATED',
              'exactness': 'TYPED_CANONICAL_AND_HEX_NO_TOLERANCE', 'time_semantics': 'INVOCATION_ORDER_ONLY_NOT_ELAPSED_TIME',
              'difference_count': total, 'detail_limit': DETAIL_LIMIT, 'details_truncated': total > len(differences),
              'first_difference': differences[0] if differences else None, 'differences': differences,
              'new_model_executions': 0, 'gates': dict(GATES)}
    raw = canonical(result)
    files = {'REFERENCE_CHECK.json': raw, 'SHA256SUMS.txt': (_sha(raw) + '  REFERENCE_CHECK.json\n').encode()}
    try:
        output_path.mkdir(exist_ok=False)
        for name in ['SHA256SUMS.txt', 'REFERENCE_CHECK.json']:
            with (output_path / name).open('xb') as stream:
                stream.write(files[name])
    except OSError as error:
        raise ReferenceCheckError('REFERENCE_PUBLICATION_FAILED') from error
    return result
