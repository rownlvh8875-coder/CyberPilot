import unittest
from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_salvage_publication as pub


class TestSalvagePublication(unittest.TestCase):
  def test_private_path_refused(self):
    with self.assertRaisesRegex(ValueError, 'PRIVATE'):
      pub.validate(p.seal({'schema': 'EMPIRICAL_TEST', 'private_path': 'hidden'}))

  def test_per_row_payload_refused(self):
    with self.assertRaisesRegex(ValueError, 'PRIVATE'):
      pub.validate(p.seal({'schema': 'EMPIRICAL_TEST', 'predictions': [0.1]}))

  def test_authority_refused(self):
    r = p.seal({'schema': 'EMPIRICAL_TEST'})
    r['production_authority'] = True
    with self.assertRaises(ValueError):
      pub.validate(r)

  def test_aggregate_metrics_permitted(self):
    self.assertEqual(pub.validate(p.seal({'schema': 'EMPIRICAL_TEST', 'count': 3}))['count'], 3)

  def test_immutable_public_write(self):
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as t:
      file = Path(t) / 'result.json'
      pub.write(file, p.seal({'schema': 'EMPIRICAL_TEST', 'count': 3}))
      with self.assertRaisesRegex(ValueError, 'IMMUTABLE'):
        pub.write(file, p.seal({'schema': 'EMPIRICAL_TEST', 'count': 4}))
