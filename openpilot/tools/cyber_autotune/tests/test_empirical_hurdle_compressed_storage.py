"""Lossless deterministic storage; no fitting or private evidence required."""

import gzip
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from openpilot.tools.cyber_autotune import empirical_hurdle_fit_cv_store as s


class TestCompressedStorage(unittest.TestCase):
  def setUp(self):
    # Synthetic fixtures need deterministic capacity, independent of CI host size.
    # Explicit low-space tests override this and exercise the real guard.
    capacity = type('Space', (), {'free': 100 * 1024**3})()
    space = patch.object(s.shutil, 'disk_usage', return_value=capacity)
    space.start()
    self.addCleanup(space.stop)

  def test_exact_arrays_and_independent_compressed_bytes(self):
    arrays = [
      np.arange(321, dtype=np.int64).reshape(3, 107),
      np.array([0.0, -0.0, 0.5, np.nextafter(0.5, 1.0)]),
      np.array([True, False]),
      np.array([], dtype=np.int16),
    ]
    with tempfile.TemporaryDirectory() as tmp:
      for i, a in enumerate(arrays):
        left, right = [Path(tmp) / n / f'{i}.npy.gz' for n in ('first', 'second')]
        x, y = s.compressed_array_write(left, a), s.compressed_array_write(right, a)
        self.assertEqual(x, y)
        self.assertEqual(left.read_bytes(), right.read_bytes())
        buffer = io.BytesIO()
        np.save(buffer, np.ascontiguousarray(a), allow_pickle=False)
        self.assertEqual(gzip.decompress(left.read_bytes()), buffer.getvalue())
        b = s.compressed_array_read(left, x)
        self.assertEqual((a.dtype, a.shape, a.tobytes()), (b.dtype, b.shape, b.tobytes()))
        self.assertFalse(left.with_suffix('').exists())

  def test_object_and_overwrite_rejected(self):
    with tempfile.TemporaryDirectory() as tmp:
      p = Path(tmp) / 'a.npy.gz'
      with self.assertRaises(ValueError):
        s.compressed_array_write(p, np.array([{}], dtype=object))
      s.compressed_array_write(p, np.arange(10))
      original = p.read_bytes()
      with self.assertRaises(ValueError):
        s.compressed_array_write(p, np.arange(11))
      self.assertEqual(p.read_bytes(), original)

  def test_low_space_before_creation(self):
    with tempfile.TemporaryDirectory() as tmp:
      p = Path(tmp) / 'a.npy.gz'
      with patch.object(s.shutil, 'disk_usage', return_value=type('Space', (), {'free': 0})()):
        with self.assertRaisesRegex(ValueError, 'STORAGE_HEADROOM'):
          s.compressed_array_write(p, np.arange(10))
      self.assertFalse(p.exists())

  def test_host_vhd_reservation_and_c_output_forbidden(self):
    gib = 1024**3

    def usage(path):
      return type('Space', (), {'free': int(1.5 * gib) if str(path) == '/mnt/d' else 100 * gib})()

    with patch.object(s.shutil, 'disk_usage', side_effect=usage), patch.object(Path, 'is_dir', return_value=True):
      with self.assertRaisesRegex(ValueError, 'STORAGE_HEADROOM_REQUIRED_HOST_D'):
        s.storage_headroom(Path('/tmp/hurdle-synthetic-space-check'), gib)
      for drive in ('c', 'e'):
        with self.assertRaisesRegex(ValueError, 'D_ONLY_RESULT_STORAGE_REQUIRED'):
          s.storage_headroom(Path('/mnt') / drive / 'hurdle-synthetic-space-check', gib)

  def test_tamper_rejected(self):
    with tempfile.TemporaryDirectory() as tmp:
      p = Path(tmp) / 'a.npy.gz'
      receipt = s.compressed_array_write(p, np.arange(10))
      p.write_bytes(p.read_bytes()[:-1] + b'x')
      with self.assertRaises(ValueError):
        s.compressed_array_read(p, receipt)

  def test_symlink_and_traversal_rejected(self):
    with tempfile.TemporaryDirectory() as tmp:
      root = Path(tmp)
      (root / 'link').symlink_to(root, target_is_directory=True)
      for path in (root / 'link/a.npy.gz', root / '../escape.npy.gz'):
        with self.assertRaises(ValueError):
          s.compressed_array_write(path, np.arange(2))


if __name__ == '__main__':
  unittest.main()
