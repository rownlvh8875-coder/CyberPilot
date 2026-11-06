"""Exclusive checked publication of existing CORE21/23 input preflight reports."""

import hashlib
from pathlib import Path

from .core_sequence_archive_preflight import ArchivePreflightError
from .core_sequence_archive_workflow import _output, _publish
from .core_sequence_bundle import PortableError, _expected
from .core_sequence_preflight_report import report_preflight_archive
from .scenario_output import canonical


def publish_preflight_report(input_archive: Path, expected_sha256: str, output_root: Path) -> dict:
    """Preflight once; serialize before mkdir, publish exclusively and read back."""
    try:
        _expected(expected_sha256)
    except PortableError as error:
        raise ArchivePreflightError('ARCHIVE_PREFLIGHT:' + error.code) from error
    target = _output(output_root)
    preflight, markdown = report_preflight_archive(input_archive, expected_sha256)
    code = {'INPUTS_COMPATIBLE': 0, 'INPUTS_REJECTED': 1}[preflight['preflight_status']]
    files = {'PREFLIGHT.json': canonical(preflight), 'SUMMARY_KO.md': markdown}
    files['SHA256SUMS.txt'] = ''.join(hashlib.sha256(raw).hexdigest() + '  ' + name + '\n'
        for name, raw in sorted(files.items())).encode()
    _publish(target, files)
    return {'schema_version': 1, 'contract_id': 'CORE25_PREFLIGHT_WORKFLOW_V1', 'status': 'PREFLIGHT_REPORT_PUBLISHED',
        'preflight_status': preflight['preflight_status'], 'preflight_exit_code': code,
        'archive_sha256': preflight['archive']['archive_sha256'], 'archive_byte_size': preflight['archive']['archive_byte_size'],
        **{key: preflight[key] for key in ('case_count', 'compatible_case_count', 'rejected_case_count',
            'validated_transition_count', 'declared_transition_count', 'recorded_model_steps')},
        'files': {name: {'sha256': hashlib.sha256(raw).hexdigest(), 'byte_size': len(raw)} for name, raw in files.items()},
        'new_synthetic_model_steps': 0, 'new_reference_steps': 0, 'numeric_validation_work': preflight['numeric_validation_work'],
        **{key: preflight[key] for key in ('source_identity_reauthenticated', 'arithmetic_recomputed', 'prehistory_checked',
            'v4_payload_allowed', 'f61_input_allowed', 'actual_activation_allowed')},
        'gates': dict(preflight['gates']), 'scope': 'VERIFIED_INPUT_PREFLIGHT_REPORT_PUBLICATION_NOT_ARITHMETIC_OR_ORIGIN_PROOF'}
