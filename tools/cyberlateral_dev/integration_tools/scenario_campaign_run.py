"""Sequential bounded R42 campaigns; no new generator, math or vehicle binding."""

import hashlib
from pathlib import Path

from . import scenario_explore_run as exploration
from .scenario_batch_input import _read
from .scenario_campaign_evidence import CampaignError, capture_tree, validate_stages, verify_manifests
from .scenario_compare_input import REPORT_FILES, ROOT_FILES
from .scenario_explore_generate import GENERATOR_ID, _parameters, generation_record
from .scenario_output import GATES, canonical
from .scenario_report_data import CAPS, _json

ROOT = Path(__file__).resolve().parents[1]


def _need(condition):
    if not condition:
        raise CampaignError('CAMPAIGN_STAGE_RECORD')


def _source_identity() -> dict:
    names = ['integration_tools/scenario_campaign_run.py', 'integration_tools/scenario_campaign_evidence.py',
             'tools/scenario_campaign.py']
    return {'exploration': exploration._source_identity(),
            'campaign': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in names}}


def _observe_identity() -> dict:
    try:
        return _source_identity()
    except (ValueError, OSError) as error:
        raise CampaignError('CAMPAIGN_SOURCE_IDENTITY') from error


def _json_file(path):
    value = _json(_read(path))
    _need(type(value) is dict)
    return value


def _child(output: Path, produced: dict, seed: int, cases: int, steps: int, identity: dict) -> tuple[dict, dict]:
    hashes = capture_tree(output)
    verify_manifests(output, hashes)
    try:
        saved = _json_file(output / 'EXPLORATION.json')
        _need(type(produced) is dict and canonical(produced) == canonical(saved))
        expected = {'schema_version': 1, 'contract_id': 'R42_DECLARED_SYNTHETIC_BOUNDARY_EXPLORATION_V1',
                    'parameters': {'seed': seed, 'cases': cases, 'steps': steps}, 'generated_samples': cases * steps,
                    'generator_id': GENERATOR_ID, 'observed_source_identity': identity['exploration'], 'gates': GATES,
                    'generation_model_executions': 0, 'reference_new_public_model_executions': 0}
        _need(all(key in saved and canonical(saved[key]) == canonical(value) for key, value in expected.items()))
        _need(saved.get('status') in {'MATCH', 'DIFFERENT', 'ERROR'})
        _need(all(type(saved.get(key)) is int and saved[key] >= 0
                  for key in ['model_steps', 'reference_steps', 'difference_count']))
        _need(type(saved.get('findings')) is list)
        payloads = exploration.generate_cases(seed, cases, steps)
        _need(_read(output / 'GENERATION.json') == canonical(generation_record(seed, cases, steps, payloads)))
        workflow = _json_file(output / 'workflow/WORKFLOW.json')
        checked = exploration._read_reference_record(output / 'workflow/reference/BATCH_REFERENCE_CHECK.json', cases)
        _need(all(key in workflow for key in ['completed', 'rejected', 'model_steps', 'reference_steps',
                  'reference_helper_counts', 'input_count', 'reference_difference_count', 'reference_status', 'status']))
        _need(type(workflow['reference_helper_counts']) is dict)
        validate_stages(output, workflow, checked, identity['exploration'], hashes, cases, steps)
        _need(canonical(workflow.get('gates')) == canonical(GATES) == canonical(checked.get('gates')))
        _need(saved['status'] == exploration._verdict(workflow, checked, cases, steps))
        _need(all(canonical(saved[key]) == canonical(workflow[key]) for key in ['model_steps', 'reference_steps']))
        _need(saved['difference_count'] == checked['numerical_difference_count'])
        allowed = {'EXPLORATION.json', 'GENERATION.json', 'SUMMARY_KO.md', 'SHA256SUMS.txt'}
        allowed.update('workflow/' + name for name in ['WORKFLOW.json', 'VALIDATION.json', 'SUMMARY_KO.md', 'RECEIPT.json', 'SHA256SUMS.txt'])
        allowed.update('workflow/batch/' + name for name in ROOT_FILES)
        allowed.update('workflow/reference/' + name for name in ['BATCH_REFERENCE_CHECK.json', 'SUMMARY_KO.md', 'SHA256SUMS.txt'])
        findings = []
        for number, (name, raw) in enumerate(payloads.items(), 1):
            case = f'case-{number:03d}'
            digest = hashlib.sha256(raw).hexdigest()
            for prefix in ['generated/', 'workflow/inputs/', 'workflow/batch/inputs/']:
                allowed.add(prefix + name)
                _need(hashes.get(prefix + name) == digest)
            allowed.update('workflow/batch/' + case + '/' + n for n in ['producer.log', 'renderer.log'])
            allowed.update('workflow/batch/' + case + '/data/' + n for n in CAPS)
            allowed.update('workflow/batch/' + case + '/report/' + n for n in REPORT_FILES)
            row = checked['cases'][number - 1]
            if row['status'] in {'MATCH', 'DIFFERENT'}:
                _need(row['report'] == case + '/REFERENCE_CHECK.json')
            if row['report'] is not None:
                allowed.update('workflow/reference/' + case + '/' + n for n in ['REFERENCE_CHECK.json', 'SHA256SUMS.txt'])
            if row['status'] != 'MATCH':
                relative = 'reproducers/' + name
                allowed.add(relative)
                _need(hashes.get(relative) == digest)
                findings.append({'case_id': case, 'case_status': row['status'], 'reproducer': relative,
                                 'reproducer_scope': 'FULL_ORIGINAL_SEQUENCE_NOT_MINIMIZED', 'input_sha256': digest,
                                 'difference_count': row['difference_count'], 'first_difference': row['first_difference'],
                                 'error_code': row['error_code'],
                                 'reference_report': 'workflow/reference/' + row['report'] if row['report'] is not None else None})
        _need(set(hashes) == allowed and canonical(saved['findings']) == canonical(findings))
    except (ValueError, OSError, TypeError, KeyError, AttributeError) as error:
        raise CampaignError('CAMPAIGN_STAGE_RECORD') from error
    return saved, hashes


def exit_code(record: dict) -> int:
    return 0 if record['status'] == 'MATCH' else 1 if record['status'] == 'DIFFERENT' else 2


def _write(path: Path, raw: bytes) -> None:
    with path.open('xb') as stream:
        stream.write(raw)


def _publish(output: Path, record: dict, hashes: dict) -> None:
    text = ('# 여러 seed 합성 경계 검사\n\n'
            f'상태: {record["status"]}\n\n'
            f'명시한 seed 순서: {record["parameters"]["seeds"]}\n\n'
            f'보고된 합성 모델 {record["model_steps"]}steps / 독립 참조 {record["reference_steps"]}steps, '
            f'수치 차이 {record["difference_count"]}.\n\n')
    for row in record['runs']:
        text += (f'- seed {row["seed"]}: {row["status"]} / [검사 기록]({row["exploration"]}) / '
                 f'[그래프·표]({row["batch_index"]})\n')
    for finding in record['findings']:
        text += f'- seed {finding["seed"]}, {finding["case_id"]}: [전체 재현 입력]({finding["reproducer"]})\n'
    text += ('\nseed/case별 상태는 독립적이며 전체 원형 sequence를 보존합니다. 최소화·튜닝·fallback은 없습니다.\n'
             '보고된 참조 합계 외에 실패 작업이 추가 NONZERO일 수 있습니다. private receipt/log는 자동 공유하지 않습니다.\n'
             '유한 합성 선택-source parity이며 exhaustive coverage·실제 이력·물리 안전/성능의 증거가 아닙니다.\n'
             '호출 순서는 실제 시간·100Hz가 아닙니다. R_BUDGET unresolved, Static Gate FAIL, 실제r/T2/scale=null.\n'
             'F61·실제r/dt·Controller·차량 Runtime·CAN·실차 입력·활성화·후보 평가는0, F70UH/V/F71 NOT_ALLOWED.\n')
    payloads = {'CAMPAIGN.json': canonical(record), 'SUMMARY_KO.md': text.encode()}
    combined = {**hashes, **{name: hashlib.sha256(raw).hexdigest() for name, raw in payloads.items()}}
    _write(output / 'SUMMARY_KO.md', payloads['SUMMARY_KO.md'])
    _write(output / 'SHA256SUMS.txt', ''.join(value + '  ' + name + '\n' for name, value in sorted(combined.items())).encode())
    _write(output / 'CAMPAIGN.json', payloads['CAMPAIGN.json'])


def run_campaign(seeds: list[int], cases: int, steps: int, output: Path) -> dict:
    if (type(seeds) is not list or not 1 <= len(seeds) <= 4 or any(type(seed) is not int for seed in seeds)
            or len(set(seeds)) != len(seeds)):
        raise CampaignError('CAMPAIGN_PARAMETERS')
    try:
        for seed in seeds:
            _parameters(seed, cases, steps)
    except exploration.ExplorationError as error:
        raise CampaignError('CAMPAIGN_PARAMETERS') from error
    seeds = seeds.copy()
    try:
        exploration._preflight(output)
    except exploration.ExplorationError as error:
        raise CampaignError(error.code.replace('EXPLORATION_', 'CAMPAIGN_', 1)) from error
    try:
        identity = _observe_identity()
        output.mkdir(exist_ok=False)
        (output / 'runs').mkdir(exist_ok=False)
        rows, findings, snapshots = [], [], {}
        for number, seed in enumerate(seeds, 1):
            run_id = f'seed-{number:03d}'
            prefix = 'runs/' + run_id + '/'
            child = output / 'runs' / run_id
            try:
                produced = exploration.run_exploration(seed, cases, steps, child)
            except (ValueError, OSError) as error:
                raise CampaignError('CAMPAIGN_STAGE_FAILED') from error
            saved, hashes = _child(child, produced, seed, cases, steps, identity)
            snapshots[run_id] = hashes
            rows.append({'run_id': run_id, 'seed': seed, 'status': saved['status'],
                         'exploration': prefix + 'EXPLORATION.json', 'batch_index': prefix + 'workflow/batch/index.html',
                         'record_sha256': hashes['EXPLORATION.json'],
                         **{key: saved[key] for key in ['model_steps', 'reference_steps', 'difference_count']}})
            for item in saved['findings']:
                findings.append({**item, 'run_id': run_id, 'seed': seed, 'reproducer': prefix + item['reproducer'],
                                 'reference_report': prefix + item['reference_report'] if item['reference_report'] is not None else None})
        if _observe_identity() != identity:
            raise CampaignError('CAMPAIGN_SOURCE_CHANGED')
        expected = {f'runs/{run_id}/{name}': digest for run_id, hashes in snapshots.items() for name, digest in hashes.items()}
        if capture_tree(output, max_files=8192, max_bytes=512 * 1024 * 1024) != expected:
            raise CampaignError('CAMPAIGN_CHILD_CHANGED')
        counts = {status: sum(row['status'] == status for row in rows) for status in ['MATCH', 'DIFFERENT', 'ERROR']}
        status = 'ERROR' if counts['ERROR'] else 'DIFFERENT' if counts['DIFFERENT'] else 'MATCH'
        record = {'schema_version': 1, 'contract_id': 'R43_DECLARED_SYNTHETIC_SEED_CAMPAIGN_V1', 'status': status,
                  'parameters': {'seeds': seeds, 'cases': cases, 'steps': steps}, 'status_counts': counts,
                  'expected_samples': len(seeds) * cases * steps, 'runs': rows, 'findings': findings,
                  **{key: sum(row[key] for row in rows) for key in ['model_steps', 'reference_steps', 'difference_count']},
                  'reference_steps_accounting': 'SUCCESSFULLY_REPORTED_CHILD_COUNTS_FAILED_WORK_MAY_BE_NONZERO',
                  'observed_source_identity': identity, 'gates': dict(GATES),
                  'state_scope': 'INDEPENDENT_PER_SEED_AND_CASE_NO_CROSS_RUN_STATE',
                  'time_semantics': 'INVOCATION_ORDER_ONLY_NOT_ELAPSED_TIME',
                  'claim': 'BOUNDED_SYNTHETIC_SELECTED_SOURCE_PARITY_NOT_EXHAUSTIVE_OR_VEHICLE_APPROVAL'}
        _publish(output, record, expected)
        return record
    except OSError as error:
        raise CampaignError('CAMPAIGN_IO') from error
