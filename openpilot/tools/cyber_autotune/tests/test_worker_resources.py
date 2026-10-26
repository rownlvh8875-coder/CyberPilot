import json
import subprocess
import sys
import unittest


class TestWorkerResources(unittest.TestCase):
  def test_caps_apply_only_in_fresh_worker_and_are_exact(self):
    import resource
    previous = resource.getrlimit(resource.RLIMIT_AS)
    code = '''
import json, os, resource
from openpilot.tools.cyber_autotune.worker_resources import apply_worker_limits
apply_worker_limits()
print(json.dumps([resource.getrlimit(resource.RLIMIT_AS), resource.getrlimit(resource.RLIMIT_CPU),
                  resource.getrlimit(resource.RLIMIT_CORE), os.environ['OPENBLAS_NUM_THREADS']]))
'''
    result = subprocess.run([sys.executable, '-c', code], capture_output=True, timeout=5.)
    self.assertEqual(result.returncode, 0, result.stderr)
    self.assertEqual(json.loads(result.stdout), [[2 * 1024 ** 3] * 2, [60] * 2, [0] * 2, '1'])
    self.assertEqual(resource.getrlimit(resource.RLIMIT_AS), previous)
