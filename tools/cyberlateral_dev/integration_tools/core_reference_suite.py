"""Fixed six-case reference regression, not new arithmetic or vehicle qualification."""

import re
from copy import deepcopy
from typing import TypedDict

from .boundary_reference import REFERENCE_SHA256 as BOUNDARY_SHA256
from .core_boundary_audit import audit_boundary_case
from .core_rollout_audit import _paths, audit_rollout_case
from .rollout_reference import REFERENCE_SHA256 as ROLLOUT_SHA256
from .scenario_output import GATES

_CASES = (('CORE30', 'sign-cycle', 3, 'MATCH'), ('CORE30', 'declared-difference', 3, 'DIFFERENT'),
          ('CORE30', 'late-invalid', 0, 'REJECTED'), ('CORE31', 'inactive-resume', 3, 'MATCH'),
          ('CORE31', 'fault-reset', 4, 'MATCH'), ('CORE31', 'rounding-ties', 6, 'MATCH'))
_FLAGS = ('source_identity_reauthenticated', 'prehistory_checked', 'v4_payload_allowed', 'f61_input_allowed', 'actual_activation_allowed')
_FIELDS = set(('schema_version contract_id case_id audit_status audit_exit_code observed_rollout_status observed_rollout_exit_code '
    'synthetic_model_steps expected_reference_model_steps numeric_preflight_work reference_sha256 reference_contract_id input_identity '
    'difference_count reported_difference_count differences_truncated difference_paths gates scope').split()) | set(_FLAGS)
_CONTRACTS = {
    'CORE30': ('CORE30_CLOSED_ROLLOUT_REFERENCE_AUDIT_V1', 'CLOSED_REFERENCE_', ROLLOUT_SHA256,
               'CORE30_HAND_DERIVED_CLOSED_ROLLOUT_V1', 'CLOSED_FULL_OUTPUT_LITERAL_AUDIT_NOT_GENERIC_OR_SOURCE_OR_VEHICLE_AUTHORITY'),
    'CORE31': ('CORE31_CLOSED_BOUNDARY_REFERENCE_AUDIT_V1', 'CLOSED_BOUNDARY_REFERENCE_', BOUNDARY_SHA256,
               'CORE31_HAND_DERIVED_BOUNDARY_V1', 'CLOSED_BOUNDARY_LITERAL_AUDIT_NOT_GENERIC_OR_SOURCE_OR_VEHICLE_AUTHORITY'),
}


class ReferenceSuiteError(ValueError):
    """Fixed case-qualified error; failed prefix work is never claimed zero."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


class _CaseReport(TypedDict):
    group: str
    case_id: str
    report: dict


def _need(condition: bool) -> None:
    if not condition:
        raise ValueError('REFERENCE_SUITE_INTERNAL_RECEIPT')


def _validated(value, group: str, case: str, steps: int, baseline: str) -> dict:
    """Version boundary on internal receipts, not arbitrary-object intake or a sandbox."""
    _need(type(value) is dict)
    r = deepcopy(value)
    _need(set(r) == _FIELDS | ({'observed_rejection_code'} if group == 'CORE30' else set()))
    contract, prefix, digest, reference_id, scope = _CONTRACTS[group]
    for key, expected in (('contract_id', contract), ('case_id', case), ('reference_sha256', digest),
                          ('reference_contract_id', reference_id), ('scope', scope), ('numeric_preflight_work', 'NONZERO_NOT_AGGREGATED')):
        _need(type(r[key]) is str and r[key] == expected)
    _need(type(r['schema_version']) is int and r['schema_version'] == 1)
    for key in ('audit_exit_code', 'observed_rollout_exit_code', 'synthetic_model_steps', 'expected_reference_model_steps', 'difference_count', 'reported_difference_count'):
        _need(type(r[key]) is int and r[key] >= 0)
    count, detail = r['difference_count'], r['reported_difference_count']
    _need(type(r['audit_status']) is str and r['audit_status'] == prefix + ('DIFFERENT' if count else 'MATCH'))
    _need(r['audit_exit_code'] == int(bool(count)) and r['expected_reference_model_steps'] == 0)
    _need(detail == min(count, 256) and type(r['differences_truncated']) is bool and r['differences_truncated'] == (count > detail))
    paths = r['difference_paths']
    _need(type(paths) is list and len(paths) == detail and all(type(p) is str and (p == '' or p.startswith('/')) for p in paths))
    observed = r['observed_rollout_status']
    _need(type(observed) is str and observed in ('MATCH', 'DIFFERENT', 'REJECTED'))
    _need(r['observed_rollout_exit_code'] == {'MATCH': 0, 'DIFFERENT': 1, 'REJECTED': 2}[observed])
    if group == 'CORE30':
        _need((case == 'late-invalid' and r['observed_rejection_code'] == 'ROLLOUT_INPUT:2:MODEL_DRIVER') if observed == 'REJECTED' else r['observed_rejection_code'] is None)
    else:
        _need(observed != 'REJECTED')
    if count == 0:
        _need(r['synthetic_model_steps'] == steps and observed == baseline)
    identity = r['input_identity']
    _need(type(identity) is dict and set(identity) == {'byte_size', 'sha256'})
    _need(type(identity['byte_size']) is int and identity['byte_size'] > 0)
    _need(type(identity['sha256']) is str and re.fullmatch('[0-9a-f]{64}', identity['sha256']) is not None)
    _need(all(r[key] is False for key in _FLAGS))
    _need(type(r['gates']) is dict and not any(_paths('', GATES, r['gates'])))
    return r


def run_reference_suite() -> dict:
    """Run each owned audit once; continue mismatches, never partial success on error."""
    reports: list[_CaseReport] = []
    for group, case, steps, baseline in _CASES:
        try:
            raw = audit_rollout_case(case) if group == 'CORE30' else audit_boundary_case(case)
        except Exception as error:
            raise ReferenceSuiteError(f'REFERENCE_SUITE_CASE_FAILED:{group}:{case}:WORK_MAY_BE_NONZERO') from error
        try:
            owned = _validated(raw, group, case, steps, baseline)
        except Exception as error:
            raise ReferenceSuiteError(f'REFERENCE_SUITE_RECEIPT_INVALID:{group}:{case}:WORK_MAY_BE_NONZERO') from error
        reports.append({'group': group, 'case_id': case, 'report': owned})
    audits = {'MATCH': 0, 'DIFFERENT': 0}; observed = {'MATCH': 0, 'DIFFERENT': 0, 'REJECTED': 0}
    for item in reports:
        r = item['report']; audits['DIFFERENT' if r['audit_exit_code'] else 'MATCH'] += 1; observed[r['observed_rollout_status']] += 1
    different = audits['DIFFERENT'] != 0
    return {'schema_version': 1, 'contract_id': 'CORE32_CLOSED_REFERENCE_SUITE_V1', 'execution_requested': True,
        'suite_status': 'CLOSED_REFERENCE_SUITE_DIFFERENT' if different else 'CLOSED_REFERENCE_SUITE_MATCH', 'suite_exit_code': int(different),
        'case_count': len(reports), 'all_cases_processed': True, 'audit_counts': audits, 'observed_rollout_counts': observed,
        'difference_count': sum(x['report']['difference_count'] for x in reports),
        'reported_difference_count': sum(x['report']['reported_difference_count'] for x in reports),
        'differences_truncated': any(x['report']['differences_truncated'] for x in reports),
        'reported_synthetic_model_steps': sum(x['report']['synthetic_model_steps'] for x in reports),
        'expected_reference_model_steps': 0, 'reported_work_is_runtime_attestation': False,
        'numeric_preflight_work': 'NONZERO_NOT_AGGREGATED', 'reports': reports,
        **{key: False for key in _FLAGS}, 'gates': dict(GATES),
        'scope': 'FIXED_SIX_CASE_REFERENCE_AUDIT_NOT_GENERIC_OR_SOURCE_OR_VEHICLE_AUTHORITY'}
