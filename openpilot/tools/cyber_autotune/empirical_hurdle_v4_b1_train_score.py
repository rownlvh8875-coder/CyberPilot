"""Manifest-bound TRAIN bytes and recorded order only; no scientific execution.

The private caller authenticates its explicit grant, exact roots, prior B0/B1
controls, this source, host/mount and bounded output before run(). Mixed TRAIN
receipts/coefficients and the previous192 array payloads are never allowlisted.
"""

import ast
from collections import Counter
import struct
import zlib

from openpilot.tools.cyber_autotune import empirical_hurdle_v4_b0_metadata as b0
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_b1_evidence as b1

OWNERS = ('V4_REPEAT_1', 'V4_REPEAT_2')
ORDER_SOURCES = {**b1.ORDER_SOURCES, 'empirical_hurdle_v3_store.py': 'eadb505681a5e46f6cf447afcf4ccc1d68c6977c5a0c2e2ded8944465450567b'}
TRAIN_MEMBERS = frozenset(('receipt.json', 'combined_probability.npy.gz', 'STATIC_coefficients.npy.gz', 'MOVE_coefficients.npy.gz'))
SUCCESS = 'B1_TRAIN_SCORE_INTEGRITY_AND_RECORDED_ALIGNMENT_VERIFIED'


def need(condition, code='B1_TRAIN_SCHEMA_CONFLICT'):
  if not condition:
    raise b1.B1Error(code)


def check_seal(row):
  need(type(row) is dict and b0._digest(row.get('receipt_sha256')), 'B1_TRAIN_RECEIPT_CONFLICT')
  need(row['receipt_sha256'] == b1.sha(b0._canonical({k: v for k, v in row.items() if k != 'receipt_sha256'})), 'B1_TRAIN_RECEIPT_CONFLICT')


def inspect_score(raw, expected_compressed_sha256, count):
  """Expected compressed identity; inner digests are observations, not descriptors."""
  compressed_cap, decoded_cap = b1.byte_caps(count, '<f8')
  need(0 < len(raw) <= compressed_cap)
  need(b0._digest(expected_compressed_sha256) and b1.sha(raw) == expected_compressed_sha256, 'B1_TRAIN_HASH_CONFLICT')
  try:
    decoder = zlib.decompressobj(wbits=31)
    npy = decoder.decompress(raw, decoded_cap + 1)
    need(len(npy) <= decoded_cap and decoder.eof and not decoder.unused_data and not decoder.unconsumed_tail)
  except zlib.error:
    raise b1.B1Error('B1_TRAIN_SCHEMA_CONFLICT') from None
  need(npy[:6] == b'\x93NUMPY' and npy[6:8] in (b'\x01\x00', b'\x02\x00'))
  prefix = 10 if npy[6] == 1 else 12
  need(len(npy) >= prefix)
  length = struct.unpack('<H' if prefix == 10 else '<I', npy[8:prefix])[0]
  need(0 < length <= b1.HEADER_BYTES - prefix and prefix + length <= len(npy))
  header_bytes = npy[prefix : prefix + length]
  need(header_bytes.endswith(b'\n'))
  try:
    parsed = ast.parse(header_bytes.decode('ascii').strip(), mode='eval').body
    need(isinstance(parsed, ast.Dict) and len(parsed.keys) == 3)
    need({ast.literal_eval(k) for k in parsed.keys} == {'descr', 'fortran_order', 'shape'})
    header = ast.literal_eval(parsed)
  except (ValueError, SyntaxError, TypeError, UnicodeError, RecursionError):
    raise b1.B1Error('B1_TRAIN_SCHEMA_CONFLICT') from None
  need(header['descr'] == '<f8' and header['fortran_order'] is False and type(header['shape']) is tuple)
  need(header['shape'] == (count,) and all(type(v) is int for v in header['shape']))
  payload = npy[prefix + length :]
  need(len(payload) == count * 8)
  return {
    'compressed_sha256': b1.sha(raw),
    'npy_sha256': b1.sha(npy),
    'payload_sha256': b1.sha(payload),
    'shape': [count],
    'dtype': '<f8',
    'order': 'C',
    'raw_bytes': len(raw),
    'decoded_bytes': len(npy),
    'compressed_identity': 'MANIFEST_BOUND_COMPRESSED_FILE_VERIFIED',
    'inner_identity': 'LIVE_NPY_AND_PAYLOAD_HASH_OBSERVED',
    'original_descriptor_compared': False,
  }


def catalog(request, previous):
  need(request.get('authorized') is True, 'B1_TRAIN_AUTHORITY_CONFLICT')
  need(b0._digest(request.get('binding_sha256')), 'B1_TRAIN_AUTHORITY_CONFLICT')
  need(request.get('order_provenance') == ORDER_SOURCES, 'B1_TRAIN_ALIGNMENT_NOT_PROVEN')
  need(tuple((j['candidate_id'], j['fold']) for j in request['jobs']) == b1.JOBS, 'B1_TRAIN_JOB_CONFLICT')
  need(set(request['roots']) == set(OWNERS) and set(request['manifests']) == set(OWNERS))
  roots = [b0._path(request['roots'][k], absolute=True) for k in OWNERS]
  need(not roots[0].is_relative_to(roots[1]) and not roots[1].is_relative_to(roots[0]), 'B1_TRAIN_ROOT_ALIAS')
  need(set(previous) == {'binding', 'result', 'resume'}, 'B1_TRAIN_PREVIOUS_PROOF_CONFLICT')
  binding, result, resume = (previous[k] for k in ('binding', 'result', 'resume'))
  for row in (binding, result, resume):
    check_seal(row)
  need(binding['schema'] == 'CYBERPILOT_V4_B1_PRIVATE_BINDING_V1' and binding['mixed_carrier_open_authorized'] is False)
  need(binding['receipt_sha256'] == request['previous_binding_sha256'] == result['binding_sha256'] == resume['binding_sha256'])
  need(result['receipt_sha256'] == request['previous_result_receipt_sha256'])
  need(b1.sha(b0._canonical(result)) == resume['result_raw_sha256'] == request['previous_result_raw_sha256'])
  b1.verify_only(result, request['previous_result_raw_sha256'], binding['receipt_sha256'])
  need(resume['status'] == 'B1_VERIFY_ONLY_PASS' and resume['recompute_calls'] == 0 and resume['source_file_openings'] == 0)
  need(result['status'] == 'B1_MIXED_CARRIER_ACCESS_BLOCKED' and result['source_writes'] == 0)
  need(all(result[k] is False for k in (*b0.AUTHORITY_KEYS, 'C_AUTHORIZED', 'D_AUTHORIZED', 'E_AUTHORIZED', 'F_AUTHORIZED')))
  need(
    result['field_status_counts'] == {'PASS': 192, 'AUTHORITY_BLOCKED': 32} and result['dev_aligned_jobs'] == 32 and result['v4_dev_equal_field_pairs'] == 64
  )
  old = binding['request']
  b1.catalog({**old, 'binding_sha256': binding['receipt_sha256']})
  need(request['jobs'] == old['jobs'] and request['authorization'] == old['authorization']['V4'], 'B1_TRAIN_PREVIOUS_PROOF_CONFLICT')
  need(all(request['roots'][k] == old['roots'][k] and request['manifests'][k] == old['manifests'][k] for k in OWNERS))
  need(request['manifests'][OWNERS[0]]['receipt_sha256'] == request['manifests'][OWNERS[1]]['receipt_sha256'], 'B1_TRAIN_REPLICA_MANIFEST_CONFLICT')
  for index, job in enumerate(request['jobs']):
    b1.byte_caps(job['train_count'], '<f8')
    rows = result['fields'][index * 7 : (index + 1) * 7]
    need(rows[0]['status'] == 'AUTHORITY_BLOCKED' and all(r['status'] == 'PASS' for r in rows[1:]))
    for row in rows[1:3]:
      need(len(row['replicas']) == 1)
      ref = row['replicas'][0]
      need(ref['replica'] == 'V1_REFERENCE' and ref['population_receipt_sha256'] == job['v1_train_receipt'])
      need(ref['anchor_sha256'] == job['train_anchor'] and ref['shape'] == [job['train_count']], 'B1_TRAIN_ALIGNMENT_NOT_PROVEN')
      need(ref['order'] == 'C' and ref['row_alignment'] == 'RECORDED_ORIGINAL_ORDER_PROVENANCE_VERIFIED')
      need(ref['hash_schema_shape_dtype'] == 'PASS' and all(b0._digest(ref[k]) for k in ('file_sha256', 'npy_sha256', 'array_sha256')))


def paths(request):
  allow = {}
  for owner in OWNERS:
    root = request['roots'][owner]
    allow[root + '/manifest.json'] = (b0.BYTE_CAPS[b0.RECORD_IDS[0]], 'metadata')
    for job in request['jobs']:
      base = root + '/candidates/' + job['candidate_id'] + '/' + job['fold']
      for member in ('train/manifest.json', 'train-finalized.json'):
        allow[base + '/' + member] = (b1.METADATA_BYTES, 'metadata')
      allow[base + '/train/combined_probability.npy.gz'] = (b1.byte_caps(job['train_count'], '<f8')[0], 'array')
  need(len(allow) == 194, 'B1_TRAIN_ALLOWLIST_CONFLICT')
  return allow


def chain(reader, root, manifest, job, authorization):
  prefix = 'candidates/' + job['candidate_id'] + '/' + job['fold']

  def read(member, receipt):
    name = prefix + '/' + member
    need(name in manifest['files'], 'B1_TRAIN_MANIFEST_MEMBER_MISSING')
    return b1.metadata(reader.read(root + '/' + name, b1.METADATA_BYTES, 'metadata'), manifest['files'][name], receipt)

  sub = read('train/manifest.json', job['train_manifest'])
  b1._fields(sub, 'V4_TRAIN_MANIFEST', ('train_receipt_sha256', 'files'))
  need(type(sub['files']) is dict and set(sub['files']) == TRAIN_MEMBERS)
  need(all(b0._digest(v) for v in sub['files'].values()))
  final = read('train-finalized.json', job['finalized_receipt'])
  b1._fields(
    final,
    'V4_TRAIN_FINALIZED',
    ('status', 'candidate_id', 'fold', 'train_anchor_sha256', 'authorization_sha256', 'train_manifest_sha256', 'model_threshold_receipt_sha256'),
  )
  need(final['status'] == 'TRAIN_COMPLETE' and final['candidate_id'] == job['candidate_id'] and final['fold'] == job['fold'])
  need(final['train_anchor_sha256'] == job['train_anchor'], 'B1_TRAIN_ALIGNMENT_NOT_PROVEN')
  need(final['authorization_sha256'] == authorization == manifest['authorization_sha256'])
  need(final['train_manifest_sha256'] == sub['receipt_sha256'] == job['train_manifest'], 'B1_TRAIN_RECEIPT_CONFLICT')
  need(final['model_threshold_receipt_sha256'] == sub['train_receipt_sha256'] == job['train_receipt'], 'B1_TRAIN_RECEIPT_CONFLICT')
  need(all(manifest['files'].get(prefix + '/train/' + name) == digest for name, digest in sub['files'].items()), 'B1_TRAIN_HASH_CONFLICT')
  return prefix + '/train/combined_probability.npy.gz', sub['files']['combined_probability.npy.gz'], final['train_anchor_sha256']


def run(request, previous):
  report = {
    'schema': 'CYBERPILOT_V4_B1_TRAIN_SCORE_RESULT_V1',
    'status': 'B1_TRAIN_SCORE_PARTIAL_VERIFICATION',
    'binding_sha256': request.get('binding_sha256'),
    'previous_result_receipt_sha256': request.get('previous_result_receipt_sha256'),
    'previous_binding_sha256': request.get('previous_binding_sha256'),
    'fields': [
      {'candidate_id': c, 'fold': f, 'role': 'TRAIN', 'field': 'combined_probability', 'status': 'INPUT_INSUFFICIENT', 'replicas': []} for c, f in b1.JOBS
    ],
    'reads': dict.fromkeys(('metadata_file_openings', 'array_file_openings', 'metadata_bytes_read', 'array_bytes_read'), 0),
    'new_train_fields_pass': 0,
    'prior_fields_carried_forward': 0,
    'cumulative_fields_verified': 0,
    'train_three_field_aligned_jobs': 0,
    'train_equal_field_pairs': 0,
    'mixed_carrier_openings': 0,
    'source_writes': 0,
    'train_rowwise_gate': 'NOT_SAVED',
    'replica_payload_equality': 'REPLICA_PAYLOAD_EQUALITY_NOT_FULLY_REVERIFIED',
    'original_mixed_descriptor': 'ORIGINAL_MIXED_DESCRIPTOR_NOT_OPENED',
    'C_AUTHORIZED': False,
    'D_AUTHORIZED': False,
    'E_AUTHORIZED': False,
    'F_AUTHORIZED': False,
  }
  reader = None
  try:
    catalog(request, previous)
    report['prior_fields_carried_forward'] = report['cumulative_fields_verified'] = 192
    with b1.GuardedReader(request['mount_root'], request['mount_identity'], paths(request)) as reader:
      roots = {}
      for owner in OWNERS:
        pin = request['manifests'][owner]
        raw = reader.read(request['roots'][owner] + '/manifest.json', b0.BYTE_CAPS[b0.RECORD_IDS[0]], 'metadata')
        row = b1.metadata(raw, pin['raw_sha256'], pin['receipt_sha256'])
        pins = b0.IdentityPins(pin['receipt_sha256'], '0' * 64, '0' * 64, request['authorization'], '0' * 64)
        b0._validate(row, 0, pin['receipt_sha256'], pins)
        roots[owner] = row
      for row, job in zip(report['fields'], request['jobs'], strict=True):
        for owner in OWNERS:
          root = request['roots'][owner]
          member, digest, anchor = chain(reader, root, roots[owner], job, request['authorization'])
          raw = reader.read(root + '/' + member, b1.byte_caps(job['train_count'], '<f8')[0], 'array')
          observed = inspect_score(raw, digest, job['train_count'])
          row['replicas'].append({'replica': owner, 'anchor_sha256': anchor, 'row_alignment': 'RECORDED_ORIGINAL_ORDER_PROVENANCE_VERIFIED', **observed})
        pair = row['replicas']
        need(
          len(pair) == 2
          and all(pair[0][k] == pair[1][k] for k in ('compressed_sha256', 'npy_sha256', 'payload_sha256', 'shape', 'dtype', 'order', 'anchor_sha256')),
          'B1_TRAIN_REPLICA_HASH_CONFLICT',
        )
        row['status'] = 'PASS'
        report['new_train_fields_pass'] += 1
        report['cumulative_fields_verified'] += 1
        report['train_three_field_aligned_jobs'] += 1
        report['train_equal_field_pairs'] += 1
      report['status'] = SUCCESS
  except (b1.B1Error, b0.B0Error, OSError, ValueError, KeyError, TypeError, AttributeError, RecursionError) as error:
    code = error.code if isinstance(error, (b1.B1Error, b0.B0Error)) else 'B1_TRAIN_SCHEMA_CONFLICT'
    report['error_code'] = code
    report['status'] = (
      'B1_TRAIN_PROVENANCE_INSUFFICIENT'
      if code == 'B1_TRAIN_ALIGNMENT_NOT_PROVEN'
      else 'B1_TRAIN_SCORE_PARTIAL_VERIFICATION'
      if code in ('B1_MISSING', 'B0_MISSING_EXACT_TARGET')
      else 'B1_TRAIN_INPUT_CONFLICT_FAIL_CLOSED'
    )
  finally:
    if reader is not None:
      report['reads'] = dict(reader.counters)
      report['read_events'] = reader.events
  return b1.sealed(report)


def verify_only(report, expected_raw_sha256, binding_sha256):
  check_seal(report)
  need(b1.sha(b0._canonical(report)) == expected_raw_sha256 and report['binding_sha256'] == binding_sha256, 'B1_TRAIN_RESUME_CONFLICT')
  need(report['schema'] == 'CYBERPILOT_V4_B1_TRAIN_SCORE_RESULT_V1')
  public_summary(report)
  return b1.sealed(
    {
      'schema': 'CYBERPILOT_V4_B1_TRAIN_VERIFY_ONLY_V1',
      'status': 'B1_TRAIN_VERIFY_ONLY_PASS',
      'result_raw_sha256': expected_raw_sha256,
      'binding_sha256': binding_sha256,
      'recompute_calls': 0,
      'source_file_openings': 0,
      'C_AUTHORIZED': False,
      'D_AUTHORIZED': False,
      'E_AUTHORIZED': False,
      'F_AUTHORIZED': False,
    }
  )


def public_summary(report):
  need(report['status'] in (SUCCESS, 'B1_TRAIN_SCORE_PARTIAL_VERIFICATION', 'B1_TRAIN_PROVENANCE_INSUFFICIENT', 'B1_TRAIN_INPUT_CONFLICT_FAIL_CLOSED'))
  need(
    tuple((r['candidate_id'], r['fold'], r['role'], r['field']) for r in report['fields']) == tuple((c, f, 'TRAIN', 'combined_probability') for c, f in b1.JOBS)
  )
  need(all(r['status'] in ('PASS', 'INPUT_INSUFFICIENT') for r in report['fields']))
  counts = Counter(r['status'] for r in report['fields'])
  for key, limit in (
    ('new_train_fields_pass', 32),
    ('prior_fields_carried_forward', 192),
    ('cumulative_fields_verified', 224),
    ('train_three_field_aligned_jobs', 32),
    ('train_equal_field_pairs', 32),
    ('source_writes', 0),
    ('mixed_carrier_openings', 0),
  ):
    need(type(report[key]) is int and 0 <= report[key] <= limit)
  need(report['new_train_fields_pass'] == counts['PASS'] == report['train_three_field_aligned_jobs'] == report['train_equal_field_pairs'])
  need(report['prior_fields_carried_forward'] in (0, 192) and report['cumulative_fields_verified'] == report['prior_fields_carried_forward'] + counts['PASS'])
  need(all(report[k] is False for k in ('C_AUTHORIZED', 'D_AUTHORIZED', 'E_AUTHORIZED', 'F_AUTHORIZED')))
  if report['status'] == SUCCESS:
    need(counts['PASS'] == 32 and report['cumulative_fields_verified'] == 224)
  return {
    'status': report['status'],
    'fields': [{k: r[k] for k in ('candidate_id', 'fold', 'role', 'field', 'status')} for r in report['fields']],
    **{
      k: report[k]
      for k in (
        'new_train_fields_pass',
        'prior_fields_carried_forward',
        'cumulative_fields_verified',
        'train_three_field_aligned_jobs',
        'train_equal_field_pairs',
      )
    },
    'mixed_carrier_openings': 0,
    'source_writes': 0,
    'original_mixed_descriptor': 'ORIGINAL_MIXED_DESCRIPTOR_NOT_OPENED',
    'replica_payload_equality': 'REPLICA_PAYLOAD_EQUALITY_NOT_FULLY_REVERIFIED',
    'train_rowwise_gate': 'NOT_SAVED',
    'C_AUTHORIZED': False,
    'D_AUTHORIZED': False,
    'E_AUTHORIZED': False,
    'F_AUTHORIZED': False,
  }
