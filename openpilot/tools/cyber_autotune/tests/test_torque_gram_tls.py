import dataclasses
import hashlib
import unittest

import numpy as np

from openpilot.tools.cyber_autotune.evidence import PROVENANCE_KEYS
from openpilot.tools.cyber_autotune.torque_identification import (
  SIGNAL_CONTRACT,
  TorqueFitInput,
  TorquePoint,
  identify_torque,
)


def raw_fixture(noisy=False):
  commands = np.concatenate((np.linspace(-.44, -.03, 80), np.linspace(.03, .44, 80)))
  points = tuple(TorquePoint(
    hashlib.sha256(str(i).encode()).hexdigest(),
    i * 50_000_000,
    float(x),
    float(1.8 * x - .03 + (.012 * np.sin(i * .7) if noisy else 0.)),
  ) for i, x in enumerate(commands))
  provenance = tuple((key, 'a' * 64) for key in sorted(PROVENANCE_KEYS))
  return TorqueFitInput(points, 'development_fit', provenance, SIGNAL_CONTRACT)


def gram_request(request):
  from openpilot.tools.cyber_autotune.torque_gram_tls import TorqueGramInput
  matrix = np.array([[p.normalized_command, 1., p.lateral_accel_mps2] for p in request.points], dtype=np.float64)
  gram = tuple(tuple(float(value) for value in row) for row in (matrix.T @ matrix))
  return TorqueGramInput(len(request.points), gram, (20,) * 8, 'a' * 64)


class TestTorqueGramTLS(unittest.TestCase):
  def test_affine_and_noisy_match_existing_raw_point_diagnostic(self):
    from openpilot.tools.cyber_autotune.torque_gram_tls import fit_torque_gram
    for noisy in (False, True):
      with self.subTest(noisy=noisy):
        raw = raw_fixture(noisy)
        expected = identify_torque(raw).estimate
        result = fit_torque_gram(gram_request(raw))
        self.assertEqual(result.status, 'NUMERICAL_DIAGNOSTIC')
        self.assertEqual(result, fit_torque_gram(gram_request(raw)))
        np.testing.assert_allclose(
          [result.estimate.lat_accel_factor, result.estimate.lat_accel_offset_mps2,
           result.estimate.native_residual_spread_coefficient, result.estimate.residual_rmse_mps2],
          [expected.lat_accel_factor, expected.lat_accel_offset_mps2,
           expected.native_residual_spread_coefficient, expected.residual_rmse_mps2],
          rtol=1e-11, atol=1e-11,
        )
        self.assertFalse(result.parameter_identification_qualified)
        self.assertFalse(result.candidate_generation_allowed)
        self.assertFalse(result.runtime_accepted)
        self.assertFalse(result.promotable)

  def test_digest_binds_count_gram_buckets_and_source(self):
    from openpilot.tools.cyber_autotune.torque_gram_tls import fit_torque_gram
    request = gram_request(raw_fixture(True))
    baseline = fit_torque_gram(request).input_sha256
    changed_gram = list(map(list, request.gram_xtx))
    changed_gram[0][0] += 1e-4
    changed_gram = tuple(tuple(row) for row in changed_gram)
    variants = (
      dataclasses.replace(request, gram_xtx=changed_gram),
      dataclasses.replace(request, bucket_counts=(19, 21) + request.bucket_counts[2:]),
      dataclasses.replace(request, source_sha256='b' * 64),
    )
    for variant in variants:
      self.assertNotEqual(fit_torque_gram(variant).input_sha256, baseline)

  def test_invalid_container_shape_types_and_accounting_block(self):
    from openpilot.tools.cyber_autotune.torque_gram_tls import fit_torque_gram
    request = gram_request(raw_fixture())
    bad_grams = (
      ((1., 0.), (0., 1.)),
      tuple(list(row) for row in request.gram_xtx),
      ((float('nan'), 0., 0.), (0., float(request.point_count), 0.), (0., 0., 1.)),
    )
    requests = [None, {}, dataclasses.asdict(request)]
    requests += [dataclasses.replace(request, gram_xtx=gram) for gram in bad_grams]
    requests += [
      dataclasses.replace(request, point_count=True),
      dataclasses.replace(request, point_count=2),
      dataclasses.replace(request, bucket_counts=request.bucket_counts[:-1]),
      dataclasses.replace(request, bucket_counts=(True,) + request.bucket_counts[1:]),
      dataclasses.replace(request, bucket_counts=(19,) * 8),
      dataclasses.replace(request, source_sha256='bad'),
    ]
    for invalid in requests:
      with self.subTest(invalid=type(invalid).__name__):
        result = fit_torque_gram(invalid)
        self.assertEqual(result.status, 'BLOCKED')
        self.assertIsNone(result.estimate)
        self.assertFalse(result.candidate_generation_allowed)

  def test_asymmetric_indefinite_and_count_mismatch_block(self):
    from openpilot.tools.cyber_autotune.torque_gram_tls import fit_torque_gram
    request = gram_request(raw_fixture())
    matrices = []
    asymmetric = [list(row) for row in request.gram_xtx]
    asymmetric[0][1] += .1
    matrices.append(tuple(tuple(row) for row in asymmetric))
    indefinite = [list(row) for row in request.gram_xtx]
    indefinite[0][0] = -1.
    matrices.append(tuple(tuple(row) for row in indefinite))
    mismatch = [list(row) for row in request.gram_xtx]
    mismatch[1][1] += 1.
    matrices.append(tuple(tuple(row) for row in mismatch))
    for gram in matrices:
      result = fit_torque_gram(dataclasses.replace(request, gram_xtx=gram))
      self.assertEqual(result.status, 'BLOCKED')
      self.assertIsNone(result.estimate)

  def test_degenerate_and_nonpositive_factor_block(self):
    from openpilot.tools.cyber_autotune.torque_gram_tls import TorqueGramInput, fit_torque_gram
    for slope in (0., -2.):
      x = np.linspace(-.4, .4, 100)
      y = slope * x
      matrix = np.column_stack((x, np.ones_like(x), y))
      gram = tuple(tuple(float(value) for value in row) for row in matrix.T @ matrix)
      request = TorqueGramInput(100, gram, (13, 13, 13, 13, 12, 12, 12, 12), 'a' * 64)
      result = fit_torque_gram(request)
      self.assertEqual(result.status, 'BLOCKED')
      self.assertIsNone(result.estimate)
      self.assertIn('NUMERICALLY_UNIDENTIFIABLE', result.blockers)

  def test_numpy_error_policy_is_preserved(self):
    from openpilot.tools.cyber_autotune.torque_gram_tls import fit_torque_gram
    before = np.geterr()
    fit_torque_gram(gram_request(raw_fixture(True)))
    self.assertEqual(np.geterr(), before)


if __name__ == '__main__':
  unittest.main()
