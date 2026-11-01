"""Sequential independent R31/R32 workers over owned synthetic input snapshots."""

import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path

from .scenario_batch_html import render_index
from .scenario_batch_input import ROOT, BatchError, prepare_batch
from .scenario_output import GATES, canonical

DATA_PORTABLE = ['INPUT.json', 'RESULTS.json', 'TRACE.csv', 'SUMMARY_KO.md']
REPORT_PORTABLE = ['index.html', 'VIEW.json']


def _write_exclusive(path: Path, raw: bytes) -> None:
    with path.open('xb') as stream:
        stream.write(raw)


def _worker(tool: str, source: Path, output: Path, log: Path) -> None:
    try:
        result = subprocess.run([sys.executable, '-I', '-B', ROOT / 'tools' / tool,
                                 '--input', source, '--output', output], capture_output=True, timeout=120, check=False)
    except subprocess.TimeoutExpired as error:
        _write_exclusive(log, (error.stdout or b'') + (error.stderr or b'') + b'\nBATCH_WORKER_TIMEOUT\n')
        raise BatchError('BATCH_WORKER_TIMEOUT') from error
    except OSError as error:
        raise BatchError('BATCH_WORKER_FAILED') from error
    _write_exclusive(log, result.stdout + result.stderr)
    if result.returncode != 0:
        raise BatchError('BATCH_WORKER_FAILED')


def _source_hashes() -> dict[str, str]:
    paths = sorted((ROOT / 'integration_tools').glob('*.py'))
    paths += [ROOT / 'tools' / n for n in ['scenario.py', 'scenario_report.py', 'scenario_batch.py']]
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def _manifest(files: dict[str, bytes]) -> bytes:
    return ''.join(hashlib.sha256(raw).hexdigest() + '  ' + name + '\n' for name, raw in sorted(files.items())).encode()


def _publish_index(output: Path, record: dict, receipt: dict) -> None:
    files = {p.relative_to(output).as_posix(): p.read_bytes() for p in output.rglob('*') if p.is_file()}
    files.update({'BATCH.json': canonical(record), 'index.html': render_index(record), 'RECEIPT.json': canonical(receipt)})
    portable = {name: files[name] for name in ['BATCH.json', 'index.html']}
    for row in record['cases']:
        if row['snapshot'] is not None:
            portable[row['snapshot']] = files[row['snapshot']]
        if row['status'] == 'COMPLETE':
            for directory, names in [(row['data'], DATA_PORTABLE), (row['report'], REPORT_PORTABLE)]:
                for name in names:
                    path = directory + '/' + name
                    portable[path] = files[path]
    files['PORTABLE_SHA256SUMS.txt'] = _manifest(portable)
    manifest = _manifest(files)
    for name in ['index.html', 'RECEIPT.json', 'PORTABLE_SHA256SUMS.txt']:
        _write_exclusive(output / name, files[name])
    _write_exclusive(output / 'SHA256SUMS.txt', manifest)
    _write_exclusive(output / 'BATCH.json', files['BATCH.json'])


def run_batch(inputs: list[Path], output: Path) -> dict:
    items = prepare_batch(inputs, output)
    if (platform.python_implementation() != 'CPython' or platform.python_version() != '3.12.13'
            or sys.platform != 'linux' or (sys.float_info.radix, sys.float_info.mant_dig) != (2, 53)):
        raise BatchError('BATCH_RUNTIME')
    try:
        identity = _source_hashes()
        output.mkdir(exist_ok=False)
        (output / 'inputs').mkdir(exist_ok=False)
        rows: list[dict] = []
        for number, item in enumerate(items, 1):
            case_id = f'case-{number:03d}'
            snapshot_path = output / 'inputs' / f'{case_id}.json'
            snapshot = f'inputs/{case_id}.json' if item.raw is not None else None
            row = {'case_id': case_id, 'input_name': item.label, 'input_sha256': item.digest, 'snapshot': snapshot,
                   'scenario_id': item.spec.scenario_id if item.spec is not None else None,
                   'status': 'REJECTED', 'rejection_code': item.rejection_code, 'model_steps': 0, 'data': None, 'report': None}
            if item.raw is not None:
                _write_exclusive(snapshot_path, item.raw)
            if item.spec is not None:
                case = output / case_id
                case.mkdir(exist_ok=False)
                _worker('scenario.py', snapshot_path, case / 'data', case / 'producer.log')
                _worker('scenario_report.py', case / 'data', case / 'report', case / 'renderer.log')
                try:
                    view = json.loads((case / 'report/VIEW.json').read_bytes())
                    if (view['input_raw_sha256'] != item.digest or view['recorded_model_steps'] != len(item.spec.samples)
                            or view['renderer_model_executions'] != 0):
                        raise BatchError('BATCH_WORKER_RECORD')
                except (ValueError, KeyError, TypeError) as error:
                    raise BatchError('BATCH_WORKER_RECORD') from error
                row.update(status='COMPLETE', rejection_code=None, model_steps=len(item.spec.samples),
                           data=f'{case_id}/data', report=f'{case_id}/report')
            rows.append(row)
        if _source_hashes() != identity:
            raise BatchError('BATCH_SOURCE_CHANGED')
        rejected = sum(r['status'] == 'REJECTED' for r in rows)
        record = {'schema_version': 1, 'contract_id': 'F70UGZ_R33_DECLARED_SYNTHETIC_BATCH_V1',
                  'status': 'BATCH_COMPLETE_WITH_REJECTIONS' if rejected else 'BATCH_COMPLETE',
                  'input_count': len(rows), 'completed': len(rows) - rejected, 'rejected': rejected,
                  'total_model_steps': sum(r['model_steps'] for r in rows), 'renderer_model_executions': 0,
                  'input_order': 'EXPLICIT_ARGUMENT_ORDER', 'state_scope': 'INDEPENDENT_PER_FILE_NO_CROSS_FILE_STATE',
                  'input_origin': 'CALLER_DECLARATION_NOT_AUTHENTICATED', 'time_semantics': 'INVOCATION_ORDER_ONLY_NOT_ELAPSED_TIME',
                  'numerical_claim': 'MODEL_RESULTS_NOT_GENERIC_INDEPENDENT_ORACLE', 'gates': GATES, 'cases': rows}
        receipt = {'schema_version': 1, 'source_root': str(ROOT), 'output_directory': str(output.absolute()),
                   'input_paths': [str(p.absolute()) for p in inputs], 'python_executable': sys.executable,
                   'python_version': platform.python_version(), 'observed_source_hashes': identity,
                   'worker_isolation': 'SEQUENTIAL_FRESH_ISOLATED_PYTHON_WITH_COLD_PRIVATE_CACHE_PER_CLI',
                   'scope': 'COOPERATIVE_PROCESS_FILESYSTEM_NOT_ATOMIC_OS_OR_ORIGIN_ATTESTATION',
                   'original_input_reads': 'ONE_BOUNDED_SNAPSHOT_PER_FILE_BEFORE_ANY_WORKER'}
        _publish_index(output, record, receipt)
        return record
    except OSError as error:
        # Preserve partial output, including an interrupted marker write. Mere
        # marker presence is not success: require canonical record AND checksums.
        raise BatchError('BATCH_PUBLICATION_FAILED') from error
