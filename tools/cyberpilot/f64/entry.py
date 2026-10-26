"""Trusted bootstrap: read-only Git proof, then install sentinel before application import."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

from tools.cyberpilot.f64 import isolation

with isolation.Guard():
  from tools.cyberpilot.f64.source import ContractError

ROOT = Path(__file__).resolve().parents[3]
MANIFEST = 'artifacts/f64/pre_holdout_source_manifest.json'
_PROOFS = {}
sys.modules.setdefault('tools.cyberpilot.f64.entry', sys.modules[__name__])


def hashes_equal(data, expected):
  return hashlib.sha256(data).hexdigest() == expected


def verify_holdout_source(root, commit):
  if type(commit) is not str or re.fullmatch('[0-9a-f]{40}', commit) is None:
    raise ContractError('F64_SOURCE_PIN')
  if isolation.active():
    if commit not in _PROOFS:
      raise ContractError('F64_SOURCE_PIN')
    return _PROOFS[commit]
  root = Path(root)
  if root != ROOT:
    raise ContractError('F64_SOURCE_PIN')
  def git(*args):
    result = subprocess.run(['/usr/bin/git', '--no-optional-locks', '-c', 'core.fsmonitor=false',
                             '-c', 'core.hooksPath=/dev/null', '-C', str(root), *args],
                            capture_output=True, check=False)
    if result.returncode:
      raise ContractError('F64_SOURCE_PIN')
    return result.stdout
  if git('rev-parse', commit+'^{commit}').decode().strip() != commit:
    raise ContractError('F64_SOURCE_PIN')
  if git('status', '--porcelain=v1', '--untracked-files=all').strip():
    raise ContractError('F64_SOURCE_PIN')
  git('merge-base', '--is-ancestor', commit, 'HEAD')
  frozen = git('show', commit+':'+MANIFEST)
  if (root/MANIFEST).read_bytes() != frozen:
    raise ContractError('F64_SOURCE_PIN')
  manifest = json.loads(frozen)
  paths = []
  for item in manifest['files']:
    rel = item['path']
    if rel.startswith('/') or '..' in Path(rel).parts or '\\' in rel or rel in paths:
      raise ContractError('F64_SOURCE_PIN')
    paths.append(rel)
    path = root/rel
    if path.is_symlink() or not hashes_equal(path.read_bytes(), item['sha256']) or not hashes_equal(git('show', commit+':'+rel), item['sha256']):
      raise ContractError('F64_SOURCE_PIN')
  actual = {p.relative_to(root).as_posix() for p in (root/'tools/cyberpilot/f64').glob('*.py')}
  if actual != {p for p in paths if p.startswith('tools/cyberpilot/f64/')}:
    raise ContractError('F64_SOURCE_PIN')
  proof = {'pre_holdout_commit': commit, 'source_manifest_sha256': hashlib.sha256(frozen).hexdigest(),
           'source_file_count': len(paths), 'source_and_tests_match_frozen_commit': True}
  _PROOFS[commit] = proof
  return proof


def proof_is_bound(proof):
  return type(proof) is dict and _PROOFS.get(proof.get('pre_holdout_commit')) is proof


def main():
  # Do not derive a seed during bootstrap. First bind source bytes to actual commit.
  argv = sys.argv[1:]
  proof = None
  if '--pre-holdout' in argv:
    i = argv.index('--pre-holdout')
    if i+1 >= len(argv):
      raise ContractError('F64_SOURCE_PIN')
    proof = verify_holdout_source(ROOT, argv[i+1])
  with isolation.Guard():
    from tools.cyberpilot.f64 import runner
    runner.main(argv, source_proof=proof)


if __name__ == '__main__':
  try:
    main()
  except Exception:
    print('F64_EXECUTION_BLOCKED', file=sys.stderr)
    raise SystemExit(1) from None
