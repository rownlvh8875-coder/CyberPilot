"""Child-only source import context; not a concurrent parent-interpreter API."""
from contextlib import contextmanager
import sys
import tempfile


@contextmanager
def source_only_imports():
  # -B/dont_write_bytecode alone still READ timestamp/size-valid stale .pyc.
  # A fresh private prefix has no cached code; disabled writes keep it empty.
  previous = sys.pycache_prefix, sys.dont_write_bytecode
  with tempfile.TemporaryDirectory(prefix='cyber-native-source-') as directory:
    sys.pycache_prefix, sys.dont_write_bytecode = directory, True
    try:
      yield
    finally:
      sys.pycache_prefix, sys.dont_write_bytecode = previous
