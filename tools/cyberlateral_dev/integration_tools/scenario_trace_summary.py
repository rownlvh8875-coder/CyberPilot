"""Summarize validated stored stage observations, never replay limiter arithmetic."""

import platform
import sys
from fractions import Fraction
from pathlib import Path

from .scenario_output import canonical
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


def _markdown(record: dict) -> bytes:
    labels = ('driver clip 숫자 차이', 'driver clip 타입·표현 차이',
              'rate clip 숫자 차이', 'rate clip 타입·표현 차이',
              'rate result → 정수 limited 숫자 차이', '기록된 fault 조건 true', '기록된 angle counter 초기화')
    lines = ['# 저장된 단계 관찰 요약', '', f'시나리오: `{record["scenario_id"]}`', '',
             f'기록된 모델 호출: {record["recorded_model_steps"]}회. 요약의 새 모델·참조 실행: 0회.', '',
             '| 관찰 | event key | 횟수 | 최초 sample index |', '| --- | --- | ---: | ---: |']
    for key, label in zip(EVENTS, labels, strict=True):
        event = record['stage_events'][key]
        first = '-' if event['first_sample_index'] is None else str(event['first_sample_index'])
        lines.append(f'| {label} | `{key}` | {event["count"]} | {first} |')
    lines.extend(['', '## 기존 R32 기록 요약', '', '| 항목 | 횟수 |', '| --- | ---: |'])
    for key, value in record['recorded_summary'].items():
        lines.append(f'| `{key}` | {value} |')
    lines.extend(['', '## 해석 경계', '',
                  '이벤트는 중복될 수 있으며 서로 배타적인 원인이 아닙니다. 숫자 동등과 타입·표현 동등은 다릅니다.',
                  '비교는 같은 정수 command 단계의 저장값에 한정됩니다. 정규화 요청·물리 torque·초당 rate 비교가 아닙니다.',
                  '최초 index는 기록된 sample index이며 row offset·실제 초·10ms 주기가 아닙니다.',
                  'fault 조건·요청 억제는 실차 고장 또는 최종 command=0을 뜻하지 않습니다.',
                  '체크섬과 레코드 일관성 검사만 수행합니다. 산술 재검산·원본 출처 인증·실차 승인이 아닙니다.',
                  f'`{record["validation_claim"]}`', f'`{record["interpretation"]}`', f'`{record["time_semantics"]}`',
                  '`source_identity_reauthenticated=false`', '',
                  f'캡처한 RESULTS.json SHA256: `{record["source_hashes"]["RESULTS.json"]}`', '',
                  '## 유지되는 Gate', '', '| 항목 | 저장값 |', '| --- | --- |'])
    for key, value in record['gates'].items():
        lines.append(f'| `{key}` | `{canonical(value).decode().strip()}` |')
    lines.extend(['', 'F61·r/dt 계산·Controller·Runtime·CAN·실차 활성화는 수행하거나 허용하지 않습니다.', ''])
    return '\n'.join(lines).encode()


def format_saved_trace(input_path: Path, output_format: str = 'json') -> bytes:
    if type(output_format) is not str or output_format not in {'json', 'markdown'}:
        raise ReportError('TRACE_SUMMARY_FORMAT')
    record = summarize_saved_trace(input_path)
    return canonical(record) if output_format == 'json' else _markdown(record)
