"""Execute actual isolated observer seam with stdlib synthetic inputs.

AST extraction avoids native imports, not their behavior: these tests DO NOT
execute MPC, stock arbitration, publish or LongControl, and cannot prove parity.
"""
import ast
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from openpilot.selfdrive.controls.lib.cyber_long.policy import CyberLongPolicy
from openpilot.selfdrive.controls.lib.cyber_long.types import (
  CyberLongConfig, CyberLongMode, LongContext, ParameterBinding, StockCandidate,
)


class SyntheticSubMaster:
  def __init__(self):
    self.logMonoTime = {'modelV2': 100, 'carState': 90, 'radarState': 80}
    self.data = {
      'carState': types.SimpleNamespace(aEgo=0., brakePressed=False, gasPressed=False),
      'carControl': types.SimpleNamespace(longActive=True),
      'controlsState': types.SimpleNamespace(forceDecel=False),
      'selfdriveState': types.SimpleNamespace(personality='standard'),
    }
    self.valid = True

  def __getitem__(self, name):
    return self.data[name]

  def all_checks(self):
    return self.valid


class TestCyberLongBoundary(unittest.TestCase):
  def setUp(self):
    path = Path(__file__).parents[1] / 'lib/longitudinal_planner.py'
    tree = ast.parse(path.read_text())
    planner = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'LongitudinalPlanner')
    methods = [node for node in planner.body if isinstance(node, ast.FunctionDef) and node.name == '_observe_stock']
    self.assertEqual(len(methods), 1, 'Production observer seam is not implemented')
    namespace = {
      'CyberLongMode': CyberLongMode, 'CyberLongPolicy': CyberLongPolicy,
      'LongContext': LongContext, 'StockCandidate': StockCandidate,
    }
    exec(compile(ast.Module(body=methods, type_ignores=[]), str(path), 'exec'), namespace)
    self.config = CyberLongConfig(mode=CyberLongMode.OBSERVE_ONLY)
    self.owner = types.SimpleNamespace(
      cyber_long_config=self.config, cyber_long_policy=CyberLongPolicy(self.config), cyber_long_fault=None,
      cyber_long_binding=ParameterBinding(vehicle='synthetic-car', configuration_epoch=0),
    )
    self.invoke = lambda sm, candidates: namespace['_observe_stock'](self.owner, sm, candidates, False, 10., 12.)

  def test_snapshot_does_not_mutate_candidates_or_return_authority(self):
    candidates = [(-0.4, 'lead0', False), (0.2, 'cruise', True)]
    self.assertIsNone(self.invoke(SyntheticSubMaster(), candidates))
    self.assertEqual(candidates, [(-0.4, 'lead0', False), (0.2, 'cruise', True)])
    observation = self.owner.cyber_long_policy.last_observation
    self.assertEqual(observation.winner_accel_mps2, -0.4)
    self.assertTrue(observation.stock_should_stop)
    self.assertFalse(observation.provenance_complete)
    candidates.clear()
    self.assertEqual(len(observation.context.candidates), 2)

  def test_disabled_never_reads_observer_inputs(self):
    self.owner.cyber_long_config = CyberLongConfig()
    self.owner.cyber_long_policy = CyberLongPolicy(self.owner.cyber_long_config)
    # A SubMaster-like object with no fields is safe only if the seam bypasses it.
    self.assertIsNone(self.invoke(object(), []))
    self.assertIsNone(self.owner.cyber_long_policy.last_observation)

  def test_observer_failure_clears_diagnostic_without_mutating_candidates(self):
    candidates = [(-0.4, 'lead0', False), (0.2, 'cruise', True)]
    self.invoke(SyntheticSubMaster(), candidates)
    with patch.object(self.owner.cyber_long_policy, 'observe', side_effect=RuntimeError('synthetic fault')):
      self.assertIsNone(self.invoke(SyntheticSubMaster(), candidates))
    self.assertEqual(candidates, [(-0.4, 'lead0', False), (0.2, 'cruise', True)])
    self.assertIsNone(self.owner.cyber_long_policy.last_observation)
    self.assertEqual(self.owner.cyber_long_fault, 'RuntimeError')

  def test_malformed_observation_inputs_do_not_escape_to_stock_caller(self):
    self.invoke(SyntheticSubMaster(), [(-0.4, 'lead0', False)])
    self.assertIsNone(self.invoke(object(), [(-0.4, 'lead0', False)]))
    self.assertIsNone(self.owner.cyber_long_policy.last_observation)
    self.assertIsNotNone(self.owner.cyber_long_fault)

  def test_observer_fault_does_not_turn_duplicate_or_reversed_frames_fresh(self):
    sm = SyntheticSubMaster()
    candidates = [(-0.4, 'lead0', False)]
    self.invoke(sm, candidates)
    sm.logMonoTime['modelV2'] = 110
    with patch.object(self.owner.cyber_long_policy, 'observe', side_effect=RuntimeError('synthetic fault')):
      self.invoke(sm, candidates)
    self.assertIsNone(self.owner.cyber_long_policy.last_observation)
    for timestamp in (100, 99, 110, 110):
      sm.logMonoTime['modelV2'] = timestamp
      self.invoke(sm, candidates)
      self.assertIsNone(self.owner.cyber_long_policy.last_observation)
    sm.logMonoTime['modelV2'] = 111
    self.invoke(sm, candidates)
    self.assertEqual(self.owner.cyber_long_policy.last_observation.context.model_mono_time_ns, 111)


if __name__ == '__main__':
  unittest.main()
