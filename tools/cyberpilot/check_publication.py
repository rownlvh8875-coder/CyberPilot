#!/usr/bin/env python3
"""Fail closed on private route/path or credential material in changed files."""
from dataclasses import asdict, dataclass
import argparse
import hashlib
import json
from pathlib import Path
import re
import stat
import subprocess


MAX_TEXT_BYTES = 1_048_576
PATTERNS = (
  ('private_route', re.compile(r'\b[0-9a-fA-F]{8,}--[0-9a-fA-F]{6,}(?:--\d+)?\b')),
  ('private_timestamp_route', re.compile(r'\b[0-9a-fA-F]{16}(?:\||--)\d{4}-\d{2}-\d{2}--\d{2}-\d{2}-\d{2}\b')),
  ('private_mnt_path', re.compile(r'/mnt/[A-Za-z]/(?:carrot(?:log|logs)?|CyberPilot)(?:[/\\]|$)', re.I)),
  ('private_home_path', re.compile(r'/' + r'home/[A-Za-z0-9_.-]+[/\\]', re.I)),
  ('private_windows_home', re.compile(r'\b[A-Za-z]:[/\\]Users[/\\][A-Za-z0-9_. -]+[/\\]', re.I)),
  ('private_windows_path', re.compile(r'\b[A-Za-z]:[\\/](?:CarrotLogs?|CyberPilot)(?:[\\/]|$)', re.I)),
  ('private_key', re.compile(r'-----BEGIN [A-Z ]*PRIVATE KEY-----')),
  ('aws_access_key', re.compile(r'AKIA[0-9A-Z]{16}')),
  ('github_token', re.compile(r'gh[pousr]_[A-Za-z0-9]{20,}')),
  ('github_fine_grained_token', re.compile(r'github_pat_[A-Za-z0-9_]{20,}')),
  ('openai_key', re.compile(r'sk-(?:proj-)?[A-Za-z0-9_-]{20,}')),
  ('bearer_token', re.compile(r'Bearer\s+[A-Za-z0-9._-]{20,}', re.I)),
  ('raw_location', re.compile(r'["\x27](?:latitude|longitude)["\x27]\s*:\s*-?\d+(?:\.\d+)?', re.I)),
)
RAW_FILE = re.compile(r'(?:^|/)(?:rlog|qlog|fcamera|dcamera|ecamera)(?:\.|$)', re.I)


@dataclass(frozen=True)
class Finding:
  kind: str
  path: str
  line_number: int
  preview: str

  def __post_init__(self):
    if any(pattern.search(self.path) for _, pattern in PATTERNS):
      object.__setattr__(self, 'path', 'redacted-path-sha256:' + hashlib.sha256(self.path.encode()).hexdigest())


def is_probably_text(raw: bytes) -> bool:
  if b'\x00' in raw:
    return False
  try:
    raw.decode('utf-8')
  except UnicodeDecodeError:
    return False
  return True


def scan_text(path: str, text: str) -> tuple[Finding, ...]:
  findings = []
  for line_number, line in enumerate(text.splitlines(), 1):
    for kind, pattern in PATTERNS:
      match = pattern.search(line)
      if match is not None:
        findings.append(Finding(
          kind=kind,
          path=path,
          line_number=line_number,
          preview='[REDACTED]',
        ))
  return tuple(findings)


def _unscannable(path: str, kind: str) -> tuple[Finding, ...]:
  return (Finding('unscannable_' + kind, path, 0, '[REDACTED]'),)


def scan_bytes(name: str, raw: bytes) -> tuple[Finding, ...]:
  if RAW_FILE.search(name):
    return (Finding('raw_log_or_video', name, 0, '[REDACTED]'),)
  if len(raw) > MAX_TEXT_BYTES:
    return _unscannable(name, 'size')
  if not is_probably_text(raw):
    return _unscannable(name, 'binary')
  return scan_text(name, name) + scan_text(name, raw.decode('utf-8'))


def scan_file(path: Path, root: Path) -> tuple[Finding, ...]:
  name = path.relative_to(root).as_posix()
  try:
    if path.is_symlink():
      return _unscannable(name, 'symlink')
    if not stat.S_ISREG(path.stat().st_mode):
      return _unscannable(name, 'file')
    with path.open('rb') as stream:
      return scan_bytes(name, stream.read(MAX_TEXT_BYTES + 1))
  except OSError:
    return _unscannable(name, 'file')


def _git(root: Path, *args: str) -> bytes:
  if args[0] in ('diff', 'diff-tree'):
    args = (*args, '--no-ext-diff', '--no-textconv', '--no-renames', '--ignore-submodules=none')
  result = subprocess.run(
    ['git', '--no-replace-objects', '--literal-pathspecs', '-C', str(root), *args], capture_output=True, check=True,
  )
  if result.stderr:
    # Git can exit zero while warning that it omitted an unreadable directory.
    raise ValueError('GIT_AUDIT_WARNING')
  return result.stdout


def _names(root: Path, *args: str) -> set[str]:
  return {name.decode('utf-8') for name in _git(root, *args).split(b'\0') if name}


def changed_paths(root: Path, base: str) -> tuple[Path, ...]:
  try:
    names = _names(root, 'diff', '--name-only', '-z', '--diff-filter=ACMRT', f'{base}...HEAD')
    names.update(_names(root, 'diff', '--name-only', '-z', '--diff-filter=ACMRT'))
    names.update(_names(root, 'diff', '--cached', '--name-only', '-z', '--diff-filter=ACMRT'))
    names.update(_names(root, 'ls-files', '--others', '--exclude-standard', '-z'))
  except (OSError, UnicodeError, subprocess.CalledProcessError) as error:
    raise ValueError('GIT_DISCOVERY_FAILED') from error
  result = []
  for name in sorted(names):
    path = root / name
    try:
      # Inspect the final symlink as content, never follow its target (or loop).
      path.parent.resolve().relative_to(root.resolve())
    except ValueError as error:
      raise ValueError('PATH_ESCAPES_REPOSITORY') from error
    result.append(path)
  return tuple(result)


def audit_changed(root: Path, base: str) -> tuple[Finding, ...]:
  """Check working content, staged blobs, and every commit that would be sent.

  Deleted worktree files still have their index/history checked. Unsupported
  content is a finding, never a zero-finding audit. No content is repaired.
  """
  findings = []
  seen = set()

  def scan_object(name: str, spec: str):
    entry = (_git(root, 'ls-files', '--stage', '-z', '--', name) if spec.startswith(':')
             else _git(root, 'ls-tree', '-z', spec.split(':', 1)[0], '--', name))
    if entry.startswith(b'120000 '):
      findings.extend(_unscannable(name, 'symlink'))
      return
    oid = _git(root, 'rev-parse', '--verify', spec).strip().decode('ascii')
    if (name, oid) in seen:
      return
    seen.add((name, oid))
    size = int(_git(root, 'cat-file', '-s', oid))
    if size > MAX_TEXT_BYTES:
      findings.extend(_unscannable(name, 'size'))
    elif _git(root, 'cat-file', '-t', oid).strip() != b'blob':
      findings.extend(_unscannable(name, 'git_object'))
    else:
      findings.extend(scan_bytes(name, _git(root, 'cat-file', 'blob', oid)))

  try:
    deleted = _names(root, 'diff', '--name-only', '-z', '--diff-filter=D')
    deleted.update(_names(root, 'diff', '--cached', '--name-only', '-z', '--diff-filter=D'))
    for path in changed_paths(root, base):
      if path.relative_to(root).as_posix() not in deleted or path.exists() or path.is_symlink():
        findings.extend(scan_file(path, root))
    for name in sorted(_names(root, 'diff', '--cached', '--name-only', '-z', '--diff-filter=ACMRT')):
      scan_object(name, ':' + name)
    for revision in _git(root, 'rev-list', f'{base}..HEAD').decode('ascii').splitlines():
      findings.extend(scan_bytes('COMMIT_MESSAGE', _git(root, 'show', '-s', '--format=%B', revision)))
      for name in sorted(_names(root, 'diff-tree', '--root', '-m', '--no-commit-id', '-r',
                                '--name-only', '-z', '--diff-filter=ACMRT', revision)):
        scan_object(name, revision + ':' + name)
  except (OSError, UnicodeError, subprocess.CalledProcessError) as error:
    raise ValueError('GIT_AUDIT_FAILED') from error
  return tuple(dict.fromkeys(findings))


def main() -> int:
  parser = argparse.ArgumentParser()
  parser.add_argument('--repo', type=Path, default=Path.cwd())
  parser.add_argument('--base', default='origin/main')
  parser.add_argument('--json', action='store_true')
  args = parser.parse_args()
  try:
    root = args.repo.resolve()
    findings = audit_changed(root, args.base)
    file_count = len(changed_paths(root, args.base))
  except (OSError, ValueError, RuntimeError):
    print(json.dumps({'status': 'BLOCKED', 'reason': 'PUBLICATION_AUDIT_UNAVAILABLE'}))
    return 2
  if args.json:
    print(json.dumps([asdict(item) for item in findings], sort_keys=True, indent=2))
  else:
    for item in findings:
      print(f'{json.dumps(item.path)}:{item.line_number}: {item.kind}: {item.preview}')
    print(f'publication_check files={file_count} findings={len(findings)}')
  return 1 if findings else 0


if __name__ == '__main__':
  raise SystemExit(main())
