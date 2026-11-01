"""Opt-in observation runner; no native import in the parent or pure DEV gate."""

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from native_qualification.coverage import validate_coverage
from native_qualification.worker import canonical, sha, verify_experiment, verify_inputs

ROOT = Path(__file__).resolve().parents[1]


def compare_observations(first: dict, second: dict) -> bytes:
    if canonical(first) != canonical(second):
        raise ValueError('OBSERVATIONS_DIFFER')
    return canonical(first)


def qualify(python: Path, wheel: Path, output: Path, *, owned_boundary: bool = False,
            semantic_bridge: bool = False, package_wheel: Path | None = None, model_consumption: bool = False,
            model_sequence: bool = False, fault_boundaries: bool = False, driver_boundaries: bool = False,
            negative_cycle: bool = False) -> dict:
    if output.exists() or output.is_symlink():
        raise FileExistsError('OUTPUT_EXISTS')
    verify_experiment(owned_boundary, semantic_bridge, package_wheel, model_consumption, model_sequence, fault_boundaries, driver_boundaries, negative_cycle)
    schema = ROOT / 'reference/car.capnp'
    verify_inputs(wheel, schema)
    processes = []
    for _ in range(2):
        with tempfile.TemporaryDirectory(prefix='r19-empty-cwd-') as cwd:
            mode = ['--owned-boundary'] if owned_boundary else []
            if semantic_bridge and package_wheel is not None:
                mode = ['--semantic-bridge', '--package-wheel', str(package_wheel.absolute())]
            if model_consumption and package_wheel is not None:
                mode = ['--model-consumption', '--package-wheel', str(package_wheel.absolute())]
            if model_sequence and package_wheel is not None:
                mode = ['--model-sequence', '--package-wheel', str(package_wheel.absolute())]
            if fault_boundaries and package_wheel is not None:
                mode = ['--fault-boundaries', '--package-wheel', str(package_wheel.absolute())]
            if driver_boundaries and package_wheel is not None:
                mode = ['--driver-boundaries', '--package-wheel', str(package_wheel.absolute())]
            if negative_cycle and package_wheel is not None:
                mode = ['--negative-cycle', '--package-wheel', str(package_wheel.absolute())]
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
    coverage_mode = 'R22' if model_consumption else 'R23' if model_sequence else 'R24' if fault_boundaries else 'R25' if driver_boundaries else 'R26'
    counts = [validate_coverage(record['observations'], coverage_mode)
              for record in processes] if model_consumption or model_sequence or fault_boundaries or driver_boundaries or negative_cycle else []
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
    if semantic_bridge or model_consumption or model_sequence or fault_boundaries or driver_boundaries or negative_cycle:
        summary['status'] = 'F70UGZ_R21_SYNTHETIC_SEMANTIC_BRIDGE_ORACLE_PASS'
        summary['tool_sources'].update({name: sha((ROOT / name).read_bytes()) for name in
                                        ['native_qualification/semantic_demo.py', 'native_qualification/owned_demo.py',
                                         'integration_tools/semantic_bridge.py', 'integration_tools/semantic_oracle.py',
                                         'integration_tools/semantic_types.py', 'integration_tools/owned_message_boundary.py']})
    if model_consumption or model_sequence or fault_boundaries or driver_boundaries or negative_cycle:
        summary.update(status='F70UGZ_R22_FIXED_SYNTHETIC_MODEL_CONSUMPTION_PASS' if model_consumption else
                       'F70UGZ_R23_FIXED_SYNTHETIC_NATIVE_SEQUENCE_PASS' if model_sequence else
                       'F70UGZ_R24_FIXED_SYNTHETIC_FAULT_RESET_PASS' if fault_boundaries else
                       'F70UGZ_R25_FIXED_SYNTHETIC_NEGATIVE_DRIVER_PASS' if driver_boundaries else
                       'F70UGZ_R26_FIXED_SYNTHETIC_NEGATIVE_CYCLE_PASS', model_execution=sum(counts),
                       model_execution_per_worker=counts[0], model_execution_scope='TWO_SEALED_WORKERS_NOT_UNIT_TEST_OR_STAGE_TOTAL',
                       model_reference_sha256=processes[0]['observations']['model_reference_sha256'])
        summary['tool_sources'].update({name: sha((ROOT / name).read_bytes()) for name in
                                       ['native_qualification/coverage.py', 'native_qualification/claims.py', 'integration_tools/model_consumption.py',
                                        'integration_tools/fixed_model_reference.py']})
    if model_sequence:
        summary['tool_sources'].update({name: sha((ROOT / name).read_bytes()) for name in
                                       ['native_qualification/sequence_demo.py', 'integration_tools/sequence_consumption.py',
                                        'integration_tools/sequence_reference.py']})
    if fault_boundaries:
        summary['tool_sources'].update({name: sha((ROOT / name).read_bytes()) for name in
                                       ['native_qualification/fault_demo.py', 'integration_tools/fault_consumption.py',
                                        'integration_tools/fault_reference.py', 'integration_tools/sequence_reference.py']})
    if driver_boundaries:
        summary['tool_sources'].update({name: sha((ROOT / name).read_bytes()) for name in
                                       ['native_qualification/driver_demo.py', 'integration_tools/driver_consumption.py',
                                        'integration_tools/driver_reference.py']})
    if negative_cycle:
        summary['tool_sources'].update({name: sha((ROOT / name).read_bytes()) for name in
                                       ['native_qualification/negative_cycle_demo.py', 'integration_tools/negative_cycle_consumption.py',
                                        'integration_tools/negative_cycle_reference.py']})
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
    parser.add_argument('--model-consumption', action='store_true', help='Explicit R22 five fixed synthetic steps with pinned expected outputs')
    parser.add_argument('--model-sequence', action='store_true', help='Explicit R23 fixed four-step synthetic state-carry sequence')
    parser.add_argument('--fault-boundaries', action='store_true', help='Explicit R24 fixed99-step synthetic fault/reset sequence')
    parser.add_argument('--driver-boundaries', action='store_true', help='Explicit R25 fixed20-step synthetic negative-angle/driver sequence')
    parser.add_argument('--negative-cycle', action='store_true', help='Explicit R26 fixed99-step synthetic negative-angle full cycle')
    parser.add_argument('--package-wheel', type=Path, help='Exact sealed public wheel, required for semantic or model mode')
    args = parser.parse_args()
    try:
        summary = qualify(args.python, args.wheel, args.output, owned_boundary=args.owned_boundary,
                           semantic_bridge=args.semantic_bridge, package_wheel=args.package_wheel, model_consumption=args.model_consumption,
                           model_sequence=args.model_sequence, fault_boundaries=args.fault_boundaries, driver_boundaries=args.driver_boundaries,
                           negative_cycle=args.negative_cycle)
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        print('REJECTED:' + str(error), file=sys.stderr)
        return 2
    print(summary['status'])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
