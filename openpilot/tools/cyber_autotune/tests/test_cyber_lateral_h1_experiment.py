"""Actual offline baseline integration and aggregate publication tests."""

from copy import deepcopy
import tempfile
import unittest
from unittest.mock import patch

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import cyber_lateral_h1_contract as c
from openpilot.tools.cyber_autotune import cyber_lateral_h1_experiment as e
from openpilot.tools.cyber_autotune import cyber_lateral_h1_producer as h
from openpilot.tools.cyber_autotune import cyber_lateral_h1_inspector as view


class TestOfflineH1(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.first_rows, cls.first = e.run_once()
    cls.second_rows, cls.second = e.run_once()
    cls.plain_rows, _ = e.run_once(observe=False)

  def test_repeat_package_bytes(self):
    self.assertEqual(p.canonical(self.first), p.canonical(self.second))

  def test_observer_no_effect(self):
    self.assertEqual(p.canonical(self.first_rows), p.canonical(self.plain_rows))
    self.assertEqual(p.canonical(self.first_rows), p.canonical(self.second_rows))

  def test_full_horizon(self):
    self.assertEqual(self.first['row_count'], 800)

  def test_actual_native_input_binding(self):
    for source, row in zip(self.first_rows, self.first['rows'], strict=True):
      self.assertEqual(row['native_input_sha256'], source['feedback']['native_input_sha256'])
      self.assertEqual(row['consumed_input_snapshot']['native_input'], source['input'])

  def test_controller_stages(self):
    for source, row in zip(self.first_rows, self.first['rows'], strict=True):
      self.assertEqual(row['signals']['controller_limited_torque'], source['pre'])
      self.assertEqual(row['signals']['final_requested_torque'], source['requested'])
      self.assertEqual(row['signals']['applied_torque'], source['applied'])

  def test_pre_step_feedback(self):
    for source, row in zip(self.first_rows, self.first['rows'], strict=True):
      self.assertEqual(row['signals']['actual_curvature'], source['input']['actual_curvature_1pm'])
      self.assertEqual(row['plant_output']['curvature'], source['curvature'])
      self.assertLess(row['decision_time_ns'], row['plant_output']['state_time_ns'])

  def test_interventions_observed(self):
    events = {row['event'] for row in self.first['rows']}
    self.assertTrue({'SCENARIO_BOUNDARY', 'INACTIVE', 'STEERING_PRESSED', 'RELEASE', 'REENGAGEMENT'} <= events)

  def test_config_exact(self):
    self.assertEqual(self.first['configs'], self.second['configs'])

  def test_source_policy_exact(self):
    self.assertEqual(self.first['policy'], c.policy())

  def test_fidelity(self):
    self.assertEqual(self.first['binding']['tier'], c.TIER)
    self.assertFalse(self.first['production_authority'])
    self.assertFalse(self.first['holdout_opener_implemented'])
    self.assertEqual(self.first['opening_count'], 0)
    self.assertEqual(self.first['holdout_opening'], 'CLOSED')

  def test_inspector_aggregate_only(self):
    result = view.aggregate(self.first)
    self.assertNotIn('rows', result)
    self.assertNotIn('signals', result)
    self.assertEqual(result['visual_readiness'], 'VISUAL_FRAME_CONVERSION_PARTIAL')

  def test_inspector_no_raw_reader(self):
    with tempfile.TemporaryDirectory() as folder, patch.object(p, 'inventory', side_effect=AssertionError('RAW_READER_FORBIDDEN')):
      h.persist(folder, self.first)
      self.assertEqual(view.inspect(folder)['row_count'], 800)

  def test_immutability_after_inspection(self):
    before = p.canonical(self.first)
    view.aggregate(self.first)
    self.assertEqual(p.canonical(self.first), before)

  def test_package_metadata_drift(self):
    bad = deepcopy(self.first)
    bad['opening_count'] = 1
    with self.assertRaises(ValueError):
      h.verify_package(bad)

  def test_saved_policy_drift_rejected_before_execution(self):
    from unittest.mock import Mock

    with tempfile.TemporaryDirectory() as folder:
      frozen = c.policy()
      changed = deepcopy(frozen)
      changed['source_sha256'] = '0' * 64
      with patch.object(c, 'policy', side_effect=[frozen, changed]), patch.object(e, 'run_once', Mock(side_effect=AssertionError('EXECUTION_AFTER_DRIFT'))):
        with self.assertRaisesRegex(ValueError, 'H1_SAVED_POLICY_DRIFT'):
          e.execute(folder)
