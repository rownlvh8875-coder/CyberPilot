"""Synthetic metadata only. No actual evidence roots or model imports."""

import hashlib
import importlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

try:
  b0 = importlib.import_module('openpilot.tools.cyber_autotune.empirical_hurdle_v4_b0_metadata')
except ModuleNotFoundError:
  b0 = None


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
IDS = ('V4_REPEAT_1_RUN_MANIFEST', 'V4_REPEAT_2_RUN_MANIFEST', 'V1_REFERENCE_REPEAT_1_MANIFEST', 'V1_REFERENCE_REPEATABILITY_RECEIPT')


def sealed(body):
  row = {**body, **dict.fromkeys(FLAGS, False)}
  return {**row, 'receipt_sha256': hashlib.sha256(json.dumps(row, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()}


def fixtures():
  members = {'results.json': '1' * 64, 'selection.json': '2' * 64}
  for d in (0, 5, 10, 20):
    for length in (1, 5, 15, 45):
      for fold in ('FOLD_A', 'FOLD_B'):
        members[f'candidates/HRI_D{d:02}_L{length:02}/{fold}/receipt.json'] = '3' * 64
  v4 = sealed(
    {
      'schema': 'V4_RUN_MANIFEST',
      'synthetic': False,
      'authorization_sha256': 'a' * 64,
      'result_sha256': 'b' * 64,
      'selection_sha256': 'c' * 64,
      'source_writes': 0,
      'source_bytes_unchanged': True,
      'files': members,
    }
  )
  v1_members = dict(members)
  v1_members.update({f'candidates/HRI_D00_L01/FOLD_A/synthetic-{i}.json': '4' * 64 for i in range(5250 - len(members))})
  v1 = sealed(
    {
      'schema': 'EMPIRICAL_HURDLE_FIT_CV_MANIFEST_V1',
      'status': 'HURDLE_RETROSPECTIVE_FIT_AND_CV_COMPLETE',
      'authorization_sha256': 'd' * 64,
      'results_sha256': 'e' * 64,
      'selection_sha256': 'f' * 64,
      'job_count': 32,
      'input_bytes_unchanged': True,
      'files': v1_members,
    }
  )
  repeat = sealed(
    {
      'schema': 'EMPIRICAL_HURDLE_FIT_CV_REPEATABILITY_V1',
      'status': 'HURDLE_FIT_CV_EXACT_REPEATABILITY_PASS',
      'manifest_sha256': v1['receipt_sha256'],
      'authorization_sha256': 'd' * 64,
      'independent_replicas': 2,
      'all_file_hashes_equal': True,
      'all_receipts_equal': True,
      'trapped_resume_exact': True,
      'scope': 'ALL_32_JOBS_MODELS_NORMALIZERS_THRESHOLDS_PREDICTIONS_PATHS_GATES_SELECTION',
      'files_per_replica': 5250,
    }
  )
  return [v4, v4, v1, repeat]


class TestB0Metadata(unittest.TestCase):
  def setUp(self):
    self.assertIsNotNone(b0, 'B0 exact-file metadata reader is not implemented')
    self.temp = tempfile.TemporaryDirectory()
    self.addCleanup(self.temp.cleanup)
    self.root = Path(self.temp.name)
    self.bodies = fixtures()
    self.paths = [self.root / f'record-{i}.json' for i in range(4)]
    self.write()

  def write(self):
    for path, body in zip(self.paths, self.bodies, strict=True):
      path.write_text(json.dumps(body, sort_keys=True, separators=(',', ':')))

  def request(self, **changes):
    pins = b0.IdentityPins(self.bodies[0]['receipt_sha256'], self.bodies[2]['receipt_sha256'], self.bodies[3]['receipt_sha256'], 'a' * 64, 'd' * 64)
    specs = tuple(
      b0.MetadataSpec(record_id, str(path), body['receipt_sha256'], b0.BYTE_CAPS[record_id])
      for record_id, path, body in zip(IDS, self.paths, self.bodies, strict=True)
    )
    args = {'specs': specs, 'approved_paths': tuple(map(str, self.paths)), 'mount_root': str(self.root), 'pins': pins, 'authorized': True}
    return {**args, **changes}

  def run_read(self, **changes):
    return b0.read_four(**self.request(**changes))

  def reseal(self, index, **changes):
    self.bodies[index] = sealed({k: v for k, v in self.bodies[index].items() if k != 'receipt_sha256'} | changes)
    if index == 0:
      self.bodies[1] = self.bodies[0]
    self.write()

  def test_four_metadata_receipts_verified_without_payload_claim(self):
    result = self.run_read()
    self.assertEqual(result['status'], 'B0_VERIFIED_METADATA_ONLY')
    self.assertEqual([r['status'] for r in result['records']], ['PASS'] * 4)
    self.assertEqual(result['metadata_file_openings'], 4)
    self.assertTrue(result['run_manifest_identities_equal'])
    self.assertEqual(result['replica_payload_equality'], 'REPLICA_PAYLOAD_EQUALITY_NOT_REVERIFIED')
    self.assertEqual(result['train_rowwise_gate'], 'NOT_SAVED')
    self.assertFalse(result['B1_GRANTED'])

  def test_missing_trusted_raw_hash_is_explicitly_insufficient(self):
    result = self.run_read()
    self.assertEqual(result['records'][0]['raw_hash_comparison'], 'INPUT_INSUFFICIENT_NO_TRUSTED_EXPECTED_RAW_HASH')
    self.assertEqual(result['records'][0]['receipt_identity'], 'PASS')
    self.assertEqual(result['records'][0]['observed_raw_sha256'], hashlib.sha256(self.paths[0].read_bytes()).hexdigest())

  def test_changed_bound_mount_is_rejected_before_any_target_open(self):
    result = self.run_read(expected_mount_identity=(-1, -1))
    self.assertEqual(result['status'], 'B0_INPUT_CONFLICT_FAIL_CLOSED')
    self.assertEqual(result['error_code'], 'B0_MOUNT_IDENTITY_CONFLICT')
    self.assertEqual(result['metadata_file_openings'], 0)

  def test_bound_mount_identity_matches_held_directory(self):
    value = self.root.stat()
    result = self.run_read(expected_mount_identity=(value.st_dev, value.st_ino))
    self.assertEqual(result['status'], 'B0_VERIFIED_METADATA_ONLY')

  def test_different_names_resolving_to_same_file_are_rejected(self):
    original = b0._open_relative

    def alias(directory_fd, relative):
      return original(directory_fd, 'record-0.json' if relative == 'record-1.json' else relative)

    with patch.object(b0, '_open_relative', side_effect=alias):
      result = self.run_read()
    self.assertEqual(result['status'], 'B0_INPUT_CONFLICT_FAIL_CLOSED')
    self.assertEqual(result['error_code'], 'B0_DUPLICATE_FILE_IDENTITY')
    self.assertEqual(result['metadata_file_openings'], 2)
    self.assertEqual(result['records'][1]['bytes_read'], 0)

  def test_member_payload_is_never_opened_or_statted(self):
    trap = self.root / 'results.json'
    trap.write_bytes(b'not metadata and must not be read')
    before = trap.stat()
    with (
      patch.object(os, 'scandir', side_effect=AssertionError('enumeration forbidden')),
      patch.object(os, 'listdir', side_effect=AssertionError('enumeration forbidden')),
      patch.object(Path, 'read_bytes', side_effect=AssertionError('unbounded read forbidden')),
    ):
      result = self.run_read()
    self.assertEqual(result['status'], 'B0_VERIFIED_METADATA_ONLY')
    self.assertEqual(trap.stat().st_mtime_ns, before.st_mtime_ns)
    self.assertFalse(any(r.get('member_content_verified', False) for r in result['records']))

  def test_actual_open_audit_contains_only_four_named_file_reads(self):
    opened = []
    original = b0._open_relative

    def record(fd, relative):
      opened.append(relative)
      return original(fd, relative)

    with patch.object(b0, '_open_relative', side_effect=record):
      result = self.run_read()
    self.assertEqual(result['status'], 'B0_VERIFIED_METADATA_ONLY')
    self.assertEqual(opened, [f'record-{i}.json' for i in range(4)])

  def test_source_bytes_remain_unchanged_and_repeat_is_idempotent(self):
    before = [p.read_bytes() for p in self.paths]
    first, second = self.run_read(), self.run_read()
    self.assertEqual(first, second)
    self.assertEqual([p.read_bytes() for p in self.paths], before)
    self.assertEqual(first['source_writes'], 0)

  def test_unknown_or_fifth_record_rejected_before_any_open(self):
    args = self.request()
    result = b0.read_four(**(args | {'specs': args['specs'] + (args['specs'][0],)}))
    self.assertEqual(result['metadata_file_openings'], 0)
    self.assertEqual(result['error_code'], 'B0_EXACT_FOUR_REQUIRED')

  def test_b0_permission_is_not_implied_by_valid_identity(self):
    result = self.run_read(authorized=False)
    self.assertEqual(result['metadata_file_openings'], 0)
    self.assertEqual(result['error_code'], 'B0_EXPLICIT_AUTHORIZATION_REQUIRED')

  def test_reordered_records_rejected_before_open(self):
    args = self.request()
    result = self.run_read(specs=tuple(reversed(args['specs'])))
    self.assertEqual(result['metadata_file_openings'], 0)
    self.assertEqual(result['error_code'], 'B0_EXACT_FOUR_REQUIRED')

  def test_target_substitution_not_authorized_by_matching_hash(self):
    replacement = self.root / 'unapproved.json'
    replacement.write_bytes(self.paths[0].read_bytes())
    args = self.request()
    changed = b0.MetadataSpec(IDS[0], str(replacement), self.bodies[0]['receipt_sha256'], b0.BYTE_CAPS[IDS[0]])
    result = self.run_read(specs=(changed, *args['specs'][1:]))
    self.assertEqual(result['metadata_file_openings'], 0)
    self.assertEqual(result['error_code'], 'B0_ALLOWLIST_CONFLICT')

  def test_duplicated_target_paths_rejected(self):
    result = self.run_read(approved_paths=(str(self.paths[0]),) * 4)
    self.assertEqual(result['metadata_file_openings'], 0)

  def test_traversal_or_wildcards_are_not_normalized_away(self):
    for value in (str(self.root) + '/x/../record-0.json', str(self.root) + '//record-0.json', str(self.root) + '/*.json'):
      with self.subTest(value=value):
        args = self.request()
        spec = b0.MetadataSpec(IDS[0], value, self.bodies[0]['receipt_sha256'], b0.BYTE_CAPS[IDS[0]])
        result = self.run_read(specs=(spec, *args['specs'][1:]), approved_paths=(value, *args['approved_paths'][1:]))
        self.assertEqual(result['metadata_file_openings'], 0)
        self.assertEqual(result['error_code'], 'B0_PATH_GRAMMAR_CONFLICT')

  def test_symlink_file_rejected_without_reading_payload(self):
    target = self.root / 'elsewhere.json'
    self.paths[0].rename(target)
    self.paths[0].symlink_to(target)
    result = self.run_read()
    self.assertEqual(result['metadata_file_openings'], 0)
    self.assertEqual(result['error_code'], 'B0_PATH_GUARD_REJECTED')

  def test_symlink_parent_rejected(self):
    parent = self.root / 'alias'
    parent.symlink_to(self.root, target_is_directory=True)
    paths = tuple(str(parent / p.name) for p in self.paths)
    args = self.request()
    specs = tuple(b0.MetadataSpec(s.record_id, p, s.expected_receipt_sha256, s.max_bytes) for s, p in zip(args['specs'], paths, strict=True))
    result = self.run_read(specs=specs, approved_paths=paths)
    self.assertEqual(result['metadata_file_openings'], 0)
    self.assertEqual(result['error_code'], 'B0_PATH_GUARD_REJECTED')

  def test_symlink_mount_root_is_rejected(self):
    alias = self.root / 'alias'
    alias.symlink_to(self.root, target_is_directory=True)
    args = self.request()
    paths = tuple(str(alias / p.name) for p in self.paths)
    specs = tuple(b0.MetadataSpec(s.record_id, p, s.expected_receipt_sha256, s.max_bytes) for s, p in zip(args['specs'], paths, strict=True))
    result = self.run_read(specs=specs, approved_paths=paths, mount_root=str(alias))
    self.assertEqual(result['metadata_file_openings'], 0)
    self.assertEqual(result['error_code'], 'B0_PATH_GUARD_REJECTED')

  def test_kernel_mount_boundary_rejected(self):
    fd = os.open('/', os.O_PATH | os.O_DIRECTORY)
    self.addCleanup(os.close, fd)
    with self.assertRaisesRegex(b0.B0Error, '^B0_PATH_GUARD_REJECTED$'):
      b0._open_relative(fd, 'proc/self/status')

  def test_hardlinked_metadata_rejected_before_bytes(self):
    os.link(self.paths[0], self.root / 'second-name.json')
    result = self.run_read()
    self.assertEqual(result['metadata_file_openings'], 1)
    self.assertEqual(result['records'][0]['bytes_read'], 0)
    self.assertEqual(result['error_code'], 'B0_REGULAR_SINGLE_LINK_REQUIRED')

  def test_directory_and_fifo_are_not_read(self):
    self.paths[0].unlink()
    self.paths[0].mkdir()
    result = self.run_read()
    self.assertEqual(result['error_code'], 'B0_REGULAR_SINGLE_LINK_REQUIRED')
    self.paths[0].rmdir()
    os.mkfifo(self.paths[0])
    result = self.run_read()
    self.assertEqual(result['error_code'], 'B0_REGULAR_SINGLE_LINK_REQUIRED')

  def test_oversize_rejected_after_one_open_before_payload(self):
    with self.paths[0].open('r+b') as stream:
      stream.truncate(b0.BYTE_CAPS[IDS[0]] + 1)
    result = self.run_read()
    self.assertEqual(result['metadata_file_openings'], 1)
    self.assertEqual(result['records'][0]['bytes_read'], 0)
    self.assertEqual(result['error_code'], 'B0_SIZE_LIMIT')

  def test_cap_cannot_be_increased_or_tuned_by_request(self):
    args = self.request()
    s = args['specs'][0]
    changed = b0.MetadataSpec(s.record_id, s.path, s.expected_receipt_sha256, s.max_bytes + 1)
    result = self.run_read(specs=(changed, *args['specs'][1:]))
    self.assertEqual(result['metadata_file_openings'], 0)
    self.assertEqual(result['error_code'], 'B0_FROZEN_SIZE_BOUND_REQUIRED')

  def test_missing_named_file_stops_without_searching(self):
    self.paths[0].unlink()
    with patch.object(os, 'scandir', side_effect=AssertionError('no search')):
      result = self.run_read()
    self.assertEqual(result['records'][0]['status'], 'INPUT_INSUFFICIENT')
    self.assertEqual(result['status'], 'B0_BLOCKED_TRUSTED_REFERENCE_INCOMPLETE')
    self.assertEqual(result['metadata_file_openings'], 0)

  def test_external_change_during_read_is_detected_without_retry(self):
    original = os.read
    changed = False

    def read_then_change(fd, count):
      nonlocal changed
      data = original(fd, count)
      if not changed:
        changed = True
        with self.paths[0].open('ab') as stream:
          stream.write(b' ')
      return data

    with patch.object(os, 'read', side_effect=read_then_change):
      result = self.run_read()
    self.assertEqual(result['error_code'], 'B0_METADATA_CHANGED_DURING_READ')
    self.assertEqual(result['metadata_file_openings'], 1)
    self.assertEqual(result['records'][1]['file_openings'], 0)

  def test_wrong_raw_hash_does_not_masquerade_as_receipt_match(self):
    args = self.request()
    s = args['specs'][0]
    changed = b0.MetadataSpec(s.record_id, s.path, s.expected_receipt_sha256, s.max_bytes, '0' * 64)
    result = self.run_read(specs=(changed, *args['specs'][1:]))
    self.assertEqual(result['error_code'], 'B0_RAW_HASH_MISMATCH')
    self.assertEqual(result['metadata_file_openings'], 1)

  def test_trusted_raw_hash_compares_exact_file_bytes(self):
    args = self.request()
    specs = tuple(
      b0.MetadataSpec(s.record_id, s.path, s.expected_receipt_sha256, s.max_bytes, hashlib.sha256(Path(s.path).read_bytes()).hexdigest()) for s in args['specs']
    )
    result = self.run_read(specs=specs)
    self.assertEqual(result['status'], 'B0_VERIFIED_METADATA_ONLY')
    self.assertEqual([r['raw_hash_comparison'] for r in result['records']], ['PASS'] * 4)

  def test_altered_metadata_rejected_by_canonical_identity(self):
    body = dict(self.bodies[0], source_writes=1)
    self.paths[0].write_text(json.dumps(body))
    result = self.run_read()
    self.assertEqual(result['error_code'], 'B0_RECEIPT_MISMATCH')

  def test_pretty_printed_metadata_preserves_canonical_receipt(self):
    self.paths[0].write_text(json.dumps(self.bodies[0], indent=4) + '\n')
    self.assertEqual(self.run_read()['status'], 'B0_VERIFIED_METADATA_ONLY')

  def test_duplicate_json_keys_are_rejected(self):
    raw = self.paths[0].read_text()
    self.paths[0].write_text('{"schema":"bad",' + raw[1:])
    self.assertEqual(self.run_read()['error_code'], 'B0_JSON_INVALID')

  def test_nonfinite_or_nonobject_json_is_rejected(self):
    for payload in ('NaN', '[]', '{} garbage'):
      with self.subTest(payload=payload):
        self.paths[0].write_text(payload)
        result = self.run_read()
        self.assertEqual(result['status'], 'B0_INPUT_CONFLICT_FAIL_CLOSED')
        self.assertNotIn(str(self.paths[0]), json.dumps(result))

  def test_unexpected_schema_rejected_even_with_self_consistent_seal(self):
    self.reseal(0, schema='V4_MODEL_THRESHOLD')
    self.assertEqual(self.run_read()['error_code'], 'B0_SCHEMA_CONFLICT')

  def test_extra_threshold_or_array_field_rejected(self):
    for field, value in (('threshold', 0.25), ('coefficients', [1, 2]), ('probabilities', [0.1])):
      with self.subTest(field=field):
        self.bodies = fixtures()
        self.reseal(0, **{field: value})
        self.assertEqual(self.run_read()['error_code'], 'B0_FIELD_SCOPE_CONFLICT')

  def test_authority_escalation_rejected(self):
    self.bodies[0] = sealed({k: v for k, v in self.bodies[0].items() if k != 'receipt_sha256'})
    self.bodies[0]['vehicle_activation_allowed'] = True
    body = {k: v for k, v in self.bodies[0].items() if k != 'receipt_sha256'}
    self.bodies[0]['receipt_sha256'] = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    self.bodies[1] = self.bodies[0]
    self.write()
    self.assertEqual(self.run_read()['error_code'], 'B0_AUTHORITY_CONFLICT')

  def test_public_authorization_link_is_checked(self):
    self.reseal(0, authorization_sha256='9' * 64)
    self.assertEqual(self.run_read()['error_code'], 'B0_IDENTITY_LINK_CONFLICT')

  def test_unsafe_declared_member_name_does_not_get_dereferenced(self):
    members = dict(self.bodies[0]['files'])
    members['../../unapproved.npy'] = '0' * 64
    self.reseal(0, files=members)
    self.assertEqual(self.run_read()['error_code'], 'B0_MEMBER_MAP_CONFLICT')

  def test_bad_member_digest_is_rejected(self):
    self.reseal(0, files=dict(self.bodies[0]['files'], **{'results.json': 'not-a-digest'}))
    self.assertEqual(self.run_read()['error_code'], 'B0_MEMBER_MAP_CONFLICT')

  def test_missing_frozen_job_declaration_is_rejected(self):
    members = dict(self.bodies[0]['files'])
    del members['candidates/HRI_D00_L01/FOLD_A/receipt.json']
    self.reseal(0, files=members)
    self.assertEqual(self.run_read()['error_code'], 'B0_JOB_DECLARATION_CONFLICT')

  def test_repeatability_receipt_cannot_claim_a_different_manifest(self):
    self.reseal(3, manifest_sha256='0' * 64)
    self.assertEqual(self.run_read()['error_code'], 'B0_IDENTITY_LINK_CONFLICT')
    self.assertEqual(self.run_read()['metadata_file_openings'], 4)

  def test_repeatability_member_count_checked_against_manifest(self):
    self.reseal(3, files_per_replica=1)
    self.assertEqual(self.run_read()['error_code'], 'B0_DECLARED_COUNT_CONFLICT')

  def test_public_projection_rejects_accidental_private_extension(self):
    result = self.run_read()
    result['injected_private_path'] = str(self.paths[0])
    result['threshold'] = 0.25
    public = b0.public_summary(result)
    text = json.dumps(public)
    self.assertNotIn(str(self.root), text)
    self.assertNotIn('threshold', text)
    self.assertNotIn('observed_raw_sha256', text)
    self.assertNotIn('declared_member_map_sha256', text)
    self.assertEqual(public['status'], 'B0_VERIFIED_METADATA_ONLY')

  def test_public_projection_rejects_private_text_in_an_allowed_slot(self):
    result = self.run_read()
    result['records'][0]['record_id'] = str(self.paths[0])
    with self.assertRaisesRegex(b0.B0Error, '^B0_PUBLIC_PROJECTION_CONFLICT$'):
      b0.public_summary(result)


if __name__ == '__main__':
  unittest.main()
