"""Explicit boundary synthetic execution against independently preregistered literals."""

import hashlib

from . import boundary_reference as reference
from .core_boundary_cases import build_boundary_case, input_record
from .core_rollout_audit import _observe, _paths
from .scenario_output import GATES, canonical
from .synthetic_sequence_rollout import rollout_synthetic_sequence


class BoundaryAuditError(ValueError):
    """Fixed public diagnostic; retained causes and uncertain failed work are preserved."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def audit_boundary_case(case_id: object) -> dict:
    """Run one fixed boundary case; never an expected rejection or vehicle activation."""
    if type(case_id) is not str or case_id not in reference.CASE_IDS:
        raise BoundaryAuditError('BOUNDARY_AUDIT_CASE')
    try:
        data = reference.load_reference()
        expected = reference._expected(case_id, data)
        identity = dict(data['input_identities'][case_id])
    except Exception as error:
        raise BoundaryAuditError('BOUNDARY_AUDIT_REFERENCE') from error
    try:
        frames, contexts = build_boundary_case(case_id)
        raw = canonical(input_record(case_id, frames, contexts))
        if {'byte_size': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} != identity:
            raise BoundaryAuditError('BOUNDARY_AUDIT_INPUT_IDENTITY')
    except BoundaryAuditError:
        raise
    except Exception as error:
        raise BoundaryAuditError('BOUNDARY_AUDIT_SETUP') from error
    try:
        result = rollout_synthetic_sequence(frames, contexts)
    except Exception as error:
        raise BoundaryAuditError('BOUNDARY_AUDIT_EXECUTION_FAILED_WORK_MAY_BE_NONZERO') from error
    try:
        observed = _observe(result)
        count, paths = 0, []
        for pointer in _paths('', expected, observed):
            count += 1
            if len(paths) < 256:
                paths.append(pointer)
        return {'schema_version': 1, 'contract_id': 'CORE31_CLOSED_BOUNDARY_REFERENCE_AUDIT_V1', 'case_id': case_id,
            'audit_status': 'CLOSED_BOUNDARY_REFERENCE_DIFFERENT' if count else 'CLOSED_BOUNDARY_REFERENCE_MATCH', 'audit_exit_code': int(bool(count)),
            'observed_rollout_status': observed['status'], 'observed_rollout_exit_code': {'MATCH': 0, 'DIFFERENT': 1}[observed['status']],
            'synthetic_model_steps': observed['synthetic_model_steps'], 'expected_reference_model_steps': 0,
            'numeric_preflight_work': 'NONZERO_NOT_AGGREGATED', 'reference_sha256': reference.REFERENCE_SHA256,
            'reference_contract_id': data['contract_id'], 'input_identity': identity,
            'difference_count': count, 'reported_difference_count': len(paths), 'differences_truncated': count > len(paths), 'difference_paths': paths,
            **{key: False for key in ('source_identity_reauthenticated', 'prehistory_checked', 'v4_payload_allowed', 'f61_input_allowed', 'actual_activation_allowed')},
            'gates': dict(GATES), 'scope': 'CLOSED_BOUNDARY_LITERAL_AUDIT_NOT_GENERIC_OR_SOURCE_OR_VEHICLE_AUTHORITY'}
    except Exception as error:
        raise BoundaryAuditError('BOUNDARY_AUDIT_RESULT_FAILED_WORK_MAY_BE_NONZERO') from error
