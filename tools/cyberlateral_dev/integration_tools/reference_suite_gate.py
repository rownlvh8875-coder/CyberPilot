"""Pure identity check for the sealed normal CORE32 receipt, not a numerical validator."""

import hashlib

RECEIPT_BYTES = 10463
RECEIPT_SHA256 = '6dba6db52bbaf8a5e602a4c2266a2e29908629f894683c67bcdb11adaf32dead'


def reference_suite_pair_summary(first: bytes, second: bytes) -> dict:
    """Require both complete prior-pinned byte records, without parsing or model work."""
    for raw in (first, second):
        if type(raw) is not bytes or len(raw) != RECEIPT_BYTES or hashlib.sha256(raw).hexdigest() != RECEIPT_SHA256:
            raise ValueError('REFERENCE_SUITE_GATE_RECEIPT_IDENTITY')
    if first != second:
        raise ValueError('REFERENCE_SUITE_GATE_BYTE_MISMATCH')
    return {'schema_version': 1, 'contract_id': 'CORE33_FIXED_REFERENCE_SUITE_GATE_V1',
        'status': 'CORE33_FIXED_REFERENCE_SUITE_GATE_PASS', 'byte_identical': True,
        'invocation_count': 2, 'case_count_per_invocation': 6,
        'audit_counts_per_invocation': {'MATCH': 6, 'DIFFERENT': 0},
        'observed_counts_per_invocation': {'MATCH': 4, 'DIFFERENT': 1, 'REJECTED': 1},
        'reported_model_steps_per_invocation': 19, 'reported_model_steps_pair': 38,
        'reported_work_is_runtime_attestation': False, 'expected_generation_model_steps': 0,
        'numeric_preflight_work': 'NONZERO_NOT_AGGREGATED',
        'receipt_identity': {'byte_size': RECEIPT_BYTES, 'sha256': RECEIPT_SHA256},
        'baseline_evidence_zip_sha256': '63fb38b5326ae689ff07fefa171557630b99b220337dc42c46718d33db525737',
        'baseline_member': 'acceptance-1/direct-receipt.json',
        'file_hashes': {name: RECEIPT_SHA256 for name in ('core_reference_one.json', 'core_reference_two.json')},
        'execution_mode': 'DEVELOPMENT_TREE_CLI_NOT_INSTALLED_WHEEL',
        'scope': 'FIXED_RECEIPT_IDENTITY_NOT_GENERIC_NUMERICAL_SOURCE_OR_VEHICLE_AUTHORITY'}
