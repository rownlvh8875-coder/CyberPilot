"""Opt-in fixed R28 adapter qualification, separate from pure DEV verification."""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from native_qualification.run import compare_observations
from native_qualification.worker import canonical, sha, verify_experiment, verify_inputs

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ['integration_tools/native_adapter.py', 'integration_tools/owned_message_boundary.py',
           'integration_tools/semantic_bridge.py', 'integration_tools/semantic_oracle.py', 'integration_tools/semantic_types.py',
           'native_qualification/adapter_checks.py', 'native_qualification/adapter_oracle.py', 'native_qualification/adapter_runtime.py',
           'native_qualification/adapter_worker.py', 'native_qualification/adapter_run.py',
           'native_qualification/run.py', 'native_qualification/worker.py']


def qualify(python: Path, wheel: Path, package_wheel: Path, output: Path, *, enabled: bool = False) -> dict:
    if output.exists() or output.is_symlink():
        raise FileExistsError('OUTPUT_EXISTS')
    if type(enabled) is not bool:
        raise ValueError('ADAPTER_EXPLICIT_BOOL')
    if not enabled:
        raise ValueError('ADAPTER_OPT_IN_REQUIRED')
    if not output.parent.is_dir():
        raise ValueError('ADAPTER_PARENT_REQUIRED')
    verify_experiment(False, True, package_wheel)
    schema = ROOT / 'reference/car.capnp'
    verify_inputs(wheel, schema)
    if not python.is_file() or not os.access(python, os.X_OK):
        raise ValueError('ADAPTER_PYTHON_PATH')
    before = {name: sha((ROOT / name).read_bytes()) for name in SOURCES}
    records = []
    for _ in range(2):
        with tempfile.TemporaryDirectory(prefix='r28-empty-cwd-') as cwd:
            result = subprocess.run([str(python.absolute()), '-I', '-B', str(ROOT / 'native_qualification/adapter_worker.py'),
                                     '--wheel', str(wheel.absolute()), '--schema', str(schema), '--package-wheel', str(package_wheel.absolute())],
                                    cwd=cwd, capture_output=True, timeout=45, check=False)
        if result.returncode:
            raise ValueError('ADAPTER_WORKER_FAILED:' + result.stderr.decode(errors='replace')[-8000:])
        record = json.loads(result.stdout)
        if canonical(record) != result.stdout or set(record) != {'observations', 'receipt'}:
            raise ValueError('NONCANONICAL_WORKER_RECORD')
        observations = record['observations']
        if (observations['checks']['tests_run'] != 15 or observations['checks']['failures'] != 0
                or observations['checks']['errors'] != 0 or observations['closed_context_checks'] != 3
                or observations['status'] != 'F70UGZ_R28_CONTROLLED_SYNTHETIC_NATIVE_ADAPTER_PASS'
                or observations['model_execution'] != 0 or observations['F61_execution'] != 0):
            raise ValueError('ADAPTER_CHECK_COVERAGE')
        records.append(record)
    observations_raw = compare_observations(records[0]['observations'], records[1]['observations'])
    if before != {name: sha((ROOT / name).read_bytes()) for name in SOURCES}:
        raise ValueError('ADAPTER_SOURCE_CHANGED')
    summary = dict(records[0]['observations'], observations_sha256=sha(observations_raw), worker_processes=2,
                   tests_per_worker=15, tool_sources=before, byte_identical_observations=True)
    files = {'OBSERVATIONS.json': observations_raw, 'SUMMARY.json': canonical(summary),
             'RECEIPT_1.json': canonical(records[0]['receipt']), 'RECEIPT_2.json': canonical(records[1]['receipt'])}
    output.mkdir(exist_ok=False)
    for name, raw in sorted(files.items()):
        (output / name).write_bytes(raw)
    (output / 'SHA256SUMS.txt').write_text(''.join(sha(raw) + '  ' + name + '\n' for name, raw in sorted(files.items())))
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--controlled-synthetic-adapter', action='store_true')
    parser.add_argument('--python', type=Path, required=True)
    parser.add_argument('--wheel', type=Path, required=True)
    parser.add_argument('--package-wheel', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        summary = qualify(args.python, args.wheel, args.package_wheel, args.output, enabled=args.controlled_synthetic_adapter)
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        print('REJECTED:' + str(error), file=sys.stderr)
        return 2
    print(summary['status'])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
