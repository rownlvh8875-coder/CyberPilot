import copy
import unittest
from unittest.mock import patch
from openpilot.tools.cyber_autotune import empirical_source_dependencies as d, empirical_plant_policy as p


class TestSourceDependencies(unittest.TestCase):
  def closure(self, commit):
    return p.seal({'commit': commit, 'policy_sha256': d.closure_policy()['receipt_sha256'],
                   'entries': {k: {'file_sha256': 'a'*64} for k in d.CLOSURE_PATHS}, 'missing': []})

  def reseal(self, row):
    return p.seal({k: v for k, v in row.items() if k != 'receipt_sha256'})

  def test_complete_exact_closure(self):
    self.assertTrue(d.verify_closure(self.closure(d.PAIR[0]), self.closure(d.PAIR[1])))

  def test_missing_transport_rejected(self):
    a, b = self.closure(d.PAIR[0]), self.closure(d.PAIR[1])
    b['missing'] = ['msgq']
    with self.assertRaises(ValueError):
      d.verify_closure(a, self.reseal(b))

  def test_changed_runtime_params_rejected(self):
    a, b = self.closure(d.PAIR[0]), self.closure(d.PAIR[1])
    b['entries']['openpilot/common/params.cc']['file_sha256'] = 'b'*64
    with self.assertRaises(ValueError):
      d.verify_closure(a, self.reseal(b))

  def test_wrong_closure_pair_rejected(self):
    with self.assertRaises(ValueError):
      d.verify_closure(self.closure('0'*40), self.closure(d.PAIR[1]))

  def test_forged_closure_hash_rejected(self):
    a = self.closure(d.PAIR[0])
    a['entries'].clear()
    with self.assertRaises(ValueError):
      d.verify_closure(a, self.closure(d.PAIR[1]))

  def test_missing_role_rejected(self):
    a = self.closure(d.PAIR[0])
    a['entries'].pop(next(iter(a['entries'])))
    with self.assertRaises(ValueError):
      d.verify_closure(self.reseal(a), self.closure(d.PAIR[1]))

  def test_wrong_policy_rejected(self):
    a = self.closure(d.PAIR[0])
    a['policy_sha256'] = '0'*64
    with self.assertRaises(ValueError):
      d.verify_closure(self.reseal(a), self.closure(d.PAIR[1]))

  def test_all_dependency_receipts_verified(self):
    source = p.seal({'files': {}})
    dep = p.seal({'entries': {}})
    review = p.seal({'fingerprint_sha256': [source['receipt_sha256']]*2,
                     'dependency_sha256': [dep['receipt_sha256']]*2, 'equivalence': 'SCOPED'})
    with patch.object(d, 'REVIEW_PIN', review['receipt_sha256']):
      self.assertEqual(d.verify_review(review, source, source, dep, dep), 'SCOPED')
      bad = copy.deepcopy(source)
      bad['files']['forged'] = {}
      with self.assertRaises(ValueError):
        d.verify_review(review, bad, source, dep, dep)

  def test_unreviewed_pair_rejected(self):
    with self.assertRaises(ValueError):
      d.review_pair({'commit': 'a'*40}, {'commit': 'b'*40}, {}, {}, {})

  def test_no_physical_runtime_equivalence(self):
    self.assertFalse(d.closure_policy()['runtime_binary_or_physical_acquisition_equivalence'])

  def test_can_checksum_and_transport_bound(self):
    self.assertIn('canfd_builder', d.closure_policy()['existing_checksum_closure'])
    self.assertIn('msgq_repo/msgq/ipc.cc', d.CLOSURE_PATHS)
