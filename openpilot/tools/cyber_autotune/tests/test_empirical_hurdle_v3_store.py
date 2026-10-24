"""Synthetic D-volume doubles; real compression, file integrity and no overwrite."""

from contextlib import ExitStack
import gzip
import importlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np


class TestV3Store(unittest.TestCase):
  def setUp(self):
    try:
      self.s = importlib.import_module('openpilot.tools.cyber_autotune.empirical_hurdle_v3_store')
    except ImportError:
      self.fail('V3 result store not implemented')
    self.tmp = tempfile.TemporaryDirectory()
    self.addCleanup(self.tmp.cleanup)
    self.root = Path(self.tmp.name)
    self.stack = ExitStack()
    self.addCleanup(self.stack.close)
    self.stack.enter_context(patch.object(self.s.io, 'prove_d'))
    self.stack.enter_context(patch.object(self.s.io, 'free_bytes', return_value=10**15))

  def test_deterministic_compression_and_three_hashes(self):
    array = np.array([0., -0., 1.5, np.nextafter(1., 2.)], dtype=np.float64)
    first = self.s.array_write(self.root / 'one.npy.gz', array)
    second = self.s.array_write(self.root / 'two.npy.gz', array)
    payload = (self.root / 'one.npy.gz').read_bytes()
    self.assertEqual(payload, (self.root / 'two.npy.gz').read_bytes())
    self.assertEqual(first['file_sha256'], second['file_sha256'])
    self.assertEqual(first['npy_sha256'], self.s.p.sha(gzip.decompress(payload)))
    self.assertEqual(first['array_sha256'], self.s.io.legacy.old.array_digest(array))
    self.assertEqual(payload[4:8], b'\0\0\0\0')
    self.assertEqual(payload[3] & 8, 0)
    with self.assertRaisesRegex(ValueError, 'NO_OVERWRITE'):
      self.s.array_write(self.root / 'one.npy.gz', array)

  def test_no_model_truth_or_hold_path_duplication(self):
    arrays = {'predicted_gate': np.array([True, False]), 'projected_next_tick': np.array([1, 0], np.int16)}
    self.s.population(self.root / 'train', arrays, {'schema': 'SYNTHETIC', 'population': 'train'})
    for key in ('coefficients', 'normalizer', 'observed_path', 'hold_last_path', 'target_next_tick'):
      with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'PAYLOAD_SCHEMA'):
        self.s.population(self.root / key, {**arrays, key: np.zeros(2)}, {'schema': 'SYNTHETIC', 'population': 'train'})

  def test_manifest_last_integrity_and_no_extra_member(self):
    self.s.write_json(self.root / 'result.json', self.s.p.seal({'value': 1}))
    manifest = self.s.finish(self.root, {'schema': 'SYNTHETIC'})
    self.assertEqual(self.s.verify_manifest(self.root), manifest)
    (self.root / 'foreign.json').write_text('{}')
    with self.assertRaisesRegex(ValueError, 'V3_RESUME_INTEGRITY_FAILURE'):
      self.s.verify_manifest(self.root)

  def test_partial_or_single_byte_mutation_rejected(self):
    self.s.write_json(self.root / 'result.json', self.s.p.seal({'value': 1}))
    self.s.finish(self.root, {'schema': 'SYNTHETIC'})
    (self.root / 'result.json').write_bytes(b'x')
    with self.assertRaisesRegex(ValueError, 'V3_RESUME_INTEGRITY_FAILURE'):
      self.s.verify_manifest(self.root)

  def test_traversal_colon_backslash_and_symlink_rejected(self):
    for name in ('../outside', 'a:b', 'a\\b', '/outside'):
      with self.subTest(name=name), self.assertRaises(ValueError):
        self.s.io.member(self.root, name)
    (self.root / 'alias').symlink_to(self.root, target_is_directory=True)
    with self.assertRaises(ValueError):
      self.s.array_write(self.root / 'alias/x.npy.gz', np.zeros(2))

  def test_capacity_never_drops_payload(self):
    with patch.object(self.s.io, 'free_bytes', return_value=0):
      with self.assertRaisesRegex(ValueError, 'V3_STORAGE_CAPACITY_BLOCKED'):
        self.s.array_write(self.root / 'blocked.npy.gz', np.zeros(2))
    self.assertFalse((self.root / 'blocked.npy.gz').exists())

  def test_nonfinite_and_object_arrays_rejected(self):
    for array in (np.array([float('nan')]), np.array([object()])):
      with self.assertRaises(ValueError):
        self.s.array_write(self.root / 'invalid.npy.gz', array)

  def test_new_directory_entries_are_durable_before_receipt_returns(self):
    events, original = [], self.s.durable_directory

    def observe(path):
      events.append(path)
      return original(path)

    with patch.object(self.s, 'durable_directory', side_effect=observe):
      self.s.write_json(self.root / 'new/nested/receipt.json', self.s.p.seal({'value': 1}))
    self.assertEqual(events, [self.root, self.root / 'new', self.root / 'new/nested'])
