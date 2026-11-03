"""Known R44/R34 saved-record consistency, not original comparison regeneration."""

import re
from collections import Counter

from .scenario_compare_data import _changes
from .scenario_output import GATES, canonical

TIME = 'INVOCATION_ORDER_ONLY_NOT_ELAPSED_TIME'
PARENT_FIXED = {
    'schema_version': 1, 'contract_id': 'R44_SAVED_SEED_CAMPAIGN_COMPARISON_V1',
    'alignment': 'EXPLICIT_RUN_AND_CASE_POSITION_NOT_SEED_SORTING',
    'comparison_claim': 'RECORDED_VALUES_AND_SOURCE_VERDICTS_NOT_NEW_NUMERICAL_OR_ORIGIN_APPROVAL',
    'exactness': 'TYPED_CANONICAL_AND_HEX_NO_TOLERANCE', 'time_semantics': TIME,
    'detail_limit': 256, 'new_model_executions': 0, 'new_reference_executions': 0, 'gates': GATES,
}
CHILD_FIXED = {
    'schema_version': 1, 'contract_id': 'F70UGZ_R34_SAVED_BATCH_COMPARISON_V1',
    'comparison_claim': 'RECORDED_VALUES_ONLY_NOT_ORIGIN_NUMERICAL_OR_VEHICLE_APPROVAL',
    'alignment': 'EXPLICIT_ARGUMENT_POSITION_NOT_SCENARIO_ID', 'exactness': 'TYPED_CANONICAL_NO_TOLERANCE',
    'time_semantics': TIME, 'detail_limit': 256, 'new_model_executions': 0, 'gates': GATES,
}
DETAIL = {'field', 'before', 'after', 'before_present', 'after_present'}
CONTEXT = {'run_id', 'baseline_seed', 'candidate_seed', 'case_id', 'sample_index'}
RUN_KEYS = {'run_id', 'baseline_seed', 'candidate_seed', 'baseline_status', 'candidate_status',
            'classification', 'comparison_report', 'difference_count', 'regression_status'}
CASE_KEYS = {'case_id', 'classification', 'difference_count', 'first_difference', 'producer_identity_changed',
             'baseline_identity_sha256', 'candidate_identity_sha256'}


class CampaignReportError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def need(ok, code='CAMPAIGN_REPORT_SCHEMA'):
    if not ok:
        raise CampaignReportError(code)


def keys(value, expected):
    need(type(value) is dict and value.keys() == set(expected))


def same(value, expected):
    need(canonical(value) == canonical(expected), 'CAMPAIGN_REPORT_CONSISTENCY')


def integer(value, low=0, high=2 ** 63 - 1):
    need(type(value) is int and low <= value <= high)


def digest(value):
    need(type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None)


def _fixed(record, fixed, extra):
    keys(record, fixed.keys() | set(extra))
    for name, expected in fixed.items():
        same(record[name], expected)


def _parameters(value):
    keys(value, {'seeds', 'cases', 'steps'})
    seeds = value['seeds']
    need(type(seeds) is list and 1 <= len(seeds) <= 4)
    for seed in seeds:
        integer(seed, 0, 2 ** 32 - 1)
    need(len(set(seeds)) == len(seeds))
    integer(value['cases'], 1, 16)
    integer(value['steps'], 16, 256)


def _detail(value, context):
    keys(value, DETAIL | context)
    need(type(value['field']) is str and 0 < len(value['field']) <= 4096)
    for side in ['before', 'after']:
        need(type(value[side + '_present']) is bool)
        need(value[side + '_present'] or value[side] is None)
    if 'sample_index' in context and value['sample_index'] is not None:
        integer(value['sample_index'], 0, 4095)


def _details(record, context):
    integer(record['difference_count'])
    integer(record['compared_sample_count'], 0, 16384)
    details, count = record['differences'], record['difference_count']
    need(type(details) is list and len(details) == min(count, 256))
    same(record['details_truncated'], count > 256)
    same(record['first_difference'], details[0] if details else None)
    for detail in details:
        _detail(detail, context)


def _child(record, old, new):
    _fixed(record, CHILD_FIXED, {
        'status', 'baseline_portable_manifest_sha256', 'candidate_portable_manifest_sha256',
        'baseline_batch_producer_identity_sha256', 'candidate_batch_producer_identity_sha256',
        'batch_producer_identity_changed', 'compared_sample_count', 'difference_count', 'details_truncated',
        'first_difference', 'differences', 'cases', 'all_observed_producer_identities_match',
    })
    for name in ['baseline_portable_manifest_sha256', 'candidate_portable_manifest_sha256',
                 'baseline_batch_producer_identity_sha256', 'candidate_batch_producer_identity_sha256']:
        digest(record[name])
    changed = record['baseline_batch_producer_identity_sha256'] != record['candidate_batch_producer_identity_sha256']
    same(record['batch_producer_identity_changed'], changed)
    _details(record, {'case_id', 'sample_index'})
    need(record['compared_sample_count'] <= 4096)
    same(record['status'], 'DIFFERENT' if record['difference_count'] else 'MATCH')
    cases = record['cases']
    need(type(cases) is list and len(cases) == max(old['cases'], new['cases']))
    total, first, identities, compared = 0, None, not changed, 0
    order = []
    for number, case in enumerate(cases, 1):
        keys(case, CASE_KEYS)
        case_id = f'case-{number:03d}'
        same(case['case_id'], case_id)
        added, removed = number > old['cases'], number > new['cases']
        for side, absent in [('baseline', added), ('candidate', removed)]:
            value = case[side + '_identity_sha256']
            if absent:
                same(value, None)
            else:
                digest(value)
        identity_changed = case['baseline_identity_sha256'] != case['candidate_identity_sha256']
        same(case['producer_identity_changed'], identity_changed)
        identities &= not identity_changed
        integer(case['difference_count'])
        count = case['difference_count']
        classification = case['classification']
        if added or removed:
            same(classification, 'CASE_ADDED' if added else 'CASE_REMOVED')
            same(count, 1)
        else:
            need(type(classification) is str and classification in {'MATCH', 'RESULT_CHANGED', 'INPUT_CHANGED'})
            need((classification == 'MATCH') == (count == 0))
            if classification != 'INPUT_CHANGED':
                compared += max(old['steps'], new['steps'])
        detail = case['first_difference']
        if count:
            _detail(detail, {'case_id', 'sample_index'})
            same(detail['case_id'], case_id)
            first = first or detail
        else:
            same(detail, None)
        total += count
        order.extend([case_id] * min(count, 256))
        retained = [d for d in record['differences'] if d['case_id'] == case_id]
        if retained:
            same(retained[0], detail)
        need(len(retained) <= count)
        if not record['details_truncated']:
            same(len(retained), count)
    same(total, record['difference_count'])
    same(compared, record['compared_sample_count'])
    same(first, record['first_difference'])
    same([d['case_id'] for d in record['differences']], order[:256])
    same(record['all_observed_producer_identities_match'], identities)


def _findings(findings, status, parameters):
    need(type(findings) is list and 1 <= len(findings) <= parameters['cases'])
    positions = []
    for finding in findings:
        keys(finding, {'case_id', 'case_status', 'difference_count', 'error_code', 'first_difference',
                       'input_sha256', 'reference_report', 'reproducer', 'reproducer_scope'})
        case_id = finding['case_id']
        need(type(case_id) is str and re.fullmatch('case-00[1-9]|case-01[0-6]', case_id) is not None)
        number = int(case_id.split('-')[1])
        need(number <= parameters['cases'])
        positions.append(number)
        need(type(finding['case_status']) is str and finding['case_status'] in {'DIFFERENT', 'ERROR'})
        digest(finding['input_sha256'])
        same(finding['reproducer'], f'reproducers/{case_id}.json')
        same(finding['reproducer_scope'], 'FULL_ORIGINAL_SEQUENCE_NOT_MINIMIZED')
        if finding['case_status'] == 'ERROR':
            need(type(finding['error_code']) is str and 0 < len(finding['error_code']) <= 4096)
            for name in ['difference_count', 'first_difference', 'reference_report']:
                same(finding[name], None)
        else:
            integer(finding['difference_count'], 1)
            _detail(finding['first_difference'], set())
            same(finding['error_code'], None)
            same(finding['reference_report'], f'workflow/reference/{case_id}/REFERENCE_CHECK.json')
    same(positions, sorted(set(positions)))
    same(status, 'ERROR' if any(f['case_status'] == 'ERROR' for f in findings) else 'DIFFERENT')


def validate_comparison(record: dict, children: dict) -> None:
    _fixed(record, PARENT_FIXED, {
        'status', 'regression_status', 'baseline_campaign_status', 'candidate_campaign_status',
        'baseline_parameters', 'candidate_parameters', 'baseline_campaign_sha256', 'candidate_campaign_sha256',
        'baseline_producer_identity_sha256', 'candidate_producer_identity_sha256',
        'all_observed_producer_identities_match', 'source_error_runs', 'source_difference_runs', 'runs',
        'compared_sample_count', 'difference_count', 'details_truncated', 'first_difference', 'differences',
    })
    old, new = record['baseline_parameters'], record['candidate_parameters']
    _parameters(old)
    _parameters(new)
    for side in ['baseline', 'candidate']:
        for suffix in ['campaign_sha256', 'producer_identity_sha256']:
            digest(record[side + '_' + suffix])
    _details(record, CONTEXT)
    runs = record['runs']
    need(type(runs) is list and len(runs) == max(len(old['seeds']), len(new['seeds'])))
    need(type(children) is dict)
    expected_children, expected_alerts = set(), {'ERROR': [], 'DIFFERENT': []}
    samples, identities = 0, record['baseline_producer_identity_sha256'] == record['candidate_producer_identity_sha256']
    parameter_details = list(_changes(old, new, 'parameters'))
    empty = dict.fromkeys(CONTEXT)
    prefix = [{**empty, **detail} for detail in parameter_details]
    same(record['differences'][:len(prefix)], prefix)
    total = len(prefix)
    by_run = Counter(d['run_id'] for d in record['differences'])
    for number, row in enumerate(runs, 1):
        keys(row, RUN_KEYS)
        run_id = f'seed-{number:03d}'
        same(row['run_id'], run_id)
        for side, params in [('baseline', old), ('candidate', new)]:
            seed = params['seeds'][number - 1] if number <= len(params['seeds']) else None
            same(row[side + '_seed'], seed)
            state = row[side + '_status']
            need(type(state) is str and state in {'MATCH', 'DIFFERENT', 'ERROR'} if seed is not None else state is None)
        paired = row['baseline_seed'] is not None and row['candidate_seed'] is not None
        same(row['classification'], 'RUN_COMPARED' if paired else 'RUN_ADDED' if row['baseline_seed'] is None else 'RUN_REMOVED')
        integer(row['difference_count'])
        total += row['difference_count']
        same(row['regression_status'], 'DIFFERENT' if row['difference_count'] else 'MATCH')
        if paired:
            same(row['comparison_report'], f'comparisons/{run_id}/COMPARE.json')
            expected_children.add(run_id)
            need(run_id in children)
            child = children[run_id]
            _child(child, old, new)
            samples += child['compared_sample_count']
            need(row['difference_count'] >= child['difference_count'])
            identities &= child['all_observed_producer_identities_match']
            root_details = [d for d in record['differences'] if d['run_id'] == run_id and d['field'].startswith('batch.')]
            mapped = [{**d, 'run_id': run_id, 'baseline_seed': row['baseline_seed'], 'candidate_seed': row['candidate_seed'],
                       'field': 'batch.' + d['field']} for d in child['differences']]
            same(root_details, mapped[:len(root_details)])
            if not record['details_truncated']:
                same(root_details, mapped)
        else:
            same(row['comparison_report'], None)
            need(row['difference_count'] == 1)
            identities = False
        need(by_run[run_id] <= row['difference_count'])
        if not record['details_truncated']:
            same(by_run[run_id], row['difference_count'])
    allowed_runs = [r['run_id'] for r in runs]
    order = []
    for detail in record['differences'][len(prefix):]:
        need(type(detail['run_id']) is str and detail['run_id'] in allowed_runs)
        row = runs[allowed_runs.index(detail['run_id'])]
        for side in ['baseline', 'candidate']:
            same(detail[side + '_seed'], row[side + '_seed'])
        if detail['case_id'] is not None:
            need(detail['run_id'] in children and detail['case_id'] in [c['case_id'] for c in children[detail['run_id']]['cases']])
        order.append(allowed_runs.index(detail['run_id']))
    same(order, sorted(order))
    need(children.keys() == expected_children)
    for side in ['baseline', 'candidate']:
        states = [r[side + '_status'] for r in runs if r[side + '_status'] is not None]
        aggregate = 'ERROR' if 'ERROR' in states else 'DIFFERENT' if 'DIFFERENT' in states else 'MATCH'
        same(record[side + '_campaign_status'], aggregate)
        for row in runs:
            state = row[side + '_status']
            if state in expected_alerts:
                expected_alerts[state].append((side, row['run_id'], row[side + '_seed']))
    for state, name in [('ERROR', 'source_error_runs'), ('DIFFERENT', 'source_difference_runs')]:
        alerts = record[name]
        need(type(alerts) is list and len(alerts) == len(expected_alerts[state]))
        for alert, (side, run_id, seed) in zip(alerts, expected_alerts[state], strict=True):
            keys(alert, {'side', 'run_id', 'seed', 'status', 'findings'})
            for key, expected in [('side', side), ('run_id', run_id), ('seed', seed), ('status', state)]:
                same(alert[key], expected)
            _findings(alert['findings'], state, old if side == 'baseline' else new)
    same(record['compared_sample_count'], samples)
    same(record['difference_count'], total)
    same(record['all_observed_producer_identities_match'], identities)
    same(record['regression_status'], 'DIFFERENT' if total else 'MATCH')
    same(record['status'], 'ERROR' if expected_alerts['ERROR'] else 'DIFFERENT' if expected_alerts['DIFFERENT'] or total else 'MATCH')
