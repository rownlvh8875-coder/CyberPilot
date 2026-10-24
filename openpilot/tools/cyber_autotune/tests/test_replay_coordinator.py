import copy
import json
import unittest
from unittest.mock import patch

from openpilot.tools.cyber_autotune import replay_coordinator
from openpilot.tools.cyber_autotune.replay_supervisor import BoundedOutcome
from openpilot.tools.cyber_autotune.tests import test_replay_admission as fixtures


class TestReplayCoordinator(unittest.TestCase):
  setUp = fixtures.TestReplayAdmission.setUp
  git = fixtures.TestReplayAdmission.git

  def run_probe(self, **kwargs):
    return replay_coordinator.run_input_probe(self.request, grants=(self.grant,), authority_sha256='a' * 64,
                                               timeout_s=2., **kwargs)

  def test_invalid_timeout_is_rejected_before_open(self):
    for value in (False, 0, -1, 61, float('nan'), float('inf')):
      with self.subTest(value=value), patch('os.open', side_effect=AssertionError('unexpected open')):
        with self.assertRaises(ValueError):
          replay_coordinator.run_input_probe(self.request, grants=(self.grant,), authority_sha256='a' * 64, timeout_s=value)

  def test_failed_process_never_returns_private_output_or_success(self):
    for status, rc in (('TIMEOUT', -9), ('OUTPUT_LIMIT', -9), ('CLEANUP_UNCONFIRMED', 0), ('EXITED', 7)):
      with self.subTest(status=status), patch.object(replay_coordinator, '_run_bounded',
                return_value=BoundedOutcome(status, rc, b'PRIVATE_SENTINEL', 100)):
        result = self.run_probe()
        self.assertEqual(result['status'], 'ISOLATED_INPUT_CHECK_FAILED')
        self.assertNotIn('PRIVATE_SENTINEL', json.dumps(result))
        self.assertIs(result['replay_allowed'], False)

  def test_response_must_match_hash_size_and_containment(self):
    good = {'status': 'SEALED_INPUT_VERIFIED', 'sha256': self.grant['sha256'], 'size_bytes': 3, 'seals': 15,
            'isolation_checked': True, 'replay_executed': False, 'runtime_accepted': False, 'promotable': False}
    for change in ({'sha256': '0' * 64}, {'size_bytes': 4}, {'size_bytes': True}, {'seals': 0},
                   {'isolation_checked': False}, {'replay_executed': True}, {'promotable': 0}, {'extra': 'field'}):
      response = dict(good, **change)
      with self.subTest(change=change), patch.object(replay_coordinator, '_run_bounded',
                return_value=BoundedOutcome('EXITED', 0, json.dumps(response).encode(), 100)):
        self.assertEqual(self.run_probe()['status'], 'ISOLATED_INPUT_CHECK_FAILED')

  def test_source_drift_during_execution_invalidates_result(self):
    before = copy.deepcopy(self.request)

    def drift(*args, **kwargs):
      (self.source / 'module.py').write_bytes(b'changed\n')
      return BoundedOutcome('EXITED', 7, b'error', 100)

    with patch.object(replay_coordinator, '_run_bounded', side_effect=drift), self.assertRaises(ValueError):
      self.run_probe()
    self.assertEqual(self.request, before)
