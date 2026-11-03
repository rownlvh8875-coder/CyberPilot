"""Complete R43 V1 recorded evidence, no model/reference evaluation or origin proof."""

import hashlib
import json
import re
from pathlib import Path

from . import scenario_campaign_run as campaign
from .scenario_batch_input import _read
from .scenario_campaign_evidence import capture_tree, verify_manifests
from .scenario_compare_input import read_batch
from .scenario_output import GATES, canonical
from .scenario_report_data import IMPORTED, _json
from .scenario_validate import validate_scenario

ROOT = Path(__file__).resolve().parents[1]
MAX_FILES = 8192
MAX_BYTES = 512 * 1024 * 1024
ACCOUNTING = 'SUCCESSFUL_REPORTS_ONLY_FAILED_WORK_MAY_BE_NONZERO'


class CampaignCompareError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _need(condition):
    if not condition:
        raise CampaignCompareError('CAMPAIGN_COMPARE_RECORD')


def _inventory(value, required=()):
    _need(type(value) is dict and 1 <= len(value) <= 256 and set(required) <= value.keys())
    for name, digest in value.items():
        _need(type(name) is str and len(name) <= 512
              and re.fullmatch(r'[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*', name) is not None
              and '..' not in Path(name).parts and '.' not in Path(name).parts)
        _need(type(digest) is str and re.fullmatch('[0-9a-f]{64}', digest) is not None)


def _identity(value):
    _need(type(value) is dict and value.keys() == {'campaign', 'exploration'})
    campaign_files = {'integration_tools/scenario_campaign_run.py', 'integration_tools/scenario_campaign_evidence.py',
                      'tools/scenario_campaign.py'}
    _inventory(value['campaign'], campaign_files)
    _need(value['campaign'].keys() == campaign_files)
    explore = value['exploration']
    _need(type(explore) is dict and explore.keys() == {'workflow', 'reference', 'exploration'})
    _inventory(explore['workflow'], ['tools/scenario.py', 'tools/scenario_batch.py', 'tools/scenario_report.py',
                                   'tools/scenario_workflow.py', 'integration_tools/scenario_batch_run.py'])
    explore_files = {'integration_tools/scenario_explore_generate.py', 'integration_tools/scenario_explore_run.py',
                     'tools/scenario_explore.py'}
    _inventory(explore['exploration'], explore_files)
    _need(explore['exploration'].keys() == explore_files)
    checked = explore['reference']
    _need(type(checked) is dict and checked.keys() == {'reference', 'batch_checker_source_hashes'})
    files = campaign.exploration.workflow.reference.SOURCE_FILES
    _inventory(checked['batch_checker_source_hashes'], files)
    _need(checked['batch_checker_source_hashes'].keys() == set(files))
    reference = checked['reference']
    _need(type(reference) is dict and reference.keys() == {'imported', 'observed_source_hashes'})
    _need(canonical(reference['imported']) == canonical(IMPORTED))
    imported = json.loads(_read(ROOT / 'IMPORTED_ARTIFACT.json'))['imported_files']
    names = set(imported) | set(campaign.exploration.workflow.reference.reference.OBSERVED)
    _inventory(reference['observed_source_hashes'], names)
    _need(reference['observed_source_hashes'].keys() == names)


def _record(path):
    value = _json(_read(path))
    _need(type(value) is dict)
    return value


def _workflow_contract(child, record, generated, workflow):
    count = generated['parameters']['cases']
    expected = {'schema_version': 1, 'contract_id': 'F70UGZ_R40_DECLARED_SYNTHETIC_WORKFLOW_V1',
                'status': {'MATCH': 'VERIFIED', 'DIFFERENT': 'REFERENCE_DIFFERENT', 'ERROR': 'ERROR'}[record['status']],
                'input_count': count, 'completed': count, 'rejected': 0,
                'validation_report': 'VALIDATION.json', 'batch_record': 'batch/BATCH.json', 'batch_index': 'batch/index.html',
                'reference_report': 'reference/BATCH_REFERENCE_CHECK.json', 'regression_report': None,
                'reference_status': record['status'], 'reference_difference_count': record['difference_count'],
                'regression_status': None, 'regression_difference_count': None,
                'model_steps': record['model_steps'], 'reference_steps': record['reference_steps'],
                'reference_helper_counts': record['reference_helper_counts'], 'reference_steps_accounting': ACCOUNTING,
                'validation_new_model_executions': 0, 'renderer_new_model_executions': 0,
                'reference_new_public_model_executions': 0, 'regression_new_model_executions': 0,
                'batch_portable_manifest_sha256': hashlib.sha256(_read(child / 'workflow/batch/PORTABLE_SHA256SUMS.txt')).hexdigest(),
                'baseline_portable_manifest_sha256': None,
                'observed_dev_source_hashes': record['observed_source_identity']['workflow'], 'gates': dict(GATES),
                'claim': 'BOUNDED_DECLARED_SYNTHETIC_SOURCE_PARITY_NOT_GENERIC_ORACLE_OR_VEHICLE_APPROVAL',
                'input_observation': 'OWNED_BYTES_COOPERATIVE_NOT_ATOMIC_OR_ORIGIN_AUTHENTICATION',
                'time_semantics': 'INVOCATION_ORDER_ONLY_NOT_ELAPSED_TIME', 'state_scope': 'INDEPENDENT_PER_FILE_NO_CROSS_FILE_STATE',
                'full_results_scope': 'PRIVATE_RECEIPTS_AND_RAW_SYNTHETIC_INPUTS_NOT_AUTOMATICALLY_SHAREABLE'}
    _need(canonical(workflow) == canonical(expected))
    validation = []
    for number in range(1, count + 1):
        case = f'case-{number:03d}'
        relative = f'inputs/{case}.json'
        checked = validate_scenario(child / 'workflow' / relative)
        _need(checked['accepted'] is True)
        validation.append({'case_id': case, 'snapshot': relative, 'validation': checked})
    expected_validation = {'schema_version': 1, 'contract_id': 'F70UGZ_R40_OWNED_VALIDATION_V1',
                           'cases': validation, 'model_executions': 0, 'gates': dict(GATES)}
    _need(canonical(_record(child / 'workflow/VALIDATION.json')) == canonical(expected_validation))


def _child_contract(child: Path, record: dict) -> None:
    generated = _record(child / 'GENERATION.json')
    workflow = _record(child / 'workflow/WORKFLOW.json')
    _workflow_contract(child, record, generated, workflow)
    _need(workflow['reference_steps_accounting'] == ACCOUNTING)
    expected = {'schema_version': 1, 'contract_id': 'R42_DECLARED_SYNTHETIC_BOUNDARY_EXPLORATION_V1',
                'status': record['status'], 'parameters': generated['parameters'],
                'generator_id': generated['generator_id'], 'generated_samples': generated['generated_samples'],
                'input_feature_counts': generated['input_feature_counts'], 'coverage_claim': generated['coverage_claim'],
                'model_steps': workflow['model_steps'], 'reference_steps': workflow['reference_steps'],
                'reference_steps_accounting': ACCOUNTING, 'reference_helper_counts': workflow['reference_helper_counts'],
                'workflow_status': workflow['status'], 'difference_count': workflow['reference_difference_count'],
                'findings': record['findings'], 'observed_source_identity': record['observed_source_identity'],
                'claim': 'BOUNDED_SYNTHETIC_SELECTED_SOURCE_PARITY_NOT_EXHAUSTIVE_OR_VEHICLE_APPROVAL',
                'time_semantics': 'INVOCATION_ORDER_ONLY_NOT_ELAPSED_TIME', 'generation_model_executions': 0,
                'reference_new_public_model_executions': 0, 'gates': dict(GATES)}
    _need(canonical(record) == canonical(expected))


def _reference_reports(child, count):
    checked = _record(child / 'workflow/reference/BATCH_REFERENCE_CHECK.json')
    result = {}
    fields = {'schema_version', 'contract_id', 'status', 'scenario_id', 'claim', 'input_source_hashes',
              'reference_identity', 'reference_expected_sha256', 'reference_steps', 'reference_helper_counts',
              'reference_forbidden_modules_loaded', 'reference_runtime', 'initial_history', 'exactness',
              'time_semantics', 'difference_count', 'detail_limit', 'details_truncated', 'first_difference',
              'differences', 'new_model_executions', 'gates'}
    _need(len(checked['cases']) == count)
    for number, row in enumerate(checked['cases'], 1):
        case = f'case-{number:03d}'
        _need(row['case_id'] == case and row['report'] in {None, case + '/REFERENCE_CHECK.json'})
        if row['report'] is None:
            result[case] = None
        else:
            report = _record(child / 'workflow/reference' / case / 'REFERENCE_CHECK.json')
            _need(report.keys() == fields)
            _need(report['claim'] == 'BOUNDED_DECLARED_SYNTHETIC_SELECTED_SOURCE_PARITY_NOT_WHOLE_CONTROLLER_VEHICLE_OR_ORIGIN_APPROVAL')
            _need(report['initial_history'] == 'EXPLICIT_SYNTHETIC_DECLARATION_NOT_AUTHENTICATED')
            # Binding hashes and producer identity are validated separately; retained
            # findings/expected digest are recorded semantics, not a new oracle run.
            result[case] = {key: value for key, value in report.items()
                            if key not in {'input_source_hashes', 'reference_identity', 'reference_runtime'}}
    return result


def read_campaign(path: Path) -> dict:
    try:
        str(path.absolute()).encode('utf-8', errors='strict')
        if path.is_symlink() or any(parent.is_symlink() for parent in path.absolute().parents):
            raise CampaignCompareError('CAMPAIGN_COMPARE_INPUT')
        hashes = capture_tree(path, max_files=MAX_FILES, max_bytes=MAX_BYTES)
        verify_manifests(path, hashes)
    except (ValueError, OSError, RuntimeError) as error:
        raise CampaignCompareError('CAMPAIGN_COMPARE_INPUT') from error
    try:
        root = _record(path / 'CAMPAIGN.json')
        params = root['parameters']
        _need(type(params) is dict and params.keys() == {'seeds', 'cases', 'steps'})
        seeds, cases, steps = params['seeds'], params['cases'], params['steps']
        _need(type(seeds) is list and 1 <= len(seeds) <= 4 and all(type(seed) is int for seed in seeds))
        _need(len(set(seeds)) == len(seeds))
        for seed in seeds:
            campaign._parameters(seed, cases, steps)
        identity = root['observed_source_identity']
        _identity(identity)
        runs, rows, findings = [], [], []
        expected_hashes = {name: hashes[name] for name in ['CAMPAIGN.json', 'SUMMARY_KO.md', 'SHA256SUMS.txt']}
        for number, seed in enumerate(seeds, 1):
            run_id = f'seed-{number:03d}'
            prefix = 'runs/' + run_id + '/'
            child = path / 'runs' / run_id
            saved, observed = campaign._child(child, _record(child / 'EXPLORATION.json'), seed, cases, steps, identity)
            _child_contract(child, saved)
            batch = read_batch(child / 'workflow/batch')
            _need(batch['root_manifest_sha256'] == observed['workflow/batch/SHA256SUMS.txt'])
            _need(batch['portable_manifest_sha256'] == observed['workflow/batch/PORTABLE_SHA256SUMS.txt'])
            expected_hashes.update({prefix + name: digest for name, digest in observed.items()})
            rows.append({'run_id': run_id, 'seed': seed, 'status': saved['status'],
                         'exploration': prefix + 'EXPLORATION.json', 'batch_index': prefix + 'workflow/batch/index.html',
                         'record_sha256': observed['EXPLORATION.json'],
                         **{key: saved[key] for key in ['model_steps', 'reference_steps', 'difference_count']}})
            for item in saved['findings']:
                findings.append({**item, 'run_id': run_id, 'seed': seed, 'reproducer': prefix + item['reproducer'],
                                 'reference_report': prefix + item['reference_report'] if item['reference_report'] is not None else None})
            runs.append({'record': saved, 'batch': batch, 'reference_reports': _reference_reports(child, cases)})
        counts = {status: sum(row['status'] == status for row in rows) for status in ['MATCH', 'DIFFERENT', 'ERROR']}
        status = 'ERROR' if counts['ERROR'] else 'DIFFERENT' if counts['DIFFERENT'] else 'MATCH'
        expected = {'schema_version': 1, 'contract_id': 'R43_DECLARED_SYNTHETIC_SEED_CAMPAIGN_V1', 'status': status,
                    'parameters': params, 'status_counts': counts, 'expected_samples': len(seeds) * cases * steps,
                    'runs': rows, 'findings': findings,
                    **{key: sum(row[key] for row in rows) for key in ['model_steps', 'reference_steps', 'difference_count']},
                    'reference_steps_accounting': 'SUCCESSFULLY_REPORTED_CHILD_COUNTS_FAILED_WORK_MAY_BE_NONZERO',
                    'observed_source_identity': identity, 'gates': dict(GATES),
                    'state_scope': 'INDEPENDENT_PER_SEED_AND_CASE_NO_CROSS_RUN_STATE',
                    'time_semantics': 'INVOCATION_ORDER_ONLY_NOT_ELAPSED_TIME',
                    'claim': 'BOUNDED_SYNTHETIC_SELECTED_SOURCE_PARITY_NOT_EXHAUSTIVE_OR_VEHICLE_APPROVAL'}
        _need(canonical(root) == canonical(expected) and hashes == expected_hashes)
        return {'record': root, 'runs': runs, 'hashes': hashes}
    except (ValueError, OSError, TypeError, KeyError, IndexError, AttributeError) as error:
        raise CampaignCompareError('CAMPAIGN_COMPARE_RECORD') from error
