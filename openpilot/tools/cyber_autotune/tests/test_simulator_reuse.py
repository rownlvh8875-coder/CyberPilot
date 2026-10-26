"""Contract boundary tests; synthetic inputs only, no simulator imports or raw readers."""

from copy import deepcopy
import unittest

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import simulator_reuse_contracts as c
from openpilot.tools.cyber_autotune import simulator_reuse_scaffolding as s

SHA = 'a' * 64


def binding():
  return dict.fromkeys(('campaign_sha256', 'model_set_sha256', 'admission_sha256', 'metric_policy_sha256'), SHA) | {
    'models': ['b' * 64],
    'purpose': 'FUTURE_UNTOUCHED_MODEL_EVALUATION',
    'model_set_sha256': p.sha(p.canonical(['b' * 64])),
  }


def configs():
  config = {'source_sha256': SHA, 'profile_sha256': SHA}
  return [{'process_epoch': 1, 'config_sequence': 1, 'config': config, 'config_sha256': p.sha(p.canonical(config))}]


def trace():
  row = {
    'schema': 'CYBER_LATERAL_OBSERVATION_V1',
    'process_epoch': 1,
    'loop_sequence': 1,
    'config_sequence': 1,
    'config_sha256': configs()[0]['config_sha256'],
    'capture_time_ns': 10,
    'decision_time_ns': 11,
    'source_sha256': SHA,
    'signals': dict.fromkeys(c.SIGNALS),
    'services': {name: {'time_ns': 9, 'updated': True, 'alive': True, 'freqOk': True, 'valid': True} for name in c.SERVICES},
    'event': 'ORDINARY',
    'synthetic_only': True,
  }
  row['consumed_input_snapshot_sha256'] = s.snapshot_sha(row)
  return row


def manifests():
  return [
    {
      'arm': arm,
      'source_receipt_sha256': SHA,
      'time_grid': {'count': 10, 'dt_ns': 10_000_000, 'origin_ns': 0},
      'tier': 'T1_DESCRIPTIVE_COUNTERFACTUAL',
      'provenance': 'PUBLIC_SYNTHETIC_RECEIPT_ONLY',
      'field_map': dict.fromkeys(c.VISUAL_FIELDS),
    }
    for arm in c.ARMS
  ]


class SimulatorContracts(unittest.TestCase):
  def test_contracts_are_nonexecuting(self):
    for row in c.artifacts().values():
      p.verify(row)
      self.assertFalse(row['execution_allowed'])
      self.assertFalse(row['production_observer_implemented'])
      self.assertEqual(row['calibration_blockers'], p.BLOCKERS)

  def test_required_lateral_fields(self):
    self.assertIn('torqueOutputCan', c.SIGNALS)
    self.assertIn('pre_limit_torque', c.SIGNALS)
    self.assertIn('steeringRateDeg', c.SIGNALS)

  def test_h1_valid_synthetic(self):
    self.assertEqual(s.validate_observations([trace()], configs())['trace_count'], 1)

  def test_snapshot_drift(self):
    row = trace()
    row['signals']['requested_torque'] = 0.5
    with self.assertRaises(ValueError):
      s.validate_observations([row], configs())

  def test_config_drift(self):
    cs = configs()
    cs[0]['config']['profile_sha256'] = 'b' * 64
    with self.assertRaises(ValueError):
      s.validate_observations([trace()], cs)

  def test_missing_config(self):
    with self.assertRaises(ValueError):
      s.validate_observations([trace()], [])

  def test_epoch_not_shared(self):
    row = trace()
    row['process_epoch'] = 2
    row['consumed_input_snapshot_sha256'] = s.snapshot_sha(row)
    with self.assertRaises(ValueError):
      s.validate_observations([row], configs())

  def test_sequence_gap(self):
    rows = [trace(), trace()]
    rows[1]['loop_sequence'] = 3
    rows[1]['consumed_input_snapshot_sha256'] = s.snapshot_sha(rows[1])
    with self.assertRaises(ValueError):
      s.validate_observations(rows, configs())

  def test_future_source_timestamp(self):
    row = trace()
    row['services']['carState']['time_ns'] = 12
    row['consumed_input_snapshot_sha256'] = s.snapshot_sha(row)
    with self.assertRaises(ValueError):
      s.validate_observations([row], configs())

  def test_decision_before_capture(self):
    row = trace()
    row['decision_time_ns'] = 8
    row['consumed_input_snapshot_sha256'] = s.snapshot_sha(row)
    with self.assertRaises(ValueError):
      s.validate_observations([row], configs())

  def test_decision_clock_regression_rejected(self):
    rows = [trace(), trace()]
    rows[0]['decision_time_ns'] = 100
    rows[1].update(loop_sequence=2, capture_time_ns=20, decision_time_ns=21)
    for row in rows:
      row['consumed_input_snapshot_sha256'] = s.snapshot_sha(row)
    with self.assertRaisesRegex(ValueError, 'CLOCK_DRIFT'):
      s.validate_observations(rows, configs())

  def test_next_capture_before_prior_decision_rejected(self):
    rows = [trace(), trace()]
    rows[0]['decision_time_ns'] = 100
    rows[1].update(loop_sequence=2, capture_time_ns=20, decision_time_ns=101)
    for row in rows:
      row['consumed_input_snapshot_sha256'] = s.snapshot_sha(row)
    with self.assertRaisesRegex(ValueError, 'CLOCK_DRIFT'):
      s.validate_observations(rows, configs())

  def test_unknown_service_rejected(self):
    row = trace()
    row['services']['modelV2'] = {}
    with self.assertRaises(ValueError):
      s.validate_observations([row], configs())

  def test_signal_extra_rejected(self):
    row = trace()
    row['signals']['lane_reference'] = 1
    with self.assertRaises(ValueError):
      s.validate_observations([row], configs())

  def test_nonfinite_signal_rejected(self):
    row = trace()
    row['signals']['actual_curvature'] = float('nan')
    with self.assertRaises(ValueError):
      s.validate_observations([row], configs())

  def test_unknown_limits_remain_null(self):
    row = trace()
    before = deepcopy(row)
    s.validate_observations([row], configs())
    self.assertEqual(row, before)
    self.assertIsNone(row['signals']['safety_limited'])

  def test_not_production_observer(self):
    row = trace()
    row['synthetic_only'] = False
    with self.assertRaises(ValueError):
      s.validate_observations([row], configs())

  def test_boolean_mask_exact(self):
    row = trace()
    row['services']['carState']['valid'] = 1
    with self.assertRaises(ValueError):
      s.validate_observations([row], configs())

  def test_unsigned_epoch(self):
    row = trace()
    row['process_epoch'] = -1
    with self.assertRaises(ValueError):
      s.validate_observations([row], configs())

  def test_no_can_ack_inference(self):
    row = c.artifacts()['cyber-lateral-observability-contract-v1.json']
    self.assertFalse(row['raw_command_is_physical_acknowledgement'])

  def test_exposure_stays_closed(self):
    row = s.exposure_plan(binding(), [])
    self.assertEqual(row['state'], 'CLOSED')
    self.assertEqual(row['opening_count'], 0)
    self.assertFalse(row['opening_allowed'])

  def test_exposure_resume_exact(self):
    row = s.exposure_plan(binding(), [])
    self.assertEqual(s.exposure_plan(binding(), [row]), row)

  def test_exposure_model_drift(self):
    row = s.exposure_plan(binding(), [])
    b = binding()
    b['models'] = ['c' * 64]
    with self.assertRaises(ValueError):
      s.exposure_plan(b, [row])

  def test_exposure_campaign_drift(self):
    row = s.exposure_plan(binding(), [])
    b = binding()
    b['campaign_sha256'] = 'c' * 64
    with self.assertRaises(ValueError):
      s.exposure_plan(b, [row])

  def test_exposure_opened_rejected(self):
    row = s.exposure_plan(binding(), [])
    row = p.seal({**row, 'opening_count': 1, 'state': 'OPENED'})
    with self.assertRaises(ValueError):
      s.exposure_plan(binding(), [row])

  def test_exposure_purpose_exact(self):
    b = binding()
    b['purpose'] = 'candidate_search'
    with self.assertRaises(ValueError):
      s.exposure_plan(b, [])

  def test_exposure_no_empty_model_set(self):
    b = binding()
    b['models'] = []
    with self.assertRaises(ValueError):
      s.exposure_plan(b, [])

  def test_exposure_unknown_field_rejected(self):
    b = binding()
    b['raw_route_path'] = 'private'
    with self.assertRaises(ValueError):
      s.exposure_plan(b, [])

  def test_exposure_not_mutated(self):
    b = binding()
    before = deepcopy(b)
    s.exposure_plan(b, [])
    self.assertEqual(b, before)

  def test_visual_plan_exact_three_arms(self):
    row = s.visual_plan(manifests())
    self.assertEqual(len(row['arms']), 3)
    self.assertFalse(row['frames_converted'])
    self.assertFalse(row['server_implemented'])

  def test_visual_grid_mismatch(self):
    rows = manifests()
    rows[2]['time_grid']['count'] = 11
    with self.assertRaises(ValueError):
      s.visual_plan(rows)

  def test_visual_missing_current(self):
    with self.assertRaises(ValueError):
      s.visual_plan(manifests()[:2])

  def test_visual_duplicate_arm(self):
    rows = manifests()
    rows[2]['arm'] = rows[0]['arm']
    with self.assertRaises(ValueError):
      s.visual_plan(rows)

  def test_visual_network_host_rejected(self):
    with self.assertRaises(ValueError):
      s.visual_plan(manifests(), host='0.0.0.0')

  def test_visual_private_traces_rejected(self):
    rows = manifests()
    rows[0]['provenance'] = 'PRIVATE_RAW_LOG'
    with self.assertRaises(ValueError):
      s.visual_plan(rows)

  def test_visual_path_field_rejected(self):
    rows = manifests()
    rows[0]['rows_path'] = 'private'
    with self.assertRaises(ValueError):
      s.visual_plan(rows)

  def test_visual_future_external_asset_rejected(self):
    rows = manifests()
    rows[0]['field_map']['external_url'] = 'https://example.org'
    with self.assertRaises(ValueError):
      s.visual_plan(rows)

  def test_visual_normalized_vs_angle_separate(self):
    self.assertIn('requested_torque', c.VISUAL_FIELDS)
    self.assertIn('steering_angle_deg', c.VISUAL_FIELDS)

  def test_visual_relative_time_only(self):
    rows = manifests()
    rows[0]['time_grid']['origin_ns'] = 100
    with self.assertRaises(ValueError):
      s.visual_plan(rows)

  def test_visual_no_higher_tier_promotion(self):
    rows = manifests()
    rows[0]['tier'] = 'T2_EMPIRICAL_PLANT_CLOSED_LOOP'
    with self.assertRaises(ValueError):
      s.visual_plan(rows)

  def test_claim_replay(self):
    self.assertEqual(s.validate_claim('T0_REPLAY', 'REPLAY_CONSISTENCY')['status'], 'CONTRACT_ONLY')

  def test_claim_descriptive(self):
    self.assertEqual(s.validate_claim('T1_DESCRIPTIVE_COUNTERFACTUAL', 'DESCRIPTIVE_COUNTERFACTUAL')['status'], 'CONTRACT_ONLY')

  def test_claim_t0_cannot_counterfactual(self):
    with self.assertRaises(ValueError):
      s.validate_claim('T0_REPLAY', 'DESCRIPTIVE_COUNTERFACTUAL')

  def test_claim_t2_not_currently_available(self):
    with self.assertRaises(ValueError):
      s.validate_claim('T2_EMPIRICAL_PLANT_CLOSED_LOOP', 'EMPIRICAL_CLOSED_LOOP')

  def test_claim_t3_not_currently_available(self):
    with self.assertRaises(ValueError):
      s.validate_claim('T3_SENSOR_WORLD_CLOSED_LOOP', 'SENSOR_WORLD_ROBUSTNESS')

  def test_claim_never_vehicle_authority(self):
    with self.assertRaises(ValueError):
      s.validate_claim('T1_DESCRIPTIVE_COUNTERFACTUAL', 'VEHICLE_QUALIFIED')

  def test_no_modelv2_reference(self):
    with self.assertRaises(ValueError):
      s.validate_claim('T0_REPLAY', 'MODEL_V2_INDEPENDENT_REFERENCE')

  def test_repeated_scaffolding_exact(self):
    self.assertEqual(s.visual_plan(manifests()), s.visual_plan(manifests()))
    self.assertEqual(s.exposure_plan(binding(), []), s.exposure_plan(binding(), []))

  def test_bad_model_set_digest(self):
    b = binding()
    b['model_set_sha256'] = 'c' * 64
    with self.assertRaises(ValueError):
      s.exposure_plan(b, [])

  def test_frozen_family_not_retuned(self):
    self.assertFalse(c.artifacts()['cyber-simulation-fidelity-contract-v1.json']['plant_imported'])

  def test_no_actual_visual_frames_in_plan(self):
    self.assertNotIn('frames', s.visual_plan(manifests()))


if __name__ == '__main__':
  unittest.main()
