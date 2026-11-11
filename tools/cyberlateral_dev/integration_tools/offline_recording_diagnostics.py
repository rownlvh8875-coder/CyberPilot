"""Explicit synthetic recorded-transition diagnostics, not actual input authority."""

from .offline_recording_preflight import preflight_recording_input
from .synthetic_sequence_check import SyntheticSequenceCheckV1, check_synthetic_sequence


def check_recorded_synthetic_sequence(recording: object, contexts: object) -> SyntheticSequenceCheckV1:
    """Preflight the whole recording, then diagnose every declared transition."""
    checked = preflight_recording_input(recording, contexts)
    return check_synthetic_sequence(checked.recording.records, checked.contexts)
