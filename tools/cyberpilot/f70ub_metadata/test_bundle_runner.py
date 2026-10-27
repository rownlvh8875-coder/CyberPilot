"""End-to-end tests of the standalone metadata bundle with inert copies."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent


class BundleRunnerTests(unittest.TestCase):
  def setUp(self):
    self.assertTrue((ROOT / 'verify_bundle.py').is_file(), 'Missing standalone bundle verifier')
    self.temp = tempfile.TemporaryDirectory()
    self.addCleanup(self.temp.cleanup)
    self.bundle = Path(self.temp.name) / 'bundle'
    self.bundle.mkdir()
    for name in ['source_boundary.py', 'verify_bundle.py']:
      shutil.copyfile(ROOT / name, self.bundle / name)
    shutil.copytree(ROOT / 'artifacts', self.bundle / 'artifacts')

  def run_bundle(self, output):
    return subprocess.run([sys.executable, '-I', '-S', '-B', str(self.bundle / 'verify_bundle.py'),
                           '--output-dir', str(output)], capture_output=True, text=True, check=False)

  def test_two_fresh_outputs_byte_identical_and_unknowns_preserved(self):
    first = Path(self.temp.name) / 'first'
    second = Path(self.temp.name) / 'second'
    for path in [first, second]:
      result = self.run_bundle(path)
      self.assertEqual(result.returncode, 0, result.stderr)
    a = {p.name: p.read_bytes() for p in first.iterdir()}
    b = {p.name: p.read_bytes() for p in second.iterdir()}
    self.assertEqual(a, b)
    self.assertEqual(len(a), 6)
    self.assertIn(b'"context_instance_resolved":false', a['boundary_result.json'])
    self.assertIn(b'"r_budget_resolved":false', a['boundary_result.json'])

  def test_existing_output_not_overwritten(self):
    output = Path(self.temp.name) / 'keep'
    output.mkdir()
    marker = output / 'marker'
    marker.write_bytes(b'unchanged')
    self.assertNotEqual(self.run_bundle(output).returncode, 0)
    self.assertEqual(marker.read_bytes(), b'unchanged')
    self.assertEqual(list(output.iterdir()), [marker])

  def test_tampered_metadata_rejected_before_output_directory_created(self):
    path = self.bundle / 'artifacts/static_metadata_envelope.json'
    path.write_bytes(path.read_bytes().replace(b'"instance_resolved":false', b'"instance_resolved":true'))
    output = Path(self.temp.name) / 'out'
    result = self.run_bundle(output)
    self.assertNotEqual(result.returncode, 0)
    self.assertFalse(output.exists())

  def test_symlink_artifact_rejected(self):
    path = self.bundle / 'artifacts/static_metadata_envelope.json'
    path.unlink()
    path.symlink_to(self.bundle / 'artifacts/synthetic_descriptor_envelope.json')
    output = Path(self.temp.name) / 'out'
    self.assertNotEqual(self.run_bundle(output).returncode, 0)
    self.assertFalse(output.exists())


if __name__ == '__main__':
  unittest.main(verbosity=2)
