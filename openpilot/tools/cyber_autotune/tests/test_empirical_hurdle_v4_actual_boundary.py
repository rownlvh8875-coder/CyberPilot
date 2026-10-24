"""Synthetic regressions for actual-run failure accounting and abort boundaries."""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_execution as e
from openpilot.tools.cyber_autotune.tests.test_empirical_hurdle_v4_execution import fixture, segment_fixture


class TestActualBoundary(unittest.TestCase):
  def test_normalizer_identity_conflict_aborts_instead_of_scientific_failure(self):
    x, y, norm = fixture()
    with self.assertRaisesRegex(ValueError, 'V4_NORMALIZER_IDENTITY_CONFLICT'):
      e.train(x, y, norm, candidate='HRI_D00_L01', normalizer_sha='0' * 64)

  def test_failed_head_preserves_attempted_checks_and_unreached_head(self):
    x, y, norm = fixture()
    target = (x[:, 1] > 0).astype(np.int64)
    result = e.train(x, target, norm, candidate='HRI_D00_L01', normalizer_sha=e.f.normalizer_identity(norm))
    self.assertEqual(result['status'], e.FAIL)
    self.assertEqual(result['head_checks']['STATIC']['support']['status'], 'PASS')
    self.assertEqual(result['head_checks']['STATIC']['rank']['status'], 'RANK_CERTIFICATE_PASS')
    self.assertEqual(result['head_checks']['STATIC']['separation']['status'], 'SEPARATION_PRESENT')
    self.assertEqual(result['head_checks']['STATIC']['convergence']['status'], 'NOT_REACHED')
    self.assertEqual(result['head_checks']['MOVE']['support']['status'], 'NOT_REACHED')
    self.assertIn('certificate_sha256', result['head_checks']['STATIC']['separation'])
    self.assertNotIn('model', result)

  def test_rank_subcause_retained(self):
    x, y, norm = fixture()
    x[:, 1] = 0
    result = e.train(x, y, norm, candidate='HRI_D00_L01', normalizer_sha=e.f.normalizer_identity(norm))
    self.assertEqual(result['head_checks']['STATIC']['rank']['status'], 'RANK_SVD_FAILURE')

  def test_development_storage_failure_aborts(self):
    s = segment_fixture()
    candidate = 'HRI_D00_L01'
    _, anchor, x, current, target = e.data.design([s], candidate)
    historical = {
      'candidate_id': candidate,
      'fold': 'FOLD_A',
      'train_anchor_sha256': anchor,
      'train_count': len(x),
      'train_move_count': int(np.count_nonzero(target != current)),
      'one_step': {'anchor_sha256': anchor, 'count': len(x)},
      'stage2': {},
      'rollout': {},
    }
    norm = fixture()[2]
    models = {'stage1': {'normalizer': norm, 'normalizer_receipt_sha256': 'b' * 64}, 'stage2': {'normalizer': norm, 'coefficients': np.zeros(5)}}
    original = e.save_arrays

    def fail_dev(root, arrays, body):
      if body.get('schema') == 'V4_DEVELOPMENT':
        raise ValueError('V4_EXECUTION_STORAGE_CAPACITY_FAILURE')
      return original(root, arrays, body)

    with tempfile.TemporaryDirectory() as tmp:
      permit = SimpleNamespace(
        roots={'output': Path(tmp)},
        replica='repeat-1',
        trusted_sha256='c' * 64,
        authorization={'resource_budget': {'certificate_integer_bits': 4096}},
        pack=e.a.contracts(),
      )
      with (
        e.store.synthetic_output(Path(tmp) / 'repeat-1'),
        patch.object(e.io, 'job_valid', return_value='candidates/' + candidate + '/FOLD_A'),
        patch.object(e.io, 'load_models', return_value=models),
        patch.object(e.io, 'load_route', return_value=[s]),
        patch.object(e.io, 'finalized'),
        patch.object(e, 'save_arrays', side_effect=fail_dev),
      ):
        with self.assertRaisesRegex(ValueError, 'V4_EXECUTION_STORAGE_CAPACITY_FAILURE'):
          e.execute_job(permit, historical)
      self.assertFalse((Path(tmp) / 'repeat-1/candidates' / candidate / 'FOLD_A/receipt.json').exists())

  def test_over_budget_failed_proof_keeps_hash_without_integer_payload(self):
    x, y, norm = fixture()
    result = e.train(x, y, norm, candidate='HRI_D00_L01', normalizer_sha=e.f.normalizer_identity(norm), certificate_bits=1)
    self.assertEqual(result['cause'], 'V4_CERTIFICATE_RESOURCE_BOUND')
    rank = result['failed_certificates']['STATIC']['rank']
    self.assertEqual(rank['payload_status'], 'OMITTED_RESOURCE_BOUND')
    self.assertEqual(len(rank['certificate_sha256']), 64)
    self.assertNotIn('determinant', rank)

  def test_failed_rank_verification_never_reports_pass(self):
    x, y, norm = fixture()
    original = e.c.rank_verify
    count = 0

    def verifier(*args, **kwargs):
      nonlocal count
      count += 1
      return original(*args, **kwargs) if count == 1 else False

    with patch.object(e.c, 'rank_verify', side_effect=verifier):
      result = e.train(x, y, norm, candidate='HRI_D00_L01', normalizer_sha=e.f.normalizer_identity(norm))
    self.assertEqual(result['head_checks']['STATIC']['rank']['status'], 'FAIL')
    self.assertEqual(result['head_checks']['STATIC']['rank']['generated_status'], 'RANK_CERTIFICATE_PASS')

  def test_all_executor_contracts_are_in_authorization_pack(self):
    from tools.cyberpilot import build_hurdle_v4_executor as b

    pack = e.a.contracts()
    bindings = pack['executor_contract_receipts']
    self.assertEqual(set(bindings), {b.filename(k) for k in b.COMPONENTS})
    for row in bindings.values():
      self.assertEqual(set(row), {'file_sha256', 'receipt_sha256'})
      self.assertEqual(len(row['file_sha256']), 64)

  def test_combined_score_failure_preserves_completed_head_convergence(self):
    x, y, norm = fixture()
    with patch.object(e, 'probability', side_effect=ValueError('HURDLE_NUMERICAL_FAILURE_NONFINITE')):
      result = e.train(x, y, norm, candidate='HRI_D00_L01', normalizer_sha=e.f.normalizer_identity(norm))
    self.assertEqual(result['status'], e.FAIL)
    self.assertEqual(result['head_checks']['STATIC']['convergence']['status'], 'CONVERGED')
    self.assertEqual(result['head_checks']['MOVE']['convergence']['status'], 'CONVERGED')
