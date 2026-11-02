"""Bounded owned campaign evidence, not authenticated filesystem snapshots."""

import hashlib
import os
import re
import stat
from pathlib import Path

from .scenario_batch_input import _read
from .scenario_input import ScenarioError


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
