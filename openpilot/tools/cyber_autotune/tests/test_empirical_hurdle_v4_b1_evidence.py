"""Synthetic integrity/provenance only; no real evidence or model execution."""

import gzip
import hashlib
import importlib
import json
import os
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

try:
  b1 = importlib.import_module('openpilot.tools.cyber_autotune.empirical_hurdle_v4_b1_evidence')
except ModuleNotFoundError:
  b1 = None

FLAGS = (
  'qualification_allowed',
  'reference_promotable',
  'sealed_reference_allowed',
  'vehicle_activation_allowed',
  'production_authority',
  'ta_execution',
  'sg_execution',
  'composition_authorized',
  'candidate_search_authorized',
  'publication_raw_data',
)
JOBS = tuple((f'HRI_D{d:02}_L{length:02}', fold) for d in (0, 5, 10, 20) for length in (1, 5, 15, 45) for fold in ('FOLD_A', 'FOLD_B'))
CONTEXT = {
  'anchor_route_id',
  'anchor_segment_sha',
  'anchor_index',
  'speed_mps',
  'speed_bin_code',
  'rail',
  'model_eligible',
  'prior_delta_tick',
  's2_ri_run_id',
  'within_run_index',
  'command_current',
  'command_feature_newest',
  'command_history',
  'anchor_order_index',
}
V1_DEV = CONTEXT | {
  'current_tick',
  'target_next_tick',
  'actual_delta_tick',
  'p_move',
  'predicted_gate',
  'integrated_delta',
  'projected_next_tick',
  'candidate_error',
  'comparator_error',
  'true_move',
  'hold_last_next_tick',
  'stage2_oracle_move_prediction',
}


def sha(raw):
  return hashlib.sha256(raw).hexdigest()


def canonical(row):
  return json.dumps(row, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def seal(body):
  body = {**body, **dict.fromkeys(FLAGS, False)}
  return {**body, 'receipt_sha256': sha(canonical(body))}


def array(dtype='<f8', n=3, *, header=None, data=None, version=1):
  width = {'<f8': 8, '<i8': 8, '|b1': 1}.get(dtype, 8)
  if header is None:
    header = str({'descr': dtype, 'fortran_order': False, 'shape': (n,)})
  text = header.encode() + b'\n'
  raw = b'\x93NUMPY' + bytes((version, 0)) + (struct.pack('<H', len(text)) if version == 1 else struct.pack('<I', len(text))) + text
  data = bytes(n * width) if data is None else data
  raw += data
  compressed = gzip.compress(raw, compresslevel=1, mtime=0)
  desc = {
    'dtype': dtype,
    'shape': [n],
    'order': 'C',
    'array_sha256': sha(data),
    'file_sha256': sha(compressed),
    'npy_sha256': sha(raw),
    'filename': 'p_move.npy.gz',
    'storage_format': 'NPY_GZIP_V1',
    'lossless_roundtrip_verified': True,
  }
  return compressed, desc


class FormatTests(unittest.TestCase):
  def setUp(self):
    self.assertIsNotNone(b1, 'B1 restricted reader not implemented')

  def inspect(self, raw, desc, **kw):
    return b1.inspect_array(raw, desc, count=3, dtype='<f8', **kw)

  def test_three_hash_layers_and_full_shape(self):
    raw, desc = array()
    result = self.inspect(raw, desc)
    self.assertEqual(result['shape'], [3])
    self.assertEqual(result['dtype'], '<f8')
    self.assertEqual(result['file_sha256'], sha(raw))
    self.assertEqual(result['array_sha256'], sha(bytes(24)))
    self.assertNotIn('values', result)

  def test_npy_v2_header(self):
    raw, desc = array(version=2)
    self.assertEqual(self.inspect(raw, desc)['shape'], [3])

  def test_file_hash_mismatch(self):
    raw, desc = array()
    with self.assertRaisesRegex(ValueError, 'HASH_CONFLICT'):
      self.inspect(raw + b'x', desc)

  def test_npy_hash_mismatch(self):
    raw, desc = array()
    with self.assertRaisesRegex(ValueError, 'HASH_CONFLICT'):
      self.inspect(raw, {**desc, 'npy_sha256': '1' * 64})

  def test_payload_hash_mismatch(self):
    raw, desc = array()
    with self.assertRaisesRegex(ValueError, 'HASH_CONFLICT'):
      self.inspect(raw, {**desc, 'array_sha256': '1' * 64})

  def test_shape_must_equal_full_count_not_first_dimension(self):
    raw, desc = array(header="{'descr':'<f8','fortran_order':False,'shape':(3,1)}")
    with self.assertRaisesRegex(ValueError, 'SCHEMA_CONFLICT'):
      self.inspect(raw, desc)

  def test_count_truncation_is_not_repaired(self):
    raw, desc = array(n=2)
    with self.assertRaisesRegex(ValueError, 'SCHEMA_CONFLICT'):
      self.inspect(raw, desc)

  def test_exact_dtype_no_cast(self):
    raw, desc = array(dtype='<i8')
    with self.assertRaisesRegex(ValueError, 'SCHEMA_CONFLICT'):
      self.inspect(raw, desc)

  def test_fortran_order_rejected(self):
    raw, desc = array(header="{'descr':'<f8','fortran_order':True,'shape':(3,)}")
    with self.assertRaisesRegex(ValueError, 'SCHEMA_CONFLICT'):
      self.inspect(raw, desc)

  def test_object_dtype_pickle_never_loaded(self):
    raw, desc = array(header="{'descr':'|O','fortran_order':False,'shape':(3,)}", data=b'not-a-pickle')
    with self.assertRaisesRegex(ValueError, 'SCHEMA_CONFLICT'):
      self.inspect(raw, desc)

  def test_structured_dtype_rejected(self):
    raw, desc = array(header="{'descr':[('x','<f8')],'fortran_order':False,'shape':(3,)}")
    with self.assertRaisesRegex(ValueError, 'SCHEMA_CONFLICT'):
      self.inspect(raw, desc)

  def test_duplicate_header_keys_rejected(self):
    raw, desc = array(header="{'descr':'|O','descr':'<f8','fortran_order':False,'shape':(3,)}")
    with self.assertRaisesRegex(ValueError, 'SCHEMA_CONFLICT'):
      self.inspect(raw, desc)

  def test_executable_header_rejected(self):
    raw, desc = array(header="dict(descr='<f8',fortran_order=False,shape=(3,))")
    with self.assertRaisesRegex(ValueError, 'SCHEMA_CONFLICT'):
      self.inspect(raw, desc)

  def test_oversized_header(self):
    raw, desc = array(header=' ' * 65536, version=2)
    with self.assertRaisesRegex(ValueError, 'SCHEMA_CONFLICT'):
      self.inspect(raw, desc)

  def test_decompression_bomb_bounded(self):
    raw, desc = array(data=bytes(100000))
    with self.assertRaisesRegex(ValueError, 'SCHEMA_CONFLICT'):
      self.inspect(raw, desc)

  def test_oversized_compressed_input_rejected(self):
    raw, desc = array()
    raw += bytes(200000)
    with self.assertRaisesRegex(ValueError, 'SCHEMA_CONFLICT'):
      self.inspect(raw, {**desc, 'file_sha256': sha(raw)})

  def test_gzip_concatenated_member_rejected(self):
    raw, desc = array()
    raw += gzip.compress(b'not-approved', mtime=0)
    with self.assertRaisesRegex(ValueError, 'SCHEMA_CONFLICT'):
      self.inspect(raw, {**desc, 'file_sha256': sha(raw)})

  def test_gzip_crc_corruption_rejected(self):
    raw, desc = array()
    raw = raw[:-8] + bytes(8)
    with self.assertRaisesRegex(ValueError, 'SCHEMA_CONFLICT'):
      self.inspect(raw, {**desc, 'file_sha256': sha(raw)})

  def test_trailing_array_bytes_rejected(self):
    raw, desc = array(data=bytes(25))
    with self.assertRaisesRegex(ValueError, 'SCHEMA_CONFLICT'):
      self.inspect(raw, desc)

  def test_false_lossless_or_bad_format_rejected(self):
    raw, desc = array()
    for changes in ({'storage_format': 'pickle'}, {'lossless_roundtrip_verified': False}, {'order': 'F'}):
      with self.subTest(changes=changes), self.assertRaisesRegex(ValueError, 'SCHEMA_CONFLICT'):
        self.inspect(raw, {**desc, **changes})


class GuardTests(unittest.TestCase):
  def setUp(self):
    self.assertIsNotNone(b1, 'B1 restricted reader not implemented')
    self.tmp = tempfile.TemporaryDirectory()
    self.addCleanup(self.tmp.cleanup)
    self.root = Path(self.tmp.name)
    self.path = self.root / 'approved.npy.gz'
    self.path.write_bytes(b'synthetic')

  def reader(self, **kw):
    v = self.root.stat()
    return b1.GuardedReader(str(self.root), (v.st_dev, v.st_ino), {str(self.path): (100, 'array')}, **kw)

  def test_exact_allowlist_no_directory_scanning(self):
    with (
      self.reader() as reader,
      patch.object(os, 'scandir', side_effect=AssertionError('scan forbidden')),
      patch.object(os, 'listdir', side_effect=AssertionError('scan forbidden')),
    ):
      self.assertEqual(reader.read(str(self.path), 100, 'array'), b'synthetic')
      self.assertEqual(reader.counters['array_file_openings'], 1)
      self.assertEqual(reader.counters['array_bytes_read'], 9)

  def test_unapproved_path_and_permission_kind_rejected_without_open(self):
    with self.reader() as reader:
      for args in ((str(self.root / 'threshold.json'), 100, 'array'), (str(self.path), 100, 'metadata'), (str(self.path), 101, 'array')):
        with self.subTest(args=args), self.assertRaises(ValueError):
          reader.read(*args)
      self.assertEqual(reader.counters['array_file_openings'], 0)

  def test_symlink_rejected(self):
    self.path.unlink()
    self.path.symlink_to(self.root / 'secret')
    with self.reader() as reader, self.assertRaises(ValueError):
      reader.read(str(self.path), 100, 'array')

  def test_duplicate_inode_rejected(self):
    other = self.root / 'alias.npy.gz'
    os.link(self.path, other)
    with self.reader() as reader, self.assertRaises(ValueError):
      reader.read(str(self.path), 100, 'array')

  def test_changed_mount_rejected(self):
    with self.assertRaises(ValueError):
      b1.GuardedReader(str(self.root), (-1, -1), {str(self.path): (100, 'array')})

  def test_oversized_file_rejected_before_payload_read(self):
    self.path.write_bytes(bytes(101))
    with self.reader() as reader, self.assertRaises(ValueError):
      reader.read(str(self.path), 100, 'array')
    self.assertEqual(reader.counters['array_file_openings'], 1)
    self.assertEqual(reader.counters['array_bytes_read'], 0)

  def test_same_target_not_reopened(self):
    with self.reader() as reader:
      reader.read(str(self.path), 100, 'array')
      with self.assertRaises(ValueError):
        reader.read(str(self.path), 100, 'array')
      self.assertEqual(reader.counters['array_file_openings'], 1)

  def test_verify_only_has_no_source_reader(self):
    with self.assertRaisesRegex(ValueError, 'RECEIPT'):
      b1.verify_only({}, '1' * 64, '2' * 64)

  def test_mutation_during_read_fails_without_retry(self):
    original = os.read

    def mutate(fd, size):
      raw = original(fd, size)
      self.path.write_bytes(b'changed-size')
      return raw

    with self.reader() as reader, patch.object(os, 'read', side_effect=mutate), self.assertRaisesRegex(ValueError, 'B1_FILE_CHANGED'):
      reader.read(str(self.path), 100, 'array')
    self.assertEqual(reader.counters['array_file_openings'], 1)
    self.assertEqual(reader.counters['array_bytes_read'], 9)


def fixture(root):
  roots = {'V4_REPEAT_1': str(root / 'r1'), 'V4_REPEAT_2': str(root / 'r2'), 'V1_REFERENCE': str(root / 'ref')}
  files = {key: {} for key in roots}
  jobs = []

  def persist(owner, name, raw):
    path = Path(roots[owner]) / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    files[owner][name] = sha(raw)

  for candidate, fold in JOBS:
    prefix = f'candidates/{candidate}/{fold}'
    job = {
      'candidate_id': candidate,
      'fold': fold,
      'train_count': 3,
      'dev_count': 3,
      'train_anchor': '1' * 64,
      'dev_anchor': '2' * 64,
      'train_manifest': '3' * 64,
      'train_receipt': '4' * 64,
    }
    for owner, role, fields, schema in (
      ('V1_REFERENCE', 'train', ('move_label', 'prior_delta_tick'), 'EMPIRICAL_HURDLE_TRAIN_POPULATION_V1'),
      ('V1_REFERENCE', 'one-step', ('true_move', 'prior_delta_tick'), 'EMPIRICAL_HURDLE_ONE_STEP_EVIDENCE_V1'),
    ):
      names = CONTEXT | {'actual_delta_tick', 'move_label'} if role == 'train' else V1_DEV
      entries = {key: {**array()[1], 'filename': key + '.npy.gz'} for key in names}
      for key in fields:
        raw, desc = array('<i8' if key == 'prior_delta_tick' else '|b1')
        entries[key] = {**desc, 'filename': key + '.npy.gz'}
        persist(owner, prefix + '/' + role + '/' + key + '.npy.gz', raw)
      body = {'schema': schema, 'anchor_sha256': job['train_anchor' if role == 'train' else 'dev_anchor'], 'arrays': entries}
      if role == 'one-step':
        body.update(candidate_id=candidate, fold=fold, model_lineage=['a' * 64] * 3)
      receipt = seal(body)
      persist(owner, prefix + '/' + role + '/receipt.json', canonical(receipt))
      job['v1_train_receipt' if role == 'train' else 'v1_dev_receipt'] = receipt['receipt_sha256']
    finalized = seal(
      {
        'schema': 'V4_TRAIN_FINALIZED',
        'status': 'TRAIN_COMPLETE',
        'candidate_id': candidate,
        'fold': fold,
        'train_anchor_sha256': job['train_anchor'],
        'authorization_sha256': 'a' * 64,
        'train_manifest_sha256': job['train_manifest'],
        'model_threshold_receipt_sha256': job['train_receipt'],
      }
    )
    job['finalized_receipt'] = finalized['receipt_sha256']
    entries = {k: {**array()[1], 'filename': k + '.npy.gz'} for k in ('p_move', 'predicted_gate', 'integrated_delta', 'projected_next_tick', 'candidate_error')}
    for owner in ('V4_REPEAT_1', 'V4_REPEAT_2'):
      persist(owner, prefix + '/train-finalized.json', canonical(finalized))
      for key in ('p_move', 'predicted_gate'):
        raw, desc = array('|b1' if key == 'predicted_gate' else '<f8')
        entries[key] = {**desc, 'filename': key + '.npy.gz'}
        persist(owner, prefix + '/one-step/' + key + '.npy.gz', raw)
      receipt = seal({'schema': 'V4_DEVELOPMENT', 'train_finalized_sha256': finalized['receipt_sha256'], 'anchor_sha256': job['dev_anchor'], 'arrays': entries})
      persist(owner, prefix + '/one-step/receipt.json', canonical(receipt))
    jobs.append(job)
  manifest_pins = {}
  for owner in roots:
    for candidate, fold in JOBS:
      files[owner][f'candidates/{candidate}/{fold}/receipt.json'] = '9' * 64
    files[owner].update({'results.json': '8' * 64, 'selection.json': '7' * 64})
    if owner == 'V1_REFERENCE':
      for i in range(5250 - len(files[owner])):
        files[owner][f'not-opened/{i}.json'] = '6' * 64
      body = {
        'schema': 'EMPIRICAL_HURDLE_FIT_CV_MANIFEST_V1',
        'status': 'HURDLE_RETROSPECTIVE_FIT_AND_CV_COMPLETE',
        'authorization_sha256': 'b' * 64,
        'results_sha256': '8' * 64,
        'selection_sha256': '7' * 64,
        'job_count': 32,
        'input_bytes_unchanged': True,
        'files': files[owner],
      }
    else:
      body = {
        'schema': 'V4_RUN_MANIFEST',
        'synthetic': False,
        'authorization_sha256': 'a' * 64,
        'result_sha256': '8' * 64,
        'selection_sha256': '7' * 64,
        'source_writes': 0,
        'source_bytes_unchanged': True,
        'files': files[owner],
      }
    manifest = seal(body)
    raw = canonical(manifest)
    (Path(roots[owner]) / 'manifest.json').write_bytes(raw)
    manifest_pins[owner] = {'receipt_sha256': manifest['receipt_sha256'], 'raw_sha256': sha(raw)}
  info = root.stat()
  return {
    'authorized': True,
    'binding_sha256': 'a' * 64,
    'mount_root': str(root),
    'mount_identity': (info.st_dev, info.st_ino),
    'roots': roots,
    'manifests': manifest_pins,
    'jobs': jobs,
    'authorization': {'V4': 'a' * 64, 'V1_REFERENCE': 'b' * 64},
    'order_provenance': b1.ORDER_SOURCES.copy(),
  }


class IntegrationTests(unittest.TestCase):
  def setUp(self):
    self.assertIsNotNone(b1, 'B1 restricted reader not implemented')
    self.tmp = tempfile.TemporaryDirectory()
    self.addCleanup(self.tmp.cleanup)
    self.root = Path(self.tmp.name)
    self.request = fixture(self.root)

  def test_six_field_integrity_and_recorded_alignment_partial_not_full(self):
    result = b1.run(self.request)
    self.assertEqual(result['status'], 'B1_MIXED_CARRIER_ACCESS_BLOCKED')
    self.assertEqual(result['field_status_counts'], {'PASS': 192, 'AUTHORITY_BLOCKED': 32})
    self.assertEqual(result['reads']['array_file_openings'], 256)
    self.assertEqual(result['reads']['metadata_file_openings'], 195)
    self.assertEqual(result['dev_aligned_jobs'], 32)
    self.assertEqual(result['train_three_field_aligned_jobs'], 0)
    self.assertEqual(result['v4_dev_equal_field_pairs'], 64)
    self.assertEqual(result['replica_payload_equality'], 'REPLICA_PAYLOAD_EQUALITY_NOT_FULLY_REVERIFIED')
    self.assertEqual(result['train_rowwise_gate'], 'NOT_SAVED')
    self.assertEqual(result['source_writes'], 0)

  def test_mixed_carrier_and_train_score_never_opened(self):
    sentinel = Path(self.request['roots']['V4_REPEAT_1']) / 'candidates/HRI_D00_L01/FOLD_A/train/receipt.json'
    sentinel.parent.mkdir(parents=True)
    sentinel.write_bytes(b'{"threshold":"PRIVATE_SENTINEL"}')
    before = sentinel.stat()
    with patch.object(os, 'scandir', side_effect=AssertionError('scan forbidden')), patch.object(os, 'listdir', side_effect=AssertionError('scan forbidden')):
      result = b1.run(self.request)
    self.assertEqual(result['field_status_counts']['AUTHORITY_BLOCKED'], 32)
    self.assertEqual(sentinel.stat().st_atime_ns, before.st_atime_ns)
    self.assertNotIn('PRIVATE_SENTINEL', json.dumps(result))

  def test_wrong_candidate_fold_or_role_rejected_before_any_open(self):
    self.request['jobs'][0] = {**self.request['jobs'][0], 'fold': 'FOLD_C'}
    result = b1.run(self.request)
    self.assertEqual(result['status'], 'B1_INPUT_CONFLICT_FAIL_CLOSED')
    self.assertEqual(result['reads']['metadata_file_openings'], 0)

  def test_no_b1_grant_rejected(self):
    result = b1.run({**self.request, 'authorized': False})
    self.assertEqual(result['status'], 'B1_INPUT_CONFLICT_FAIL_CLOSED')
    self.assertEqual(result['reads']['array_file_openings'], 0)

  def test_root_alias_rejected(self):
    self.request['roots']['V4_REPEAT_2'] = self.request['roots']['V4_REPEAT_1']
    result = b1.run(self.request)
    self.assertEqual(result['status'], 'B1_INPUT_CONFLICT_FAIL_CLOSED')
    self.assertEqual(result['reads']['array_file_openings'], 0)

  def test_same_count_different_ordered_anchor_fails(self):
    self.request['jobs'][0]['dev_anchor'] = '5' * 64
    result = b1.run(self.request)
    self.assertEqual(result['status'], 'B1_INPUT_CONFLICT_FAIL_CLOSED')
    self.assertEqual(result['error_code'], 'B1_ROW_ALIGNMENT_CONFLICT')

  def test_anchor_digest_without_frozen_order_contract_never_passes(self):
    result = b1.run({**self.request, 'order_provenance': {}})
    self.assertEqual(result['status'], 'B1_ALIGNMENT_NOT_PROVEN')
    self.assertEqual(result['dev_aligned_jobs'], 0)
    self.assertEqual(result['reads']['array_file_openings'], 0)

  def test_payload_corruption_aborts_no_alternate_or_retry(self):
    path = Path(self.request['roots']['V1_REFERENCE']) / 'candidates/HRI_D00_L01/FOLD_A/train/move_label.npy.gz'
    path.write_bytes(b'corrupted')
    result = b1.run(self.request)
    self.assertEqual(result['status'], 'B1_INPUT_CONFLICT_FAIL_CLOSED')
    self.assertEqual(result['error_code'], 'B1_HASH_CONFLICT')
    self.assertEqual(result['reads']['array_file_openings'], 1)

  def test_missing_exact_payload_no_discovery(self):
    path = Path(self.request['roots']['V1_REFERENCE']) / 'candidates/HRI_D00_L01/FOLD_A/train/move_label.npy.gz'
    path.unlink()
    result = b1.run(self.request)
    self.assertEqual(result['status'], 'B1_PARTIAL_VERIFICATION_INPUT_INSUFFICIENT')
    self.assertIn('MISSING', result['field_status_counts'])
    self.assertEqual(result['reads']['array_file_openings'], 0)

  def test_v4_field_not_pass_when_second_replica_not_fully_checked(self):
    path = Path(self.request['roots']['V4_REPEAT_2']) / 'candidates/HRI_D00_L01/FOLD_A/one-step/p_move.npy.gz'
    path.unlink()
    result = b1.run(self.request)
    gate = result['fields'][4]
    self.assertEqual(gate['field'], 'predicted_gate')
    self.assertEqual(len(gate['replicas']), 1)
    self.assertEqual(gate['status'], 'INPUT_INSUFFICIENT')
    self.assertEqual(result['v4_dev_equal_field_pairs'], 0)

  def test_manifest_hash_conflict_before_payload(self):
    self.request['manifests']['V4_REPEAT_1']['raw_sha256'] = '1' * 64
    result = b1.run(self.request)
    self.assertEqual(result['status'], 'B1_INPUT_CONFLICT_FAIL_CLOSED')
    self.assertEqual(result['reads']['array_file_openings'], 0)

  def test_canonical_manifest_equality_does_not_require_equal_json_whitespace(self):
    path = Path(self.request['roots']['V4_REPEAT_2']) / 'manifest.json'
    row = json.loads(path.read_bytes())
    raw = json.dumps(row, indent=2).encode()
    path.write_bytes(raw)
    self.request['manifests']['V4_REPEAT_2']['raw_sha256'] = sha(raw)
    result = b1.run(self.request)
    self.assertEqual(result['status'], 'B1_MIXED_CARRIER_ACCESS_BLOCKED')
    self.assertEqual(result['v4_dev_equal_field_pairs'], 64)

  def test_resume_verifies_saved_receipt_with_every_recompute_trapped(self):
    result = b1.run(self.request)
    raw = canonical(result)
    with (
      patch.object(b1, 'run', side_effect=AssertionError('recompute')),
      patch.object(b1.GuardedReader, 'read', side_effect=AssertionError('source read')),
      patch.object(b1, 'inspect_array', side_effect=AssertionError('array recompute')),
      patch.object(b1, 'metadata', side_effect=AssertionError('metadata recompute')),
      patch.object(b1, '_population', side_effect=AssertionError('population recompute')),
    ):
      resume = b1.verify_only(result, sha(raw), 'a' * 64)
    self.assertEqual(resume['status'], 'B1_VERIFY_ONLY_PASS')
    self.assertEqual(resume['recompute_calls'], 0)

  def test_public_projection_drops_private_details(self):
    result = b1.run(self.request)
    result['private_path'] = '/private/sentinel'
    public = b1.public_summary(result)
    text = json.dumps(public)
    self.assertNotIn('/private/', text)
    self.assertNotIn('file_sha256', text)
    self.assertFalse(public['C_AUTHORIZED'])
    self.assertFalse(public['E_AUTHORIZED'])

  def test_public_projection_rejects_poisoned_scalar_or_train_promotion(self):
    result = b1.run(self.request)
    for key in ('dev_aligned_jobs', 'train_three_field_aligned_jobs', 'v4_dev_equal_field_pairs', 'source_writes'):
      with self.subTest(key=key), self.assertRaises(ValueError):
        b1.public_summary({**result, key: '/private/projection-sentinel'})
      with self.subTest(key=key), self.assertRaises(ValueError):
        b1.public_summary({**result, key: True})
    result['fields'][0]['status'] = 'PASS'
    with self.assertRaises(ValueError):
      b1.public_summary(result)

  def test_full_verified_state_cannot_be_published_by_partial_reader(self):
    result = b1.run(self.request)
    result['status'] = 'B1_FIELD_INTEGRITY_AND_ALIGNMENT_VERIFIED'
    with self.assertRaises(ValueError):
      b1.public_summary(result)
