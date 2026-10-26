import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from openpilot.tools.cyber_autotune import empirical_identifiability_policy as policy
from openpilot.tools.cyber_autotune import empirical_plant_policy as p


class TestIdentifiabilityContract(unittest.TestCase):
  def test_fixed_envelopes(self):
    r = policy.policy()
    self.assertEqual(r['histories'], list(range(1, 46)))
    self.assertEqual(r['lags'], list(range(21)))
    self.assertEqual(r['minimum_route_development_support'], 201)

  def test_no_authority(self):
    r = policy.policy()
    for k, value in r['authority'].items():
      self.assertFalse(value, k)
    self.assertEqual(r['holdout'], 'HOLDOUT_OPENING_CLOSED')

  def test_authoritative_inputs(self):
    r = policy.policy()
    self.assertEqual(r['resolution']['final_dataset_status'], 'RETROSPECTIVE_CAUSAL_TRAIN_DEV_DATASET_PARTIAL')
    self.assertEqual(r['stream_count'], 154)
    self.assertEqual(len(r['excluded_qlog_content_sha256']), 2)

  def test_policy_immutable(self):
    with tempfile.TemporaryDirectory() as td:
      policy.freeze(Path(td))
      policy.freeze(Path(td))
      path = Path(td)/'policy.json'
      path.write_text('{}')
      with self.assertRaises(ValueError):
        policy.freeze(Path(td))

  def test_source_unit_not_inferred_from_name(self):
    r = policy.source_contract()
    self.assertEqual(r['rate']['classification'], 'SOURCE_NATIVE_RATE_CODE_ONLY')
    self.assertEqual(r['rate']['contract'], 'RATE_SOURCE_CONTRACT_PARTIAL')
    self.assertFalse(r['rate']['signed_physical_rate_proven'])
    self.assertEqual(r['rate']['unit'], '')

  def test_s3_not_physical_from_controller_deadzone(self):
    r = policy.source_contract()
    self.assertEqual(r['s3']['status'], 'S3_SOURCE_MECHANISM_BLOCKED')
    self.assertFalse(r['s3']['physical_deadzone_proven'])
    self.assertFalse(r['s3']['physical_hysteresis_proven'])

  def test_source_claims_bound_to_exact_commit(self):
    r = policy.source_contract()
    self.assertEqual(r['commit'], '18c07cfae4a35786955d5c7fa8bcbe4bfaee0c29')
    for row in r['files'].values():
      self.assertEqual(len(row['file_sha256']), 64)
      self.assertEqual(len(row['reviewed_slice_sha256']), 64)
      self.assertIn('path', row)

  def test_source_drift_rejected(self):
    with patch.object(policy, 'git_blob', return_value=b'wrong'):
      with self.assertRaises(ValueError):
        policy.audit_source('/public-git-store')

  def test_source_audit_result_not_empirical(self):
    r = policy.source_contract()
    self.assertEqual(r['rate']['numeric_diagnostic_authority'], 'CANNOT_PROMOTE_SOURCE_SEMANTICS')
    self.assertFalse(r['s3']['numeric_regime_discovery_allowed'])

  def test_rank_policy_no_target(self):
    r = policy.policy()
    self.assertEqual(r['rank']['target_used'], False)
    self.assertEqual(r['rank']['condition_threshold'], None)
    self.assertFalse(r['rank']['symbolic_identifiability_proof'])

  def test_reset_and_leakage_contract(self):
    r = policy.leakage_reset()
    self.assertIn('qlog', r['prohibited'])
    self.assertIn('next_target_in_X', r['prohibited'])
    self.assertEqual(set(r['families']), {'S1', 'S2', 'S3'})
    self.assertFalse(r['runtime_implemented'])

  def test_missing_final_no_fallback(self):
    with patch('openpilot.tools.cyber_autotune.empirical_final_readiness.load', side_effect=ValueError('MISSING')):
      with self.assertRaises(ValueError):
        policy.policy()

  def test_tampered_source_contract_rejected(self):
    r = copy.deepcopy(policy.source_contract())
    r['rate']['signed_physical_rate_proven'] = True
    r.pop('receipt_sha256')
    with self.assertRaises(ValueError):
      policy.validate_source(p.seal(r))

  def test_source_contract_json_roundtrip(self):
    policy.validate_source(json.loads(p.canonical(policy.source_contract())))
