"""Private namespaces for synthetic host tests, not vehicle endpoints."""

import os
import re
import stat
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

TOPICS = ('deviceState', 'selfdriveState', 'carState', 'managerState')


@dataclass(frozen=True)
class Namespace:
  prefix: str
  path: Path
  device: int
  inode: int


def validate_namespace(run: Namespace):
  if not re.fullmatch(r'cyberpilot_web_native_[0-9a-f]{32}', run.prefix):
    raise ValueError('unsafe_prefix')
  if os.environ.get('OPENPILOT_PREFIX') != run.prefix or 'CEREAL_FAKE' in os.environ:
    raise ValueError('namespace_environment_mismatch')
  info = run.path.lstat()
  if (not stat.S_ISDIR(info.st_mode) or info.st_mode & 0o777 != 0o700 or info.st_uid != os.getuid()
      or (info.st_dev, info.st_ino) != (run.device, run.inode) or run.path.name != 'msgq_' + run.prefix):
    raise ValueError('namespace_identity_mismatch')
  for child in run.path.iterdir():
    if child.name not in TOPICS or not stat.S_ISREG(child.lstat().st_mode):
      raise ValueError('unexpected_endpoint')


@contextmanager
def namespace(shm_root=Path('/dev/shm')):
  if 'OPENPILOT_PREFIX' in os.environ or 'CEREAL_FAKE' in os.environ:
    raise ValueError('existing_namespace_refused')
  root = shm_root.absolute()
  if root.resolve() != root:
    raise ValueError('symlink_namespace_root')
  prefix = 'cyberpilot_web_native_' + uuid.uuid4().hex
  path = root / ('msgq_' + prefix)
  path.mkdir(mode=0o700)
  info = path.lstat()
  run = Namespace(prefix, path, info.st_dev, info.st_ino)
  os.environ['OPENPILOT_PREFIX'] = prefix
  try:
    validate_namespace(run)
    yield run
  finally:
    try:
      validate_namespace(run)
      for child in path.iterdir():
        child.unlink()
      path.rmdir()
    finally:
      os.environ.pop('OPENPILOT_PREFIX', None)
