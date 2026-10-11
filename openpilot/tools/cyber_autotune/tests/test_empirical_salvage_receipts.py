from pathlib import Path
import tempfile
import unittest
from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_prior_use as u
from openpilot.tools.cyber_autotune import empirical_salvage_policy as s
from openpilot.tools.cyber_autotune import empirical_salvage_sources as source


class TestSalvageReceipts(unittest.TestCase):
  def test_empty_evidence_cannot_prove_untouched(self):
    self.assertEqual(s.prior_state([], True, True), 'PRIOR_USE_UNKNOWN')

  def test_renamed_cache_rejected_by_schema(self):
    with tempfile.TemporaryDirectory() as t:
      root = Path(t)
      (root / 'manifest.json').write_bytes(p.canonical(p.seal({'schema': 'NUMERIC_ALIGNED_CACHE', 'rows': [[1, 2]]})))
      with self.assertRaisesRegex(ValueError, 'SCHEMA'):
        u.read_receipt(root, [root], 'manifest.json')

  def test_actual_fold_receipt_read_without_array(self):
    with tempfile.TemporaryDirectory() as t:
      root = Path(t)
      relative = Path('folds/STAGE_A/LOW/ARX1-d5/FOLD_A/receipt.json')
      file = root / relative
      file.parent.mkdir(parents=True)
      row = p.seal({'schema': 'EMPIRICAL_PLANT_V3_PRIVATE_FOLD_RESULT_V1', 'train_route': 'a', 'development_route': 'b'})
      file.write_bytes(p.canonical(row))
      self.assertEqual(u.read_receipt(root, [root], relative), row)
      with self.assertRaisesRegex(ValueError, 'ALLOWLIST'):
        u.read_receipt(root, [root], relative.parent / 'target.npy')

  def test_predicate_difference_blocks_equivalence(self):
    a = {'complete': True, 'public_available': True, 'dirty': False, 'files': {}, 'closure': {}, 'predicate_sha256': 'a'}
    self.assertEqual(source.compare_bound(a, {**a, 'predicate_sha256': 'b'}), 'SOURCE_ADAPTER_REQUIRED')

  def test_missing_predicate_blocks_equivalence(self):
    a = {'complete': True, 'public_available': True, 'dirty': False, 'files': {}, 'closure': {}}
    self.assertEqual(source.compare_bound(a, a), 'SOURCE_AUDIT_PARTIAL')

  def test_identical_bound_source_equivalent(self):
    a = {'complete': True, 'public_available': True, 'dirty': False, 'files': {}, 'closure': {}, 'predicate_sha256': 'a'}
    self.assertEqual(source.compare_bound(a, a), 'SOURCE_EQUIVALENT')

  def test_numeric_flag_one_does_not_become_untouched(self):
    row = {
      'metadata_opened': True,
      'numeric_opened': 1,
      'fitting_used': False,
      'selection_used': False,
      'evaluation_used': False,
      'holdout_used': False,
    }
    self.assertEqual(s.prior_state([row], True, True), 'PRIOR_USE_UNKNOWN')

  def test_string_flag_does_not_become_untouched(self):
    row = {
      'metadata_opened': True,
      'numeric_opened': 'false',
      'fitting_used': False,
      'selection_used': False,
      'evaluation_used': False,
      'holdout_used': False,
    }
    self.assertEqual(s.prior_state([row], True, True), 'PRIOR_USE_UNKNOWN')

  def test_baseline_public_inputs_ignore_new_outputs(self):
    from openpilot.tools.cyber_autotune import empirical_salvage_execution as e

    self.assertNotIn('empirical-route-prior-use-ledger-v1.json', dict(e.baseline_public_inputs()))
    self.assertIn('empirical-plant-v3-folds-v1.json', dict(e.baseline_public_inputs()))

  def test_two_run_receipt_rejects_different_result(self):
    from openpilot.tools.cyber_autotune import empirical_salvage_report as r

    a = p.seal({'schema': 'EMPIRICAL_TEST', 'count': 1})
    b = p.seal({'schema': 'EMPIRICAL_TEST', 'count': 2})
    with self.assertRaisesRegex(ValueError, 'REPEATABILITY'):
      r.repeatability(a, b)

  def test_two_run_receipt_proves_exact_result(self):
    from openpilot.tools.cyber_autotune import empirical_salvage_report as r

    a = p.seal({'schema': 'EMPIRICAL_TEST', 'count': 1})
    self.assertEqual(r.repeatability(a, a)['status'], 'TWO_COMPLETE_EXECUTIONS_EXACT')

  def test_first_run_cannot_claim_repeatability(self):
    from openpilot.tools.cyber_autotune import empirical_salvage_report as r

    self.assertEqual(r.REPEATABILITY_INITIAL, 'SEPARATE_VERIFIED_REPEATABILITY_RECEIPT_REQUIRED')
