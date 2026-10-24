"""E dependency preparation and runtime audit; no scientific input or authority.

Public Python/NumPy dependencies load before source access. Their import caches
must be ready before the runtime no-directory-discovery audit is installed.
This audit is defense in depth, not a complete OS sandbox. Exact input opens
remain guarded by the independently pinned openat2/member reader.
"""

import os
import pickle
from unittest.mock import patch

import numpy as np


def warm_dependencies():
  # NumPy unique/union lazily imports masked-array helpers, whose import finder
  # scans the public installed package directory. No private inputs are used.
  import numpy.ma  # noqa: F401

  _ = np.linalg.solve, np.linalg.lstsq, np.linalg.pinv


def trap_deserialization(stack, forbidden):
  for module, names in ((pickle, ('load', 'loads', 'Unpickler', 'dump', 'dumps')), (np, ('load', 'save'))):
    for name in names:
      stack.enter_context(patch.object(module, name, forbidden))


class RuntimeFirewall:
  def __init__(self):
    self.active, self.attempts, self.writing_output = True, 0, False
    self.blocked_events = []

  def __call__(self, event, args):
    if not self.active:
      return
    blocked = event in ('os.listdir', 'os.scandir', 'subprocess.Popen', 'os.system', 'os.remove', 'os.rename', 'os.rmdir', 'os.mkdir')
    blocked |= event == 'import' and (args[0].split('.')[0] in ('pickle', 'sklearn', 'scipy', 'torch') or 'logreader' in args[0])
    if event == 'open' and len(args) >= 3 and type(args[2]) is int:
      writing = bool(args[2] & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
      blocked |= writing and not self.writing_output
      if isinstance(args[0], str) and args[0].startswith(('/mnt/e/', '/mnt/d/', '/mnt/c/')):
        blocked = True
    if blocked:
      self.attempts += 1
      self.blocked_events.append(event)  # Event names only; never paths/data.
      raise ValueError('E_FORBIDDEN_OPERATION_ATTEMPT')
