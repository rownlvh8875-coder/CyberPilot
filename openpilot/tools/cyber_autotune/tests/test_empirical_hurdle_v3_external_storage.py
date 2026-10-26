"""Synthetic external-volume proofs; no actual private source access."""

from contextlib import ExitStack
import importlib
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch


class TestExternalVolume(unittest.TestCase):
  def setUp(self):
    try:
      self.s = importlib.import_module('openpilot.tools.cyber_autotune.empirical_hurdle_v3_external_storage')
    except ImportError:
      self.fail('External E storage amendment is not implemented')
    self.record = {'point': Path('/mnt/e'), 'root': '/', 'filesystem': '9p', 'source': 'E:\\',
                   'device': '0:73', 'mount_id': '73', 'parent_id': '1'}
    self.stack = ExitStack()
    self.addCleanup(self.stack.close)
    self.stack.enter_context(patch.object(self.s, 'mount_records', return_value=[self.record]))
    self.stack.enter_context(patch.object(self.s, 'volume_identity', return_value='b' * 64))
    self.stack.enter_context(patch.object(Path, 'is_symlink', return_value=False))
    self.stack.enter_context(patch.object(Path, 'exists', return_value=True))
    self.stack.enter_context(patch.object(Path, 'stat', return_value=SimpleNamespace(st_dev=os.makedev(0, 73), st_mode=0o40755)))
    self.stack.enter_context(patch.object(Path, 'resolve', autospec=True, side_effect=lambda p: p))

  def test_only_exact_e_volume_is_accepted(self):
    proof = self.s.prove_authorized_external_volume(Path('/mnt/e/synthetic/result'))
    self.assertEqual(proof['storage_volume'], 'E_EXTERNAL_SSD')
    for path in ('/mnt/c/result', '/mnt/d/result', '/mnt/f/result', '/home/result', '/mnt/e', 'relative/result', '/mnt/e/a/../result'):
      with self.subTest(path=path), self.assertRaises(ValueError):
        self.s.prove_authorized_external_volume(Path(path))

  def test_exact_mount_fields_and_unique_mount_required(self):
    for key, value in (('source', 'D:\\'), ('source', 'f:'), ('root', '/subtree'), ('filesystem', 'ext4'), ('device', '0:74')):
      with self.subTest(key=key, value=value), patch.object(self.s, 'mount_records', return_value=[{**self.record, key: value}]), self.assertRaises(ValueError):
        self.s.prove_authorized_external_volume(Path('/mnt/e/synthetic'))
    for rows in ([], [self.record, self.record]):
      with patch.object(self.s, 'mount_records', return_value=rows), self.assertRaises(ValueError):
        self.s.prove_authorized_external_volume(Path('/mnt/e/synthetic'))

  def test_nested_mount_both_ancestor_and_descendant_rejected(self):
    for point in ('/mnt/e/synthetic', '/mnt/e/synthetic/nested'):
      row = {**self.record, 'point': Path(point), 'mount_id': '74'}
      with self.subTest(point=point), patch.object(self.s, 'mount_records', return_value=[self.record, row]), self.assertRaises(ValueError):
        self.s.prove_authorized_external_volume(Path('/mnt/e/synthetic'))

  def test_symlink_and_resolved_alias_rejected(self):
    with patch.object(Path, 'is_symlink', return_value=True), self.assertRaises(ValueError):
      self.s.prove_authorized_external_volume(Path('/mnt/e/synthetic'))
    with patch.object(Path, 'resolve', return_value=Path('/mnt/d/alias')), self.assertRaises(ValueError):
      self.s.prove_authorized_external_volume(Path('/mnt/e/synthetic'))

  def test_mount_identity_changes_on_remount(self):
    before = self.s.prove_authorized_external_volume(Path('/mnt/e/synthetic'))
    with patch.object(self.s, 'mount_records', return_value=[{**self.record, 'mount_id': '99'}]):
      after = self.s.prove_authorized_external_volume(Path('/mnt/e/synthetic'))
      self.assertNotEqual(before['mount_identity_sha256'], after['mount_identity_sha256'])
      with self.assertRaisesRegex(ValueError, 'V3_EXTERNAL_VOLUME_IDENTITY_CONFLICT'):
        self.s.prove_authorized_external_volume(Path('/mnt/e/synthetic'), expected_mount=before['mount_identity_sha256'])

  def test_storage_scope_limits_writes_to_exact_output(self):
    root = Path('/mnt/e/synthetic/output')
    proof = self.s.prove_authorized_external_volume(root)
    auth = {'storage_volume': 'E_EXTERNAL_SSD', 'mount_identity_sha256': proof['mount_identity_sha256'], 'volume_identity_sha256': 'b' * 64}
    with self.s.output_scope(auth, root):
      self.assertTrue(self.s.checked_bound_output(root / 'repeat-1/receipt.json'))
      for path in ('/mnt/e/synthetic/source/x', '/mnt/d/result', '/home/result'):
        with self.subTest(path=path), self.assertRaises(ValueError):
          self.s.checked_bound_output(Path(path))
    self.assertFalse(self.s.checked_bound_output(root / 'outside-scope'))

  def test_storage_scope_rechecks_mount_on_every_write(self):
    root = Path('/mnt/e/synthetic/output')
    proof = self.s.prove_authorized_external_volume(root)
    auth = {'storage_volume': 'E_EXTERNAL_SSD', 'mount_identity_sha256': proof['mount_identity_sha256'], 'volume_identity_sha256': 'b' * 64}
    with self.s.output_scope(auth, root), patch.object(self.s, 'mount_records', return_value=[]), self.assertRaises(ValueError):
      self.s.checked_bound_output(root / 'receipt.json')

  def test_live_volume_drift_with_unchanged_mount_rejects_write(self):
    root = Path('/mnt/e/synthetic/output')
    proof = self.s.prove_authorized_external_volume(root)
    auth = {**proof, 'volume_identity_sha256': 'b' * 64}
    with self.s.output_scope(auth, root), patch.object(self.s, 'volume_identity', return_value='c' * 64), \
         self.assertRaisesRegex(ValueError, 'V3_EXTERNAL_VOLUME_IDENTITY_CONFLICT'):
      self.s.checked_bound_output(root / 'receipt.json')

  def test_amendment_keeps_all_base_numerical_receipts(self):
    row = self.s.amendment()
    self.assertEqual(row['change_scope'], 'STORAGE_AUTHORITY_ONLY')
    self.assertEqual(row['storage_volume'], 'E_EXTERNAL_SSD')
    self.assertEqual(row['base_policy_receipts'], {
      'policy': 'c6795b87374f696d9701e30eaaa675ec88e2e1de5e60d381bc33efd90be20925',
      'fitting-policy': 'e9991c5ea12ecf5f52b07651c08ad66be0fe1d23fccafbe90b68216ab1c1e09f',
      'execution-policy': '9f46c3ff85df88eff84f36c126eb847cd7a1b509a0de25bac1193c707e8e9461',
    })
    self.assertFalse(row['authorization_minting'])
    self.assertEqual(row['holdout'], 'CLOSED')
    self.assertEqual(row['vehicle_authority'], 'NONE')


class TestExternalAuthorization(unittest.TestCase):
  def setUp(self):
    from openpilot.tools.cyber_autotune.tests.test_empirical_hurdle_v3_authorization import TestV3Authorization as Fixture
    self.f = Fixture()
    self.f.setUp()
    self.addCleanup(self.f.doCleanups)
    from openpilot.tools.cyber_autotune import empirical_hurdle_v3_external_storage as external
    self.s = external
    self.migration = self.f.io.p.seal({'status': 'CYBERPILOT_STORAGE_MIGRATION_V1_VERIFIED',
                                     'destination_root_sha256': {k: self.f.auth['root_identities'][k] for k in ('source', 'causal', 'derived')}})
    body = {k: v for k, v in self.f.auth.items() if k != 'receipt_sha256'}
    body.update(storage_volume='E_EXTERNAL_SSD', storage_amendment_receipt_sha256=self.s.amendment()['receipt_sha256'],
                storage_migration_receipt_sha256=self.migration['receipt_sha256'], mount_identity_sha256='a' * 64,
                volume_identity_sha256='b' * 64)
    self.auth = self.f.io.p.seal(body)

  def test_external_authorization_reaches_metadata_only_after_e_proof(self):
    with patch.object(self.s, 'contracts', return_value=(self.s.amendment(), self.migration)), \
         patch.object(self.s, 'roots_checked', side_effect=lambda roots, auth: self.f.event('e-volume', None)):
      self.f.invoke(auth=self.auth)
    self.assertEqual(self.f.events, ['policies', 'head', 'e-volume', 'space', 'environment', 'metadata'])

  def test_external_auth_receipt_mutations_reject_before_private_metadata(self):
    with patch.object(self.s, 'contracts', return_value=(self.s.amendment(), self.migration)):
      for key, value in (('storage_volume', 'D_INTERNAL'), ('storage_amendment_receipt_sha256', '0' * 64),
                         ('storage_migration_receipt_sha256', '0' * 64), ('mount_identity_sha256', 'bad')):
        body = {k: v for k, v in self.auth.items() if k != 'receipt_sha256'}
        body[key] = value
        with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'V3_EXECUTION_AUTHORIZATION_CONFLICT'):
          self.f.invoke(auth=self.f.io.p.seal(body))
    self.assertNotIn('metadata', self.f.events)

  def test_volume_drift_rejects_before_private_metadata(self):
    with patch.object(self.s, 'contracts', return_value=(self.s.amendment(), self.migration)), \
         patch.object(self.s, 'roots_checked', side_effect=ValueError('V3_EXTERNAL_VOLUME_IDENTITY_CONFLICT')), \
         self.assertRaisesRegex(ValueError, 'V3_EXTERNAL_VOLUME_IDENTITY_CONFLICT'):
      self.f.invoke(auth=self.auth)
    self.assertNotIn('metadata', self.f.events)

  def test_migration_root_mismatch_rejects_before_metadata(self):
    changed = {**self.migration, 'destination_root_sha256': dict.fromkeys(('source', 'causal', 'derived'), '0' * 64)}
    with patch.object(self.s, 'contracts', return_value=(self.s.amendment(), changed)), self.assertRaises(ValueError):
      self.f.invoke(auth=self.auth)
    self.assertNotIn('metadata', self.f.events)

  def test_saved_output_checks_volume_without_source_loading(self):
    with patch.object(self.s, 'contracts', return_value=(self.s.amendment(), self.migration)), \
         patch.object(self.s, 'roots_checked') as checked:
      self.s.verify_saved_output(self.f.roots['output'], self.auth)
    self.assertEqual(checked.call_args.args[0], {'output': self.f.roots['output']})


class TestExternalCompleteRuns(unittest.TestCase):
  def test_amended_synthetic_32_by_two_repeat_resume_never_uses_d_writer(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_v3_execution as e
    from openpilot.tools.cyber_autotune import empirical_hurdle_v3_io as io
    from openpilot.tools.cyber_autotune.tests.hurdle_v3_fixtures import fixture
    external = io.external
    with tempfile.TemporaryDirectory() as name, patch.object(io, 'prove_d'), patch.object(io, 'free_bytes', return_value=10**15):
      original = fixture(Path(name), all_jobs=True)
      auth = io.p.seal({**{k: v for k, v in original.authorization.items() if k != 'receipt_sha256'},
                        'storage_volume': 'E_EXTERNAL_SSD', 'mount_identity_sha256': 'a' * 64,
                        'volume_identity_sha256': 'b' * 64, 'policies': external.BASE_RECEIPTS,
                        'storage_amendment_receipt_sha256': external.amendment()['receipt_sha256']})
      migration = io.p.seal({'destination_root_sha256': {k: auth['root_identities'][k] for k in ('source', 'causal', 'derived')}})
      auth = io.p.seal({**{k: v for k, v in auth.items() if k != 'receipt_sha256'},
                        'storage_migration_receipt_sha256': migration['receipt_sha256']})
      permit = io.Permit(original.roots, auth, auth['receipt_sha256'], original.pack, original.jobs,
                         original.records, original.pins, original.record_sha256)
      io._PERMITS[permit] = permit.trusted_sha256  # Synthetic core only; real preflight rejects this schema.
      history = {(j['candidate_id'], j['fold']): {**j, 'train_metrics': None} for j in permit.jobs}
      with patch.object(io, 'preflight', return_value=permit), \
           patch.object(io, 'prove_d', side_effect=AssertionError('D writer reached by E execution')), \
           patch.object(external, 'prove_authorized_external_volume', return_value={'storage_volume': 'E_EXTERNAL_SSD', 'mount_identity_sha256': 'a' * 64}), \
           patch.object(external, 'roots_checked'), \
           patch.object(external, 'volume_identity', return_value='b' * 64), \
           patch.object(external, 'contracts', return_value=(external.amendment(), migration)), \
           patch.object(e, 'comparison_history', side_effect=lambda c, f: history[c, f]):
        first = e.run(authorization=auth, authorization_sha256=permit.trusted_sha256, replica='repeat-1')
        second = e.run(authorization=auth, authorization_sha256=permit.trusted_sha256, replica='repeat-2')
        self.assertEqual(first, second)
        self.assertEqual(first['job_count'], 32)
        for replica in ('repeat-1', 'repeat-2'):
          self.assertEqual(e.trapped_resume(permit.roots['output'] / replica, permit.trusted_sha256, first['receipt_sha256']), first)
        repeated = e.repeatability(permit.roots['output'], permit.trusted_sha256, first['receipt_sha256'], second['receipt_sha256'])
        self.assertEqual(repeated['status'], 'V3_EXACT_REPEATABILITY_PASS')
        cleanup = e.cleanup_eligibility(permit.roots['output'], permit.trusted_sha256, first['receipt_sha256'], second['receipt_sha256'],
                                        {key: permit.roots[key] for key in ('source', 'causal', 'derived')})
        self.assertTrue(cleanup['eligible'])
        self.assertFalse(cleanup['deletion_performed'])
        self.assertTrue((permit.roots['output'] / 'repeat-2').is_dir())


class TestExternalManifestAndNumericBoundary(unittest.TestCase):
  def test_manifest_members_only_hash_size_and_mutation(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_v3_external_storage as external
    with tempfile.TemporaryDirectory() as directory:
      root = Path(directory)
      (root / 'pinned.bin').write_bytes(b'opaque fixture')
      (root / 'not-listed.bin').write_bytes(b'must never be opened')
      pins = {'pinned.bin': external.p.sha(b'opaque fixture')}
      with patch.object(Path, 'rglob', side_effect=AssertionError('broad scan')), \
           patch.object(Path, 'iterdir', side_effect=AssertionError('inventory')):
        row = external.verify_manifest_members(root, pins, sizes={'pinned.bin': 14})
      self.assertEqual((row['members'], row['bytes']), (1, 14))
      for files, sizes in ((pins, {'pinned.bin': 13}), ({'../outside': 'a' * 64}, None), ({'pinned.bin': '0' * 64}, None)):
        with self.subTest(files=files, sizes=sizes), self.assertRaises(ValueError):
          external.verify_manifest_members(root, files, sizes=sizes)
      (root / 'pinned.bin').write_bytes(b'changed')
      with self.assertRaises(ValueError):
        external.verify_manifest_members(root, pins)

  def test_post_admission_volume_drift_blocks_numeric_model_open(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_v3_io as io
    from openpilot.tools.cyber_autotune.tests.hurdle_v3_fixtures import fixture
    with tempfile.TemporaryDirectory() as name, patch.object(io, 'prove_d'), patch.object(io, 'free_bytes', return_value=10**15):
      original = fixture(Path(name))
      auth = io.p.seal({**{k: v for k, v in original.authorization.items() if k != 'receipt_sha256'},
                        'storage_volume': 'E_EXTERNAL_SSD', 'mount_identity_sha256': 'a' * 64, 'volume_identity_sha256': 'b' * 64})
      permit = io.Permit(original.roots, auth, auth['receipt_sha256'], original.pack, original.jobs,
                         original.records, original.pins, original.record_sha256)
      io._PERMITS[permit] = permit.trusted_sha256
      with patch.object(io.external, 'volume_identity', return_value='c' * 64), \
           patch.object(io.external, 'prove_authorized_external_volume'), \
           patch.object(io, 'decode_bound_array', side_effect=AssertionError('numeric open reached')), \
           self.assertRaisesRegex(ValueError, 'V3_EXTERNAL_VOLUME_IDENTITY_CONFLICT'):
        io.load_model(permit, permit.jobs[0], 'stage1')
