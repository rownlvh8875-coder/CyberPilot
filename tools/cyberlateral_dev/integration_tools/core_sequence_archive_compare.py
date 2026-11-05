"""Compare two verified saved ZIP captures, never extraction or numerical replay."""

from collections.abc import Callable
from itertools import islice
from pathlib import Path

from .core_sequence_bundle import PortableError, _expected, _verified_suite
from .core_sequence_cases import CASE_IDS
from .core_sequence_compare import DETAIL_LIMIT, _compare_captured, _walk
from .core_sequence_portable import _read_archive
from .scenario_output import GATES, canonical

DETAIL_BYTE_LIMIT = 4_194_304


class ArchiveCompareError(ValueError):
    """Role-qualified fixed diagnostic, no partial comparison or raw caller data."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _preflight(left_sha256: str, right_sha256: str) -> None:
    for side, value in (('LEFT', left_sha256), ('RIGHT', right_sha256)):
        try:
            _expected(value)
        except PortableError as error:
            raise ArchiveCompareError('ARCHIVE_COMPARE_' + side + ':' + error.code) from error


def _load(capture: Callable[[], bytes], expected: str, side: str) -> tuple[dict, dict, bytes]:
    # Closed internal callbacks only; caller-facing APIs accept Paths or bytes.
    try:
        raw = capture()
        receipt, records = _verified_suite(raw, expected)
        return receipt, records, raw
    except PortableError as error:
        raise ArchiveCompareError('ARCHIVE_COMPARE_' + side + ':' + error.code) from error


def _detail_bytes(left_records: dict, right_records: dict) -> int:
    # Stream at most the retained details, discarding each temporary diagnostic.
    # Count escaped JSON bytes, not characters or unescaped pointer lengths.
    size = 0
    for case in CASE_IDS:
        differences = (d for name, key in (('INPUT.json', 'input_record'), ('RESULTS.json', 'result_record'))
                       for d in _walk('/' + name, left_records[case][key], right_records[case][key]))
        for difference in islice(differences, DETAIL_LIMIT):
            size += len(canonical(difference))
            if size > DETAIL_BYTE_LIMIT:
                raise ArchiveCompareError('ARCHIVE_COMPARE_DETAIL_BYTE_LIMIT')
    return size


def _comparison(left: tuple[dict, dict, bytes], right: tuple[dict, dict, bytes]) -> dict:
    lhs, left_records, left_raw = left
    rhs, right_records, right_raw = right
    detail_bytes = _detail_bytes(left_records, right_records)
    reports: list[dict] = [{'case_id': c, 'comparison': _compare_captured(left_records[c], right_records[c])} for c in CASE_IDS]
    counts = {kind: sum(r['comparison']['difference_counts'][kind] for r in reports) for kind in ('INPUT', 'RESULT', 'IDENTITY')}
    total = sum(counts.values())
    reported = sum(r['comparison']['reported_difference_count'] for r in reports)
    changed = sum(r['comparison']['difference_count'] != 0 for r in reports)
    identical = left_raw == right_raw
    return {'schema_version': 1, 'contract_id': 'CORE14_ARCHIVE_COMPARISON_V1',
        'comparison_status': 'SAVED_SUITE_ARCHIVES_IDENTICAL' if identical else 'SAVED_SUITE_ARCHIVES_DIFFERENT',
        'archive_bytes_identical': identical, 'left': lhs, 'right': rhs, 'case_ids': list(CASE_IDS),
        'case_count': len(reports), 'all_cases_processed': True, 'reports': reports,
        'comparison_counts': {'IDENTICAL': len(reports) - changed, 'DIFFERENT': changed},
        'difference_count': total, 'difference_counts': counts, 'reported_difference_count': reported,
        'detail_limit_per_case': DETAIL_LIMIT, 'differences_truncated': total > reported,
        'detail_byte_limit': DETAIL_BYTE_LIMIT, 'reported_difference_bytes': detail_bytes,
        'new_synthetic_model_steps': 0, 'comparison_model_executions': 0, 'comparison_reference_executions': 0,
        'source_identity_reauthenticated': False, 'arithmetic_recomputed': False, 'gates': dict(GATES),
        'scope': 'VERIFIED_SAVED_ZIP_COMPARISON_NOT_ARITHMETIC_OR_ORIGIN_PROOF'}


def compare_suite_archive_bytes(left: bytes, left_sha256: str, right: bytes, right_sha256: str) -> dict:
    """Preflight both digests, then verify/compare each captured byte role once."""
    _preflight(left_sha256, right_sha256)
    return _comparison(_load(lambda: left, left_sha256, 'LEFT'), _load(lambda: right, right_sha256, 'RIGHT'))


def compare_suite_archives(left: Path, left_sha256: str, right: Path, right_sha256: str) -> dict:
    """Read exactly two roles after digest preflight; no source reopen or writes."""
    _preflight(left_sha256, right_sha256)
    return _comparison(_load(lambda: _read_archive(left), left_sha256, 'LEFT'), _load(lambda: _read_archive(right), right_sha256, 'RIGHT'))


def exit_code(report: dict) -> int:
    """Comparator-owned report only: stored numerical outcomes do not set exit."""
    return 0 if report['archive_bytes_identical'] else 1
