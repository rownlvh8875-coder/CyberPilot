"""Bounded supplementary R67 recovery; archived code is copied, never executed."""

import hashlib
import json
import subprocess
from pathlib import Path

from artifacts import git, new_restore_directory, sha, validate_names
from browser_verify import FILES, load_saved_browser
from cloud_restore import archive_payloads
from cloud_run import canonical

SOURCE_SCOPE = 'COMMITTED_CLOUD_TOOLS_AND_R67_DOCS_NOT_DEV_APP_FULL_REPO_OR_VEHICLE_INSTALL'
SOURCE_PATHS = ('tools/cyberlateral_cloud',
                'docs/superpowers/specs/2026-11-04-r67-korean-comparison-summary-design.md',
                'docs/superpowers/plans/2026-11-04-r67-korean-comparison-summary.md')
ALIASES = ('one', 'two', 'fail')


def _need(condition, code):
    if not condition:
        raise ValueError(code)


def _pairs(items):
    result = {}
    for key, value in items:
        _need(key not in result, 'TOOL_METADATA_INVALID')
        result[key] = value
    return result


def _constant(value):
    raise ValueError('TOOL_METADATA_INVALID')


def _json(raw):
    try:
        return json.loads(raw, object_pairs_hook=_pairs, parse_constant=_constant)
    except (ValueError, UnicodeError, RecursionError):
        raise ValueError('TOOL_METADATA_INVALID') from None


def _identity(repo: Path, commit: str) -> tuple[dict, dict[str, bytes]]:
    try:
        _need(Path(git(repo, 'rev-parse', '--show-toplevel').decode().strip()).resolve() == repo.resolve(),
              'REPOSITORY_ROOT_REQUIRED')
        _need(len(commit) == 40 and all(c in '0123456789abcdef' for c in commit), 'FULL_COMMIT_REQUIRED')
        _need(git(repo, 'rev-parse', commit + '^{commit}').decode().strip() == commit, 'COMMIT_IDENTITY')
        files, records = {}, {}
        entries = git(repo, 'ls-tree', '-r', '-z', commit, '--', *SOURCE_PATHS).split(b'\0')
        for entry in filter(None, entries):
            header, raw_name = entry.split(b'\t', 1)
            mode, kind, blob = header.decode().split()
            name = raw_name.decode()
            _need(kind == 'blob' and mode in {'100644', '100755'}, 'SOURCE_MODE')
            raw = git(repo, 'show', commit + ':' + name)
            _need(hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == blob, 'SOURCE_GIT_BLOB')
            files[name] = raw
            records[name] = {'sha256': sha(raw), 'byte_size': len(raw), 'git_mode': mode, 'git_blob': blob}
        _need(bool(files), 'EMPTY_TOOL_SOURCE')
        validate_names(files)
        return {'commit': commit, 'tree': git(repo, 'rev-parse', commit + '^{tree}').decode().strip(),
                'files': records, 'scope': SOURCE_SCOPE}, files
    except (subprocess.CalledProcessError, UnicodeError):
        raise ValueError('TOOL_GIT_SOURCE_UNAVAILABLE') from None


def recover_tooling(repo: Path, commit: str, archive: Path, digest: str, destination: Path) -> dict:
    destination = new_restore_directory(destination)
    _need(not destination.resolve().is_relative_to(repo.resolve()), 'EXTERNAL_OUTPUT_REQUIRED')
    payload = archive_payloads(archive, digest)
    identity = _json(payload['SOURCE_IDENTITY.json'])
    saved = _json(payload['SAVED_IDENTITY.json'])
    expected, original = _identity(repo, commit)
    _need(canonical(identity) == canonical(expected), 'TOOL_SOURCE_IDENTITY_MISMATCH')
    _need({n.removeprefix('SOURCE/') for n in payload if n.startswith('SOURCE/')} == set(original), 'TOOL_SOURCE_MEMBER_SET')
    _need(all(payload['SOURCE/' + n] == raw for n, raw in original.items()), 'TOOL_SOURCE_GIT_MISMATCH')
    _need(type(saved) is dict and set(saved) == set(ALIASES), 'TOOL_SAVED_IDENTITY_MISMATCH')
    _need({n for n in payload if n.startswith('SAVED/')} ==
          {f'SAVED/{alias}/{name}' for alias in ALIASES for name in FILES}, 'TOOL_SAVED_MEMBER_SET')
    for alias in ALIASES:
        record = saved[alias]
        _need(type(record) is dict and type(record.get('files')) is dict and set(record['files']) == FILES,
              'TOOL_SAVED_IDENTITY_MISMATCH')
        for name in FILES:
            raw, item = payload[f'SAVED/{alias}/{name}'], record['files'][name]
            _need(type(item) is dict and item.get('sha256') == sha(raw)
                  and type(item.get('byte_size')) is int and item['byte_size'] == len(raw)
                  and type(item.get('mode')) is int and 0 <= item['mode'] <= 0o777,
                  'TOOL_SAVED_IDENTITY_MISMATCH')
    destination.mkdir(exist_ok=False)
    for name, raw in original.items():
        path = destination / 'source' / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(raw)
        path.chmod(int(expected['files'][name]['git_mode'], 8) & 0o777)
    receipts = {}
    for alias in ALIASES:
        for name in sorted(FILES):
            path = destination / 'saved' / alias / name
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('xb') as stream:
                stream.write(payload[f'SAVED/{alias}/{name}'])
            path.chmod(saved[alias]['files'][name]['mode'])
        receipts[alias] = load_saved_browser(destination / 'saved' / alias)[0]
        _need(canonical(receipts[alias]) == canonical(saved[alias].get('recorded_receipt')), 'TOOL_SAVED_RECEIPT_MISMATCH')
    return {'status': 'EXACT_GIT_MATCHED_TOOLING_AND_SAVED_RECOVERED', 'source_commit': commit,
            'source_tree': expected['tree'], 'source_files': len(original), 'identity': expected,
            'saved_files': len(ALIASES) * len(FILES), 'original_receipts': receipts, 'downloaded_driver_executions': 0}
