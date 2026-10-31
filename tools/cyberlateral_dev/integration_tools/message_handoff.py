"""Fixed synthetic source-shaped extraction -> pure model step -> owned continuation."""

import argparse
import hashlib
import importlib.util
import json
import sys
from dataclasses import asdict
from pathlib import Path


class HandoffError(RuntimeError):
    """The closed synthetic chain did not satisfy its handoff contract."""


def canonical(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode()


def _require(condition, code):
    if not condition:
        raise HandoffError(code)


def _encode(sample, state, sequence):
    from integration_tools import message_boundary as b

    return b.SyntheticBoundaryFrameV1(
        1, 'SYNTHETIC_DEVELOPMENT_ONLY', b.PROFILE_ID, b.SOURCE_SET_ID, 'SYNTHETIC_PYTHON_BINARY64', sequence, sample.index,
        'SYNTHETIC_CONTEXT_NOT_VEHICLE_AUTHORITY', 'EXPLICIT_SYNTHETIC_CALL_ENTRY',
        b.SyntheticCarControlV1(b.SyntheticActuatorsV1(sample.request), sample.lat_active),
        b.SyntheticCarStateWrapperV1(b.SyntheticCarStateValuesV1(sample.driver, sample.angle_deg)), sample.limits,
        b.SyntheticPreviousV1('ENTRY_BEFORE_CURRENT_LIMITER', sequence, None if sample.index == 0 else sample.index - 1,
                              state.previous_applied, state.angle_counter, state),
    )


def _advance_owned(sample, state, sequence):
    """One declared synthetic extraction and exact owned-state model transition."""
    import cyberlateral_dev as p
    from integration_tools import message_boundary as b

    frame = _encode(sample, state, sequence)
    try:
        prepared = b.extract_synthetic_message(frame)
    except ValueError as error:
        raise HandoffError('HANDOFF_EXTRACTION_REJECTED') from error
    _require(type(prepared) is b.PreparedLateralInputV1 and type(prepared.sample) is p.LateralInput
             and type(prepared.state) is p.LateralState and type(prepared.sample.limits) is p.Limits, 'HANDOFF_PREPARED_MISMATCH')
    expected_prepared = {
        'contract_id': 'F70UGZ_R13_MESSAGE_BOUNDARY_V1', 'source_set_id': 'R11_C8FB9068_4134C0D1_V1',
        'sequence_id': sequence, 'sample': asdict(sample), 'state': asdict(state),
        'custody_claim': 'SYNTHETIC_DECLARATION_ONLY', 'precision_claim': 'EXACT_SUPPLIED_BINARY64_NOT_NATIVE_ABI',
        'time_semantics': 'INVOCATION_ORDER_ONLY_NOT_ELAPSED_TIME',
    }
    _require(canonical(asdict(prepared)) == canonical(expected_prepared), 'HANDOFF_PREPARED_MISMATCH')
    try:
        output = p.step(prepared.sample, prepared.state)
    except ValueError as error:
        raise HandoffError('HANDOFF_MODEL_REJECTED') from error
    _require(type(output) is p.LateralOutput and type(output.next_state) is p.LateralState, 'HANDOFF_MODEL_OUTPUT')
    return frame, prepared, output


def run_handoff_chain() -> dict:
    if __package__ in (None, ''):
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # DEV glue, never src/reference/native selectors.
    import cyberlateral_dev as p
    from cyberlateral_dev import synthetic_catalog

    golden = json.loads((Path(__file__).resolve().parents[1] / 'reference/synthetic_harness_expected_v1.json').read_bytes())
    _require(type(p.__version__) is str and p.__version__ == golden['package_version'] == '0.3.0', 'HANDOFF_IDENTITY')
    catalog = synthetic_catalog.fixed_catalog()
    fixtures = [{'id': s.id, 'initial_state': asdict(s.initial_state), 'samples': [asdict(x) for x in s.samples]} for s in catalog]
    fixture_sha = hashlib.sha256(canonical(fixtures)).hexdigest()
    _require(fixture_sha == golden['fixture_catalog_sha256']
             and [(s.id, len(s.samples)) for s in catalog] == [(r['id'], r['steps']) for r in golden['scenarios']], 'HANDOFF_IDENTITY')
    records = []
    extractor_calls = model_steps = 0
    for scenario, expected in zip(catalog, golden['scenarios'], strict=True):
        state, outputs, frames, prepared_records = scenario.initial_state, [], [], []
        sequence = 'handoff_' + scenario.id
        for sample in scenario.samples:
            frame, prepared, output = _advance_owned(sample, state, sequence)
            extractor_calls += 1
            model_steps += 1
            frames.append(asdict(frame))
            prepared_records.append(asdict(prepared))
            outputs.append(output)
            state = output.next_state
        result = asdict(p.SimulationResult(tuple(outputs), state))
        result_sha = hashlib.sha256(canonical(result)).hexdigest()
        _require(result_sha == expected['result_sha256'], 'HANDOFF_GOLDEN_MISMATCH')
        records.append({
            'id': scenario.id, 'steps': len(scenario.samples), 'initial_state': asdict(scenario.initial_state),
            'source_samples': [asdict(s) for s in scenario.samples], 'frames': frames, 'prepared': prepared_records,
            'result': result, 'result_sha256': result_sha,
            'seed_origin': ('DECLARED_CANONICAL_SYNTHETIC_INITIAL_STATE' if scenario.initial_state.index == 0 else
                            'REGISTERED_SYNTHETIC_SEED_NOT_OBSERVED_PREHISTORY'),
            'continuation_scope': 'OWNED_IMMEDIATE_PRIOR_MODEL_OUTPUT_NOT_NATIVE_CUSTODY',
        })
    return {
        'schema_version': 1, 'contract_id': 'F70UGZ_R15_FIXED_SYNTHETIC_HANDOFF_V1',
        'status': 'F70UGZ_R15_SYNTHETIC_HANDOFF_CHAIN_PASS', 'package_version': p.__version__,
        'boundary_contract_id': 'F70UGZ_R13_MESSAGE_BOUNDARY_V1', 'fixture_catalog_sha256': fixture_sha,
        'scope': 'FIXED_SYNTHETIC_HANDOFF_NOT_NATIVE_OR_INDEPENDENT_ARITHMETIC_PROOF',
        'scenario_count': len(records), 'extractor_calls': extractor_calls, 'model_steps': model_steps, 'prefix_validation_steps': 0,
        'count_scope': 'PER_FIXED_HANDOFF_PROCESS_NOT_AGGREGATE_TEST_ACTIVITY',
        'time_semantics': 'INVOCATION_ORDER_ONLY_NOT_ELAPSED_TIME', 'scenarios': records,
        'native_qualification': 'NOT_RUN_NOT_AUTHORIZED',
        'gates': {
            'actual_r': None, 'actual_T2': None, 'actual_vehicle_scale': None, 'R_BUDGET': 'UNRESOLVED',
            'STATIC_EVIDENCE_GATE': 'FAIL', 'SOURCE_SCHEMA_UNQUALIFIED': 6000, 'Candidate': 'NO_GO', 'Runtime': 'NO_GO',
            'actual_activation': 'NOT_ALLOWED', 'F70UH': 'NOT_ALLOWED', 'F70V': 'NOT_ALLOWED', 'F71': 'NOT_ALLOWED',
            'D2': 'PERFORMANCE_NOT_EVALUATED', 'F19': 'LEGACY_UNRESOLVED', 'NATIVE_EXACT_REPLAY': 'NOT_PROVEN',
        },
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='NEW directory, existing fixed synthetic catalog only')
    args = parser.parse_args(argv)
    try:
        output = args.output
        if output.exists() or output.is_symlink():
            raise FileExistsError('OUTPUT_EXISTS_NO_HANDOFF_WORK')
        output.mkdir(parents=True, exist_ok=False)
        result = run_handoff_chain()
        package_file = sys.modules['cyberlateral_dev'].__file__
        if type(package_file) is not str:
            raise HandoffError('PACKAGE_LOCATION_NOT_ESTABLISHED')
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
