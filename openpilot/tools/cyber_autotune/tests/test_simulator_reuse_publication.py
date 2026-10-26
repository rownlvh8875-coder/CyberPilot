"""Source audit pins and additive authority boundary tests; no external repositories needed."""

from copy import deepcopy
import unittest
from unittest.mock import patch
from openpilot.tools.cyber_autotune import empirical_plant_policy as p


class ReusePublication(unittest.TestCase):
  def load(self):
    from openpilot.tools.cyber_autotune import simulator_reuse_publication as pub

    return pub.load()

  def validate(self, rows):
    from openpilot.tools.cyber_autotune import simulator_reuse_publication as pub

    return pub.validate(rows)

  def test_exact_eight_artifacts(self):
    self.assertEqual(len(self.load()), 8)

  def test_source_heads_exact(self):
    identity = self.load()['simulator-source-identity-v1.json']
    self.assertEqual([r['commit'] for r in identity['repositories']], ['50af6679956ed4ef0f13214f832b8f65e212e370', '4c2d094f188b072172de6e8d848dfb4a31b23bd9'])

  def test_source_identity_stale_branch_rejected(self):
    rows = self.load()
    name = 'simulator-source-identity-v1.json'
    rows[name]['repositories'][0]['commit'] = '0' * 40
    rows[name] = p.seal(rows[name])
    with self.assertRaises(ValueError):
      self.validate(rows)

  def test_tree_object_not_query_commit_identity(self):
    repos = self.load()["simulator-source-identity-v1.json"]["repositories"]
    self.assertEqual([row["tree_sha1"] for row in repos], ["1cd8d4545999f65bf84e839ecdc1213c3d6b7fa4", "b134922105588653b4be7f687fbec71fbcd5d663"])
    self.assertTrue(all(row["tree_sha1"] != row["commit"] for row in repos))

  def test_private_provenance_preserved(self):
    row = self.load()['simulator-source-identity-v1.json']['repositories'][1]
    self.assertEqual(row['visibility'], 'PRIVATE')
    self.assertEqual(row['branch'], 'carrot-sim-v0')

  def test_missing_public_modules_not_substituted(self):
    rows = self.load()['simulator-reuse-matrix-v1.json']['components']
    missing = [r for r in rows if r['repository'] == 'public' and r['source_file_sha256'] is None]
    self.assertEqual({r['path'] for r in missing}, {'carrot_sim/behavior_metrics.py', 'carrot_sim/simulation_fidelity_tiers.py'})
    self.assertTrue(all(r['status'] == 'REJECT_UNSAFE_OR_STALE' for r in missing))

  def test_not_as_is_due_to_overlap_schema_and_license(self):
    rows = self.load()['simulator-reuse-matrix-v1.json']
    self.assertEqual(rows['status_counts']['REUSE_AS_IS'], 0)

  def test_historical_blocker_drift_rejected(self):
    rows = self.load()
    name = 'simulator-reuse-audit-v1.json'
    rows[name]['calibration_blockers'] = []
    rows[name] = p.seal(rows[name])
    with self.assertRaises(ValueError):
      self.validate(rows)

  def test_production_authority_rejected(self):
    rows = self.load()
    rows['simulator-reuse-audit-v1.json']['production_authority'] = True
    with self.assertRaises(ValueError):
      self.validate(rows)

  def test_no_private_data_access(self):
    with patch.object(p, 'inventory', side_effect=AssertionError('raw root accessed')):
      row = self.load()['simulator-source-identity-v1.json']
    self.assertFalse(row['private_data_accessed'])

  def test_historical_verdicts_retained(self):
    h = self.load()['simulator-reuse-audit-v1.json']['historical']
    self.assertEqual(h['ta'], 'TA_STANDALONE_TRADEOFF_ONLY')
    self.assertEqual(h['sg'], 'SG_CLOSED_LOOP_TRADEOFF_ONLY')
    self.assertEqual(h['v2_violations'], 37)
    self.assertEqual(h['opening'], 'HOLDOUT_OPENING_CLOSED')

  def test_missing_artifact_rejected(self):
    rows = self.load()
    rows.pop('cyber-visual-adapter-contract-v1.json')
    with self.assertRaises(ValueError):
      self.validate(rows)

  def test_private_extra_data_rejected(self):
    rows = self.load()
    name = 'simulator-reuse-audit-v1.json'
    rows[name]['private_trace'] = [1, 2, 3]
    rows[name] = p.seal(rows[name])
    with self.assertRaises(ValueError):
      self.validate(rows)

  def test_model_import_never_authorized(self):
    rows = self.load()['simulator-reuse-matrix-v1.json']['components']
    self.assertTrue(all(not r['result_or_plant_evidence_imported'] for r in rows))

  def test_modelv2_cannot_become_reference(self):
    rows = self.load()
    name = 'cyber-simulation-fidelity-contract-v1.json'
    rows[name]['forbidden_claims'].remove('MODEL_V2_INDEPENDENT_REFERENCE')
    rows[name] = p.seal(rows[name])
    with self.assertRaises(ValueError):
      self.validate(rows)

  def test_contract_regeneration_exact(self):
    from openpilot.tools.cyber_autotune import simulator_reuse_contracts as c

    rows = self.load()
    self.assertEqual({n: rows[n] for n in c.NAMES}, c.artifacts())

  def test_receipt_inputs_not_modified(self):
    rows = self.load()
    before = deepcopy(rows)
    self.validate(rows)
    self.assertEqual(rows, before)

  def test_visual_adapter_frame_mapping_preserves_semantics(self):
    row = self.load()['cyber-visual-adapter-contract-v1.json']
    self.assertIsNone(row['future_SG_trace_mapping_design']['pre_limit_torque'])
    self.assertEqual(row['future_SG_trace_mapping_design']['pre_governor_torque'], '/pre')
    self.assertFalse(row['private_trace_access_allowed'])


if __name__ == '__main__':
  unittest.main()
