"""Synthetic tests: no private routes, model execution or raw fixtures."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import numpy as np

from openpilot.tools.cyber_autotune import empirical_causal_dataset_policy as policy
from openpilot.tools.cyber_autotune import empirical_causal_dataset_reader as reader
from openpilot.tools.cyber_autotune import empirical_causal_dataset_alignment as alignment
from openpilot.tools.cyber_autotune import empirical_causal_dataset_store as storage


def streams(n=80):
  rows = {'state': [], 'command': [], 'control': [], 'gyro': [], 'settings': [{'CustomSteerMax': 409}]}
  for i in range(n):
    t = 10_000_000 * (i + 1)
    rows['state'].append({'time_ns': t, 'valid': True, 'speed_mps': 10., 'angle_deg': float(i)/10, 'rate': 4.,
      'driver_pressed': False, 'driver_torque': 0., 'eps_fault': False, 'fault_temporary': False, 'fault_permanent': False,
      'torque_eps': 0., 'gear': 'drive', 'yaw_raw': 0., 'wheel_fl': 10., 'wheel_fr': 10., 'wheel_rl': 10., 'wheel_rr': 10.})
    rows['command'].append({'time_ns': t-1, 'valid': True, 'raw': 1., 'normalized': float(np.float32(1/409))})
    rows['control'].append({'time_ns': t-2, 'valid': True, 'requested': .2, 'lat_active': True, 'desired_curvature': None})
  return rows


class TestCausalDataset(unittest.TestCase):
  def test_resolve_exact_two_from_history(self):
    result = policy.resolve_routes()
    self.assertEqual(len(result), 2)
    self.assertTrue(all(x['role'] == 'RETROSPECTIVE_TRAIN_DEV_CV_POOL' for x in result))
    self.assertTrue(all(x['holdout_allowed'] is False for x in result))

  def test_rate_is_actual_not_coverage(self):
    result, _ = alignment.build(streams(), 'a'*64, 0, 0)
    self.assertEqual(result['state.rate'].tolist(), [4.]*80)
    self.assertTrue(result['state.rate.available'].all())

  def test_source_clock_regression(self):
    s = streams()
    s['state'][1]['time_ns'] = s['state'][0]['time_ns']
    with self.assertRaises(ValueError):
      alignment.build(s, 'a'*64, 0, 0)

  def test_latest_past_no_future(self):
    s = streams()
    s['command'][0]['time_ns'] = s['state'][0]['time_ns']+1
    result, _ = alignment.build(s, 'a'*64, 0, 0)
    self.assertFalse(result['command.raw.available'][0])
    self.assertTrue((result['command.time_ns'][1:] <= result['state.time_ns'][1:]).all())

  def test_stale_missing_remains_null(self):
    s = streams()
    s['command'] = s['command'][:1]
    result, _ = alignment.build(s, 'a'*64, 0, 0)
    self.assertFalse(result['command.raw.available'][-1])
    self.assertTrue(np.isnan(result['command.raw'][-1]))

  def test_all_rows_not_only_valid(self):
    s = streams()
    s['control'][20]['lat_active'] = False
    result, stats = alignment.build(s, 'a'*64, 0, 0)
    self.assertEqual(len(result['grid_time_ns']), 80)
    self.assertLess(stats['diagnostic_valid'], 80)

  def test_causal_run_not_speed_split(self):
    s = streams()
    for row in s['state'][40:]:
      row['speed_mps'] = 20.
    result, _ = alignment.build(s, 'a'*64, 0, 0)
    self.assertEqual(len(set(result['causal_run_id'])), 1)
    self.assertEqual(len(set(result['legacy_run_id'])), 2)

  def test_bridge_exact_float32(self):
    self.assertEqual(reader.bridge(streams()['command'], 409)['status'], 'ROUTE_COMMAND_BRIDGE_CONFIRMED')

  def test_wrong_max_rejected(self):
    with self.assertRaises(ValueError):
      reader.bridge(streams()['command'], 384)

  def test_bridge_conflict(self):
    s = streams()
    s['command'][0]['normalized'] = .7
    self.assertEqual(reader.bridge(s['command'], 409)['status'], 'ROUTE_COMMAND_BRIDGE_CONFLICT')

  def test_forbidden_body_not_dereferenced(self):
    class Event:
      def which(self):
        return 'modelV2'
      def __getattr__(self, name):
        raise AssertionError('forbidden body')
    result = reader.numeric([Event()])
    self.assertEqual(result['state'], [])

  def test_exact_repeatability(self):
    a, sa = alignment.build(streams(), 'a'*64, 0, 0)
    b, sb = alignment.build(streams(), 'a'*64, 0, 0)
    self.assertEqual(sa, sb)
    for key in a:
      self.assertEqual(a[key].tobytes(), b[key].tobytes())

  def test_no_fitting(self):
    with patch('numpy.linalg.lstsq', side_effect=AssertionError('fit')):
      alignment.build(streams(), 'a'*64, 0, 0)

  def test_immutable_array_resume(self):
    with TemporaryDirectory() as d:
      path = Path(d)/'array.npy'
      storage.array_write(path, np.arange(4))
      storage.array_write(path, np.arange(4))
      with self.assertRaises(ValueError):
        storage.array_write(path, np.arange(5))

  def test_symlink_rejected(self):
    with TemporaryDirectory() as d:
      path = Path(d)/'alias'
      path.symlink_to(Path(d), target_is_directory=True)
      with self.assertRaises(ValueError):
        storage.safe(path/'x')

  def test_store_overlap_rejected(self):
    with self.assertRaises(ValueError):
      storage.external('/tmp/raw-root/output', [Path('/tmp/raw-root')])

  def test_unknown_source_rejected(self):
    with self.assertRaises(ValueError):
      policy.validate_source({'commit': 'unknown'}, {}, {})

  def test_authorization_exact_segment(self):
    with self.assertRaises(ValueError):
      policy.require_segment({'segments': {'a'*64: ['b'*64]}}, 'c'*64, 'b'*64)

  def test_historical_schema_unchanged(self):
    x = policy.inputs()
    self.assertEqual(x['empirical-causal-context-schema-v2.json']['scope'], 'FUTURE_GENERATIONS_ONLY')



class TestCausalAlignmentEdges(unittest.TestCase):
  def test_actual_rate_nonzero_and_missing_distinct(self):
    s = streams()
    s['state'][10]['rate'] = None
    a, _ = alignment.build(s, 'a'*64, 0, 0)
    self.assertEqual(a['state.rate'][9], 4.)
    self.assertTrue(np.isnan(a['state.rate'][10]))
    self.assertFalse(a['state.rate.available'][10])

  def test_no_rate_coverage_substitution(self):
    s = streams()
    for row in s['state']:
      row.pop('rate')
    a, c = alignment.build(s, 'a'*64, 0, 0)
    self.assertEqual(c['required_field_coverage']['state.rate'], 0)
    self.assertFalse(a['causal_required_valid'].any())

  def test_segment_and_route_origins(self):
    a, _ = alignment.build(streams(), 'a'*64, 8, 100)
    self.assertEqual(a['segment_ordinal'].tolist(), [8]*80)
    self.assertEqual(a['route_global_row_index'].tolist(), list(range(100, 180)))
    self.assertEqual(a['aligned_row_index'].tolist(), list(range(80)))

  def test_segments_never_share_history(self):
    a, _ = alignment.build(streams(), 'a'*64, 0, 0)
    b, _ = alignment.build(streams(), 'a'*64, 1, 80)
    self.assertEqual(a['within_causal_run_index'][0], 0)
    self.assertEqual(b['within_causal_run_index'][0], 0)

  def test_run_identity_invalid_is_nullable(self):
    s = streams()
    s['state'][40]['rate'] = None
    a, _ = alignment.build(s, 'a'*64, 0, 0)
    self.assertEqual(a['causal_run_id'][40], -1)
    self.assertEqual(a['within_causal_run_index'][41], 0)

  def test_legacy_history_45_support(self):
    _, c = alignment.build(streams(80), 'a'*64, 0, 0)
    self.assertEqual(c['bins']['LOW']['common_design_rows'], 36)

  def test_legacy_mask_speed_boundary(self):
    s = streams()
    for row in s['state'][40:]:
      row['speed_mps'] = 20.
    _, c = alignment.build(s, 'a'*64, 0, 0)
    self.assertEqual(c['bins']['LOW']['common_design_rows'], 0)
    self.assertEqual(c['bins']['MEDIUM']['common_design_rows'], 0)

  def test_no_active_or_override_filter_on_base_rows(self):
    s = streams()
    for row in s['state']:
      row['driver_pressed'] = True
    a, c = alignment.build(s, 'a'*64, 0, 0)
    self.assertEqual(c['total_grid_samples'], 80)
    self.assertEqual(c['diagnostic_valid'], 0)
    self.assertTrue(a['state.driver_pressed'].all())

  def test_distinct_command_stages(self):
    a, _ = alignment.build(streams(), 'a'*64, 0, 0)
    self.assertTrue((a['control.requested'] != a['command.normalized']).all())
    self.assertTrue((a['command.raw'] != a['command.normalized']).all())

  def test_source_ages_preserved(self):
    a, _ = alignment.build(streams(), 'a'*64, 0, 0)
    self.assertEqual(a['command.age_ns'].tolist(), [1]*80)
    self.assertEqual(a['control.age_ns'].tolist(), [2]*80)

  def test_max_age_exact_boundary(self):
    s = streams(5)
    s['command'] = [s['command'][0]]
    a, _ = alignment.build(s, 'a'*64, 0, 0)
    self.assertTrue(a['command.raw.available'][1])
    self.assertFalse(a['command.raw.available'][2])

  def test_repeated_target_not_live_updated(self):
    s = streams()
    s['state'].pop(20)
    a, _ = alignment.build(s, 'a'*64, 0, 0)
    self.assertFalse(a['state.new_event_since_grid'][20])
    self.assertNotIn('live_updated', a)

  def test_event_valid_separate_from_presence(self):
    s = streams()
    s['state'][20]['valid'] = False
    a, _ = alignment.build(s, 'a'*64, 0, 0)
    self.assertTrue(a['state.present'][20])
    self.assertTrue(a['state.rate.available'][20])
    self.assertEqual(a['state.event_valid'][20], 0)
    self.assertFalse(a['causal_required_valid'][20])

  def test_source_gap_breaks_causal_history(self):
    s = streams()
    for k in ('state', 'command', 'control'):
      s[k] = s[k][:20]+s[k][24:]
    a, c = alignment.build(s, 'a'*64, 0, 0)
    self.assertGreater(c['mask_reason_counts']['SOURCE_EVENT_GAP'], 0)
    self.assertGreater(len(set(a['causal_run_id'])), 1)

  def test_clock_regression_all_required_streams(self):
    for kind in ('state', 'control', 'command'):
      s = streams()
      s[kind][1]['time_ns'] = s[kind][0]['time_ns']-1
      with self.subTest(kind=kind), self.assertRaises(ValueError):
        alignment.build(s, 'a'*64, 0, 0)

  def test_gyro_device_axes_not_vehicle_yaw(self):
    s = streams()
    s['gyro'] = [{'time_ns': r['time_ns']-3, 'sensor_ns': r['time_ns']-4, 'valid': True,
                   'source': 'lsm6ds3', 'xyz': [1., 2., 3.]} for r in s['state']]
    a, c = alignment.build(s, 'a'*64, 0, 0)
    self.assertEqual(c['gyro_xyz_available'], 80)
    self.assertEqual(a['gyro.xyz'][0].tolist(), [1., 2., 3.])
    self.assertNotIn('vehicle_yaw_truth', a)

  def test_future_gyro_acquisition_rejected(self):
    s = streams()
    s['gyro'] = [{'time_ns': r['time_ns']-1, 'sensor_ns': r['time_ns']+1, 'valid': True,
                   'source': 'lsm6ds3', 'xyz': [1., 2., 3.]} for r in s['state']]
    a, c = alignment.build(s, 'a'*64, 0, 0)
    self.assertEqual(c['gyro_xyz_available'], 0)
    self.assertTrue(np.isnan(a['gyro.xyz']).all())

  def test_gyro_acquisition_regression_not_silently_fixed(self):
    s = streams()
    s['gyro'] = [{'time_ns': r['time_ns']-1, 'sensor_ns': 1, 'valid': True,
                   'source': 'lsm6ds3', 'xyz': [1., 2., 3.]} for r in s['state']]
    _, c = alignment.build(s, 'a'*64, 0, 0)
    self.assertEqual(c['gyro_acquisition_clock_failures'], 79)
    self.assertEqual(c['gyro_xyz_available'], 0)

  def test_input_snapshot_changes_with_rate(self):
    s = streams()
    a, _ = alignment.build(s, 'a'*64, 0, 0)
    s['state'][10]['rate'] = 8.
    b, _ = alignment.build(s, 'a'*64, 0, 0)
    self.assertNotEqual(a['consumed_input_snapshot_sha256'][10], b['consumed_input_snapshot_sha256'][10])

  def test_snapshot_excludes_future(self):
    s = streams()
    a, _ = alignment.build(s, 'a'*64, 0, 0)
    s['state'][-1]['angle_deg'] += 1.
    b, _ = alignment.build(s, 'a'*64, 0, 0)
    self.assertEqual(a['consumed_input_snapshot_sha256'][:-1].tobytes(), b['consumed_input_snapshot_sha256'][:-1].tobytes())

  def test_config_snapshot_identity_changes_rows(self):
    a, _ = alignment.build(streams(), 'a'*64, 0, 0)
    b, _ = alignment.build(streams(), 'b'*64, 0, 0)
    self.assertNotEqual(a['consumed_input_snapshot_sha256'].tobytes(), b['consumed_input_snapshot_sha256'].tobytes())

  def test_segment_rotation_not_config_increment(self):
    a, _ = alignment.build(streams(), 'a'*64, 0, 0)
    b, _ = alignment.build(streams(), 'a'*64, 1, 80)
    self.assertEqual(set(a['config_sequence']), {0})
    self.assertEqual(set(b['config_sequence']), {0})

  def test_null_limit_and_physical_ack_mapping(self):
    from openpilot.tools.cyber_autotune import empirical_causal_dataset_execution as execution
    self.assertIsNone(execution.mapping()['physical_applied_torque'])
    self.assertIsNone(execution.mapping()['actual_curvature'])
    self.assertIn('live_updated', execution.mapping()['unavailable'])

  def test_no_forbidden_union_access(self):
    for kind in ('modelV2', 'lateralPlan', 'longitudinalPlan', 'gpsLocation', 'gpsLocationExternal',
                 'cameraOdometry', 'liveCalibration', 'liveLocationKalman', 'roadEncodeData', 'radarState'):
      class Event:
        def which(self, event_kind=kind):
          return event_kind
        def __getattr__(self, name):
          raise AssertionError('forbidden body '+name)
      with self.subTest(kind=kind):
        self.assertEqual(reader.numeric([Event()])['state'], [])


class TestCausalPersistenceAndAuthority(unittest.TestCase):
  def test_absolute_path_required(self):
    with self.assertRaises(ValueError):
      storage.safe('relative/output')

  def test_traversal_rejected(self):
    with self.assertRaises(ValueError):
      storage.safe('/tmp/a/../b')

  def test_receipt_symlink_rejected(self):
    with TemporaryDirectory() as d:
      a, b = Path(d)/'receipt.json', Path(d)/'alias.json'
      from openpilot.tools.cyber_autotune import empirical_plant_policy as p
      p.persist(a, p.seal({'schema': 'TEST'}))
      b.symlink_to(a)
      with self.assertRaises(ValueError):
        policy.read(b)

  def test_object_arrays_rejected(self):
    with TemporaryDirectory() as d, self.assertRaises(ValueError):
      storage.array_write(Path(d)/'x.npy', np.array([{}], dtype=object))

  def test_interrupted_array_resume(self):
    with TemporaryDirectory() as d:
      path = Path(d)/'x.npy'
      original = storage.array_write(path, np.arange(5, dtype='<i8'))
      path.rename(path.with_name('x.npy.atomic'))
      resumed = storage.array_write(path, np.arange(5, dtype='<i8'))
      self.assertEqual(original, resumed)
      self.assertFalse(path.with_name('x.npy.atomic').exists())

  def test_interrupted_conflict_rejected(self):
    with TemporaryDirectory() as d:
      path = Path(d)/'x.npy'
      storage.array_write(path, np.arange(5))
      path.rename(path.with_name('x.npy.atomic'))
      with self.assertRaises(ValueError):
        storage.array_write(path, np.arange(6))

  def test_array_manifest_exact_dtype_shape(self):
    with TemporaryDirectory() as d:
      a = np.arange(10, dtype='<f8').reshape(5, 2)
      x = storage.array_write(Path(d)/'x.npy', a)
      self.assertEqual(x['dtype'], '<f8')
      self.assertEqual(x['shape'], [5, 2])
      np.testing.assert_array_equal(np.load(Path(d)/'x.npy', allow_pickle=False), a)

  def test_input_pins_reject_wrong_role_set(self):
    x = policy.inputs()
    x['empirical-plant-v2-train-dev-split-v1.json']['routes'][0]['role'] = 'DEVELOPMENT'
    with self.assertRaises(ValueError):
      policy.resolve_routes(x)

  def test_zero_support_route_excluded(self):
    x = policy.inputs()
    ids = {r['route_id'] for r in policy.resolve_routes(x)}
    zero = {r['route_id'] for r in x['empirical-plant-v2-train-dev-split-v1.json']['routes'] if r['role'] == 'DEVELOPMENT'}
    self.assertFalse(ids & zero)

  def test_partial_class_rejected(self):
    x = policy.inputs()
    for c in x['empirical-source-equivalence-classes-v1.json']['classes']:
      c['status'] = 'SOURCE_AUDIT_PARTIAL'
    with self.assertRaises(ValueError):
      policy.resolve_routes(x)

  def test_historical_wrong_full_profile_rejected(self):
    x = policy.inputs()
    x['empirical-plant-v2-train-dev-split-v1.json']['routes'][0]['full_carparams_sha256'] = 'x'*64
    with self.assertRaises(ValueError):
      policy.resolve_routes(x)

  def test_wrong_fold_inversion_rejected(self):
    x = policy.inputs()
    x['empirical-plant-v3-folds-v1.json']['folds'].pop()
    with self.assertRaises(ValueError):
      policy.resolve_routes(x)

  def test_no_models_or_controller_imports(self):
    import ast
    base = Path(policy.__file__).parent
    forbidden = ('empirical_plant_model', 'empirical_v2_signals', 'empirical_signal_reader', 'latcontrol', 'trajectory_v0',
                 'smoothness_v0', 'smoothness_closed_loop', 'panda', 'Params')
    for name in policy.MODULES:
      tree = ast.parse((base/('empirical_causal_dataset_'+name+'.py')).read_bytes())
      for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
          content = ast.unparse(node)
          self.assertFalse(any(f in content for f in forbidden), content)

  def test_no_background_automation_or_search(self):
    self.assertEqual(policy.policy()['candidate_execution'], 'NOT_RUN')
    self.assertEqual(policy.policy()['model_fitting'], 'NOT_RUN')
    self.assertFalse(policy.policy()['candidate_search_authorized'])

  def test_calibration_and_authority_blockers(self):
    x = policy.policy()
    self.assertIn('METRIC_CALIBRATION_UNAVAILABLE', x['calibration_blockers'])
    self.assertFalse(x['production_authority'])
    self.assertFalse(x['vehicle_activation_allowed'])
    self.assertEqual(x['opening_count'], 0)
    self.assertEqual(x['reservation'], 'NONE')

  def test_no_model_coefficients_artifact(self):
    x = policy.policy()
    self.assertNotIn('coefficients', x)
    self.assertEqual(x['model_selection'], 'NOT_RUN')


class TestCausalPublication(unittest.TestCase):
  def test_rows_not_publishable(self):
    from openpilot.tools.cyber_autotune import empirical_causal_dataset_publication as public
    from openpilot.tools.cyber_autotune import empirical_plant_policy as p
    for key in ('rows', 'targets', 'predictions', 'coefficients', 'xyz', 'state_time_ns', 'row_origin'):
      with self.subTest(key=key), self.assertRaises(ValueError):
        public.validate_public(p.seal({'schema': 'TEST', key: [1., 2.]}))

  def test_relative_public_source_path_allowed(self):
    from openpilot.tools.cyber_autotune import empirical_causal_dataset_publication as public
    from openpilot.tools.cyber_autotune import empirical_plant_policy as p
    public.validate_public(p.seal({'files': {'role': {'path': 'opendbc/car/car.capnp', 'file_sha256': 'a'*64}}}))

  def test_files_exemption_cannot_publish_rows(self):
    from openpilot.tools.cyber_autotune import empirical_causal_dataset_publication as public
    from openpilot.tools.cyber_autotune import empirical_plant_policy as p
    with self.assertRaises(ValueError):
      public.validate_public(p.seal({'files': {'rows': [1., 2.]}}))

  def test_private_path_rejected(self):
    from openpilot.tools.cyber_autotune import empirical_causal_dataset_publication as public
    from openpilot.tools.cyber_autotune import empirical_plant_policy as p
    with self.assertRaises(ValueError):
      public.validate_public(p.seal({'store': '/private-store/not-publishable'}))

  def test_qlog_is_not_execution_authority(self):
    x = policy.policy()
    self.assertEqual(x['raw_kind_allowlist'], ['rlog.zst'])
    self.assertIn('HARD_BLOCK', x['historical_qlog_policy'])

  def test_excluded_qlog_cannot_enter_authorization(self):
    from openpilot.tools.cyber_autotune import empirical_plant_policy as p
    auth = p.seal({'segments': {'a'*64: ['b'*64]}, 'excluded_sources': {'a'*64: ['c'*64]}})
    with self.assertRaises(ValueError):
      policy.require_segment(auth, 'a'*64, 'c'*64)

  def test_complete_lineage_required_for_readiness(self):
    from openpilot.tools.cyber_autotune import empirical_causal_dataset_execution as execution
    import inspect
    source = inspect.getsource(execution.route_summary)
    self.assertIn("not route['excluded_sources']", source)
    self.assertIn("all(aggregate_checks.values())", source)


class TestCausalEvidenceChain(unittest.TestCase):
  def test_actual_public_chain(self):
    from openpilot.tools.cyber_autotune import empirical_causal_dataset_publication as public
    x = public.load()
    self.assertEqual(len(x), 11)

  def altered(self, index, key, value):
    from openpilot.tools.cyber_autotune import empirical_causal_dataset_publication as public
    from openpilot.tools.cyber_autotune import empirical_plant_policy as p
    x = public.load()
    row = x[public.FILES[index]]
    row.pop('receipt_sha256')
    row[key] = value
    x[public.FILES[index]] = p.seal(row)
    with self.assertRaises(ValueError):
      public.validate_chain(x)

  def test_resealed_repeat_receipt_rejected(self):
    self.altered(9, 'repeats', 1)

  def test_resealed_repeat_dataset_rejected(self):
    self.altered(9, 'dataset_manifest_sha256', 'a'*64)

  def test_resealed_policy_rejected(self):
    self.altered(0, 'max_age_ns', 30_000_000)

  def test_resealed_legacy_receipt_rejected(self):
    self.altered(8, 'status', 'LEGACY_ALIGNMENT_REPRODUCED')

  def test_resealed_authorization_rejected(self):
    self.altered(2, 'private_authorization_sha256', 'a'*64)

  def test_resealed_readiness_opening_rejected(self):
    self.altered(10, 'opening_count', 1)

  def test_resealed_readiness_model_rejected(self):
    self.altered(10, 'model_selection', 'RUN')

  def test_resealed_readiness_promotion_rejected(self):
    self.altered(10, 'status', 'RETROSPECTIVE_CAUSAL_TRAIN_DEV_DATASET_READY')

  def test_resealed_exposure_role_rejected(self):
    from openpilot.tools.cyber_autotune import empirical_causal_dataset_publication as public
    from openpilot.tools.cyber_autotune import empirical_plant_policy as p
    x = public.load()
    row = x[public.FILES[1]]
    row.pop('receipt_sha256')
    row['routes'][0]['holdout_allowed'] = True
    x[public.FILES[1]] = p.seal(row)
    with self.assertRaises(ValueError):
      public.validate_chain(x)


class TestCausalConfiguration(unittest.TestCase):
  def sample(self):
    s = streams()
    s['init'] = [{'commit': 'c'*40, 'remote': 'https://github.com/ajouatom/openpilot', 'dirty': False, 'os_version': 'synthetic'}]
    s['profiles'] = [{'fields': {'flags': 0, 'steerControlType': 'torque'},
                      'full_carparams_sha256': 'a'*64, 'empirical_profile_sha256': 'b'*64}]
    route = {'source_commit': 'c'*40, 'full_carparams_sha256': 'a'*64, 'empirical_profile_sha256': 'b'*64}
    return s, route

  def test_dirty_build_rejected(self):
    s, r = self.sample()
    s['init'][0]['dirty'] = True
    with self.assertRaises(ValueError):
      reader.configuration(s, r)

  def test_source_commit_drift_rejected(self):
    s, r = self.sample()
    s['init'][0]['commit'] = 'd'*40
    with self.assertRaises(ValueError):
      reader.configuration(s, r)

  def test_remote_drift_rejected(self):
    s, r = self.sample()
    s['init'][0]['remote'] = 'https://example.invalid/other/repo'
    with self.assertRaises(ValueError):
      reader.configuration(s, r)

  def test_full_carparams_drift_rejected(self):
    s, r = self.sample()
    s['profiles'][0]['full_carparams_sha256'] = 'd'*64
    with self.assertRaises(ValueError):
      reader.configuration(s, r)

  def test_empirical_profile_drift_rejected(self):
    s, r = self.sample()
    s['profiles'][0]['empirical_profile_sha256'] = 'd'*64
    with self.assertRaises(ValueError):
      reader.configuration(s, r)

  def test_config_drift_rejected(self):
    s, r = self.sample()
    s['settings'].append({'CustomSteerMax': 408})
    with self.assertRaises(ValueError):
      reader.configuration(s, r)

  def test_missing_runtime_provenance_rejected(self):
    s, r = self.sample()
    s['settings'] = [{}]
    with self.assertRaises(ValueError):
      reader.configuration(s, r)

  def test_source_default_explicit_zero(self):
    s, r = self.sample()
    s['settings'] = [{'CustomSteerMax': 0}]
    self.assertEqual(reader.configuration(s, r)['runtime_steer_max'], 409)

  def test_wrong_runtime_max_rejected(self):
    s, r = self.sample()
    s['settings'] = [{'CustomSteerMax': 384}]
    with self.assertRaises(ValueError):
      reader.configuration(s, r)

  def test_angle_control_rejected(self):
    s, r = self.sample()
    s['profiles'][0]['fields']['steerControlType'] = 'angle'
    with self.assertRaises(ValueError):
      reader.configuration(s, r)


if __name__ == '__main__':
  unittest.main()
