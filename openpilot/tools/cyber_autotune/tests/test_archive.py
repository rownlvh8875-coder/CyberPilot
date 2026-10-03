from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from openpilot.tools.cyber_autotune import archive
from openpilot.tools.cyber_autotune.archive import ArchiveError, load_audit, load_proposal, save_audit, save_proposal
from openpilot.tools.cyber_autotune.archive_codec import encode_audit, encode_proposal
from openpilot.tools.cyber_autotune.audit import append_event
from openpilot.tools.cyber_autotune.profiles import inspect_proposal
from openpilot.tools.cyber_autotune.tests.test_audit import started, terminal
from openpilot.tools.cyber_autotune.tests.test_profiles import proposal


class TestArchive(unittest.TestCase):
  def setUp(self):
    self.temp = tempfile.TemporaryDirectory()
    self.addCleanup(self.temp.cleanup)
    self.root = Path(self.temp.name) / 'archive'
    self.root.mkdir(mode=0o700)
    self.path = str(self.root)
    self.profile = inspect_proposal(proposal()).profile_sha256
    self.file = self.root / f'proposal-{self.profile}.json'
    self.first = append_event((), started())
    self.finished = append_event(self.first, terminal(self.first))
    self.run = '1' * 64

  def test_proposal_roundtrip_and_identical_save_never_overwrites(self):
    self.assertEqual(save_proposal(self.path, proposal()), self.profile)
    identity = self.file.stat().st_ino
    self.assertEqual(load_proposal(self.path, self.profile), proposal())
    self.assertEqual(save_proposal(self.path, proposal()), self.profile)
    self.assertEqual(self.file.stat().st_ino, identity)
    self.assertEqual(stat.S_IMODE(self.file.stat().st_mode), 0o600)
    self.assertEqual(list(self.root.iterdir()), [self.file])
    variant = replace(proposal(), review=replace(proposal().review, minimum=2))
    with self.assertRaises(ArchiveError):
      save_proposal(self.path, variant)
    self.assertEqual(self.file.read_bytes(), encode_proposal(proposal()))

  def test_audit_requires_durable_start_and_preserves_terminal(self):
    with self.assertRaises(ArchiveError):
      save_audit(self.path, self.finished)
    self.assertEqual(list(self.root.iterdir()), [])
    save_audit(self.path, self.first)
    self.assertEqual(load_audit(self.path, self.run), self.first)
    save_audit(self.path, self.finished)
    save_audit(self.path, self.finished)
    save_audit(self.path, self.first)
    self.assertEqual(load_audit(self.path, self.run), self.finished)
    conflict = append_event(self.first, terminal(self.first, 'FAILED'))
    with self.assertRaises(ArchiveError):
      save_audit(self.path, conflict)
    changed = append_event((), replace(started(), reasons=('CHANGED',)))
    with self.assertRaises(ArchiveError):
      save_audit(self.path, append_event(changed, terminal(changed)))
    self.assertEqual(load_audit(self.path, self.run), self.finished)

  def test_invalid_contract_or_noncanonical_root_and_hash_create_nothing(self):
    for root in (None, '/', self.path + '/', self.path + '/../archive', 'relative', self.path + '/missing'):
      with self.subTest(root=root), self.assertRaises(ArchiveError):
        save_proposal(root, proposal())
    for key in ('../escape', 'A' * 64, '', True):
      with self.subTest(key=key), self.assertRaises(ArchiveError):
        load_proposal(self.path, key)
    with self.assertRaises(ArchiveError):
      save_proposal(self.path, replace(proposal(), name='steer_max'))
    with self.assertRaises(ArchiveError):
      save_audit(self.path, ())
    self.assertEqual(list(self.root.iterdir()), [])

  def test_symlink_ancestors_and_targets_never_follow(self):
    alias = Path(self.temp.name) / 'alias'
    alias.symlink_to(self.root, target_is_directory=True)
    with self.assertRaises(ArchiveError):
      save_proposal(str(alias), proposal())
    outside = Path(self.temp.name) / 'outside'
    outside.write_bytes(b'PRESERVE')
    self.file.symlink_to(outside)
    for operation in (lambda: load_proposal(self.path, self.profile), lambda: save_proposal(self.path, proposal())):
      with self.assertRaises(ArchiveError):
        operation()
    self.assertEqual(outside.read_bytes(), b'PRESERVE')

  def test_hardlink_special_and_oversized_files_are_not_read_as_artifacts(self):
    outside = Path(self.temp.name) / 'outside'
    outside.write_bytes(encode_proposal(proposal()))
    os.link(outside, self.file)
    with self.assertRaises(ArchiveError):
      load_proposal(self.path, self.profile)
    self.file.unlink()
    os.mkfifo(self.file)
    with self.assertRaises(ArchiveError):
      load_proposal(self.path, self.profile)
    self.file.unlink()
    self.file.write_bytes(b'x' * (1048576 + 1))
    with self.assertRaises(ArchiveError):
      load_proposal(self.path, self.profile)
    with self.assertRaises(ArchiveError):
      save_proposal(self.path, proposal())
    self.assertEqual(self.file.stat().st_size, 1048576 + 1)

  def test_corrupt_or_orphan_audit_is_not_repaired(self):
    final = self.root / f'job-{self.run}-1.json'
    final.write_bytes(encode_audit(self.finished))
    with self.assertRaises(ArchiveError):
      load_audit(self.path, self.run)
    with self.assertRaises(ArchiveError):
      save_audit(self.path, self.first)
    self.assertFalse((self.root / f'job-{self.run}-0.json').exists())
    final.unlink()
    save_audit(self.path, self.first)
    start_file = self.root / f'job-{self.run}-0.json'
    start_file.write_bytes(b'{')
    with self.assertRaises(ArchiveError):
      save_audit(self.path, self.finished)
    self.assertEqual(start_file.read_bytes(), b'{')

  def test_unsafe_directory_mode_or_owner_reject_without_mutating_permissions(self):
    self.root.chmod(0o777)
    with self.assertRaises(ArchiveError):
      save_proposal(self.path, proposal())
    self.assertEqual(stat.S_IMODE(self.root.stat().st_mode), 0o777)
    self.root.chmod(0o700)
    actual_uid = os.geteuid()
    with patch('openpilot.tools.cyber_autotune.archive.os.geteuid', return_value=actual_uid + 1), self.assertRaises(ArchiveError):
      save_proposal(self.path, proposal())
    self.assertEqual(list(self.root.iterdir()), [])

  def test_prepublication_failures_do_not_commit_or_leave_owned_temporary(self):
    for boundary in ('fsync', 'rename'):
      target = 'openpilot.tools.cyber_autotune.archive.' + ('os.fsync' if boundary == 'fsync' else '_rename_no_replace')
      with self.subTest(boundary=boundary), patch(target, side_effect=OSError('PRIVATE_ERROR')), self.assertRaises(ArchiveError) as error:
        save_proposal(self.path, proposal())
      self.assertNotIn('PRIVATE_ERROR', str(error.exception))
      self.assertEqual(list(self.root.iterdir()), [])

  def test_postpublication_fsync_failure_is_not_success_and_retry_verifies(self):
    original = os.fsync

    def fail_directory(fd):
      if stat.S_ISDIR(os.fstat(fd).st_mode):
        raise OSError('injected directory durability failure')
      original(fd)

    with patch('openpilot.tools.cyber_autotune.archive.os.fsync', fail_directory), self.assertRaises(ArchiveError):
      save_proposal(self.path, proposal())
    self.assertTrue(self.file.exists())
    self.assertEqual(load_proposal(self.path, self.profile), proposal())
    self.assertEqual(save_proposal(self.path, proposal()), self.profile)

  def test_atomic_publication_refuses_noncooperating_racing_target(self):
    original = archive._rename_no_replace

    def race(fd, temporary, target):
      descriptor = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600, dir_fd=fd)
      try:
        os.write(descriptor, b'RACING_TARGET')
      finally:
        os.close(descriptor)
      original(fd, temporary, target)

    with patch('openpilot.tools.cyber_autotune.archive._rename_no_replace', race), self.assertRaises(ArchiveError):
      save_proposal(self.path, proposal())
    self.assertEqual(self.file.read_bytes(), b'RACING_TARGET')
    self.assertEqual(list(self.root.iterdir()), [self.file])

  def test_concurrent_conflicting_terminal_preserves_one_winner(self):
    save_audit(self.path, self.first)
    rejected = append_event(self.first, terminal(self.first, 'FAILED'))

    def attempt(chain):
      try:
        save_audit(self.path, chain)
        return 'SAVED'
      except ArchiveError as error:
        return error.code

    with ThreadPoolExecutor(max_workers=2) as pool:
      outcomes = list(pool.map(attempt, (self.finished, rejected)))
    self.assertEqual(outcomes.count('SAVED'), 1)
    self.assertTrue(set(outcomes) <= {'SAVED', 'BUSY', 'CONFLICT'})
    winner = load_audit(self.path, self.run)
    loser = rejected if winner == self.finished else self.finished
    self.assertIn(winner, (self.finished, rejected))
    with self.assertRaises(ArchiveError):
      save_audit(self.path, loser)
    self.assertEqual(load_audit(self.path, self.run), winner)

  def test_process_restart_and_crash_orphan_preserve_verified_artifacts(self):
    code = '''
import os, sys
from openpilot.tools.cyber_autotune import archive
from openpilot.tools.cyber_autotune.tests.test_profiles import proposal
def crash(*args):
  os._exit(17)
archive._rename_no_replace = crash
archive.save_proposal(sys.argv[1], proposal())
'''
    result = subprocess.run([sys.executable, '-c', code, self.path], capture_output=True, timeout=10.)
    self.assertEqual(result.returncode, 17)
    orphan = list(self.root.iterdir())
    self.assertEqual(len(orphan), 1)
    self.assertFalse(self.file.exists())
    with self.assertRaises(ArchiveError):
      load_proposal(self.path, self.profile)
    save_proposal(self.path, proposal())
    self.assertTrue(orphan[0].exists())
    save_audit(self.path, self.first)
    read_code = '''
import sys
from openpilot.tools.cyber_autotune.archive import load_audit, load_proposal
from openpilot.tools.cyber_autotune.profiles import inspect_proposal
assert len(load_audit(sys.argv[1], '1'*64)) == 1
assert not inspect_proposal(load_proposal(sys.argv[1], sys.argv[2])).runtime_accepted
'''
    restarted = subprocess.run([sys.executable, '-c', read_code, self.path, self.profile], capture_output=True, timeout=10.)
    self.assertEqual(restarted.returncode, 0, restarted.stderr.decode())


if __name__ == '__main__':
  unittest.main()
