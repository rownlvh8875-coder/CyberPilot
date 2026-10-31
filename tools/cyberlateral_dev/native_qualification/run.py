"""Opt-in observation runner; no native import in the parent or pure DEV gate."""

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from native_qualification.worker import canonical, sha, verify_experiment, verify_inputs

ROOT = Path(__file__).resolve().parents[1]


def compare_observations(first: dict, second: dict) -> bytes:
    if canonical(first) != canonical(second):
        raise ValueError('OBSERVATIONS_DIFFER')
    return canonical(first)


def qualify(python: Path, wheel: Path, output: Path, *, owned_boundary: bool = False,
            semantic_bridge: bool = False, package_wheel: Path | None = None) -> dict:
    if output.exists() or output.is_symlink():
        raise FileExistsError('OUTPUT_EXISTS')
    verify_experiment(owned_boundary, semantic_bridge, package_wheel)
    schema = ROOT / 'reference/car.capnp'
    verify_inputs(wheel, schema)
    processes = []
    for _ in range(2):
        with tempfile.TemporaryDirectory(prefix='r19-empty-cwd-') as cwd:
            mode = ['--owned-boundary'] if owned_boundary else []
            if semantic_bridge and package_wheel is not None:
                mode = ['--semantic-bridge', '--package-wheel', str(package_wheel.absolute())]
            result = subprocess.run([str(python.absolute()), '-I', '-B', str(ROOT / 'native_qualification/worker.py'),
                                     '--wheel', str(wheel.absolute()), '--schema', str(schema), *mode],
                                    cwd=cwd, capture_output=True, timeout=45, check=False)
        if result.returncode:
            raise ValueError('NATIVE_WORKER_FAILED:' + result.stderr.decode(errors='replace')[-4000:])
        record = json.loads(result.stdout)
        if canonical(record) != result.stdout or set(record) != {'observations', 'receipt'}:
            raise ValueError('NONCANONICAL_WORKER_RECORD')
        processes.append(record)
    observations = compare_observations(processes[0]['observations'], processes[1]['observations'])
    summary = {'status': 'F70UGZ_R19_OBSERVATIONS_REPRODUCED_READER_STILL_BLOCKED',
               'observations_sha256': sha(observations), 'worker_processes': 2, 'byte_identical_observations': True,
               'native_reader': 'NOT_IMPLEMENTED', 'actual_input': 'NOT_ALLOWED',
               'R_BUDGET': 'UNRESOLVED', 'STATIC_EVIDENCE_GATE': 'FAIL',
               'tool_sources': {p.name: sha(p.read_bytes()) for p in [Path(__file__), ROOT / 'native_qualification/worker.py']},
               'F61_execution': 0, 'model_execution': 0, 'r_calculation': 0, 'dt_calculation': 0}
    if owned_boundary:
        summary['status'] = 'F70UGZ_R20_OWNED_SYNTHETIC_BOUNDARY_REFERENCE_PASS'
        summary['tool_sources'].update({name: sha((ROOT / name).read_bytes()) for name in
                                        ['native_qualification/owned_demo.py', 'integration_tools/owned_message_boundary.py']})
    if semantic_bridge:
        summary['status'] = 'F70UGZ_R21_SYNTHETIC_SEMANTIC_BRIDGE_ORACLE_PASS'
        summary['tool_sources'].update({name: sha((ROOT / name).read_bytes()) for name in
                                        ['native_qualification/semantic_demo.py', 'native_qualification/owned_demo.py',
                                         'integration_tools/semantic_bridge.py', 'integration_tools/semantic_oracle.py',
                                         'integration_tools/semantic_types.py', 'integration_tools/owned_message_boundary.py']})
    output.mkdir(parents=True, exist_ok=False)
    files = {'OBSERVATIONS.json': observations, 'SUMMARY.json': canonical(summary),
             'RECEIPT_1.json': canonical(processes[0]['receipt']), 'RECEIPT_2.json': canonical(processes[1]['receipt'])}
    for name, raw in sorted(files.items()):
        (output / name).write_bytes(raw)
    (output / 'SHA256SUMS.txt').write_text(''.join(sha(raw) + '  ' + name + '\n' for name, raw in sorted(files.items())))
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--python', type=Path, required=True, help='Separate pinned native venv interpreter')
    parser.add_argument('--wheel', type=Path, required=True, help='Exact downloaded wheel; never installed by this tool')
    parser.add_argument('--output', type=Path, required=True, help='New data-only output directory')
    parser.add_argument('--owned-boundary', action='store_true', help='Explicit R20 closed owned-message experiment, not an external reader')
    parser.add_argument('--semantic-bridge', action='store_true', help='Explicit R21 closed semantic/oracle experiment, no model execution')
    parser.add_argument('--package-wheel', type=Path, help='Exact sealed public wheel, required ONLY for --semantic-bridge')
    args = parser.parse_args()
    try:
        summary = qualify(args.python, args.wheel, args.output, owned_boundary=args.owned_boundary,
                           semantic_bridge=args.semantic_bridge, package_wheel=args.package_wheel)
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        print('REJECTED:' + str(error), file=sys.stderr)
        return 2
    print(summary['status'])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
