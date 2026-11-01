"""Portable fixed-suite report; no environment receipt or real-vehicle approval."""

import re

from native_qualification.suite_profiles import REGISTRY_SHA256, ROOT, load_profiles
from native_qualification.worker import PUBLIC_WHEEL_SHA, SCHEMA_SHA, WHEEL_SHA, canonical, sha


def build_summary(rows: list[dict]) -> dict:
    profiles = load_profiles()
    if type(rows) is not list or len(rows) != len(profiles):
        raise ValueError('SUITE_COVERAGE')
    for row, profile in zip(rows, profiles, strict=True):
        if type(row) is not dict or type(row.get('summary_sha256')) is not str or not re.fullmatch('[0-9a-f]{64}', row['summary_sha256']):
            raise ValueError('SUITE_COVERAGE')
        expected = {'stage_id': profile.stage_id, 'status': profile.status, 'observations_sha256': profile.observations_sha256,
                    'summary_sha256': row['summary_sha256'], 'reference_sha256': profile.reference_sha256,
                    'case_count': profile.case_count, 'worker_processes': 2,
                    'model_execution_per_worker': profile.model_steps_per_worker, 'model_execution': profile.model_steps_per_worker * 2}
        if canonical(row) != canonical(expected):
            raise ValueError('SUITE_COVERAGE')
    return {'schema_version': 1, 'status': 'F70UGZ_R27_FIXED_NATIVE_SUITE_PASS',
            'scope': 'COMPLETE_FIXED_R19_R26_SYNTHETIC_SUITE_NOT_READER_OR_PRODUCTION_GATE',
            'registry_sha256': REGISTRY_SHA256,
            'tool_sources': {name: sha((ROOT / name).read_bytes()) for name in
                             ['native_qualification/suite.py', 'native_qualification/suite_profiles.py',
                              'native_qualification/suite_validation.py', 'native_qualification/suite_report.py']},
            'identities': {'public_wheel_sha256': PUBLIC_WHEEL_SHA, 'native_wheel_sha256': WHEEL_SHA, 'schema_sha256': SCHEMA_SHA},
            'stage_count': len(rows), 'worker_processes': sum(row['worker_processes'] for row in rows),
            'model_execution': sum(row['model_execution'] for row in rows),
            'model_execution_scope': 'THIS_FIXED_SUITE_WORKERS_NOT_UNIT_TEST_OR_STAGE_TOTAL',
            'stages': [dict(row) for row in rows], 'default_pure_gate': 'UNCHANGED_NOT_RUN_BY_THIS_COMMAND',
            'capabilities': {'fixed_registered_native_cases': 'PASS_FIXED_SYNTHETIC_RECORDS_ONLY',
                             'fixed_registered_model_cases': 'PASS_FIXED_SYNTHETIC_RECORDS_ONLY',
                             'generic_native_reader': 'NOT_IMPLEMENTED', 'actual_call_custody': 'NOT_QUALIFIED'},
            'gates': {'R_BUDGET': 'UNRESOLVED', 'STATIC_EVIDENCE_GATE': 'FAIL', 'actual_activation': 'NOT_ALLOWED',
                      'F61_execution': 0, 'calculator_input_execution': 0, 'Controller_execution': 0, 'Runtime_execution': 0,
                      'CAN': 0, 'actual_inputs': 0, 'r_calculation': 0, 'dt_calculation': 0,
                      'r': None, 'T2': None, 'vehicle_scale': None, 'SOURCE_SCHEMA_UNQUALIFIED': 6000,
                      'Candidate': 'NO_GO', 'Runtime': 'NO_GO', 'D2': 'PERFORMANCE_NOT_EVALUATED', 'F19': 'LEGACY_UNRESOLVED',
                      'NATIVE_EXACT_REPLAY': 'NOT_PROVEN', 'deployment': 'NOT_RUN', 'main_merge': 'NOT_RUN',
                      'native_GitHub_CI': 'NOT_RUN', 'F70UH': 'NOT_ALLOWED', 'F70V': 'NOT_ALLOWED', 'F71': 'NOT_ALLOWED'}}


def render_report(summary: dict) -> str:
    if canonical(summary) != canonical(build_summary(summary['stages'])):
        raise ValueError('SUITE_COVERAGE')
    lines = ['# R27 고정 합성 네이티브 통합 검증', '', 'STATUS: ' + summary['status'], '',
             '등록된 R19–R26 사례만 검증했습니다. 일반 reader·실제 차량·물리 안전 승인이 아닙니다.', '',
             '| 단계 | cases 기록 수 | 이 실행의 합성 모델 호출 |', '| --- | --- | --- |']
    for row in summary['stages']:
        cases = 'N/A' if row['case_count'] is None else str(row['case_count'])
        lines.append('| ' + row['stage_id'] + ' | ' + cases + ' | ' + str(row['model_execution']) + ' |')
    lines.extend(['', 'cases는 JSON cases 배열의 기록 수이며, 전체 독립 테스트·구성·거부 실험 수가 아닙니다.',
                  '등록된 ' + str(summary['stage_count']) + '단계·' + str(summary['worker_processes']) + ' workers·'
                  + str(summary['model_execution']) + ' 모델 호출은 이 suite 실행만의 수치입니다. 단위 테스트·CI 등은 별도입니다.',
                  '기본 순수 검증은 이 명령에서 실행하지 않으며 기존 CI는 바뀌지 않습니다.', '',
                  '## 검증 범위와 남은 기능', '',
                  '- 고정 합성 네이티브/모델 사례: PASS_FIXED_SYNTHETIC_RECORDS_ONLY',
                  '- 일반 native reader: NOT_IMPLEMENTED', '- 실제 호출 이력·상태 custody: NOT_QUALIFIED',
                  '- R_BUDGET: UNRESOLVED / Static Evidence Gate: FAIL',
                  '- 실제 활성화: NOT_ALLOWED / F61·Controller·Runtime·CAN·실제 입력·r·dt 실행: 0',
                  '- 실제 r/T2/vehicle scale: null / Candidate·Runtime: NO_GO / F70UH·F70V·F71: NOT_ALLOWED', '',
                  '환경별 receipts와 manifest는 보존하지만 동일성·OS/ABI 인증을 주장하지 않습니다.',
                  '결과는 일관성과 고정 회귀 검증이며 일반 입력·물리 동작·실제 elapsed time의 증명이 아닙니다.', ''])
    return '\n'.join(lines)
