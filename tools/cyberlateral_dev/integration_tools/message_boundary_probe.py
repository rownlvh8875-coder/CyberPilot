"""Four fixed prepared-input examples only; no data reader or model transitions."""

import argparse
import hashlib
import importlib.util
import json
import sys
from dataclasses import asdict
from pathlib import Path


def canonical(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode()


def _hex(value) -> str:
    if type(value) is not float:
        raise ValueError('PREPARED_BUILTIN_FLOAT_REQUIRED')
    return value.hex()


def run_message_boundary_probe() -> dict:
    if __package__ in (None, ''):
        # DEV glue only; never add src/reference/original module selectors under -I.
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    import cyberlateral_dev as p
    from integration_tools import message_boundary as boundary

    ramp, small = p.Limits(16, 2, 5, 7, 1, 3), p.Limits(5, 5, 5, 0, 1, 1)
    fixtures = (
        ('base', 0, 1.0, p.LateralState(0, None, 0, 0), ramp, None, 0, 0),
        ('resume', 1, 1.0, p.LateralState(1, 16, 2, 0), ramp, 0, 2, 0),
        ('history-scale-change', 1, 0.0, p.LateralState(1, 100, 100, 0), small, 0, 100, 0),
        ('signed-zero', 0, -0.0, p.LateralState(0, None, 0, 0), ramp, None, 0, 0),
    )
    records = []
    for name, index, request, state, limits, previous_index, source_applied, source_counter in fixtures:
        sequence = 'probe_' + name
        frame = boundary.SyntheticBoundaryFrameV1(
            1, 'SYNTHETIC_DEVELOPMENT_ONLY', boundary.PROFILE_ID, boundary.SOURCE_SET_ID,
            'SYNTHETIC_PYTHON_BINARY64', sequence, index, 'SYNTHETIC_CONTEXT_NOT_VEHICLE_AUTHORITY', 'EXPLICIT_SYNTHETIC_CALL_ENTRY',
            boundary.SyntheticCarControlV1(boundary.SyntheticActuatorsV1(request), True),
            boundary.SyntheticCarStateWrapperV1(boundary.SyntheticCarStateValuesV1(0.0, 0.0)), limits,
            boundary.SyntheticPreviousV1('ENTRY_BEFORE_CURRENT_LIMITER', sequence, previous_index, source_applied, source_counter, state),
        )
        prepared = boundary.extract_synthetic_message(frame)
        payload = {'prepared': asdict(prepared), 'float_hex': {
            'request': _hex(prepared.sample.request), 'driver': _hex(prepared.sample.driver), 'angle_deg': _hex(prepared.sample.angle_deg),
        }}
        records.append({'id': name, 'payload': payload, 'sha256': hashlib.sha256(canonical(payload)).hexdigest()})
    return {
        'schema_version': 1, 'contract_id': 'F70UGZ_R14_SYNTHETIC_MESSAGE_PROBE_V1',
        'boundary_contract_id': boundary.CONTRACT_ID, 'profile_id': boundary.PROFILE_ID, 'source_set_id': boundary.SOURCE_SET_ID,
        'status': 'F70UGZ_R14_FIXED_SYNTHETIC_MESSAGE_EXTRACTION_PASS', 'package_version': p.__version__,
        'scope': 'PREPARED_INPUTS_ONLY_NOT_NATIVE_OR_HISTORY_PROOF',
        'scenario_count': len(records), 'model_transitions': 0, 'native_qualification': 'NOT_RUN_NOT_AUTHORIZED', 'records': records,
        'gates': {
            'actual_r': None, 'actual_T2': None, 'actual_vehicle_scale': None, 'R_BUDGET': 'UNRESOLVED',
            'STATIC_EVIDENCE_GATE': 'FAIL', 'SOURCE_SCHEMA_UNQUALIFIED': 6000, 'Candidate': 'NO_GO', 'Runtime': 'NO_GO',
            'actual_activation': 'NOT_ALLOWED', 'F70UH': 'NOT_ALLOWED', 'F70V': 'NOT_ALLOWED', 'F71': 'NOT_ALLOWED',
            'D2': 'PERFORMANCE_NOT_EVALUATED', 'F19': 'LEGACY_UNRESOLVED', 'NATIVE_EXACT_REPLAY': 'NOT_PROVEN',
        },
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='NEW directory, fixed synthetic prepared inputs only')
    args = parser.parse_args(argv)
    try:
        output = args.output
        if output.exists() or output.is_symlink():
            raise FileExistsError('OUTPUT_EXISTS_NO_MESSAGE_BOUNDARY_WORK')
        output.mkdir(parents=True, exist_ok=False)
        result = run_message_boundary_probe()
        package_file = sys.modules['cyberlateral_dev'].__file__
        if type(package_file) is not str:
            raise ValueError('PACKAGE_LOCATION_NOT_ESTABLISHED')
        forbidden = {'numpy', 'kernel', 'openpilot', 'selfdrive', 'opendbc', 'cereal', 'capnp', 'normalized_reference', 'output_oracle',
                     'synthetic_rate_constraint_feasibility_v1', 'synthetic_rate_constraint_feasibility_reconstructed_v2'}
        result['execution_environment'] = {
            'isolated': bool(sys.flags.isolated), 'installed_package': 'site-packages' in Path(package_file).parts,
            'numpy_available': importlib.util.find_spec('numpy') is not None,
            'forbidden_modules_loaded': sorted(n for n in sys.modules if n.split('.')[0] in forbidden),
        }
        raw = canonical(result)
        staged = output / 'RESULTS.pending'
        with staged.open('xb') as stream:
            stream.write(raw)
        with (output / 'SHA256SUMS.txt').open('xb') as stream:
            stream.write((hashlib.sha256(raw).hexdigest() + '  RESULTS.json\n').encode())
        staged.rename(output / 'RESULTS.json')
    except (OSError, ValueError, RuntimeError, ImportError) as error:
        print(f'REJECTED: {error}', file=sys.stderr)
        return 2
    print(result['status'])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
