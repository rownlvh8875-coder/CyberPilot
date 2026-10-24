"""No video decoder is called during encoded-only camera metadata inventory."""
import tempfile
from pathlib import Path
import unittest

from openpilot.tools.cyber_autotune import private_camera_metadata as m
from openpilot.tools.cyber_autotune import private_pixel_executor as e


def ue(value):
  bits = bin(value + 1)[2:]
  return '0' * (len(bits) - 1) + bits


def sps(width_mbs=33, height_mbs=21, crop_right=1, crop_bottom=3):
  bits = f'{66:08b}' + '00000000' + f'{30:08b}' + ue(0)
  bits += ue(0) + ue(0) + ue(0) + ue(1) + '0' + ue(width_mbs - 1) + ue(height_mbs - 1)
  bits += '1' + '1' + '1' + ue(0) + ue(crop_right) + ue(0) + ue(crop_bottom)
  bits += '1'
  bits += '0' * ((8 - len(bits) % 8) % 8)
  return bytes(int(bits[i:i+8], 2) for i in range(0, len(bits), 8))


class TestEncodedMetadata(unittest.TestCase):
  def test_known_cropped_geometry(self):
    self.assertEqual(m.sps_geometry(sps()), (526, 330))

  def test_known_alternative_geometry(self):
    self.assertEqual(m.sps_geometry(sps(80, 45, 0, 0)), (1280, 720))

  def test_truncated_sps_rejected(self):
    with self.assertRaises(ValueError):
      m.sps_geometry(b'\x42')

  def test_aud_count_no_decode(self):
    data = b'\0\0\1\x67' + sps() + (b'\0\0\1\x09\xf0' * 12)
    value = m.h264_metadata(data, [i * 4500 for i in range(12)])
    self.assertEqual(value, {'width': 526, 'height': 330, 'frame_count': 12, 'fps': 20.0, 'codec': 'h264'})

  def test_missing_aud_rejects_unknown_frame_count(self):
    with self.assertRaises(ValueError):
      m.h264_metadata(b'\0\0\1\x67' + sps(), [])

  def test_transport_corruption_rejected(self):
    with self.assertRaises(ValueError):
      m.ts_metadata(b'bad transport')

  def test_atomic_image_rejects_symlink_before_write(self):
    with tempfile.TemporaryDirectory() as temp:
      root = Path(temp)
      target = root / 'outside'
      target.mkdir()
      (root / 'images').symlink_to(target, target_is_directory=True)
      with self.assertRaises(ValueError):
        e.atomic_image(root / 'images/test.png', b'fixture-only')
      self.assertFalse((target / 'test.png').exists())
