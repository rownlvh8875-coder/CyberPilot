"""Read-only audit tables from an exact validated fixed synthetic R16 pair."""

import argparse
import csv
import hashlib
import io
import json
import sys
from pathlib import Path

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # DEV stdlib glue, never src/reference/native selectors.

from integration_tools.lifecycle_validation import read_lifecycle_pair

COLUMNS = (
    'scenario_id offset invocation_index sequence_id seed_origin source_request source_request_hex lat_active driver driver_hex '
    'angle_deg angle_deg_hex STEER_MAX STEER_DELTA_UP STEER_DELTA_DOWN STEER_DRIVER_ALLOWANCE STEER_DRIVER_FACTOR '
    'STEER_DRIVER_MULTIPLIER previous_requested previous_applied angle_counter quantized_integer driver_clip_result rate_clip_result '
    'limited_command final_command normalized_expression normalized_expression_hex steer_request next_index next_previous_requested '
    'next_previous_applied next_angle_counter source_result_sha256 custody_claim precision_claim time_semantics'
).split()


def canonical(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode()


def _render_audit(record: dict, source_sha: str) -> dict[str, bytes]:
    """Project a trusted validated snapshot, not an arbitrary-data input API."""
    rows, summaries = [], []
    for scenario, splits in zip(record['baseline']['scenarios'], record['split_runs'], strict=True):
        summaries.append({'id': scenario['id'], 'samples': scenario['steps'], 'cuts': len(splits['cuts']),
                          'seed_origin': scenario['seed_origin'], 'result_sha256': scenario['result_sha256']})
        for offset, prepared in enumerate(scenario['prepared']):
            sample, state = prepared['sample'], prepared['state']
            output = scenario['result']['outputs'][offset]
            downstream, quantization, projection = output['trace']['downstream'], output['trace']['quantization'], output['projection']
            row = {
                'scenario_id': scenario['id'], 'offset': offset, 'invocation_index': sample['index'], 'sequence_id': prepared['sequence_id'],
                'seed_origin': scenario['seed_origin'], 'source_request': sample['request'], 'source_request_hex': sample['request'].hex(),
                'lat_active': sample['lat_active'], 'driver': sample['driver'], 'driver_hex': sample['driver'].hex(),
                'angle_deg': sample['angle_deg'], 'angle_deg_hex': sample['angle_deg'].hex(),
                'previous_requested': state['previous_requested'], 'previous_applied': state['previous_applied'], 'angle_counter': state['angle_counter'],
                'quantized_integer': quantization['integer_command'], 'driver_clip_result': downstream['driver_clip']['result']['value'],
                'rate_clip_result': downstream['rate_clip']['result']['value'], 'limited_command': downstream['limited_command'],
                'final_command': downstream['final_command'], 'normalized_expression': projection['normalized_expression'],
                'normalized_expression_hex': projection['normalized_expression_hex'], 'steer_request': output['steer_request'],
                'next_index': output['next_state']['index'], 'next_previous_requested': output['next_state']['previous_requested'],
                'next_previous_applied': output['next_state']['previous_applied'], 'next_angle_counter': output['next_state']['angle_counter'],
                'source_result_sha256': scenario['result_sha256'], 'custody_claim': prepared['custody_claim'],
                'precision_claim': prepared['precision_claim'], 'time_semantics': prepared['time_semantics'],
            }
            row.update(sample['limits'])
            rows.append(row)
    audit = {
        'schema_version': 1, 'contract_id': 'F70UGZ_R17_FIXED_HANDOFF_AUDIT_V1', 'status': 'F70UGZ_R17_FIXED_HANDOFF_AUDIT_PASS',
        'scope': 'READ_ONLY_VIEW_OF_FROZEN_SYNTHETIC_EVIDENCE_NOT_NEW_EXECUTION_OR_POLICY',
        'input_lifecycle_sha256': source_sha, 'scenario_count': len(summaries), 'row_count': len(rows), 'columns': COLUMNS,
        'rows': rows, 'scenario_summaries': summaries, 'gates': record['gates'],
        'source_execution_counts': {'model_steps': record['model_steps'], 'extractor_calls': record['extractor_calls']},
        'report_execution_counts': {'model_steps': 0, 'extractor_calls': 0, 'F61': 0, 'r_calculations': 0, 'dt_calculations': 0},
        'time_semantics': 'INVOCATION_ORDER_ONLY_NOT_ELAPSED_TIME',
    }
    stream = io.StringIO(newline='')
    writer = csv.writer(stream, lineterminator='\n')
    writer.writerow(COLUMNS)
    for row in rows:
        writer.writerow(row[name] if type(row[name]) is str else json.dumps(row[name], allow_nan=False) for name in COLUMNS)
    lines = [
        '# 고정 합성 메시지 상태 인계 감사표', '',
        '검증된 R16 근거를 읽기 전용으로 표시합니다. 실제 차량 입력·native custody·성능·안전 승인이 아닙니다.', '',
        f'입력 RESULTS SHA256: `{source_sha}`', '',
        '7개 시나리오·112행·37열입니다. 보고서 모델/추출기/F61/r/dt 계산은 모두 0입니다.',
        '근거의 프로세스당 9010회 합성 호출과 보고서의 0회를 구분합니다. 시간은 호출 순서일 뿐 elapsed time이 아닙니다.', '',
        '| Scenario | Samples | Cuts | Seed origin | Result SHA256 |',
        '| --- | ---: | ---: | --- | --- |',
    ]
    lines.extend(f"| {s['id']} | {s['samples']} | {s['cuts']} | {s['seed_origin']} | {s['result_sha256']} |" for s in summaries)
    lines += [
        '', 'history-scale index1은 선언된 seed이며 관측된 이전 호출을 뜻하지 않습니다.',
        'CSV의 null·true/false·-0.0과 binary64 hex를 보존합니다. 스프레드시트가 값을 변환할 수 있으므로 정밀도는 JSON/hex로 확인하세요.',
        '임의 로그 입력·checkpoint·native reader·차량 실행 경로는 제공하지 않습니다. 기존 기준 자료의 일관성이지 새 산술/출처 인증이 아닙니다.', '',
        '## 유지되는 Gate', '', '```json', canonical(record['gates']).decode().rstrip(), '```', '',
    ]
    return {'AUDIT.json': canonical(audit), 'audit.csv': stream.getvalue().encode(), 'SUMMARY_KO.md': '\n'.join(lines).encode()}


def _manifest(files: dict[str, bytes]) -> bytes:
    return ''.join(hashlib.sha256(raw).hexdigest() + '  ' + name + '\n' for name, raw in sorted(files.items())).encode()


def write_audit(first: Path, second: Path, output: Path) -> None:
    if output.exists() or output.is_symlink():
        raise FileExistsError('OUTPUT_EXISTS_NO_AUDIT_WORK')
    record, summary = read_lifecycle_pair(first, second)
    files = _render_audit(record, summary['file_hashes']['RESULTS.json'])
    forbidden = {'cyberlateral_dev', 'numpy', 'kernel', 'openpilot', 'selfdrive', 'opendbc', 'cereal', 'capnp', 'normalized_reference', 'output_oracle',
                 'synthetic_rate_constraint_feasibility_v1', 'synthetic_rate_constraint_feasibility_reconstructed_v2'}
    files['EXECUTION.json'] = canonical({'isolated': bool(sys.flags.isolated),
                                         'forbidden_modules_loaded': sorted(n for n in sys.modules if n.split('.')[0] in forbidden)})
    files['SHA256SUMS.txt'] = _manifest(files)
    output.mkdir(parents=True, exist_ok=False)
    with (output / 'AUDIT.pending').open('xb') as stream:
        stream.write(files['AUDIT.json'])
    for name, raw in files.items():
        if name != 'AUDIT.json':
            with (output / name).open('xb') as stream:
                stream.write(raw)
    (output / 'AUDIT.pending').rename(output / 'AUDIT.json')


def read_audit_pair(first_report: Path, second_report: Path, first_source: Path, second_source: Path) -> tuple[dict, dict[str, bytes], dict]:
    record, source_summary = read_lifecycle_pair(first_source, second_source)
    try:
        one = {p.name: p.read_bytes() for p in first_report.iterdir()}
        two = {p.name: p.read_bytes() for p in second_report.iterdir()}
    except OSError as error:
        raise ValueError('AUDIT_ARTIFACT_READ') from error
    if set(one) != {'AUDIT.json', 'audit.csv', 'SUMMARY_KO.md', 'EXECUTION.json', 'SHA256SUMS.txt'} or one != two:
        raise ValueError('AUDIT_ARTIFACT_MISSING_OR_BYTE_MISMATCH')
    expected = _render_audit(record, source_summary['file_hashes']['RESULTS.json'])
    expected['EXECUTION.json'] = canonical({'isolated': True, 'forbidden_modules_loaded': []})
    expected['SHA256SUMS.txt'] = _manifest(expected)
    if one != expected:
        raise ValueError('AUDIT_PAYLOAD_SOURCE_ENVIRONMENT_OR_MANIFEST_MISMATCH')
    summary = {'status': 'F70UGZ_R17_FIXED_HANDOFF_AUDIT_PASS', 'byte_identical': True, 'scenario_count': 7, 'row_count': 112, 'model_steps': 0,
            'input_lifecycle_sha256': source_summary['file_hashes']['RESULTS.json'],
            'file_hashes': {name: hashlib.sha256(raw).hexdigest() for name, raw in sorted(one.items())},
            'scope': 'read-only fixed evidence view; shared projection acceptance is not an independent mapping or numerical oracle'}
    return record, one, summary


def audit_pair_summary(first_report: Path, second_report: Path, first_source: Path, second_source: Path) -> dict:
    return read_audit_pair(first_report, second_report, first_source, second_source)[2]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--first', type=Path, required=True, help='first exact fixed R16 artifact directory')
    parser.add_argument('--second', type=Path, required=True, help='second exact fixed R16 artifact directory')
    parser.add_argument('--output', type=Path, required=True, help='NEW directory')
    args = parser.parse_args(argv)
    try:
        write_audit(args.first, args.second, args.output)
    except (OSError, ValueError, RuntimeError, ImportError) as error:
        print(f'REJECTED: {error}', file=sys.stderr)
        return 2
    print('F70UGZ_R17_FIXED_HANDOFF_AUDIT_PASS')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
