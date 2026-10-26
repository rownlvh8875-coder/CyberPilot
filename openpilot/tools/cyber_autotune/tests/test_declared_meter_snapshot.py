import json
import tempfile
import unittest
from pathlib import Path

from openpilot.tools.cyber_autotune import declared_meter_snapshot as s
from openpilot.tools.cyber_autotune import declared_meter_evidence as e
from openpilot.tools.cyber_autotune import declared_meter_diagnostic as m


class TestMeterSnapshot(unittest.TestCase):
  def fixture(self):
    r = m.output(
      {
        'schema': 'DECLARED_HYPOTHESIS_APPROX_METER_ENVELOPE_V1',
        'status': 'CONDITIONAL_DIAGNOSTIC_COMPLETE',
        'policy': m.policy(),
        'source_bindings': e.frozen_bindings(),
        'coverage': e.frozen_coverage(),
        'fixed_distance': [],
        'holdout_projection': [],
        'scenario_attribution': [],
        'all_declared_envelopes': [],
        'executor_identity': e.executor_identity(),
        'point_derivative_set_sha256': '0' * 64,
      }
    )
    return e.publication(r)

  def test_exact_snapshot_roundtrip(self):
    r = self.fixture()
    with tempfile.TemporaryDirectory() as d:
      s.write(r, Path(d))
      self.assertEqual(s.load(Path(d)), r)

  def test_corrupt_chunk_rejected(self):
    with tempfile.TemporaryDirectory() as d:
      s.write(self.fixture(), Path(d))
      p = Path(d) / s.part_name('fixed_distance')
      p.write_bytes(p.read_bytes() + b' ')
      with self.assertRaises(ValueError):
        s.load(Path(d))

  def test_unknown_filename_rejected(self):
    with self.assertRaises(ValueError):
      s.part_name('../private')

  def test_source_immutable(self):
    with tempfile.TemporaryDirectory() as d:
      r = self.fixture()
      s.write(r, Path(d))
      s.write(r, Path(d))
      self.assertEqual(s.load(Path(d)), r)

  def test_index_has_no_point_coordinates(self):
    with tempfile.TemporaryDirectory() as d:
      s.write(self.fixture(), Path(d))
      x = json.loads((Path(d) / s.INDEX).read_bytes())
      self.assertEqual(len(x['tables']), 4)
      self.assertNotIn('qcamera_pairs', x)


if __name__ == '__main__':
  unittest.main()
