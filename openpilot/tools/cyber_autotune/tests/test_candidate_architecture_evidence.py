"""Frozen policy and source bindings; historical artifacts remain read-only."""
from copy import deepcopy
import tempfile
import unittest
from pathlib import Path

from openpilot.tools.cyber_autotune import candidate_architecture as a
from openpilot.tools.cyber_autotune import candidate_architecture_evidence as e
from openpilot.tools.cyber_autotune import candidate_architecture_policy as p
from openpilot.tools.cyber_autotune import candidate_role_contracts as c
from openpilot.tools.cyber_autotune.controller_plant_publication import load


class TestArchitectureEvidence(unittest.TestCase):
  def test_build_deterministic(self):
    self.assertEqual(e.build(), e.build())

  def test_role_schemas(self):
    r = e.build()
    self.assertNotIn('tracking_error', r['smoothness']['input_schema']['command'])
    self.assertNotIn('desired_curvature_1pm', r['smoothness']['input_schema']['intervention'])

  def test_reference_graph_unchanged(self):
    self.assertEqual(e.build()['readiness']['reference_blocker_graph'], load()['readiness']['blockers'])

  def test_receipt_binding(self):
    for row in e.build().values():
      body = {k: v for k, v in row.items() if k != 'receipt_sha256'}
      self.assertEqual(row['receipt_sha256'], a.hash_object(body))

  def test_no_history_reinterpretation(self):
    r = e.build()['decision']
    self.assertEqual(r['historical_candidate_role'], 'MIXED_HISTORICAL_NO_RETROACTIVE_RECLASSIFICATION')
    self.assertEqual(r['historical_authority_audit_sha256'], load()['audit']['receipt_sha256'])

  def test_sources_bound(self):
    for r in e.injection_points():
      self.assertEqual(r['source_sha256'], e.digest((a.ROOT / r['source_path']).read_bytes()))
      self.assertEqual(r['update_hz'], 100.)

  def test_no_candidate_algorithm(self):
    for r in e.build().values():
      self.assertFalse(r['actual_algorithm_implemented'])
      self.assertFalse(r['parameter_search_allowed'])
      self.assertFalse(r['production_authority'])

  def test_metric_threshold_pending(self):
    for role in ('TA', 'SG'):
      for row in p.metrics(role):
        self.assertIsNone(row['threshold'])
        self.assertEqual(row['threshold_status'], 'THRESHOLD_UNJUSTIFIED')

  def test_cross_objective_constraints(self):
    r = e.build()
    self.assertEqual(r['trajectory']['cross_objective_hard_constraints'], p.metrics('SG'))
    self.assertEqual(r['smoothness']['cross_objective_hard_constraints'], p.metrics('TA'))

  def test_family_not_selected(self):
    self.assertEqual(len(p.families()), 3)
    for r in p.families():
      self.assertFalse(r['algorithm_selected'])
      self.assertIsNone(r['parameter_ranges'])

  def test_write_immutable(self):
    with tempfile.TemporaryDirectory() as tmp:
      e.write_new(tmp)
      e.write_new(tmp)
      path = Path(tmp) / e.FILES['matrix']
      path.write_text('{}')
      with self.assertRaises(ValueError):
        e.write_new(tmp)

  def test_validation_content_drift(self):
    r = e.build()
    r['matrix']['composition_execution_allowed'] = True
    with self.assertRaises(ValueError):
      e.validate(r)

  def test_resealed_unauthorized_policy(self):
    r = e.build()
    r['matrix'] = e.seal({**r['matrix'], 'composition_execution_allowed': True})
    with self.assertRaises(ValueError):
      e.validate(r)

  def test_unknown_private_payload(self):
    r = e.build()
    r['readiness']['private_path'] = '/private/example'
    with self.assertRaises(ValueError):
      e.validate(r)

  def test_input_causality(self):
    values = {'desired_curvature_1pm': 0., 'actual_curvature_1pm': 0., 'speed_mps': 5., 'roll_rad': 0.,
              'time_s': 0., 'dt_s': .01, 'active': True, 'steering_pressed': False,
              'safety_limited': False, 'curvature_limited': False}
    first = c.TrajectoryInput.parse(values)
    second = c.TrajectoryInput.parse({**values, 'time_s': .01})
    a.validate_input_sequence((first, second))
    with self.assertRaises(ValueError):
      a.validate_input_sequence((second, first))

  def test_input_state_cross_arm_isolation(self):
    first = a.SmoothnessGovernor()
    second = a.SmoothnessGovernor()
    self.assertIsNot(first, second)
    self.assertEqual(first, second)

  def test_output_unknown_field(self):
    row = {'normalized_torque': 0., 'core_source_sha256': 'a'*64, 'core_config_sha256': 'b'*64, 'path': []}
    with self.assertRaises(ValueError):
      c.GovernorCommand.parse(row)

  def test_readiness_identity_distinct(self):
    r = e.build()
    self.assertNotEqual(r['trajectory']['identity'], r['smoothness']['identity'])

  def test_no_extended_meter_envelope(self):
    self.assertFalse(a.matrix()['secondary_meter_classification_allowed'])

  def test_copy_does_not_mutate_frozen_policy(self):
    altered = deepcopy(a.matrix())
    altered['roles']['FROZEN_EVALUATION'] = True
    with self.assertRaises(ValueError):
      a.validate_matrix(altered)
    self.assertFalse(a.matrix()['roles']['FROZEN_EVALUATION'])


class TestGovernorOutputIdentity(unittest.TestCase):
  def test_full_contract_identity_bound(self):
    from dataclasses import asdict
    command = c.GovernorCommand(.25, 'a'*64, 'b'*64)
    actual = a.SmoothnessGovernor().update(command, c.InterventionInput(0., .01, True, False, False, False))
    self.assertEqual(actual.governor_identity_sha256, a.hash_object(e.build()['smoothness']['identity']))
    self.assertEqual(actual.governor_identity_sha256, a.hash_object(asdict(a.identity('SG', a.governor_config()))))


class TestReviewRegressions(unittest.TestCase):
  def test_physical_plant_retained_across_interventions(self):
    table = {(owner, event): action for owner, event, action in a.RESETS}
    for event in ('INACTIVE', 'STEERING_PRESSED', 'RELEASE', 'REENGAGEMENT'):
      self.assertEqual(table['PLANT', event], 'RETAIN_PHYSICAL_STATE_AND_QUEUE')

  def test_identity_binds_probe_and_metric_policy(self):
    from unittest.mock import patch
    old = a.identity('TA', {})
    with patch.object(p, 'TRAJECTORY_METRICS', p.TRAJECTORY_METRICS[:-1]):
      self.assertNotEqual(old.experiment_policy_sha256, a.identity('TA', {}).experiment_policy_sha256)

  def test_identity_binds_fixture_policy(self):
    from unittest.mock import patch
    from openpilot.tools.cyber_autotune import candidate_architecture_probe as probe
    old = a.identity('TA', {})
    with patch.object(probe, 'ARC_LENGTH_M', 11.):
      self.assertNotEqual(old.experiment_policy_sha256, a.identity('TA', {}).experiment_policy_sha256)


class TestPublicationSafety(unittest.TestCase):
  def test_file_symlink_rejected(self):
    with tempfile.TemporaryDirectory() as tmp:
      e.write_new(tmp)
      path = Path(tmp) / e.FILES['matrix']
      target = Path(tmp) / 'unchanged.json'
      path.rename(target)
      path.symlink_to(target)
      with self.assertRaises(ValueError):
        e.write_new(tmp)

  def test_parent_symlink_rejected(self):
    with tempfile.TemporaryDirectory() as tmp:
      target = Path(tmp) / 'actual'
      target.mkdir()
      link = Path(tmp) / 'linked'
      link.symlink_to(target, target_is_directory=True)
      with self.assertRaises(ValueError):
        e.write_new(link)

  def test_integer_cannot_spoof_boolean_matrix(self):
    row = a.matrix()
    row['current_alias'] = 1
    with self.assertRaises(ValueError):
      a.validate_matrix(row)

  def test_output_input_roundtrip_exact(self):
    from dataclasses import asdict
    value = c.GovernorCommand(-.25, 'a'*64, 'b'*64)
    self.assertEqual(c.GovernorCommand.parse(asdict(value)), value)


class TestReceiptSealing(unittest.TestCase):
  def test_reseal_idempotent(self):
    row = e.seal({'schema': 'TEST'})
    self.assertEqual(e.seal(row), row)

  def test_correct_reseal_still_cannot_authorize(self):
    reports = e.build()
    reports['matrix'] = e.seal({**reports['matrix'], 'composition_execution_allowed': True})
    row = reports['matrix']
    self.assertEqual(row['receipt_sha256'], a.hash_object({k: v for k, v in row.items() if k != 'receipt_sha256'}))
    with self.assertRaises(ValueError):
      e.validate(reports)
