"""Bounded complete R33 snapshots and cross-record consistency; no model work."""

import hashlib
import os
import re
import stat
from dataclasses import asdict
from pathlib import Path

from .scenario_input import ScenarioError, parse_scenario
from .scenario_output import GATES, canonical
from .scenario_report_data import CAPS, PORTABLE, ReportError, _json, _spec, decode_report

MAX_FILE_BYTES = 16 * 1024 * 1024
MAX_TOTAL_BYTES = 128 * 1024 * 1024
MAX_MEMBERS = 512
ROOT_FILES = {'BATCH.json', 'index.html', 'RECEIPT.json', 'PORTABLE_SHA256SUMS.txt', 'SHA256SUMS.txt'}
REPORT_FILES = {'VIEW.json', 'index.html', 'RECEIPT.json', 'SHA256SUMS.txt'}
CASE_KEYS = {'case_id', 'input_name', 'input_sha256', 'snapshot', 'scenario_id', 'status', 'rejection_code', 'model_steps', 'data', 'report'}


class CompareError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _need(ok, code='COMPARE_SCHEMA'):
    if not ok:
        raise CompareError(code)


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _manifest(files: dict[str, bytes]) -> bytes:
    return ''.join(_sha(raw) + '  ' + name + '\n' for name, raw in sorted(files.items())).encode()


def _owned_files(path: Path) -> tuple[dict[str, bytes], set[str]]:
    owned: dict[str, bytes] = {}
    directories: set[str] = set()
    total = 0
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC

    def walk(directory, prefix='', depth=0):
        nonlocal total
        _need(depth <= 4, 'COMPARE_SIZE')
        with os.scandir(directory) as entries:
            for entry in entries:
                _need(len(owned) + len(directories) < MAX_MEMBERS + 128, 'COMPARE_SIZE')
                name = prefix + entry.name
                if entry.is_dir(follow_symlinks=False):
                    _need(re.fullmatch(r'(?:inputs|case-\d{3}(?:/(?:data|report))?)', name) is not None, 'COMPARE_FILES')
                    child = os.open(entry.name, flags | os.O_DIRECTORY, dir_fd=directory)
                    try:
                        directories.add(name)
                        walk(child, name + '/', depth + 1)
                    finally:
                        os.close(child)
                else:
                    _need(len(owned) < MAX_MEMBERS, 'COMPARE_SIZE')
                    _need(name in ROOT_FILES or re.fullmatch(r'(?:inputs/case-\d{3}\.json|case-\d{3}/(?:producer\.log|renderer\.log|(?:data|report)/[A-Za-z0-9_.]+))', name) is not None,
                          'COMPARE_FILES')
                    cap = min(MAX_FILE_BYTES, MAX_TOTAL_BYTES - total)
                    if name in ('BATCH.json', 'RECEIPT.json'):
                        cap = min(cap, 524288)
                    if name in ('SHA256SUMS.txt', 'PORTABLE_SHA256SUMS.txt'):
                        cap = min(cap, 131072)
                    descriptor = os.open(entry.name, flags, dir_fd=directory)
                    with os.fdopen(descriptor, 'rb') as stream:
                        observed = os.fstat(stream.fileno())
                        _need(stat.S_ISREG(observed.st_mode), 'COMPARE_INPUT_FILE')
                        _need(observed.st_size <= cap, 'COMPARE_SIZE')
                        raw = stream.read(cap + 1)
                    _need(len(raw) <= cap, 'COMPARE_SIZE')
                    owned[name] = raw
                    total += len(raw)

    try:
        directory = os.open(path, flags | os.O_DIRECTORY)
        try:
            walk(directory)
        finally:
            os.close(directory)
    except (OSError, AttributeError) as error:
        raise CompareError('COMPARE_INPUT_FILE') from error
    return owned, directories


def _read_batch(path: Path) -> dict:
    files, directories = _owned_files(path)
    _need(ROOT_FILES <= files.keys(), 'COMPARE_FILES')
    _need(files['SHA256SUMS.txt'] == _manifest({n: raw for n, raw in files.items() if n != 'SHA256SUMS.txt'}), 'COMPARE_CHECKSUM')
    record = _json(files['BATCH.json'])
    _need(type(record) is dict and type(record.get('cases')) is list)
    rows = record['cases']
    _need(1 <= len(rows) <= 32)
    expected_files = set(ROOT_FILES)
    expected_dirs = {'inputs'}
    portable = {n: files[n] for n in ['BATCH.json', 'index.html']}
    cases = []
    for number, row in enumerate(rows, 1):
        case_id = f'case-{number:03d}'
        _need(type(row) is dict and row.keys() == CASE_KEYS)
        _need(row['case_id'] == case_id and type(row['input_name']) is str and 1 <= len(row['input_name'].encode()) <= 1024)
        _need(row['status'] in ('COMPLETE', 'REJECTED') and type(row['model_steps']) is int)
        raw = None
        if row['input_sha256'] is not None:
            _need(type(row['input_sha256']) is str and re.fullmatch('[0-9a-f]{64}', row['input_sha256']) is not None)
            name = f'inputs/{case_id}.json'
            _need(row['snapshot'] == name and name in files, 'COMPARE_FILES')
            raw = files[name]
            _need(len(raw) <= 1048576 and _sha(raw) == row['input_sha256'], 'COMPARE_INPUT_BINDING')
            expected_files.add(name)
            portable[name] = raw
        else:
            _need(row['snapshot'] is None and row['status'] == 'REJECTED')
        detail = {'metadata': row, 'input': None, 'result': None}
        if row['status'] == 'COMPLETE':
            if raw is None:
                raise CompareError('COMPARE_INPUT_BINDING')
            _need(row['rejection_code'] is None and 1 <= row['model_steps'] <= 4096)
            _need(row['data'] == case_id + '/data' and row['report'] == case_id + '/report')
            expected_dirs.update({case_id, row['data'], row['report']})
            data = {n: files[row['data'] + '/' + n] for n in CAPS}
            decoded = decode_report(data)
            spec = parse_scenario(raw)
            source = _json(data['INPUT.json'])
            _need(canonical(asdict(spec)) == canonical(asdict(_spec(source))), 'COMPARE_INPUT_BINDING')
            result = _json(data['RESULTS.json'])
            _need(row['scenario_id'] == spec.scenario_id and row['model_steps'] == len(spec.samples), 'COMPARE_INPUT_BINDING')
            report = {n: files[row['report'] + '/' + n] for n in REPORT_FILES}
            _need(report['SHA256SUMS.txt'] == _manifest({n: v for n, v in report.items() if n != 'SHA256SUMS.txt'}), 'COMPARE_CHECKSUM')
            _need(report['VIEW.json'] == canonical(decoded['view']), 'COMPARE_RECORD')
            _need(type(_json(report['RECEIPT.json'])) is dict)
            for directory, names in [(row['data'], CAPS), (row['report'], REPORT_FILES)]:
                expected_files.update(directory + '/' + n for n in names)
            expected_files.update(case_id + '/' + n for n in ['producer.log', 'renderer.log'])
            for directory, names in [(row['data'], PORTABLE), (row['report'], ['VIEW.json', 'index.html'])]:
                portable.update({directory + '/' + n: files[directory + '/' + n] for n in names})
            detail.update(input=source, result=result)
        else:
            _need(row['data'] is None and row['report'] is None and row['scenario_id'] is None and row['model_steps'] == 0)
            _need(type(row['rejection_code']) is str and re.fullmatch('SCENARIO_[A-Z_]+', row['rejection_code']) is not None)
        cases.append(detail)
    _need(files.keys() == expected_files and directories == expected_dirs, 'COMPARE_FILES')
    _need(files['PORTABLE_SHA256SUMS.txt'] == _manifest(portable), 'COMPARE_CHECKSUM')
    _need(type(_json(files['RECEIPT.json'])) is dict)
    rejected = sum(r['status'] == 'REJECTED' for r in rows)
    steps = sum(r['model_steps'] for r in rows)
    _need(steps <= 8192, 'COMPARE_SIZE')
    expected = {'schema_version': 1, 'contract_id': 'F70UGZ_R33_DECLARED_SYNTHETIC_BATCH_V1',
                'status': 'BATCH_COMPLETE_WITH_REJECTIONS' if rejected else 'BATCH_COMPLETE',
                'input_count': len(rows), 'completed': len(rows) - rejected, 'rejected': rejected,
                'total_model_steps': steps, 'renderer_model_executions': 0,
                'input_order': 'EXPLICIT_ARGUMENT_ORDER', 'state_scope': 'INDEPENDENT_PER_FILE_NO_CROSS_FILE_STATE',
                'input_origin': 'CALLER_DECLARATION_NOT_AUTHENTICATED', 'time_semantics': 'INVOCATION_ORDER_ONLY_NOT_ELAPSED_TIME',
                'numerical_claim': 'MODEL_RESULTS_NOT_GENERIC_INDEPENDENT_ORACLE', 'gates': GATES, 'cases': rows}
    _need(canonical(record) == canonical(expected), 'COMPARE_RECORD')
    return {'record': record, 'cases': cases, 'portable_manifest_sha256': _sha(files['PORTABLE_SHA256SUMS.txt']),
            'root_manifest_sha256': _sha(files['SHA256SUMS.txt'])}


def read_batch(path: Path) -> dict:
    try:
        return _read_batch(path)
    except CompareError:
        raise
    except (ReportError, ScenarioError, KeyError, TypeError, ValueError, UnicodeError) as error:
        raise CompareError('COMPARE_RECORD') from error
