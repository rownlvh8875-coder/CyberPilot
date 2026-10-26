"""Restricted saved-byte integrity and recorded ordering; no scientific evaluation.

The reviewed private caller authenticates its human B1 grant, B0 receipts, host,
volume, public catalog, output and this source before calling. No process-wide
sandbox is claimed. Only public_summary is suitable for publication.
"""

import ast
from collections import Counter
import hashlib
import os
from pathlib import PurePosixPath
import stat
import struct
import zlib

from openpilot.tools.cyber_autotune import empirical_hurdle_v4_b0_metadata as b0

JOBS = tuple((f'HRI_D{d:02}_L{length:02}', fold) for d in (0, 5, 10, 20) for length in (1, 5, 15, 45) for fold in ('FOLD_A', 'FOLD_B'))
OWNERS = ('V4_REPEAT_1', 'V4_REPEAT_2', 'V1_REFERENCE')
FIELDS = (
  ('TRAIN', 'V4', 'combined_probability'),
  ('TRAIN', 'V1_REFERENCE', 'move_label'),
  ('TRAIN', 'V1_REFERENCE', 'prior_delta_tick'),
  ('DEV', 'V4', 'p_move'),
  ('DEV', 'V4', 'predicted_gate'),
  ('DEV', 'V1_REFERENCE', 'true_move'),
  ('DEV', 'V1_REFERENCE', 'prior_delta_tick'),
)
ORDER_SOURCES = {
  'empirical_hurdle_fit_cv_execution.py': 'a952eb4986f47e0335bf355ee74868755f14b592d05070008a0b117979d4e635',
  'empirical_hurdle_fit_cv_data.py': '9e104a83a928c6b997a914a606820f2d2190fa56917e4042856474f747b900ac',
  'empirical_s2_ri_reconstruction_math.py': 'e6bb2f276b3e87104f1aedb0ecbafae7175147c60e9b03aaba19b77a49db0055',
  'empirical_hurdle_v4_execution.py': 'f7ae1ae98c645de4997e56d1bcd73b76e2f4f153090b65e5fd6bb8d207f7fd0e',
  'empirical_s2_ri_schema.py': '6f8fd733b6634738db6c01b3bc3bc0a4330733cb6363326b4c3994318065e31a',
}
MAX_COUNT = 336941  # Maximum sealed public TRAIN/DEV N; caller pins each exact public N.
HEADER_BYTES = 65536  # Conservative fixed header allowance; no live header/size-derived budget.
METADATA_BYTES = 65536  # <=32 fixed nine-field descriptors plus fixed scalar schema, SHA256 strings, ten flags.
WIDTHS = {'|b1': 1, '<f8': 8, '<i8': 8}
CONTEXT = frozenset(
  (
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
  )
)
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
V4_DEV = frozenset(('p_move', 'predicted_gate', 'integrated_delta', 'projected_next_tick', 'candidate_error'))
DESCRIPTOR_KEYS = frozenset(
  ('dtype', 'shape', 'order', 'array_sha256', 'file_sha256', 'npy_sha256', 'filename', 'storage_format', 'lossless_roundtrip_verified')
)


class B1Error(ValueError):
  def __init__(self, code):
    self.code = code
    super().__init__(code)


def need(condition, code='B1_SCHEMA_CONFLICT'):
  if not condition:
    raise B1Error(code)


def sha(raw):
  return hashlib.sha256(raw).hexdigest()


def sealed(body):
  body = {**body, **dict.fromkeys(b0.AUTHORITY_KEYS, False)}
  return {**body, 'receipt_sha256': sha(b0._canonical(body))}


def byte_caps(count, dtype):
  need(type(count) is int and 0 < count <= MAX_COUNT and dtype in WIDTHS)
  decoded = count * WIDTHS[dtype] + HEADER_BYTES
  # Existing V1 compressed-store reservation: raw + raw//100 +65536.
  return decoded + decoded // 100 + HEADER_BYTES, decoded


def descriptor(row, *, count, dtype, field):
  need(type(row) is dict and set(row) == DESCRIPTOR_KEYS)
  need(row['dtype'] == dtype and row['shape'] == [count] and all(type(x) is int for x in row['shape']) and row['order'] == 'C')
  need(row['storage_format'] == 'NPY_GZIP_V1' and row['lossless_roundtrip_verified'] is True)
  need(row['filename'] == field + '.npy.gz')
  need(all(b0._digest(row[k]) for k in ('array_sha256', 'npy_sha256', 'file_sha256')))


def inspect_array(raw, desc, *, count, dtype):
  """Hash byte sequences and parse one bounded header; never create numeric arrays."""
  compressed_cap, decoded_cap = byte_caps(count, dtype)
  need(0 < len(raw) <= compressed_cap)
  descriptor(desc, count=count, dtype=dtype, field=desc.get('filename', '').removesuffix('.npy.gz'))
  need(sha(raw) == desc['file_sha256'], 'B1_HASH_CONFLICT')
  try:
    decoder = zlib.decompressobj(wbits=31)
    npy = decoder.decompress(raw, decoded_cap + 1)
    need(len(npy) <= decoded_cap and decoder.eof and not decoder.unused_data and not decoder.unconsumed_tail)
  except zlib.error:
    raise B1Error('B1_SCHEMA_CONFLICT') from None
  need(npy[:6] == b'\x93NUMPY' and npy[6:8] in (b'\x01\x00', b'\x02\x00'))
  prefix = 10 if npy[6] == 1 else 12
  need(len(npy) >= prefix)
  length = struct.unpack('<H' if prefix == 10 else '<I', npy[8:prefix])[0]
  need(0 < length <= HEADER_BYTES - prefix and prefix + length <= len(npy))
  text = npy[prefix : prefix + length]
  need(text.endswith(b'\n'))
  try:
    parsed = ast.parse(text.decode('ascii').strip(), mode='eval').body
    need(isinstance(parsed, ast.Dict) and len(parsed.keys) == 3)
    keys = [ast.literal_eval(k) for k in parsed.keys]
    need(set(keys) == {'descr', 'fortran_order', 'shape'})
    header = ast.literal_eval(parsed)
  except (ValueError, SyntaxError, UnicodeError, TypeError, RecursionError):
    raise B1Error('B1_SCHEMA_CONFLICT') from None
  need(header['descr'] == dtype and header['fortran_order'] is False and type(header['shape']) is tuple)
  need(header['shape'] == (count,) and all(type(x) is int for x in header['shape']))
  payload = npy[prefix + length :]
  need(len(payload) == count * WIDTHS[dtype])
  need(sha(npy) == desc['npy_sha256'] and sha(payload) == desc['array_sha256'], 'B1_HASH_CONFLICT')
  return {
    'dtype': dtype,
    'shape': [count],
    'order': 'C',
    'file_sha256': sha(raw),
    'npy_sha256': sha(npy),
    'array_sha256': sha(payload),
    'raw_bytes': len(raw),
    'decoded_bytes': len(npy),
    'file_openings': 1,
    'hash_schema_shape_dtype': 'PASS',
  }


class GuardedReader:
  """Exact paths and fixed caps only. Every successful open/byte is counted on failure."""

  def __init__(self, mount_root, mount_identity, allowlist):
    self.counters = dict.fromkeys(('array_file_openings', 'metadata_file_openings', 'array_bytes_read', 'metadata_bytes_read'), 0)
    self.allowlist, self.paths, self.inodes, self.events = dict(allowlist), set(), set(), []
    self.root = b0._path(mount_root, absolute=True)
    need(type(mount_identity) is tuple and len(mount_identity) == 2)
    for path, (cap, kind) in self.allowlist.items():
      item = b0._path(path, absolute=True)
      need(item != self.root and item.is_relative_to(self.root) and type(cap) is int and cap > 0 and kind in ('array', 'metadata'))
    self.fd = b0._mount_fd(mount_root)
    info = os.fstat(self.fd)
    if (info.st_dev, info.st_ino) != mount_identity:
      os.close(self.fd)
      raise B1Error('B1_MOUNT_CONFLICT')

  def __enter__(self):
    return self

  def __exit__(self, *_args):
    os.close(self.fd)

  def read(self, path, cap, kind):
    need(self.allowlist.get(path) == (cap, kind) and path not in self.paths, 'B1_ALLOWLIST_CONFLICT')
    self.paths.add(path)
    relative = str(PurePosixPath(path).relative_to(self.root))
    event = {'member': relative, 'kind': kind, 'file_openings': 0, 'bytes_read': 0}
    self.events.append(event)
    try:
      fd = b0._open_relative(self.fd, relative)
    except b0.B0Error as error:
      raise B1Error('B1_MISSING' if error.code == 'B0_MISSING_EXACT_TARGET' else 'B1_PATH_GUARD_CONFLICT') from None
    self.counters[kind + '_file_openings'] += 1
    event['file_openings'] = 1
    try:
      before = os.fstat(fd)
      need(stat.S_ISREG(before.st_mode) and before.st_nlink == 1)
      inode = before.st_dev, before.st_ino
      need(inode not in self.inodes, 'B1_ALIAS_CONFLICT')
      self.inodes.add(inode)
      need(0 < before.st_size <= cap)
      chunks, left = [], before.st_size
      while left:
        part = os.read(fd, min(65536, left))
        need(bool(part), 'B1_FILE_CHANGED')
        chunks.append(part)
        left -= len(part)
        event['bytes_read'] += len(part)
        self.counters[kind + '_bytes_read'] += len(part)
      need(b0._stamp(before) == b0._stamp(os.fstat(fd)), 'B1_FILE_CHANGED')
      return b''.join(chunks)
    finally:
      os.close(fd)


def metadata(raw, raw_sha, receipt=None):
  need(sha(raw) == raw_sha, 'B1_HASH_CONFLICT')
  row = b0._decode(raw)
  actual = row.get('receipt_sha256')
  need(b0._digest(actual) and actual == sha(b0._canonical({k: v for k, v in row.items() if k != 'receipt_sha256'})), 'B1_RECEIPT_CONFLICT')
  need(receipt is None or actual == receipt, 'B1_RECEIPT_CONFLICT')
  need(all(row.get(k) is False for k in b0.AUTHORITY_KEYS), 'B1_AUTHORITY_CONFLICT')
  return row


def _fields(row, schema, fields):
  need(row.get('schema') == schema and set(row) == set(fields) | b0.AUTHORITY_KEYS | {'schema', 'receipt_sha256'})


def catalog(request):
  need(request.get('authorized') is True, 'B1_AUTHORITY_CONFLICT')
  need(b0._digest(request.get('binding_sha256')), 'B1_AUTHORITY_CONFLICT')
  need(tuple((j['candidate_id'], j['fold']) for j in request['jobs']) == JOBS, 'B1_JOB_SCOPE_CONFLICT')
  need(set(request['roots']) == set(OWNERS) and set(request['manifests']) == set(OWNERS))
  roots = [b0._path(request['roots'][owner], absolute=True) for owner in OWNERS]
  need(all(not a.is_relative_to(b) for i, a in enumerate(roots) for j, b in enumerate(roots) if i != j), 'B1_ROOT_ALIAS_CONFLICT')
  need(request['order_provenance'] == ORDER_SOURCES, 'B1_ROW_ALIGNMENT_NOT_PROVEN')
  for job in request['jobs']:
    for key in ('train_count', 'dev_count'):
      byte_caps(job[key], '<i8')
    need(
      all(
        b0._digest(job[key])
        for key in ('train_anchor', 'dev_anchor', 'train_manifest', 'train_receipt', 'v1_train_receipt', 'v1_dev_receipt', 'finalized_receipt')
      )
    )
  need(all(b0._digest(v) for v in request['authorization'].values()))
  need(set(request['authorization']) == {'V4', 'V1_REFERENCE'})
  for owner in OWNERS:
    need(set(request['manifests'][owner]) == {'receipt_sha256', 'raw_sha256'} and all(b0._digest(v) for v in request['manifests'][owner].values()))
  need(request['manifests'][OWNERS[0]]['receipt_sha256'] == request['manifests'][OWNERS[1]]['receipt_sha256'], 'B1_REPLICA_MANIFEST_CONFLICT')


def paths(request):
  allow = {}
  for owner in OWNERS:
    root = request['roots'][owner]
    allow[root + '/manifest.json'] = (b0.BYTE_CAPS[b0.RECORD_IDS[2 if owner == 'V1_REFERENCE' else 0]], 'metadata')
    for job in request['jobs']:
      base = root + '/candidates/' + job['candidate_id'] + '/' + job['fold']
      roles = ('train', 'one-step') if owner == 'V1_REFERENCE' else ('one-step',)
      if owner != 'V1_REFERENCE':
        allow[base + '/train-finalized.json'] = (METADATA_BYTES, 'metadata')
      for role in roles:
        allow[base + '/' + role + '/receipt.json'] = (METADATA_BYTES, 'metadata')
        keys = (
          ('move_label', 'prior_delta_tick')
          if role == 'train'
          else (('true_move', 'prior_delta_tick') if owner == 'V1_REFERENCE' else ('p_move', 'predicted_gate'))
        )
        for key in keys:
          dtype = '<i8' if key == 'prior_delta_tick' else ('<f8' if key == 'p_move' else '|b1')
          cap, _ = byte_caps(job['train_count' if role == 'train' else 'dev_count'], dtype)
          allow[base + '/' + role + '/' + key + '.npy.gz'] = (cap, 'array')
  need(len(allow) == 451, 'B1_ALLOWLIST_CONFLICT')
  return allow


def _population(reader, root, manifest, job, owner, role):
  prefix = 'candidates/' + job['candidate_id'] + '/' + job['fold']

  def read(name, receipt=None):
    member = prefix + '/' + name
    need(member in manifest['files'], 'B1_MANIFEST_MEMBER_MISSING')
    return metadata(reader.read(root + '/' + member, METADATA_BYTES, 'metadata'), manifest['files'][member], receipt)

  if owner != 'V1_REFERENCE':
    parent = read('train-finalized.json', job['finalized_receipt'])
    _fields(
      parent,
      'V4_TRAIN_FINALIZED',
      ('status', 'candidate_id', 'fold', 'train_anchor_sha256', 'authorization_sha256', 'train_manifest_sha256', 'model_threshold_receipt_sha256'),
    )
    need(parent['status'] == 'TRAIN_COMPLETE' and parent['candidate_id'] == job['candidate_id'] and parent['fold'] == job['fold'])
    need(parent['train_anchor_sha256'] == job['train_anchor'], 'B1_ROW_ALIGNMENT_CONFLICT')
    need(
      parent['authorization_sha256'] == manifest['authorization_sha256']
      and parent['train_manifest_sha256'] == job['train_manifest']
      and parent['model_threshold_receipt_sha256'] == job['train_receipt'],
      'B1_RECEIPT_CONFLICT',
    )
    row = read('one-step/receipt.json')
    _fields(row, 'V4_DEVELOPMENT', ('train_finalized_sha256', 'anchor_sha256', 'arrays'))
    need(row['train_finalized_sha256'] == parent['receipt_sha256'], 'B1_RECEIPT_CONFLICT')
    names = V4_DEV
  else:
    row = read(role + '/receipt.json', job['v1_train_receipt' if role == 'train' else 'v1_dev_receipt'])
    if role == 'train':
      _fields(row, 'EMPIRICAL_HURDLE_TRAIN_POPULATION_V1', ('anchor_sha256', 'arrays'))
      names = CONTEXT | {'actual_delta_tick', 'move_label'}
    else:
      _fields(row, 'EMPIRICAL_HURDLE_ONE_STEP_EVIDENCE_V1', ('candidate_id', 'fold', 'anchor_sha256', 'model_lineage', 'arrays'))
      need(row['candidate_id'] == job['candidate_id'] and row['fold'] == job['fold'])
      need(type(row['model_lineage']) is list and len(row['model_lineage']) == 3 and all(b0._digest(v) for v in row['model_lineage']))
      names = V1_DEV
  need(type(row['arrays']) is dict and set(row['arrays']) == names)
  need(row['anchor_sha256'] == job['train_anchor' if role == 'train' else 'dev_anchor'], 'B1_ROW_ALIGNMENT_CONFLICT')
  return row, prefix + '/' + role


def _rows():
  return [
    {
      'candidate_id': candidate,
      'fold': fold,
      'role': role,
      'owner': owner,
      'field': field,
      'status': 'AUTHORITY_BLOCKED' if field == 'combined_probability' else 'INPUT_INSUFFICIENT',
      'reason': 'B1_MIXED_CARRIER_ACCESS_NOT_AUTHORIZED' if field == 'combined_probability' else 'NOT_ATTEMPTED',
      'replicas': [],
    }
    for candidate, fold in JOBS
    for role, owner, field in FIELDS
  ]


def run(request):
  """One read per exact approved target, stop on first integrity conflict; no fallback."""
  report = {
    'schema': 'CYBERPILOT_V4_B1_SAVED_INTEGRITY_V1',
    'status': 'B1_PARTIAL_VERIFICATION_INPUT_INSUFFICIENT',
    'binding_sha256': request.get('binding_sha256'),
    'fields': _rows(),
    'reads': dict.fromkeys(('array_file_openings', 'metadata_file_openings', 'array_bytes_read', 'metadata_bytes_read'), 0),
    'source_writes': 0,
    'dev_aligned_jobs': 0,
    'train_three_field_aligned_jobs': 0,
    'v4_dev_equal_field_pairs': 0,
    'replica_payload_equality': 'REPLICA_PAYLOAD_EQUALITY_NOT_FULLY_REVERIFIED',
    'train_rowwise_gate': 'NOT_SAVED',
    'C_AUTHORIZED': False,
    'D_AUTHORIZED': False,
    'E_AUTHORIZED': False,
    'F_AUTHORIZED': False,
    'holdout': 'CLOSED',
    'vehicle_authority': 'NONE',
  }
  reader, active = None, []
  try:
    catalog(request)
    with GuardedReader(request['mount_root'], request['mount_identity'], paths(request)) as reader:
      manifests = {}
      pins = b0.IdentityPins(
        request['manifests'][OWNERS[0]]['receipt_sha256'],
        request['manifests']['V1_REFERENCE']['receipt_sha256'],
        '0' * 64,
        request['authorization']['V4'],
        request['authorization']['V1_REFERENCE'],
      )
      for owner in OWNERS:
        index = 2 if owner == 'V1_REFERENCE' else 0
        raw = reader.read(request['roots'][owner] + '/manifest.json', b0.BYTE_CAPS[b0.RECORD_IDS[index]], 'metadata')
        row = metadata(raw, request['manifests'][owner]['raw_sha256'], request['manifests'][owner]['receipt_sha256'])
        b0._validate(row, index, request['manifests'][owner]['receipt_sha256'], pins)
        manifests[owner] = row
      for job_index, job in enumerate(request['jobs']):
        rows = report['fields'][job_index * 7 : (job_index + 1) * 7]
        for owner, role, indices in (
          ('V1_REFERENCE', 'train', (1, 2)),
          ('V1_REFERENCE', 'one-step', (5, 6)),
          ('V4_REPEAT_1', 'one-step', (3, 4)),
          ('V4_REPEAT_2', 'one-step', (3, 4)),
        ):
          active = [rows[i] for i in indices]
          root, manifest = request['roots'][owner], manifests[owner]
          population, prefix = _population(reader, root, manifest, job, owner, role)
          for index in indices:
            row = rows[index]
            active = [row]
            field = row['field']
            dtype = '<i8' if field == 'prior_delta_tick' else ('<f8' if field == 'p_move' else '|b1')
            count = job['train_count' if role == 'train' else 'dev_count']
            entry = population['arrays'][field]
            descriptor(entry, count=count, dtype=dtype, field=field)
            member = prefix + '/' + entry['filename']
            need(manifest['files'].get(member) == entry['file_sha256'], 'B1_HASH_CONFLICT')
            compressed_cap, _ = byte_caps(count, dtype)
            raw = reader.read(root + '/' + member, compressed_cap, 'array')
            verified = inspect_array(raw, entry, count=count, dtype=dtype)
            row['replicas'].append(
              {
                'replica': owner,
                **verified,
                'population_receipt_sha256': population['receipt_sha256'],
                'anchor_sha256': population['anchor_sha256'],
                'row_alignment': 'RECORDED_ORIGINAL_ORDER_PROVENANCE_VERIFIED',
              }
            )
            row.update(
              status='PASS' if owner == 'V1_REFERENCE' else 'INPUT_INSUFFICIENT',
              reason='EXACT_SAVED_INTEGRITY_AND_RECORDED_ORDER_VERIFIED' if owner == 'V1_REFERENCE' else 'V4_BOTH_REPLICAS_AND_EQUALITY_NOT_YET_VERIFIED',
            )
        for index in (3, 4):
          active = [rows[index]]
          pair = rows[index]['replicas']
          need(
            len(pair) == 2 and all(pair[0][key] == pair[1][key] for key in ('file_sha256', 'npy_sha256', 'array_sha256', 'dtype', 'shape', 'anchor_sha256')),
            'B1_REPLICA_FIELD_HASH_CONFLICT',
          )
          report['v4_dev_equal_field_pairs'] += 1
          rows[index].update(status='PASS', reason='EXACT_SAVED_INTEGRITY_RECORDED_ORDER_AND_FIELD_REPLICA_EQUALITY_VERIFIED')
        report['dev_aligned_jobs'] += 1
      report['status'] = 'B1_MIXED_CARRIER_ACCESS_BLOCKED'
  except (B1Error, b0.B0Error, OSError, ValueError, KeyError, TypeError, AttributeError, RecursionError) as error:
    code = error.code if isinstance(error, (B1Error, b0.B0Error)) else 'B1_SCHEMA_CONFLICT'
    report['error_code'] = code
    report['status'] = (
      'B1_ALIGNMENT_NOT_PROVEN'
      if code == 'B1_ROW_ALIGNMENT_NOT_PROVEN'
      else 'B1_PARTIAL_VERIFICATION_INPUT_INSUFFICIENT'
      if code == 'B1_MISSING'
      else 'B1_INPUT_CONFLICT_FAIL_CLOSED'
    )
    status = 'MISSING' if code == 'B1_MISSING' else ('HASH_CONFLICT' if 'HASH' in code else 'SCHEMA_CONFLICT')
    for row in active:
      row.update(status=status, reason=code)
  finally:
    if reader is not None:
      report['reads'] = reader.counters.copy()
      report['read_events'] = reader.events
  report['field_status_counts'] = dict(Counter(row['status'] for row in report['fields']))
  return sealed(report)


def verify_only(report, expected_raw_sha256, binding_sha256):
  """No source reader, decompressor, field verifier, model or scientific operation."""
  need(sha(b0._canonical(report)) == expected_raw_sha256, 'B1_RESUME_RECEIPT_CONFLICT')
  need(report.get('receipt_sha256') == sha(b0._canonical({k: v for k, v in report.items() if k != 'receipt_sha256'})), 'B1_RESUME_RECEIPT_CONFLICT')
  need(report.get('schema') == 'CYBERPILOT_V4_B1_SAVED_INTEGRITY_V1' and report.get('binding_sha256') == binding_sha256, 'B1_RESUME_RECEIPT_CONFLICT')
  need(
    len(report['fields']) == 224
    and [(r['candidate_id'], r['fold'], r['role'], r['owner'], r['field']) for r in report['fields']] == [(c, f, *field) for c, f in JOBS for field in FIELDS],
    'B1_RESUME_RECEIPT_CONFLICT',
  )
  return sealed(
    {
      'schema': 'CYBERPILOT_V4_B1_VERIFY_ONLY_V1',
      'status': 'B1_VERIFY_ONLY_PASS',
      'recompute_calls': 0,
      'source_file_openings': 0,
      'result_raw_sha256': expected_raw_sha256,
      'binding_sha256': binding_sha256,
      'C_AUTHORIZED': False,
      'D_AUTHORIZED': False,
      'E_AUTHORIZED': False,
      'F_AUTHORIZED': False,
    }
  )


def public_summary(report):
  """Explicit fixed projection; no paths, bytes, hashes, descriptors or row values."""
  allowed = {
    'B1_PARTIAL_VERIFICATION_INPUT_INSUFFICIENT',
    'B1_MIXED_CARRIER_ACCESS_BLOCKED',
    'B1_ALIGNMENT_NOT_PROVEN',
    'B1_INPUT_CONFLICT_FAIL_CLOSED',
  }
  need(report['status'] in allowed)
  need(
    tuple((r['candidate_id'], r['fold'], r['role'], r['owner'], r['field']) for r in report['fields'])
    == tuple((c, f, *field) for c, f in JOBS for field in FIELDS)
  )
  statuses = {'PASS', 'INPUT_INSUFFICIENT', 'MISSING', 'HASH_CONFLICT', 'SCHEMA_CONFLICT', 'ALIGNMENT_NOT_PROVEN', 'AUTHORITY_BLOCKED'}
  need(all(r['status'] in statuses for r in report['fields']))
  need(
    type(report['source_writes']) is int
    and report['source_writes'] == 0
    and all(report[k] is False for k in ('C_AUTHORIZED', 'D_AUTHORIZED', 'E_AUTHORIZED', 'F_AUTHORIZED'))
  )
  need(
    all(
      type(report[k]) is int and 0 <= report[k] <= limit
      for k, limit in (('dev_aligned_jobs', 32), ('train_three_field_aligned_jobs', 0), ('v4_dev_equal_field_pairs', 64))
    )
  )
  need(all(row['status'] == 'AUTHORITY_BLOCKED' for row in report['fields'] if row['field'] == 'combined_probability'))
  return {
    'status': report['status'],
    'field_status_counts': dict(Counter(r['status'] for r in report['fields'])),
    'fields': [{key: row[key] for key in ('candidate_id', 'fold', 'role', 'owner', 'field', 'status')} for row in report['fields']],
    'dev_aligned_jobs': report['dev_aligned_jobs'],
    'train_three_field_aligned_jobs': report['train_three_field_aligned_jobs'],
    'v4_dev_equal_field_pairs': report['v4_dev_equal_field_pairs'],
    'replica_payload_equality': 'REPLICA_PAYLOAD_EQUALITY_NOT_FULLY_REVERIFIED',
    'train_rowwise_gate': 'NOT_SAVED',
    'source_writes': 0,
    'C_AUTHORIZED': False,
    'D_AUTHORIZED': False,
    'E_AUTHORIZED': False,
    'F_AUTHORIZED': False,
  }
