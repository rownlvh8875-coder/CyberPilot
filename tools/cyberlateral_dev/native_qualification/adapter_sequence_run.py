"""Explicit two-profile R29 runner; no generic input, subset or installation mode."""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from native_qualification.adapter_run import SOURCES as R28_SOURCES
from native_qualification.adapter_sequence_validation import validate_observations
from native_qualification.run import compare_observations
from native_qualification.worker import canonical, sha, verify_experiment, verify_inputs

ROOT = Path(__file__).resolve().parents[1]
SOURCES = sorted({*R28_SOURCES, 'integration_tools/adapter_sequence.py', 'integration_tools/model_consumption.py',
                  'integration_tools/sequence_consumption.py', 'integration_tools/sequence_reference.py',
                  'integration_tools/negative_cycle_consumption.py', 'integration_tools/negative_cycle_reference.py',
                  'integration_tools/fixed_model_reference.py', 'reference/r23_sequence_expected_v1.json',
                  'reference/r26_negative_cycle_expected_v1.json', 'native_qualification/adapter_sequence_worker.py',
                  'native_qualification/adapter_sequence_run.py', 'native_qualification/adapter_sequence_validation.py'})


def qualify(python: Path, wheel: Path, package_wheel: Path, output: Path, *, enabled: bool = False) -> dict:
    if output.exists() or output.is_symlink():
        raise FileExistsError('OUTPUT_EXISTS')
    if type(enabled) is not bool:
        raise ValueError('CHAIN_EXPLICIT_BOOL')
    if not enabled:
        raise ValueError('CHAIN_OPT_IN_REQUIRED')
    if not output.parent.is_dir():
        raise ValueError('CHAIN_PARENT_REQUIRED')
    verify_experiment(False, True, package_wheel)
    schema = ROOT / 'reference/car.capnp'
    verify_inputs(wheel, schema)
    if not python.is_file() or not os.access(python, os.X_OK):
        raise ValueError('CHAIN_PYTHON_PATH')
    before = {name: sha((ROOT / name).read_bytes()) for name in SOURCES}
    records = []
    for _ in range(2):
        with tempfile.TemporaryDirectory(prefix='r29-empty-cwd-') as cwd:
            result = subprocess.run([str(python.absolute()), '-I', '-B', str(ROOT / 'native_qualification/adapter_sequence_worker.py'),
                                     '--wheel', str(wheel.absolute()), '--schema', str(schema), '--package-wheel', str(package_wheel.absolute())],
                                    cwd=cwd, capture_output=True, timeout=45, check=False)
        if result.returncode:
            raise ValueError('CHAIN_WORKER_FAILED:' + result.stderr.decode(errors='replace')[-8000:])
        record = json.loads(result.stdout)
        if canonical(record) != result.stdout or set(record) != {'observations', 'receipt'}:
            raise ValueError('NONCANONICAL_WORKER_RECORD')
        validate_observations(record['observations'])
        records.append(record)
    observations = compare_observations(records[0]['observations'], records[1]['observations'])
    if before != {name: sha((ROOT / name).read_bytes()) for name in SOURCES}:
        raise ValueError('CHAIN_SOURCE_CHANGED')
    summary = {'status': records[0]['observations']['status'], 'observations_sha256': sha(observations),
               'worker_processes': 2, 'profile_count': 2, 'model_execution_per_worker': 103, 'model_execution': 206,
               'model_execution_scope': 'TWO_R29_QUALIFICATION_WORKERS_NOT_UNIT_TEST_OR_STAGE_TOTAL',
               'byte_identical_observations': True, 'tool_sources': before,
               'F61_execution': 0, 'r_calculation': 0, 'dt_calculation': 0, 'actual_input': 'NOT_ALLOWED',
               'R_BUDGET': 'UNRESOLVED', 'STATIC_EVIDENCE_GATE': 'FAIL'}
    files = {'OBSERVATIONS.json': observations, 'SUMMARY.json': canonical(summary),
             'RECEIPT_1.json': canonical(records[0]['receipt']), 'RECEIPT_2.json': canonical(records[1]['receipt'])}
    output.mkdir(exist_ok=False)
    for name, raw in sorted(files.items()):
        (output / name).write_bytes(raw)
    (output / 'SHA256SUMS.txt').write_text(''.join(sha(raw) + '  ' + name + '\n' for name, raw in sorted(files.items())))
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixed-adapter-model-sequences', action='store_true')
    parser.add_argument('--python', type=Path, required=True)
    parser.add_argument('--wheel', type=Path, required=True)
    parser.add_argument('--package-wheel', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        summary = qualify(args.python, args.wheel, args.package_wheel, args.output, enabled=args.fixed_adapter_model_sequences)
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        print('REJECTED:' + str(error), file=sys.stderr)
        return 2
    print(summary['status'])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
