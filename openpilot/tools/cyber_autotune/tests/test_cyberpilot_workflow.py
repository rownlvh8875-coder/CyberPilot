import unittest
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[4]
WORKFLOW = ROOT / '.github/workflows/cyberpilot.yaml'


class TestCyberPilotWorkflow(unittest.TestCase):
  def text(self):
    self.assertTrue(WORKFLOW.is_file())
    return WORKFLOW.read_text()

  def test_branch_and_pull_request_triggers_are_present(self):
    text = self.text()
    self.assertIn('name: CyberPilot', text)
    self.assertIn('feature/cyber-autotune', text)
    self.assertIn('pull_request:', text)
    self.assertIn('workflow_dispatch:', text)
    self.assertIn('permissions:', text)
    self.assertIn('contents: read', text)

  def test_checkout_and_setup_are_reproducible(self):
    text = self.text()
    self.assertIn('actions/checkout@v7', text)
    self.assertIn('fetch-depth: 0', text)
    self.assertIn('submodules: recursive', text)
    self.assertIn('./tools/op.sh setup', text)
    self.assertIn('scons -j2', text)

  def test_required_cyberpilot_checks_are_enforced(self):
    text = self.text()
    required = (
      'tools/test_runner.py openpilot/tools/cyber_autotune/tests openpilot/selfdrive/controls/tests -j 1',
      'openpilot/selfdrive/test/process_replay/test_cyber_lateral_card_replay.py',
      'openpilot/selfdrive/test/process_replay/test_cyber_lateral_native_experiment.py',
      'ruff check',
      'tools/cyberpilot/check_publication.py --base origin/main',
      'docs/cyberpilot/policies',
      'docs/cyberpilot/changes',
    )
    for item in required:
      with self.subTest(item=item):
        self.assertIn(item, text)

  def test_privacy_only_commits_cannot_skip_workflow(self):
    # A structural guard, not a claim of GitHub workflow execution.
    self.assertIsNone(re.search(r'^\s+paths(?:-ignore)?:', self.text(), re.MULTILINE))

  def test_no_write_permissions_or_continue_on_error(self):
    text = self.text()
    self.assertNotIn('contents: write', text)
    self.assertNotIn('continue-on-error: true', text)
    self.assertNotIn('pull-requests: write', text)


if __name__ == '__main__':
  unittest.main()
