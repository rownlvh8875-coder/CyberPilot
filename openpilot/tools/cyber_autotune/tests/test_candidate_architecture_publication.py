"""Public receipt tamper rejection; no private evidence access."""
from copy import deepcopy
import unittest

from openpilot.tools.cyber_autotune import candidate_architecture as a
from openpilot.tools.cyber_autotune import candidate_architecture_publication as p


class TestArchitecturePublication(unittest.TestCase):
  def test_exact_frozen_set(self):
    self.assertEqual(set(p.load()), set(p.FILES))

  def test_resealed_change_rejected(self):
    row = deepcopy(p.load()['readiness'])
    row['search_execution_allowed'] = True
    row['receipt_sha256'] = a.hash_object({k: v for k, v in row.items() if k != 'receipt_sha256'})
    with self.assertRaises(ValueError):
      p.validate(row)

  def test_unsealed_content_change(self):
    row = deepcopy(p.load()['matrix'])
    row['roles']['FROZEN_EVALUATION'] = True
    with self.assertRaises(ValueError):
      p.validate(row)

  def test_private_unknown_field_rejected(self):
    row = deepcopy(p.load()['decision'])
    row['private_path'] = '/private/example'
    with self.assertRaises(ValueError):
      p.validate(row)

  def test_source_binding(self):
    p.validate_sources(p.load())

  def test_history_unchanged(self):
    r = p.load()['readiness']
    self.assertEqual(r['historical_verdicts'], dict(a.HISTORY))
    self.assertEqual(r['v2_historical_violations'], 37)
    self.assertFalse(r['reference_track_modified'])

  def test_no_authorization(self):
    for row in p.load().values():
      self.assertFalse(row['production_authority'])
      self.assertFalse(row['parameter_search_allowed'])
      self.assertFalse(row['qualification_allowed'])
      self.assertFalse(row['sealed_reference_allowed'])
