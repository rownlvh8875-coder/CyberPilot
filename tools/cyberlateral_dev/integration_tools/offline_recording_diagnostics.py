"""Explicit synthetic recorded-transition diagnostics, not actual input authority."""

from .offline_recording_codec import decode_recording
from .offline_recording_input_codec import decode_recording_input
from .offline_recording_preflight import preflight_recording_input
from .synthetic_sequence_check import SyntheticSequenceCheckV1, check_synthetic_sequence


def check_recorded_synthetic_sequence(recording: object, contexts: object) -> SyntheticSequenceCheckV1:
    """Preflight the whole recording, then diagnose every declared transition."""
    checked = preflight_recording_input(recording, contexts)
    return check_synthetic_sequence(checked.recording.records, checked.contexts)


def check_serialized_synthetic_recording(raw: object, contexts: object) -> SyntheticSequenceCheckV1:
    """Strictly decode canonical synthetic bytes, then explicitly diagnose them."""
    return check_recorded_synthetic_sequence(decode_recording(raw), contexts)


def check_serialized_recording_input(raw: object) -> SyntheticSequenceCheckV1:
    """Decode the full explicit synthetic input,then diagnose without context overrides."""
    checked = decode_recording_input(raw)
    return check_recorded_synthetic_sequence(checked.recording, checked.contexts)
