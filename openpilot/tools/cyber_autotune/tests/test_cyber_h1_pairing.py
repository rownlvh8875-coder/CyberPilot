"""Frozen two-arm causal pairing boundaries; no real logs."""

from dataclasses import asdict
import unittest

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import cyber_h1_pairing as q
from openpilot.tools.cyber_autotune import cyber_h1_pair_producer as producer
from openpilot.tools.cyber_autotune import cyber_lateral_h1_producer as h
from openpilot.tools.cyber_autotune.tests.h1_pair_fixture import pairs


class TestPairing(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.pairs = pairs()

  def changed(self, kind='SG_A', arm=1):
    return h.clone(self.pairs[kind][arm])

  def reseal(self, package):
    for row in package['rows']:
      row['row_sha256'] = h.row_sha(row)
    package['trace_sha256'] = p.sha(p.canonical(package['rows']))
    package['row_digest_set_sha256'] = p.sha(p.canonical([r['row_sha256'] for r in package['rows']]))
    package['snapshot_set_sha256'] = p.sha(p.canonical([r['consumed_input_snapshot_sha256'] for r in package['rows']]))
    return q.verify(q.seal({k: v for k, v in package.items() if k != 'receipt_sha256'}))

  def test_two_separate_campaigns_exact_pair(self):
    for kind, packages in self.pairs.items():
      pair = q.pair(*packages)
      self.assertEqual(pair['sample_count'], 800)
      self.assertEqual(pair['baseline_arm'], 'UPSTREAM_BASELINE')
      self.assertEqual(pair['candidate_arm'], q.CAMPAIGNS[kind][1])
      self.assertEqual(pair['historical_verdict'], q.CAMPAIGNS[kind][2])
      self.assertFalse(pair['composition_authorized'])
      self.assertFalse(pair['qualification_allowed'])

  def test_distinct_identity_even_when_commands_equal(self):
    for packages in self.pairs.values():
      self.assertNotEqual(packages[0]['configs'][0]['process_epoch'], packages[1]['configs'][0]['process_epoch'])
      self.assertNotEqual(packages[0]['configs'][0]['config_sha256'], packages[1]['configs'][0]['config_sha256'])
      self.assertEqual(packages[0]['rows'][0]['signals']['final_requested_torque'], packages[1]['rows'][0]['signals']['final_requested_torque'])

  def test_no_fake_baseline_candidate(self):
    with self.assertRaises(ValueError):
      q.pair(self.pairs['TA_B'][0], self.pairs['TA_B'][0])

  def test_no_cross_campaign_composition(self):
    with self.assertRaises(ValueError):
      q.pair(self.pairs['TA_B'][0], self.pairs['SG_A'][1])

  def test_ta_governor_disabled(self):
    row = self.pairs['TA_B'][1]
    self.assertEqual(row['configs'][0]['config']['arm_identity']['governor'], 'SG_DISABLED')
    self.assertTrue(all(r['signals']['pre_governor_torque'] == r['signals']['post_governor_torque'] for r in row['rows']))

  def test_sg_native_core_and_own_feedback(self):
    left, right = self.pairs['SG_A']
    self.assertEqual(left['configs'][0]['config']['arm_identity']['core'], 'UNCHANGED_NATIVE_BASELINE')
    self.assertEqual(right['configs'][0]['config']['arm_identity']['core'], 'UNCHANGED_NATIVE_BASELINE')
    self.assertTrue(any(a['native_input_sha256'] != b['native_input_sha256'] for a, b in zip(left['rows'], right['rows'], strict=True)))
    for a, b in zip(right['rows'], right['rows'][1:], strict=False):
      self.assertEqual(a['plant_output']['curvature'], b['signals']['actual_curvature'])

  def test_arm_snapshots_differ_shared_stimulus_same(self):
    a, b = self.pairs['SG_A']
    cfg = a['configs'][0]['config']
    self.assertTrue(any(x['consumed_input_snapshot_sha256'] != y['consumed_input_snapshot_sha256'] for x, y in zip(a['rows'], b['rows'], strict=True)))
    self.assertEqual(
      [q.stimulus(r, 'driver_events', cfg['scenario_sha256']) for r in a['rows']], [q.stimulus(r, 'driver_events', cfg['scenario_sha256']) for r in b['rows']]
    )

  def test_wrong_own_feedback_rejected(self):
    row = self.changed()
    item = row['rows'][125]
    item['consumed_input_snapshot']['native_input']['actual_curvature_1pm'] = 1
    item['signals']['actual_curvature'] = 1
    item['native_input_sha256'] = p.sha(p.canonical(item['consumed_input_snapshot']['native_input']))
    item['consumed_input_snapshot_sha256'] = p.sha(p.canonical(item['consumed_input_snapshot']))
    with self.assertRaisesRegex(ValueError, 'PAIR_OWN_FEEDBACK_ONLY'):
      q.validate_package(self.reseal(row))

  def test_changed_time_grid_rejected(self):
    row = self.changed()
    row['rows'][50]['completion_time_ns'] += 1
    with self.assertRaises(ValueError):
      q.validate_package(self.reseal(row))

  def test_event_reset_drift_rejected(self):
    row = self.changed()
    row['rows'][200]['reset_events'] = []
    with self.assertRaises(ValueError):
      q.validate_package(self.reseal(row))

  def test_missing_row_rejected(self):
    row = self.changed()
    row['rows'].pop()
    with self.assertRaises(ValueError):
      q.validate_package(self.reseal(row))

  def test_duplicate_row_rejected(self):
    row = self.changed()
    row['rows'][20] = row['rows'][19]
    with self.assertRaises(ValueError):
      q.validate_package(self.reseal(row))

  def test_candidate_config_forgery_rejected(self):
    row = self.changed()
    cfg = row['configs'][0]
    cfg['config']['arm_identity']['governor'] = 'SG_DISABLED'
    cfg['config']['arm_identity_sha256'] = p.sha(p.canonical(cfg['config']['arm_identity']))
    cfg['config_sha256'] = p.sha(p.canonical(cfg['config']))
    with self.assertRaises(ValueError):
      q.validate_package(self.reseal(row))

  def test_third_or_current_arm_rejected(self):
    for arm in ('CURRENT', 'CYBER_CURRENT_ALIAS', 'TA_B_PLUS_SG_A'):
      with self.assertRaises(ValueError):
        producer.runtime('SG_A', arm, 'driver_events')

  def test_separate_evolving_state(self):
    a = producer.runtime('SG_A', q.BASELINE, 'driver_events')
    b = producer.runtime('SG_A', 'SG_A_V0', 'driver_events')
    from openpilot.tools.cyber_autotune.smoothness_closed_loop import assert_isolated

    assert_isolated([a, b])
    before = asdict(b.state)
    a.advance(0)
    self.assertEqual(before, asdict(b.state))
    self.assertEqual(b.index, 0)

  def test_no_invented_can_sensor_or_health(self):
    for packages in self.pairs.values():
      for package in packages:
        for row in package['rows']:
          self.assertIsNone(row['signals']['torqueOutputCan'])
          self.assertIsNone(row['signals']['steering_angle_deg'])
          self.assertIsNone(row['signals']['driver_torque'])
          self.assertTrue(all(service['valid'] is None for service in row['service_health'].values()))

  def test_tier_escalation_rejected(self):
    row = self.changed()
    row['binding']['tier'] = 'T2_EMPIRICAL_PLANT_CLOSED_LOOP'
    with self.assertRaises(ValueError):
      q.validate_package(self.reseal(row))

  def test_exact_repeat_and_observer_removed(self):
    context = self.pairs['SG_A'][0]['policy']
    raw, again = producer.run('SG_A', 'SG_A_V0', 'driver_events', context)
    plain, _ = producer.run('SG_A', 'SG_A_V0', 'driver_events', context, observe=False)
    self.assertEqual(p.canonical(again), p.canonical(self.pairs['SG_A'][1]))
    self.assertEqual(p.canonical(raw), p.canonical(plain))

  def test_pair_digest_deterministic(self):
    a = q.pair(*self.pairs['TA_B'])
    b = q.pair(*self.pairs['TA_B'])
    self.assertEqual(p.canonical(a), p.canonical(b))

  def test_stage_fabrication_rejected(self):
    row = self.changed('TA_B')
    row['rows'][120]['signals']['post_governor_torque'] = 0.2
    with self.assertRaises(ValueError):
      q.validate_package(self.reseal(row))

  def test_source_binding_drift_rejected(self):
    row = self.changed()
    row['policy']['sources']['cyber_h1_pair_producer.py'] = '0' * 64
    row['policy'] = q.verify(q.seal({k: v for k, v in row['policy'].items() if k != 'receipt_sha256'}))
    with self.assertRaises(ValueError):
      q.validate_package(self.reseal(row))

  def test_holdout_stays_closed(self):
    for pair in (q.pair(*v) for v in self.pairs.values()):
      self.assertEqual(pair['holdout_opening'], 'CLOSED')
      self.assertEqual(pair['opening_count'], 0)
      self.assertEqual(pair['blockers'], p.BLOCKERS)


class TestDisabledTAPath(unittest.TestCase):
  def test_ta_calls_own_disabled_passthrough(self):
    arm = producer.runtime('TA_B', 'TA_B_V0', 'driver_events')
    self.assertTrue(hasattr(arm, 'governor'), 'TA arm must execute a disabled passthrough stage')
    row = arm.advance(120) if arm.index == 120 else arm.advance(0)
    self.assertEqual(row['requested'], arm.governor.last_output.final_requested_torque)
    self.assertEqual(arm.governor.last_output.saturation_reason, 'DISABLED_EXACT_PASSTHROUGH')


class TestPersistedPolicy(unittest.TestCase):
  def test_package_json_roundtrip_keeps_exact_policy(self):
    import json

    context = q.policy()
    from openpilot.tools.cyber_autotune import cyber_h1_pair_producer as producer

    package = producer.run('TA_B', 'TA_B_V0', 'straight', context)[1]
    restored = json.loads(p.canonical(package))
    self.assertEqual(q.validate_package(restored), restored)
