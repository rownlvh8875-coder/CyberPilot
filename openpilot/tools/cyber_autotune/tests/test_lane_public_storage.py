import copy
import multiprocessing
import os
from pathlib import Path
import signal
import tempfile
import unittest
from unittest.mock import patch

from openpilot.tools.cyber_autotune import lane_public_storage as s
from openpilot.tools.cyber_autotune.lane_tail_report import seal


def kill_before_rename(root):
  with patch.object(s.os, 'fsync', side_effect=lambda _: os.kill(os.getpid(), signal.SIGKILL)):
    s.atomic_json(Path(root) / 'value.json', seal({'value': 1}))


def kill_before_index(root, run, expected, row):
  cache = s.DurableRun(root, run, expected)
  cache.recover(lambda r: r)
  original = s.atomic_json

  def write(path, value):
    if Path(path).name == 'index.json':
      os.kill(os.getpid(), signal.SIGKILL)
    return original(path, value)

  with patch.object(s, 'atomic_json', side_effect=write):
    cache.put(0, row, lambda r: r)


class TestDurablePublicRun(unittest.TestCase):
  def setUp(self):
    self.temp = tempfile.TemporaryDirectory()
    self.root = Path(self.temp.name)
    self.run = seal(dict.fromkeys(('source', 'weight', 'config', 'environment', 'preprocessing', 'metric', 'image', 'mask'), 'a' * 64))
    self.expected = ['imgs/a.png', 'imgs/b.png']

  def tearDown(self):
    self.temp.cleanup()

  def row(self, ordinal=0, status='COMPLETED'):
    return seal({'run_sha256': self.run['receipt_sha256'], 'ordinal': ordinal, 'frame_status': status, 'value': ordinal})

  def cache(self):
    return s.DurableRun(self.root, self.run, self.expected)

  def test_restart_recovers_exact_rows_without_inference(self):
    cache = self.cache()
    cache.put(0, self.row(), lambda r: r)
    restarted = self.cache()
    self.assertEqual(restarted.recover(lambda r: r), {0: self.row()})
    self.assertEqual(restarted.missing(), [1])
    self.assertEqual(restarted.index()['storage_status'], 'INTERRUPTED_RESUMABLE')

  def test_each_identity_change_rejects_prior_cache_before_reader(self):
    self.cache().put(0, self.row(), lambda r: r)
    for key in self.run:
      if key == 'receipt_sha256':
        continue
      changed = {k: v for k, v in self.run.items() if k != 'receipt_sha256'}
      changed[key] = 'b' * 64
      with self.subTest(identity=key), self.assertRaises(ValueError):
        s.DurableRun(self.root, seal(changed), self.expected)

  def test_changed_input_order_or_count_rejects(self):
    self.cache()
    for expected in (self.expected[::-1], self.expected[:1], [self.expected[0]] * 2):
      with self.assertRaises(ValueError):
        s.DurableRun(self.root, self.run, expected)

  def test_corrupt_row_is_partial_invalid_and_not_reusable(self):
    cache = self.cache()
    cache.put(0, self.row(), lambda r: r)
    cache.row_path(0).write_text('{}')
    with self.assertRaises(ValueError):
      self.cache().recover(lambda r: r)
    self.assertEqual(cache.index()['storage_status'], 'PARTIAL_INVALID')

  def test_missing_indexed_receipt_fails_closed(self):
    cache = self.cache()
    cache.put(0, self.row(), lambda r: r)
    cache.row_path(0).unlink()
    with self.assertRaises(ValueError):
      self.cache().recover(lambda r: r)
    self.assertFalse(cache.marker_path.exists())

  def test_duplicate_index_receipt_rejected(self):
    cache = self.cache()
    cache.put(0, self.row(), lambda r: r)
    core = {k: v for k, v in cache.index().items() if k != 'receipt_sha256'}
    core['rows'] += copy.deepcopy(core['rows'])
    s.atomic_json(cache.index_path, seal(core))
    with self.assertRaises(ValueError):
      self.cache().recover(lambda r: r)

  def test_early_completion_marker_cannot_be_created(self):
    cache = self.cache()
    cache.put(0, self.row(), lambda r: r)
    with self.assertRaises(ValueError):
      cache.complete({'summary.json': seal({'value': 1})}, lambda r: r)
    self.assertFalse(cache.marker_path.exists())
    self.assertFalse((self.root / 'summary.json').exists())

  def test_completed_marker_is_last_binds_outputs_and_all_rows(self):
    cache = self.cache()
    for i in range(2):
      cache.put(i, self.row(i, 'REFERENCE_UNAVAILABLE' if i else 'COMPLETED'), lambda r: r)
    marker = cache.complete({'summary.json': seal({'frames': 2})}, lambda r: r)
    self.assertEqual(marker['processed'], 2)
    self.assertEqual(marker['expected'], 2)
    self.assertEqual(marker['storage_status'], 'COMPLETED')
    self.assertEqual(self.cache().verify_completed(lambda r: r), marker)
    (self.root / 'summary.json').write_text('{}')
    with self.assertRaises(ValueError):
      self.cache().verify_completed(lambda r: r)

  def test_failed_frame_never_completes(self):
    cache = self.cache()
    for i in range(2):
      cache.put(i, self.row(i, 'DETECTOR_FAILED'), lambda r: r)
    with self.assertRaises(ValueError):
      cache.complete({'summary.json': {}}, lambda r: r)
    self.assertFalse(cache.marker_path.exists())

  def test_mismatched_row_binding_or_ordinal_or_unsealed_row_rejected(self):
    cache = self.cache()
    for row in (self.row(1), seal({'run_sha256': 'f' * 64, 'ordinal': 0, 'frame_status': 'COMPLETED'}), {}):
      with self.assertRaises(ValueError):
        cache.put(0, row, lambda r: r)
    self.assertEqual(cache.missing(), [0, 1])

  def test_row_is_immutable_and_validator_failure_never_writes(self):
    cache = self.cache()
    cache.put(0, self.row(), lambda r: r)
    changed = self.row()
    changed = seal({**{k: v for k, v in changed.items() if k != 'receipt_sha256'}, 'value': 123})
    with self.assertRaises(ValueError):
      cache.put(0, changed, lambda r: r)
    with self.assertRaises(ValueError):
      cache.put(1, self.row(1), lambda r: (_ for _ in ()).throw(ValueError('INVALID_INPUT_SHA')))
    self.assertFalse(cache.row_path(1).exists())

  def test_process_kill_before_rename_does_not_publish_partial_json(self):
    proc = multiprocessing.get_context('fork').Process(target=kill_before_rename, args=(str(self.root),))
    proc.start()
    proc.join(5)
    self.assertEqual(proc.exitcode, -signal.SIGKILL)
    self.assertFalse((self.root / 'value.json').exists())

  def test_process_kill_after_row_before_index_recovers_orphan_exactly(self):
    self.cache().recover(lambda r: r)
    proc = multiprocessing.get_context('fork').Process(target=kill_before_index, args=(str(self.root), self.run, self.expected, self.row()))
    proc.start()
    proc.join(5)
    self.assertEqual(proc.exitcode, -signal.SIGKILL)
    restarted = self.cache()
    self.assertEqual(restarted.recover(lambda r: r), {0: self.row()})
    self.assertEqual(restarted.missing(), [1])

  def test_batch_row_durable_before_index_flush(self):
    cache = self.cache()
    cache.recover(lambda r: r)
    cache.put(0, self.row(), lambda r: r, sync_index=False)
    self.assertEqual(cache.index()['rows'], [])
    self.assertEqual(self.cache().recover(lambda r: r)[0], self.row())
    cache.flush_index()
    self.assertEqual(cache.index()['rows'][0]['receipt_sha256'], self.row()['receipt_sha256'])

  def test_bounded_recovery_does_not_retain_large_row_payload(self):
    cache = self.cache()
    cache.put(0, self.row(), lambda r: r)
    recovered = self.cache().recover(lambda r: r, retain=False)
    self.assertEqual(recovered[0]['receipt_sha256'], self.row()['receipt_sha256'])
    self.assertNotIn('value', recovered[0])

  def test_exclusive_writer_lease_released_after_context(self):
    with s.writer_lease(self.root):
      with self.assertRaises(ValueError):
        with s.writer_lease(self.root):
          pass
    with s.writer_lease(self.root):
      pass

  def test_new_directory_entry_is_fsynced_in_parent(self):
    synced = []
    original = os.fsync

    def record(fd):
      synced.append(Path(os.readlink('/proc/self/fd/' + str(fd))))
      original(fd)

    with patch.object(s.os, 'fsync', side_effect=record):
      s.atomic_json(self.root / 'new' / 'value.json', {'value': 1})
    self.assertIn(self.root, synced)

  def test_final_identity_guard_failure_before_marker_cannot_complete(self):
    cache = self.cache()
    for i in range(2):
      cache.put(i, self.row(i), lambda r: r)

    def reject():
      raise ValueError('ACTIVE_IDENTITY_CHANGED_DURING_AGGREGATE_WRITE')

    with self.assertRaises(ValueError):
      cache.complete({'summary.json': {'value': 1}}, lambda r: r, before_marker=reject)
    self.assertFalse(cache.marker_path.exists())

  def test_unicode_filename_alias_duplicate_rejected(self):
    cache = self.cache()
    cache.put(0, self.row(), lambda r: r)
    (cache.rows_dir / ('\u0660' * 5 + '.json')).write_bytes(cache.row_path(0).read_bytes())
    with self.assertRaises(ValueError):
      self.cache().recover(lambda r: r)

  def test_existing_completion_cannot_be_overwritten(self):
    cache = self.cache()
    for i in range(2):
      cache.put(i, self.row(i), lambda r: r)
    original = cache.complete({'summary.json': {'value': 1}}, lambda r: r)
    with self.assertRaises(ValueError):
      cache.complete({'summary.json': {'value': 2}}, lambda r: r)
    self.assertEqual(cache.verify_completed(lambda r: r), original)

  def test_symlink_receipt_and_index_are_rejected(self):
    cache = self.cache()
    outside = self.root / 'outside.json'
    s.atomic_json(outside, self.row())
    cache.row_path(0).symlink_to(outside)
    with self.assertRaises(ValueError):
      cache.recover(lambda r: r)


if __name__ == '__main__':
  unittest.main()
