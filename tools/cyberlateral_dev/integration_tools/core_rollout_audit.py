"""Explicit closed synthetic computation compared with independent literal records."""

import hashlib
from dataclasses import asdict

from . import rollout_reference as reference
from .core_rollout_run import _input_record
from .core_sequence_cases import build_case
from .scenario_output import GATES, canonical
from .synthetic_sequence_rollout import SequenceRolloutError, rollout_synthetic_sequence


class RolloutAuditError(ValueError):
    """Fixed phase errors never claim failed model work was zero."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _observe(result) -> dict:
    return {**{key: getattr(result, key) for key in reference.META}, 'status': result.status, 'rejection_code': None,
        'synthetic_model_steps': result.synthetic_model_steps, 'checked_transition_count': result.checked_transition_count,
        'initial_declared_state': asdict(result.initial_declared_state), 'final_computed_state': asdict(result.final_computed_state),
        **{key: list(getattr(result, key)) for key in ('entry_differing_transition_indices', 'output_differing_transition_indices', 'differing_transition_indices')},
        'steps': [{'model_index': row.prepared.context.model_index, 'entry_state': asdict(row.entry_state),
            'declared_entry_state': asdict(row.prepared.model_state),
            'declared_saved_state': {'saved_limited_state': row.prepared.current.saved_limited_state,
                                   'saved_angle_counter': row.prepared.current.saved_angle_counter},
            'output': asdict(row.output), 'entry_differences': [asdict(d) for d in row.entry_differences],
            'output_differences': [asdict(d) for d in row.output_differences], 'status': row.status} for row in result.steps]}


def _paths(path: str, expected, actual):
    """Exact owned-record comparison; floats use hex, not tolerant equality."""
    if type(expected) is not type(actual):
        yield path
    elif type(expected) is dict:
        for key in sorted(expected.keys() | actual.keys()):
            pointer = path + '/' + key.replace('~', '~0').replace('/', '~1')
            if key not in expected or key not in actual:
                yield pointer
            else:
                yield from _paths(pointer, expected[key], actual[key])
    elif type(expected) is list:
        for i in range(max(len(expected), len(actual))):
            pointer = path + '/' + str(i)
            if i >= len(expected) or i >= len(actual):
                yield pointer
            else:
                yield from _paths(pointer, expected[i], actual[i])
    elif (expected.hex() != actual.hex()) if type(expected) is float else (expected != actual):
        yield path


def audit_rollout_case(case_id: object) -> dict:
    """Execute exactly one closed rollout; audit0 is separate from rollout M/D/R."""
    if type(case_id) is not str or case_id not in reference.CASE_IDS:
        raise RolloutAuditError('ROLLOUT_AUDIT_CASE')
    try:
        data = reference.load_reference()
        expected = reference._expected(case_id, data)
        identity = dict(data['input_identities'][case_id])
    except Exception as error:
        raise RolloutAuditError('ROLLOUT_AUDIT_REFERENCE') from error
    try:
        frames, contexts = build_case(case_id)
        raw = canonical(_input_record(case_id, frames, contexts))
        if {'byte_size': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} != identity:
            raise RolloutAuditError('ROLLOUT_AUDIT_INPUT_IDENTITY')
    except RolloutAuditError:
        raise
    except Exception as error:
        raise RolloutAuditError('ROLLOUT_AUDIT_SETUP') from error
    rejection, result = None, None
    try:
        result = rollout_synthetic_sequence(frames, contexts)
    except SequenceRolloutError as error:
        if case_id != 'late-invalid' or error.code != 'ROLLOUT_INPUT:2:MODEL_DRIVER':
            raise RolloutAuditError('ROLLOUT_AUDIT_EXECUTION_FAILED_WORK_MAY_BE_NONZERO') from error
        rejection = error.code
    except Exception as error:
        raise RolloutAuditError('ROLLOUT_AUDIT_EXECUTION_FAILED_WORK_MAY_BE_NONZERO') from error
    try:
        observed = ({'status': 'REJECTED', 'rejection_code': rejection, 'synthetic_model_steps': 0, 'steps': []}
                    if rejection is not None else _observe(result))
        count, paths = 0, []
        for pointer in _paths('', expected, observed):
            count += 1
            if len(paths) < 256:
                paths.append(pointer)
        return {'schema_version': 1, 'contract_id': 'CORE30_CLOSED_ROLLOUT_REFERENCE_AUDIT_V1', 'case_id': case_id,
            'audit_status': 'CLOSED_REFERENCE_DIFFERENT' if count else 'CLOSED_REFERENCE_MATCH', 'audit_exit_code': int(bool(count)),
            'observed_rollout_status': observed['status'], 'observed_rollout_exit_code': {'MATCH': 0, 'DIFFERENT': 1, 'REJECTED': 2}[observed['status']],
            'observed_rejection_code': rejection, 'synthetic_model_steps': observed['synthetic_model_steps'], 'expected_reference_model_steps': 0,
            'numeric_preflight_work': 'NONZERO_NOT_AGGREGATED', 'reference_sha256': reference.REFERENCE_SHA256,
            'reference_contract_id': data['contract_id'], 'input_identity': identity,
            'difference_count': count, 'reported_difference_count': len(paths), 'differences_truncated': count > len(paths), 'difference_paths': paths,
            **{key: False for key in ('source_identity_reauthenticated', 'prehistory_checked', 'v4_payload_allowed', 'f61_input_allowed', 'actual_activation_allowed')},
            'gates': dict(GATES), 'scope': 'CLOSED_FULL_OUTPUT_LITERAL_AUDIT_NOT_GENERIC_OR_SOURCE_OR_VEHICLE_AUTHORITY'}
    except Exception as error:
        raise RolloutAuditError('ROLLOUT_AUDIT_RESULT_FAILED_WORK_MAY_BE_NONZERO') from error
