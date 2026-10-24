"""Pinned, read-only compressed evidence admission and small immutable outputs."""

from contextlib import contextmanager, ExitStack
import gzip
import hashlib
import json
from pathlib import Path
import sys
from unittest.mock import patch

import numpy as np
from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune.empirical_hurdle_attribution_math import require

SOURCE_SHA = 'c4de3955c12cd0d9721d4c7c1519da53b4d80f80be0c05e142047853a7b217a6'
REPEAT_SHA = '3b9e8e1f562972268a7a0543f72d3f98fe237a9f3e1c5e045b69e19f9c69949b'
AUTH_SHA = 'e4eeaca2f891cc9fdb1370b7ae735d963287af6c09cca85dc689c8e9c560c6ea'
BASELINE = 'f5ed849bd27287084efc81ba3dd0275ebfc5ca0a'
CANDIDATES = tuple(f'HRI_D{d:02d}_L{length:02d}' for d in (0, 5, 10, 20) for length in (1, 5, 15, 45))
JOBS = tuple((c, f) for c in CANDIDATES for f in ('FOLD_A', 'FOLD_B'))
HORIZONS = (25, 50, 100, 200)
PUBLIC_PINS = {
  'fit-cv-authorization': 'd93d6bb418a958b998c0308e4ce71a605a4069286029b5539d80b38001a34c6b',
  'fit-cv-job-manifest': 'b13b25f1f5c0f37d8465a24472e126c8f7f1d221643d5411dcf047996f9a7fe0',
  'fit-cv-results': '8d7c45a7a97f73918f927b19b0004c309078239b8b8523e1beac08fa6c53f5c4',
  'stage1-results': 'a3a2eb82e70109c9db38d81a07d3147087494f5927eeb540d54f4a2c6abf24be',
  'threshold-results': '543dc8a06914d9ef5baaf9da73254429dba200c207310252a1b522ea6d16b389',
  'stage2-diagnostics': 'fa7f76fa93c19f77d038ea1f5dadfa786e78ac28bac793ff1c749bcdc4ca7b98',
  'candidate-gates': 'e18ba4ad15e48f8aac860a3366fbb71786de3ef34548f92d2c95c409dc7e4fb4',
  'selection-result': 'cac341f353befbf014726df964009525484e938abc1b5a5dc6d5de4e5a7a6df8',
  'fit-cv-repeatability': '60c262b004f253f6de203404520f9edc8ab3d78c0dba51948dd62759003f35dc',
  'fit-cv-readiness': 'e00c9da0992fed899e77f9833d0ad04f333acc086e59846644ec164945b06861',
  'fit-cv-validation': '340cc48499dc7def91e8fa71f4d7202cd0239e455bedca4bc1f1eb69c9cd2004',
}


def safe(path):
  path = Path(path)
  require(path.is_absolute() and '..' not in path.parts, 'HURDLE_ATTRIBUTION_UNSAFE_PATH')
  for item in (path, *path.parents):
    require(not item.is_symlink(), 'HURDLE_ATTRIBUTION_SYMLINK_FORBIDDEN')
  return path


def member(root, name):
  require(
    isinstance(name, str) and not Path(name).is_absolute() and '..' not in Path(name).parts and '\\' not in name and ':' not in name,
    'HURDLE_ATTRIBUTION_UNSAFE_MEMBER',
  )
  return safe(safe(root) / name)


def digest(path):
  with safe(path).open('rb') as stream:
    return hashlib.file_digest(stream, 'sha256').hexdigest()


def read_json(path, expected=None):
  value = p.verify(json.loads(safe(path).read_bytes()))
  require(expected is None or value['receipt_sha256'] == expected, 'HURDLE_ATTRIBUTION_INPUT_CONFLICT')
  return value


def write_json(path, value):
  safe(path)
  p.persist(path, value)


def verify_files(root, files):
  root = safe(root)
  checked = set()
  for name, expected in files.items():
    relative = Path(name)
    require(not relative.is_absolute() and '..' not in relative.parts and ':' not in name and chr(92) not in name, 'HURDLE_ATTRIBUTION_UNSAFE_MEMBER')
    path = root
    for component in relative.parts:
      path = path / component
      if path not in checked:
        require(not path.is_symlink(), 'HURDLE_ATTRIBUTION_SYMLINK_FORBIDDEN')
        checked.add(path)
    with path.open('rb') as stream:
      actual = hashlib.file_digest(stream, 'sha256').hexdigest()
    require(actual == expected, 'HURDLE_ATTRIBUTION_INPUT_CONFLICT')
  return p.sha(p.canonical(files))


class HashedReader:
  def __init__(self, stream):
    self.stream, self.sha = stream, hashlib.sha256()

  def read(self, n=-1):
    data = self.stream.read(n)
    self.sha.update(data)
    return data


def header(stream, receipt):
  version = np.lib.format.read_magic(stream)
  require(version in ((1, 0), (2, 0)), 'HURDLE_ATTRIBUTION_NPY_CONFLICT')
  reader = np.lib.format.read_array_header_1_0 if version == (1, 0) else np.lib.format.read_array_header_2_0
  shape, fortran, dtype = reader(stream)
  require(
    not dtype.hasobject
    and not fortran
    and receipt['order'] == 'C'
    and list(shape) == receipt['shape']
    and dtype.str == receipt['dtype']
    and len(shape) in (1, 2)
    and all(type(s) is int and s >= 0 for s in shape),
    'HURDLE_ATTRIBUTION_NPY_CONFLICT',
  )
  return shape, dtype


def array_chunks(path, receipt, chunk=512):
  """First verify full decoded NPY and raw content; then yield bounded read-only rows."""
  require(
    receipt['storage_format'] == 'NPY_GZIP_V1' and receipt['lossless_roundtrip_verified'] and digest(path) == receipt['file_sha256'],
    'HURDLE_ATTRIBUTION_COMPRESSED_CONFLICT',
  )
  with gzip.open(safe(path), 'rb') as stream:
    reader = HashedReader(stream)
    shape, dtype = header(reader, receipt)
    raw_hash, size = hashlib.sha256(), 0
    for data in iter(lambda: reader.read(1024**2), b''):
      raw_hash.update(data)
      size += len(data)
    require(
      size == int(np.prod(shape)) * dtype.itemsize and raw_hash.hexdigest() == receipt['array_sha256'] and reader.sha.hexdigest() == receipt['npy_sha256'],
      'HURDLE_ATTRIBUTION_DECODED_CONFLICT',
    )
  width = int(np.prod(shape[1:])) * dtype.itemsize
  with gzip.open(safe(path), 'rb') as stream:
    header(stream, receipt)
    for start in range(0, shape[0], chunk):
      rows = min(chunk, shape[0] - start)
      data = stream.read(rows * width)
      require(len(data) == rows * width, 'HURDLE_ATTRIBUTION_TRUNCATED_ARRAY')
      array = np.frombuffer(data, dtype=dtype).reshape((rows, *shape[1:]))
      require(array.flags.c_contiguous)
      yield array
    require(not stream.read(1), 'HURDLE_ATTRIBUTION_TRAILING_BYTES')


def load_array(root, receipt, key):
  require(key in receipt['arrays'], 'HURDLE_ATTRIBUTION_INPUT_INSUFFICIENT')
  binding = receipt['arrays'][key]
  chunks = list(array_chunks(member(root, binding['filename']), binding))
  return np.concatenate(chunks) if chunks else np.empty(binding['shape'], dtype=binding['dtype'])


def public_inputs():
  result = {k: read_json(p.PUBLIC / f'empirical-hurdle-{k}-v1.json', v) for k, v in PUBLIC_PINS.items()}
  ready = result['fit-cv-readiness']
  require(
    ready['status'] == 'HURDLE_RETROSPECTIVE_FIT_AND_CV_COMPLETE'
    and ready['private_manifest_sha256'] == SOURCE_SHA
    and 'HURDLE_NO_ADMISSIBLE_CANDIDATE' in ready['states']
    and ready['opening_count'] == 0,
    'HURDLE_ATTRIBUTION_INPUT_NOT_READY',
  )
  require([(j['candidate_id'], j['fold']) for j in result['fit-cv-results']['jobs']] == list(JOBS), 'HURDLE_ATTRIBUTION_JOB_SET_CONFLICT')
  return result


def admit(root):
  root = safe(root)
  manifest = read_json(root / 'repeat-1/manifest.json', SOURCE_SHA)
  repeated = read_json(root / 'repeatability.json', REPEAT_SHA)
  authorization = read_json(root / 'authorization.json', AUTH_SHA)
  require(
    manifest['job_count'] == 32
    and manifest['authorization_sha256'] == AUTH_SHA
    and repeated['manifest_sha256'] == SOURCE_SHA
    and repeated['all_file_hashes_equal']
  )
  files = manifest['files']
  require(len(files) == 5250, 'HURDLE_ATTRIBUTION_INPUT_INSUFFICIENT')
  verify_files(root / 'repeat-1', files)
  public = public_inputs()
  jobs = []
  for (candidate, fold), published in zip(JOBS, public['fit-cv-results']['jobs'], strict=True):
    name = f'candidates/{candidate}/{fold}'
    local = root / 'repeat-1' / name
    manifest_job = read_json(local / 'manifest.json')
    job = read_json(local / 'receipt.json', manifest_job['receipt_sha256_binding'])
    require(
      job['candidate_id'] == candidate
      and job['fold'] == fold
      and job['status'] == 'EXECUTED_COMPLETE'
      and not job['failures']
      and job['authorization_sha256'] == AUTH_SHA,
      'HURDLE_ATTRIBUTION_JOB_SET_CONFLICT',
    )
    for key, val in published.items():
      require(job.get(key) == val, 'HURDLE_ATTRIBUTION_HISTORICAL_RECONCILIATION_FAILURE')
    require(all(files.get(name + '/' + k) == v for k, v in manifest_job['files'].items()))
    populations = {}
    for label in ('one-step', *(f'rollout-{h}' for h in HORIZONS)):
      pop = read_json(local / label / 'receipt.json', job['population_receipts'][label])
      require(pop['candidate_id'] == candidate and pop['fold'] == fold)
      for binding in pop['arrays'].values():
        require(files.get(f'{name}/{label}/{binding["filename"]}') == binding['file_sha256'])
        member(local / label, binding['filename'])
      populations[label] = pop
    threshold = read_json(local / 'threshold/receipt.json', job['threshold']['receipt_sha256'])
    require(threshold['stage1_model_sha256'] == job['stage1']['model_receipt_sha256'] and threshold['train_anchor_sha256'] == job['train_anchor_sha256'])
    require({k: v for k, v in threshold['selection'].items() if k != 'value'} == {k: v for k, v in job['threshold'].items() if k != 'receipt_sha256'})
    require(0 <= threshold['selection']['value'] <= 1)
    jobs.append((local, job, populations, threshold))
  return (
    manifest,
    jobs,
    public,
    {
      'source_manifest_sha256': SOURCE_SHA,
      'repeatability_sha256': REPEAT_SHA,
      'authorization_sha256': AUTH_SHA,
      'manifest_file_set_sha256': p.sha(p.canonical(files)),
      'authorization_file_sha256': digest(root / 'authorization.json'),
      'repeatability_file_sha256': digest(root / 'repeatability.json'),
      'manifest_file_sha256': digest(root / 'repeat-1/manifest.json'),
      'authorized_environment': {k: authorization['environment'][k] for k in ('python', 'numpy', 'blas_build_identity_sha256')},
    },
  )


def forbidden(*args, **kwargs):
  raise ValueError('HURDLE_ATTRIBUTION_EXECUTION_FORBIDDEN')


@contextmanager
def firewall():
  from openpilot.tools.cyber_autotune import empirical_hurdle_fit_cv_math as math
  from openpilot.tools.cyber_autotune import empirical_hurdle_fit_cv_data as data
  from openpilot.tools.cyber_autotune import empirical_hurdle_fit_cv_execution as executor
  from openpilot.tools.cyber_autotune import empirical_hurdle_fit_cv_gates as gates
  from openpilot.tools.cyber_autotune import empirical_hurdle_fit_cv_store as store
  from openpilot.tools.cyber_autotune import empirical_identifiability_execution as source
  from openpilot.tools.cyber_autotune import empirical_s2_ri_fit_cv_math as old
  from openpilot.tools.cyber_autotune import empirical_s2_ri_reconstruction_math as reconstruction

  targets = [
    (np.linalg, ('solve', 'lstsq', 'pinv')),
    (math, ('newton', 'fit_stage1', 'fit_stage2', 'normalizer', 'threshold', 'probability', 'predict_delta', 'integrated', 'project', 'recursive')),
    (old, ('fit', 'normalizer', 'predict', 'project', 'one_step', 'recursive')),
    (reconstruction, ('one_step', 'recursive_path', 'rollout')),
    (data, ('load_route', 'design', 'one_step', 'rollout')),
    (executor, ('run', 'execute_job')),
    (gates, ('select', 'fold_gate', 'selection_key')),
    (store, ('admit', 'compressed_array_read')),
    (source, ('read_array',)),
  ]
  with ExitStack() as stack:
    for module, names in targets:
      for name in names:
        require(hasattr(module, name), 'HURDLE_ATTRIBUTION_FIREWALL_TARGET_MISSING')
        stack.enter_context(patch.object(module, name, forbidden))
    stack.enter_context(
      patch.dict(
        sys.modules,
        dict.fromkeys(
          (
            'openpilot.tools.lib.logreader',
            'tools.lib.logreader',
            'scipy.optimize',
            'sklearn',
            'openpilot.tools.cyber_autotune.empirical_s2_ri_reconstruction_execution',
          ),
          None,
        ),
      )
    )
    yield


def output_root(path, source):
  path, source = safe(path), safe(source)
  require(
    str(path).startswith('/mnt/d/') and path != source and source not in path.parents and path not in source.parents,
    'HURDLE_ATTRIBUTION_D_ONLY_EXTERNAL_OUTPUT_REQUIRED',
  )
  repo = p.PUBLIC.parents[2]
  require(path != repo and repo not in path.parents)
  return path


def finish(root, names, fields):
  files = {name: digest(member(root, name)) for name in sorted(names)}
  value = p.seal({**fields, 'files': files})
  write_json(root / 'manifest.json', value)
  return value


def resume(root):
  from openpilot.tools.cyber_autotune import empirical_hurdle_attribution as analysis
  from openpilot.tools.cyber_autotune import empirical_hurdle_attribution_schema as schema

  root = safe(root)
  value = read_json(root / 'manifest.json')
  require(
    value.get('schema') == 'EMPIRICAL_HURDLE_ATTRIBUTION_MANIFEST_V1'
    and value.get('status') == analysis.SUCCESS
    and value.get('source_manifest_sha256') == SOURCE_SHA
    and value.get('job_order') == [list(j) for j in JOBS],
    'HURDLE_ATTRIBUTION_RESUME_CONFLICT',
  )
  policy_value = read_json(root.parent / 'policy.json', analysis.policy()['receipt_sha256'])
  authorization = read_json(root.parent / 'authorization.json', value['authorization_sha256'])
  require(
    authorization['policy_sha256'] == policy_value['receipt_sha256'] == value['policy_sha256']
    and authorization['executor_sources'] == analysis.source_code()
    and authorization['source_identity']['source_manifest_sha256'] == SOURCE_SHA
    and authorization['output_identity_sha256'] == p.sha(str(root.parent).encode()),
    'HURDLE_ATTRIBUTION_RESUME_CONFLICT',
  )
  expected = {f'jobs/{c}/{f}/receipt.json' for c, f in JOBS} | {'summary.json', 'readiness.json'}
  require(set(value['files']) == expected, 'HURDLE_ATTRIBUTION_RESUME_CONFLICT')
  verify_files(root, value['files'])
  for candidate, fold in JOBS:
    job = read_json(root / f'jobs/{candidate}/{fold}/receipt.json')
    schema.job(job)
    require(
      job['schema'] == 'EMPIRICAL_HURDLE_FAILURE_ATTRIBUTION_JOB_V1'
      and job['candidate_id'] == candidate
      and job['fold'] == fold
      and job['authorization_sha256'] == authorization['receipt_sha256']
    )
  summary = read_json(root / 'summary.json', value['summary_sha256'])
  readiness = read_json(root / 'readiness.json', value['readiness_sha256'])
  schema.summary(summary)
  schema.readiness(readiness, summary)
  return value
