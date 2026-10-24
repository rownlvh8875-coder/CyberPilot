"""Synthetic metadata and row contracts; never opens driving evidence."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import future_empirical_contracts as c
from openpilot.tools.cyber_autotune import future_empirical_admission as a
from openpilot.tools.cyber_autotune import future_empirical_context as x


def digest(value):
  return p.sha(str(value).encode())


def metadata(number=0):
  source = c.known_sources()[0]
  profile = c.known_profiles()[0]
  return p.seal(
    {
      'schema': 'FUTURE_ROUTE_METADATA_V1',
      'source_commit': source['commit'],
      'os_version': 'synthetic',
      'vehicle_fingerprint': 'HYUNDAI_SANTA_FE_2022',
      'full_carparams_sha256': profile['full_carparams_sha256'],
      'empirical_profile_sha256': profile['empirical_profile_sha256'],
      'logger_start_sha256': digest(f'logger{number}'),
      'segments': [{'ordinal': 0, 'receipt_sha256': digest(f'segment{number}')}],
      'adapter_sha256': source['adapter_sha256'],
      'source_class_sha256': source['class_sha256'],
      'source_fingerprint_sha256': source['fingerprint_sha256'],
      'control_type': 'torque',
      'envelopes': dict.fromkeys(c.REQUIRED_MESSAGES, 1),
      'complete_lineage': True,
      'prior_analysis': 'NONE',
      'numeric_opened': False,
      'dirty': False,
      'root_id': 'CARROT_LOGS',
      'field_presence': {**dict.fromkeys(c.SIGNAL_FIELDS, 'UNKNOWN'), **dict.fromkeys(c.REQUIRED_STAGE_A_FIELDS, 'AVAILABLE')},
    }
  )


OLD_IDENTITY = {
  'logger_start_sha256': digest('old-logger'),
  'generation_hashes': [digest('old-generation')],
  'lineages': [digest('old-lineage')],
  'monotonic_ranges': [[0, 10, 0]],
}
OLD_ROUTE = digest('old-route')
OLD_SEGMENT = digest('old-segment')


def history_inventory():
  return p.seal(
    {
      'schema': 'EMPIRICAL_CROSS_ROOT_PRIVATE_INVENTORY_V1',
      'routes': [{'route_id': OLD_ROUTE, 'source_hashes': [OLD_SEGMENT]}],
      'numeric_payloads_opened': False,
    }
  )


def history():
  return p.seal(
    {
      'schema': 'FUTURE_ROUTE_HISTORY_METADATA_V1',
      'inventory_sha256': c.history_sha(),
      'complete': True,
      'metadata_inventory': history_inventory(),
      'routes': [
        {'route_id': OLD_ROUTE, 'identity': OLD_IDENTITY, 'logger_start_sha256': OLD_IDENTITY['logger_start_sha256'], 'segment_receipts': [OLD_SEGMENT]}
      ],
    }
  )


def admitted(number=0, old=None):
  return a.inventory(metadata(number), history(), old or [])


def assigned():
  return a.assign([admitted(i) for i in range(3)])


def frozen_fixture(roles):
  return p.seal(
    {
      'schema': 'FUTURE_MODEL_FREEZE_CONTRACT_V1',
      'roles_sha256': roles['receipt_sha256'],
      'family_sha256': digest('family'),
      'config_sha256': digest('config'),
      'model_sha256': digest('model'),
      'metrics_sha256': digest('metrics'),
      'support_policy_sha256': digest('support'),
      'source_class_sha256': roles['source_class_sha256'],
      'empirical_profile_sha256': roles['empirical_profile_sha256'],
      'status': 'MODEL_FROZEN_AWAITING_HOLDOUT',
      'no_reselection': True,
      'no_refit': True,
    }
  )


def context(role=None):
  roles = role or assigned()
  route = next(z for z in roles['routes'] if z['role'] == 'TRAIN')
  base = {
    'generation': 'FUTURE_SYNTHETIC_GENERATION',
    'route_id': route['route_id'],
    'segment_receipt_sha256': route['segment_receipts'][0],
    'aligned_row_index': 2,
    'run_id': digest('run'),
    'within_run_index': 2,
    'design_row_index': 0,
    'source_commit': route['source_commit'],
    'profile_sha256': route['empirical_profile_sha256'],
    'adapter_sha256': route['adapter_sha256'],
    'policy_sha256': c.generation_policy()['receipt_sha256'],
    'role_receipt_sha256': roles['receipt_sha256'],
    'prediction_time_ns': 30_000_000,
    'grid_time_ns': 20_000_000,
    'state_time_ns': 20_000_000,
    'command_time_ns': 19_000_000,
    'control_time_ns': 18_000_000,
    'source_age_ns': 0,
    'steeringAngleDeg': 1.2,
    'steeringRateDeg': 4.0,
    'vEgo': 12.0,
    'mask_reasons': [],
  }
  return x.capture(base, roles), roles


class SyntheticHistory:
  def setUp(self):
    handle = patch.object(c, 'history_bindings', return_value={OLD_ROUTE: p.sha(p.canonical(OLD_IDENTITY))})
    handle.start()
    self.addCleanup(handle.stop)
    private = patch.object(c, 'history_private_sha', return_value=history_inventory()['receipt_sha256'])
    private.start()
    self.addCleanup(private.stop)


class TestFutureAdmission(SyntheticHistory, unittest.TestCase):
  def test_closure_bound(self):
    policy = c.generation_policy()
    self.assertEqual(policy['closure']['verdict'], 'SOURCE_GRID_OBSERVATION_REJECTED')
    self.assertEqual(policy['closure']['track'], 'CURRENT_ARX1_FIR25_SIMPLE_OBSERVATION_TRACK_CLOSED')

  def test_metadata_only(self):
    with patch('openpilot.tools.cyber_autotune.empirical_route_eligibility.read_numeric', side_effect=AssertionError('raw')):
      self.assertEqual(admitted()['numeric_coverage'], None)

  def test_required_signal_unknown_not_admitted(self):
    m = metadata()
    m['field_presence']['steeringRateDeg'] = 'UNKNOWN'
    m = p.seal({k: v for k, v in m.items() if k != 'receipt_sha256'})
    self.assertEqual(a.inventory(m, history(), [])['status'], 'METADATA_ONLY_PENDING')

  def test_known_exact_source(self):
    self.assertEqual(a.source_status(metadata()), 'SOURCE_EQUIVALENT')

  def test_unknown_full_profile_pending(self):
    m = metadata()
    m['full_carparams_sha256'] = digest('new-profile')
    self.assertEqual(a.source_status(m), 'SOURCE_AUDIT_PENDING')

  def test_unknown_source(self):
    m = metadata()
    m['source_commit'] = '0' * 40
    self.assertEqual(a.source_status(p.seal({k: v for k, v in m.items() if k != 'receipt_sha256'})), 'SOURCE_AUDIT_PENDING')

  def test_wrong_adapter(self):
    m = metadata()
    m['adapter_sha256'] = digest('bad')
    self.assertEqual(a.source_status(m), 'SOURCE_ADAPTER_REQUIRED')

  def test_dirty_rejected(self):
    m = metadata()
    m['dirty'] = True
    self.assertEqual(a.source_status(m), 'SOURCE_INCOMPATIBLE')

  def test_angle_control_rejected(self):
    m = metadata()
    m['control_type'] = 'angle'
    self.assertEqual(a.source_status(m), 'SOURCE_INCOMPATIBLE')

  def test_exact_metadata_keys(self):
    m = metadata()
    m['yawRate'] = 0.0
    with self.assertRaises(ValueError):
      a.inventory(m, history(), [])

  def test_empty_history_cannot_claim_complete(self):
    h = history()
    h['routes'] = []
    h = p.seal({k: v for k, v in h.items() if k != 'receipt_sha256'})
    with self.assertRaises(ValueError):
      a.inventory(metadata(), h, [])

  def test_wrong_history_proof(self):
    h = history()
    h['routes'][0]['identity'] = {**OLD_IDENTITY, 'logger_start_sha256': digest('other')}
    h = p.seal({k: v for k, v in h.items() if k != 'receipt_sha256'})
    with self.assertRaises(ValueError):
      a.inventory(metadata(), h, [])

  def test_changed_historical_segments_rejected(self):
    h = history()
    h['routes'][0]['segment_receipts'] = [digest('fake-old-segment')]
    h = p.seal({k: v for k, v in h.items() if k != 'receipt_sha256'})
    with self.assertRaises(ValueError):
      a.inventory(metadata(), h, [])

  def test_copy_logger_rejected(self):
    m = metadata(1)
    m['logger_start_sha256'] = metadata(0)['logger_start_sha256']
    m = p.seal({k: v for k, v in m.items() if k != 'receipt_sha256'})
    with self.assertRaises(ValueError):
      a.inventory(m, history(), [admitted(0)])

  def test_overlap_lineage_rejected(self):
    m = metadata(1)
    m['segments'] = metadata(0)['segments']
    m = p.seal({k: v for k, v in m.items() if k != 'receipt_sha256'})
    with self.assertRaises(ValueError):
      a.inventory(m, history(), [admitted(0)])

  def test_missing_segment_rejected(self):
    m = metadata()
    m['segments'][0]['ordinal'] = 1
    m = p.seal({k: v for k, v in m.items() if k != 'receipt_sha256'})
    with self.assertRaises(ValueError):
      a.inventory(m, history(), [])

  def test_history_complete_required(self):
    h = history()
    h['complete'] = None
    h = p.seal({k: v for k, v in h.items() if k != 'receipt_sha256'})
    with self.assertRaises(ValueError):
      a.inventory(metadata(), h, [])

  def test_existing_logger_rejected(self):
    h = history()
    h['routes'] = [{'logger_start_sha256': metadata()['logger_start_sha256'], 'segment_receipts': []}]
    h = p.seal({k: v for k, v in h.items() if k != 'receipt_sha256'})
    with self.assertRaises(ValueError):
      a.inventory(metadata(), h, [])

  def test_three_whole_routes(self):
    roles = assigned()
    self.assertEqual([z['role'] for z in roles['routes']], ['TRAIN', 'DEVELOPMENT', 'HOLDOUT'])
    self.assertEqual(len({z['route_id'] for z in roles['routes']}), 3)

  def test_five_preferred(self):
    self.assertEqual([z['role'] for z in a.assign([admitted(i) for i in range(5)])['routes']], ['TRAIN', 'TRAIN', 'TRAIN', 'DEVELOPMENT', 'HOLDOUT'])

  def test_two_insufficient(self):
    with self.assertRaises(ValueError):
      a.assign([admitted(0), admitted(1)])

  def test_segment_not_route(self):
    r = admitted()
    with self.assertRaises(ValueError):
      a.assign([r, r, r])

  def test_mixed_profile(self):
    rows = [admitted(i) for i in range(3)]
    rows[1]['full_carparams_sha256'] = digest('other')
    rows[1] = p.seal({k: v for k, v in rows[1].items() if k != 'receipt_sha256'})
    with self.assertRaises(ValueError):
      a.assign(rows)

  def test_prior_unknown_no_holdout(self):
    m = metadata()
    m['prior_analysis'] = 'UNKNOWN'
    m = p.seal({k: v for k, v in m.items() if k != 'receipt_sha256'})
    row = a.inventory(m, history(), [])
    self.assertEqual(row['status'], 'METADATA_ONLY_PENDING')
    with self.assertRaises(ValueError):
      a.assign([row, admitted(1), admitted(2)])

  def test_numeric_preopened_no_role(self):
    m = metadata()
    m['numeric_opened'] = True
    m = p.seal({k: v for k, v in m.items() if k != 'receipt_sha256'})
    self.assertEqual(a.inventory(m, history(), [])['status'], 'REJECTED')

  def test_role_persistence_no_overwrite(self):
    with tempfile.TemporaryDirectory() as temp:
      path = Path(temp) / 'roles.json'
      p.persist(path, assigned())
      different = a.assign([admitted(i) for i in range(3, 6)])
      with self.assertRaises(ValueError):
        p.persist(path, different)

  def test_role_before_numeric(self):
    with self.assertRaises(ValueError):
      x.capture({}, None)

  def test_holdout_stays_closed(self):
    self.assertEqual(a.holdout_plan(assigned(), None, [])['status'], 'CLOSED_MISSING_ADMISSIBLE_MODEL')

  def test_holdout_requires_frozen_model(self):
    with self.assertRaises(ValueError):
      a.holdout_plan(assigned(), p.seal({'schema': 'bad'}), [])

  def test_holdout_one_time(self):
    model = frozen_fixture(assigned())  # contract fixture only, no model implementation
    h = next(z for z in assigned()['routes'] if z['role'] == 'HOLDOUT')
    with self.assertRaises(ValueError):
      a.holdout_plan(assigned(), model, [h['route_id']])

  def test_holdout_future_auth_required(self):
    plan = a.holdout_plan(assigned(), frozen_fixture(assigned()), [])
    self.assertEqual(plan['status'], 'CLOSED_FUTURE_AUTHORIZATION_REQUIRED')
    self.assertFalse(plan['opening_allowed'])

  def test_roots_exact(self):
    self.assertEqual(a.root_id('D:\\' + 'CarrotLogs'), a.root_id('/mnt/d/CarrotLogs'))
    for root in ('/mnt/d', '/mnt/d/' + 'CarrotLogs/child', '/tmp', '//server/share'):
      with self.assertRaises(ValueError):
        a.root_id(root)

  def test_store_not_repository(self):
    with self.assertRaises(ValueError):
      a.private_store(Path(__file__).parent)

  def test_eligibility_metadata_unknowns(self):
    report = a.eligibility(admitted())
    self.assertIsNone(report['speed_bin_potential'])
    self.assertIsNone(report['active_no_override_potential'])
    self.assertFalse(report['fitting_performed'])


class TestFutureContext(SyntheticHistory, unittest.TestCase):
  def test_actual_rate_sample(self):
    row, _ = context()
    self.assertEqual(row['steeringRateDeg'], 4.0)

  def test_missing_null_not_zero(self):
    row, _ = context()
    self.assertIsNone(row['safety_limited'])
    self.assertIsNone(row['gyro_xyz'])
    self.assertIsNone(row['yaw_raw'])

  def test_base_schema_pin(self):
    self.assertEqual(c.context_schema()['base_sha256'], c.read('empirical-causal-context-schema-v1.json')['receipt_sha256'])

  def test_historical_generation(self):
    row, roles = context()
    row['generation'] = 'EMPIRICAL_PLANT_V2'
    with self.assertRaises(ValueError):
      x.capture(row, roles)

  def test_future_target_forbidden(self):
    row, roles = context()
    row['target'] = 1.0
    with self.assertRaises(ValueError):
      x.capture(row, roles)

  def test_future_command(self):
    row, roles = context()
    row['command_time_ns'] = 21_000_000
    with self.assertRaises(ValueError):
      x.capture(row, roles)

  def test_target_time_leak(self):
    row, roles = context()
    row['state_time_ns'] = row['prediction_time_ns']
    with self.assertRaises(ValueError):
      x.capture(row, roles)

  def test_age_gap(self):
    row, roles = context()
    row['grid_time_ns'] = 50_000_000
    with self.assertRaises(ValueError):
      x.capture(row, roles)

  def test_float_time_rejected(self):
    row, roles = context()
    row['state_time_ns'] = 20_000_000.0
    with self.assertRaises(ValueError):
      x.capture(row, roles)

  def test_holdout_row_capture_prohibited(self):
    row, roles = context()
    h = next(z for z in roles['routes'] if z['role'] == 'HOLDOUT')
    row['route_id'] = h['route_id']
    with self.assertRaises(ValueError):
      x.capture(row, roles)

  def test_wrong_profile(self):
    row, roles = context()
    row['profile_sha256'] = digest('bad')
    with self.assertRaises(ValueError):
      x.capture(row, roles)

  def test_unknown_source_no_fallback(self):
    row, roles = context()
    row['source_commit'] = '0' * 40
    with self.assertRaises(ValueError):
      x.capture(row, roles)

  def test_nonfinite_rejected(self):
    row, roles = context()
    row['steeringRateDeg'] = float('nan')
    with self.assertRaises(ValueError):
      x.capture(row, roles)

  def test_no_result_label(self):
    row, roles = context()
    row['arx_win'] = True
    with self.assertRaises(ValueError):
      x.capture(row, roles)

  def test_no_future_history(self):
    row, roles = context()
    row['command_history'] = [
      {'time_ns': 30_000_000, 'value': 1.0, 'route_id': row['route_id'], 'segment_receipt_sha256': row['segment_receipt_sha256'], 'run_id': row['run_id']}
    ]
    with self.assertRaises(ValueError):
      x.capture(row, roles)

  def test_no_cross_route_history(self):
    row, roles = context()
    row['angle_history'] = [
      {'time_ns': 10_000_000, 'value': 1.0, 'route_id': digest('other'), 'segment_receipt_sha256': row['segment_receipt_sha256'], 'run_id': row['run_id']}
    ]
    with self.assertRaises(ValueError):
      x.capture(row, roles)

  def test_no_cross_segment_history(self):
    row, roles = context()
    row['angle_history'] = [
      {'time_ns': 10_000_000, 'value': 1.0, 'route_id': row['route_id'], 'segment_receipt_sha256': digest('other'), 'run_id': row['run_id']}
    ]
    with self.assertRaises(ValueError):
      x.capture(row, roles)

  def test_no_cross_run_history(self):
    row, roles = context()
    row['angle_history'] = [
      {'time_ns': 10_000_000, 'value': 1.0, 'route_id': row['route_id'], 'segment_receipt_sha256': row['segment_receipt_sha256'], 'run_id': digest('other')}
    ]
    with self.assertRaises(ValueError):
      x.capture(row, roles)

  def test_stale_command(self):
    row, roles = context()
    row['state_time_ns'] = 50_000_000
    row['grid_time_ns'] = 50_000_000
    row['prediction_time_ns'] = 60_000_000
    row['control_time_ns'] = 49_000_000
    with self.assertRaises(ValueError):
      x.capture(row, roles)

  def test_gyro_source_missing(self):
    row, roles = context()
    row['gyro_xyz'] = [0.0, 0.0, 0.0]
    with self.assertRaises(ValueError):
      x.capture(row, roles)

  def test_gyro_acquisition_future(self):
    row, roles = context()
    row.update(gyro_xyz=[0.0, 0.0, 0.0], gyro_source='synthetic', sensor_acquisition_time_ns=21_000_000, sensor_publish_time_ns=20_000_000)
    with self.assertRaises(ValueError):
      x.capture(row, roles)

  def test_row_clock_regression(self):
    row, roles = context()
    with self.assertRaises(ValueError):
      x.eligibility([row, row], roles)

  def test_synthetic_eligibility_no_fit(self):
    row, roles = context()
    report = x.eligibility([row], roles)
    self.assertTrue(report['synthetic_contract_only'])
    self.assertFalse(report['fitting_performed'])
    self.assertEqual(report['available_samples']['steeringRateDeg'], 1)

  def test_speed_bin_consistency(self):
    row, roles = context()
    row['speed_bin'] = 'HIGH'
    with self.assertRaises(ValueError):
      x.capture(row, roles)

  def test_source_clock_regression(self):
    row, roles = context()
    second = {
      **row,
      'aligned_row_index': 3,
      'grid_time_ns': 30_000_000,
      'state_time_ns': 19_000_000,
      'source_age_ns': 11_000_000,
      'command_time_ns': 18_000_000,
      'control_time_ns': 17_000_000,
      'prediction_time_ns': 40_000_000,
    }
    with self.assertRaises(ValueError):
      x.eligibility([row, second], roles)

  def test_scope_reentry_rejected(self):
    row, roles = context()
    route = next(z for z in roles['routes'] if z['role'] == 'DEVELOPMENT')
    other = {**row, 'route_id': route['route_id'], 'segment_receipt_sha256': route['segment_receipts'][0]}
    with self.assertRaises(ValueError):
      x.eligibility([row, other, row], roles)

  def test_boundary_breaks_support(self):
    first, roles = context()
    rows = []
    for i in range(60):
      state = 20_000_000 + i * 10_000_000
      rows.append(
        {
          **first,
          'aligned_row_index': i + 2,
          'within_run_index': i + 2,
          'grid_time_ns': state,
          'state_time_ns': state,
          'command_time_ns': state - 1_000_000,
          'control_time_ns': state - 2_000_000,
          'prediction_time_ns': state + 10_000_000,
          'latActive': True,
          'steeringPressed': False,
          'eps_temporary_fault': False,
          'eps_permanent_fault': False,
          'gear': 'drive',
          'raw_command': 0,
          'runtime_steer_max': 409,
          'gap_boundary': i == 30,
          'intervention_boundary': False,
        }
      )
    report = x.eligibility(rows, roles)
    self.assertEqual(report['support']['bins']['LOW']['design_rows'], 0)

  def test_repeatable_capture(self):
    self.assertEqual(context(), context())

  def test_nonexecuting_families(self):
    shortlist = c.families()
    self.assertEqual(len(shortlist['families']), 3)
    self.assertFalse(shortlist['implementation_allowed'])

  def test_no_numeric_executor(self):
    with self.assertRaises(ValueError):
      a.numeric_open(assigned(), 'TRAIN')

  def test_no_holdout_executor(self):
    with self.assertRaises(ValueError):
      a.numeric_open(assigned(), 'HOLDOUT')


if __name__ == '__main__':
  unittest.main()
