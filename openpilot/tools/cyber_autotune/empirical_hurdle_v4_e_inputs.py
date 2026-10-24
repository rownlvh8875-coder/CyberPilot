"""E-only exact manifest-member reader. No discovery or sensitive TRAIN receipt.

The external reviewed caller authenticates roots, prior controls, protocol, CI,
human scope and output binding before constructing Reader. This module cannot
grant authority. openat2 protects each input open, not the entire process.
"""

import ast
import math
from pathlib import PurePosixPath
import re
import struct
import zlib

import numpy as np

from openpilot.tools.cyber_autotune import empirical_hurdle_v4_b0_metadata as b0
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_b1_evidence as b1
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e_decision as decision
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e_evaluation as evaluation

need = decision.need
MAX_SOURCE_ROWS = 916535  # Frozen public causal readiness total-aligned-row upper bound.
METADATA_BYTES = 32 * 1024**2  # Exceeds frozen B0 maximum manifest schema bound.
HEADER_BYTES = 65536  # Existing B1 bound; headers cannot grow with numeric payload.
MAX_INPUT_OPENS = 2989  # 637 exact metadata +2352 numeric members, all32 jobs/154 segments.
MAX_INPUT_BYTES = 64 * 1024**3  # Sum of fixed per-member worst-case caps is below this bound.
DTYPES = {'|b1': 1, '<i2': 2, '<i8': 8, '<f8': 8}
NORMALIZER_FIELDS = ('mean', 'std', 'constant', 'effective', 'constant_reference')
CAUSAL_FIELDS = ('command.normalized', 'state.speed_mps')
DERIVED_FIELDS = ('angle_tick', 'streak_all', 'model_eligible', 'rail', 's2_ri_causal_run_id', 'within_s2_ri_causal_run_index')
DEV_FIELDS = ('p_move', 'predicted_gate', 'integrated_delta', 'projected_next_tick', 'candidate_error')
ROLLOUT_FIELDS = ('projected_path', 'predicted_gate_path', 'candidate_error')


class Phase:
  def __init__(self):
    self.train_sha256 = None

  def seal_train(self, jobs):
    need(self.train_sha256 is None and tuple((j['candidate_id'], j['fold']) for j in jobs) == decision.JOBS, 'E_ALL_TRAIN_DECISIONS_REQUIRED')
    for job in jobs:
      need(set(job['contexts']) == {'PREVIOUS_STATIC', 'PREVIOUS_MOVE'})
      for value in job['contexts'].values():
        need(
          type(value['decision']) is float
          and np.isfinite(value['decision'])
          and 0 <= value['decision'] <= 1
          and value['positive'] > 0
          and value['negative'] > 0
        )
    self.train_sha256 = evaluation.sha(evaluation.canonical(jobs))

  def require_dev(self):
    need(self.train_sha256 is not None, 'E_DEV_BEFORE_ALL_64_TRAIN_DECISIONS_SEALED')


def member_allowed(owner, member, kind):
  b0._path(member, absolute=False)
  need(kind in ('metadata', 'array') and owner in ('V4', 'V1', 'V1_TOP', 'CAUSAL', 'DERIVED'), 'E_MEMBER_SCOPE')
  if kind == 'metadata':
    if owner in ('V4', 'V1') and member == 'manifest.json':
      return
    if owner == 'V1_TOP' and member in ('authorization.json', 'input-pins.json'):
      return
    if owner == 'CAUSAL' and (
      member in ('authorization.json', 'repeat-1/manifest.json') or re.fullmatch(r'repeat-1/routes/[0-9a-f]{64}/segments/[0-9a-f]{64}/receipt\.json', member)
    ):
      return
    if owner == 'DERIVED' and (
      member in ('repeat-1/derived-index.json', 'repeat-1/results.json', 'repeat-1/admission.json')
      or re.fullmatch(r'repeat-1/segments/[0-9a-f]{64}/receipt\.json', member)
    ):
      return
  if owner in ('V4', 'V1'):
    parts = member.split('/')
    need(len(parts) >= 4 and parts[0] == 'candidates' and (parts[1], parts[2]) in decision.JOBS, 'E_JOB_SCOPE')
    tail = '/'.join(parts[3:])
    if owner == 'V4':
      metadata = {'train/manifest.json', 'train-finalized.json', 'one-step/receipt.json', *(f'rollout-{h}/receipt.json' for h in evaluation.HORIZONS)}
      arrays = {'train/' + f + '.npy.gz' for f in ('combined_probability', 'STATIC_coefficients', 'MOVE_coefficients')}
      arrays |= {'one-step/' + f + '.npy.gz' for f in DEV_FIELDS}
      arrays |= {f'rollout-{h}/{f}.npy.gz' for h in evaluation.HORIZONS for f in ROLLOUT_FIELDS}
    else:
      metadata = {f'{stage}/normalizer/receipt.json' for stage in ('stage1', 'stage2')} | {'stage2/model/receipt.json'}
      arrays = {f'{stage}/normalizer/{f}.npy.gz' for stage in ('stage1', 'stage2') for f in NORMALIZER_FIELDS}
      arrays |= {
        'stage2/model/coefficients.npy.gz',
        'train/move_label.npy.gz',
        'train/prior_delta_tick.npy.gz',
        'one-step/true_move.npy.gz',
        'one-step/prior_delta_tick.npy.gz',
      }
    need(member != '' and (tail in metadata if kind == 'metadata' else tail in arrays), 'E_MEMBER_SCOPE')
    return
  if kind == 'array' and owner == 'CAUSAL':
    need(
      re.fullmatch(r'repeat-1/routes/[0-9a-f]{64}/segments/[0-9a-f]{64}/arrays/(' + '|'.join(map(re.escape, CAUSAL_FIELDS)) + r')\.npy', member) is not None,
      'E_SOURCE_FIELD_SCOPE',
    )
    return
  if kind == 'array' and owner == 'DERIVED':
    need(re.fullmatch(r'repeat-1/segments/[0-9a-f]{64}/(' + '|'.join(DERIVED_FIELDS) + r')\.npy', member) is not None, 'E_SOURCE_FIELD_SCOPE')
    return
  raise ValueError('E_MEMBER_SCOPE')


def caps(shape, dtype):
  need(dtype in DTYPES and type(shape) is tuple and 1 <= len(shape) <= 2 and all(type(n) is int and n > 0 for n in shape), 'E_ARRAY_SCHEMA_CONFLICT')
  need(shape[0] <= MAX_SOURCE_ROWS and (len(shape) == 1 or (shape[0] <= decision.MAX_COUNT and shape[1] <= 201)), 'E_ARRAY_SIZE_BOUND')
  decoded = math.prod(shape) * DTYPES[dtype] + HEADER_BYTES
  return decoded + decoded // 100 + HEADER_BYTES, decoded


def decode(raw, desc, *, shape, dtype, compressed):
  """Full raw/NPY/payload validation, bounded single gzip member; no pickle."""
  raw_cap, decoded_cap = caps(shape, dtype)
  need(type(raw) is bytes and len(raw) <= (raw_cap if compressed else decoded_cap), 'E_ARRAY_SIZE_BOUND')
  need(desc['dtype'] == dtype and desc['shape'] == list(shape) and desc['order'] == 'C', 'E_ARRAY_SCHEMA_CONFLICT')
  need(evaluation.sha(raw) == desc['file_sha256'], 'E_ARRAY_RAW_HASH_CONFLICT')
  if compressed:
    try:
      decoder = zlib.decompressobj(wbits=31)
      npy = decoder.decompress(raw, decoded_cap + 1)
      need(len(npy) <= decoded_cap and decoder.eof and not decoder.unused_data and not decoder.unconsumed_tail, 'E_GZIP_BOUND_OR_TRAILING_CONFLICT')
    except zlib.error:
      raise ValueError('E_GZIP_INTEGRITY_CONFLICT') from None
  else:
    npy = raw
  need(npy[:6] == b'\x93NUMPY' and npy[6:8] in (b'\x01\x00', b'\x02\x00'), 'E_NPY_FORMAT_CONFLICT')
  prefix = 10 if npy[6] == 1 else 12
  need(len(npy) >= prefix, 'E_NPY_HEADER_CONFLICT')
  size = struct.unpack('<H' if prefix == 10 else '<I', npy[8:prefix])[0]
  need(0 < size <= HEADER_BYTES and prefix + size <= len(npy), 'E_NPY_HEADER_BOUND')
  try:
    header = ast.literal_eval(npy[prefix : prefix + size].decode('ascii'))
  except (ValueError, SyntaxError, UnicodeError):
    raise ValueError('E_NPY_HEADER_CONFLICT') from None
  need(
    type(header) is dict
    and set(header) == {'descr', 'fortran_order', 'shape'}
    and header['descr'] == dtype
    and header['fortran_order'] is False
    and header['shape'] == shape,
    'E_NPY_SCHEMA_CONFLICT',
  )
  payload = npy[prefix + size :]
  need(len(payload) == math.prod(shape) * DTYPES[dtype], 'E_NPY_PAYLOAD_LENGTH_CONFLICT')
  npy_sha, payload_sha = evaluation.sha(npy), evaluation.sha(payload)
  need('npy_sha256' not in desc or desc['npy_sha256'] == npy_sha, 'E_NPY_HASH_CONFLICT')
  need('array_sha256' not in desc or desc['array_sha256'] == payload_sha, 'E_PAYLOAD_HASH_CONFLICT')
  if dtype == '|b1':
    need(bool(np.all(np.frombuffer(payload, dtype='u1') <= 1)), 'E_NONBINARY_ENCODING')
  values = np.frombuffer(payload, dtype=dtype).reshape(shape)
  need(not values.flags.writeable, 'E_SOURCE_ARRAY_WRITABLE')
  return values, {
    'compressed_or_raw_sha256': desc['file_sha256'],
    'npy_sha256': npy_sha,
    'payload_sha256': payload_sha,
    'shape': list(shape),
    'dtype': dtype,
    'historical_descriptor_payload_hash_compared': 'array_sha256' in desc,
  }


class Reader:
  """Roots/maps are supplied only by the reviewed external execution binding.

  Each one-file GuardedReader uses the existing openat2 and bounded-read checks.
  This class also rejects duplicate/aliased reads across those instances.
  """

  def __init__(self, roots, mount_root, mount_identity, phase):
    need(set(roots) == {'V4', 'V1', 'V1_TOP', 'CAUSAL', 'DERIVED'})
    self.roots = {k: b0._path(v, absolute=True) for k, v in roots.items()}
    self.mount_root, self.mount_identity, self.phase = mount_root, mount_identity, phase
    self.events, self.inodes, self.used, self.metadata_cache = [], set(), set(), {}
    self.maps = {}

  def raw(self, owner, member, kind, expected_raw, cap):
    member_allowed(owner, member, kind)
    bootstrap = kind == 'metadata' and ((owner in ('V4', 'V1') and member == 'manifest.json') or owner == 'V1_TOP')
    train_array = kind == 'array' and (
      (owner == 'V4' and member.endswith('/train/combined_probability.npy.gz'))
      or (owner == 'V1' and member.endswith(('/train/move_label.npy.gz', '/train/prior_delta_tick.npy.gz')))
    )
    if not bootstrap and not train_array:
      self.phase.require_dev()
    path = str(self.roots[owner] / member)
    named_bootstrap = kind == 'metadata' and owner == 'V1_TOP' and member in ('authorization.json', 'input-pins.json')
    need(path not in self.used and (b0._digest(expected_raw) or (expected_raw is None and named_bootstrap)), 'E_DUPLICATE_OR_HASH_BINDING_CONFLICT')
    need(len(self.events) < MAX_INPUT_OPENS and sum(e['bytes_read'] for e in self.events) + cap <= MAX_INPUT_BYTES, 'E_INPUT_RESOURCE_BOUND')
    self.used.add(path)
    with b1.GuardedReader(self.mount_root, self.mount_identity, {path: (cap, kind)}) as reader:
      try:
        raw = reader.read(path, cap, kind)
        need(not self.inodes.intersection(reader.inodes), 'E_ALIAS_CONFLICT')
        self.inodes.update(reader.inodes)
      finally:
        self.events.extend({'owner': owner, **e} for e in reader.events)
    need(expected_raw is None or evaluation.sha(raw) == expected_raw, 'E_MANIFEST_MEMBER_HASH_CONFLICT')
    return raw

  def metadata(self, owner, member, *, raw_sha=None, receipt_sha=None):
    if (owner, member) in self.metadata_cache:
      row, digest = self.metadata_cache[owner, member]
      need(raw_sha is None or digest == raw_sha, 'E_METADATA_PIN_CONFLICT')
      need(receipt_sha is None or row['receipt_sha256'] == receipt_sha, 'E_METADATA_RECEIPT_CONFLICT')
      return row
    expected = raw_sha or self.maps.get(owner, {}).get(member)
    raw = self.raw(owner, member, 'metadata', expected, METADATA_BYTES)
    row = b0._decode(raw)
    need(row['receipt_sha256'] == evaluation.sha(evaluation.canonical({k: v for k, v in row.items() if k != 'receipt_sha256'})), 'E_METADATA_SEAL_CONFLICT')
    need(all(row.get(key) is False for key in b0.AUTHORITY_KEYS), 'E_LEGACY_AUTHORITY_CONFLICT')
    need(receipt_sha is None or row['receipt_sha256'] == receipt_sha, 'E_METADATA_RECEIPT_CONFLICT')
    self.metadata_cache[owner, member] = row, evaluation.sha(raw)
    return row

  def array(self, owner, member, desc, *, shape, dtype, compressed=True):
    need(self.maps[owner].get(member) == desc['file_sha256'], 'E_UNBOUND_ARRAY_MEMBER')
    cap = caps(shape, dtype)[0 if compressed else 1]
    raw = self.raw(owner, member, 'array', desc['file_sha256'], cap)
    array, proof = decode(raw, desc, shape=shape, dtype=dtype, compressed=compressed)
    self.events[-1]['verification'] = proof
    return array

  def old_field(self, record):
    owner = 'V4' if record['owner'] == 'V4' else 'V1'
    member = str(PurePosixPath(record['path']).relative_to(self.roots[owner]))
    return self.array(owner, member, record['descriptor'], shape=(record['n'],), dtype=record['dtype'])

  def summary(self):
    return {
      kind: {
        'files': sum(e['file_openings'] for e in self.events if e['kind'] == kind),
        'bytes': sum(e['bytes_read'] for e in self.events if e['kind'] == kind),
      }
      for kind in ('metadata', 'array')
    }


class Provider:
  """Exact historical file-set pins plus the seven B1-verified field bindings."""

  def __init__(self, reader, bound_jobs, *, v4_manifest, v1_manifest, v4_authorization, v1_authorization_sha, references, job_catalog, source_policy):
    self.reader, self.bound_jobs, self.references = reader, bound_jobs, references
    self.catalog, self.source_policy = job_catalog, source_policy
    need(tuple((j['candidate_id'], j['fold']) for j in bound_jobs) == decision.JOBS)
    self.v4_auth = v4_authorization
    for owner, pin in (('V4', v4_manifest), ('V1', v1_manifest)):
      manifest = reader.metadata(owner, 'manifest.json', raw_sha=pin['raw_sha256'], receipt_sha=pin['receipt_sha256'])
      need(type(manifest['files']) is dict and all(b0._digest(v) for v in manifest['files'].values()), 'E_ROOT_MANIFEST_CONFLICT')
      reader.maps[owner] = manifest['files']
    original = reader.metadata('V1_TOP', 'authorization.json', receipt_sha=v1_authorization_sha)
    pins = reader.metadata('V1_TOP', 'input-pins.json')
    need(
      set(pins) == {'source', 'derived', 'authorization_sha256', 'receipt_sha256', *b0.AUTHORITY_KEYS} and pins['authorization_sha256'] == v1_authorization_sha
    )
    for owner, name in (('CAUSAL', 'source'), ('DERIVED', 'derived')):
      digest = evaluation.sha(evaluation.canonical(pins[name]))
      need(digest == original[name + '_file_set_sha256'] == v4_authorization['source_manifests'][name + '_file_set'], 'E_FROZEN_SOURCE_PIN_SET_CONFLICT')
      need(type(pins[name]) is dict and all(b0._digest(v) for v in pins[name].values()))
      for member in pins[name]:
        b0._path(member, absolute=False)
      reader.maps[owner] = pins[name]
    need(
      original['source_manifest_sha256'] == v4_authorization['source_manifests']['causal']
      and original['derived_index_sha256'] == v4_authorization['source_manifests']['derived_index']
      and original['derived_result_sha256'] == v4_authorization['source_manifests']['derived_result'],
      'E_SOURCE_MANIFEST_IDENTITY_CONFLICT',
    )
    self.original_authorization = original
    self.segments = None

  def train(self, index):
    fields = self.bound_jobs[index]['fields'][:3]
    need([v['role'] for v in fields] == ['TRAIN'] * 3)
    return tuple(self.reader.old_field(v) for v in fields)

  def admit_segments(self):
    self.reader.phase.require_dev()
    r, expected = self.reader, self.v4_auth['source_manifests']
    manifest = r.metadata('CAUSAL', 'repeat-1/manifest.json', receipt_sha=expected['causal'])
    auth = r.metadata('CAUSAL', 'authorization.json')
    index = r.metadata('DERIVED', 'repeat-1/derived-index.json', receipt_sha=expected['derived_index'])
    result = r.metadata('DERIVED', 'repeat-1/results.json', receipt_sha=expected['derived_result'])
    admission = r.metadata('DERIVED', 'repeat-1/admission.json', receipt_sha=result['admission_sha256'])
    need(admission['manifest_sha256'] == manifest['receipt_sha256'], 'E_DERIVED_ADMISSION_CONFLICT')
    indexed = {s['content_sha256']: s['receipt_sha256'] for s in index['segments']}
    identities = [s for values in auth['segments'].values() for s in values]
    need(
      len(index['segments']) == len(indexed) == len(identities) == len(set(identities)) == 154 and set(identities) == set(indexed),
      'E_EXACT_154_SEGMENTS_REQUIRED',
    )
    need(
      set(auth['segments']) == set(self.source_policy['route_ids']) and not set(identities).intersection(self.source_policy['excluded_qlog_content_sha256']),
      'E_ROUTE_OR_QLOG_CONFLICT',
    )
    segments, total = [], 0
    for route in sorted(auth['segments']):
      for identity in sorted(auth['segments'][route]):
        need(b0._digest(route) and b0._digest(identity))
        source_prefix = f'repeat-1/routes/{route}/segments/{identity}'
        derived_prefix = f'repeat-1/segments/{identity}'
        source = r.metadata('CAUSAL', source_prefix + '/receipt.json')
        derived = r.metadata('DERIVED', derived_prefix + '/receipt.json', receipt_sha=indexed[identity])
        need(
          source['route_id'] == route
          and source['segment_sha256'] == identity
          and derived['source_receipt_sha256'] == source['receipt_sha256']
          and derived['policy_sha256'] == self.source_policy['receipt_sha256'],
          'E_SEGMENT_LINEAGE_CONFLICT',
        )
        n = source['arrays']['state.speed_mps']['shape'][0]
        need(type(n) is int and 0 < n <= MAX_SOURCE_ROWS)
        total += n
        need(total <= MAX_SOURCE_ROWS, 'E_FROZEN_SOURCE_TOTAL_ROW_BOUND')
        arrays = {}
        for owner, prefix, row, fields in (('CAUSAL', source_prefix + '/arrays', source, CAUSAL_FIELDS), ('DERIVED', derived_prefix, derived, DERIVED_FIELDS)):
          for field in fields:
            desc = row['arrays'][field]
            dtype = '<f8' if owner == 'CAUSAL' else '|b1' if field in ('model_eligible', 'rail') else '<i8'
            arrays[field] = r.array(owner, prefix + '/' + field + '.npy', desc, shape=(n,), dtype=dtype, compressed=False)
        need(bool(np.all((arrays['angle_tick'] >= -32768) & (arrays['angle_tick'] <= 32767))), 'E_SOURCE_TICK_RANGE')
        need(bool(np.all((arrays['streak_all'] > 0) == arrays['model_eligible'])), 'E_ELIGIBILITY_CONFLICT')
        segments.append(
          {
            'route_id': route,
            'segment_sha256': identity,
            'tick': arrays['angle_tick'],
            'streak': arrays['streak_all'],
            'command': arrays['command.normalized'],
            'speed': arrays['state.speed_mps'],
            'rail': arrays['rail'],
            'eligible': arrays['model_eligible'],
            'run': arrays['s2_ri_causal_run_id'],
            'within': arrays['within_s2_ri_causal_run_index'],
          }
        )
    self.segments = tuple(segments)

  def route(self, route, candidate):
    self.reader.phase.require_dev()
    need(self.segments is not None)
    selected = sorted((s for s in self.segments if s['route_id'] == route), key=lambda s: s['segment_sha256'])
    need(bool(selected))
    # No timestamps are opened: immutable frozen streak/run/within identities
    # and the exact ordered anchor digests prove the original admitted windows.
    for horizon in (1, *evaluation.HORIZONS):
      for segment in selected:
        ix = evaluation.frozen.m.anchors(segment, candidate, horizon)
        need(
          np.all(segment['run'][ix] == segment['run'][ix + horizon]) and np.all(segment['within'][ix + horizon] - segment['within'][ix] == horizon),
          'E_SOURCE_BOUNDARY_CONFLICT',
        )
    return selected

  def models(self, index):
    r = self.reader
    r.phase.require_dev()
    public, reference = self.catalog[index], self.references[index]
    candidate, fold = public['candidate_id'], public['fold']
    need((candidate, fold) == (reference['candidate_id'], reference['fold']))
    prefix = f'candidates/{candidate}/{fold}'
    _, length = evaluation.frozen.m.parameters(candidate)
    dim = 2 * length + 3
    norms = {}
    for stage in ('stage1', 'stage2'):
      part = f'{prefix}/{stage}/normalizer'
      receipt = r.metadata('V1', part + '/receipt.json', receipt_sha=reference[stage]['normalizer_receipt_sha256'])
      need(receipt['candidate_id'] == candidate and receipt['fold'] == fold and receipt['stage'] == stage.upper())
      need(set(receipt['arrays']) == set(NORMALIZER_FIELDS))
      norm = {}
      for field in NORMALIZER_FIELDS:
        desc = receipt['arrays'][field]
        count = desc['shape'][0]
        need(0 < count <= dim and (field == 'effective' or count == dim))
        dtype = '|b1' if field == 'constant' else '<i8' if field == 'effective' else '<f8'
        norm[field] = r.array('V1', part + '/' + field + '.npy.gz', desc, shape=(count,), dtype=dtype)
      norms[stage] = norm
    need(
      public['v1_stage1_normalizer_receipt_sha256'] == reference['stage1']['normalizer_receipt_sha256']
      and public['v1_stage2_receipts_sha256'] == evaluation.sha(evaluation.canonical(reference['stage2'])),
      'E_V1_FROZEN_MODEL_LINK_CONFLICT',
    )
    fitting = evaluation.frozen.f
    fitting.validate_normalizer(norms['stage1'], candidate)
    fitting.validate_normalizer(norms['stage2'], candidate)
    need(not np.any(norms['stage1']['constant']) and np.array_equal(norms['stage1']['effective'], np.arange(dim)))
    train_manifest = r.metadata('V4', prefix + '/train/manifest.json', receipt_sha=public['train_manifest_sha256'])
    finalized = r.metadata('V4', prefix + '/train-finalized.json', receipt_sha=public['train_finalized_sha256'])
    need(
      finalized['candidate_id'] == candidate
      and finalized['fold'] == fold
      and finalized['status'] == 'TRAIN_COMPLETE'
      and finalized['authorization_sha256'] == self.v4_auth['authorization_sha256']
      and finalized['train_anchor_sha256'] == public['train_anchor_sha256']
      and finalized['train_manifest_sha256'] == train_manifest['receipt_sha256']
      and finalized['model_threshold_receipt_sha256'] == train_manifest['train_receipt_sha256'] == public['train_receipt_sha256'],
      'E_TRAIN_CHAIN_CONFLICT',
    )
    heads = {}
    for state, label in enumerate(('STATIC', 'MOVE')):
      name = label + '_coefficients.npy.gz'
      positions = fitting.basis(norms['stage1'], candidate, state)
      member = prefix + '/train/' + name
      need(train_manifest['files'][name] == r.maps['V4'][member], 'E_HEAD_MANIFEST_CONFLICT')
      desc = {'dtype': '<f8', 'shape': [len(positions)], 'order': 'C', 'file_sha256': train_manifest['files'][name]}
      coefficients = r.array('V4', member, desc, shape=(len(positions),), dtype='<f8')
      need(np.all(np.isfinite(coefficients)))
      heads[state] = {'positions': positions, 'coefficients': coefficients}
    model_receipt = r.metadata('V1', prefix + '/stage2/model/receipt.json', receipt_sha=reference['stage2']['model_receipt_sha256'])
    need(
      model_receipt['candidate_id'] == candidate
      and model_receipt['fold'] == fold
      and model_receipt['normalizer_sha256'] == reference['stage2']['normalizer_receipt_sha256']
    )
    desc = model_receipt['arrays']['coefficients']
    need(desc['array_sha256'] == reference['stage2']['coefficient_sha256'])
    coefficient = r.array('V1', prefix + '/stage2/model/coefficients.npy.gz', desc, shape=(len(norms['stage2']['effective']),), dtype='<f8')
    need(np.all(np.isfinite(coefficient)))
    return {'normalizer': norms['stage1'], 'heads': heads}, {'normalizer': norms['stage2'], 'coefficients': coefficient}

  def one_step(self, candidate, fold):
    index = decision.JOBS.index((candidate, fold))
    bound = self.bound_jobs[index]
    prefix = f'candidates/{candidate}/{fold}/one-step'
    receipt = self.reader.metadata('V4', prefix + '/receipt.json')
    need(
      receipt['schema'] == 'V4_DEVELOPMENT'
      and set(receipt['arrays']) == set(DEV_FIELDS)
      and receipt['anchor_sha256'] == bound['fields'][3]['anchor_sha256']
      and receipt['train_finalized_sha256'] == self.catalog[index]['train_finalized_sha256']
    )
    n = bound['fields'][3]['n']
    values = {}
    for field in DEV_FIELDS:
      desc = receipt['arrays'][field]
      dtype = '|b1' if field == 'predicted_gate' else '<i2' if field == 'projected_next_tick' else '<f8'
      if field in ('p_move', 'predicted_gate'):
        proof = bound['fields'][3 if field == 'p_move' else 4]['descriptor']
        need(all(desc[k] == proof[k] for k in ('file_sha256', 'npy_sha256', 'array_sha256')), 'E_B1_DEV_PIN_CONFLICT')
      values[field] = self.reader.array('V4', prefix + '/' + field + '.npy.gz', desc, shape=(n,), dtype=dtype)
    values['true_move'] = self.reader.old_field(bound['fields'][5])
    values['prior_delta_tick'] = self.reader.old_field(bound['fields'][6])
    return values

  def rollout(self, candidate, fold, horizon):
    self.reader.phase.require_dev()
    need(horizon in evaluation.HORIZONS)
    index = decision.JOBS.index((candidate, fold))
    prefix = f'candidates/{candidate}/{fold}/rollout-{horizon}'
    receipt = self.reader.metadata('V4', prefix + '/receipt.json')
    need(
      receipt['schema'] == 'V4_ROLLOUT'
      and set(receipt['arrays']) == set(ROLLOUT_FIELDS)
      and receipt['horizon'] == horizon
      and receipt['train_finalized_sha256'] == self.catalog[index]['train_finalized_sha256']
      and receipt['anchor_sha256'] == self.references[index]['rollout'][str(horizon)]['overall']['anchor_sha256']
    )
    values = {}
    n = receipt['arrays']['candidate_error']['shape'][0]
    for field in ROLLOUT_FIELDS:
      shape = (n, horizon + int(field == 'projected_path')) if field != 'candidate_error' else (n,)
      dtype = '<i2' if field == 'projected_path' else '|b1' if field == 'predicted_gate_path' else '<f8'
      values[field] = self.reader.array('V4', prefix + '/' + field + '.npy.gz', receipt['arrays'][field], shape=shape, dtype=dtype)
    return values
