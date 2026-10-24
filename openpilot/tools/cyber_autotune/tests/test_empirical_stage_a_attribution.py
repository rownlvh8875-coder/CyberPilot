"""Source and immutable derivative boundaries; no private store needed in CI."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from openpilot.tools.cyber_autotune import empirical_stage_a_attribution as a
from openpilot.tools.cyber_autotune import empirical_stage_a_regime as r
from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_v3_publication as v3


class TestAttribution(unittest.TestCase):
  def test_old_artifacts_pinned(self):
    self.assertEqual(len(v3.load()), 9)

  def test_only_six_selected_folds(self):
    folds = a.selected()
    self.assertEqual(len(folds), 6)
    self.assertEqual({x['config']['family'] for x in folds}, {'ARX1'})
    self.assertEqual({x['config']['delay_samples'] for x in folds}, {5})

  def test_full_route_ids_read_from_artifacts(self):
    self.assertEqual(len({x['development_route'] for x in a.selected()}), 2)
    self.assertTrue(all(len(x['development_route']) == 64 for x in a.selected()))

  def test_source_binding(self):
    row = a.source_contract()
    self.assertEqual(row['step_deg'], 0.1)
    self.assertEqual(row['offset_deg'], 0)
    self.assertEqual(row['storage'], 'Float32')
    self.assertEqual(len(row['dbc']['file_sha256']), 64)

  def test_dbc_conflict(self):
    with self.assertRaises(ValueError):
      a.parse_dbc('SG_ SAS_Angle : 0|16@1- (0.2,0.0) [-3276.8|3276.7] "Deg"')

  def test_wrong_unit(self):
    with self.assertRaises(ValueError):
      a.parse_dbc('SG_ SAS_Angle : 0|16@1- (0.1,0.0) [-3276.8|3276.7] "rad"')

  def test_policy_freeze_required(self):
    with tempfile.TemporaryDirectory() as d:
      with self.assertRaises(FileNotFoundError):
        a.require_frozen(Path(d))

  def test_private_store_no_overwrite(self):
    with tempfile.TemporaryDirectory() as d:
      row = p.seal({'a': 1})
      p.persist(Path(d) / 'test.json', row)
      with self.assertRaises(ValueError):
        p.persist(Path(d) / 'test.json', p.seal({'a': 2}))

  def test_array_digest_before_load(self):
    with tempfile.TemporaryDirectory() as d:
      file = Path(d) / 'one_step.npy'
      np.save(file, np.zeros((1, 5)))
      with patch.object(np, 'load', side_effect=AssertionError('must not open values')):
        with self.assertRaisesRegex(ValueError, 'DERIVATIVE_HASH_MISMATCH'):
          a.load_array(file, '0' * 64)

  def test_bad_array_shape(self):
    with self.assertRaises(ValueError):
      a.validate_pair(np.zeros((2, 3)), np.zeros((3, 5)))

  def test_past_measurement_identity(self):
    with self.assertRaisesRegex(ValueError, 'PAST_MEASUREMENT_MISMATCH'):
      a.validate_pair(np.zeros((2, 3)), np.ones((2, 5)))

  def test_no_private_public_fields(self):
    for key in ('predictions', 'residuals', 'coefficients', 'command_raw', 'angle_deg'):
      with self.assertRaises(ValueError):
        a.validate_public(p.seal({key: [1]}))

  def test_no_absolute_private_path(self):
    with self.assertRaises(ValueError):
      a.validate_public(p.seal({'path': '/private/store'}))

  def test_no_refit_execution_api(self):
    text = Path(a.__file__).read_text()
    for token in ('m.fit(', 'm.select(', 'log_events(', 'cross.run(', 'predictions('):
      self.assertNotIn(token, text)

  def test_no_raw_access(self):
    text = Path(a.__file__).read_text()
    self.assertNotIn('/mnt/d', text)
    self.assertNotIn('empirical-plant-v2-train-dev-v1', text)

  def test_nonexecuting_authority(self):
    for name, value in p.FIREWALL.items():
      self.assertFalse(value, name)

  def test_historical_stage_b_holdout(self):
    old = v3.load()['empirical-plant-v3-readiness-v1.json']
    self.assertEqual(old['stage_b_state'], 'STAGE_B_SIGNAL_ADMISSION_BLOCKED')
    self.assertEqual(old['one_time_opening_state'], 'CLOSED')
    self.assertEqual(old['calibration_blockers'], p.BLOCKERS)

  def test_policy_contains_exact_source(self):
    with patch.object(a, 'source_contract', return_value={'receipt_sha256': 'a' * 64, 'dbc': {'file_sha256': 'b' * 64}}):
      row = a.policy()
    self.assertEqual(row['exact_dbc_sha256'], 'b' * 64)
    self.assertEqual(row['numeric_raw_opening'], 'PROHIBITED')
    self.assertEqual(row['rule_combination_search'], False)

  def test_outcomes_never_causal_fields(self):
    self.assertFalse(any(k.startswith('TARGET_') for k in r.availability()))

  def test_unavailable_not_false(self):
    for k, v in r.availability().items():
      if k != r.CAUSAL_BOUNDARY:
        self.assertEqual(v['status'], 'UNAVAILABLE')


class TestStoreBoundaries(unittest.TestCase):
  def test_repository_private_store_forbidden(self):
    with self.assertRaises(ValueError):
      a.private_store(Path(a.__file__).parent / 'private')

  def test_nested_store_forbidden(self):
    with tempfile.TemporaryDirectory() as d:
      with self.assertRaises(ValueError):
        a.distinct_stores(Path(d), Path(d) / 'attribution')

  def test_same_store_forbidden(self):
    with tempfile.TemporaryDirectory() as d:
      with self.assertRaises(ValueError):
        a.distinct_stores(d, d)

  def test_symlink_derivative_rejected(self):
    with tempfile.TemporaryDirectory() as d:
      source = Path(d) / 'actual.npy'
      np.save(source, np.zeros((1, 5)))
      link = Path(d) / 'link.npy'
      link.symlink_to(source)
      with self.assertRaisesRegex(ValueError, 'NO_SYMLINK_DERIVATIVE'):
        a.load_array(link, p.sha(source.read_bytes()))


class TestRepeatabilityGuard(unittest.TestCase):
  def test_valid_repeat(self):
    a.validate_repeatability({'runs': 2, 'exact_repeatability': True, 'result_sha256': 'a'}, 'a')

  def test_stale_repeat(self):
    with self.assertRaises(ValueError):
      a.validate_repeatability({'runs': 2, 'exact_repeatability': True, 'result_sha256': 'b'}, 'a')

  def test_false_repeat(self):
    with self.assertRaises(ValueError):
      a.validate_repeatability({'runs': 2, 'exact_repeatability': False, 'result_sha256': 'a'}, 'a')

  def test_wrong_run_count(self):
    with self.assertRaises(ValueError):
      a.validate_repeatability({'runs': 1, 'exact_repeatability': True, 'result_sha256': 'a'}, 'a')
