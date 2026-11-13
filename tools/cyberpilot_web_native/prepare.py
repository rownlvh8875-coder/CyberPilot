"""Exact external minimal msgq build for synthetic host-native qualification."""

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
from pathlib import Path

PROFILE = Path(__file__).with_name('dependencies.json')
ROOT = Path(__file__).resolve().parents[2]


def check_output_path(root: Path, output: Path) -> Path:
  path = output.absolute()
  if path.resolve() != path or path.exists() or path.is_relative_to(root.resolve()):
    raise ValueError('output_must_be_new_external_real_path')
  if any((p / '.git').exists() for p in path.parents):
    raise ValueError('output_inside_repository')
  return path


def check_gitlinks(root: Path) -> dict:
  profile = json.loads(PROFILE.read_text())
  for entry in profile.values():
    result = subprocess.run(['git', 'ls-tree', 'HEAD', entry['gitlink']], cwd=root, text=True, capture_output=True, timeout=5)
    fields = result.stdout.split()
    if result.returncode or fields != ['160000', 'commit', entry['commit'], entry['gitlink']]:
      raise ValueError('gitlink_profile_mismatch')
  return profile


def source_hashes(root: Path) -> dict:
  names = subprocess.check_output(['git', 'ls-files', '-z'], cwd=root).decode().split('\0')
  return {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in names if name and (root / name).is_file()}


def prepare(root: Path, output: Path):
  if platform.system() != 'Linux' or platform.machine() != 'x86_64' or sys.version_info[:2] != (3, 12):
    raise ValueError('qualification_requires_linux_x86_64_python312')
  profile = check_gitlinks(root)
  out = check_output_path(root, output)
  out.mkdir()

  def command(name, argv, cwd):
    env = {**os.environ, 'PATH': str(Path(sys.executable).parent) + os.pathsep + os.environ['PATH']}
    with (out / (name + '.log')).open('w') as stream:
      subprocess.run(argv, cwd=cwd, env=env, stdout=stream, stderr=subprocess.STDOUT, check=True, timeout=180)

  records = {}
  for name, entry in profile.items():
    dest = out / name
    dest.mkdir()
    command(name + '-init', ['git', 'init', '-q'], dest)
    command(name + '-fetch', ['git', 'fetch', '--depth=1', '--no-tags', entry['repository'], entry['commit']], dest)
    command(name + '-checkout', ['git', 'checkout', '--detach', '-q', 'FETCH_HEAD'], dest)
    actual = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=dest, text=True).strip()
    if actual != entry['commit']:
      raise ValueError('dependency_commit_mismatch')
    records[name] = {**entry, 'path': str(dest), 'tracked_source_sha256': source_hashes(dest)}
  command('msgq-build', [sys.executable, '-m', 'SCons', '--minimal', '-j2', 'msgq/ipc_pyx.so'], out / 'msgq')
  for name, entry in records.items():
    if source_hashes(out / name) != entry['tracked_source_sha256']:
      raise ValueError('native_build_changed_tracked_source')
  binary = out / 'msgq/msgq/ipc_pyx.so'
  receipt = {'status': 'PASS', 'scope': 'LINUX_X86_64_HOST_IPC_ONLY_NOT_COMMA4_BUILD', 'dependencies': records,
             'python': sys.version, 'platform': platform.platform(), 'binary_sha256': hashlib.sha256(binary.read_bytes()).hexdigest(),
             'compiler': subprocess.check_output(['g++', '--version'], text=True).splitlines()[0],
             'tracked_dependency_sources_unchanged': True, 'binary_reproducibility_claim': False}
  (out / 'BUILD_RECEIPT.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
  return receipt


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--output', type=Path, required=True)
  args = parser.parse_args()
  prepare(ROOT, args.output)
  print('Pinned host-native IPC build PASS; not a device build.')


if __name__ == '__main__':
  main()
