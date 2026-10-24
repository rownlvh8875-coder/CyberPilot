import unittest
from openpilot.tools.cyber_autotune import smoothness_v0_metrics as m


class TestMetrics(unittest.TestCase):
  def test_derivative_exact(self):
    self.assertEqual(m.command_metrics([1.0, 0.0, -1.0])['derivative_abs']['maximum'], 100.0)

  def test_rms(self):
    self.assertEqual(m.command_metrics([1.0, 0.0, -1.0])['derivative_rms'], 100.0)

  def test_total_variation(self):
    self.assertEqual(m.command_metrics([1.0, 0.0, -1.0])['total_variation'], 2.0)

  def test_exact_zero_sign(self):
    r = m.command_metrics([1.0, 0.0, -1.0])
    self.assertEqual(r['direct_zero_crossings'], 0)
    self.assertEqual(r['nonzero_sign_reversals'], 1)

  def test_derivative_redistribution(self):
    a = m.command_metrics([1.0] + [-1.0] * 20)
    b = m.command_metrics([1.0, 0.0] + [-1.0] * 19)
    self.assertGreater(b['derivative_abs']['p95'], a['derivative_abs']['p95'])
    self.assertEqual(a['total_variation'], b['total_variation'])

  def test_empty(self):
    self.assertIsNone(m.command_metrics([])['derivative_abs']['p95'])

  def test_single(self):
    self.assertEqual(m.command_metrics([0.0])['derivative_abs']['n'], 0)

  def test_nonfinite(self):
    with self.assertRaises(ValueError):
      m.command_metrics([float('nan')])

  def test_dist_no_extrapolation(self):
    self.assertIsNone(m.base.distance_value([{'pose_x': 0.0, 'pose_y': 1.0}], 5.0, 'pose_y'))

  def test_spectrum_constant(self):
    self.assertEqual(m.command_metrics([0.5] * 100)['high_frequency_energy'], 0.0)

  def test_multibin_spectrum_oracle(self):
    import numpy as np

    values = [0.4, -0.2, 0.1, -0.3] * 16
    x = np.array(values)
    f = np.fft.rfftfreq(len(x), 0.01)
    fft = np.fft.rfft((x - x.mean()) * np.hanning(len(x)))
    band = np.abs(fft[(f >= 1.2) & (f <= 50.0)])
    expected = float(np.sum(band**2) / len(x) ** 2)
    self.assertAlmostEqual(m.command_metrics(values)['high_frequency_energy'], expected, places=15)
    self.assertNotAlmostEqual(expected, float(np.sum(band) ** 2 / len(x) ** 2), places=8)

  def test_bias_unavailable(self):
    r = m.settling([0.0, 0.1, 0.2], [0.0, 0.1, 0.2])
    self.assertIsNone(r['settling_s'])

  def test_settling(self):
    self.assertEqual(m.settling([1.0, -1.0, -1.0], [1.0, 0.0, -1.0])['settling_s'], 0.01)

  def test_bias(self):
    self.assertEqual(m.settling([1.0, 1.0, 1.0], [1.0, 1.0, 1.0])['steady_bias'], 0.0)


if __name__ == '__main__':
  unittest.main()
