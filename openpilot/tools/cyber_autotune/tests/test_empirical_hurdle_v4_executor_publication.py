"""Public V4 executor aggregate schema, no private values."""

import copy
import unittest
from tools.cyberpilot import build_hurdle_v4_executor as b


class TestPublication(unittest.TestCase):
  def test_contracts_and_privacy(self):
    rows = b.build()
    self.assertEqual(len(rows), 13)
    b.validate(rows)
    ready = rows[b.filename('executor-readiness')]
    self.assertFalse(ready['actual_execution_authorized'])
    self.assertEqual(ready['actual_private_numeric_access'], 0)
    self.assertEqual(ready['status'], 'V4_PRIVATE_EXECUTOR_IMPLEMENTATION_BLOCKED')

  def test_private_field_rejected(self):
    rows = b.build()
    for key in ('private_root', 'coefficients', 'threshold', 'normalizer_values', 'probabilities', 'raw_ticks', 'row_indices', 'gps'):
      with self.subTest(key=key):
        bad = copy.deepcopy(rows)
        bad[b.filename('executor-readiness')][key] = 'FORBIDDEN_SYNTHETIC_MUTATION'
        with self.assertRaises(ValueError):
          b.validate(bad)

  def test_frozen_numerics(self):
    rows = b.build()
    decision = rows[b.filename('executor-authorization-policy')]
    self.assertEqual(decision['policies'][b.PREFIX + 'fitting-policy-decision.json'], 'f63a046c8e40606921852e5709349b140d229cfc1714df97e837105826505268')
    self.assertFalse(decision['authorization_minting'])

  def test_no_false_readiness(self):
    rows = b.build(validation={'focused': {'exit_code': 1}}, reviews={'A': 'APPROVED', 'B': 'APPROVED'})
    self.assertEqual(rows[b.filename('executor-readiness')]['status'], 'V4_PRIVATE_EXECUTOR_IMPLEMENTATION_BLOCKED')
