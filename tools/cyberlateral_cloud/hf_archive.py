"""Private content-addressed archival; SDK stays outside the model environment."""

import argparse
import importlib.metadata
import json
import re
import tempfile
import zipfile
from pathlib import Path

from artifacts import MAX_TOTAL_BYTES, new_restore_directory, sha, verify_archive


def call(code, function, *args):
    try:
        return function(*args)
    except Exception:
        raise ValueError(code) from None


def preflight(repo: str, hub) -> dict:
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,95}/[A-Za-z0-9][A-Za-z0-9_.-]{0,95}', repo):
        raise ValueError('REPO_ID')
    user = call('STORAGE_AUTH_OR_REPOSITORY_FAILED', hub.whoami)
    if user != repo.split('/')[0]:
        raise ValueError('OWN_NAMESPACE_REQUIRED')
    info = call('STORAGE_AUTH_OR_REPOSITORY_FAILED', hub.info, repo)
    if info['private'] is not True:
        raise ValueError('PRIVATE_REPOSITORY_REQUIRED')
    if not re.fullmatch(r'[0-9a-f]{40}', info['sha']):
        raise ValueError('REMOTE_COMMIT_INVALID')
    return info


def backup(archive: Path, digest: str, repo: str, source_commit: str, hub) -> dict:
    verified = verify_archive(archive, digest)
    if not re.fullmatch(r'[0-9a-f]{40}', source_commit):
        raise ValueError('FULL_COMMIT_REQUIRED')
    with zipfile.ZipFile(archive) as bundle:
        if json.loads(bundle.read('SOURCE_IDENTITY.json')).get('commit') != source_commit:
            raise ValueError('SOURCE_COMMIT_MISMATCH')
    info = preflight(repo, hub)
    prefix = f'runs/{source_commit}/{digest}/'
    captured = archive.read_bytes()
    if sha(captured) != digest:
        raise ValueError('ARCHIVE_HASH')
    payloads = {prefix + 'EVIDENCE.zip': captured,
                prefix + 'SHA256SUMS.txt': (digest + '  EVIDENCE.zip\n').encode()}
    existing = call('STORAGE_LIST_FAILED', hub.list_files, repo, info['sha'])
    collisions = set(payloads).intersection(existing)
    received = {}
    if collisions:
        if collisions != set(payloads):
            raise ValueError('REMOTE_PARTIAL_NO_OVERWRITE')
        for name, raw in payloads.items():
            received[name] = call('STORAGE_DOWNLOAD_FAILED', hub.download, repo, name, info['sha'], len(raw))
            if received[name] != raw:
                raise ValueError('REMOTE_CONFLICT_DOWNLOAD_MISMATCH')
        commit = info['sha']
    else:
        commit = call('STORAGE_UPLOAD_FAILED', hub.commit, repo, info['sha'], payloads)
        if not re.fullmatch(r'[0-9a-f]{40}', commit):
            raise ValueError('REMOTE_COMMIT_INVALID')
        for name, raw in payloads.items():
            received[name] = call('STORAGE_DOWNLOAD_FAILED', hub.download, repo, name, commit, len(raw))
            if received[name] != raw or sha(received[name]) != sha(raw):
                raise ValueError('DOWNLOAD_MISMATCH')
    after = call('STORAGE_AUTH_OR_REPOSITORY_FAILED', hub.info, repo, commit)
    if after['private'] is not True:
        raise ValueError('PRIVATE_REPOSITORY_REQUIRED')
    if after['sha'] != commit:
        raise ValueError('REMOTE_COMMIT_INVALID')
    with tempfile.TemporaryDirectory(prefix='cyberpilot-archive-check-') as scratch:
        restored = Path(scratch) / 'EVIDENCE.zip'
        restored.write_bytes(received[prefix + 'EVIDENCE.zip'])
        if verify_archive(restored, digest) != verified:
            raise ValueError('DOWNLOAD_MISMATCH')
    return {'status': 'PRIVATE_BACKUP_EXACT', 'repo_id': repo, 'private': True, 'commit_sha': commit,
            'prefix': prefix, 'archive_sha256': digest, 'verified_files': 2, 'reused_commit': bool(collisions),
            'scope': 'EXACT_CONTENT_CONSISTENCY_NOT_ORIGIN_AUTHENTICATION_OR_RUNTIME_QUALIFICATION'}


def fetch(digest: str, repo: str, source_commit: str, revision: str, output: Path, hub) -> dict:
    for value, length in [(digest, 64), (source_commit, 40), (revision, 40)]:
        if not isinstance(value, str) or re.fullmatch('[0-9a-f]{' + str(length) + '}', value) is None:
            raise ValueError('FULL_ARCHIVE_SOURCE_AND_REVISION_REQUIRED')
    output = new_restore_directory(output)
    preflight(repo, hub)
    pinned = call('STORAGE_AUTH_OR_REPOSITORY_FAILED', hub.info, repo, revision)
    if pinned['private'] is not True:
        raise ValueError('PRIVATE_REPOSITORY_REQUIRED')
    if pinned['sha'] != revision:
        raise ValueError('REMOTE_COMMIT_INVALID')
    prefix = f'runs/{source_commit}/{digest}/'
    output.mkdir(exist_ok=False)
    raw = call('STORAGE_DOWNLOAD_FAILED', hub.download, repo, prefix + 'EVIDENCE.zip', revision, MAX_TOTAL_BYTES)
    checksum = (digest + '  EVIDENCE.zip\n').encode()
    sidecar = call('STORAGE_DOWNLOAD_FAILED', hub.download, repo, prefix + 'SHA256SUMS.txt', revision, len(checksum))
    if sidecar != checksum:
        raise ValueError('ARCHIVE_CHECKSUM_MISMATCH')
    if len(raw) > MAX_TOTAL_BYTES:
        raise ValueError('ARCHIVE_LIMIT')
    archive = output / 'EVIDENCE.zip'
    with archive.open('xb') as stream:
        stream.write(raw)
    with (output / 'SHA256SUMS.txt').open('xb') as stream:
        stream.write(sidecar)
    verified = verify_archive(archive, digest)
    with zipfile.ZipFile(archive) as bundle:
        if json.loads(bundle.read('SOURCE_IDENTITY.json')).get('commit') != source_commit:
            raise ValueError('SOURCE_COMMIT_MISMATCH')
    after = call('STORAGE_AUTH_OR_REPOSITORY_FAILED', hub.info, repo, revision)
    if after['private'] is not True or preflight(repo, hub)['private'] is not True:
        raise ValueError('PRIVATE_REPOSITORY_REQUIRED')
    if after['sha'] != revision:
        raise ValueError('REMOTE_COMMIT_INVALID')
    return {'status': 'PRIVATE_FETCH_EXACT', 'repo_id': repo, 'private': True, 'commit_sha': revision,
            'prefix': prefix, 'archive_sha256': digest, 'archive_bytes': verified['archive_bytes'],
            'member_count': verified['member_count'], 'verified_files': 2, 'remote_writes': 0}


class SdkHub:
    def __init__(self):
        # Deliberately imported only in this isolated worker, never model/tests.
        from huggingface_hub import CommitOperationAdd, HfApi
        if importlib.metadata.version('huggingface-hub') != '2.4.0':
            raise ValueError('HF_SDK_VERSION')
        self.api = HfApi()
        self.operation = CommitOperationAdd

    def whoami(self):
        return self.api.whoami()['name']

    def info(self, repo, revision=None):
        result = self.api.repo_info(repo, repo_type='dataset', revision=revision)
        return {'private': result.private, 'sha': result.sha}

    def list_files(self, repo, revision):
        return set(self.api.list_repo_files(repo, repo_type='dataset', revision=revision))

    def commit(self, repo, parent, files):
        operations = [self.operation(path_in_repo=name, path_or_fileobj=raw) for name, raw in sorted(files.items())]
        return self.api.create_commit(repo_id=repo, repo_type='dataset', parent_commit=parent,
                                      operations=operations, commit_message='Archive verified CyberPilot cloud evidence').oid

    def download(self, repo, name, revision, max_bytes):
        metadata = self.api.get_paths_info(repo, name, repo_type='dataset', revision=revision)
        size = getattr(metadata[0], 'size', None) if len(metadata) == 1 else None
        if type(size) is not int or not 0 <= size <= max_bytes:
            raise ValueError('DOWNLOAD_LIMIT')
        with tempfile.TemporaryDirectory(prefix='cyberpilot-hf-download-') as scratch:
            path = self.api.hf_hub_download(repo, name, repo_type='dataset', revision=revision,
                                            local_dir=scratch, force_download=True)
            raw = Path(path).read_bytes()
        if len(raw) > max_bytes:
            raise ValueError('DOWNLOAD_LIMIT')
        return raw


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='action', required=True)
    check = commands.add_parser('preflight')
    check.add_argument('--repo-id', required=True)
    put = commands.add_parser('backup')
    put.add_argument('--repo-id', required=True)
    put.add_argument('--archive', type=Path, required=True)
    put.add_argument('--archive-sha', required=True)
    put.add_argument('--source-commit', required=True)
    get = commands.add_parser('fetch')
    get.add_argument('--repo-id', required=True)
    get.add_argument('--archive-sha', required=True)
    get.add_argument('--source-commit', required=True)
    get.add_argument('--revision', required=True)
    get.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        hub = SdkHub()
        if args.action == 'preflight':
            info = preflight(args.repo_id, hub)
            result = {'status': 'PRIVATE_STORAGE_READY', 'repo_id': args.repo_id, **info}
        elif args.action == 'backup':
            result = backup(args.archive, args.archive_sha, args.repo_id, args.source_commit, hub)
        else:
            result = fetch(args.archive_sha, args.repo_id, args.source_commit, args.revision, args.output, hub)
    except Exception as error:
        code = str(error) if type(error) is ValueError and re.fullmatch(r'[A-Z0-9_]{1,80}', str(error)) else 'STORAGE_WORKER_FAILED'
        print(json.dumps({'status': 'FAILED', 'code': code}, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
