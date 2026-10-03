import copy
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import traceback
import unittest
from unittest.mock import patch

from openpilot.tools.cyber_autotune.replay_admission import inspect_replay_input


class TestReplayAdmission(unittest.TestCase):
  def setUp(self):
    directory = tempfile.TemporaryDirectory()
    self.addCleanup(directory.cleanup)
    self.root = Path(directory.name)
    self.source = self.root / 'source'
    self.source.mkdir()
    (self.source / 'module.py').write_bytes(b'pass\n')
    self.git('init', '-q')
    self.git('add', 'module.py')
    self.git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-qm', 'fixture')
    self.head = self.git('rev-parse', 'HEAD').strip()
    self.data = self.root / 'data'
    self.data.mkdir()
    (self.data / 'input').write_bytes(b'abc')
    self.grant = {'input_id': 'window', 'root': str(self.data), 'path': 'input', 'role': 'development',
                      'segment': 29, 'size_bytes': 3, 'sha256': hashlib.sha256(b'abc').hexdigest()}
    self.request = {'version': 1, 'process': 'torqued', 'input_id': 'window',
                        'source': {'root': str(self.source), 'head': self.head,
                                    'files': {'module.py': hashlib.sha256(b'pass\n').hexdigest()}},
                        'initial_state': {'run_start_ns': 100, 'cache_mode': 'recorded_before_start', 'cache_time_ns': 90,
                                           'previous_cp_sha256': '1' * 64, 'torque_cache_sha256': '2' * 64,
                                           'original_cp_sha256': '3' * 64, 'migrated_cp_sha256': '4' * 64,
                                           'initialized_cp_sha256': '5' * 64, 'review_sha256': '6' * 64,
                                           'sampling_review_sha256': '7' * 64}}

  def git(self, *args):
    return subprocess.check_output(['git', '-C', str(self.source), *args], text=True, stderr=subprocess.DEVNULL)

  def inspect(self, request=None, grants=None):
    return inspect_replay_input(self.request if request is None else request,
                                grants=(self.grant,) if grants is None else grants, authority_sha256='a' * 64)

  def test_verified_snapshot_never_grants_execution_or_promotion(self):
    before = copy.deepcopy(self.request)
    result = self.inspect()
    self.assertEqual(result, self.inspect())
    self.assertEqual(result['status'], 'INPUT_SNAPSHOT_VERIFIED')
    self.assertEqual(result['input_sha256'], 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad')
    self.assertEqual(result['source_head'], self.head)
    for field in ('replay_allowed', 'runtime_accepted', 'promotable'):
      self.assertIs(result[field], False)
    self.assertEqual(self.request, before)

  def test_denied_or_duplicate_grants_reject_before_file_open(self):
    cases = [(), (dict(self.grant, input_id='other'),), (self.grant, self.grant)]
    cases += [(dict(self.grant, role=role),) for role in ('holdout', 'validation', 'unclassified')]
    cases += [(dict(self.grant, segment=segment),) for segment in (53, 71, True, -1)]
    for grants in cases:
      with self.subTest(grants=grants), patch('os.open', side_effect=AssertionError('opened denied bytes')):
        with self.assertRaises(ValueError):
          self.inspect(grants=grants)

  def test_invalid_state_and_schema_rejected_before_open(self):
    variants = [dict(self.request, **{k: v}) for k, v in [('version', True), ('process', 'card'), ('extra', 0)]]
    for key, value in [('cache_mode', 'unknown'), ('cache_time_ns', 100), ('cache_time_ns', 101),
                       ('run_start_ns', True), ('run_start_ns', 0), ('cache_time_ns', float('nan')),
                       ('previous_cp_sha256', None), ('review_sha256', ''), ('sampling_review_sha256', None)]:
      variants.append(dict(self.request, initial_state=dict(self.request['initial_state'], **{key: value})))
    for request in variants:
      with self.subTest(request=request), patch('os.open', side_effect=AssertionError('opened invalid bytes')):
        with self.assertRaises(ValueError):
          self.inspect(request)

  def test_reviewed_empty_cache_must_not_include_cache_data(self):
    state = dict(self.request['initial_state'], cache_mode='reviewed_empty', cache_time_ns=None,
                 previous_cp_sha256=None, torque_cache_sha256=None)
    self.assertFalse(self.inspect(dict(self.request, initial_state=state))['replay_allowed'])
    for key in ('cache_time_ns', 'previous_cp_sha256', 'torque_cache_sha256'):
      with self.subTest(key=key), self.assertRaises(ValueError):
        self.inspect(dict(self.request, initial_state=dict(state, **{key: self.request['initial_state'][key]})))

  def test_unsafe_paths_are_rejected(self):
    for path in ('../data/input', '/etc/passwd', './input', 'x/../input', 'x//input', 'input/', 'x\\input'):
      with self.subTest(path=path), self.assertRaises(ValueError):
        self.inspect(grants=(dict(self.grant, path=path),))

  def test_root_parent_and_leaf_symlinks_are_rejected(self):
    (self.data / 'alias').symlink_to(self.data / 'input')
    (self.data / 'parent').symlink_to(self.data, target_is_directory=True)
    (self.root / 'aliasroot').symlink_to(self.data, target_is_directory=True)
    for grant in (dict(self.grant, path='alias'), dict(self.grant, path='parent/input'),
                  dict(self.grant, root=str(self.root / 'aliasroot'))):
      with self.subTest(grant=grant), self.assertRaises(ValueError):
        self.inspect(grants=(grant,))

  def test_fifo_rejected_without_waiting_for_writer(self):
    os.mkfifo(self.data / 'fifo')
    with self.assertRaises(ValueError):
      self.inspect(grants=(dict(self.grant, path='fifo'),))

  def test_length_hash_and_modified_input_rejected(self):
    for size, digest in ((2, self.grant['sha256']), (4, self.grant['sha256']), (3, '0' * 64),
                         (True, self.grant['sha256']), (0, self.grant['sha256'])):
      with self.subTest(size=size), self.assertRaises(ValueError):
        self.inspect(grants=(dict(self.grant, size_bytes=size, sha256=digest),))
    (self.data / 'input').write_bytes(b'xyz')
    with self.assertRaises(ValueError):
      self.inspect()

  def test_source_revision_hash_dirty_worktree_and_index_rejected(self):
    for source in (dict(self.request['source'], head='0' * 40),
                   dict(self.request['source'], files={'module.py': '0' * 64})):
      with self.subTest(source=source), self.assertRaises(ValueError):
        self.inspect(dict(self.request, source=source))
    (self.source / 'module.py').write_bytes(b'changed\n')
    with self.assertRaises(ValueError):
      self.inspect()
    self.git('add', 'module.py')
    with self.assertRaises(ValueError):
      self.inspect()

  def test_receipt_binds_initial_state_and_authority(self):
    first = self.inspect()
    request = copy.deepcopy(self.request)
    request['initial_state']['review_sha256'] = 'b' * 64
    self.assertNotEqual(first['request_sha256'], self.inspect(request)['request_sha256'])
    other = inspect_replay_input(self.request, grants=(self.grant,), authority_sha256='c' * 64)
    self.assertNotEqual(first['authority_sha256'], other['authority_sha256'])

  def test_source_subdirectory_cannot_inherit_parent_repository_identity(self):
    child = self.source / 'child'
    child.mkdir()
    (child / 'module.py').write_bytes(b'pass\n')
    request = dict(self.request, source=dict(self.request['source'], root=str(child)))
    with self.assertRaises(ValueError):
      self.inspect(request)

  def test_git_status_must_not_run_local_fsmonitor_hook(self):
    marker = self.root / 'hook-ran'
    hook = self.root / 'monitor'
    hook.write_text(f'#!/bin/sh\ntouch {marker}\nprintf "token\\0"\n')
    hook.chmod(0o700)
    self.git('config', 'core.fsmonitor', str(hook))
    result = self.inspect()
    self.assertEqual(result['status'], 'INPUT_SNAPSHOT_VERIFIED')
    self.assertFalse(marker.exists())

  def test_rejection_traceback_does_not_expose_private_filename(self):
    grant = dict(self.grant, path='PRIVATE_FILENAME_SENTINEL')
    try:
      self.inspect(grants=(grant,))
    except ValueError:
      self.assertNotIn('PRIVATE_FILENAME_SENTINEL', traceback.format_exc())
    else:
      self.fail('Missing file was accepted')

  def test_git_clean_filter_is_rejected_before_it_can_execute(self):
    (self.source / '.gitattributes').write_text('module.py filter=probe\n')
    self.git('add', '.gitattributes')
    self.git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-qm', 'attribute')
    self.request['source']['head'] = self.git('rev-parse', 'HEAD').strip()
    marker = self.root / 'clean-filter-ran'
    self.git('config', 'filter.probe.clean', f'touch {marker}; cat')
    (self.source / 'module.py').write_bytes(b'fail\n')
    with self.assertRaises(ValueError):
      self.inspect()
    self.assertFalse(marker.exists())

  def test_nested_repository_filter_is_rejected_before_recursive_status(self):
    nested = self.source / 'nested'
    nested.mkdir()
    def child_git(*args):
      return subprocess.check_output(['git', '-C', str(nested), *args], text=True, stderr=subprocess.DEVNULL)
    child_git('init', '-q')
    (nested / 'module.py').write_bytes(b'pass\n')
    (nested / '.gitattributes').write_text('module.py filter=probe\n')
    child_git('add', '.')
    child_git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-qm', 'nested')
    head = child_git('rev-parse', 'HEAD').strip()
    self.git('update-index', '--add', '--cacheinfo', f'160000,{head},nested')
    self.git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-qm', 'gitlink')
    self.request['source']['head'] = self.git('rev-parse', 'HEAD').strip()
    self.assertEqual(self.inspect()['status'], 'INPUT_SNAPSHOT_VERIFIED')
    marker = self.root / 'nested-filter-ran'
    child_git('config', 'filter.probe.clean', f'touch {marker}; cat')
    (nested / 'module.py').write_bytes(b'fail\n')
    with self.assertRaises(ValueError):
      self.inspect()
    self.assertFalse(marker.exists())


if __name__ == '__main__':
  unittest.main()
