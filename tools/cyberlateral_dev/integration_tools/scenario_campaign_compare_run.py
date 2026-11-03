"""Read-only R43/R34 composition with source-aware verdict and exclusive publication."""

import hashlib
import os
import platform
import sys
import tempfile
import warnings
from itertools import zip_longest
from pathlib import Path

from . import scenario_campaign_run as campaign
from .scenario_campaign_compare_input import MAX_BYTES, MAX_FILES, CampaignCompareError, read_campaign
from .scenario_campaign_evidence import capture_tree
from .scenario_compare_data import DETAIL_LIMIT, MISSING, _changes, compare_batches
from .scenario_compare_input import CompareError, _manifest
from .scenario_compare_run import FORBIDDEN, _preflight
from .scenario_output import GATES, canonical

ROOT = Path(__file__).resolve().parents[1]


def _source_hashes() -> dict:
    try:
        result = campaign.exploration.workflow.batch._source_hashes()
        for name in ['IMPORTED_ARTIFACT.json', 'tools/scenario_campaign_compare.py']:
            result[name] = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
        return result
    except (ValueError, OSError) as error:
        raise CampaignCompareError('CAMPAIGN_COMPARE_SOURCE_IDENTITY') from error


def _metadata(run):
    return {key: run['record'][key] for key in ['status', 'model_steps', 'reference_steps', 'difference_count', 'findings']}


def _alerts(old, new, status):
    return [{'side': side, 'run_id': f'seed-{number:03d}', 'seed': run['record']['parameters']['seed'],
             'status': status, 'findings': run['record']['findings']}
            for side, snapshot in [('baseline', old), ('candidate', new)]
            for number, run in enumerate(snapshot['runs'], 1) if run['record']['status'] == status]


def _compare(old, new):
    details, rows, reports = [], [], {}
    total = samples = 0
    identities_match = canonical(old['record']['observed_source_identity']) == canonical(new['record']['observed_source_identity'])

    def add(changes, context):
        nonlocal total
        for change in changes:
            total += 1
            if len(details) < DETAIL_LIMIT:
                details.append({**context, **change})

    empty = {'run_id': None, 'baseline_seed': None, 'candidate_seed': None, 'case_id': None, 'sample_index': None}
    add(_changes(old['record']['parameters'], new['record']['parameters'], 'parameters'), empty)
    for number, (before, after) in enumerate(zip_longest(old['runs'], new['runs']), 1):
        run_id = f'seed-{number:03d}'
        context = {**empty, 'run_id': run_id,
                   'baseline_seed': before['record']['parameters']['seed'] if before else None,
                   'candidate_seed': after['record']['parameters']['seed'] if after else None}
        initial = total
        path = None
        if before is None or after is None:
            classification = 'RUN_ADDED' if before is None else 'RUN_REMOVED'
            add(_changes(_metadata(before) if before else MISSING, _metadata(after) if after else MISSING, 'run'), context)
            identities_match = False
        else:
            classification = 'RUN_COMPARED'
            add(_changes(_metadata(before), _metadata(after), 'source'), context)
            add(_changes(before['reference_reports'], after['reference_reports'], 'reference'), context)
            checked = compare_batches(before['batch'], after['batch'])
            total += checked['difference_count']
            samples += checked['compared_sample_count']
            for detail in checked['differences']:
                if len(details) < DETAIL_LIMIT:
                    details.append({**context, **detail, 'field': 'batch.' + detail['field']})
            identities_match &= checked['all_observed_producer_identities_match']
            path = f'comparisons/{run_id}/COMPARE.json'
            reports[path] = canonical(checked)
        rows.append({'run_id': run_id, 'baseline_seed': context['baseline_seed'], 'candidate_seed': context['candidate_seed'],
                     'baseline_status': before['record']['status'] if before else None,
                     'candidate_status': after['record']['status'] if after else None,
                     'classification': classification, 'comparison_report': path,
                     'difference_count': total - initial, 'regression_status': 'DIFFERENT' if total > initial else 'MATCH'})
    errors, different = _alerts(old, new, 'ERROR'), _alerts(old, new, 'DIFFERENT')
    regression = 'DIFFERENT' if total else 'MATCH'
    status = 'ERROR' if errors else 'DIFFERENT' if different or total else 'MATCH'
    record = {'schema_version': 1, 'contract_id': 'R44_SAVED_SEED_CAMPAIGN_COMPARISON_V1',
              'status': status, 'regression_status': regression,
              'baseline_campaign_status': old['record']['status'], 'candidate_campaign_status': new['record']['status'],
              'baseline_parameters': old['record']['parameters'], 'candidate_parameters': new['record']['parameters'],
              'baseline_campaign_sha256': old['hashes']['CAMPAIGN.json'], 'candidate_campaign_sha256': new['hashes']['CAMPAIGN.json'],
              'baseline_producer_identity_sha256': hashlib.sha256(canonical(old['record']['observed_source_identity'])).hexdigest(),
              'candidate_producer_identity_sha256': hashlib.sha256(canonical(new['record']['observed_source_identity'])).hexdigest(),
              'all_observed_producer_identities_match': identities_match,
              'source_error_runs': errors, 'source_difference_runs': different, 'runs': rows,
              'compared_sample_count': samples, 'difference_count': total, 'detail_limit': DETAIL_LIMIT,
              'details_truncated': total > len(details), 'first_difference': details[0] if details else None,
              'differences': details, 'new_model_executions': 0, 'new_reference_executions': 0,
              'alignment': 'EXPLICIT_RUN_AND_CASE_POSITION_NOT_SEED_SORTING',
              'comparison_claim': 'RECORDED_VALUES_AND_SOURCE_VERDICTS_NOT_NEW_NUMERICAL_OR_ORIGIN_APPROVAL',
              'exactness': 'TYPED_CANONICAL_AND_HEX_NO_TOLERANCE', 'time_semantics': 'INVOCATION_ORDER_ONLY_NOT_ELAPSED_TIME',
              'gates': dict(GATES)}
    return record, reports


def exit_code(record: dict) -> int:
    return 0 if record['status'] == 'MATCH' else 1 if record['status'] == 'DIFFERENT' else 2


def _summary(record):
    text = ('# 저장된 여러 seed 캠페인 비교\n\n'
            f'전체 판정: {record["status"]}. 저장 기록 회귀: {record["regression_status"]}.\n\n'
            f'원본 캠페인: {record["baseline_campaign_status"]} → {record["candidate_campaign_status"]}.\n\n'
            f'조건: {record["baseline_parameters"]} → {record["candidate_parameters"]}.\n\n'
            f'같은 입력의 비교 sample: {record["compared_sample_count"]}. 차이: {record["difference_count"]}. '
            f'상세 보존: {len(record["differences"])}; 잘림: {record["details_truncated"]}.\n\n'
            f'producer identity 일치: {record["all_observed_producer_identities_match"]}. 새 모델/참조 실행:0/0.\n\n')
    for row in record['runs']:
        label = f'{row["run_id"]}, seed {row["baseline_seed"]} → {row["candidate_seed"]}: {row["classification"]}'
        text += f'- [{label}]({row["comparison_report"]})\n' if row['comparison_report'] else f'- {label}\n'
    text += ('\n동일 ERROR/DIFFERENT 기록도 전체 MATCH로 승격하지 않습니다. 원본의 수치 판정과 새 저장값 회귀는 별개입니다.\n'
             '명시한 위치로 정렬하며 seed/scenario 이름으로 재배열하지 않습니다. identity 변화는 값 차이와 별도입니다.\n'
             '입력 bytes·참조 기록의 일관성 검사이며 원본 출처 인증이나 새로운 독립 수치 검증은 아닙니다.\n'
             'R43 V1 입력 생성 규칙은 메모리에서 재검산하지만 모델/참조 worker는 실행하지 않습니다.\n'
             'private receipt/log/전체 Manifest 동일성·원자적 OS snapshot·실제 시간/100Hz는 보장하지 않습니다.\n'
             'R_BUDGET unresolved, Static Gate FAIL, 실제r/T2/scale=null. Candidate/Runtime NO_GO.\n'
             'F61·실제r/dt·Controller·차량 Runtime·CAN·실차 입력/활성화·후보 평가는0, F70UH/V/F71 NOT_ALLOWED.\n')
    return text.encode()


def _write(path, raw):
    with path.open('xb') as stream:
        stream.write(raw)


def _publish(output, record, reports, receipt, check):
    marker = canonical(record)
    files = {**reports, 'SUMMARY_KO.md': _summary(record), 'RECEIPT.json': canonical(receipt)}
    for name, raw in reports.items():
        files[str(Path(name).parent / 'SHA256SUMS.txt')] = _manifest({'COMPARE.json': raw})
    files['SHA256SUMS.txt'] = _manifest({**files, 'CAMPAIGN_COMPARE.json': marker})
    committed = False
    try:
        output.mkdir(exist_ok=False)
        for name, raw in files.items():
            target = output / name
            target.parent.mkdir(parents=True, exist_ok=True)
            _write(target, raw)
        # A failed marker write must not create even a partial completion file.
        # Same-parent temporary directory ensures an exclusive same-filesystem link.
        with tempfile.TemporaryDirectory(prefix='cyberlateral-r44-publish-', dir=output.parent) as scratch:
            pending = Path(scratch) / 'pending_record'
            _write(pending, marker)
            check()
            os.link(pending, output / 'CAMPAIGN_COMPARE.json')
            committed = True
    except OSError as error:
        if not committed:
            raise CampaignCompareError('CAMPAIGN_COMPARE_PUBLICATION_FAILED') from error
        warnings.warn('CAMPAIGN_COMPARE_CLEANUP_FAILED_AFTER_COMMIT', RuntimeWarning, stacklevel=2)


def run_campaign_comparison(baseline: Path, candidate: Path, output: Path) -> dict:
    try:
        _preflight(baseline, candidate, output)
        if any(parent.is_symlink() for parent in output.absolute().parents):
            raise CompareError('COMPARE_OUTPUT_LOCATION')
    except CompareError as error:
        raise CampaignCompareError(error.code.replace('COMPARE_', 'CAMPAIGN_COMPARE_', 1)) from error
    except CampaignCompareError:
        raise
    except (OSError, ValueError) as error:
        raise CampaignCompareError('CAMPAIGN_COMPARE_IO') from error
    identity = _source_hashes()
    old, new = read_campaign(baseline), read_campaign(candidate)
    record, reports = _compare(old, new)

    def unchanged():
        for source, observed in [(baseline, old), (candidate, new)]:
            try:
                current = capture_tree(source, max_files=MAX_FILES, max_bytes=MAX_BYTES)
            except (ValueError, OSError) as error:
                raise CampaignCompareError('CAMPAIGN_COMPARE_INPUT_CHANGED') from error
            if current != observed['hashes']:
                raise CampaignCompareError('CAMPAIGN_COMPARE_INPUT_CHANGED')
        if _source_hashes() != identity:
            raise CampaignCompareError('CAMPAIGN_COMPARE_SOURCE_CHANGED')

    unchanged()
    try:
        receipt = {'schema_version': 1, 'baseline_directory': str(baseline.absolute()),
                   'candidate_directory': str(candidate.absolute()), 'output_directory': str(output.absolute()),
                   'source_root': str(ROOT), 'comparator_source_hashes': identity,
                   'baseline_root_manifest_sha256': old['hashes']['SHA256SUMS.txt'],
                   'candidate_root_manifest_sha256': new['hashes']['SHA256SUMS.txt'],
                   'python_executable': sys.executable, 'python_version': platform.python_version(),
                   'python_executable_sha256': hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest(),
                   'forbidden_modules_loaded': sorted({n.split('.')[0] for n in sys.modules} & FORBIDDEN),
                   'new_model_executions': 0, 'new_reference_executions': 0,
                   'cache_policy': 'COLD_PRIVATE_PREFIX_IN_CLI_ONLY_NOT_IN_PROCESS_API',
                   'scope': 'COOPERATIVE_BEFORE_AFTER_CONSISTENCY_NOT_OS_SNAPSHOT_OR_ORIGIN_AUTHENTICATION'}
        _publish(output, record, reports, receipt, unchanged)
    except OSError as error:
        raise CampaignCompareError('CAMPAIGN_COMPARE_IO') from error
    return record
