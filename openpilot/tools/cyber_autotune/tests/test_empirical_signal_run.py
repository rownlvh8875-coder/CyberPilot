import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from openpilot.tools.cyber_autotune import empirical_plant_policy as p


class TestProvenanceRun(unittest.TestCase):
  def setUp(self):
    self.assertIsNotNone(importlib.util.find_spec('openpilot.tools.cyber_autotune.empirical_signal_run'), 'provenance runner missing')
    from openpilot.tools.cyber_autotune import empirical_signal_run as r

    self.r = r

  def test_holdout_requires_frozen_selection(self):
    with self.assertRaises(ValueError):
      self.r.open_gate('YAW_HOLDOUT', None, None, None)

  def test_wrong_freeze_binding_rejected(self):
    selection = p.seal({'schema': 'EMPIRICAL_PROVENANCE_SELECTION_V1', 'binding_sha256': 'a' * 64})
    binding = p.seal({'schema': 'EMPIRICAL_PROVENANCE_EXECUTION_V1'})
    freeze = p.seal({'schema': 'EMPIRICAL_YAW_FREEZE_V1', 'selection_sha256': selection['receipt_sha256'], 'binding_sha256': 'b' * 64})
    with self.assertRaises(ValueError):
      self.r.open_gate('YAW_HOLDOUT', freeze, selection, binding)

  def test_train_without_holdout_receipt(self):
    self.r.open_gate('TRAIN', None, None, None)

  def test_unknown_role_rejected(self):
    with self.assertRaises(ValueError):
      self.r.open_gate('TA_B', None, None, None)

  def test_wrong_source_commit_rejected(self):
    source = p.verify(json.loads((p.PUBLIC / 'empirical-yaw-source-audit-v1.json').read_bytes()))
    source['commit'] = '0' * 40
    source = p.seal({k: v for k, v in source.items() if k != 'receipt_sha256'})
    with self.assertRaises(ValueError):
      self.r.source_gate(source)

  def test_empty_dbc_unit_preserved(self):
    source = p.verify(json.loads((p.PUBLIC / 'empirical-yaw-source-audit-v1.json').read_bytes()))
    self.r.source_gate(source)
    self.assertEqual(source['yaw_dbc']['unit'], '')

  def test_resealed_source_fact_change_rejected(self):
    source = json.loads((p.PUBLIC / 'empirical-yaw-source-audit-v1.json').read_bytes())
    source['default_steer_max_santa_fe_legacy'] = 384
    with self.assertRaises(ValueError):
      self.r.source_gate(p.seal({k: v for k, v in source.items() if k != 'receipt_sha256'}))

  def test_stage_a_gate_not_redefined(self):
    self.assertFalse(self.r.stage_c_allowed(True))
    self.assertEqual(self.r.historical()['stage_a'], 'STRICT_READY_GATE_FAILED')

  def test_ta_sg_forbidden(self):
    self.assertFalse(self.r.historical()['ta_execution'])
    self.assertFalse(self.r.historical()['sg_execution'])
    self.assertFalse(self.r.historical()['composition_authorized'])

  def test_private_store_cannot_alias_prior(self):
    with tempfile.TemporaryDirectory() as t:
      with self.assertRaises(ValueError):
        self.r.store_gate(Path(t) / 'same', Path(t) / 'same')

  def test_private_store_cannot_be_in_repo(self):
    with self.assertRaises(ValueError):
      self.r.store_gate(p.PUBLIC / 'private', Path('/nonexistent-prior'))

  def test_symlink_store_rejected(self):
    with tempfile.TemporaryDirectory() as t:
      root = Path(t)
      (root / 'real').mkdir()
      (root / 'alias').symlink_to(root / 'real', target_is_directory=True)
      with self.assertRaises(ValueError):
        self.r.store_gate(root / 'alias' / 'child', root / 'prior')

  def test_no_public_private_trace(self):
    name = 'empirical-command-bridge-v1.json'
    with self.assertRaises(ValueError):
      self.r.publication_guard(name, p.seal({'schema': 'X', 'yaw_trace': [1.0, 2.0]}))

  def test_unknown_public_filename(self):
    with self.assertRaises(ValueError):
      self.r.publication_guard('../../private.json', p.seal({'schema': 'X'}))

  def test_historical_receipts_revalidated(self):
    rows = self.r.historical()
    self.assertEqual(rows['v2'], 'REJECTED')
    self.assertEqual(rows['v2_violations'], 37)
    self.assertEqual(rows['calibration_blockers'], p.BLOCKERS)

  def test_no_model_ready_from_missing_support(self):
    self.assertFalse(self.r.ready_rule({'status': 'UNAVAILABLE'}))

  def test_strict_naive_gate_preserved(self):
    metric = {'count': 300, 'MAE': 1.0, 'RMSE': 1.0, 'P95_ABS': 1.0}
    group = {name: dict(metric) for name in ['model', 'ZERO_RESPONSE', 'HOLD_LAST_OUTPUT', 'TRAIN_STATIC_GAIN']}
    result = {'status': 'EVALUATED', 'one_step': group, 'rollout': {'100': group}}
    self.assertFalse(self.r.ready_rule(result))

  def test_model_unit_is_yaw_not_steering(self):
    self.assertEqual(self.r.yaw_result_unit({'status': 'EVALUATED', 'unit': 'STEERING_ANGLE_DEGREES'})['unit'], 'YAW_RAD_PER_S_CONDITIONAL')

  def test_inherited_model_source_bound(self):
    from unittest.mock import patch

    with tempfile.TemporaryDirectory() as t:
      path = Path(t) / 'model.py'
      path.write_text('original')
      with patch.object(self.r.m, '__file__', str(path)):
        first = self.r.source_identity()
        path.write_text('changed inherited model')
        self.assertNotEqual(first, self.r.source_identity())

  def test_missing_settings_cannot_admit_fit(self):
    roles = {
      'TRAIN': [{'settings_sha256': 'a', 'runtime_setting_known': False}],
      'DEVELOPMENT': [{'settings_sha256': 'a', 'runtime_setting_known': False}],
      'COMMAND_BRIDGE_ONLY': [{'settings_sha256': 'a', 'runtime_setting_known': True}],
    }
    self.assertFalse(self.r.settings_complete(roles))

  def test_old_holdout_settings_do_not_influence_fit(self):
    roles = {
      'TRAIN': [{'settings_sha256': 'a', 'runtime_setting_known': True}],
      'DEVELOPMENT': [{'settings_sha256': 'a', 'runtime_setting_known': True}],
      'COMMAND_BRIDGE_ONLY': [{'settings_sha256': 'b', 'runtime_setting_known': False}],
    }
    self.assertTrue(self.r.settings_complete(roles))

  def test_output_gap_not_limit_evidence(self):
    streams = {
      'command': [{'time_ns': 0, 'normalized': 0.0, 'valid': True}, {'time_ns': 1000000000, 'normalized': 0.1, 'valid': True}],
      'control': [{'time_ns': 0, 'requested': 0.9, 'valid': True}],
      'state': [],
    }
    self.assertEqual(self.r._limit_comparison(streams)['pairs'], 0)

  def test_resealed_old_split_rejected(self):
    rows = self.r.oldpub.load()
    with self.assertRaises(ValueError):
      self.r.prior_gate(p.seal({'segments': []}), p.seal({}), p.seal({}), p.seal({}), rows)

  def test_numeric_resume_never_reopens_payload(self):
    from unittest.mock import patch

    with tempfile.TemporaryDirectory() as t:
      path = Path(t) / 'numeric.json'
      expected = {'segment_id': 'a', 'role': 'YAW_HOLDOUT', 'binding_sha256': 'b'}
      numeric = p.seal({'schema': 'EMPIRICAL_PROVENANCE_NUMERIC_V1', **expected, 'streams': {'cached': True}, 'payload_repeats': 1})
      p.persist(path, numeric)
      with patch.object(self.r.s, 'events', side_effect=AssertionError('raw reopened')):
        actual = self.r.numeric_once(path, expected, Path(t) / 'raw', None, True)
      self.assertEqual(actual, numeric)

  def test_complete_yaw_verdict_publication(self):
    row = p.seal(
      {
        'schema': 'EMPIRICAL_YAW_VERDICT_V1',
        'binding_sha256': 'a' * 64,
        'status': 'YAW_UNIT_SUPPORTED_FRAME_PARTIAL',
        'unit_status': 'YAW_UNIT_EMPIRICALLY_SUPPORTED',
        'device_frame': 'DEVICE_AXIS_CORRESPONDENCE_ONLY',
        'vehicle_frame_calibrated': False,
        'rigid_transform': None,
        'fitting_allowed': False,
        'fitting_gates': dict.fromkeys(self.r.q.GATES, False),
        'hypothesis': 'YAW_H1',
        'gyro_candidate': {'axis': 0, 'sign': 1, 'lag_samples': 0},
        'source_unit_string': self.r.public_yaw_unit(),
        'holdout_used_for_selection': False,
      }
    )
    self.r.publication_guard('empirical-yaw-verdict-v1.json', row)
    self.assertEqual(self.r.public_yaw_unit(), 'EMPTY_DBC_UNIT_UNVERIFIED')

  def test_atomic_numeric_resume_never_reopens(self):
    from unittest.mock import patch

    with tempfile.TemporaryDirectory() as t:
      path = Path(t) / 'numeric.json'
      expected = {'segment_id': 'a', 'role': 'YAW_HOLDOUT', 'binding_sha256': 'b'}
      numeric = p.seal({'schema': 'EMPIRICAL_PROVENANCE_NUMERIC_V1', **expected, 'streams': {'cached': True}, 'payload_repeats': 1})
      path.with_name(path.name + '.atomic').write_text(json.dumps(numeric))
      with patch.object(self.r.s, 'events', side_effect=AssertionError('raw reopened')):
        self.assertEqual(self.r.numeric_once(path, expected, Path(t) / 'raw', None, True), numeric)

  def test_gyro_clock_regression_rejects_whole_stream(self):
    streams = {
      'state': [],
      'command': [],
      'control': [],
      'settings': [],
      'gyro_rejected': 0,
      'gyro': [{'time_ns': 10, 'sensor_ns': 9, 'valid': True, 'xyz': [0.0, 0.0, 0.0]}, {'time_ns': 20, 'sensor_ns': 8, 'valid': True, 'xyz': [0.0, 0.0, 0.0]}],
    }
    aligned, rejected, reason = self.r.checked_alignment(streams)
    self.assertEqual(rejected, 2)
    self.assertEqual(reason, 'GYRO_TIMELINE_REJECTED_WHOLE_SEGMENT')
    self.assertEqual(aligned['rows'], [])
    self.assertEqual(len(streams['gyro']), 2)

  def test_valid_gyro_keeps_exact_alignment(self):
    streams = {'state': [], 'command': [], 'control': [], 'settings': [], 'gyro_rejected': 0, 'gyro': []}
    aligned, rejected, reason = self.r.checked_alignment(streams)
    self.assertEqual(aligned, self.r.r.aligned(streams))
    self.assertEqual(rejected, 0)
    self.assertIsNone(reason)
