"""Fixed synthetic DEV bridge evidence only. No external data or vehicle hook."""

import argparse
import hashlib
import importlib.util
import json
import sys
from dataclasses import asdict
from pathlib import Path


def canonical(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode()


def run_bridge_probe() -> dict:
    # Under -I only our DEV glue directory is added, never src/reference/native.
    # Package resolution must still come from the independently installed wheel.
    if __package__ in (None, ''):
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    import cyberlateral_dev as p
    from cyberlateral_dev.synthetic_catalog import fixed_catalog
    from integration_tools import dev_bridge as bridge

    scenarios: list[dict] = []
    for fixture in fixed_catalog():
        sequence_id = 'probe_' + fixture.id
        session = bridge.begin_sequence(fixture.id, sequence_id)
        outputs = []
        for offset in range(len(fixture.samples)):
            result = bridge.advance(bridge.fixture_snapshot(fixture.id, offset, sequence_id), session)
            outputs.append(result.diagnostic)
            session = result.next_session
        payload = asdict(p.SimulationResult(tuple(outputs), session.model_state))
        scenarios.append({'id': fixture.id, 'sequence_id': sequence_id, 'steps': len(outputs), 'result': payload,
                          'result_sha256': hashlib.sha256(canonical(payload)).hexdigest(), 'final_session': asdict(session)})
    return {
        'schema_version': 1, 'contract_id': bridge.CONTRACT_ID,
        'profile_id': bridge.PROFILE_ID, 'source_set_id': bridge.SOURCE_SET_ID,
        'status': 'F70UGZ_R12_FIXED_SYNTHETIC_DEV_BRIDGE_PASS',
        'scope': 'FIXED_SYNTHETIC_DEV_GLUE_REGRESSION_NOT_PRODUCTION_OR_INDEPENDENT_ORACLE',
        'package_version': p.__version__, 'fixture_catalog_sha256': bridge.CATALOG_SHA256,
        'scenario_count': len(scenarios), 'total_steps': sum(s['steps'] for s in scenarios),
        'scenarios': scenarios, 'time_semantics': 'INVOCATION_ORDER_ONLY_NOT_ELAPSED_TIME',
        'work_semantics': 'ONE_NEW_CURRENT_TRANSITION_PLUS_TRUSTED_PREFIX_PER_ADVANCE',
        'gates': {
            'actual_r': None, 'actual_T2': None, 'actual_vehicle_scale': None, 'R_BUDGET': 'UNRESOLVED',
            'STATIC_EVIDENCE_GATE': 'FAIL', 'SOURCE_SCHEMA_UNQUALIFIED': 6000, 'Candidate': 'NO_GO', 'Runtime': 'NO_GO',
            'actual_activation': 'NOT_ALLOWED', 'F70UH': 'NOT_ALLOWED', 'F70V': 'NOT_ALLOWED', 'F71': 'NOT_ALLOWED',
            'D2': 'PERFORMANCE_NOT_EVALUATED', 'F19': 'LEGACY_UNRESOLVED', 'NATIVE_EXACT_REPLAY': 'NOT_PROVEN',
        },
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='NEW directory, closed synthetic fixtures only')
    args = parser.parse_args(argv)
    try:
        output = args.output
        if output.exists() or output.is_symlink():
            raise FileExistsError('OUTPUT_EXISTS_NO_BRIDGE_WORK')
        output.mkdir(parents=True, exist_ok=False)
        result = run_bridge_probe()
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
