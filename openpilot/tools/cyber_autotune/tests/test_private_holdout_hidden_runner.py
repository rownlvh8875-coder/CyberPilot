from pathlib import Path
import tempfile
import unittest

from openpilot.tools.cyber_autotune import private_holdout_contract as h
from openpilot.tools.cyber_autotune.tests.test_private_holdout_contract import setup_package
from openpilot.tools.cyber_autotune.tests.test_private_holdout_hidden import prediction
from openpilot.tools.cyber_autotune.tests.test_private_pixel_execution import SHA, STAMP


class TestHiddenRunner(unittest.TestCase):
  def setUp(self):
    try:
      from openpilot.tools.cyber_autotune import private_holdout_hidden_runner as runner
      from openpilot.tools.cyber_autotune import private_holdout_hidden as hidden
    except ImportError:
      self.fail('Isolated frozen hidden detector runner is not implemented')
    self.runner, self.hidden = runner, hidden
    self.temp = tempfile.TemporaryDirectory(dir=Path.home())
    self.addCleanup(self.temp.cleanup)
    self.raw = Path(self.temp.name) / 'raw'
    self.raw.mkdir()
    self.output = Path(self.temp.name) / 'hidden'
    _, _, self.package = setup_package(self.raw)
    h.write_immutable(self.raw / 'materialization.json', self.package)
    self.auth = hidden.authorize(self.package, SHA[:40], STAMP, acknowledged=True)

  def test_image_sha_mismatch_fail_closed(self):
    im = self.package['images'][0]
    (self.raw / 'images' / (im['sample_id'] + '.png')).write_bytes(b'corrupt')
    with self.assertRaises(ValueError):
      self.runner.read_image(self.raw, self.package, self.auth, 0)

  def test_symlink_image_rejected(self):
    im = self.package['images'][0]
    p = self.raw / 'images' / (im['sample_id'] + '.png')
    p.unlink()
    p.symlink_to(self.raw / 'materialization.json')
    with self.assertRaises((ValueError, OSError)):
      self.runner.read_image(self.raw, self.package, self.auth, 0)

  def test_without_authority_no_frame_inference(self):
    calls = []
    with self.assertRaises(ValueError):
      self.runner.run_engine(self.raw, self.output, lambda b: calls.append(b), lambda: None, SHA[:40], acknowledge=False)
    self.assertEqual(calls, [])

  def test_twice_exact_inference_and_restart_zero_new(self):
    calls = []

    def engine(data):
      calls.append(len(data))
      return prediction()

    result = self.runner.run_engine(self.raw, self.output, engine, lambda: None, SHA[:40], acknowledge=True)
    self.assertEqual(len(calls), 120)
    self.assertEqual(result['processed'], 60)
    calls.clear()
    second = self.runner.run_engine(self.raw, self.output, engine, lambda: None, SHA[:40], acknowledge=True)
    self.assertEqual(calls, [])
    self.assertEqual(second['reused'], 60)

  def test_corrupt_cached_row_rejected_without_reinference(self):
    self.runner.run_engine(self.raw, self.output, lambda b: prediction(), lambda: None, SHA[:40], acknowledge=True)
    p = next((self.output / 'rows').glob('*.json'))
    p.write_bytes(b'{}')
    calls = []
    with self.assertRaises(ValueError):
      self.runner.run_engine(self.raw, self.output, lambda b: calls.append(b), lambda: None, SHA[:40], acknowledge=True)
    self.assertEqual(calls, [])

  def test_runtime_guard_failure_prevents_open(self):
    def guard():
      raise ValueError('runtime drift')

    calls = []
    with self.assertRaises(ValueError):
      self.runner.run_engine(self.raw, self.output, lambda b: calls.append(b), guard, SHA[:40], acknowledge=True)
    self.assertEqual(calls, [])
