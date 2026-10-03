"""Isolated stdlib-only byte verifier. Never imports replay or decodes a log."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import stat
import sys


# Linux UAPI fcntl.h seal mask and command, independent of Python build exports.
GET_SEALS = 1034
REQUIRED_SEALS = 15
CHUNK_BYTES = 1024 * 1024
MAX_INPUT_BYTES = 512 * 1024 * 1024


def main():
  fd, size, expected = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
  if not 0 < size <= MAX_INPUT_BYTES:
    raise ValueError('INVALID_SIZE')
  status = dict(line.split(':', 1) for line in Path('/proc/self/status').read_text().splitlines() if ':' in line)
  if (os.getpid() != 1 or os.getppid() != 0 or int(status['CapEff'].strip(), 16) != 0 or
      int(status['CapBnd'].strip(), 16) != 0 or status['NoNewPrivs'].strip() != '1'):
    raise ValueError('ISOLATION_MISSING')
  if (Path('/mnt').exists() or Path('/dev/dxg').exists() or Path('/dev/bus').exists() or
      sorted(p.name for p in Path('/home').iterdir()) != ['private'] or list(Path('/dev/shm').iterdir())):
    raise ValueError('UNEXPECTED_HOST_EXPOSURE')
  interfaces = [line.split(':', 1)[0].strip() for line in Path('/proc/net/dev').read_text().splitlines()[2:]]
  if interfaces != ['lo']:
    raise ValueError('UNEXPECTED_NETWORK')
  for directory in ('/usr/bin', '/usr/lib/x86_64-linux-gnu', '/usr/lib/python3.12'):
    if not os.statvfs(directory).f_flag & os.ST_RDONLY:
      raise ValueError('WRITABLE_RUNTIME')
  info = os.fstat(fd)
  if not stat.S_ISREG(info.st_mode) or info.st_size != size or fcntl.fcntl(fd, GET_SEALS) != REQUIRED_SEALS:
    raise ValueError('INVALID_INPUT_SNAPSHOT')
  digest = hashlib.sha256()
  position = 0
  while position < size:
    block = os.pread(fd, min(CHUNK_BYTES, size - position), position)
    if not block:
      raise ValueError('SHORT_INPUT')
    digest.update(block)
    position += len(block)
  if digest.hexdigest() != expected or os.pread(fd, 1, size):
    raise ValueError('INPUT_HASH_MISMATCH')
  print(json.dumps({'status': 'SEALED_INPUT_VERIFIED', 'sha256': digest.hexdigest(), 'size_bytes': size,
                    'seals': REQUIRED_SEALS, 'isolation_checked': True, 'replay_executed': False,
                    'runtime_accepted': False, 'promotable': False}, sort_keys=True))


if __name__ == '__main__':
  main()
