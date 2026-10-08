import unittest
from unittest.mock import Mock

from openpilot.tools.cyber_autotune import private_holdout_materializer as m
from openpilot.tools.cyber_autotune import private_holdout_contract as h
from openpilot.tools.cyber_autotune.tests.test_private_holdout_contract import manifest
from openpilot.tools.cyber_autotune.tests.test_private_pixel_execution import SHA, STAMP


class TestHoldoutMaterializer(unittest.TestCase):
  def setUp(self):
    self.manifest = manifest()
    self.auth = h.authorize(self.manifest, SHA[:40], STAMP, acknowledged=True)
    self.sample = h.holdouts(self.manifest)[0]['sample_id']

  def test_no_decode_without_auth(self):
    decode = Mock()
    with self.assertRaises(ValueError):
      m.guarded_decode(self.manifest, None, self.sample, decode)
    decode.assert_not_called()

  def test_development_decode_rejected(self):
    decode = Mock()
    with self.assertRaises(ValueError):
      m.guarded_decode(self.manifest, self.auth, self.manifest['selected'][0]['sample_id'], decode)
    decode.assert_not_called()

  def test_exact_holdout_only_callback(self):
    decode = Mock(return_value=b'fixture')
    self.assertEqual(m.guarded_decode(self.manifest, self.auth, self.sample, decode), b'fixture')
    decode.assert_called_once()

  def test_no_detector_or_ai_import(self):
    import ast
    from pathlib import Path
    tree = ast.parse(Path(m.__file__).read_text())
    imports = [n.module or '' for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
    self.assertFalse(any('detector' in name or 'modeld' in name for name in imports))
