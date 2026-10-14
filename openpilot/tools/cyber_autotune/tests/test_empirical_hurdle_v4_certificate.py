"""Exact certificates on deterministic synthetic arrays only."""

import copy
import unittest
import numpy as np
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_certificate as c


class TestCertificate(unittest.TestCase):
  def test_bareiss(self):
    self.assertEqual(c.determinant([[0, 2], [3, 4]]), -6)
    self.assertEqual(c.determinant([[1, 2], [2, 4]]), 0)

  def test_rank(self):
    for p in (4, 12, 32, 92, 93):
      with self.subTest(p=p):
        x = np.ascontiguousarray(np.vstack((np.eye(p), np.eye(p))))
        result = c.rank_generate(x, binding={'basis': 'synthetic'})
        self.assertEqual(result['status'], 'RANK_CERTIFICATE_PASS')
        self.assertTrue(c.rank_verify(x, result, binding={'basis': 'synthetic'}))
        bad = copy.deepcopy(result)
        bad['rows'][0] = bad['rows'][1]
        self.assertFalse(c.rank_verify(x, bad, binding={'basis': 'synthetic'}))

  def test_rank_failure(self):
    self.assertEqual(c.rank_generate(np.ones((20, 4)))['status'], 'RANK_SVD_FAILURE')
    x = np.eye(4)
    self.assertEqual(c.rank_generate(x, max_rows=0)['status'], 'RANK_CERTIFICATE_INCONCLUSIVE')

  def test_binary64(self):
    a = np.array([[1.0, 1.0], [1.0, np.nextafter(1.0, 2.0)]])
    self.assertNotEqual(c.minor_determinant(a)[0], 0)

  def test_separation_suite(self):
    cases = [
      (np.array([[1.0, -1.0], [1.0, 1.0]]), [0, 1], 'SEPARATION_PRESENT'),
      (np.array([[1.0, 0.0], [1.0, 0.0], [1.0, 1.0]]), [0, 1, 1], 'SEPARATION_PRESENT'),
      (np.array([[1.0, 0.0], [1.0, 0.0], [1.0, 1.0], [1.0, 1.0]]), [0, 1, 0, 1], 'NO_SEPARATION'),
      (np.ones((3, 1)), [0, 1, 1], 'NO_SEPARATION'),
      (np.zeros((2, 2)), [0, 1], 'NO_SEPARATION'),
      (np.array([[1.0, -0.0], [1.0, 0.0]]), [0, 1], 'NO_SEPARATION'),
      (np.array([[1.0, -(2.0**-100)], [1.0, 2.0**-100]]), [0, 1], 'SEPARATION_PRESENT'),
    ]
    for x, y, status in cases:
      with self.subTest(status=status, x=x):
        y = np.array(y)
        result = c.separation_generate(x, y)
        self.assertEqual(result['status'], status)
        self.assertEqual(c.separation_verify(x, y, result)['status'], status)
        bad = copy.deepcopy(result)
        bad['matrix_sha256'] = '0' * 64
        self.assertEqual(c.separation_verify(x, y, bad)['status'], 'SEPARATION_CERTIFICATE_INCONCLUSIVE')

  def test_sparse_correction(self):
    x, y = np.ones((7, 1)), np.array([0, 1, 1, 1, 1, 1, 1])
    r = c.separation_generate(x, y)
    self.assertEqual(r['status'], 'NO_SEPARATION')
    self.assertEqual(r['D'], 1)
    self.assertEqual(r['active'], [[0, 5]])
    self.assertLessEqual(len(r['active']), x.shape[1])

  def test_wrong_proposal(self):
    x, y = np.array([[1.0, -1.0], [1.0, 1.0]]), np.array([0, 1])
    r = c.separation_generate(x, y)
    r['direction'] = [1, 0]
    self.assertEqual(c.separation_verify(x, y, r)['status'], 'SEPARATION_CERTIFICATE_INCONCLUSIVE')

  def test_resource(self):
    r = c.separation_generate(np.ones((7, 1)), np.array([0, 1, 1, 1, 1, 1, 1]), max_iterations=0)
    self.assertEqual(r['status'], 'SEPARATION_CERTIFICATE_INCONCLUSIVE_RESOURCE_BOUND')

  def test_near_zero_not_zero(self):
    x = np.array([[1.0, 0.0], [1.0, np.nextafter(0.0, 1.0)]])
    y = np.array([0, 1])
    cert = {'matrix_sha256': c.binding(x, y), 'kind': 'ABSENCE', 'D': 1, 'active': []}
    self.assertEqual(c.separation_verify(x, y, cert)['status'], 'SEPARATION_CERTIFICATE_INCONCLUSIVE')


class TestCertificateAdversarial(unittest.TestCase):
  def test_receipt_stable(self):
    for x, y in ((np.ones((7, 1)), np.array([0, 1, 1, 1, 1, 1, 1])), (np.eye(2), np.array([0, 1]))):
      first = c.separation_generate(x, y)
      second = c.separation_generate(x, y)
      self.assertEqual(first, second)
      self.assertEqual(c.separation_verify(x, y, first)['certificate_sha256'], first['certificate_sha256'])

  def test_absence_corruption(self):
    x, y = np.ones((7, 1)), np.array([0, 1, 1, 1, 1, 1, 1])
    original = c.separation_generate(x, y)
    for key, value in (
      ('D', 0),
      ('D', 2),
      ('active', [[0, -5]]),
      ('active', [[7, 5]]),
      ('active', [[0, 4]]),
      ('active', [[0, 5], [0, 5]]),
      ('certificate_sha256', '0' * 64),
    ):
      with self.subTest(key=key, value=value):
        bad = {**original, key: value}
        self.assertEqual(c.separation_verify(x, y, bad)['status'], c.UNKNOWN)

  def test_presence_corruption(self):
    x, y = np.array([[1.0, -1.0], [1.0, 1.0]]), np.array([0, 1])
    original = c.separation_generate(x, y)
    for direction in ([0, 0], [0, -1], [0, 2], [1, 0], [0, 1, 2], [0, True]):
      with self.subTest(direction=direction):
        self.assertEqual(c.separation_verify(x, y, {**original, 'direction': direction})['status'], c.UNKNOWN)

  def test_rank_corruption(self):
    x = np.eye(4)
    original = c.rank_generate(x, binding={'normalizer': 'synthetic'})
    for key, value in (
      ('rows', [-1, 1, 2, 3]),
      ('determinant', ['0', '1']),
      ('determinant_sign', -1),
      ('matrix_sha256', '0' * 64),
      ('binding', {}),
      ('certificate_sha256', '0' * 64),
    ):
      self.assertFalse(c.rank_verify(x, {**original, key: value}, binding={'normalizer': 'synthetic'}))
    x[0, 0] = 2
    self.assertFalse(c.rank_verify(x, original, binding={'normalizer': 'synthetic'}))

  def test_extreme_scale_and_exact_independence(self):
    x = np.array([[2.0**500, 0.0], [0.0, 2.0**-500]])
    num, den = c.minor_determinant(x)
    self.assertEqual((num, den), (1, 1))
    # SVD rule can fail even where exact rank is full; both frozen conditions matter.
    self.assertEqual(c.rank_generate(x)['status'], 'RANK_SVD_FAILURE')

  def test_exact_minor_resource(self):
    x = np.ascontiguousarray(np.vstack((np.zeros((10, 4)), np.eye(4))))
    self.assertEqual(c.rank_generate(x, max_rows=10)['status'], 'RANK_CERTIFICATE_INCONCLUSIVE')

  def test_singular_active_exactification(self):
    from fractions import Fraction

    with self.assertRaises(ValueError):
      c.exact_proposal(np.ones((3, 2)), [Fraction(3), Fraction(3)], [0, 1])

  def test_nullspace_direction_rejected(self):
    x, y = np.array([[1.0, 0.0], [1.0, 0.0]]), np.array([0, 1])
    cert = {'matrix_sha256': c.binding(x, y), 'kind': 'PRESENCE', 'direction': [0, 1]}
    self.assertEqual(c.separation_verify(x, y, cert)['status'], c.UNKNOWN)
