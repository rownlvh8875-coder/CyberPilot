"""Fail closed if assisted rows become blind, unverified truth or detector input."""
import copy
from pathlib import Path
import tempfile
import unittest

from openpilot.tools.cyber_autotune import private_holdout_contract as h
from openpilot.tools.cyber_autotune.tests.test_private_holdout_contract import setup_package
from openpilot.tools.cyber_autotune.tests.test_private_pixel_execution import SHA, STAMP


class TestAssisted(unittest.TestCase):
  def setUp(self):
    try:
      from openpilot.tools.cyber_autotune import private_holdout_assisted as a
    except ImportError:
      self.fail('Separate assisted evidence admission is not implemented')
    self.a = a
    self.temp = tempfile.TemporaryDirectory(dir=Path.home())
    self.addCleanup(self.temp.cleanup)
    _, _, self.package = setup_package(Path(self.temp.name))
    self.auth = a.authorize(self.package, SHA[:40], STAMP, acknowledged=True)
    self.body = {'state': 'BOTH_EGO_BOUNDARIES_VISIBLE',
                 'left': [[10, 90], [15, 70], [20, 50]], 'right': [[80, 90], [75, 70], [70, 50]],
                 'reason': 'Visible marking on raw image only.', 'confidence': 'MEDIUM'}
    self.ai = a.ai_row(self.package, self.auth, 0, self.body, STAMP, observation_id='native-vision-1')
    self.human = {'action': 'ACCEPT_AI', 'state': self.body['state'], 'left': self.body['left'],
                  'right': self.body['right'], 'reviewer_id': 'reviewer-1', 'acknowledged_assisted': True, 'comment': ''}

  def test_generated_ai_has_no_human_or_blind_status(self):
    self.assertTrue(self.ai['ai_generated'])
    for key in ('human_verified', 'blind_human', 'assisted_human', 'qualification_allowed', 'sealed_reference_allowed'):
      self.assertFalse(self.ai[key])
    self.assertIsNone(self.ai['human_annotation'])

  def test_authorization_cannot_precede_materialization_authorization(self):
    with self.assertRaises(ValueError):
      self.a.authorize(self.package, SHA[:40], '2000-01-01T00:00:00Z', acknowledged=True)

  def test_authorization_required(self):
    with self.assertRaises(ValueError):
      self.a.authorize(self.package, SHA[:40], STAMP, acknowledged=False)

  def test_raw_only_generator_rejects_detector_or_model_extras(self):
    for extra in ('detector_prediction', 'modelV2', 'candidate', 'planner', 'steering'):
      with self.subTest(extra=extra), self.assertRaises(ValueError):
        self.a.ai_row(self.package, self.auth, 0, {**self.body, extra: []}, STAMP, observation_id='vision')

  def test_source_drift_rejected(self):
    auth = h.unseal(self.auth)
    auth['source_identity']['private_holdout_assisted.py'] = 'b' * 64
    with self.assertRaises(ValueError):
      self.a.ai_row(self.package, h.seal(auth), 0, self.body, STAMP, observation_id='vision')

  def test_unknown_frame_rejected(self):
    with self.assertRaises(ValueError):
      self.a.ai_row(self.package, self.auth, 60, self.body, STAMP, observation_id='vision')

  def test_stale_image_rejected(self):
    row = h.unseal(self.ai)
    row['image_sha256'] = 'b' * 64
    with self.assertRaises(ValueError):
      self.a.validate_ai(self.package, self.auth, 0, h.seal(row))

  def test_ai_immutable(self):
    path = Path(self.temp.name) / 'ai.json'
    h.write_immutable(path, self.ai)
    changed = h.seal({**h.unseal(self.ai), 'reason': 'changed'})
    with self.assertRaises(ValueError):
      h.write_immutable(path, changed)

  def test_accept_creates_separate_assisted_receipt(self):
    final = self.a.human_row(self.package, self.auth, 0, self.ai, self.human, STAMP)
    self.assertNotEqual(final['receipt_sha256'], self.ai['receipt_sha256'])
    self.assertTrue(final['human_verified'])
    self.assertTrue(final['assisted_human'])
    self.assertFalse(final['blind_human'])
    self.assertEqual(final['ai_receipt_sha256'], self.ai['receipt_sha256'])
    self.assertFalse(self.ai['human_verified'])

  def test_accept_cannot_hide_modification(self):
    body = copy.deepcopy(self.human)
    body['left'][0][0] += 1
    with self.assertRaises(ValueError):
      self.a.human_row(self.package, self.auth, 0, self.ai, body, STAMP)

  def test_modify_requires_actual_change(self):
    with self.assertRaises(ValueError):
      self.a.human_row(self.package, self.auth, 0, self.ai, {**self.human, 'action': 'MODIFY_AI'}, STAMP)
    body = copy.deepcopy(self.human)
    body['action'] = 'MODIFY_AI'
    body['left'][0][0] += 1
    final = self.a.human_row(self.package, self.auth, 0, self.ai, body, STAMP)
    self.assertEqual(final['left'][0][0], 11)

  def test_reject_or_ambiguous_cannot_retain_visible_gt(self):
    for action in ('REJECT_AI', 'AMBIGUOUS'):
      with self.subTest(action=action), self.assertRaises(ValueError):
        self.a.human_row(self.package, self.auth, 0, self.ai, {**self.human, 'action': action}, STAMP)

  def test_ambiguous_human_empty_polylines(self):
    body = {**self.human, 'action': 'AMBIGUOUS', 'state': 'EGO_BOUNDARIES_AMBIGUOUS', 'left': [], 'right': []}
    final = self.a.human_row(self.package, self.auth, 0, self.ai, body, STAMP)
    self.assertEqual(final['left'], [])

  def test_crossing_invalid_points_rejected(self):
    for left in ([[90, 90], [90, 70], [90, 50]], [[10, 90], [10, 90], [10, 50]], [[float('nan'), 90], [10, 70], [10, 50]]):
      with self.subTest(left=left), self.assertRaises(ValueError):
        self.a.ai_row(self.package, self.auth, 0, {**self.body, 'left': left}, STAMP, observation_id='vision')

  def test_acknowledgment_required(self):
    with self.assertRaises(ValueError):
      self.a.human_row(self.package, self.auth, 0, self.ai, {**self.human, 'acknowledged_assisted': False}, STAMP)

  def test_sixty_ai_zero_human_cannot_freeze_reference(self):
    ai = [self.a.ai_row(self.package, self.auth, i, self.body, STAMP, observation_id='vision') for i in range(60)]
    with self.assertRaises(ValueError):
      self.a.freeze(self.package, self.auth, ai, [], STAMP)

  def test_assisted_cannot_enter_blind_reference_gate(self):
    ai = [self.a.ai_row(self.package, self.auth, i, self.body, STAMP, observation_id='vision') for i in range(60)]
    finals = [self.a.human_row(self.package, self.auth, i, row, self.human, STAMP) for i, row in enumerate(ai)]
    reference = self.a.freeze(self.package, self.auth, ai, finals, STAMP)
    self.assertEqual(reference['schema'], 'AI_ASSISTED_HUMAN_PIXEL_REFERENCE_V1')
    self.assertEqual(reference['action_counts']['ACCEPT_AI'], 60)
    self.assertFalse(reference['sealed_reference_allowed'])
    with self.assertRaises((ValueError, KeyError)):
      h.require_detector_gate(self.package, reference)

  def test_duplicate_final_not_completion(self):
    final = self.a.human_row(self.package, self.auth, 0, self.ai, self.human, STAMP)
    with self.assertRaises(ValueError):
      self.a.freeze(self.package, self.auth, [self.ai] * 60, [final] * 60, STAMP)


if __name__ == '__main__':
  unittest.main()
