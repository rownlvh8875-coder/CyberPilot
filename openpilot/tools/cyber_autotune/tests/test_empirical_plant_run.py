import importlib.util
import unittest


class TestRun(unittest.TestCase):
  def setUp(self):
    self.assertIsNotNone(importlib.util.find_spec('openpilot.tools.cyber_autotune.empirical_plant_run'))
    from openpilot.tools.cyber_autotune import empirical_plant_run as r, empirical_plant_policy as p

    self.r, self.p = r, p

  def test_holdout_closed(self):
    self.assertRaises(ValueError, self.r.extraction_gate, 'HOLDOUT', None)

  def test_holdout_model_required(self):
    bad = self.p.seal({'schema': 'SOMETHING'})
    self.assertRaises(ValueError, self.r.extraction_gate, 'HOLDOUT', bad)

  def test_holdout_frozen_allowed(self):
    f = self.p.seal({'schema': 'EMPIRICAL_MODEL_FROZEN_V1', 'selection_sha256': 'a' * 64, 'models_sha256': 'b' * 64})
    with self.assertRaises(ValueError):
      self.r.extraction_gate('HOLDOUT', f)

  def test_unknown_role(self):
    self.assertRaises(ValueError, self.r.extraction_gate, 'CANDIDATE', None)

  def test_embargo_not_opened(self):
    self.assertRaises(ValueError, self.r.extraction_gate, 'EMBARGO', None)

  def test_ready_not_possible_missing_limits(self):
    self.assertEqual(self.r.verdict(True, True, False), 'EMPIRICAL_ACTUATOR_MODEL_ONLY')

  def test_no_model_partial(self):
    self.assertEqual(self.r.verdict(False, True, False), 'EMPIRICAL_PLANT_PARTIAL')

  def test_signal_unavailable(self):
    self.assertEqual(self.r.verdict(False, False, False), 'EMPIRICAL_SIGNAL_CHAIN_UNAVAILABLE')

  def test_no_yaw_invention(self):
    self.assertRaises(ValueError, self.r.verdict, True, True, True)

  def test_publication_no_coefficients(self):
    self.assertRaises(ValueError, self.r.publication_guard, {'coefficients': [1, 2]})

  def test_publication_no_timestamps(self):
    self.assertRaises(ValueError, self.r.publication_guard, {'x': [{'time_ns': 1}]})

  def test_authority_unchanged(self):
    self.assertFalse(self.p.FIREWALL['sg_execution'])
    self.assertFalse(self.p.FIREWALL['ta_execution'])
    self.assertFalse(self.p.FIREWALL['sealed_reference_allowed'])
    self.assertEqual(len(self.p.BLOCKERS), 5)

  def test_publication_unknown_field(self):
    self.assertRaises(ValueError, self.r.publication_guard, {'renamed_private_values': [1, 2, 3]})

  def test_publication_path_string(self):
    self.assertRaises(ValueError, self.r.publication_guard, {'status': '/private/source'})

  def test_publication_name_traversal(self):
    self.assertRaises(ValueError, self.r.publish, '../escape.json', {'schema': 'UNKNOWN'})

  def test_holdout_raw_read_once_policy(self):
    from pathlib import Path

    source = Path(self.r.__file__).read_text()
    self.assertIn("if segment['role'] != 'HOLDOUT':", source)

  def test_frozen_model_cross_binding(self):
    b = self.p.seal({'schema': 'EMPIRICAL_PLANT_EXECUTION_BINDING_V1'})
    models = self.p.seal({'schema': 'EMPIRICAL_PRIVATE_MODELS_V1', 'execution_binding_sha256': b['receipt_sha256']})
    sel = self.p.seal(
      {'schema': 'EMPIRICAL_PLANT_SELECTION_V1', 'local_model_sha256': models['receipt_sha256'], 'execution_binding_sha256': b['receipt_sha256']}
    )
    f = self.p.seal(
      {
        'schema': 'EMPIRICAL_MODEL_FROZEN_V1',
        'selection_sha256': sel['receipt_sha256'],
        'models_sha256': models['receipt_sha256'],
        'execution_binding_sha256': b['receipt_sha256'],
      }
    )
    self.r.extraction_gate('HOLDOUT', f, models, sel, b)
    bad = self.p.seal({'schema': 'EMPIRICAL_PRIVATE_MODELS_V1', 'execution_binding_sha256': 'WRONG'})
    self.assertRaises(ValueError, self.r.extraction_gate, 'HOLDOUT', f, bad, sel, b)
