"""Input semantics of one verified portable suite, never extraction or replay."""

from pathlib import Path

from .core_sequence_bundle import PortableError, _expected, _verified_suite
from .core_sequence_cases import CASE_IDS
from .core_sequence_input_preflight import _preflight_captured
from .core_sequence_portable import _read_archive
from .scenario_output import GATES


class ArchivePreflightError(ValueError):
    """Fixed integrity/capture diagnostic, not a semantic rejection receipt."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def preflight_suite_archive_bytes(raw: bytes, expected_sha256: str) -> dict:
    """Fully verify once before processing every owned case in fixed order."""
    try:
        archive, records = _verified_suite(raw, expected_sha256)
    except PortableError as error:
        raise ArchivePreflightError('ARCHIVE_PREFLIGHT:' + error.code) from error
    reports = []
    counts = {'INPUTS_COMPATIBLE': 0, 'INPUTS_REJECTED': 0}
    for case in CASE_IDS:
        report = _preflight_captured(records[case])
        counts[report['preflight_status']] += 1
        reports.append(report)
    return {'schema_version': 1, 'contract_id': 'CORE21_PORTABLE_SUITE_INPUT_PREFLIGHT_V1',
        'archive': archive, 'case_ids': list(CASE_IDS), 'case_reports': reports, 'case_count': len(reports),
        'all_cases_processed': True, 'preflight_status': 'INPUTS_REJECTED' if counts['INPUTS_REJECTED'] else 'INPUTS_COMPATIBLE',
        'compatible_case_count': counts['INPUTS_COMPATIBLE'], 'rejected_case_count': counts['INPUTS_REJECTED'],
        'validated_transition_count': sum(r['validated_transition_count'] for r in reports),
        'declared_transition_count': sum(r['declared_transition_count'] for r in reports),
        'recorded_model_steps': sum(r['recorded_model_steps'] for r in reports),
        'new_synthetic_model_steps': 0, 'new_reference_steps': 0, 'numeric_validation_work': 'NONZERO_NOT_AGGREGATED',
        'source_identity_reauthenticated': False, 'arithmetic_recomputed': False, 'prehistory_checked': False,
        'v4_payload_allowed': False, 'f61_input_allowed': False, 'actual_activation_allowed': False, 'gates': dict(GATES)}


def preflight_suite_archive(input_archive: Path, expected_sha256: str) -> dict:
    """Validate digest format before caller path access, then capture once."""
    try:
        _expected(expected_sha256)
        raw = _read_archive(input_archive)
    except PortableError as error:
        raise ArchivePreflightError('ARCHIVE_PREFLIGHT:' + error.code) from error
    return preflight_suite_archive_bytes(raw, expected_sha256)
