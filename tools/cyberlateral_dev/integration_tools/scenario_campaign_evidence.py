"""Bounded owned campaign evidence, not authenticated filesystem snapshots."""

import hashlib
import os
import re
import stat
from pathlib import Path

from .scenario_batch_input import _read
from .scenario_batch_reference_run import COUNT_KEYS
from .scenario_compare_input import read_batch
from .scenario_input import ScenarioError
from .scenario_output import GATES, canonical
from .scenario_reference_run import DETAIL_LIMIT
from .scenario_report_data import CAPS, _json


class CampaignError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _need(condition):
    if not condition:
        raise CampaignError('CAMPAIGN_CHILD_EVIDENCE')


def capture_tree(root: Path, *, max_files: int = 2048, max_bytes: int = 134217728) -> dict[str, str]:
    hashes, total, entries = {}, 0, 0
    try:
        _need(not root.is_symlink() and root.is_dir())
        for path in root.rglob('*'):
            entries += 1
            relative = path.relative_to(root)
            _need(entries <= max_files * 2 and len(relative.parts) <= 16 and not path.is_symlink())
            name = relative.as_posix()
            _need(re.fullmatch(r'[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*', name) is not None)
            if path.is_dir():
                continue
            _need(len(hashes) < max_files)
            limit = min(16 * 1024 * 1024, max_bytes - total)
            flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC
            digest, size = hashlib.sha256(), 0
            with os.fdopen(os.open(path, flags), 'rb') as stream:
                observed = os.fstat(stream.fileno())
                _need(stat.S_ISREG(observed.st_mode) and observed.st_size <= limit)
                while block := stream.read(min(65536, limit - size + 1)):
                    size += len(block)
                    _need(size <= limit)
                    digest.update(block)
            total += size
            hashes[name] = digest.hexdigest()
    except (OSError, RuntimeError, AttributeError) as error:
        raise CampaignError('CAMPAIGN_CHILD_EVIDENCE') from error
    return hashes


def verify_manifests(root: Path, hashes: dict) -> None:
    _need('SHA256SUMS.txt' in hashes)
    try:
        for name, digest in hashes.items():
            path = Path(name)
            if path.name not in {'SHA256SUMS.txt', 'PORTABLE_SHA256SUMS.txt'}:
                continue
            raw = _read(root / name)
            _need(hashlib.sha256(raw).hexdigest() == digest)
            prefix = '' if path.parent == Path('.') else path.parent.as_posix() + '/'
            if path.name == 'SHA256SUMS.txt':
                expected = {n.removeprefix(prefix): value for n, value in hashes.items()
                            if n.startswith(prefix) and n != name}
            else:
                lines = raw.decode().splitlines()
                members = [line.split('  ')[1] for line in lines]
                _need(len(members) == len(set(members)))
                expected = {member: hashes[prefix + member] for member in members}
            encoded = ''.join(value + '  ' + member + '\n' for member, value in sorted(expected.items())).encode()
            _need(raw == encoded)
    except (ScenarioError, ValueError, UnicodeError, KeyError, IndexError) as error:
        raise CampaignError('CAMPAIGN_CHILD_EVIDENCE') from error


def validate_stages(root: Path, workflow: dict, checked: dict, identity: dict,
                    hashes: dict, cases: int, steps: int) -> None:
    """Bind saved batch/per-case references; no model or reference worker execution."""
    def same_fields(actual, expected):
        if type(actual) is not dict or any(key not in actual or canonical(actual[key]) != canonical(value)
                                          for key, value in expected.items()):
            raise CampaignError('CAMPAIGN_STAGE_RECORD')

    try:
        batch = read_batch(root / 'workflow/batch')
        same_fields(batch['record'], {'input_count': cases, 'completed': cases, 'rejected': 0,
                                     'total_model_steps': cases * steps})
        helper_totals = dict.fromkeys(COUNT_KEYS, 0)
        reports = []
        for number, item in enumerate(batch['cases'], 1):
            case = f'case-{number:03d}'
            row = checked['cases'][number - 1]
            same_fields(row, {'case_id': case, 'scenario_id': item['metadata']['scenario_id'],
                              'source_status': 'COMPLETE', 'rejection_code': None, 'observed_rejection_code': None})
            if row['status'] == 'ERROR':
                same_fields(row, {'reference_steps': None, 'report': None, 'difference_count': None, 'first_difference': None})
                if type(row['error_code']) is not str or not row['error_code']:
                    raise CampaignError('CAMPAIGN_STAGE_RECORD')
                continue
            if row['status'] not in {'MATCH', 'DIFFERENT'} or type(row['difference_count']) is not int or row['difference_count'] < 0:
                raise CampaignError('CAMPAIGN_STAGE_RECORD')
            same_fields(row, {'reference_steps': steps, 'report': case + '/REFERENCE_CHECK.json', 'error_code': None})
            report = _json(_read(root / 'workflow/reference' / row['report']))
            counts = {'compile_calls': 1, 'selected_definitions_compiled': 2, 'limiter_direct': 0,
                      'limiter_traced': steps, 'fault_explicit': steps, 'fault_default': 0, 'traced_clip_calls': 2 * steps}
            inputs = {name: hashes[f'workflow/batch/{case}/data/{name}'] for name in CAPS}
            same_fields(report, {'schema_version': 1, 'contract_id': 'F70UGZ_R38_SAVED_SCENARIO_REFERENCE_CHECK_V1',
                                 'scenario_id': item['metadata']['scenario_id'], 'status': row['status'],
                                 'reference_steps': steps, 'difference_count': row['difference_count'],
                                 'first_difference': row['first_difference'], 'reference_helper_counts': counts,
                                 'input_source_hashes': inputs, 'reference_identity': identity['reference']['reference'],
                                 'reference_runtime': {'python': '3.12.13', 'numpy': '2.5.3'},
                                 'reference_forbidden_modules_loaded': [], 'new_model_executions': 0,
                                 'detail_limit': DETAIL_LIMIT, 'gates': GATES,
                                 'time_semantics': 'INVOCATION_ORDER_ONLY_NOT_ELAPSED_TIME',
                                 'exactness': 'TYPED_CANONICAL_AND_HEX_NO_TOLERANCE'})
            details = report.get('differences')
            count = row['difference_count']
            if (type(details) is not list or len(details) != min(count, DETAIL_LIMIT)
                    or any(type(d) is not dict or type(d.get('field')) is not str for d in details)
                    or row['status'] != ('DIFFERENT' if count else 'MATCH')):
                raise CampaignError('CAMPAIGN_STAGE_RECORD')
            same_fields(report, {'first_difference': details[0] if details else None, 'details_truncated': count > len(details)})
            if type(report.get('reference_expected_sha256')) is not str or re.fullmatch('[0-9a-f]{64}', report['reference_expected_sha256']) is None:
                raise CampaignError('CAMPAIGN_STAGE_RECORD')
            for key, value in counts.items():
                helper_totals[key] += value
            reports.append(report)
        matched = sum(row['status'] == 'MATCH' for row in checked['cases'])
        different = sum(row['status'] == 'DIFFERENT' for row in checked['cases'])
        errors = cases - len(reports)
        status = 'ERROR' if errors else 'DIFFERENT' if different else 'MATCH'
        first = next(({'case_id': row['case_id'], **row['first_difference']} for row in checked['cases']
                      if row['first_difference'] is not None), None)
        total_differences = sum(report['difference_count'] for report in reports)
        same_fields(checked, {'schema_version': 1, 'contract_id': 'F70UGZ_R39_SAVED_BATCH_REFERENCE_CHECK_V1',
                             'status': status, 'input_count': cases, 'completed_cases': cases, 'matched_cases': matched,
                             'different_cases': different, 'error_cases': errors, 'reference_steps': len(reports) * steps,
                             'input_rejections_confirmed': 0, 'input_rejections_unverified': 0, 'rejection_mismatch_cases': 0,
                             'numerical_difference_count': total_differences, 'first_difference': first,
                             'reference_helper_counts': helper_totals, 'reference_identity': identity['reference'],
                             'input_root_manifest_sha256': batch['root_manifest_sha256'],
                             'input_portable_manifest_sha256': batch['portable_manifest_sha256'],
                             'new_model_executions': 0, 'gates': GATES})
        same_fields(workflow, {'input_count': cases, 'completed': cases, 'rejected': 0, 'model_steps': cases * steps,
                              'reference_steps': len(reports) * steps, 'reference_difference_count': total_differences,
                              'reference_status': status, 'reference_helper_counts': helper_totals,
                              'status': {'MATCH': 'VERIFIED', 'DIFFERENT': 'REFERENCE_DIFFERENT', 'ERROR': 'ERROR'}[status],
                              'observed_dev_source_hashes': identity['workflow'], 'gates': GATES,
                              'batch_portable_manifest_sha256': batch['portable_manifest_sha256']})
    except (ValueError, OSError, TypeError, KeyError, IndexError, AttributeError) as error:
        raise CampaignError('CAMPAIGN_STAGE_RECORD') from error
