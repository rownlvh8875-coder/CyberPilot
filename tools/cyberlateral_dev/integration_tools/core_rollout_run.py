"""Explicit closed synthetic rollout and checked new-folder publication."""

import hashlib
from dataclasses import asdict
from pathlib import Path

from .core_sequence_archive_workflow import ArchiveWorkflowError, _output, _publish
from .core_sequence_cases import CASE_IDS, build_case
from .scenario_output import GATES, canonical
from .synthetic_sequence_rollout import SequenceRolloutError, SyntheticSequenceRolloutV1, rollout_synthetic_sequence

SCOPE = 'CLOSED_COUNTERFACTUAL_COMPUTED_ROLLOUT_FIXTURE_ONLY'
FLAGS = {'source_identity_reauthenticated': False, 'prehistory_checked': False, 'v4_payload_allowed': False,
         'f61_input_allowed': False, 'actual_activation_allowed': False}


class RolloutRunError(ValueError):
    """Fixed phase diagnostics distinguish preflight from uncertain execution work."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


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
    return {'schema_version': 1, 'contract_id': 'CORE28_CLOSED_COMPUTED_ROLLOUT_INPUT_V1',
            'case_id': case_id, 'scope': SCOPE, 'frames': projected_frames, 'contexts': projected_contexts}


def _result_record(case_id: str, checked: SyntheticSequenceRolloutV1 | None, rejection: str | None) -> dict:
    completed = checked is not None
    rows = [] if checked is None else [
        {'transition_index': i, 'model_index': row.prepared.context.model_index, 'status': row.status,
         'declared_entry_state': asdict(row.prepared.model_state), 'entry_state': asdict(row.entry_state),
         'computed_next_state': asdict(row.output.next_state),
         'declared_saved_state': {'saved_limited_state': row.prepared.current.saved_limited_state,
                                 'saved_angle_counter': row.prepared.current.saved_angle_counter},
         'entry_differences': [asdict(d) for d in row.entry_differences],
         'output_differences': [asdict(d) for d in row.output_differences]} for i, row in enumerate(checked.steps)]
    return {'schema_version': 1, 'contract_id': 'CORE28_CLOSED_COMPUTED_ROLLOUT_RESULT_V1', 'case_id': case_id, 'scope': SCOPE,
        'status': 'REJECTED' if checked is None else checked.status, 'rejection_code': rejection, 'sequence_completed': completed,
        'frame_count': 4, 'declared_transition_count': 3, 'completed_transition_count': len(rows), 'model_steps': len(rows),
        'initial_declared_state': None if checked is None else asdict(checked.initial_declared_state),
        'final_computed_state': None if checked is None else asdict(checked.final_computed_state),
        'entry_differing_transition_indices': [] if checked is None else list(checked.entry_differing_transition_indices),
        'output_differing_transition_indices': [] if checked is None else list(checked.output_differing_transition_indices),
        'differing_transition_indices': [] if checked is None else list(checked.differing_transition_indices), 'rows': rows,
        'source_rollout_contract_id': 'CORE27_COUNTERFACTUAL_COMPUTED_STATE_ROLLOUT_V1',
        'requested_state_feed_rule': 'FIRST_DECLARED_ENTRY_THEN_COMPUTED_NEXT_STATE_NO_RESEED',
        'computed_state_fed': completed, 'anchor_transition_checked': False, **FLAGS, 'gates': dict(GATES)}


def run_rollout_case(case_id: object, output_root: Path) -> dict:
    """Run one fixed case explicitly; preserve both rejection and partial failures."""
    if type(case_id) is not str or case_id not in CASE_IDS:
        raise RolloutRunError('ROLLOUT_RUN_CASE')
    target = _output(output_root)
    frames, contexts = build_case(case_id)
    try:
        input_bytes = canonical(_input_record(case_id, frames, contexts))
    except (ValueError, TypeError, ArithmeticError) as error:
        raise RolloutRunError('ROLLOUT_RUN_INPUT_ENCODING') from error
    checked, rejection = None, None
    try:
        checked = rollout_synthetic_sequence(frames, contexts)
    except SequenceRolloutError as error:
        if not (error.code.startswith(('ROLLOUT_INPUT:', 'ROLLOUT_MODEL_ORDER:'))
                or error.code in ('ROLLOUT_TYPE', 'ROLLOUT_CONTAINER', 'ROLLOUT_COUNT')):
            raise RolloutRunError('ROLLOUT_RUN_EXECUTION_FAILED_WORK_MAY_BE_NONZERO') from error
        rejection = error.code
    status = 'REJECTED' if checked is None else checked.status
    code = {'MATCH': 0, 'DIFFERENT': 1, 'REJECTED': 2}[status]
    try:
        record = _result_record(case_id, checked, rejection)
        files = {'INPUT.json': input_bytes, 'RESULTS.json': canonical(record)}
        files['SHA256SUMS.txt'] = ''.join(hashlib.sha256(raw).hexdigest() + '  ' + name + '\n'
            for name, raw in sorted(files.items())).encode()
    except (ValueError, TypeError, ArithmeticError) as error:
        raise RolloutRunError('ROLLOUT_RUN_RESULT_FAILED_WORK_MAY_BE_NONZERO') from error
    try:
        _publish(target, files)
    except ArchiveWorkflowError as error:
        raise RolloutRunError('ROLLOUT_RUN_PUBLICATION:' + error.code + ':WORK_MAY_BE_NONZERO') from error
    return {'schema_version': 1, 'contract_id': 'CORE28_CLOSED_COMPUTED_ROLLOUT_RUN_V1',
        'status': 'COMPUTED_ROLLOUT_RUN_PUBLISHED', 'case_id': case_id, 'result_status': status, 'result_exit_code': code,
        'execution_requested': True, 'sequence_completed': record['sequence_completed'], 'model_steps': record['model_steps'],
        'completed_transition_count': record['completed_transition_count'], 'computed_state_fed': record['computed_state_fed'],
        'files': {name: {'sha256': hashlib.sha256(raw).hexdigest(), 'byte_size': len(raw)} for name, raw in files.items()},
        **FLAGS, 'gates': dict(GATES), 'scope': SCOPE}
