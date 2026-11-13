import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.cyberpilot_web_native.verify import verification_environment


class SdkEnvironmentTests(unittest.TestCase):
  def test_composed_project_resolves_installed_sdk_without_own_venv(self):
    with tempfile.TemporaryDirectory() as directory:
      project = Path(directory)
      (project / 'pyproject.toml').write_text('[project]\nname="isolated-sdk-consumer"\nversion="0.0.0"\nrequires-python=">=3.12,<3.13"\n')
      source = project / 'sample.py'
      source.write_text('import Cython\n')
      result = subprocess.run([sys.executable, '-m', 'ty', 'check', '--project', str(project), str(source)],
                              env=verification_environment(project), capture_output=True, text=True, timeout=10)
      self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
