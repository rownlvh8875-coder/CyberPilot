"""Read-only current-format saved browser verification, never a new browser run."""

import argparse
import json
import math
import os
import re
import stat
import sys
from pathlib import Path, PurePosixPath

from artifacts import manifest, sha, validate_names
from browser_probe import PROFILES
from browser_summary import render_summary

MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_TOTAL_BYTES = 32 * 1024 * 1024
CAPTURES = {f'{p}-{w}-{s}.png' for p in PROFILES for w in (390, 1440) for s in ('top', 'charts', 'footer')}
FILES = ({'RESULT.json', 'SUMMARY_KO.md', 'SHA256SUMS.txt', 'fixture-preparation.log',
          'sign-render.log', 'resumed-render.log'}
         | {'captures/' + n for n in CAPTURES}
         | {f'fixture-inputs/{p}/{n}' for p in PROFILES for n in
            ('INPUT.json', 'RESULTS.json', 'TRACE.csv', 'SUMMARY_KO.md', 'RECEIPT.json', 'SHA256SUMS.txt')}
         | {f'reports/{p}/{n}' for p in PROFILES for n in ('index.html', 'VIEW.json', 'RECEIPT.json', 'SHA256SUMS.txt')})
DIRECTORIES = {p.as_posix() for n in FILES for p in PurePosixPath(n).parents if p != PurePosixPath('.')}


def _need(condition, code='BROWSER_BUNDLE_RECORD'):
    if not condition:
        raise ValueError(code)


def _snapshot(root: Path) -> dict[str, bytes]:
    try:
        root = root.absolute()
        _need(not any(p.is_symlink() for p in (root, *root.parents)) and root.is_dir(), 'BROWSER_BUNDLE_PATH')
        pending, directories, files = [root], set(), {}
        while pending:
            with os.scandir(pending.pop()) as entries:
                for entry in entries:
                    path = Path(entry.path)
                    name = path.relative_to(root).as_posix()
                    info = entry.stat(follow_symlinks=False)
                    if stat.S_ISDIR(info.st_mode) and name in DIRECTORIES:
                        directories.add(name)
                        pending.append(path)
                    elif stat.S_ISREG(info.st_mode) and name in FILES:
                        files[name] = (path, info.st_size)
                    else:
                        raise ValueError('BROWSER_BUNDLE_LAYOUT')
        _need(set(files) == FILES and directories == DIRECTORIES, 'BROWSER_BUNDLE_LAYOUT')
        _need(all(size <= MAX_FILE_BYTES for _, size in files.values())
              and sum(size for _, size in files.values()) <= MAX_TOTAL_BYTES, 'BROWSER_BUNDLE_LIMIT')
        saved = {}
        for name, (path, size) in sorted(files.items()):
            with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), 'rb') as stream:
                _need(stat.S_ISREG(os.fstat(stream.fileno()).st_mode), 'BROWSER_BUNDLE_LAYOUT')
                raw = stream.read(MAX_FILE_BYTES + 1)
            _need(len(raw) == size and len(raw) <= MAX_FILE_BYTES, 'BROWSER_BUNDLE_LIMIT')
            saved[name] = raw
        return saved
    except OSError:
        raise ValueError('BROWSER_BUNDLE_IO') from None


def _pairs(items):
    result = {}
    for key, value in items:
        _need(key not in result)
        result[key] = value
    return result


def _float(value):
    number = float(value)
    _need(math.isfinite(number))
    return number


def _constant(value):
    raise ValueError('BROWSER_BUNDLE_RECORD')


def _record(raw):
    try:
        record = json.loads(raw.decode('utf-8'), object_pairs_hook=_pairs, parse_float=_float, parse_constant=_constant)
        _need(type(record) is dict)
        _need(type(record.get('schema_version')) is int and record['schema_version'] == 1)
        _need(record.get('source_selected_files_unchanged') is True)
        _need(record.get('fixture_runtime_attestation') is False)
        _need(type(record.get('model_F61_r_dt_native_vehicle_executions')) is int
              and record['model_F61_r_dt_native_vehicle_executions'] == 0)
        source = record.get('source_sha256')
        _need(type(source) is dict and len(source) == 16)
        validate_names(source)
        _need(all(type(h) is str and re.fullmatch('[0-9a-f]{64}', h) for h in source.values()))
        return record
    except (ValueError, TypeError, RecursionError):
        raise ValueError('BROWSER_BUNDLE_RECORD') from None


def load_saved_browser(root: Path) -> tuple[dict, dict[str, bytes]]:
    """Return the receipt and its exact validated snapshot, not a later reread."""
    files = _snapshot(root)
    for prefix in ['', *[f'{folder}/{p}/' for folder in ('fixture-inputs', 'reports') for p in PROFILES]]:
        name = prefix + 'SHA256SUMS.txt'
        members = {n.removeprefix(prefix): raw for n, raw in files.items() if n.startswith(prefix) and n != name}
        _need(files[name] == manifest(members), 'BROWSER_BUNDLE_MANIFEST')
    record = _record(files['RESULT.json'])
    for field, prefix in [('captures', 'captures/'), ('input_sha256', 'fixture-inputs/'), ('report_sha256', 'reports/')]:
        hashes = {n.removeprefix(prefix): sha(raw) for n, raw in files.items() if n.startswith(prefix)}
        _need(type(record.get(field)) is dict and record[field] == hashes)
    owned = {n: sha(raw) for n, raw in files.items() if n not in {'RESULT.json', 'SUMMARY_KO.md', 'SHA256SUMS.txt'}}
    try:
        expected = render_summary(record, owned)
    except (ValueError, TypeError, KeyError, RecursionError):
        raise ValueError('BROWSER_BUNDLE_RECORD') from None
    _need(files['SUMMARY_KO.md'] == expected, 'BROWSER_BUNDLE_SUMMARY')
    receipt = {'status': 'R64_SAVED_BROWSER_BUNDLE_VALID', 'recorded_status': record['status'],
            'cases': len(record['cases']), 'recorded_case_failures': sum(bool(r['failures']) for r in record['cases']),
            'recorded_failure_records': len(record['failures']), 'verified_files': len(files),
            'result_sha256': sha(files['RESULT.json']), 'reader_browser_model_F61_vehicle_executions': 0,
            'source_identity_reauthenticated': False,
            'scope': 'SAVED_BYTES_AND_RECORD_CONSISTENCY_NOT_NEW_BROWSER_OR_ORIGIN_ATTESTATION'}
    return receipt, files


def verify_saved_browser(root: Path) -> dict:
    return load_saved_browser(root)[0]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--input', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = verify_saved_browser(args.input)
    except ValueError as error:
        print('REJECTED: ' + str(error), file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, ensure_ascii=True, allow_nan=False))
    return 1 if result['recorded_status'] == 'R60_BROWSER_SMOKE_FAIL' else 0


if __name__ == '__main__':
    raise SystemExit(main())
