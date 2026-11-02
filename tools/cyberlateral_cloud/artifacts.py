"""Committed component export and bounded deterministic evidence, no execution."""

import hashlib
import io
import re
import stat
import subprocess
import unicodedata
import zipfile
from pathlib import Path, PurePosixPath

SOURCE_PREFIX = 'tools/cyberlateral_dev/'
SOURCE_CONTEXT = ('README.md', '.github/workflows/cyberlateral-dev.yaml')
MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_TOTAL_BYTES = 32 * 1024 * 1024
MAX_MEMBERS = 2048
SECRET_SHAPE = re.compile(
    rb'(?:hf_[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{30,}'
    rb'|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)'
)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def new_path(path: Path) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError('OUTPUT_EXISTS')


def validate_names(names) -> None:
    seen = set()
    reserved = {'CON', 'PRN', 'AUX', 'NUL'} | {f'{p}{i}' for p in ['COM', 'LPT'] for i in range(1, 10)}
    for name in names:
        path = PurePosixPath(name)
        alias = unicodedata.normalize('NFC', name).casefold()
        if (not name or path.is_absolute() or path.as_posix() != name or '..' in path.parts
                or name != unicodedata.normalize('NFC', name) or alias in seen
                or any(ord(c) < 32 or c in '\\:<>"|?*' for c in name)
                or any(p.rstrip(' .') != p or p.split('.')[0].upper() in reserved for p in path.parts)):
            raise ValueError('UNSAFE_MEMBER')
        seen.add(alias)
    for name in seen:
        if any('/'.join(name.split('/')[:i]) in seen for i in range(1, len(name.split('/')))):
            raise ValueError('UNSAFE_MEMBER')


def git(repo: Path, *args: str) -> bytes:
    return subprocess.check_output(['git', '-C', str(repo), *args], stderr=subprocess.DEVNULL)


def export_source(repo: Path, commit: str, destination: Path) -> dict:
    if not re.fullmatch(r'[0-9a-f]{40}', commit):
        raise ValueError('FULL_COMMIT_REQUIRED')
    new_path(destination)
    if Path(git(repo, 'rev-parse', '--show-toplevel').decode().strip()).resolve() != repo.resolve():
        raise ValueError('REPOSITORY_ROOT_REQUIRED')
    if git(repo, 'rev-parse', commit + '^{commit}').decode().strip() != commit:
        raise ValueError('COMMIT_IDENTITY')
    entries = git(repo, 'ls-tree', '-r', '-z', commit, '--', SOURCE_PREFIX.rstrip('/'), *SOURCE_CONTEXT).split(b'\0')
    files, records = {}, {}
    for entry in filter(None, entries):
        header, raw_name = entry.split(b'\t', 1)
        mode, kind, blob = header.decode().split()
        name = raw_name.decode('utf-8')
        if kind != 'blob' or mode not in {'100644', '100755'}:
            raise ValueError('SOURCE_MODE')
        if not name.startswith(SOURCE_PREFIX) and name not in SOURCE_CONTEXT:
            raise ValueError('SOURCE_SCOPE')
        raw = git(repo, 'show', commit + ':' + name)
        if hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() != blob:
            raise ValueError('SOURCE_GIT_BLOB')
        files[name] = raw
        records[name] = {'git_blob': blob, 'git_mode': mode, 'sha256': sha(raw), 'byte_size': len(raw)}
    validate_names(files)
    if not files:
        raise ValueError('EMPTY_SOURCE')
    limits(files)
    destination.mkdir(parents=True, exist_ok=False)
    for name, raw in files.items():
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(raw)
    return {'commit': commit, 'tree': git(repo, 'rev-parse', commit + '^{tree}').decode().strip(),
            'scope': 'COMMITTED_COMPONENT_AND_ROOT_CI_CONTEXT_NOT_DIRTY_WORKTREE_OR_FULL_VEHICLE_REPOSITORY', 'files': records}


def limits(files: dict[str, bytes]) -> None:
    if (len(files) > MAX_MEMBERS or sum(map(len, files.values())) > MAX_TOTAL_BYTES
            or any(len(raw) > MAX_FILE_BYTES for raw in files.values())):
        raise ValueError('ARCHIVE_LIMIT')


def manifest(files: dict[str, bytes]) -> bytes:
    return ''.join(sha(raw) + '  ' + name + '\n' for name, raw in sorted(files.items())).encode()


def seal(output: Path, members: dict[str, bytes]) -> dict:
    new_path(output)
    if not members or any(n.casefold() == 'sha256sums.txt' for n in members):
        raise ValueError('EMPTY_OR_CALLER_MANIFEST')
    validate_names(members)
    limits(members)
    if any(SECRET_SHAPE.search(raw) for raw in members.values()):
        raise ValueError('CREDENTIAL_SHAPED_PAYLOAD')
    files = {**members, 'SHA256SUMS.txt': manifest(members)}
    limits(files)
    raw = io.BytesIO()
    with zipfile.ZipFile(raw, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, payload in sorted(files.items()):
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            archive.writestr(info, payload, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    with output.open('xb') as stream:
        stream.write(raw.getvalue())
    return verify_archive(output, sha(raw.getvalue()))


def verify_archive(path: Path, expected_sha: str | None = None) -> dict:
    if path.is_symlink() or path.stat().st_size > MAX_TOTAL_BYTES:
        raise ValueError('ARCHIVE_LIMIT_OR_LINK')
    raw = path.read_bytes()
    digest = sha(raw)
    if expected_sha is not None and digest != expected_sha:
        raise ValueError('ARCHIVE_HASH')
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        entries = archive.infolist()
        validate_names([e.orig_filename for e in entries])
        if any(e.orig_filename != e.filename for e in entries):
            raise ValueError('UNSAFE_MEMBER')
        names = [e.filename for e in entries]
        validate_names(names)
        if (len(entries) > MAX_MEMBERS or sum(e.file_size for e in entries) > MAX_TOTAL_BYTES
                or any(e.file_size > MAX_FILE_BYTES for e in entries)):
            raise ValueError('ARCHIVE_LIMIT')
        if any(e.create_system != 3 or stat.S_IFMT(e.external_attr >> 16) != stat.S_IFREG for e in entries):
            raise ValueError('ARCHIVE_MODE')
        if archive.testzip() is not None:
            raise ValueError('ARCHIVE_CRC')
        files = {name: archive.read(name) for name in names}
    if any(SECRET_SHAPE.search(payload) for payload in files.values()):
        raise ValueError('CREDENTIAL_SHAPED_PAYLOAD')
    if 'SHA256SUMS.txt' not in files:
        raise ValueError('ARCHIVE_CLOSURE')
    lines = files['SHA256SUMS.txt'].decode().splitlines()
    recorded = {}
    for line in lines:
        match = re.fullmatch(r'([0-9a-f]{64})  (.+)', line)
        if match is None or match[2] in recorded:
            raise ValueError('ARCHIVE_CLOSURE')
        recorded[match[2]] = match[1]
    if set(recorded) != set(files) - {'SHA256SUMS.txt'} or not recorded:
        raise ValueError('ARCHIVE_CLOSURE')
    if any(sha(files[name]) != value for name, value in recorded.items()):
        raise ValueError('ARCHIVE_HASH')
    return {'archive_sha256': digest, 'archive_bytes': len(raw), 'member_count': len(files),
            'members': {name: sha(payload) for name, payload in sorted(files.items())}}
