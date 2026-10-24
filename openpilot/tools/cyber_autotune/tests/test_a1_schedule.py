import importlib
import math
import unittest

from openpilot.selfdrive.controls.lib.cyber_lateral.speed_aware_tune import SpeedAwareTuneTable, SpeedTunePoint


def table(factors=(4., 4.015625), frictions=(.125, .125), response=1.):
  return SpeedAwareTuneTable(tuple(SpeedTunePoint(speed, factor, friction, response)
                                  for speed, factor, friction in zip((0., 10.), factors, frictions, strict=True)), 'synthetic-test')


class TestA1Schedule(unittest.TestCase):
  def prepare(self, tune, speeds=(0., 5., 10.), factor=4., friction=.125):
    try:
      module = importlib.import_module('openpilot.tools.cyber_autotune.a1_schedule')
    except ModuleNotFoundError:
      self.fail('A1 whole-schedule admission is not implemented')
    return module.prepare_schedule(tune, speeds, factor, friction)

  def test_interpolation_and_endpoints_are_immutable(self):
    # Wrong interpolation or skipping endpoint validation must fail this test.
    self.assertEqual(self.prepare(table()), ((0., 4., .125, 4., .125),
                                            (5., 4.0078125, .125, 4.0078125, .125),
                                            (10., 4.015625, .125, 4.015625, .125)))

  def test_effective_wire_speed_and_tuning_are_used(self):
    rows = self.prepare(table(), (5.00000001,))
    self.assertEqual(rows, ((5., 4.0078125, .125, 4.0078125, .125),))

  def test_exact_transition_allowed_but_above_it_rejected(self):
    self.assertEqual(self.prepare(table(), (10.,))[0][3], 4.015625)
    with self.assertRaises(ValueError):
      self.prepare(table(factors=(4., 4.03125)), (10.,))
    self.assertEqual(self.prepare(table(frictions=(.125, .1259765625)), (10.,))[0][4], .1259765625)
    with self.assertRaises(ValueError):
      self.prepare(table(frictions=(.125, .126953125)), (10.,))

  def test_late_domain_exit_or_transition_rejects_whole_sequence(self):
    for speeds in ((0., 1., 10.1), (0., 1., -1.), (0., 1., float('nan')), (0., 1., True), (0., 1., 1e100)):
      with self.subTest(speeds=speeds), self.assertRaises(ValueError):
        self.prepare(table(), speeds)
    with self.assertRaises(ValueError):
      self.prepare(table(factors=(4., 4.03125)), (0., 1., 10.))

  def test_unvisited_bad_knot_and_nonidentity_response_rejected(self):
    for tune in (table(factors=(4., 4.0625001)), table(frictions=(.125, .1328126)),
                 table(response=1.001), table(factors=(4., 1e300))):
      with self.subTest(tune=tune), self.assertRaises(ValueError):
        self.prepare(tune, (0.,))

  def test_invalid_baseline_and_empty_inputs_rejected(self):
    for value in (True, 0., -1., math.inf, math.nan, 10 ** 400):
      with self.subTest(value=value), self.assertRaises(ValueError):
        self.prepare(table(), factor=value)
    for speeds in ((), [], (False,), (10 ** 400,)):
      with self.subTest(speeds=speeds), self.assertRaises(ValueError):
        self.prepare(table(), speeds)


if __name__ == '__main__':
  unittest.main()
