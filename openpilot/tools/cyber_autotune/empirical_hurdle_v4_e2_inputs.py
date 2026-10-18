"""E2 role-bound exact member reader; legacy E1/B0/B1 readers are unchanged."""

from contextlib import contextmanager
import numpy as np
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e_inputs as e1
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_decision as decision

need = decision.need
MAX_INPUT_OPENS = 3000  # <=E1 2989 original members; E1 aggregate comparison is separate.
MAX_INPUT_BYTES = e1.MAX_INPUT_BYTES
NORMALIZER_FIELDS = e1.NORMALIZER_FIELDS


def member_allowed(owner, member, kind):
  e1.member_allowed(owner, member, kind)
  if '/rollout-' in member:
    need(member.endswith(('/receipt.json', '/candidate_error.npy.gz')), 'E2_D0_ROLLOUT_PAYLOAD_NOT_NEEDED')


class Phase:
  def __init__(self):
    self.job = None
    self.loading_source = False
    self.train_sha256 = None
    self.qualified = []

  def qualify(self, candidate, fold):
    need(
      self.train_sha256 is None and len(self.qualified) < len(decision.JOBS) and (candidate, fold) == decision.JOBS[len(self.qualified)],
      'E2_TRAIN_QUALIFICATION_ORDER',
    )
    self.qualified.append((candidate, fold))

  def require_selection(self):
    need(tuple(self.qualified) == decision.JOBS, 'E2_ALL32_QUALIFICATION_PASS_BEFORE_SELECTION')

  def unlock(self, records, raw_digest, verified_digest):
    self.require_selection()
    need(self.train_sha256 is None and raw_digest == verified_digest, 'E2_DURABLE_TRAIN_READBACK_CONFLICT')
    need(tuple((j['candidate_id'], j['fold']) for j in records) == decision.JOBS)
    need(all(set(j['contexts']) == set(decision.CONTEXTS) and type(j['count']) is int and j['count'] > 0 for j in records))
    for job in records:
      need(sum(c['count'] for c in job['contexts'].values()) == job['count'])
      for context in job['contexts'].values():
        need(type(context['decision']) is float and np.isfinite(context['decision']) and 0 <= context['decision'] <= 1)
        need(context['positive'] > 0 and context['negative'] > 0 and context['positive'] + context['negative'] == context['count'])
        need(set(context['guards']) == {'TRUE_MOVE_TP', 'TRUE_MOVE_SSE', 'TRUE_MOVE_SAE', 'HARMFUL_STATIC'})
    need(all(c['witness_verified'] and all(c['guards'].values()) for j in records for c in j['contexts'].values()))
    self.train_sha256 = raw_digest

  def require_dev(self):
    need(self.train_sha256 is not None, 'E2_DEV_BEFORE_ALL64_DURABLE_DECISIONS')

  @contextmanager
  def source(self):
    need(not self.loading_source)
    self.loading_source = True
    try:
      yield
    finally:
      self.loading_source = False

  def authorize(self, owner, member, kind):
    if (owner in ('V4', 'V1') and member == 'manifest.json') or owner == 'V1_TOP':
      return
    if self.train_sha256 is not None:
      return
    if owner in ('CAUSAL', 'DERIVED'):
      need(self.loading_source, 'E2_SOURCE_ROLE_CAPABILITY_REQUIRED')
      return
    need(self.job in decision.JOBS and member.startswith('candidates/' + '/'.join(self.job) + '/'), 'E2_CURRENT_TRAIN_JOB_REQUIRED')
    tail = '/'.join(member.split('/')[3:])
    allowed = owner == 'V4' and tail in ('train/combined_probability.npy.gz', 'train/manifest.json', 'train-finalized.json')
    train_v1 = ('train/move_label.npy.gz', 'train/prior_delta_tick.npy.gz', 'stage2/model/receipt.json', 'stage2/model/coefficients.npy.gz')
    allowed |= owner == 'V1' and (
      tail in train_v1 or tail == 'stage2/normalizer/receipt.json' or tail in ('stage2/normalizer/' + f + '.npy.gz' for f in NORMALIZER_FIELDS)
    )
    need(allowed, 'E2_DEV_OR_UNAPPROVED_FIELD_BEFORE_TRAIN_SEAL')


class Reader(e1.Reader):
  def metadata(self, owner, member, *, raw_sha=None, receipt_sha=None):
    member_allowed(owner, member, 'metadata')
    self.phase.authorize(owner, member, 'metadata')
    return super().metadata(owner, member, raw_sha=raw_sha, receipt_sha=receipt_sha)

  def raw(self, owner, member, kind, expected_raw, cap):
    member_allowed(owner, member, kind)
    self.phase.authorize(owner, member, kind)
    path = str(self.roots[owner] / member)
    named_bootstrap = kind == 'metadata' and owner == 'V1_TOP' and member in ('authorization.json', 'input-pins.json')
    need(path not in self.used and (e1.b0._digest(expected_raw) or (expected_raw is None and named_bootstrap)), 'E_DUPLICATE_OR_HASH_BINDING_CONFLICT')
    need(len(self.events) < MAX_INPUT_OPENS and sum(e['bytes_read'] for e in self.events) + cap <= MAX_INPUT_BYTES, 'E_INPUT_RESOURCE_BOUND')
    self.used.add(path)
    with e1.b1.GuardedReader(self.mount_root, self.mount_identity, {path: (cap, kind)}) as reader:
      try:
        raw = reader.read(path, cap, kind)
        need(not self.inodes.intersection(reader.inodes), 'E_ALIAS_CONFLICT')
        self.inodes.update(reader.inodes)
      finally:
        self.events.extend({'owner': owner, **e} for e in reader.events)
    need(expected_raw is None or e1.evaluation.sha(raw) == expected_raw, 'E_MANIFEST_MEMBER_HASH_CONFLICT')
    return raw


class Provider(e1.Provider):
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.stage2_cache = {}

  def admit_train_sources(self):
    need(self.segments is None)
    with self.reader.phase.source():
      self._read_train_source_members()

  def _read_train_source_members(self):
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
        need(e1.b0._digest(route) and e1.b0._digest(identity))
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
        need(type(n) is int and 0 < n <= e1.MAX_SOURCE_ROWS)
        total += n
        need(total <= e1.MAX_SOURCE_ROWS, 'E_FROZEN_SOURCE_TOTAL_ROW_BOUND')
        arrays = {}
        sources = (('CAUSAL', source_prefix + '/arrays', source, e1.CAUSAL_FIELDS), ('DERIVED', derived_prefix, derived, e1.DERIVED_FIELDS))
        for owner, prefix, row, fields in sources:
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

  def train_blocks(self, index):
    need(self.reader.phase.train_sha256 is None and self.reader.phase.job == decision.JOBS[index])
    candidate, fold = decision.JOBS[index]
    reference = self.references[index]
    need((candidate, fold) == (reference['candidate_id'], reference['fold']))
    segments = sorted((s for s in self.segments if s['route_id'] == reference['train_route']), key=lambda s: s['segment_sha256'])
    need(bool(segments), 'E2_TRAIN_ROUTE_MISSING')
    blocks, anchor, n = e1.evaluation.data.binding(segments, candidate, 1)
    need(
      anchor == reference['train_anchor_sha256'] == self.bound_jobs[index]['fields'][0]['anchor_sha256'] and n == reference['train_count'],
      'E2_TRAIN_ORDERED_ANCHOR_CONFLICT',
    )
    for segment, ix in blocks:
      need(
        bool(np.all(segment['run'][ix] == segment['run'][ix + 1])) and bool(np.all(segment['within'][ix + 1] - segment['within'][ix] == 1)),
        'E2_TRAIN_SEGMENT_BOUNDARY_CONFLICT',
      )
    return blocks, anchor, n

  def normalizer(self, index, stage):
    r, reference = self.reader, self.references[index]
    candidate, fold = decision.JOBS[index]
    _, length = e1.evaluation.frozen.m.parameters(candidate)
    dim = 2 * length + 3
    prefix = f'candidates/{candidate}/{fold}/{stage}/normalizer'
    receipt = r.metadata('V1', prefix + '/receipt.json', receipt_sha=reference[stage]['normalizer_receipt_sha256'])
    need(receipt['candidate_id'] == candidate and receipt['fold'] == fold and receipt['stage'] == stage.upper())
    need(set(receipt['arrays']) == set(NORMALIZER_FIELDS))
    norm = {}
    for field in NORMALIZER_FIELDS:
      desc = receipt['arrays'][field]
      n = desc['shape'][0]
      need(0 < n <= dim and (field == 'effective' or n == dim))
      dtype = '|b1' if field == 'constant' else '<i8' if field == 'effective' else '<f8'
      norm[field] = r.array('V1', prefix + '/' + field + '.npy.gz', desc, shape=(n,), dtype=dtype)
    e1.evaluation.frozen.f.validate_normalizer(norm, candidate)
    return norm

  def stage2(self, index):
    need(index not in self.stage2_cache, 'E2_STAGE2_DUPLICATE_LOAD')
    candidate, fold = decision.JOBS[index]
    reference = self.references[index]
    need(self.catalog[index]['v1_stage2_receipts_sha256'] == e1.evaluation.sha(e1.evaluation.canonical(reference['stage2'])))
    norm = self.normalizer(index, 'stage2')
    prefix = f'candidates/{candidate}/{fold}/stage2/model'
    row = self.reader.metadata('V1', prefix + '/receipt.json', receipt_sha=reference['stage2']['model_receipt_sha256'])
    need(row['candidate_id'] == candidate and row['fold'] == fold and row['normalizer_sha256'] == reference['stage2']['normalizer_receipt_sha256'])
    desc = row['arrays']['coefficients']
    need(desc['array_sha256'] == reference['stage2']['coefficient_sha256'])
    coeff = self.reader.array('V1', prefix + '/coefficients.npy.gz', desc, shape=(len(norm['effective']),), dtype='<f8')
    need(bool(np.all(np.isfinite(coeff))))
    result = {'normalizer': norm, 'coefficients': coeff}
    self.stage2_cache[index] = result
    return result

  def models(self, index):
    self.reader.phase.require_dev()
    candidate, fold = decision.JOBS[index]
    public, reference = self.catalog[index], self.references[index]
    norm = self.normalizer(index, 'stage1')
    need(public['v1_stage1_normalizer_receipt_sha256'] == reference['stage1']['normalizer_receipt_sha256'])
    _, length = e1.evaluation.frozen.m.parameters(candidate)
    need(not np.any(norm['constant']) and np.array_equal(norm['effective'], np.arange(2 * length + 3)))
    prefix = f'candidates/{candidate}/{fold}'
    manifest = self.reader.metadata('V4', prefix + '/train/manifest.json', receipt_sha=public['train_manifest_sha256'])
    finalized = self.reader.metadata('V4', prefix + '/train-finalized.json', receipt_sha=public['train_finalized_sha256'])
    need(
      finalized['candidate_id'] == candidate
      and finalized['fold'] == fold
      and finalized['status'] == 'TRAIN_COMPLETE'
      and finalized['authorization_sha256'] == self.v4_auth['authorization_sha256']
      and finalized['train_anchor_sha256'] == public['train_anchor_sha256']
      and finalized['train_manifest_sha256'] == manifest['receipt_sha256']
      and finalized['model_threshold_receipt_sha256'] == manifest['train_receipt_sha256'] == public['train_receipt_sha256'],
      'E2_TRAIN_MODEL_CHAIN_CONFLICT',
    )
    heads = {}
    for state, label in enumerate(('STATIC', 'MOVE')):
      positions = e1.evaluation.frozen.f.basis(norm, candidate, state)
      name = label + '_coefficients.npy.gz'
      member = prefix + '/train/' + name
      need(manifest['files'][name] == self.reader.maps['V4'][member])
      desc = {'dtype': '<f8', 'shape': [len(positions)], 'order': 'C', 'file_sha256': manifest['files'][name]}
      coeff = self.reader.array('V4', member, desc, shape=(len(positions),), dtype='<f8')
      need(bool(np.all(np.isfinite(coeff))))
      heads[state] = {'positions': positions, 'coefficients': coeff}
    return {'normalizer': norm, 'heads': heads}, self.stage2_cache[index]

  def baseline_error(self, candidate, fold, horizon):
    self.reader.phase.require_dev()
    need(horizon in e1.evaluation.HORIZONS)
    index = decision.JOBS.index((candidate, fold))
    prefix = f'candidates/{candidate}/{fold}/rollout-{horizon}'
    row = self.reader.metadata('V4', prefix + '/receipt.json')
    need(row['schema'] == 'V4_ROLLOUT' and row['horizon'] == horizon and row['train_finalized_sha256'] == self.catalog[index]['train_finalized_sha256'])
    expected = self.references[index]['rollout'][str(horizon)]['overall']
    need(row['anchor_sha256'] == expected['anchor_sha256'])
    desc = row['arrays']['candidate_error']
    return self.reader.array('V4', prefix + '/candidate_error.npy.gz', desc, shape=(expected['count'],), dtype='<f8')
