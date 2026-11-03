"""Complete R43 V1 recorded evidence, no model/reference evaluation or origin proof."""

import json
import re
from pathlib import Path

from . import scenario_campaign_run as campaign
from .scenario_batch_input import _read
from .scenario_campaign_evidence import capture_tree, verify_manifests
from .scenario_compare_input import read_batch
from .scenario_output import GATES, canonical
from .scenario_report_data import IMPORTED, _json

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


def _child_contract(child: Path, record: dict) -> None:
    generated = _record(child / 'GENERATION.json')
    workflow = _record(child / 'workflow/WORKFLOW.json')
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
            runs.append({'record': saved, 'batch': batch})
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
