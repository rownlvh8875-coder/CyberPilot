"""Portable read-only public device facts. No native/openpilot imports."""

import argparse
import datetime
import hashlib
import json
import os
import platform
import re
import stat
import subprocess
from pathlib import Path

MODEL_SOURCE = {
  'repository': 'rownlvh8875-coder/CyberPilot',
  'baseline_commit': '13d6929d95d2b600a234a29d9d68b59fa04b2d9a',
  'path': 'openpilot/common/hardware/comma/hardware.py',
  'symbol': 'get_device_type; HardwareComma device-code documentation',
  'sha256': 'd357b90f878ef7b8ea1df5a537cdf986df2243bc4b20b37c7ed88175020cadd8',
}
SELECTORS = ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_COMMON_DIR', 'GIT_INDEX_FILE', 'GIT_OBJECT_DIRECTORY',
             'GIT_ALTERNATE_OBJECT_DIRECTORIES', 'GIT_NAMESPACE', 'GIT_PREFIX')


def public_text(path):
  result = {'status': 'UNREADABLE', 'value': None, 'sha256': None, 'bytes_read': None}
  try:
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as stream:
      if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
        return result
      data = stream.read(4097)
    if len(data) > 4096:
      result['status'] = 'TOO_LARGE'
      return result
    text = data.decode('utf-8').strip('\x00')
    result.update(status='OBSERVED' if text else 'EMPTY', value=text or None,
                  sha256=hashlib.sha256(data).hexdigest(), bytes_read=len(data))
  except FileNotFoundError:
    result['status'] = 'MISSING'
  except (OSError, UnicodeError):
    pass
  return result


def marker(path):
  try:
    info = path.lstat()
    kind = 'regular_file' if stat.S_ISREG(info.st_mode) else 'symlink' if stat.S_ISLNK(info.st_mode) else 'other'
    return {'status': 'OBSERVED_METADATA_ONLY', 'kind': kind}
  except FileNotFoundError:
    return {'status': 'MISSING', 'kind': None}
  except OSError:
    return {'status': 'UNREADABLE', 'kind': None}


def source_metadata(source_root):
  result = {'status': 'NOT_PROVIDED', 'root': None, 'commit': None, 'branch': None,
            'role': 'observed_existing_checkout', 'working_tree_content_verified': False}
  if source_root is None:
    return result
  try:
    root = Path(source_root).resolve()
    result['root'] = str(root)
    if not root.is_dir():
      result['status'] = 'MISSING'
      return result
    if not (root / '.git').exists():
      result['status'] = 'NOT_REPOSITORY_ROOT'
      return result
  except (OSError, ValueError):
    result.update(status='UNAVAILABLE', root=None)
    return result
  env = {key: value for key, value in os.environ.items() if key not in SELECTORS}
  try:
    def git(*args):
      run = subprocess.run(['git', '--no-optional-locks', '-C', str(root), 'rev-parse', *args],
                           env=env, capture_output=True, text=True, check=True, timeout=2)
      return run.stdout.strip()
    top = Path(git('--show-toplevel')).resolve()
    if top != root:
      result['status'] = 'NOT_REPOSITORY_ROOT'
      return result
    commit = git('HEAD')
    branch = git('--abbrev-ref', 'HEAD')
    if not re.fullmatch(r'[0-9a-f]{40}|[0-9a-f]{64}', commit):
      raise ValueError('invalid_git_commit')
    result.update(status='OBSERVED_METADATA_ONLY', commit=commit, branch=branch[:256])
  except (OSError, ValueError, subprocess.SubprocessError):
    result['status'] = 'UNAVAILABLE'
  return result


def collect(root=Path('/'), source_root=None):
  root = Path(root).absolute()
  model = public_text(root / 'sys/firmware/devicetree/base/model')
  version = public_text(root / 'VERSION')
  code = model['value'].split('comma ')[-1] if model['status'] == 'OBSERVED' else None
  script = Path(__file__).resolve()
  return {
    'schema_version': 1,
    'status': 'OBSERVATION_ONLY_NOT_QUALIFICATION',
    'captured_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),  # noqa: UP017 - portable Python 3.8+
    'observation_scope': 'SYSTEM_ROOT' if root.resolve() == Path('/') else 'FILESYSTEM_FIXTURE',
    'probe_sha256': hashlib.sha256(script.read_bytes()).hexdigest(),
    'platform': {'system': platform.system(), 'machine': platform.machine(), 'python': platform.python_version()},
    'model': model, 'version_file': version, 'agnos_marker': marker(root / 'AGNOS'),
    'hardware_code_hint': code, 'product_hint': 'comma four' if code == 'mici' else None,
    'model_rule_authority': dict(MODEL_SOURCE),
    'source': source_metadata(source_root),
    'device_installation_qualified': False,
    'actual_activation_allowed': False,
    'vehicle_identity_observed': False,
    'scope_limit': 'Public local facts only; no attestation, build, deployment, vehicle or control qualification.',
  }


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--source-root', type=Path, help='optional exact existing checkout root; metadata only')
  args = parser.parse_args()
  print(json.dumps(collect(source_root=args.source_root), ensure_ascii=False, sort_keys=True, indent=2))


if __name__ == '__main__':
  main()
