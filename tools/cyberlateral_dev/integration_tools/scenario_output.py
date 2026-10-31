"""Portable projections plus separate actual receipt; no overwrite or retry."""

import csv
import hashlib
import io
import json
from dataclasses import asdict
from pathlib import Path

from .scenario_input import ScenarioError, ScenarioSpec

COLUMNS = ('index request_hex driver_hex angle_hex lat_active previous_requested previous_applied angle_counter_before '
           'integer_request limited_command final_command steer_request angle_counter_after').split()
GATES = {
    'R_BUDGET': 'UNRESOLVED', 'STATIC_EVIDENCE_GATE': 'FAIL', 'actual_r': None, 'T2': None, 'vehicle_scale': None,
    'actual_vehicle_input_authorization': 'NOT_ALLOWED', 'actual_production_activation': 'NOT_ALLOWED',
    'F61_calculator_executions': 0, 'r_calculations': 0, 'dt_calculations': 0,
    'SOURCE_SCHEMA_UNQUALIFIED': 6000, 'Candidate': 'NO_GO', 'Runtime': 'NO_GO', 'D2': 'PERFORMANCE_NOT_EVALUATED',
    'F19': 'LEGACY_UNRESOLVED', 'NATIVE_EXACT_REPLAY': 'NOT_PROVEN',
    'F70UH': 'NOT_ALLOWED', 'F70V': 'NOT_ALLOWED', 'F71': 'NOT_ALLOWED',
}


def canonical(value) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode()


def _cell(value):
    if value is None:
        return 'null'
    if type(value) is bool:
        return 'true' if value else 'false'
    return value


def _hex(value: float) -> str:
    if type(value) is not float:
        raise ScenarioError('SCENARIO_DOMAIN')
    return value.hex()


def render_outputs(spec: ScenarioSpec, result: dict, identity: dict, receipt: dict) -> dict[str, bytes]:
    samples = [{'index': s.index, 'request_hex': _hex(s.request), 'driver_hex': _hex(s.driver),
                'angle_hex': _hex(s.angle_deg), 'lat_active': s.lat_active} for s in spec.samples]
    source = {'schema_version': 1, 'contract_id': 'F70UGZ_R31_DECLARED_SYNTHETIC_V1',
              'scenario_id': spec.scenario_id, 'input_raw_sha256': spec.raw_sha256,
              'input_origin': 'CALLER_DECLARATION_NOT_AUTHENTICATED'}
    typed_input = {**source, 'limits': asdict(spec.limits), 'initial_state': asdict(spec.initial_state), 'samples': samples}
    record = {**source, **result, 'status': 'F70UGZ_R31_DECLARED_SYNTHETIC_SCENARIO_COMPLETE', 'identity': identity,
              'gates': GATES, 'output_scope': 'SCHEMA_SIMULATION_NOT_CAPNP_OR_CAN_WIRE',
              'numerical_claim': 'MODEL_RESULTS_NOT_GENERIC_INDEPENDENT_ORACLE',
              'time_semantics': 'INVOCATION_ORDER_ONLY_NOT_ELAPSED_TIME'}
    text = io.StringIO(newline='')
    writer = csv.writer(text, lineterminator='\n')
    writer.writerow(COLUMNS)
    for row in result['rows']:
        sample, state = row['prepared']['sample'], row['prepared']['state']
        output = row['model_output']
        writer.writerow([_cell(v) for v in [sample['index'], sample['request_hex'], sample['driver_hex'], sample['angle_hex'],
                         sample['lat_active'], state['previous_requested'], state['previous_applied'], state['angle_counter'],
                         output['trace']['quantization']['integer_command'], output['trace']['downstream']['limited_command'],
                         output['projection']['integer_command'], output['steer_request'], output['next_state']['angle_counter']]])
    summary = (f'# 사용자 선언 합성 시나리오 결과\n\n시나리오: {spec.scenario_id}\n\n'
               f'모델 호출: {result["model_steps"]}회. 시간 간격이 아닌 호출 순서만 사용합니다.\n\n'
               'SYNTHETIC_ONLY는 사용자 선언이며 입력의 실제 출처를 인증하지 않습니다.\n'
               '결과는 기존 순수 모델의 출력이며 일반적인 독립 수치 oracle 검증이 아닙니다.\n\n'
               'R_BUDGET=UNRESOLVED, Static Evidence Gate=FAIL. 실차 입력·활성화·F70UH/V/F71은 허용되지 않습니다.\n')
    files = {'INPUT.json': canonical(typed_input), 'RESULTS.json': canonical(record), 'TRACE.csv': text.getvalue().encode(),
             'SUMMARY_KO.md': summary.encode(), 'RECEIPT.json': canonical(receipt)}
    files['SHA256SUMS.txt'] = ''.join(hashlib.sha256(raw).hexdigest() + '  ' + name + '\n' for name, raw in sorted(files.items())).encode()
    return files


def _write_exclusive(path: Path, raw: bytes) -> None:
    with path.open('xb') as stream:
        stream.write(raw)


def publish(output: Path, files: dict[str, bytes]) -> None:
    try:
        output.mkdir(exist_ok=False)
        for name in ['INPUT.json', 'TRACE.csv', 'SUMMARY_KO.md', 'RECEIPT.json', 'SHA256SUMS.txt', 'RESULTS.json']:
            _write_exclusive(output / name, files[name])
    except OSError as error:
        # Preserve any newly created partial directory. No cleanup, overwrite or resume.
        raise ScenarioError('SCENARIO_PUBLICATION_FAILED') from error
