from dataclasses import replace
import tempfile
import unittest
from pathlib import Path
import os
import stat
import subprocess
import sys
from unittest.mock import patch

from openpilot.tools.cyber_autotune.tests.test_profiles import proposal


class TestProfileRehearsal(unittest.TestCase):
  def new(self):
    from openpilot.tools.cyber_autotune.profile_rehearsal import new_rehearsal
    candidate = proposal()
    return new_rehearsal(replace(candidate, proposed_value=candidate.baseline_value), candidate)

  def test_confirmation_never_opens_vehicle_activation_and_rollback_is_memory_only(self):
    from openpilot.tools.cyber_autotune.profile_rehearsal import advance, assess
    original = self.new()
    state = original
    for action in ('SANDBOX', 'SHADOW_REHEARSAL', 'REVIEW', 'REQUEST_ACTIVATION'):
      state = advance(state, action, 'OFFLINE_TEST', 'd' * 64, operator_confirmed=True)
    self.assertEqual(assess(state)['state'], 'ACTIVATION_BLOCKED')
    for key in ('runtime_accepted', 'vehicle_write_enabled', 'can_write_enabled', 'active_profile_enabled'):
      self.assertIs(assess(state)[key], False)
    state = advance(state, 'FAULT', 'SOURCE_MISMATCH', 'e' * 64)
    self.assertEqual(assess(state)['state'], 'ROLLBACK_PENDING')
    state = advance(state, 'ROLLBACK', 'VERIFIED_SNAPSHOT', 'f' * 64)
    self.assertEqual(assess(state)['state'], 'ROLLED_BACK')
    self.assertEqual(assess(state)['selected_snapshot_sha256'], assess(original)['baseline_snapshot_sha256'])
    self.assertFalse(assess(state)['vehicle_rollback_executed'])
    self.assertEqual(assess(original)['state'], 'INACTIVE')

  def test_atomic_roundtrip_corruption_partial_and_source_version_mismatch_fail_closed(self):
    from openpilot.tools.cyber_autotune.profile_rehearsal import save_state, load_state, advance, assess
    from openpilot.tools.cyber_autotune.archive import ArchiveError
    state = advance(self.new(), 'SANDBOX', 'OFFLINE_TEST', 'd' * 64)
    with tempfile.TemporaryDirectory() as root:
      with patch('openpilot.tools.cyber_autotune.archive._rename_no_replace', side_effect=OSError('injected')):
        with self.assertRaises(ArchiveError):
          save_state(root, state)
      self.assertEqual(list(Path(root).iterdir()), [])
      key = save_state(root, state)
      self.assertEqual(load_state(root, key, 'a' * 64, 'c' * 64), state)
      self.assertFalse(assess(load_state(root, key, 'a' * 64, 'c' * 64))['runtime_accepted'])
      with self.assertRaises(ArchiveError):
        load_state(root, key, '0' * 64, 'c' * 64)
      file = Path(root) / ('rehearsal-' + key + '.json')
      raw = file.read_bytes()
      for damaged in (b'{', raw.replace(b'profile-rehearsal-v1', b'profile-rehearsal-v9')):
        file.write_bytes(damaged)
        with self.assertRaises(ArchiveError):
          load_state(root, key, 'a' * 64, 'c' * 64)
        self.assertEqual(file.read_bytes(), damaged)

  def test_illegal_transition_untrusted_snapshot_and_forged_history_rejected(self):
    from openpilot.tools.cyber_autotune.profile_rehearsal import advance, new_rehearsal, assess
    state = self.new()
    for action in ('ACTIVE', 'ROLLBACK', 'REVIEW', 'SHADOW_REHEARSAL'):
      with self.subTest(action=action), self.assertRaises(ValueError):
        advance(state, action, 'TEST', 'a' * 64)
    with self.assertRaises(ValueError):
      new_rehearsal(proposal(), replace(proposal(), name='steer_max'))
    with self.assertRaises(ValueError):
      assess(replace(state, events=({'action': 'ACTIVE'},)))

  def test_real_process_crash_and_restart_preserve_verified_snapshot(self):
    from openpilot.tools.cyber_autotune.profile_rehearsal import save_state, load_state, encode_state
    code = '''
import os, sys
from openpilot.tools.cyber_autotune import archive
from openpilot.tools.cyber_autotune.profile_rehearsal import decode_state, save_state
state = decode_state(sys.stdin.buffer.read())
def crash(*args):
  os._exit(17)
archive._rename_no_replace = crash
save_state(sys.argv[1], state)
'''
    state = self.new()
    with tempfile.TemporaryDirectory() as root:
      crashed = subprocess.run([sys.executable, '-c', code, root], input=encode_state(state), capture_output=True, timeout=10.)
      self.assertEqual(crashed.returncode, 17)
      orphans = list(Path(root).iterdir())
      self.assertEqual(len(orphans), 1)
      self.assertTrue(orphans[0].name.startswith('.tmp-'))
      key = save_state(root, state)
      self.assertTrue(orphans[0].exists(), 'never reinterpret or delete crash residue')
      read_code = '''
import sys
from openpilot.tools.cyber_autotune.profile_rehearsal import load_state, encode_state
sys.stdout.buffer.write(encode_state(load_state(sys.argv[1], sys.argv[2], 'a'*64, 'c'*64)))
'''
      restarted = subprocess.run([sys.executable, '-c', read_code, root, key], capture_output=True, timeout=10.)
      self.assertEqual(restarted.returncode, 0)
      self.assertEqual(restarted.stdout, encode_state(state))
      self.assertEqual(load_state(root, key, 'a' * 64, 'c' * 64), state)

  def test_postpublication_durability_failure_never_reported_as_success(self):
    from openpilot.tools.cyber_autotune.profile_rehearsal import save_state, load_state
    from openpilot.tools.cyber_autotune.archive import ArchiveError
    original = os.fsync
    def fail_directory(fd):
      if stat.S_ISDIR(os.fstat(fd).st_mode):
        raise OSError('injected durability failure')
      original(fd)
    with tempfile.TemporaryDirectory() as root:
      state = self.new()
      with patch('openpilot.tools.cyber_autotune.archive.os.fsync', fail_directory), self.assertRaises(ArchiveError):
        save_state(root, state)
      self.assertEqual(len(list(Path(root).iterdir())), 1)
      key = save_state(root, state)
      self.assertEqual(load_state(root, key, 'a' * 64, 'c' * 64), state)
