"""Saved-only deterministic synthetic store, no actual private roots."""

import tempfile
import unittest
from pathlib import Path
import numpy as np
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_store as s


class TestStore(unittest.TestCase):
  def test_replicas_resume(self):
    with tempfile.TemporaryDirectory() as tmp:
      root = Path(tmp)
      manifests = []
      for replica in ('repeat-1', 'repeat-2'):
        with s.synthetic_output(root / replica):
          s.array_write(root / replica / 'coeff.npy.gz', np.array([1.0, -0.0]))
          s.write_json(root / replica / 'model.json', s.p.seal({'schema': 'SYNTHETIC_MODEL', 'coeff': 'coeff.npy.gz'}))
          manifests.append(s.finish(root / replica, {'schema': 'V4_RUN_MANIFEST', 'synthetic': True}))
      self.assertEqual(manifests[0], manifests[1])
      self.assertEqual(s.verify(root / 'repeat-1', manifests[0]['receipt_sha256']), manifests[0])
      (root / 'repeat-1' / 'coeff.npy.gz').write_bytes(b'broken')
      with self.assertRaisesRegex(ValueError, 'V4_RESUME_INTEGRITY_FAILURE'):
        s.verify(root / 'repeat-1', manifests[0]['receipt_sha256'])

  def test_output_authority(self):
    with tempfile.TemporaryDirectory() as tmp:
      with self.assertRaises(ValueError):
        s.write_json(Path(tmp) / 'not-authorized.json', {})

  def test_atomic_no_overwrite(self):
    with tempfile.TemporaryDirectory() as tmp:
      root = Path(tmp)
      with s.synthetic_output(root):
        row = s.p.seal({'schema': 'SYNTHETIC'})
        s.write_json(root / 'receipt.json', row)
        before = (root / 'receipt.json').read_bytes()
        with self.assertRaisesRegex(ValueError, 'NO_OVERWRITE'):
          s.write_json(root / 'receipt.json', row)
        self.assertEqual(before, (root / 'receipt.json').read_bytes())
        self.assertFalse((root / 'receipt.json.atomic').exists())

  def test_symlink_and_traversal(self):
    with tempfile.TemporaryDirectory() as tmp:
      root = Path(tmp)
      (root / 'link').symlink_to(root)
      with s.synthetic_output(root):
        for path in (root / 'link' / 'file.json', root / '..' / 'escaped.json'):
          with self.subTest(path=path), self.assertRaises(ValueError):
            s.write_json(path, s.p.seal({'schema': 'SYNTHETIC'}))

  def test_array_receipt_decode(self):
    with tempfile.TemporaryDirectory() as tmp:
      root = Path(tmp)
      with s.synthetic_output(root):
        receipt = s.array_write(root / 'x.npy.gz', np.array([1.0, 2.0]))
        receipt['array_sha256'] = '0' * 64
        s.write_json(root / 'receipt.json', s.p.seal({'schema': 'SYNTHETIC', 'arrays': {'x': receipt}}))
        manifest = s.finish(root, {'schema': 'V4_RUN_MANIFEST', 'synthetic': True})
      with self.assertRaisesRegex(ValueError, 'V4_RESUME_INTEGRITY_FAILURE'):
        s.verify(root, manifest['receipt_sha256'])
