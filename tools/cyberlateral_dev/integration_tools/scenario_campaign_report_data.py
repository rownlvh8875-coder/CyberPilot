"""Own bounded complete R44 bytes. Do not open paths declared inside records."""

import hashlib
import os
import stat
from pathlib import Path

from .scenario_campaign_evidence import capture_tree, verify_manifests
from .scenario_campaign_report_schema import CampaignReportError, digest, integer, keys, need, same, validate_comparison
from .scenario_compare_run import FORBIDDEN
from .scenario_report_data import _json

MAX_FILES, MAX_BYTES, FILE_BYTES = 12, 32 * 1024 * 1024, 16 * 1024 * 1024
CLAIM = 'STRUCTURAL_SAVED_RECORD_CONSISTENCY_NOT_ORIGINAL_COMPARISON_REGENERATION_OR_ORIGIN_AUTHENTICATION'


def _receipt(value):
    keys(value, {'schema_version', 'baseline_directory', 'candidate_directory', 'output_directory', 'source_root',
                 'comparator_source_hashes', 'baseline_root_manifest_sha256', 'candidate_root_manifest_sha256',
                 'python_executable', 'python_version', 'python_executable_sha256', 'forbidden_modules_loaded',
                 'new_model_executions', 'new_reference_executions', 'cache_policy', 'scope'})
    same(value['schema_version'], 1)
    same(value['python_version'], '3.12.13')
    for name in ['new_model_executions', 'new_reference_executions']:
        integer(value[name], 0, 0)
    for name in ['baseline_directory', 'candidate_directory', 'output_directory', 'source_root', 'python_executable']:
        need(type(value[name]) is str and len(value[name]) <= 8192)
    for name in ['baseline_root_manifest_sha256', 'candidate_root_manifest_sha256', 'python_executable_sha256']:
        digest(value[name])
    inventory = value['comparator_source_hashes']
    need(type(inventory) is dict and 1 <= len(inventory) <= 256)
    for name, value_hash in inventory.items():
        need(type(name) is str and len(name) <= 512)
        digest(value_hash)
    loaded = value['forbidden_modules_loaded']
    need(type(loaded) is list and all(type(n) is str and n in FORBIDDEN for n in loaded))
    same(loaded, sorted(set(loaded)))
    same(value['cache_policy'], 'COLD_PRIVATE_PREFIX_IN_CLI_ONLY_NOT_IN_PROCESS_API')
    same(value['scope'], 'COOPERATIVE_BEFORE_AFTER_CONSISTENCY_NOT_OS_SNAPSHOT_OR_ORIGIN_AUTHENTICATION')


def _owned(path, digest_hash):
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC
    with os.fdopen(os.open(path, flags), 'rb') as stream:
        info = os.fstat(stream.fileno())
        need(stat.S_ISREG(info.st_mode) and info.st_size <= FILE_BYTES, 'CAMPAIGN_REPORT_INPUT_FILE')
        raw = stream.read(FILE_BYTES + 1)
    need(len(raw) <= FILE_BYTES and hashlib.sha256(raw).hexdigest() == digest_hash, 'CAMPAIGN_REPORT_INPUT_CHANGED')
    return raw


def read_comparison(path: Path) -> dict:
    try:
        need(not any(p.is_symlink() for p in [path, *path.absolute().parents]), 'CAMPAIGN_REPORT_INPUT_FILE')
        hashes = capture_tree(path, max_files=MAX_FILES, max_bytes=MAX_BYTES)
        verify_manifests(path, hashes)
        need({'CAMPAIGN_COMPARE.json', 'SUMMARY_KO.md', 'RECEIPT.json', 'SHA256SUMS.txt'} <= hashes.keys(), 'CAMPAIGN_REPORT_FILES')
        owned = {name: _owned(path / name, value) for name, value in hashes.items()}
        record = _json(owned['CAMPAIGN_COMPARE.json'])
        need(type(record) is dict and type(record.get('runs')) is list and len(record['runs']) <= 4)
        children, expected = {}, {'CAMPAIGN_COMPARE.json', 'SUMMARY_KO.md', 'RECEIPT.json', 'SHA256SUMS.txt'}
        for number, row in enumerate(record['runs'], 1):
            need(type(row) is dict)
            if row.get('comparison_report') is not None:
                run_id = f'seed-{number:03d}'
                name = f'comparisons/{run_id}/COMPARE.json'
                same(row['comparison_report'], name)
                expected.update({name, f'comparisons/{run_id}/SHA256SUMS.txt'})
                need(name in owned, 'CAMPAIGN_REPORT_FILES')
                children[run_id] = _json(owned[name])
        need(hashes.keys() == expected, 'CAMPAIGN_REPORT_FILES')
        directories = {p.parent for p in map(Path, expected)} - {Path('.')}
        if directories:
            directories.add(Path('comparisons'))
        need({p.relative_to(path) for p in path.rglob('*') if p.is_dir()} == directories, 'CAMPAIGN_REPORT_FILES')
        validate_comparison(record, children)
        _receipt(_json(owned['RECEIPT.json']))
        need(capture_tree(path, max_files=MAX_FILES, max_bytes=MAX_BYTES) == hashes, 'CAMPAIGN_REPORT_INPUT_CHANGED')
    except CampaignReportError:
        raise
    except (OSError, ValueError, RuntimeError) as error:
        raise CampaignReportError('CAMPAIGN_REPORT_INPUT_FILE') from error
    return {'hashes': hashes, 'view': {
        'schema_version': 1, 'contract_id': 'R46_RECORDED_CAMPAIGN_COMPARISON_VIEW_V1',
        'comparison': record, 'children': children, 'source_file_hashes': hashes,
        'renderer_model_executions': 0, 'renderer_reference_executions': 0, 'claim': CLAIM,
    }}
