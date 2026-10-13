"""V2 prediction-only authorization, immutable input lineage and D-only output."""

from contextlib import contextmanager, ExitStack
import gzip
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
from unittest.mock import patch

import numpy as np
from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_hurdle_attribution_io as verified
from openpilot.tools.cyber_autotune import empirical_hurdle_fit_cv_store as old
from openpilot.tools.cyber_autotune import empirical_hurdle_fit_cv_math as m
from openpilot.tools.cyber_autotune import empirical_hurdle_fit_cv_data as data
from openpilot.tools.cyber_autotune import empirical_hurdle_v2_execution_policy as policy

BASELINE = 'f203450ceea5a1d26bea0617fc7d8e097f2e63b3'
POLICY_SHA = 'b0f838bf1c981cc5f137416f1f6397398dd5c3c5867cfed3f649f1ccc815346e'
READY_SHA = '81e6a953589ec768e8194f5f503292b11796ff074165e7c3fc151d957a5ebc5f'
BLAS_SHA = '704bde2afe24c22d171cc7d2508517db81b7db455743b2cb0e5de9dda88da7a2'
RESERVE = 2 * 1024**3
METADATA_BUDGET = 128 * 1024**2
JOBS = verified.JOBS
read_json, digest, safe, member = verified.read_json, verified.digest, verified.safe, verified.member
write_json = old.write_json


def require(value, message='V2_SOURCE_IDENTITY_CONFLICT'):
  if not value:
    raise ValueError(message)


def forbidden(*args, **kwargs):
  raise ValueError('V2_REFIT_OR_UNAUTHORIZED_EXECUTION_FORBIDDEN')


@contextmanager
def firewall():
  from openpilot.tools.cyber_autotune import empirical_hurdle_fit_cv_execution as executor

  with ExitStack() as stack:
    for module, names in (
      (m, ('fit_stage1', 'fit_stage2', 'normalizer', 'newton', 'threshold')),
      (m.source, ('fit', 'normalizer')),
      (np.linalg, ('solve', 'lstsq', 'pinv')),
      (executor, ('execute_job', 'run')),
      (data, ('load_route',)),
    ):
      for name in names:
        stack.enter_context(patch.object(module, name, forbidden))
    for name in ('scipy.optimize', 'sklearn', 'openpilot.tools.lib.logreader'):
      stack.enter_context(patch.dict(sys.modules, {name: None}))
    yield


def sources():
  root = Path(__file__).parent
  names = [
    'empirical_hurdle_v2_io.py',
    'empirical_hurdle_v2_threshold.py',
    'empirical_hurdle_v2_execution.py',
    'empirical_hurdle_v2_publication.py',
    'empirical_hurdle_fit_cv_math.py',
    'empirical_hurdle_fit_cv_data.py',
    'empirical_hurdle_fit_cv_gates.py',
    'empirical_s2_ri_fit_cv_math.py',
    'empirical_hurdle_attribution_io.py',
    'empirical_hurdle_fit_cv_store.py',
    'empirical_identifiability_execution.py',
    'empirical_plant_policy.py',
  ]
  return {n: digest(root / n) for n in names}


def output_path(path, excluded=()):
  path = old.storage.external(path, excluded)
  require(path.is_relative_to(Path('/mnt/d')), 'V2_D_ONLY_OUTPUT_REQUIRED')
  return path


def headroom(path, required=0):
  path = output_path(path)
  parent = path
  while not parent.exists():
    parent = parent.parent
  require(parent.stat().st_dev == Path('/mnt/d').stat().st_dev, 'V2_D_BACKING_VOLUME_REQUIRED')
  require(shutil.disk_usage('/mnt/d').free >= required + RESERVE, 'HURDLE_STAGE1_V2_STORAGE_CAPACITY_BLOCKED')


def capacity(jobs):
  # All tick values are range-checked signed16, persisted losslessly as int16.
  # Use an incompressible gzip bound, not observed compression ratios.
  payload, peak = 0, 0
  for job in jobs:
    payload += job['train_count'] * 3 + job['one_step']['count'] * 27
    for h in m.HORIZONS:
      n = job['rollout'][str(h)]['overall']['count']
      payload += n * ((h + 1) * 2 + h + 8)
      peak = max(peak, n * (h + 1) * 2)
  bound = payload + payload // 100 + METADATA_BUDGET
  return {
    'run1_upper_bytes': bound,
    'run2_upper_bytes': bound,
    'atomic_upper_bytes': peak + peak // 100 + 65536,
    'safety_reserve_bytes': RESERVE,
    'estimate_basis': 'SIGNED16_LOSSLESS_PAYLOAD_PLUS_GZIP_OVERHEAD',
  }


def contracts():
  inputs = policy.load_inputs()
  execution = {policy.filename(k): read_json(p.PUBLIC / policy.filename(k)) for k in policy.LABELS}
  policy.validate(execution)
  require(execution[policy.filename('policy')]['receipt_sha256'] == POLICY_SHA, 'V2_POLICY_BINDING_CONFLICT')
  require(execution[policy.filename('readiness')]['receipt_sha256'] == READY_SHA, 'V2_POLICY_BINDING_CONFLICT')
  return inputs, execution


def metadata(source, causal, derived, output, *, remaining_runs=2):
  """Only JSON receipts/manifests and filesystem metadata; no array opens."""
  source, causal, derived = map(safe, (source, causal, derived))
  output_path(output, (source, causal, derived))
  inputs, execution = contracts()
  env = old.environment()
  require(env['blas_build_identity_sha256'] == BLAS_SHA, 'V2_EXECUTION_ENVIRONMENT_CONFLICT')
  historical = read_json(source / 'authorization.json', verified.AUTH_SHA)
  manifest = read_json(source / 'repeat-1/manifest.json', verified.SOURCE_SHA)
  repeat = read_json(source / 'repeatability.json', verified.REPEAT_SHA)
  require(manifest['authorization_sha256'] == verified.AUTH_SHA and manifest['job_count'] == 32)
  require(repeat['manifest_sha256'] == verified.SOURCE_SHA and repeat['all_file_hashes_equal'])
  input_pins = read_json(source / 'input-pins.json')
  require(input_pins['authorization_sha256'] == verified.AUTH_SHA)
  for kind in ('source', 'derived'):
    require(p.sha(p.canonical(input_pins[kind])) == historical[kind + '_file_set_sha256'])
  jobs = []
  for candidate, fold in JOBS:
    name = f'candidates/{candidate}/{fold}/receipt.json'
    path = source / 'repeat-1' / name
    require(digest(path) == manifest['files'][name])
    job = read_json(path)
    require((job['candidate_id'], job['fold']) == (candidate, fold) and job['status'] == 'EXECUTED_COMPLETE')
    for stage in ('stage1', 'stage2'):
      for kind in ('model', 'normalizer'):
        rel = f'candidates/{candidate}/{fold}/{stage}/{kind}/receipt.json'
        require(digest(source / 'repeat-1' / rel) == manifest['files'][rel])
        read_json(source / 'repeat-1' / rel, job[stage][kind + '_receipt_sha256'])
    jobs.append(job)
  pol = old.source_policy.policy()
  _, resolved, causal_manifest, records, _ = old.metadata.preflight(causal, pol)
  require(causal_manifest['receipt_sha256'] == historical['source_manifest_sha256'])
  require(resolved['final_dataset_status'] == 'RETROSPECTIVE_CAUSAL_TRAIN_DEV_DATASET_PARTIAL')
  index = read_json(derived / 'repeat-1/derived-index.json', historical['derived_index_sha256'])
  result = read_json(derived / 'repeat-1/results.json', historical['derived_result_sha256'])
  admission = read_json(derived / 'repeat-1/admission.json', result['admission_sha256'])
  require(admission['manifest_sha256'] == causal_manifest['receipt_sha256'])
  indexed = {s['content_sha256']: s['receipt_sha256'] for s in index['segments']}
  require(len(indexed) == len(records) == 154 and set(indexed) == {s['segment_sha256'] for _, s in records})
  require(not set(indexed).intersection(pol['excluded_qlog_content_sha256']), 'QLOG_SOURCE_FORBIDDEN')
  attached = []
  for base, segment in sorted(records, key=lambda pair: (pair[1]['route_id'], pair[1]['segment_sha256'])):
    root = derived / 'repeat-1/segments' / segment['segment_sha256']
    local = read_json(root / 'receipt.json', indexed[segment['segment_sha256']])
    require(local['source_receipt_sha256'] == segment['receipt_sha256'] and local['policy_sha256'] == pol['receipt_sha256'])
    attached.append((base, segment, root, local))
  estimate = capacity(jobs)
  require(remaining_runs in (1, 2))
  required = estimate['run1_upper_bytes'] * remaining_runs + estimate['atomic_upper_bytes']
  headroom(output, required)
  head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=p.PUBLIC, text=True).strip()
  subprocess.run(['git', 'merge-base', '--is-ancestor', BASELINE, head], cwd=p.PUBLIC, check=True)
  auth = p.seal(
    {
      'schema': 'EMPIRICAL_HURDLE_STAGE1_V2_RETROSPECTIVE_EXECUTION_AUTHORIZATION',
      'head': head,
      'execution_policy_sha256': POLICY_SHA,
      'execution_readiness_sha256': READY_SHA,
      'design_policy_sha256': inputs[policy.design.filename('policy')]['receipt_sha256'],
      'v1_manifest_sha256': verified.SOURCE_SHA,
      'v1_file_set_sha256': p.sha(p.canonical(manifest['files'])),
      'v1_authorization_sha256': verified.AUTH_SHA,
      'v1_repeatability_sha256': verified.REPEAT_SHA,
      'source_manifest_sha256': causal_manifest['receipt_sha256'],
      'derived_index_sha256': index['receipt_sha256'],
      'derived_result_sha256': result['receipt_sha256'],
      'source_file_set_sha256': historical['source_file_set_sha256'],
      'derived_file_set_sha256': historical['derived_file_set_sha256'],
      'jobs': [
        {'candidate_id': j['candidate_id'], 'fold': j['fold'], 'train_anchor_sha256': j['train_anchor_sha256'], 'stage1': j['stage1'], 'stage2': j['stage2']}
        for j in jobs
      ],
      'routes': pol['route_ids'],
      'qlog_deny_identities': sorted(pol['excluded_qlog_content_sha256']),
      'environment': env,
      'executor_sources': sources(),
      'root_identities': {k: p.sha(str(v).encode()) for k, v in (('v1', source), ('causal', causal), ('derived', derived), ('output', output))},
      'capacity_preflight': {**estimate, 'D_free_bytes': shutil.disk_usage('/mnt/d').free},
      'prediction_only_authorized': True,
      'stage1_fitting_authorized': False,
      'stage2_fitting_authorized': False,
      'normalizer_fitting_authorized': False,
      'train_only_threshold_authorized': True,
      'array_access_before_seal': False,
      'holdout': 'CLOSED',
      'opening_count': 0,
      'holdout_discovery': 0,
      'pooled_refit_authorized': False,
      'vehicle_authority': 'NONE',
    }
  )
  return auth, manifest, jobs, attached, input_pins, execution


def authorize(source, causal, derived, output):
  output = output_path(output, (source, causal, derived))
  require(not output.exists(), 'V2_NEW_IMMUTABLE_OUTPUT_REQUIRED')
  # Durable metadata-only permission before opening even private JSON receipts.
  preflight = p.seal(
    {
      'schema': 'V2_PRIVATE_METADATA_PREFLIGHT_AUTHORIZATION',
      'baseline': BASELINE,
      'source_manifest_sha256': verified.SOURCE_SHA,
      'execution_policy_sha256': POLICY_SHA,
      'numeric_access_authorized': False,
      'prediction_authorized': False,
      'fitting_authorized': False,
    }
  )
  write_json(output / 'metadata-authorization.json', preflight)
  auth, manifest, jobs, records, pins, _ = metadata(source, causal, derived, output)
  write_json(output / 'authorization.json', auth)
  write_json(output / 'source-pins.json', p.seal({'v1': manifest['files'], 'source': pins['source'], 'derived': pins['derived']}))
  write_json(output / 'source-jobs.json', p.seal({'jobs': jobs}))
  return auth, jobs, records


def validate_seal(auth):
  p.verify(auth)
  require(auth['schema'] == 'EMPIRICAL_HURDLE_STAGE1_V2_RETROSPECTIVE_EXECUTION_AUTHORIZATION')
  require(auth['prediction_only_authorized'] and not auth['array_access_before_seal'])
  require(all(auth[k] is False for k in ('stage1_fitting_authorized', 'stage2_fitting_authorized', 'normalizer_fitting_authorized')))
  require(auth['executor_sources'] == sources(), 'V2_EXECUTOR_SOURCE_DRIFT')


def verify_inputs(source, causal, derived, output, *, complete=False):
  auth = read_json(output / 'authorization.json')
  validate_seal(auth)
  actual_roots = {k: p.sha(str(safe(v)).encode()) for k, v in (('v1', source), ('causal', causal), ('derived', derived), ('output', output))}
  require(actual_roots == auth['root_identities'], 'V2_AUTHORIZED_ROOT_IDENTITY_CONFLICT')
  require(old.environment() == auth['environment'], 'V2_EXECUTION_ENVIRONMENT_CONFLICT')
  pins = read_json(output / 'source-pins.json')
  for key in ('v1', 'source', 'derived'):
    require(p.sha(p.canonical(pins[key])) == auth[key + '_file_set_sha256'], 'V2_SOURCE_PIN_SET_CONFLICT')
  if complete:
    for key, root in (('v1', source / 'repeat-1'), ('source', causal), ('derived', derived)):
      verified.verify_files(root, pins[key])
  # Before execution bind historical file hashes; each authorized numeric reader
  # verifies its file before decoding. Never pre-open DEVELOPMENT payloads.
  return auth


def load_route(records, route, auth):
  validate_seal(auth)
  require(route in auth['routes'])
  segments = []
  for base, segment, root, local in records:
    if segment['route_id'] != route:
      continue
    require(segment['segment_sha256'] not in auth['qlog_deny_identities'], 'QLOG_SOURCE_FORBIDDEN')
    d = {
      k: old.read.read_array(root / old.read.array_name(k), local['arrays'][k])
      for k in ('angle_tick', 'streak_all', 'model_eligible', 'rail', 's2_ri_causal_run_id', 'within_s2_ri_causal_run_index')
    }
    a = {
      k: old.read.read_array(base / 'arrays' / old.read.array_name(k), segment['arrays'][k]) for k in ('command.normalized', 'state.speed_mps', 'grid_time_ns')
    }
    continuity = np.r_[
      False,
      (np.diff(a['grid_time_ns']) == 10_000_000)
      & (d['s2_ri_causal_run_id'][1:] == d['s2_ri_causal_run_id'][:-1])
      & (d['within_s2_ri_causal_run_index'][1:] == d['within_s2_ri_causal_run_index'][:-1] + 1),
    ]
    eligible = d['model_eligible']
    index = np.arange(len(eligible))
    starts = eligible & (~continuity | np.r_[True, ~eligible[:-1]])
    origins = np.maximum.accumulate(np.where(starts, index, 0))
    expected = np.where(eligible, index - origins + 1, 0)
    require(np.array_equal(expected, d['streak_all']), 'V2_RATE_FREE_STREAK_CONFLICT')
    segments.append(
      {
        'route_id': route,
        'segment_sha256': segment['segment_sha256'],
        'tick': d['angle_tick'],
        'streak': d['streak_all'],
        'command': a['command.normalized'],
        'speed': a['state.speed_mps'],
        'rail': d['rail'],
        'eligible': eligible,
        'run': d['s2_ri_causal_run_id'],
        'within': d['within_s2_ri_causal_run_index'],
      }
    )
  return sorted(segments, key=lambda s: s['segment_sha256'])


def load_model(jobroot, stage, expected, auth):
  validate_seal(auth)
  model_root, norm_root = jobroot / stage / 'model', jobroot / stage / 'normalizer'
  receipt = read_json(model_root / 'receipt.json', expected['model_receipt_sha256'])
  norm = read_json(norm_root / 'receipt.json', expected['normalizer_receipt_sha256'])
  require(receipt['arrays']['coefficients']['array_sha256'] == expected['coefficient_sha256'], 'V2_V1_MODEL_IDENTITY_CONFLICT')
  require(receipt['normalizer_sha256'] == norm['receipt_sha256'], 'V2_V1_MODEL_IDENTITY_CONFLICT')
  arrays = {k: verified.load_array(norm_root, norm, k) for k in norm['arrays']}
  coeff = verified.load_array(model_root, receipt, 'coefficients')
  return {'normalizer': arrays, 'coefficients': coeff, 'effective_x_sha256': receipt['effective_x_sha256']}


def compact_ticks(array):
  require(array.dtype.kind in 'iu' and np.all((array >= -32768) & (array <= 32767)), 'V2_SIGNED16_RANGE_REQUIRED')
  return np.ascontiguousarray(array, dtype=np.int16)


def array_write(path, array):
  path = output_path(path)
  array = np.ascontiguousarray(array)
  require(not array.dtype.hasobject and not path.exists(), 'V2_IMMUTABLE_ARRAY_CONFLICT')
  headroom(path, array.nbytes + array.nbytes // 100 + 65536)
  path.parent.mkdir(parents=True, exist_ok=True)
  temporary = path.with_name(path.name + '.atomic')
  with temporary.open('xb') as stream:
    with gzip.GzipFile(fileobj=stream, mode='wb', filename='', mtime=0, compresslevel=1) as compressed:
      writer = old._HashedWriter(compressed)
      np.save(writer, array, allow_pickle=False)
    stream.flush()
    os.fsync(stream.fileno())
  check = hashlib.sha256()
  with gzip.open(temporary, 'rb') as decoded:
    for block in iter(lambda: decoded.read(1024**2), b''):
      check.update(block)
  require(check.hexdigest() == writer.sha.hexdigest(), 'V2_LOSSLESS_STORAGE_FAILURE')
  os.link(temporary, path)
  temporary.unlink()
  return {
    'dtype': array.dtype.str,
    'shape': list(array.shape),
    'order': 'C',
    'array_sha256': old.array_digest(array),
    'file_sha256': digest(path),
    'npy_sha256': check.hexdigest(),
    'storage_format': 'NPY_GZIP_V1',
    'filename': path.name,
    'lossless_roundtrip_verified': True,
  }


def population(path, arrays, body):
  saved = {k: array_write(path / (k + '.npy.gz'), v) for k, v in sorted(arrays.items())}
  receipt = p.seal({**body, 'arrays': saved})
  write_json(path / 'receipt.json', receipt)
  return receipt


def reference(job, population_name, receipt):
  return {
    'manifest_sha256': verified.SOURCE_SHA,
    'member': f"candidates/{job['candidate_id']}/{job['fold']}/{population_name}/receipt.json",
    'receipt_sha256': receipt['receipt_sha256'],
    'arrays': receipt['arrays'],
  }
