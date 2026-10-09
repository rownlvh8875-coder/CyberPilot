from copy import deepcopy
from dataclasses import replace
import unittest

from openpilot.tools.cyber_autotune import smoothness_closed_loop as s
from openpilot.tools.cyber_autotune import candidate_architecture as a
from openpilot.tools.cyber_autotune.smoothness_v0_screen import STAGES
from openpilot.tools.cyber_autotune.trajectory_v0_screen import scenarios
from openpilot.tools.cyber_autotune.smoothness_v0_publication import load as historical


class TestLoopIsolation(unittest.TestCase):
  def test_components_distinct(self):
    x, y = s.Arm('gentle_left', s.ARMS[0]), s.Arm('gentle_left', s.ARMS[2])
    s.assert_isolated([x, y])
    for name in ('core', 'governor', 'state', 'owner'):
      self.assertIsNot(getattr(x, name), getattr(y, name))
    self.assertIsNot(x.core.controller.pid, y.core.controller.pid)
    self.assertIsNot(x.state.command_history, y.state.command_history)

  def test_shared_arm_rejected(self):
    x = s.Arm('straight', s.ARMS[0])
    with self.assertRaises(ValueError):
      s.assert_isolated([x, x])

  def test_shared_pid_rejected(self):
    x, y = s.Arm('straight', s.ARMS[0]), s.Arm('straight', s.ARMS[1])
    y.core.controller.pid = x.core.controller.pid
    with self.assertRaises(ValueError):
      s.assert_isolated([x, y])

  def test_cross_arm_feedback_rejected(self):
    x, y = s.Arm('straight', s.ARMS[0]), s.Arm('straight', s.ARMS[2])
    with self.assertRaises(ValueError):
      y._accept_feedback(x._feedback())

  def test_future_feedback_rejected(self):
    x = s.Arm('straight', s.ARMS[0])
    with self.assertRaises(ValueError):
      x._accept_feedback(replace(x._feedback(), index=1))

  def test_stale_feedback_rejected(self):
    x = s.Arm('straight', s.ARMS[0])
    token = x._feedback()
    x.advance(0)
    with self.assertRaises(ValueError):
      x._accept_feedback(token)

  def test_same_value_foreign_state_rejected(self):
    x = s.Arm('straight', s.ARMS[0])
    with self.assertRaises(ValueError):
      x._accept_feedback(replace(x._feedback(), state=replace(x.state)))

  def test_off_by_one_rejected(self):
    x = s.Arm('straight', s.ARMS[0])
    with self.assertRaises(ValueError):
      x.advance(1)

  def test_unknown_arm_rejected(self):
    with self.assertRaises(ValueError):
      s.Arm('straight', 'TA-B')

  def test_unknown_scenario_rejected(self):
    with self.assertRaises(ValueError):
      s.Arm('best_new_case', s.ARMS[0])

  def test_no_external_feedback_api(self):
    x = s.Arm('straight', s.ARMS[2])
    with self.assertRaises(TypeError):
      x.advance(0, actual_curvature_1pm=1.)

  def test_mutated_mode_rejected(self):
    x = s.Arm('straight', s.ARMS[2])
    x.governor._mode = 'SG_DISABLED'
    with self.assertRaises(ValueError):
      x.advance(0)

  def test_composition_denied(self):
    with self.assertRaises(ValueError):
      s.authorize('DEVELOPMENT_SCREEN', composition=True)

  def test_ta_denied(self):
    with self.assertRaises(ValueError):
      s.authorize('DEVELOPMENT_SCREEN', ta_enabled=True)

  def test_search_denied(self):
    with self.assertRaises(ValueError):
      s.authorize('SEARCH')

  def test_evaluation_denied(self):
    with self.assertRaises(ValueError):
      s.authorize('FROZEN_EVALUATION')


class TestClosedLoopTraces(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.b = s.run_arm('high_speed', s.ARMS[0])
    cls.c = s.run_arm('high_speed', s.ARMS[1])
    cls.g = s.run_arm('high_speed', s.ARMS[2])
    cls.driver = s.run_arm('driver_events', s.ARMS[2])

  def test_alias_full_trace(self):
    self.assertEqual(self.b, self.c)

  def test_repeat_full_trace(self):
    self.assertEqual(self.g, s.run_arm('high_speed', s.ARMS[2]))

  def test_own_pre_feedback(self):
    for rows in (self.b, self.g):
      self.assertEqual(rows[0]['input']['actual_curvature_1pm'], 0.)
      for prev, row in zip(rows, rows[1:], strict=False):
        self.assertEqual(row['input']['actual_curvature_1pm'], prev['curvature'])

  def test_feedback_not_shared(self):
    self.assertNotEqual([r['input']['actual_curvature_1pm'] for r in self.b], [r['input']['actual_curvature_1pm'] for r in self.g])

  def test_core_not_frozen_replay(self):
    self.assertNotEqual([r['pre'] for r in self.b], [r['pre'] for r in self.g])

  def test_no_off_by_one_output_feedback(self):
    self.assertTrue(any(r['input']['actual_curvature_1pm'] != r['curvature'] for r in self.g))

  def test_plant_single_queue(self):
    for r in self.g:
      self.assertEqual(len(r['plant_state_before']['command_history']), 2)
      self.assertEqual(len(r['plant_state_after']['command_history']), 2)
      self.assertEqual(r['trace']['physical_delay_owner'], 'PLANT')

  def test_exact_plant_reconstruction(self):
    s.validate_trace('high_speed', self.g, s.ARMS[2])

  def test_trace_timing_tamper_rejected(self):
    rows = deepcopy(self.g)
    index = next(i for i, r in enumerate(rows) if r['input']['actual_curvature_1pm'] != r['curvature'])
    rows[index]['input']['actual_curvature_1pm'] = rows[index]['curvature']
    with self.assertRaises(ValueError):
      s.validate_trace('high_speed', rows, s.ARMS[2])

  def test_trace_source_tamper_rejected(self):
    rows = deepcopy(self.g)
    rows[5]['trace']['core_source_sha256'] = '0' * 64
    with self.assertRaises(ValueError):
      s.validate_trace('high_speed', rows, s.ARMS[2])

  def test_no_authority_expansion(self):
    self.assertTrue(all(abs(r['requested']) <= abs(r['pre']) for r in self.g))

  def test_state_is_only_last_command(self):
    self.assertTrue(all(len(r['trace']['governor_state']) <= 1 for r in self.g))

  def test_exact_inactive_zero(self):
    rows = [r for r in self.driver if not r['input']['active']]
    self.assertTrue(rows)
    self.assertTrue(all(r['pre'] == r['requested'] == 0. and r['trace']['state_after'] is None for r in rows))

  def test_pressed_passthrough(self):
    self.assertTrue(all(r['pre'] == r['requested'] for r in self.driver if r['input']['steering_pressed']))

  def test_release_reengagement_fresh(self):
    rows = [r for r in self.driver if any(e in r['reset_events'] for e in ('RELEASE', 'REENGAGEMENT'))]
    self.assertEqual(len(rows), 2)
    self.assertTrue(all(r['requested'] == r['pre'] and r['trace']['state_after'] == r['pre'] for r in rows))

  def test_new_scenario_no_tail(self):
    x = s.Arm('straight', s.ARMS[2])
    self.assertEqual(x.advance(0)['requested'], 0.)

  def test_original_scenarios(self):
    self.assertEqual(len(scenarios()), 11)
    self.assertEqual(len(self.g), 800)

  def test_baseline_matches_historical_trace_without_rerun(self):
    old = historical()['results']['scenarios']
    ref = next(r for r in old if r['scenario'] == 'high_speed')
    stages = [{k: r[k] for k in STAGES} for r in self.b]
    self.assertEqual(a.hash_object(stages), ref['baseline_generation_plant_sha256'])

  def test_sg_config_receipt_unchanged(self):
    self.assertEqual(s.policy()['policy']['sg_config_sha256'], s.frozen()['config']['receipt_sha256'])

  def test_fabricated_native_state_rejected(self):
    rows = deepcopy(self.g)
    rows[20]['native_state_after']['pid'][1] += .1
    with self.assertRaises(ValueError):
      s.validate_trace('high_speed', rows, s.ARMS[2])

  def test_candidate_cannot_validate_disabled_trace(self):
    with self.assertRaises(ValueError):
      s.validate_trace('high_speed', self.b, s.ARMS[2])

  def test_native_pre_state_rejected(self):
    rows = deepcopy(self.g)
    rows[20]['native_state_before']['sat_time'] += .1
    with self.assertRaises(ValueError):
      s.validate_trace('high_speed', rows, s.ARMS[2])

  def test_core_command_not_arbitrary(self):
    rows = deepcopy(self.g)
    rows[20]['pre'] = .5
    with self.assertRaises(ValueError):
      s.validate_trace('high_speed', rows, s.ARMS[2])

  def test_first_feedback_after_first_plant_divergence(self):
    first_post = next(i for i, (b, g) in enumerate(zip(self.b, self.g, strict=True)) if b['curvature'] != g['curvature'])
    first_pre = next(i for i, (b, g) in enumerate(zip(self.b, self.g, strict=True))
                     if b['input']['actual_curvature_1pm'] != g['input']['actual_curvature_1pm'])
    self.assertEqual(first_pre, first_post + 1)

  def test_single_delay_first_application(self):
    shape = next(i for i, g in enumerate(self.g) if g['pre'] != g['requested'])
    applied = next(i for i, (b, g) in enumerate(zip(self.b, self.g, strict=True)) if b['applied'] != g['applied'])
    self.assertEqual(applied, shape + 2)

  def test_core_divergence_not_before_feedback(self):
    feedback = next(i for i, (b, g) in enumerate(zip(self.b, self.g, strict=True))
                    if b['input']['actual_curvature_1pm'] != g['input']['actual_curvature_1pm'])
    requested = next(i for i, (b, g) in enumerate(zip(self.b, self.g, strict=True)) if b['pre'] != g['pre'])
    self.assertGreaterEqual(requested, feedback)

  def test_mutating_one_arm_does_not_change_other(self):
    x, y = s.Arm('straight', s.ARMS[0]), s.Arm('straight', s.ARMS[2])
    before = s.native_state(y.core)
    x.core.controller.pid.i = .3
    x.governor._last = .2
    x.state = replace(x.state, command_history=(.3, .4))
    self.assertEqual(s.native_state(y.core), before)
    self.assertIsNone(y.governor._last)
    self.assertEqual(y.state.command_history, (0., 0.))

  def test_unknown_exogenous_field_rejected(self):
    x = s.Arm('straight', s.ARMS[2])
    x.frames[0]['modelV2'] = 1.
    with self.assertRaises(ValueError):
      x.advance(0)

  def test_json_roundtrip_valid_trace(self):
    import json
    s.validate_trace('high_speed', json.loads(json.dumps(self.g)), s.ARMS[2])

  def test_phase_binding(self):
    rows = deepcopy(self.g)
    rows[20]['phase'] = 'APEX'
    with self.assertRaises(ValueError):
      s.validate_trace('high_speed', rows, s.ARMS[2])

  def test_reset_metric_binding(self):
    rows = deepcopy(self.g)
    rows[20]['reset_events'] = ['RELEASE']
    with self.assertRaises(ValueError):
      s.validate_trace('high_speed', rows, s.ARMS[2])

  def test_saturation_metric_binding(self):
    rows = deepcopy(self.g)
    rows[20]['saturation'] = not rows[20]['saturation']
    with self.assertRaises(ValueError):
      s.validate_trace('high_speed', rows, s.ARMS[2])

  def test_unknown_trace_field_rejected(self):
    rows = deepcopy(self.g)
    rows[20]['future_truth'] = .3
    with self.assertRaises(ValueError):
      s.validate_trace('high_speed', rows, s.ARMS[2])
