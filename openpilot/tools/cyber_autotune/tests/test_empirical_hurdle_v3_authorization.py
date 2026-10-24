"""No actual private root: preflight ordering and immutable reference guards."""

from contextlib import ExitStack
from copy import deepcopy
import importlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from openpilot.tools.cyber_autotune import empirical_plant_policy as p


class TestV3Authorization(unittest.TestCase):
  def setUp(self):
    try:
      self.io = importlib.import_module('openpilot.tools.cyber_autotune.empirical_hurdle_v3_io')
    except ImportError:
      self.fail('V3 authorization boundary not implemented')
    self.tmp = tempfile.TemporaryDirectory()
    self.addCleanup(self.tmp.cleanup)
    self.root = Path(self.tmp.name)
    self.roots = {name: self.root / name for name in ('source', 'causal', 'derived', 'output')}
    for name, root in self.roots.items():
      if name != 'output':
        root.mkdir()
    self.pack = self.io.contracts()
    self.env = {
      'python': '3.12.13', 'numpy': '2.5.3', 'OPENBLAS_NUM_THREADS': '1', 'OMP_NUM_THREADS': '1',
      'blas_build_identity_sha256': self.io.legacy.BLAS_SHA, 'dtype': 'float64', 'order': 'C', 'rng': 'NONE',
      'private_build_metadata': {}, 'zlib_runtime_version': 'synthetic',
    }
    self.head = 'c7514cbea0f87a21acae15593e63c4af70f59dee'
    self.auth = p.seal({
      'schema': self.io.AUTH_SCHEMA, 'head': self.head, 'policies': self.pack['receipts'],
      'executor_sources': self.io.sources(), 'v1_manifest_sha256': self.io.verified.SOURCE_SHA,
      'v1_authorization_sha256': self.io.verified.AUTH_SHA, 'v1_repeatability_sha256': self.io.verified.REPEAT_SHA,
      'source_manifests': {k: str(i) * 64 for i, k in enumerate(self.io.MANIFEST_KEYS, 1)},
      'root_identities': {k: p.sha(str(v).encode()) for k, v in self.roots.items()},
      'jobs': [self.io.job_identity(j) for j in self.pack['jobs']],
      'environment': self.env, 'compression': self.io.COMPRESSION,
      'capacity_preflight': {**self.io.capacity(self.pack['jobs']), 'free_bytes': 10**15},
      'no_refit_firewall_sha256': self.io.FIREWALL_SHA,
      'numeric_access_authorized': True, 'prediction_only_authorized': True, 'train_only_decision_authorized': True,
      'stage1_refit_authorized': False, 'stage2_refit_authorized': False, 'normalizer_refit_authorized': False,
      'holdout': 'CLOSED', 'opening_count': 0, 'holdout_discovery': 0, 'vehicle_authority': 'NONE',
      'pooled_refit_authorized': False, 'raw_qlog_authorized': False,
    })
    self.events = []
    self.stack = ExitStack()
    self.addCleanup(self.stack.close)
    for name, value in (
      ('contracts', lambda: self.event('policies', self.pack)),
      ('current_head', lambda: self.event('head', self.head)),
      ('prove_d', lambda root: self.event('volume', None)),
      ('free_bytes', lambda root: self.event('space', 10**15)),
      ('environment', lambda: self.event('environment', self.env)),
      ('admit_metadata', lambda *args: self.event('metadata', None)),
    ):
      self.stack.enter_context(patch.object(self.io, name, side_effect=value))

  def event(self, name, result):
    self.events.append(name)
    return result

  def invoke(self, auth=None, **changes):
    values = {f'{k}_root': v for k, v in self.roots.items()}
    values.update(authorization=self.auth if auth is None else auth, authorization_sha256=(self.auth if auth is None else auth)['receipt_sha256'])
    values.update(changes)
    return self.io.preflight(**values)

  def test_missing_authorization_never_opens_private_metadata(self):
    with self.assertRaisesRegex(ValueError, 'V3_PRIVATE_EXECUTION_NOT_AUTHORIZED'):
      self.io.preflight(authorization=None, authorization_sha256=None)
    self.assertEqual(self.events, ['policies', 'head'])

  def test_precheck_order_reaches_metadata_last(self):
    original = getattr(self.io, 'non_overlap', lambda _: None)
    with patch.object(self.io, 'non_overlap', side_effect=lambda roots: self.event('overlap', original(roots)), create=True):
      self.invoke()
    self.assertEqual(self.events, ['policies', 'head', 'volume', 'overlap', 'space', 'environment', 'metadata'])

  def test_authorization_document_is_read_after_public_checks(self):
    path = self.root / 'external-authorization.json'
    p.persist(path, self.auth)
    original = self.io.read_json

    def observe(*args):
      self.events.append('authorization')
      return original(*args)

    with patch.object(self.io, 'read_json', side_effect=observe):
      self.invoke(authorization=path)
    self.assertEqual(self.events, ['policies', 'head', 'authorization', 'volume', 'space', 'environment', 'metadata'])

  def test_descendant_bind_alias_is_rejected(self):
    alias = self.root / 'alias'
    alias.mkdir()
    output = alias / 'new-output'
    changed = {**self.roots, 'output': output}
    auth = p.seal({**{k: v for k, v in self.auth.items() if k not in ('receipt_sha256', *p.FIREWALL)},
                   'root_identities': {k: p.sha(str(v).encode()) for k, v in changed.items()}})
    with patch.object(self.io, 'mount_points', return_value={Path('/'), alias}, create=True):
      with self.assertRaisesRegex(ValueError, 'V3_OUTPUT_ROOT_INVALID'):
        self.invoke(auth=auth, output_root=output)

  def test_malformed_or_untrusted_receipt_rejects_before_roots(self):
    for bad in ({}, {'receipt_sha256': '0' * 64}):
      with self.assertRaisesRegex(ValueError, 'V3_EXECUTION_AUTHORIZATION_CONFLICT'):
        self.io.preflight(authorization=bad, authorization_sha256='0' * 64)
    with self.assertRaisesRegex(ValueError, 'V3_EXECUTION_AUTHORIZATION_CONFLICT'):
      self.invoke(authorization_sha256='0' * 64)
    self.assertNotIn('volume', self.events)
    self.assertNotIn('metadata', self.events)

  def test_authorization_mutations(self):
    for key, value in (
      ('head', '0' * 40), ('v1_manifest_sha256', '0' * 64), ('policies', {}),
      ('executor_sources', {}), ('no_refit_firewall_sha256', '0' * 64),
      ('stage1_refit_authorized', True), ('normalizer_refit_authorized', True),
      ('holdout', 'OPEN'), ('opening_count', True), ('raw_qlog_authorized', True),
      ('vehicle_authority', 'WRITE'), ('compression', {}), ('jobs', []),
    ):
      with self.subTest(key=key):
        bad = p.seal({**{k: v for k, v in self.auth.items() if k != 'receipt_sha256'}, key: value})
        p.verify(bad)
        with self.assertRaisesRegex(ValueError, 'V3_EXECUTION_AUTHORIZATION_CONFLICT'):
          self.invoke(bad)
    self.assertNotIn('metadata', self.events)

  def test_explicit_source_required_no_search(self):
    with self.assertRaisesRegex(ValueError, 'V3_PRIVATE_SOURCE_UNRESOLVED'):
      self.invoke(source_root=None)
    self.assertNotIn('metadata', self.events)
    with patch.object(self.io, 'admit_metadata', side_effect=FileNotFoundError('missing synthetic source manifest')):
      with self.assertRaisesRegex(ValueError, 'V3_PRIVATE_SOURCE_UNRESOLVED'):
        self.invoke()

  def test_root_identity_overlap_traversal_and_symlink(self):
    for changed in (self.root / 'other', self.roots['source'], self.root / 'a/../output'):
      with self.subTest(root=changed), self.assertRaises(ValueError):
        self.invoke(output_root=changed)
    alias = self.root / 'alias'
    alias.symlink_to(self.roots['source'], target_is_directory=True)
    with self.assertRaises(ValueError):
      self.invoke(source_root=alias)
    changed = {**self.roots, 'output': self.roots['source']}
    auth = p.seal({**{k: v for k, v in self.auth.items() if k != 'receipt_sha256'},
                   'root_identities': {k: p.sha(str(v).encode()) for k, v in changed.items()}})
    with self.assertRaisesRegex(ValueError, 'V3_OUTPUT_ROOT_INVALID'):
      self.invoke(auth=auth, output_root=self.roots['source'])
    self.assertNotIn('metadata', self.events)

  def test_c_output_rejected_by_real_volume_proof(self):
    self.stack.close()
    with self.assertRaisesRegex(ValueError, 'V3_OUTPUT_ROOT_INVALID'):
      self.io.prove_d(Path('/mnt/c/synthetic-result'))
    from types import SimpleNamespace
    import os
    for drive in ('D:\\', 'C:\\'):
      record = {'point': Path('/mnt/d'), 'root': '/', 'filesystem': '9p', 'source': drive, 'device': '0:72'}
      with self.subTest(drive=drive), patch.object(self.io, 'mount_records', return_value=[record], create=True), \
           patch.object(Path, 'exists', return_value=True), patch.object(Path, 'stat', return_value=SimpleNamespace(st_dev=os.makedev(0, 72), st_mode=0o40755)):
        if drive.startswith('C'):
          with self.assertRaisesRegex(ValueError, 'V3_OUTPUT_ROOT_INVALID'):
            self.io.prove_d(Path('/mnt/d/synthetic-result'))
        else:
          self.io.prove_d(Path('/mnt/d/synthetic-result'))

  def test_capacity_blocks_before_environment_and_metadata(self):
    with patch.object(self.io, 'free_bytes', return_value=0):
      with self.assertRaisesRegex(ValueError, 'V3_STORAGE_CAPACITY_BLOCKED'):
        self.invoke()
    self.assertNotIn('environment', self.events)
    self.assertNotIn('metadata', self.events)

  def test_environment_conflict_before_metadata(self):
    with patch.object(self.io, 'environment', return_value={**self.env, 'numpy': 'wrong'}):
      with self.assertRaisesRegex(ValueError, 'V3_EXECUTION_ENVIRONMENT_CONFLICT'):
        self.invoke()
    self.assertNotIn('metadata', self.events)

  def test_reference_identity_not_recomputed_or_modified(self):
    job, ref = self.pack['jobs'][0], self.pack['references'][0]
    self.io.reference(job, ref)
    for field in ('reference_tp', 'positive_count', 'negative_count', 'train_anchor_sha256', 'stage1_model_sha256', 'v1_confusion_receipt_sha256'):
      bad = deepcopy(ref)
      bad[field] = bad[field] + 1 if isinstance(bad[field], int) else '0' * 64
      with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'V3_REFERENCE_CONFLICT'):
        self.io.reference(job, bad)

  def test_refit_firewall_traps_real_fit_entrypoints(self):
    import numpy as np
    from openpilot.tools.cyber_autotune import empirical_hurdle_fit_cv_math as math
    with self.io.firewall():
      for fn in (math.fit_stage1, math.fit_stage2, math.normalizer, np.linalg.solve, np.linalg.lstsq):
        with self.assertRaisesRegex(ValueError, 'FORBIDDEN'):
          fn(None)
