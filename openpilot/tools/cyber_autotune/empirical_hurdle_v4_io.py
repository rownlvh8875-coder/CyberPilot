"""Manifest-bound V4 metadata and numeric readers. No root discovery or rebuilding."""

from contextlib import contextmanager, ExitStack
from unittest.mock import patch
import numpy as np

from openpilot.tools.cyber_autotune import empirical_hurdle_v4_authorization as a
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_fitting_policy as f

old = a.prior
p = a.p


def admit_metadata(roots, auth, pack):
  """Called only after external auth/storage/environment preflight; JSON only."""
  source, causal, derived = (roots[k] for k in ('source', 'causal', 'derived'))
  original = old.read_json(source / 'authorization.json', old.verified.AUTH_SHA)
  manifest = old.read_json(source / 'repeat-1/manifest.json', old.verified.SOURCE_SHA)
  repeat = old.read_json(source / 'repeatability.json', old.verified.REPEAT_SHA)
  a.need(manifest['authorization_sha256'] == old.verified.AUTH_SHA and manifest['job_count'] == 32)
  a.need(repeat['manifest_sha256'] == old.verified.SOURCE_SHA and repeat['all_file_hashes_equal'] is True)
  pins = old.read_json(source / 'input-pins.json')
  a.need(pins['authorization_sha256'] == old.verified.AUTH_SHA)
  for key, root in (('source', causal), ('derived', derived)):
    a.need(p.sha(p.canonical(pins[key])) == original[key + '_file_set_sha256'])
    for name in pins[key]:
      old.member(root, name)  # Validate member grammar before any member access.
  source_policy = old.contracts()['source_policy']  # Public frozen causal contract.
  _, resolved, causal_manifest, records, _ = old.legacy.old.metadata.preflight(causal, source_policy)
  a.need(resolved['final_dataset_status'] == 'RETROSPECTIVE_CAUSAL_TRAIN_DEV_DATASET_PARTIAL')
  index = old.read_json(derived / 'repeat-1/derived-index.json', original['derived_index_sha256'])
  result = old.read_json(derived / 'repeat-1/results.json', original['derived_result_sha256'])
  admission = old.read_json(derived / 'repeat-1/admission.json', result['admission_sha256'])
  a.need(admission['manifest_sha256'] == causal_manifest['receipt_sha256'])
  identities = {
    'causal': causal_manifest['receipt_sha256'],
    'derived_index': index['receipt_sha256'],
    'derived_result': result['receipt_sha256'],
    'source_file_set': original['source_file_set_sha256'],
    'derived_file_set': original['derived_file_set_sha256'],
    'v1_file_set': p.sha(p.canonical(manifest['files'])),
  }
  a.need(identities == auth['source_manifests'] and causal_manifest['receipt_sha256'] == original['source_manifest_sha256'])
  indexed = {s['content_sha256']: s['receipt_sha256'] for s in index['segments']}
  a.need(len(indexed) == len(records) == 154 and set(indexed) == {s['segment_sha256'] for _, s in records})
  a.need(not set(indexed).intersection(source_policy['excluded_qlog_content_sha256']))
  attached = []
  for base, segment in sorted(records, key=lambda row: (row[1]['route_id'], row[1]['segment_sha256'])):
    root = derived / 'repeat-1/segments' / segment['segment_sha256']
    local = old.read_json(root / 'receipt.json', indexed[segment['segment_sha256']])
    a.need(local['source_receipt_sha256'] == segment['receipt_sha256'] and local['policy_sha256'] == source_policy['receipt_sha256'])
    attached.append((base, segment, root, local))
  jobs, receipts = [], {}
  for public in pack['jobs']:
    prefix = f"candidates/{public['candidate_id']}/{public['fold']}"
    job = old.metadata_member(source / 'repeat-1', prefix + '/receipt.json', manifest['files'], public['receipt_sha256'])
    a.need(job == public or old.job_identity(job) == old.job_identity(public), 'V4_SOURCE_IDENTITY_CONFLICT')
    a.need(job['status'] == 'EXECUTED_COMPLETE')
    for stage in ('stage1', 'stage2'):
      models = {}
      for kind in ('model', 'normalizer'):
        name = prefix + f'/{stage}/{kind}/receipt.json'
        row = old.metadata_member(source / 'repeat-1', name, manifest['files'], job[stage][kind + '_receipt_sha256'])
        for binding in row['arrays'].values():
          relative = prefix + f'/{stage}/{kind}/' + binding['filename']
          old.member(source / 'repeat-1', relative)
          a.need(manifest['files'].get(relative) == binding['file_sha256'], 'V4_MODEL_IDENTITY_CONFLICT')
        models[kind] = row
      a.need(
        models['model']['normalizer_sha256'] == models['normalizer']['receipt_sha256']
        and models['model']['arrays']['coefficients']['array_sha256'] == job[stage]['coefficient_sha256'],
        'V4_MODEL_IDENTITY_CONFLICT',
      )
      receipts[public['candidate_id'], public['fold'], stage] = models
    jobs.append(job)
  lineage = {
    'jobs': jobs,
    'records': tuple(attached),
    'source_policy': source_policy,
    'pins': {'v1': manifest['files'], 'causal': pins['source'], 'derived': pins['derived']},
    'receipts': receipts,
    'record_sha256': old.records_identity(attached),
  }
  metadata_names = {
    'source': ('authorization.json', 'repeat-1/manifest.json', 'repeatability.json', 'input-pins.json'),
    'causal': ('authorization.json', 'repeat-1/manifest.json'),
    'derived': ('repeat-1/derived-index.json', 'repeat-1/results.json', 'repeat-1/admission.json'),
  }
  lineage['metadata_pins'] = {key: {name: old.digest(old.member(roots[key], name)) for name in names} for key, names in metadata_names.items()}
  # Opaque full manifest-bound byte validation before any numerical decoding.
  for key, root in (('v1', source / 'repeat-1'), ('causal', causal), ('derived', derived)):
    old.verified.verify_files(root, lineage['pins'][key])
  return lineage


def job_valid(permit, job):
  a.valid(permit)
  a.need(old.records_identity(permit.lineage['records']) == permit.lineage['record_sha256'], 'V4_SOURCE_IDENTITY_CONFLICT')
  position = old.JOBS.index((job['candidate_id'], job['fold']))
  a.need(job == permit.lineage['jobs'][position], 'V4_ANCHOR_IDENTITY_CONFLICT')
  return f"candidates/{job['candidate_id']}/{job['fold']}"


def load_models(permit, job):
  prefix = job_valid(permit, job)
  source = permit.roots['source'] / 'repeat-1'
  out = {}
  for stage in ('stage1', 'stage2'):
    receipts = permit.lineage['receipts'][job['candidate_id'], job['fold'], stage]
    norm = {}
    for key in receipts['normalizer']['arrays']:
      a.valid(permit)
      norm[key] = old.decode_bound_array(source / prefix / stage / 'normalizer', receipts['normalizer'], key, 'V4_NORMALIZER_IDENTITY_CONFLICT')
    for array in norm.values():
      array.flags.writeable = False
    out[stage] = {'normalizer': norm, 'normalizer_receipt_sha256': receipts['normalizer']['receipt_sha256']}
    if stage == 'stage2':
      a.valid(permit)
      out[stage]['coefficients'] = old.decode_bound_array(source / prefix / stage / 'model', receipts['model'], 'coefficients', 'V4_MODEL_IDENTITY_CONFLICT')
  out['stage2']['coefficients'].flags.writeable = False
  p_dim = f.validate_normalizer(out['stage1']['normalizer'], job['candidate_id'])
  norm = out['stage1']['normalizer']
  a.need(np.array_equal(norm['effective'], np.arange(p_dim)) and not np.any(norm['constant']), 'V4_NORMALIZER_IDENTITY_CONFLICT')
  return out


def finalized(permit, job, receipt):
  prefix = job_valid(permit, job)
  p.verify(receipt)
  a.need(
    receipt['schema'] == 'V4_TRAIN_FINALIZED'
    and receipt['status'] == 'TRAIN_COMPLETE'
    and receipt['authorization_sha256'] == permit.trusted_sha256
    and receipt['train_anchor_sha256'] == job['train_anchor_sha256']
    and (receipt['candidate_id'], receipt['fold']) == (job['candidate_id'], job['fold']),
    'V4_TRAIN_FINALIZATION_REQUIRED',
  )
  root = permit.roots['output'] / permit.replica / prefix
  from openpilot.tools.cyber_autotune import empirical_hurdle_v4_store as store

  saved = store.verify(root / 'train', receipt['train_manifest_sha256'])
  a.need(saved['train_receipt_sha256'] == receipt['model_threshold_receipt_sha256'], 'V4_TRAIN_FINALIZATION_REQUIRED')
  a.need(old.read_json(root / 'train-finalized.json', receipt['receipt_sha256']) == receipt, 'V4_TRAIN_FINALIZATION_REQUIRED')


def load_route(permit, job, *, development=False, receipt=None):
  job_valid(permit, job)
  if development:
    finalized(permit, job, receipt)
  a.valid(permit)
  # Internal read adapter conveys the already-admitted capability to the old
  # immutable numerical reader. It is not an external trusted authorization.
  policy = permit.lineage['source_policy']
  adapter = p.seal(
    {
      'schema': 'EMPIRICAL_HURDLE_STAGE1_V2_RETROSPECTIVE_EXECUTION_AUTHORIZATION',
      'prediction_only_authorized': True,
      'array_access_before_seal': False,
      'stage1_fitting_authorized': False,
      'stage2_fitting_authorized': False,
      'normalizer_fitting_authorized': False,
      'executor_sources': old.legacy.sources(),
      'routes': policy['route_ids'],
      'qlog_deny_identities': sorted(policy['excluded_qlog_content_sha256']),
    }
  )
  route = job['development_route'] if development else job['train_route']
  return old.legacy.load_route(permit.lineage['records'], route, adapter)


def immutability(permit):
  a.valid(permit)
  for key, files in permit.lineage['metadata_pins'].items():
    for name, expected in files.items():
      a.need(old.digest(old.member(permit.roots[key], name)) == expected, 'V4_SOURCE_IMMUTABILITY_FAILURE')
  old.read_json(permit.roots['source'] / 'repeat-1/manifest.json', old.verified.SOURCE_SHA)
  for key, root in (('v1', permit.roots['source'] / 'repeat-1'), ('causal', permit.roots['causal']), ('derived', permit.roots['derived'])):
    old.verified.verify_files(root, permit.lineage['pins'][key])
  old.read_json(permit.roots['source'] / 'authorization.json', old.verified.AUTH_SHA)
  old.read_json(permit.roots['source'] / 'repeatability.json', old.verified.REPEAT_SHA)
  return {'source_writes': 0, 'source_bytes_unchanged': True}


def forbidden(*args, **kwargs):
  raise ValueError('V4_FORBIDDEN_OPERATION')


@contextmanager
def firewall():
  from openpilot.tools.cyber_autotune import empirical_s2_ri_fit_cv_math as s2

  with ExitStack() as stack:
    for module, names in ((f.old, ('fit_stage1', 'fit_stage2', 'normalizer')), (s2, ('fit', 'normalizer'))):
      for name in names:
        if hasattr(module, name):
          stack.enter_context(patch.object(module, name, forbidden))
    yield
