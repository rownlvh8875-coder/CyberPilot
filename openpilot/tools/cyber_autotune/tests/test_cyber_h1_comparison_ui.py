"""Execute independently derived UI phase and response-race regressions in Node VM."""

from pathlib import Path
import subprocess
import unittest


class TestPairedUI(unittest.TestCase):
  def run_ui(self, name):
    root = Path(__file__).resolve().parent
    result = subprocess.run(
      ['node', str(root / 'h1_compare_ui_check.js'), str(root.parent / 'static/cyber_h1_compare.js'), name],
      capture_output=True,
      text=True,
      timeout=15,
      check=False,
    )
    self.assertEqual(result.returncode, 0, result.stderr)
    self.assertIn('PASS ' + name, result.stdout)

  def test_post_step_x_is_completion_not_capture(self):
    self.run_ui('phase')

  def test_reversed_campaign_responses_and_old_playback_rejected(self):
    self.run_ui('switch')

  def test_play_disabled_without_loaded_frames(self):
    self.run_ui('emptyplay')
