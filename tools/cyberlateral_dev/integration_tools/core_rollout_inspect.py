"""Bounded read-only identity check for three pinned historical CORE28 fixtures."""

import hashlib
import os
from pathlib import Path

from .core_sequence_run_inspect import RunInspectError, _directory, _read_file
from .core_sequence_suite import SuiteError, _path
from .scenario_output import GATES

# Canonical identities from the independently verified CORE28 evidence seal.
# These are historical byte pins, not regenerated expectations or runtime ZIP verification.
_REFERENCE_ZIP_SHA256 = '2e8f658c5bfa03aea6d688cded43314118d10a949abdc9f7928a3fe4b9362fdc'
_NAMES = ('INPUT.json', 'RESULTS.json', 'SHA256SUMS.txt')
_CASES = {
    'sign-cycle': ('MATCH', 0, 3, (
        (4732, '5d25bdc18d3fb8d29fca5905ce111e5727572f8801dc0071280cd5adf1371309'),
        (2908, 'ec64ff9addea901944b8f3787d345fbb22c82dc68c24864d2a43a3ab85e217f7'),
        (156, 'f6f781f37c0e60649b895940b13f790c78db41d86cb02177d7a92cc729cc56b0'))),
    'declared-difference': ('DIFFERENT', 1, 3, (
        (4741, '4165a779107894c3ff8a772e630dabee13b0173a59f7c53a9d74119521addf37'),
        (3241, '706dd359fcff6be214aeedfb571f0ce911d7a0f766bef836bc389c261872c67b'),
        (156, 'f65fabd1c2a79f3c8afaf2e9c1d92aa3d1c01adb1a26654bfa2025cde35b979f'))),
    'late-invalid': ('REJECTED', 2, 0, (
        (4734, '13b6f346bf8b8df7d9a8390f3efc2782b234ffc1182034363696d08fe5df37f6'),
        (1420, '90ea953b0b9d7ecbb78f33769af1da4466eef3d8def874da724edaf140f53973'),
        (156, 'b942d0677af4b0679a69daa195c0000f59959f7cc0bf1661969f19c2096210f3'))),
}


class RolloutInspectError(ValueError):
    """Fixed inspection diagnostics without caller bytes or private paths."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def inspect_rollout_case(case_id: object, input_root: Path) -> dict:
    """Match captured bytes only; never parse, regenerate, execute or repair them."""
    if type(case_id) is not str or case_id not in _CASES:
        raise RolloutInspectError('ROLLOUT_INSPECT_CASE')
    status, code, steps, identities = _CASES[case_id]
    captured = {}
    try:
        target = _path(input_root, 'ROLLOUT_INSPECT_PATH')
        with _directory(target, {name: False for name in _NAMES}) as directory:
            for name, (size, digest) in zip(_NAMES, identities, strict=True):
                raw = _read_file(directory, name, size)
                actual = hashlib.sha256(raw).hexdigest()
                if len(raw) != size or actual != digest:
                    raise RolloutInspectError('ROLLOUT_INSPECT_ARTIFACT_IDENTITY')
                captured[name] = {'byte_size': len(raw), 'sha256': actual}
            opened, current = os.fstat(directory), target.stat(follow_symlinks=False)
            if (opened.st_dev, opened.st_ino) != (current.st_dev, current.st_ino):
                raise RolloutInspectError('ROLLOUT_INSPECT_ROOT_IDENTITY')
        return {'schema_version': 1, 'contract_id': 'CORE29_PINNED_ROLLOUT_INSPECTION_V1',
            'inspection_status': 'PINNED_CORE28_ARTIFACTS_MATCH', 'inspection_exit_code': 0, 'case_id': case_id,
            'reference_id': 'CORE29_PINNED_CORE28_ARTIFACT_IDENTITIES_V1',
            'reference_evidence_zip_sha256': _REFERENCE_ZIP_SHA256, 'reference_evidence_verified_during_inspection': False,
            'reference_byte_match': True, 'recorded_metadata_origin': 'PINNED_CORE28_VECTOR_NOT_REPARSED',
            'recorded_result_status': status, 'recorded_result_exit_code': code, 'recorded_model_steps': steps,
            'captured_file_count': 3, 'files': captured, 'execution_requested': False,
            'new_synthetic_model_steps': 0, 'new_reference_steps': 0,
            'numeric_validation_work': 'NOT_PERFORMED_SAVED_BYTES_ONLY',
            **{key: False for key in ('input_semantics_revalidated', 'stored_arithmetic_recomputed',
                'source_identity_reauthenticated', 'prehistory_checked', 'v4_payload_allowed', 'f61_input_allowed', 'actual_activation_allowed')},
            'gates': dict(GATES), 'scope': 'PINNED_CLOSED_SAVED_BYTES_ONLY_NOT_CURRENT_INPUT_ARITHMETIC_OR_ORIGIN_PROOF'}
    except RolloutInspectError:
        raise
    except (RunInspectError, SuiteError) as error:
        raise RolloutInspectError('ROLLOUT_INSPECT:' + error.code) from error
    except (OSError, ValueError, RuntimeError) as error:
        raise RolloutInspectError('ROLLOUT_INSPECT_INPUT') from error
