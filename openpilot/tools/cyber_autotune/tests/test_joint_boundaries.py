"""Malformed result shapes must become fixed failure, not leak exceptions."""
import copy
import unittest
from unittest.mock import patch

from openpilot.tools.cyber_autotune import joint_continuity as api
from openpilot.tools.cyber_autotune.native_protocol import canonical
from openpilot.tools.cyber_autotune.native_runner import ProcessOutcome
from openpilot.tools.cyber_autotune.tests.test_joint_continuity import pair_fixture


class TestJointBoundaries(unittest.TestCase):
  def setUp(self):
    self.request = api.build_request(pair_fixture(), [2, 3, 6])
    self.valid = api.execute_experiment(self.request)

  def test_wrong_arm_types_and_missing_state_are_rejected_by_public_validator(self):
    for axis in ('lateral', 'longitudinal'):
      for arm in ('baseline', 'candidate'):
        for value in ([], None, 'PRIVATE_SENTINEL', 1, True, {}):
          result = copy.deepcopy(self.valid)
          result['axes'][axis][arm] = value
          with self.subTest(axis=axis, arm=arm, value=type(value)), self.assertRaises(ValueError):
            api.validate_response(self.request, result)

  def test_supervisor_never_exposes_malformed_arm_exceptions(self):
    for axis in ('lateral', 'longitudinal'):
      result = copy.deepcopy(self.valid)
      result['axes'][axis]['candidate'] = 'PRIVATE_SENTINEL'
      with self.subTest(axis=axis), patch.object(api, '_run_process', return_value=ProcessOutcome('EXITED', 0, canonical(result), 1)):
        receipt = api.run_experiment(self.request, timeout_s=5.)
        self.assertEqual(receipt['status'], 'INVALID_RESPONSE')
        self.assertNotIn('axes', receipt)
        self.assertNotIn(b'PRIVATE_SENTINEL', canonical(receipt))


if __name__ == '__main__':
  unittest.main()
