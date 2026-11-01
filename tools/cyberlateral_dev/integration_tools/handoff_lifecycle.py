"""Closed synthetic extraction-to-model split/resume and independent-stream checks."""

import argparse
import hashlib
import importlib.util
import sys
from dataclasses import asdict
from pathlib import Path


class LifecycleError(RuntimeError):
    """The fixed synthetic lifecycle did not preserve its full handoff trace."""


def canonical(value):
    import json

    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode()


def _require(condition, code):
    if not condition:
        raise LifecycleError(code)


def _sha(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def _chunk(samples, state, sequence) -> dict:
    from integration_tools import message_handoff as h

    outputs, frames, prepared = [], [], []
    for sample in samples:
        frame, item, output = h._advance_owned(sample, state, sequence)
        frames.append(asdict(frame))
        prepared.append(asdict(item))
        outputs.append(asdict(output))
        state = output.next_state
    return {'frames': frames, 'prepared': prepared, 'outputs': outputs, 'next_state': state}


def run_lifecycle() -> dict:
    if __package__ in (None, ''):
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # DEV glue, never src/reference/native selectors.
    from cyberlateral_dev import synthetic_catalog
    from integration_tools import message_handoff as h

    baseline = h.run_handoff_chain()
    catalog = synthetic_catalog.fixed_catalog()
    fixtures = [{'id': s.id, 'initial_state': asdict(s.initial_state), 'samples': [asdict(x) for x in s.samples]} for s in catalog]
    _require(_sha(fixtures) == baseline['fixture_catalog_sha256'], 'LIFECYCLE_CATALOG_DRIFT')
    split_runs, events = [], []
    transitions = baseline['model_steps']
    for scenario, row in zip(catalog, baseline['scenarios'], strict=True):
        cuts = []
        for cut in range(1, len(scenario.samples)):
            first = _chunk(scenario.samples[:cut], scenario.initial_state, 'handoff_' + scenario.id)
            second = _chunk(scenario.samples[cut:], first['next_state'], 'handoff_' + scenario.id)
            frames, prepared = first['frames'] + second['frames'], first['prepared'] + second['prepared']
            result = {'outputs': first['outputs'] + second['outputs'], 'next_state': asdict(second['next_state'])}
            _require(canonical(frames) == canonical(row['frames']) and canonical(prepared) == canonical(row['prepared'])
                     and canonical(result) == canonical(row['result']), f'LIFECYCLE_SPLIT_MISMATCH:{scenario.id}:{cut}')
            cuts.append({'cut': cut, 'prefix_final_state': asdict(first['next_state']), 'resumed_prepared_state': second['prepared'][0]['state'],
                         'frames_sha256': _sha(frames), 'prepared_sha256': _sha(prepared), 'result_sha256': _sha(result)})
            transitions += len(scenario.samples)
        split_runs.append({'id': scenario.id, 'cuts': cuts})
    states = [s.initial_state for s in catalog]
    for offset in range(max(len(s.samples) for s in catalog)):
        for position, (scenario, row) in enumerate(zip(catalog, baseline['scenarios'], strict=True)):
            if offset >= len(scenario.samples):
                continue
            frame, prepared, output = h._advance_owned(scenario.samples[offset], states[position], 'handoff_' + scenario.id)
            event = {'id': scenario.id, 'offset': offset, 'frame': asdict(frame), 'prepared': asdict(prepared), 'output': asdict(output)}
            expected = {'id': row['id'], 'offset': offset, 'frame': row['frames'][offset], 'prepared': row['prepared'][offset], 'output': row['result']['outputs'][offset]}
            _require(canonical(event) == canonical(expected), 'LIFECYCLE_INTERLEAVED_MISMATCH')
            events.append(event)
            states[position] = output.next_state
            transitions += 1
    after = [{'id': s.id, 'initial_state': asdict(s.initial_state), 'samples': [asdict(x) for x in s.samples]} for s in catalog]
    _require(_sha(after) == baseline['fixture_catalog_sha256'], 'LIFECYCLE_CATALOG_MUTATED')
    return {
        'schema_version': 1, 'contract_id': 'F70UGZ_R16_SYNTHETIC_HANDOFF_LIFECYCLE_V1',
        'status': 'F70UGZ_R16_SYNTHETIC_HANDOFF_LIFECYCLE_PASS', 'scope': 'CLOSED_SAME_PROCESS_SYNTHETIC_LIFECYCLE_NOT_NATIVE_OR_PERSISTENT_REPLAY',
        'scenario_count': len(catalog), 'total_source_samples': baseline['model_steps'], 'two_chunk_splits': sum(len(r['cuts']) for r in split_runs),
        'extractor_calls': transitions, 'model_steps': transitions, 'prefix_validation_steps': 0,
        'count_scope': 'PER_FIXED_LIFECYCLE_PROCESS_NOT_AGGREGATE_TEST_ACTIVITY',
        'time_semantics': 'INVOCATION_ORDER_ONLY_NOT_ELAPSED_TIME', 'native_qualification': 'NOT_RUN_NOT_AUTHORIZED',
        'baseline': baseline, 'split_runs': split_runs, 'interleaved_events': events, 'gates': baseline['gates'],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='NEW directory, fixed synthetic lifecycle only')
    args = parser.parse_args(argv)
    try:
        output = args.output
        if output.exists() or output.is_symlink():
            raise FileExistsError('OUTPUT_EXISTS_NO_LIFECYCLE_WORK')
        output.mkdir(parents=True, exist_ok=False)
        result = run_lifecycle()
        package_file = sys.modules['cyberlateral_dev'].__file__
        if type(package_file) is not str:
            raise LifecycleError('PACKAGE_LOCATION_NOT_ESTABLISHED')
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
