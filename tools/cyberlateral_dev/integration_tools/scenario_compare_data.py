"""Exact typed differences over validated saved records, never model evaluation."""

import hashlib
from itertools import zip_longest

from .scenario_output import GATES, canonical

MISSING = object()
DETAIL_LIMIT = 256


def _changes(before, after, field):
    if before is not MISSING and after is not MISSING:
        if canonical(before) == canonical(after):
            return
        if type(before) is dict and type(after) is dict:
            for key in sorted(before.keys() | after.keys()):
                yield from _changes(before.get(key, MISSING), after.get(key, MISSING), field + '.' + key)
            return
        if type(before) is list and type(after) is list:
            for number, (old, new) in enumerate(zip_longest(before, after, fillvalue=MISSING)):
                yield from _changes(old, new, f'{field}[{number}]')
            return
    yield {'field': field, 'before_present': before is not MISSING, 'after_present': after is not MISSING,
           'before': None if before is MISSING else before, 'after': None if after is MISSING else after}


def _identity(case):
    if case is None or case['result'] is None:
        return None
    return hashlib.sha256(canonical(case['result']['identity'])).hexdigest()


def compare_batches(baseline: dict, candidate: dict) -> dict:
    """Inputs must be snapshots returned by read_batch; no files are opened here."""
    details: list[dict] = []
    cases: list[dict] = []
    total = samples = 0
    for number, (old, new) in enumerate(zip_longest(baseline['cases'], candidate['cases']), 1):
        case_id = f'case-{number:03d}'
        old_identity, new_identity = _identity(old), _identity(new)
        summary: dict = {'case_id': case_id, 'classification': 'MATCH', 'difference_count': 0, 'first_difference': None,
                   'producer_identity_changed': old_identity != new_identity,
                   'baseline_identity_sha256': old_identity, 'candidate_identity_sha256': new_identity}

        def add(changes, sample_index=None, case_id=case_id, summary=summary):
            nonlocal total
            for change in changes:
                detail = {'case_id': case_id, 'sample_index': sample_index, **change}
                total += 1
                summary['difference_count'] += 1
                if summary['first_difference'] is None:
                    summary['first_difference'] = detail
                if len(details) < DETAIL_LIMIT:
                    details.append(detail)

        if old is None or new is None:
            summary['classification'] = 'CASE_ADDED' if old is None else 'CASE_REMOVED'
            add(_changes(old['metadata'] if old else MISSING, new['metadata'] if new else MISSING, 'case'))
        else:
            before, after = old['metadata'], new['metadata']
            if before['status'] != after['status']:
                summary['classification'] = 'STATUS_CHANGED'
                for field in ['status', 'rejection_code', 'input_sha256']:
                    add(_changes(before[field], after[field], field))
            elif before['input_sha256'] != after['input_sha256']:
                summary['classification'] = 'INPUT_CHANGED'
                add(_changes(before['input_sha256'], after['input_sha256'], 'input_raw_sha256'))
                add(_changes(old['input'], new['input'], 'input'))
            elif before['input_sha256'] is None:
                summary['classification'] = 'UNVERIFIABLE_INPUT'
                add([{'field': 'input_raw_sha256', 'before_present': True, 'after_present': True, 'before': None, 'after': None}])
                add(_changes(before['rejection_code'], after['rejection_code'], 'rejection_code'))
            elif before['status'] == 'REJECTED':
                add(_changes(before['rejection_code'], after['rejection_code'], 'rejection_code'))
                if summary['difference_count']:
                    summary['classification'] = 'REJECTION_CHANGED'
            else:
                add(_changes(old['input'], new['input'], 'input'))
                old_rows, new_rows = old['result']['rows'], new['result']['rows']
                samples += max(len(old_rows), len(new_rows))
                for offset, (old_row, new_row) in enumerate(zip_longest(old_rows, new_rows, fillvalue=MISSING)):
                    present = old_rows[offset] if offset < len(old_rows) else new_rows[offset]
                    add(_changes(old_row, new_row, f'rows[{offset}]'), present['prepared']['sample']['index'])
                add(_changes(old['result']['final_state'], new['result']['final_state'], 'final_state'))
                if summary['difference_count']:
                    summary['classification'] = 'RESULT_CHANGED'
        cases.append(summary)
    return {'schema_version': 1, 'contract_id': 'F70UGZ_R34_SAVED_BATCH_COMPARISON_V1',
            'status': 'DIFFERENT' if total else 'MATCH',
            'comparison_claim': 'RECORDED_VALUES_ONLY_NOT_ORIGIN_NUMERICAL_OR_VEHICLE_APPROVAL',
            'baseline_portable_manifest_sha256': baseline['portable_manifest_sha256'],
            'candidate_portable_manifest_sha256': candidate['portable_manifest_sha256'],
            'alignment': 'EXPLICIT_ARGUMENT_POSITION_NOT_SCENARIO_ID', 'exactness': 'TYPED_CANONICAL_NO_TOLERANCE',
            'time_semantics': 'INVOCATION_ORDER_ONLY_NOT_ELAPSED_TIME',
            'compared_sample_count': samples, 'difference_count': total, 'detail_limit': DETAIL_LIMIT,
            'details_truncated': total > len(details), 'first_difference': details[0] if details else None,
            'differences': details, 'cases': cases,
            'all_observed_producer_identities_match': all(not c['producer_identity_changed'] for c in cases),
            'new_model_executions': 0, 'gates': dict(GATES)}
