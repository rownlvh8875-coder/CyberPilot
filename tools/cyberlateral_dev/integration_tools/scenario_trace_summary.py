"""Summarize validated stored stage observations, never replay limiter arithmetic."""

import platform
import sys
from fractions import Fraction
from pathlib import Path

from .scenario_report_data import ReportError, _files, _json, decode_report

EVENTS = ('driver_clip_numeric_changed', 'driver_clip_representation_changed',
          'rate_clip_numeric_changed', 'rate_clip_representation_changed',
          'rate_to_limited_numeric_changed', 'fault_condition_true', 'angle_counter_reset')


def _input_guard(input_path: Path) -> None:
    if (platform.python_implementation() != 'CPython' or platform.python_version() != '3.12.13'
            or sys.platform != 'linux' or (sys.float_info.radix, sys.float_info.mant_dig) != (2, 53)):
        raise ReportError('TRACE_SUMMARY_RUNTIME')
    try:
        absolute = input_path.absolute()
        text = str(absolute)
        text.encode('utf-8', errors='strict')
        if '\0' in text or any(path.is_symlink() for path in [absolute, *absolute.parents]):
            raise ReportError('TRACE_SUMMARY_INPUT_FILE')
    except ReportError:
        raise
    except (OSError, ValueError, RuntimeError) as error:
        raise ReportError('TRACE_SUMMARY_INPUT_FILE') from error


def _number(scalar: dict) -> Fraction:
    # Called only after the existing decoder validates every scalar kind/value.
    if scalar['kind'] in {'python.int', 'numpy.int64'}:
        return Fraction(scalar['value'])
    return Fraction(float.fromhex(scalar['value']))


def summarize_saved_trace(input_path: Path) -> dict:
    _input_guard(input_path)
    owned = _files(input_path)
    data = decode_report(owned)
    record = _json(owned['RESULTS.json'])
    events: dict[str, dict] = {name: {'count': 0, 'first_sample_index': None} for name in EVENTS}
    for row in record['rows']:
        down = row['model_output']['trace']['downstream']
        driver, rate = down['driver_clip'], down['rate_clip']
        observed = (
            _number(driver['x']) != _number(driver['result']),
            driver['x'] != driver['result'],
            _number(rate['x']) != _number(rate['result']),
            rate['x'] != rate['result'],
            _number(rate['result']) != down['limited_command'],
            down['fault_condition'],
            row['prepared']['state']['angle_counter'] > 0 and down['next_state']['angle_counter'] == 0,
        )
        for name, changed in zip(EVENTS, observed, strict=True):
            if changed:
                event = events[name]
                event['count'] += 1
                if event['first_sample_index'] is None:
                    event['first_sample_index'] = row['prepared']['sample']['index']
    view = data['view']
    return {'schema_version': 1, 'contract_id': 'R70_RECORDED_TRACE_STAGE_SUMMARY_V1',
            'status': 'RECORDED_TRACE_SUMMARY_COMPLETE', 'scenario_id': view['scenario_id'],
            'recorded_model_steps': view['recorded_model_steps'], 'recorded_summary': view['summary'],
            'stage_events': events, 'source_hashes': data['source_hashes'],
            'validation_claim': view['validation_claim'], 'source_identity_reauthenticated': False,
            'summary_model_executions': 0, 'summary_reference_executions': 0,
            'time_semantics': view['time_semantics'], 'gates': view['gates'],
            'interpretation': 'OBSERVED_STAGE_RECORD_DIFFERENCES_NOT_UNIQUE_CAUSE_OR_ARITHMETIC_APPROVAL'}
