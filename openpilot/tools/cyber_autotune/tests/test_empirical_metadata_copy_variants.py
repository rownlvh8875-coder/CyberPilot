import unittest


class TestMetadataCopyVariants(unittest.TestCase):
  def test_only_declared_copy_names(self):
    from openpilot.tools.cyber_autotune import empirical_metadata_copy_variants as c

    self.assertTrue(c.is_variant('rlog-1.zst'))
    self.assertTrue(c.is_variant('rlog (1).zst'))
    self.assertTrue(c.is_variant('opaque--3--rlog-1.zst'))
    self.assertTrue(c.is_variant('opaque--3--rlog (1).zst'))
    for name in ('rlog.zst', 'rlog.zip', '../rlog-1.zst', 'qcamera.ts', 'rlog-2.zst'):
      self.assertFalse(c.is_variant(name))

  def test_byte_match_only_proves_existing_copy(self):
    from openpilot.tools.cyber_autotune import empirical_metadata_copy_variants as c

    self.assertEqual(c.classify('a' * 64, {'a' * 64}), 'IDENTICAL_BYTE_COPY_OF_ALREADY_INVENTORIED_LOG')
    self.assertEqual(c.classify('b' * 64, {'a' * 64}), 'UNRESOLVED_COPY_FILENAME_METADATA_ONLY')

  def test_unknown_copy_not_new_or_untouched_route(self):
    from openpilot.tools.cyber_autotune import empirical_metadata_copy_variants as c

    self.assertEqual(c.classify('b' * 64, set()), 'UNRESOLVED_COPY_FILENAME_METADATA_ONLY')
