"""Closed synthetic DEV execution and portable publication, not external intake."""

import hashlib
from dataclasses import asdict
from pathlib import Path

from .core_sequence_cases import CASE_IDS, build_case
from .scenario_input import ScenarioError
from .scenario_output import GATES, canonical
from .scenario_run import load_model, source_identity

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = 'CORE8_CLOSED_SYNTHETIC_SEQUENCE_DEMO_V1'
SCOPE = 'CLOSED_DECLARED_SYNTHETIC_FIXTURE_ONLY'


class DemoError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _preflight(output: Path) -> None:
    if not isinstance(output, Path):
        raise DemoError('DEMO_OUTPUT_PATH')
    try:
        if output.exists() or output.is_symlink():
            raise DemoError('DEMO_OUTPUT_EXISTS')
        text = str(output.absolute())
        text.encode('utf-8', errors='strict')
        if '\0' in text:
            raise ValueError('invalid path')
        if any(parent.is_symlink() for parent in output.absolute().parents):
            raise DemoError('DEMO_OUTPUT_LOCATION')
        if not output.parent.is_dir():
            raise DemoError('DEMO_OUTPUT_PARENT')
        if output.resolve().is_relative_to(ROOT.parents[1].resolve()):
            raise DemoError('DEMO_OUTPUT_LOCATION')
    except DemoError:
        raise
    except (OSError, ValueError, RuntimeError) as error:
        raise DemoError('DEMO_OUTPUT_PATH') from error


def _cli_sha() -> str:
    return hashlib.sha256((ROOT / 'tools/core_sequence.py').read_bytes()).hexdigest()


def _input_record(case_id, frames, contexts) -> dict:
    projected_frames, projected_contexts = [], []
    for frame in frames:
        item = asdict(frame)
        item['request']['requested_binary32_be_hex'] = item['request'].pop('requested_binary32').hex()
        projected_frames.append(item)
    for context in contexts:
        item = asdict(context)
        item['current_driver_hex'] = item.pop('current_driver').hex()
        item['current_angle_deg_hex'] = item.pop('current_angle_deg').hex()
        projected_contexts.append(item)
    return {'schema_version': 1, 'contract_id': CONTRACT, 'case_id': case_id, 'scope': SCOPE,
            'frames': projected_frames, 'contexts': projected_contexts}


def _write_exclusive(path: Path, raw: bytes) -> None:
    with path.open('xb') as stream:
        stream.write(raw)


def _publish(output: Path, files: dict[str, bytes]) -> None:
    try:
        output.mkdir(exist_ok=False)
        for name in ('INPUT.json', 'RESULTS.json', 'SHA256SUMS.txt'):
            _write_exclusive(output / name, files[name])
    except OSError as error:
        raise DemoError('DEMO_PUBLICATION_FAILED_WORK_MAY_BE_NONZERO') from error


def run_sequence_case(case_id: object, output: Path) -> dict:
    if type(case_id) is not str or case_id not in CASE_IDS:
        raise DemoError('DEMO_CASE')
    _preflight(output)
    try:
        _, initial = load_model(ROOT)
        identity = {**initial, 'demo_cli_sha256': _cli_sha()}
    except ScenarioError as error:
        raise DemoError('DEMO_SOURCE:' + error.code) from error
    frames, contexts = build_case(case_id)
    from .synthetic_sequence_check import SequenceCheckError, check_synthetic_sequence

    rows, differing = [], []
    rejection = None
    try:
        checked = check_synthetic_sequence(frames, contexts)
    except SequenceCheckError as error:
        if not (error.code.startswith(('SEQUENCE_INPUT:', 'SEQUENCE_MODEL_ORDER:'))
                or error.code in ('SEQUENCE_TYPE', 'SEQUENCE_CONTAINER', 'SEQUENCE_COUNT')):
            raise DemoError('DEMO_CHECK_FAILED_WORK_MAY_BE_NONZERO') from error
        status, completed, steps, rejection = 'REJECTED', False, 0, error.code
    else:
        status, completed, steps = checked.status, True, checked.synthetic_model_steps
        differing = list(checked.differing_transition_indices)
        for i, check in enumerate(checked.checks):
            rows.append({'transition_index': i, 'status': check.status, 'model_index': check.context.model_index,
                'entry_state': asdict(check.prepared.model_state), 'computed_next_state': asdict(check.computed_next_state),
                'declared_saved_state': {'saved_limited_state': check.current.saved_limited_state,
                                         'saved_angle_counter': check.current.saved_angle_counter},
                'differences': [asdict(value) for value in check.differences]})
    try:
        after = {**source_identity(ROOT), 'demo_cli_sha256': _cli_sha()}
    except ScenarioError as error:
        raise DemoError('DEMO_SOURCE:' + error.code) from error
    if after != identity:
        raise DemoError('DEMO_SOURCE_CHANGED')
    record = {'schema_version': 1, 'contract_id': CONTRACT, 'scope': SCOPE, 'case_id': case_id,
        'status': status, 'rejection_code': rejection, 'sequence_completed': completed,
        'frame_count': len(frames), 'declared_transition_count': len(contexts), 'completed_transition_count': len(rows),
        'model_steps': steps, 'differing_transition_indices': differing, 'rows': rows, 'identity': identity, 'gates': dict(GATES),
        'validation_claim': 'ADJACENT_DECLARED_CURRENT_TRANSITIONS_ONLY_NOT_COMPUTED_ROLLOUT',
        'anchor_transition_checked': False, 'prehistory_checked': False, 'source_authenticated': False}
    files = {'INPUT.json': canonical(_input_record(case_id, frames, contexts)), 'RESULTS.json': canonical(record)}
    files['SHA256SUMS.txt'] = ''.join(hashlib.sha256(raw).hexdigest() + '  ' + name + '\n'
                                   for name, raw in sorted(files.items())).encode()
    _publish(output, files)
    return record


def exit_code(record: dict) -> int:
    return {'MATCH': 0, 'DIFFERENT': 1, 'REJECTED': 2}[record['status']]
