"""Fixed synthetic caller checks. No external data, controller, policy or timing."""

import argparse
import hashlib
import importlib.util
import json
import sys
from dataclasses import asdict, replace
from pathlib import Path


class HarnessError(RuntimeError):
    """A fixed caller/regression contract was not satisfied."""


def canonical(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode()


def _require(condition, code):
    if not condition:
        raise HarnessError(code)


def _rejections(p, scenario):
    first, second = scenario.samples[:2]
    start = scenario.initial_state
    continued = p.step(first, start).next_state
    cases = [
        ('missing-state', (first,), None, 'FlowError', 'EXACT_SYNTHETIC_MODELS_REQUIRED'),
        ('reset-mid-sequence', (second,), start, 'FlowError', 'ADJACENT_MODEL_INVOCATION_REQUIRED'),
        ('gap', (replace(first, index=2),), start, 'FlowError', 'ADJACENT_MODEL_INVOCATION_REQUIRED'),
        ('duplicate', (first,), continued, 'FlowError', 'ADJACENT_MODEL_INVOCATION_REQUIRED'),
        ('missing-history', (second,), replace(continued, previous_requested=None), 'FlowError', 'SYNTHETIC_STATE_INTEGER_REQUIRED'),
        ('missing-limits', (replace(first, limits=None),), start, 'QuantizationError', 'EXACT_SYNTHETIC_SAMPLE_AND_LIMITS_REQUIRED'),
        ('nonfinite-request', (replace(first, request=float('nan')),), start, 'QuantizationError', 'BUILTIN_FINITE_NORMALIZED_FLOAT_REQUIRED'),
        ('exhausted-state', (replace(first, index=4096),), p.LateralState(4096, 0, 0, 0), 'FlowError', 'SYNTHETIC_STATE_INTEGER_REQUIRED'),
        ('production-label', (replace(first, provenance='PRODUCTION'),), start, 'QuantizationError', 'SYNTHETIC_SCOPE_REQUIRED'),
        ('empty-batch', (), start, 'SimulationError', 'EXPLICIT_BOUNDED_SYNTHETIC_TUPLE_REQUIRED'),
        ('list-batch', [first], start, 'SimulationError', 'EXPLICIT_BOUNDED_SYNTHETIC_TUPLE_REQUIRED'),
    ]
    records = []
    for name, samples, state, exception, code in cases:
        before = canonical(asdict(state) if state is not None else None)
        try:
            p.simulate(samples, state)
        except ValueError as error:
            _require((type(error).__name__, str(error)) == (exception, code), f'WRONG_REJECTION:{name}')
        else:
            raise HarnessError(f'MISSING_REJECTION:{name}')
        _require(before == canonical(asdict(state) if state is not None else None), f'REJECTION_STATE_MUTATED:{name}')
        records.append({'id': name, 'exception': exception, 'code': code, 'state_unchanged': True})
    return records


def run_harness(expected: dict) -> dict:
    # Lazy imports keep the CLI output/argument guard ahead of package work.
    import cyberlateral_dev as p
    from cyberlateral_dev.synthetic_catalog import fixed_catalog

    catalog = fixed_catalog()
    fixtures = [{'id': s.id, 'initial_state': asdict(s.initial_state), 'samples': [asdict(x) for x in s.samples]} for s in catalog]
    fixture_sha = hashlib.sha256(canonical(fixtures)).hexdigest()
    _require(p.__version__ == expected.get('package_version') == '0.3.0', 'PACKAGE_VERSION_MISMATCH')
    _require(fixture_sha == expected.get('fixture_catalog_sha256'), 'FIXTURE_IDENTITY_MISMATCH')
    golden = expected.get('scenarios')
    if type(golden) is not list or not all(type(row) is dict for row in golden):
        raise HarnessError('GOLDEN_COVERAGE_MISMATCH')
    _require([(r.get('id'), r.get('steps')) for r in golden] == [(s.id, len(s.samples)) for s in catalog], 'GOLDEN_COVERAGE_MISMATCH')
    records, batch_results = [], []
    split_count = 0
    for scenario, record in zip(catalog, golden, strict=True):
        before = canonical({'state': asdict(scenario.initial_state), 'samples': [asdict(s) for s in scenario.samples]})
        full = p.simulate(scenario.samples, scenario.initial_state)
        raw = canonical(asdict(full))
        result_sha = hashlib.sha256(raw).hexdigest()
        _require(result_sha == record.get('result_sha256'), f'GOLDEN_RESULT_MISMATCH:{scenario.id}')
        state, outputs = scenario.initial_state, []
        for sample in scenario.samples:
            output = p.step(sample, state)
            outputs.append(output)
            state = output.next_state
        _require(canonical(asdict(p.SimulationResult(tuple(outputs), state))) == raw, f'STEP_CHAIN_MISMATCH:{scenario.id}')
        for split in range(1, len(scenario.samples)):
            first = p.simulate(scenario.samples[:split], scenario.initial_state)
            second = p.simulate(scenario.samples[split:], first.next_state)
            combined = p.SimulationResult(first.outputs + second.outputs, second.next_state)
            _require(canonical(asdict(combined)) == raw, f'SPLIT_RESUME_MISMATCH:{scenario.id}:{split}')
            split_count += 1
        _require(before == canonical({'state': asdict(scenario.initial_state), 'samples': [asdict(s) for s in scenario.samples]}),
                 f'CALLER_INPUT_MUTATED:{scenario.id}')
        batch_results.append(raw)
        records.append({'id': scenario.id, 'steps': len(scenario.samples), 'result_sha256': result_sha, 'result': asdict(full)})
    states = [s.initial_state for s in catalog]
    interleaved = [[] for _ in catalog]
    for index in range(max(len(s.samples) for s in catalog)):
        for position, scenario in enumerate(catalog):
            if index < len(scenario.samples):
                output = p.step(scenario.samples[index], states[position])
                interleaved[position].append(output)
                states[position] = output.next_state
    for outputs, state, raw in zip(interleaved, states, batch_results, strict=True):
        _require(canonical(asdict(p.SimulationResult(tuple(outputs), state))) == raw, 'INTERLEAVED_CALLER_MISMATCH')
    rejections = _rejections(p, catalog[0])
    return {
        'schema_version': 1,
        'contract_id': 'F70UGZ_R9_FIXED_SYNTHETIC_CALLER_V1',
        'status': 'F70UGZ_R9_SYNTHETIC_CALLER_HARNESS_PASS',
        'scope': 'FIXED_SYNTHETIC_LIFECYCLE_REGRESSION_NOT_INDEPENDENT_NUMERICAL_ORACLE',
        'package_version': p.__version__,
        'fixture_catalog_sha256': fixture_sha,
        'golden_source_report_sha256': expected.get('source_report_sha256'),
        'scenario_count': len(catalog),
        'total_steps': sum(len(s.samples) for s in catalog),
        'two_chunk_splits': split_count,
        'step_chain_parity': True,
        'interleaved_caller_parity': True,
        'scenarios': records,
        'rejections': rejections,
        'time_semantics': 'INVOCATION_ORDER_ONLY_NOT_ELAPSED_TIME',
        'gates': {
            'actual_r': None, 'actual_T2': None, 'actual_vehicle_scale': None, 'R_BUDGET': 'UNRESOLVED',
            'STATIC_EVIDENCE_GATE': 'FAIL', 'SOURCE_SCHEMA_UNQUALIFIED': 6000, 'Candidate': 'NO_GO', 'Runtime': 'NO_GO',
            'actual_activation': 'NOT_ALLOWED', 'F70UH': 'NOT_ALLOWED', 'F70V': 'NOT_ALLOWED', 'F71': 'NOT_ALLOWED',
            'D2': 'PERFORMANCE_NOT_EVALUATED', 'F19': 'LEGACY_UNRESOLVED', 'NATIVE_EXACT_REPLAY': 'NOT_PROVEN',
        },
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='NEW directory, fixed synthetic fixtures only')
    args = parser.parse_args(argv)
    try:
        output = args.output
        if output.exists() or output.is_symlink():
            raise FileExistsError('OUTPUT_EXISTS_NO_HARNESS_WORK')
        output.mkdir(parents=True, exist_ok=False)
        expected = json.loads((Path(__file__).resolve().parents[1] / 'reference/synthetic_harness_expected_v1.json').read_bytes())
        result = run_harness(expected)
        forbidden = {'numpy', 'kernel', 'openpilot', 'selfdrive', 'opendbc', 'cereal', 'capnp', 'normalized_reference', 'output_oracle'}
        package_file = sys.modules['cyberlateral_dev'].__file__
        if type(package_file) is not str:
            raise HarnessError('PACKAGE_LOCATION_NOT_ESTABLISHED')
        result['execution_environment'] = {
            'isolated': bool(sys.flags.isolated),
            'installed_package': 'site-packages' in Path(package_file).parts,
            'numpy_available': importlib.util.find_spec('numpy') is not None,
            'forbidden_modules_loaded': sorted(n for n in sys.modules if n.split('.')[0] in forbidden),
        }
        raw = canonical(result)
        with (output / 'RESULTS.json').open('xb') as stream:
            stream.write(raw)
        with (output / 'SHA256SUMS.txt').open('xb') as stream:
            stream.write((hashlib.sha256(raw).hexdigest() + '  RESULTS.json\n').encode())
    except (OSError, ValueError, RuntimeError, ImportError) as error:
        print(f'REJECTED: {error}', file=sys.stderr)
        return 2
    print(result['status'])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
