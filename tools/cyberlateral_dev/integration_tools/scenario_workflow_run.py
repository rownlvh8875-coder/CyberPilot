"""Compose existing DEV stages over owned synthetic inputs, never vehicle input."""

import hashlib
import platform
import sys
import tempfile
from pathlib import Path

from . import scenario_batch_reference_run as reference
from . import scenario_batch_run as batch
from .scenario_compare_run import run_comparison
from .scenario_output import GATES, canonical
from .scenario_validate import validate_scenario
from .scenario_workflow_input import WorkflowError, prepare_workflow
from .scenario_workflow_summary import summary


def _source_identity() -> dict:
    return {**batch._source_hashes(),
            'tools/scenario_workflow.py': hashlib.sha256((batch.ROOT / 'tools/scenario_workflow.py').read_bytes()).hexdigest()}


def _write(path: Path, raw: bytes) -> None:
    with path.open('xb') as stream:
        stream.write(raw)


def _status(reference_status: str, regression_status: str | None, rejected: int) -> str:
    if (reference_status not in {'MATCH', 'MATCH_WITH_INPUT_REJECTIONS', 'DIFFERENT', 'INCOMPLETE', 'NO_COMPLETED_CASES', 'ERROR'}
            or regression_status not in {None, 'MATCH', 'DIFFERENT'}):
        raise WorkflowError('WORKFLOW_STAGE_STATUS')
    if reference_status == 'ERROR':
        return 'ERROR'
    if reference_status == 'DIFFERENT':
        return 'REFERENCE_DIFFERENT'
    if regression_status == 'DIFFERENT':
        return 'REGRESSION_DIFFERENT'
    if reference_status in {'INCOMPLETE', 'NO_COMPLETED_CASES'}:
        return reference_status
    return 'VERIFIED_WITH_INPUT_REJECTIONS' if rejected else 'VERIFIED'


def exit_code(record: dict) -> int:
    return 0 if record['status'] == 'VERIFIED' else 2 if record['status'] == 'ERROR' else 1


def _publish(output: Path, record: dict, receipt: dict) -> None:
    files = {p.relative_to(output).as_posix(): p.read_bytes() for p in output.rglob('*') if p.is_file()}
    files.update({'WORKFLOW.json': canonical(record), 'SUMMARY_KO.md': summary(record), 'RECEIPT.json': canonical(receipt)})
    for name in ['SUMMARY_KO.md', 'RECEIPT.json']:
        _write(output / name, files[name])
    _write(output / 'SHA256SUMS.txt', batch._manifest(files))
    _write(output / 'WORKFLOW.json', files['WORKFLOW.json'])


def run_workflow(inputs: list[Path], output: Path, baseline: Path | None = None) -> dict:
    with tempfile.TemporaryDirectory(prefix='cyberlateral-r40-owned-') as temporary:
        items, owned_baseline, baseline_record = prepare_workflow(inputs, output, baseline, Path(temporary))
        identity = _source_identity()
        try:
            output.mkdir(exist_ok=False)
            (output / 'inputs').mkdir(exist_ok=False)
            snapshots, validation = [], []
            for number, item in enumerate(items, 1):
                relative = f'inputs/case-{number:03d}.json'
                path = output / relative
                if item.raw is None:
                    raise WorkflowError('WORKFLOW_INPUT_UNAVAILABLE')
                _write(path, item.raw)
                snapshots.append(path)
                checked = validate_scenario(path)
                if checked['accepted'] != (item.spec is not None) or checked['rejection_code'] != item.rejection_code:
                    raise WorkflowError('WORKFLOW_INPUT_CHANGED')
                validation.append({'case_id': f'case-{number:03d}', 'snapshot': relative, 'validation': checked})
            _write(output / 'VALIDATION.json', canonical({'schema_version': 1, 'contract_id': 'F70UGZ_R40_OWNED_VALIDATION_V1',
                'cases': validation, 'model_executions': 0, 'gates': dict(GATES)}))
            produced = batch.run_batch(snapshots, output / 'batch')
            if [row['input_sha256'] for row in produced['cases']] != [item.digest for item in items]:
                raise WorkflowError('WORKFLOW_INPUT_CHANGED')
            checked = reference.check_batch(output / 'batch', output / 'reference')
            compared = run_comparison(owned_baseline, output / 'batch', output / 'regression') if owned_baseline is not None else None
            if _source_identity() != identity:
                raise WorkflowError('WORKFLOW_SOURCE_CHANGED')
            if any(path.read_bytes() != item.raw for path, item in zip(snapshots, items, strict=True)):
                raise WorkflowError('WORKFLOW_INPUT_CHANGED')
            regression_status = compared['status'] if compared is not None else None
            record = {'schema_version': 1, 'contract_id': 'F70UGZ_R40_DECLARED_SYNTHETIC_WORKFLOW_V1',
                'status': _status(checked['status'], regression_status, produced['rejected']),
                'input_count': produced['input_count'], 'completed': produced['completed'], 'rejected': produced['rejected'],
                'validation_report': 'VALIDATION.json', 'batch_record': 'batch/BATCH.json', 'batch_index': 'batch/index.html',
                'reference_report': 'reference/BATCH_REFERENCE_CHECK.json',
                'regression_report': 'regression/COMPARE.json' if compared is not None else None,
                'reference_status': checked['status'], 'reference_difference_count': checked['numerical_difference_count'],
                'regression_status': regression_status, 'regression_difference_count': compared['difference_count'] if compared is not None else None,
                'model_steps': produced['total_model_steps'], 'reference_steps': checked['reference_steps'],
                'reference_helper_counts': checked['reference_helper_counts'], 'reference_steps_accounting': checked['reference_steps_accounting'],
                'validation_new_model_executions': 0, 'renderer_new_model_executions': 0,
                'reference_new_public_model_executions': checked['new_model_executions'], 'regression_new_model_executions': 0,
                'batch_portable_manifest_sha256': checked['input_portable_manifest_sha256'],
                'baseline_portable_manifest_sha256': baseline_record['portable_manifest_sha256'] if baseline_record is not None else None,
                'observed_dev_source_hashes': identity, 'gates': dict(GATES),
                'claim': 'BOUNDED_DECLARED_SYNTHETIC_SOURCE_PARITY_NOT_GENERIC_ORACLE_OR_VEHICLE_APPROVAL',
                'input_observation': 'OWNED_BYTES_COOPERATIVE_NOT_ATOMIC_OR_ORIGIN_AUTHENTICATION',
                'time_semantics': 'INVOCATION_ORDER_ONLY_NOT_ELAPSED_TIME', 'state_scope': 'INDEPENDENT_PER_FILE_NO_CROSS_FILE_STATE',
                'full_results_scope': 'PRIVATE_RECEIPTS_AND_RAW_SYNTHETIC_INPUTS_NOT_AUTOMATICALLY_SHAREABLE'}
            receipt = {'schema_version': 1, 'source_root': str(batch.ROOT), 'output_directory': str(output.absolute()),
                'input_paths': [str(p.absolute()) for p in inputs], 'baseline_directory': str(baseline.absolute()) if baseline is not None else None,
                'baseline_root_manifest_sha256': baseline_record['root_manifest_sha256'] if baseline_record is not None else None,
                'python_executable': sys.executable, 'python_version': platform.python_version(),
                'original_reads': 'ONE_BOUNDED_RAW_CAPTURE_PER_INPUT_AND_COMPLETE_BASELINE_BEFORE_MODEL',
                'scope': 'PRIVATE_COOPERATIVE_OBSERVATIONS_NOT_OS_OR_VEHICLE_AUTHENTICATION'}
            _publish(output, record, receipt)
            return record
        except OSError as error:
            raise WorkflowError('WORKFLOW_IO') from error
