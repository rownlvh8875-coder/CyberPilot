"""Single-capture declared-synthetic diagnostics;not actual input or source authority."""

import hashlib
import os
import stat
from dataclasses import asdict
from pathlib import Path

from .offline_recording_diagnostics import check_serialized_recording_input
from .scenario_output import GATES

LIMIT = 1048576


class RecordingInputRunError(ValueError):
    """Fixed pre-execution file/digest code, never caller data."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _capture(path: Path) -> bytes:
    if not isinstance(path, Path):
        raise RecordingInputRunError('RECORDING_DIAGNOSTICS_INPUT_FILE')
    try:
        target = path.absolute()
        text = str(target)
        text.encode('utf-8', errors='strict')
        if '\0' in text or any(p.is_symlink() for p in (target, *target.parents)):
            raise RecordingInputRunError('RECORDING_DIAGNOSTICS_INPUT_FILE')
        fd = os.open(target, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode):
                raise RecordingInputRunError('RECORDING_DIAGNOSTICS_INPUT_FILE')
            if not 0 < info.st_size <= LIMIT:
                raise RecordingInputRunError('RECORDING_DIAGNOSTICS_INPUT_SIZE')
            chunks, size = [], 0
            while size <= LIMIT:
                raw = os.read(fd, LIMIT + 1 - size)
                if not raw:
                    break
                chunks.append(raw)
                size += len(raw)
            if not 0 < size <= LIMIT:
                raise RecordingInputRunError('RECORDING_DIAGNOSTICS_INPUT_SIZE')
            return b''.join(chunks)
        finally:
            os.close(fd)
    except RecordingInputRunError:
        raise
    except (OSError, ValueError, RuntimeError) as error:
        raise RecordingInputRunError('RECORDING_DIAGNOSTICS_INPUT_FILE') from error


def _diagnose_captured(raw: bytes) -> dict:
    """Run unchanged CORE58 on owned bytes and preserve the CORE61 record format."""
    checked = check_serialized_recording_input(raw)
    rows = [{'transition_index': i, 'model_index': check.context.model_index, 'status': check.status,
             'declared_entry_state': asdict(check.prepared.model_state),
             'computed_next_state': asdict(check.computed_next_state),
             'declared_saved_state': {'saved_limited_state': check.current.saved_limited_state,
                                      'saved_angle_counter': check.current.saved_angle_counter},
             'differences': [asdict(difference) for difference in check.differences]}
            for i, check in enumerate(checked.checks)]
    return {'schema_version': 1, 'contract_id': 'CORE61_COUNTERFACTUAL_RECORDING_DIAGNOSTICS_V1',
        'scope': 'DECLARED_SYNTHETIC_INPUT_DIAGNOSTICS_ONLY', 'input_sha256': hashlib.sha256(raw).hexdigest(), 'input_bytes': len(raw),
        'status': checked.status, 'frame_count': len(checked.frames),
        'checked_transition_count': checked.checked_transition_count,
        'new_synthetic_model_steps': checked.synthetic_model_steps,
        'differing_transition_indices': list(checked.differing_transition_indices), 'rows': rows,
        'validation_claim': checked.validation_claim, 'state_feed_rule': checked.state_feed_rule,
        'first_frame_transition_checked': checked.first_frame_transition_checked,
        'prehistory_checked': checked.prehistory_checked,
        'source_identity_reauthenticated': checked.source_identity_reauthenticated,
        'v4_payload_allowed': checked.v4_payload_allowed, 'f61_input_allowed': checked.f61_input_allowed,
        'actual_activation_allowed': checked.actual_activation_allowed, 'gates': dict(GATES)}


def run_recording_input(input_file: Path, expected_sha256: str) -> dict:
    """Pin one capture,then explicitly run unchanged CORE58;no reopen or publication."""
    if type(expected_sha256) is not str or len(expected_sha256) != 64 or any(c not in '0123456789abcdef' for c in expected_sha256):
        raise RecordingInputRunError('RECORDING_DIAGNOSTICS_INPUT_SHA256')
    raw = _capture(input_file)
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise RecordingInputRunError('RECORDING_DIAGNOSTICS_INPUT_CHECKSUM')
    return _diagnose_captured(raw)
