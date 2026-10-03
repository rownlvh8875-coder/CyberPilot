import dataclasses
import hashlib
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

from openpilot.tools.cyber_autotune.evidence import PROVENANCE_KEYS
from openpilot.tools.cyber_autotune.torque_identification import (
  SIGNAL_CONTRACT, TorqueFitInput, TorquePoint, identify_torque,
)


def fixture(noisy=False):
  commands = np.concatenate((np.linspace(-.44, -.03, 60), np.linspace(.03, .44, 60)))
  points = tuple(TorquePoint(hashlib.sha256(str(i).encode()).hexdigest(), i * 50_000_000,
                            float(x), float(2 * x + .03 + (.01 * np.sin(i) if noisy else 0)))
                 for i, x in enumerate(commands))
  return TorqueFitInput(points, 'development_fit', tuple((key, 'a' * 64) for key in sorted(PROVENANCE_KEYS)), SIGNAL_CONTRACT)


class TestTorqueIdentification(unittest.TestCase):
  def assert_blocked(self, request):
    result = identify_torque(request)
    self.assertEqual(result.status, 'BLOCKED')
    self.assertIsNone(result.estimate)
    self.assertTrue(result.blockers)
    self.assertFalse(result.candidate_generation_allowed)

  def test_affine_repeatable_without_authority_or_fake_confidence(self):
    request = fixture()
    result = identify_torque(request)
    self.assertEqual(result, identify_torque(request))
    self.assertEqual(result.status, 'NUMERICAL_DIAGNOSTIC')
    self.assertAlmostEqual(result.estimate.lat_accel_factor, 2.)
    self.assertAlmostEqual(result.estimate.lat_accel_offset_mps2, .03)
    self.assertLess(result.estimate.native_residual_spread_coefficient, 1e-12)
    self.assertLess(result.estimate.residual_rmse_mps2, 1e-12)
    self.assertEqual(result.point_count, 120)
    self.assertIsNone(result.confidence)
    self.assertIsNone(result.independent_sample_count)
    for field in ('parameter_identification_qualified', 'candidate_generation_allowed', 'runtime_accepted', 'promotable'):
      self.assertFalse(getattr(result, field))
      with self.assertRaises(ValueError):
        dataclasses.replace(result, **{field: True})
    self.assertTrue(result.blockers)
    self.assertNotIn('points', dataclasses.asdict(result))

  def test_native_kernel_parity_affine_and_noisy(self):
    from openpilot.selfdrive.locationd.torqued import TorqueEstimator
    for noisy in (False, True):
      with self.subTest(noisy=noisy):
        request = fixture(noisy)
        points = np.array([[p.normalized_command, 1., p.lateral_accel_mps2] for p in request.points])
        proxy = SimpleNamespace(filtered_points=SimpleNamespace(get_points=lambda count, frozen=points: frozen), fit_points=len(points))
        native = TorqueEstimator.estimate_params(proxy)
        estimate = identify_torque(request).estimate
        np.testing.assert_allclose([estimate.lat_accel_factor, estimate.lat_accel_offset_mps2,
                                    estimate.native_residual_spread_coefficient], native, rtol=1e-13, atol=1e-13)

  def test_digest_binds_points_identity_and_all_provenance(self):
    request = fixture()
    baseline = identify_torque(request).input_sha256
    for i in range(len(PROVENANCE_KEYS)):
      provenance = list(request.provenance)
      provenance[i] = (provenance[i][0], 'b' * 64)
      self.assertNotEqual(identify_torque(dataclasses.replace(request, provenance=tuple(provenance))).input_sha256, baseline)
    changed = dataclasses.replace(request.points[0], sample_sha256='c' * 64)
    self.assertNotEqual(identify_torque(dataclasses.replace(request, points=(changed,) + request.points[1:])).input_sha256, baseline)

  def test_roles_contract_and_provenance_rejected(self):
    request = fixture()
    for role in ('holdout', 'evaluation', 'FIT', None, True):
      with self.subTest(role=role):
        self.assert_blocked(dataclasses.replace(request, role=role))
    for contract in ('requested_torque', 'Nm', '', None):
      self.assert_blocked(dataclasses.replace(request, signal_contract=contract))
    for provenance in ((), request.provenance[:-1], list(request.provenance),
                       request.provenance + (request.provenance[0],),
                       tuple((key, 'INVALID') for key in PROVENANCE_KEYS)):
      self.assert_blocked(dataclasses.replace(request, provenance=provenance))

  def test_bad_container_count_and_scalar_types(self):
    request = fixture()
    for invalid in (None, {}, dataclasses.asdict(request)):
      self.assert_blocked(invalid)
    for points in ((), request.points[:2], list(request.points), request.points * 101):
      self.assert_blocked(dataclasses.replace(request, points=points))
    for field, bad_values in {'time_ns': (True, -1, 1.5, '0'),
                              'sample_sha256': ('', 'X' * 64, None),
                              'normalized_command': (True, float('nan'), float('inf'), 10 ** 1000, '0.2'),
                              'lateral_accel_mps2': (True, float('nan'), float('inf'), '0.2')}.items():
      for value in bad_values:
        with self.subTest(field=field, kind=type(value).__name__):
          point = dataclasses.replace(request.points[0], **{field: value})
          self.assert_blocked(dataclasses.replace(request, points=(point,) + request.points[1:]))

  def test_duplicate_identity_and_time_and_reverse_order(self):
    request = fixture()
    for changed in (dataclasses.replace(request.points[1], sample_sha256=request.points[0].sample_sha256),
                    dataclasses.replace(request.points[1], time_ns=0)):
      self.assert_blocked(dataclasses.replace(request, points=(request.points[0], changed) + request.points[2:]))
    self.assert_blocked(dataclasses.replace(request, points=request.points[::-1]))

  def test_point_domain_and_missing_excitation(self):
    request = fixture()
    for field, values in (('normalized_command', (-.50001, .5, 0., .02, -.02)),
                          ('lateral_accel_mps2', (-1.00001, 1.00001))):
      for value in values:
        point = dataclasses.replace(request.points[0], **{field: value})
        self.assert_blocked(dataclasses.replace(request, points=(point,) + request.points[1:]))
    for points in (request.points[60:],
                   tuple(dataclasses.replace(p, normalized_command=.2) for p in request.points),
                   tuple(dataclasses.replace(p, lateral_accel_mps2=-2*p.normalized_command) for p in request.points),
                   tuple(dataclasses.replace(p, lateral_accel_mps2=0.) for p in request.points)):
      self.assert_blocked(dataclasses.replace(request, points=points))

  def test_svd_failure_is_blocked_and_numpy_error_policy_preserved(self):
    before = np.geterr()
    with patch('numpy.linalg.svd', side_effect=np.linalg.LinAlgError('test failure')):
      self.assert_blocked(fixture())
    self.assertEqual(np.geterr(), before)
    identify_torque(fixture())
    self.assertEqual(np.geterr(), before)


if __name__ == '__main__':
  unittest.main()
