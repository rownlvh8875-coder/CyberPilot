from pathlib import Path
import tempfile
import unittest

from openpilot.tools.cyber_autotune import private_holdout_assisted as a
from openpilot.tools.cyber_autotune import private_holdout_hidden as hidden
from openpilot.tools.cyber_autotune import private_holdout_contract as h
from openpilot.tools.cyber_autotune.tests.test_private_holdout_contract import setup_package
from openpilot.tools.cyber_autotune.tests.test_private_pixel_execution import SHA, STAMP


class TestAssistedMetrics(unittest.TestCase):
  def setUp(self):
    if not hasattr(a, 'evaluate'):
      self.fail('Post-verification assisted pixel evaluation is not implemented')
    self.temp = tempfile.TemporaryDirectory(dir=Path.home())
    self.addCleanup(self.temp.cleanup)
    _, _, self.package = setup_package(Path(self.temp.name))
    self.auth = a.authorize(self.package, SHA[:40], STAMP, acknowledged=True)
    self.detector_auth = hidden.authorize(self.package, SHA[:40], STAMP, acknowledged=True)
    self.ai, self.finals, self.predictions = [], [], []
    for i in range(60):
      body = {'state': 'BOTH_EGO_BOUNDARIES_VISIBLE', 'left': [[100, 300], [110, 200], [120, 100]],
              'right': [[400, 300], [390, 200], [380, 100]], 'reason': 'Synthetic visible span', 'confidence': 'LOW'}
      if i == 59:
        body.update(state='EGO_BOUNDARIES_AMBIGUOUS', left=[], right=[])
      row = a.ai_row(self.package, self.auth, i, body, STAMP, observation_id='synthetic-only')
      self.ai.append(row)
      human = {k: body[k] for k in ('state', 'left', 'right')}
      human.update(action='ACCEPT_AI', reviewer_id='reviewer', acknowledged_assisted=True, comment='')
      self.finals.append(a.human_row(self.package, self.auth, i, row, human, STAMP))
      lanes = [{'confidence': .8, 'points': [[105, 300], [115, 200], [125, 100]]},
               {'confidence': .7, 'points': [[410, 300], [400, 200], [390, 100]]}]
      points = sorted({tuple(pt) for lane in lanes for pt in lane['points']}, key=lambda pt: (pt[1], pt[0]))
      prediction = {'image_geometry': [330, 526], 'lane_count': 2, 'points': [list(pt) for pt in points], 'lanes': lanes}
      self.predictions.append(hidden.detector_row(self.package, self.detector_auth, i, prediction, prediction, STAMP))
    self.reference = a.freeze(self.package, self.auth, self.ai, self.finals, STAMP)

  def test_known_five_ten_pixel_shifts_and_center(self):
    result = a.evaluate(self.package, self.auth, self.ai, self.reference, self.detector_auth, self.predictions)
    self.assertEqual(result['left']['median'], 5)
    self.assertEqual(result['right']['p95'], 10)
    self.assertEqual(result['center']['median'], 7.5)
    self.assertEqual(result['evaluable_visible_boundary_frames'], 59)
    self.assertEqual(result['excluded_frames'], 1)
    self.assertFalse(result['qualification_allowed'])
    self.assertEqual(result['schema'], 'AI_ASSISTED_PRIVATE_HOLDOUT_EVALUATION_V1')

  def test_incomplete_human_cannot_evaluate(self):
    bad = h.seal({**h.unseal(self.reference), 'annotations': self.finals[:59]})
    with self.assertRaises(ValueError):
      a.evaluate(self.package, self.auth, self.ai, bad, self.detector_auth, self.predictions)

  def test_unverified_ai_cannot_replace_human(self):
    bad = h.seal({**h.unseal(self.reference), 'annotations': self.ai})
    with self.assertRaises((ValueError, KeyError)):
      a.evaluate(self.package, self.auth, self.ai, bad, self.detector_auth, self.predictions)

  def test_stale_detector_rejected(self):
    bad = list(self.predictions)
    bad[0] = h.seal({**h.unseal(bad[0]), 'image_sha256': 'b' * 64})
    with self.assertRaises(ValueError):
      a.evaluate(self.package, self.auth, self.ai, self.reference, self.detector_auth, bad)

  def test_no_output_is_observed_boundary_unavailable(self):
    empty = {'image_geometry': [330, 526], 'lane_count': 0, 'points': [], 'lanes': []}
    rows = [hidden.detector_row(self.package, self.detector_auth, i, empty, empty, STAMP) for i in range(60)]
    result = a.evaluate(self.package, self.auth, self.ai, self.reference, self.detector_auth, rows)
    self.assertIsNone(result['combined']['median'])
    self.assertEqual(result['left_unavailable_visible_frames'], 59)
    self.assertEqual(result['right_unavailable_visible_frames'], 59)
    self.assertEqual(result['both_boundary_geometry_match_frames'], 0)


if __name__ == '__main__':
  unittest.main()
