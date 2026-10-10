import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


class TestPolicy(unittest.TestCase):
  def setUp(self):
    self.assertIsNotNone(importlib.util.find_spec('openpilot.tools.cyber_autotune.empirical_plant_policy'), 'empirical policy missing')
    from openpilot.tools.cyber_autotune import empirical_plant_policy as p

    self.p = p

  def rows(self):
    return [
      {
        'route_id': self.p.sha(b'route'),
        'ordinal': i,
        'segment_id': self.p.sha(str(i).encode()),
        'source_sha256': self.p.sha(str(i).encode()),
        'bytes': 20,
        'source_key': f'route--{i}/rlog.zst',
      }
      for i in range(95)
    ]

  def test_split_disjoint(self):
    r = self.p.split(self.rows())
    self.assertEqual(len(r['segments']), 95)
    self.assertEqual({x['role'] for x in r['segments']}, {'TRAIN', 'DEVELOPMENT', 'HOLDOUT', 'EMBARGO'})
    self.assertEqual(len({x['segment_id'] for x in r['segments']}), 95)

  def test_adjacent_cross_role_rejected_by_construction(self):
    r = self.p.split(self.rows())['segments']
    for a, b in zip(r, r[1:], strict=False):
      if a['role'] != 'EMBARGO' and b['role'] != 'EMBARGO':
        self.assertEqual(a['role'], b['role'])

  def test_split_independent_of_input_order(self):
    self.assertEqual(self.p.split(self.rows()), self.p.split(list(reversed(self.rows()))))

  def test_split_no_quality_fields(self):
    r = self.rows()
    r[0]['output_quality'] = 1
    with self.assertRaises(ValueError):
      self.p.split(r)

  def test_duplicate_rejected(self):
    r = self.rows()
    r.append(r[0])
    with self.assertRaises(ValueError):
      self.p.split(r)

  def test_atomic_immutable_resume(self):
    with tempfile.TemporaryDirectory() as t:
      path = Path(t) / 'x.json'
      r = self.p.seal({'v': 1})
      self.p.persist(path, r)
      self.p.persist(path, r)
      with self.assertRaises(ValueError):
        self.p.persist(path, self.p.seal({'v': 2}))

  def test_corrupt_receipt_rejected(self):
    r = self.p.seal({'v': 1})
    r['v'] = 2
    with self.assertRaises(ValueError):
      self.p.verify(r)

  def test_inventory_metadata_only(self):
    with tempfile.TemporaryDirectory() as t:
      root = Path(t)
      (root / 'x--0').mkdir()
      (root / 'x--0' / 'rlog.zst').write_bytes(b'not decoded')
      (root / 'x--0' / 'qcamera.ts').write_bytes(b'never open')
      r = self.p.inventory(root)
      self.assertEqual(len(r['segments']), 1)
      self.assertEqual(r['file_types']['qcamera.ts'], 1)

  def test_policy_no_candidate_or_vehicle(self):
    r = self.p.policy()
    for k in ('ta_execution', 'sg_execution', 'production_authority', 'qualification_allowed', 'sealed_reference_allowed'):
      self.assertIs(r[k], False)

  def test_model_grid_bounded(self):
    r = self.p.family_policy()
    self.assertEqual(len(r['candidates']), 8)
    self.assertEqual({c['family'] for c in r['candidates']}, {'ARX1', 'FIR25'})

  def test_policy_serialization(self):
    r = self.p.policy()
    self.assertEqual(self.p.verify(json.loads(json.dumps(r))), r)
