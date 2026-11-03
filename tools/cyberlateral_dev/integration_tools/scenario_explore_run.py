"""Generate bounded synthetic inputs and retain existing independent verdicts."""

import hashlib
import platform
import sys
from pathlib import Path

from . import scenario_workflow_run as workflow
from .scenario_batch_input import _read
from .scenario_explore_generate import ExplorationError, generate_cases, generation_record
from .scenario_input import ScenarioError
from .scenario_output import GATES, canonical
from .scenario_report_data import ReportError, _json

ROOT = Path(__file__).resolve().parents[1]


def _source_identity() -> dict:
    names = ['integration_tools/scenario_explore_generate.py', 'integration_tools/scenario_explore_run.py',
             'tools/scenario_explore.py']
    return {'workflow': workflow._source_identity(), 'reference': workflow.reference._source_identity(),
            'exploration': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in names}}


def _preflight(output: Path) -> None:
    if output.exists() or output.is_symlink():
        raise ExplorationError('EXPLORATION_OUTPUT_EXISTS')
    if not output.parent.is_dir():
        raise ExplorationError('EXPLORATION_OUTPUT_PARENT')
    try:
        str(output.absolute()).encode('utf-8', errors='strict')
        if output.resolve().is_relative_to(ROOT.resolve()):
            raise ExplorationError('EXPLORATION_OUTPUT_LOCATION')
    except UnicodeError as error:
        raise ExplorationError('EXPLORATION_PATH_ENCODING') from error
    except (OSError, RuntimeError) as error:
        raise ExplorationError('EXPLORATION_OUTPUT_LOCATION') from error
    if (platform.python_implementation() != 'CPython' or platform.python_version() != '3.12.13'
            or sys.platform != 'linux' or (sys.float_info.radix, sys.float_info.mant_dig) != (2, 53)):
        raise ExplorationError('EXPLORATION_RUNTIME')


def _write(path: Path, raw: bytes) -> None:
    with path.open('xb') as stream:
        stream.write(raw)


def _read_reference_record(path: Path, count: int) -> dict:
    """Own bounded canonical bytes and check consumed shapes before traversal."""
    try:
        record = _json(_read(path))
    except (ScenarioError, ReportError) as error:
        raise ExplorationError('EXPLORATION_STAGE_RECORD') from error

    def require(condition):
        if not condition:
            raise ExplorationError('EXPLORATION_STAGE_RECORD')

    integers = {'input_count', 'completed_cases', 'matched_cases', 'different_cases', 'error_cases',
                'input_rejections_confirmed', 'input_rejections_unverified', 'rejection_mismatch_cases',
                'reference_steps', 'numerical_difference_count'}
    require(type(record) is dict and integers | {'status', 'cases', 'reference_helper_counts'} <= record.keys())
    require(type(record['status']) is str and all(type(record[key]) is int for key in integers))
    require(type(record['cases']) is list and len(record['cases']) == count)
    helpers = record['reference_helper_counts']
    require(type(helpers) is dict and set(workflow.reference.COUNT_KEYS) <= helpers.keys())
    require(all(type(helpers[key]) is int for key in workflow.reference.COUNT_KEYS))
    fields = {'case_id', 'source_status', 'status', 'report', 'reference_steps', 'difference_count', 'first_difference', 'error_code'}
    for number, case in enumerate(record['cases'], 1):
        require(type(case) is dict and fields <= case.keys())
        require(all(type(case[key]) is str for key in ['case_id', 'source_status', 'status']))
        require(all(case[key] is None or type(case[key]) is int for key in ['reference_steps', 'difference_count']))
        require(all(case[key] is None or type(case[key]) is str for key in ['report', 'error_code']))
        first = case['first_difference']
        require(first is None or (type(first) is dict and 'field' in first and type(first['field']) is str))
        case_id = f'case-{number:03d}'
        require(case['case_id'] == case_id and case['report'] in {None, case_id + '/REFERENCE_CHECK.json'})
    return record


def _findings(output: Path, checked: dict, payloads: dict[str, bytes]) -> list[dict]:
    cases = checked['cases']
    if len(cases) != len(payloads):
        raise ExplorationError('EXPLORATION_STAGE_RECORD')
    findings = []
    for number, (case, (name, raw)) in enumerate(zip(cases, payloads.items(), strict=True), 1):
        case_id = f'case-{number:03d}'
        if case['case_id'] != case_id or case['report'] not in {None, case_id + '/REFERENCE_CHECK.json'}:
            raise ExplorationError('EXPLORATION_STAGE_RECORD')
        if case['status'] == 'MATCH':
            continue
        if not findings:
            (output / 'reproducers').mkdir(exist_ok=False)
        relative = 'reproducers/' + name
        _write(output / relative, raw)
        findings.append({'case_id': case_id, 'case_status': case['status'], 'reproducer': relative,
                         'reproducer_scope': 'FULL_ORIGINAL_SEQUENCE_NOT_MINIMIZED',
                         'input_sha256': hashlib.sha256(raw).hexdigest(), 'difference_count': case['difference_count'],
                         'first_difference': case['first_difference'], 'error_code': case['error_code'],
                         'reference_report': 'workflow/reference/' + case['report'] if case['report'] is not None else None})
    return findings


def _verdict(produced: dict, checked: dict, cases: int, steps: int) -> str:
    exact_counts = (type(produced['completed']) is int and produced['completed'] == cases
                    and type(produced['rejected']) is int and produced['rejected'] == 0
                    and type(produced['model_steps']) is int and produced['model_steps'] == cases * steps
                    and type(produced['reference_steps']) is int and produced['reference_steps'] == cases * steps)
    if not exact_counts or any(case['status'] not in {'MATCH', 'DIFFERENT'} for case in checked['cases']):
        return 'ERROR'
    for case in checked['cases']:
        if (case['source_status'] != 'COMPLETE' or type(case['reference_steps']) is not int or case['reference_steps'] != steps
                or type(case['difference_count']) is not int or case['difference_count'] < 0 or case['error_code'] is not None
                or (case['status'] == 'MATCH' and (case['difference_count'] != 0 or case['first_difference'] is not None))
                or (case['status'] == 'DIFFERENT' and (case['difference_count'] == 0 or type(case['first_difference']) is not dict))):
            return 'ERROR'
    expected = {'input_count': cases, 'completed_cases': cases, 'matched_cases': sum(c['status'] == 'MATCH' for c in checked['cases']),
                'different_cases': sum(c['status'] == 'DIFFERENT' for c in checked['cases']), 'error_cases': 0,
                'input_rejections_confirmed': 0, 'input_rejections_unverified': 0, 'rejection_mismatch_cases': 0,
                'reference_steps': cases * steps, 'numerical_difference_count': sum(c['difference_count'] for c in checked['cases'])}
    if len(checked['cases']) != cases or any(type(checked[k]) is not int or checked[k] != v for k, v in expected.items()):
        return 'ERROR'
    helpers = {'compile_calls': cases, 'selected_definitions_compiled': 2 * cases, 'limiter_direct': 0,
               'limiter_traced': cases * steps, 'fault_explicit': cases * steps, 'fault_default': 0, 'traced_clip_calls': 2 * cases * steps}
    for counts in [checked['reference_helper_counts'], produced['reference_helper_counts']]:
        if counts.keys() != helpers.keys() or any(type(counts[k]) is not int or counts[k] != v for k, v in helpers.items()):
            return 'ERROR'
    if (type(produced['input_count']) is not int or produced['input_count'] != cases
            or type(produced['reference_difference_count']) is not int
            or produced['reference_difference_count'] != expected['numerical_difference_count']
            or produced['reference_status'] != checked['status']):
        return 'ERROR'
    if (produced['status'] == 'VERIFIED' and checked['status'] == 'MATCH'
            and all(case['status'] == 'MATCH' for case in checked['cases']) and checked['numerical_difference_count'] == 0):
        return 'MATCH'
    if (produced['status'] == 'REFERENCE_DIFFERENT' and checked['status'] == 'DIFFERENT'
            and any(case['status'] == 'DIFFERENT' for case in checked['cases']) and checked['numerical_difference_count'] > 0):
        return 'DIFFERENT'
    return 'ERROR'


def exit_code(record: dict) -> int:
    return 0 if record['status'] == 'MATCH' else 1 if record['status'] == 'DIFFERENT' else 2


def _summary(record: dict) -> bytes:
    text = ('# 자동 생성 합성 경계 탐색\n\n'
            f'상태: {record["status"]}\n\n'
            f'seed {record["parameters"]["seed"]}, case {record["parameters"]["cases"]}개, '
            f'case당 {record["parameters"]["steps"]}samples.\n'
            f'새 합성 모델 {record["model_steps"]}steps / 독립 참조 {record["reference_steps"]}steps.\n'
            f'참조 수치 차이 {record["difference_count"]}, 보존된 비일치 case {len(record["findings"])}개.\n\n'
            '[생성 조건·입력 feature 수](GENERATION.json) · [그래프·표](workflow/batch/index.html) · '
            '[독립 참조](workflow/reference/SUMMARY_KO.md)\n\n')
    for finding in record['findings']:
        text += f'- {finding["case_id"]}: {finding["case_status"]} / [전체 재현 입력]({finding["reproducer"]})\n'
    text += ('\n입력 feature 수는 exhaustive branch coverage가 아닙니다. 재현 입력은 전체 원형 sequence이며 최소화하지 않습니다.\n'
             '허용오차·기준 자동 수정·fallback·차량 성능 최적화는 없습니다.\n'
             '참조 계산량은 성공 보고서만 집계하며 실패한 작업은 추가 NONZERO일 수 있습니다.\n'
             '결과에는 private receipt와 로그가 있어 자동 공유하지 않습니다.\n'
             'bounded 합성·선택 source parity이며 물리 안전·실제 이력 인증이 아닙니다. 호출 순서는 실제 시간·100Hz가 아닙니다.\n'
             'R_BUDGET=UNRESOLVED, Static Gate=FAIL, 실제r/T2/scale=null.\n'
             'F61·실제r/dt·Controller·차량 Runtime·CAN·실차 입력·활성화·후보 성능 평가는0. F70UH/V/F71 NOT_ALLOWED.\n')
    return text.encode()


def _publish(output: Path, record: dict) -> None:
    paths = list(output.rglob('*'))
    if any(path.is_symlink() for path in paths):
        raise ExplorationError('EXPLORATION_OUTPUT_CHANGED')
    files = {path.relative_to(output).as_posix(): path.read_bytes() for path in paths if path.is_file()}
    files.update({'EXPLORATION.json': canonical(record), 'SUMMARY_KO.md': _summary(record)})
    _write(output / 'SUMMARY_KO.md', files['SUMMARY_KO.md'])
    _write(output / 'SHA256SUMS.txt', workflow.batch._manifest(files))
    _write(output / 'EXPLORATION.json', files['EXPLORATION.json'])


def run_exploration(seed: int, cases: int, steps: int, output: Path) -> dict:
    payloads = generate_cases(seed, cases, steps)
    generated = generation_record(seed, cases, steps, payloads)
    try:
        _preflight(output)
    except ExplorationError:
        raise
    except (OSError, ValueError) as error:
        raise ExplorationError('EXPLORATION_IO') from error
    try:
        identity = _source_identity()
        output.mkdir(exist_ok=False)
        (output / 'generated').mkdir(exist_ok=False)
        for name, raw in payloads.items():
            _write(output / 'generated' / name, raw)
        _write(output / 'GENERATION.json', canonical(generated))
        produced = workflow.run_workflow([output / 'generated' / name for name in payloads], output / 'workflow')
        if _source_identity() != identity:
            raise ExplorationError('EXPLORATION_SOURCE_CHANGED')
        if any((output / 'generated' / name).read_bytes() != raw for name, raw in payloads.items()):
            raise ExplorationError('EXPLORATION_INPUT_CHANGED')
        checked = _read_reference_record(output / 'workflow/reference/BATCH_REFERENCE_CHECK.json', cases)
        findings = _findings(output, checked, payloads)
        record = {'schema_version': 1, 'contract_id': 'R42_DECLARED_SYNTHETIC_BOUNDARY_EXPLORATION_V1',
                  'status': _verdict(produced, checked, cases, steps), 'parameters': generated['parameters'],
                  'generator_id': generated['generator_id'], 'generated_samples': generated['generated_samples'],
                  'input_feature_counts': generated['input_feature_counts'], 'coverage_claim': generated['coverage_claim'],
                  'model_steps': produced['model_steps'], 'reference_steps': produced['reference_steps'],
                  'reference_steps_accounting': produced['reference_steps_accounting'],
                  'reference_helper_counts': produced['reference_helper_counts'],
                  'workflow_status': produced['status'], 'difference_count': checked['numerical_difference_count'],
                  'findings': findings, 'observed_source_identity': identity,
                  'claim': 'BOUNDED_SYNTHETIC_SELECTED_SOURCE_PARITY_NOT_EXHAUSTIVE_OR_VEHICLE_APPROVAL',
                  'time_semantics': 'INVOCATION_ORDER_ONLY_NOT_ELAPSED_TIME',
                  'generation_model_executions': 0, 'reference_new_public_model_executions': 0,
                  'gates': dict(GATES)}
        _publish(output, record)
        return record
    except OSError as error:
        raise ExplorationError('EXPLORATION_IO') from error
