import copy
import unittest

from openpilot.tools.cyber_autotune import controller_plant_publication as p
from openpilot.tools.cyber_autotune import controller_plant_authority as a


class TestAuthorityPublication(unittest.TestCase):
  def test_real_artifacts(self):
    reports = p.load()
    self.assertEqual(len(reports), 6)
    self.assertEqual(reports['audit']['historical_revalidated_cases'], 70)

  def test_resealed_nested_private_field(self):
    row = copy.deepcopy(p.load()['audit'])
    row['historical_bindings'][0]['private_path'] = 'private'
    with self.assertRaises(ValueError):
      p.validate(a.seal(row))

  def test_resealed_numerical_edit(self):
    row = copy.deepcopy(p.load()['control'])
    row['rows'][0]['amplitude'] = .9
    with self.assertRaises(ValueError):
      p.validate(a.seal(row))

  def test_no_acceptance(self):
    for row in p.load().values():
      self.assertFalse(row['candidate_acceptance_allowed'])
      self.assertFalse(row['vehicle_activation_allowed'])
      self.assertIsNone(row['total_physical_bound_m'])

  def test_verdicts_preserved(self):
    row = p.load()['audit']
    self.assertEqual(row['historical_verdicts']['V1'], 'TRADEOFF_ONLY')
    self.assertEqual(row['historical_verdicts']['V2'], 'REJECTED')
    self.assertEqual(row['v2_existing_violation_count'], 37)

  def test_geometry_oracles(self):
    r = p.load()['control']
    self.assertTrue(r['analytic_geometry_all_pass'])
    self.assertTrue(r['analytic_recurrence_all_pass'])

  def test_zero_alias(self):
    rows = p.load()['stage']['rows']
    self.assertTrue(all(r['maximum_pose_y_delta_m'] == 0. for r in rows if r['candidate'] == 'CURRENT'))

  def test_fixed_distance_no_extension(self):
    rows = p.load()['stage']['distances']
    self.assertTrue(all(r['classification'] is None and not r['meter_envelope_extended'] for r in rows))
    self.assertTrue(all(r['pose_y_delta_m'] is None for r in rows if r['status'] != 'AVAILABLE'))

  def test_open_blockers(self):
    r = p.load()['readiness']
    self.assertEqual(r['reference_calibration_track'], 'BLOCKED_UNCHANGED')
    self.assertEqual(r['reference_status'], 'INDEPENDENT_REFERENCE_UNAVAILABLE')
    self.assertIsNone(r['independent_meter_result'])

  def test_derivation_separate_from_historical(self):
    r = p.load()['audit']
    self.assertFalse(r['meter_envelope_recomputed'])
    self.assertFalse(r['candidate_mutation'])
    self.assertFalse(r['detector_mutation'])
    self.assertFalse(r['private_data_open'])

  def test_historical_archives_unchanged(self):
    from openpilot.tools.cyber_autotune import resolution_candidate_repeat as old
    for name in old.ARCHIVES:
      self.assertIsInstance(old.pinned(name), dict)

  def test_new_result_cannot_overwrite_old(self):
    import tempfile
    from pathlib import Path
    from openpilot.tools.cyber_autotune.resolution_candidate_repeat import immutable
    with tempfile.TemporaryDirectory() as temp:
      path = Path(temp) / 'historical.json'
      immutable(path, b'old')
      with self.assertRaises(ValueError):
        immutable(path, b'corrected')
      self.assertEqual(path.read_bytes(), b'old')

  def test_no_vehicle_authority_calls(self):
    import ast
    from pathlib import Path
    from openpilot.tools.cyber_autotune import controller_plant_evidence as e
    banned = {'Params', 'CarController', 'sendcan', 'put', 'put_bool', 'PubMaster'}
    for name in ('controller_plant_authority', 'controller_plant_experiment', 'controller_plant_evidence',
                 'controller_plant_findings', 'controller_plant_publication', 'controller_plant_visualizer'):
      tree = ast.parse(Path(e.__file__).with_name(name + '.py').read_text())
      calls = {node.func.id for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
      self.assertFalse(calls & banned)
