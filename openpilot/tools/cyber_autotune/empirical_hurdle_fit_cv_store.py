"""Exact pre-array authorization and additive, hash-verified Hurdle stores."""

import gzip
import hashlib
import shutil
import zlib
import os
import platform
import subprocess
from pathlib import Path

import numpy as np

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_causal_dataset_store as storage
from openpilot.tools.cyber_autotune import empirical_identifiability_execution as read
from openpilot.tools.cyber_autotune import empirical_s2_ri_execution as metadata
from openpilot.tools.cyber_autotune import empirical_s2_ri_policy as source_policy
from openpilot.tools.cyber_autotune import empirical_s2_ri_fit_cv_store as historical
from openpilot.tools.cyber_autotune import empirical_hurdle_fitting_policy as frozen
from openpilot.tools.cyber_autotune import empirical_hurdle_fit_cv_math as m

STORAGE = {
  'format': 'NPY_GZIP_V1',
  'windows_result_volume': 'D',
  'windows_c_output_allowed': False,
  'compression_level': 1,
  'gzip_mtime': 0,
  'output_reserve_bytes': 20 * 1024**3,
  'windows_d_reserve_bytes': 1024**3,
  'read_chunk_bytes': 1024**2,
}


def storage_headroom(path, required=0):
  existing = storage.safe(path)
  if len(existing.parts) >= 3 and existing.parts[1] == 'mnt' and existing.parts[2] != 'd':
    raise ValueError('HURDLE_D_ONLY_RESULT_STORAGE_REQUIRED')
  while not existing.exists():
    existing = existing.parent
  # The execution host's root filesystem is the verified D-backed WSL VHD.
  # Reject any other mounted filesystem, including mounts outside /mnt.
  host = Path('/mnt/d')
  if host.exists() and existing.stat().st_dev not in {Path('/').stat().st_dev, host.stat().st_dev}:
    raise ValueError('HURDLE_D_ONLY_RESULT_STORAGE_REQUIRED')
  if shutil.disk_usage(existing).free < STORAGE['output_reserve_bytes'] + required:
    raise ValueError('HURDLE_STORAGE_HEADROOM_REQUIRED')
  # WSL virtual free space is not the Windows host-volume free space.
  if host.is_dir() and shutil.disk_usage(host).free < STORAGE['windows_d_reserve_bytes'] + required:
    raise ValueError('HURDLE_STORAGE_HEADROOM_REQUIRED_HOST_D')


def array_digest(array):
  return hashlib.sha256(memoryview(np.ascontiguousarray(array)).cast('B')).hexdigest()


class _HashedWriter:
  def __init__(self, stream):
    self.stream, self.sha = stream, hashlib.sha256()

  def write(self, data):
    self.sha.update(data)
    return self.stream.write(data)


def compressed_array_write(path, array):
  path = storage.safe(path)
  array = np.ascontiguousarray(array)
  if array.dtype.hasobject:
    raise ValueError('NO_OBJECT_ARRAYS')
  if path.exists():
    raise ValueError('IMMUTABLE_ARRAY_CONFLICT')
  # Reserve even an incompressible member before writing; no uncompressed temp.
  storage_headroom(path, array.nbytes + array.nbytes // 100 + 65536)
  path.parent.mkdir(parents=True, exist_ok=True)
  temp = storage.safe(path.with_name(path.name + '.atomic'))
  with temp.open('xb') as raw:
    with gzip.GzipFile(filename='', mode='wb', compresslevel=STORAGE['compression_level'], fileobj=raw, mtime=0) as compressed:
      writer = _HashedWriter(compressed)
      np.save(writer, array, allow_pickle=False)
    raw.flush()
    os.fsync(raw.fileno())
  # Independently decode every written member before it becomes committed evidence.
  verified = hashlib.sha256()
  with gzip.open(temp, 'rb') as decoded:
    for chunk in iter(lambda: decoded.read(STORAGE['read_chunk_bytes']), b''):
      verified.update(chunk)
  if verified.hexdigest() != writer.sha.hexdigest():
    raise ValueError('HURDLE_LOSSLESS_STORAGE_VERIFICATION_FAILURE')
  storage_headroom(path)
  os.link(temp, path)
  temp.unlink()
  return {
    'dtype': array.dtype.str,
    'shape': list(array.shape),
    'order': 'C',
    'array_sha256': array_digest(array),
    'file_sha256': digest(path),
    'npy_sha256': verified.hexdigest(),
    'storage_format': STORAGE['format'],
    'filename': path.name,
    'lossless_roundtrip_verified': True,
  }


def compressed_array_read(path, receipt):
  path = storage.safe(path)
  if receipt['storage_format'] != STORAGE['format'] or digest(path) != receipt['file_sha256']:
    raise ValueError('HURDLE_COMPRESSED_ARRAY_CONFLICT')
  with gzip.open(path, 'rb') as stream:
    array = np.load(stream, allow_pickle=False)
    if stream.read(1):
      raise ValueError('HURDLE_COMPRESSED_ARRAY_TRAILING_BYTES')
  if (
    array.dtype.str != receipt['dtype']
    or list(array.shape) != receipt['shape']
    or not array.flags.c_contiguous
    or array_digest(array) != receipt['array_sha256']
  ):
    raise ValueError('HURDLE_COMPRESSED_ARRAY_CONFLICT')
  return array


BASELINE = '15b75a14bad91cb4c04391526318abe0bd9ebf1d'
PINS = dict(
  zip(
    (
      'fitting-policy',
      'candidate-set',
      'stage1-fit-method',
      'stage1-convergence',
      'threshold-policy',
      'stage2-fit-method',
      'stage-normalization',
      'route-cv-contract',
      'metric-contract',
      'comparator-contract',
      'acceptance-gate',
      'selection-rule',
      'fitting-policy-readiness',
    ),
    (
      '3824973d9851ebfffbfd47e9f95b9f49580326b75f652e55c1ca21808d624104',
      'eff4ff37f74e06520e917f017c509175733a108df9399ebab8f2e93fa6a871f4',
      '6c644678deb454008c3a3146cece0a24393642e2025707dbacbe47e3355a7b9a',
      '4a2c377be5379c1a03d65dbb9c06070619d60cedee3ab6d4af331aba8426a82a',
      '56c8ce9eeba90be17d5ec4bd73ec604447dfcc9463dce7b38b8f6a1769706841',
      '31761a5961b755f3d0ca719bb88355b560c8b47e8b00df5f6f04e17ad8b986b4',
      '4704b839037042084da818cc72eecd651b7a1d7ac12fa5d74f1531bb2517e549',
      '9e6bddd4f4d0e3dbe1cd02d7cfe2313a17da5459215f4fa397d42b098b406a4a',
      '98df562961a9c60cd43531694cd0dfbbde19b528c856bf6562ea6d5c6aad17e5',
      '80561a7f863363fa5ce6ed6710e2c29cae58ff985f2597bb0761faf86e27cf00',
      '1a5198475b7a3843381762078475915a389b2898e950effc171a3df58219ca60',
      '9622e7134b56f0c48153cba1a23dd690bdc6d578a433c6f77b34e3f7a3cf70f0',
      'cde321da593da445d5df34a7a2a9212555209c7d66b2979b7ef01987c230cefb',
    ),
    strict=True,
  )
)
MODULES = (
  'empirical_hurdle_fit_cv_math.py',
  'empirical_hurdle_fit_cv_store.py',
  'empirical_hurdle_fit_cv_execution.py',
  'empirical_hurdle_fit_cv_gates.py',
  'empirical_hurdle_fit_cv_publication.py',
  'empirical_hurdle_fit_cv_data.py',
)
DEPENDENCIES = (
  'empirical_s2_ri_fit_cv_math.py',
  'empirical_s2_ri_reconstruction_math.py',
  'empirical_s2_ri_schema.py',
  'empirical_identifiability_execution.py',
  'empirical_causal_dataset_store.py',
  'empirical_plant_policy.py',
  'empirical_s2_ri_execution.py',
  'empirical_causal_support_guard.py',
  'empirical_final_readiness.py',
  'empirical_hurdle_fitting_policy.py',
  'empirical_hurdle_fitting_contracts.py',
)


def digest(path):
  with storage.safe(path).open('rb') as stream:
    return hashlib.file_digest(stream, 'sha256').hexdigest()


def contracts():
  bundle = {label: read.read_json(p.PUBLIC / ('empirical-hurdle-' + label + '-v1.json')) for label in PINS}
  if any(bundle[label]['receipt_sha256'] != sha for label, sha in PINS.items()):
    raise ValueError('HURDLE_EXECUTION_POLICY_BINDING_CONFLICT')
  frozen.load_inputs()  # Exact design file and receipt pins; public metadata only.
  if tuple(c['candidate_id'] for c in bundle['candidate-set']['candidates']) != m.CANDIDATES:
    raise ValueError('HURDLE_EXECUTION_POLICY_BINDING_CONFLICT')
  return bundle


def environment():
  if platform.python_version() != '3.12.13' or np.__version__ != '2.5.3' or any(os.environ.get(k) != '1' for k in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS')):
    raise ValueError('HURDLE_FROZEN_EXECUTION_ENVIRONMENT_REQUIRED')
  config = np.show_config(mode='dicts')
  # Private build metadata binds compiler/BLAS configuration, never published.
  return {
    'python': platform.python_version(),
    'numpy': np.__version__,
    'OPENBLAS_NUM_THREADS': '1',
    'OMP_NUM_THREADS': '1',
    'blas_build_identity_sha256': p.sha(p.canonical(config)),
    'private_build_metadata': config,
    'dtype': 'float64',
    'order': 'C',
    'rng': 'NONE',
    'zlib_runtime_version': zlib.ZLIB_RUNTIME_VERSION,
  }


def sources():
  return {name: digest(Path(__file__).with_name(name)) for name in (*MODULES, *DEPENDENCIES)}


def write_json(path, value):
  historical.write_json(path, value)


def verify_files(root, pins):
  for name, sha in pins.items():
    if Path(name).is_absolute() or '..' in Path(name).parts or digest(root / name) != sha:
      raise ValueError('HURDLE_IMMUTABLE_INPUT_CONFLICT')


def finish(root, names, fields):
  if len(names) != len(set(names)):
    raise ValueError('DUPLICATE_RESULT_PATH')
  receipt = p.seal({**fields, 'files': {name: digest(root / name) for name in sorted(names)}})
  write_json(root / 'manifest.json', receipt)
  return receipt


def verify_manifest(root):
  value = read.read_json(root / 'manifest.json')
  verify_files(root, value['files'])
  actual = {item.relative_to(root).as_posix() for item in root.rglob('*') if storage.safe(item).is_file()}
  if actual != set(value['files']) | {'manifest.json'}:
    raise ValueError('HURDLE_EXACT_COMPLETE_FILE_SET_REQUIRED')
  return value


def admit(source, derived, output):
  """Metadata-only admission. Numeric arrays are not decoded until seal exists."""
  env, bundle = environment(), contracts()
  storage_headroom(output)
  source, derived = map(storage.safe, (source, derived))
  output = storage.external(output, [source, derived, '/mnt/d/carrotlog', '/mnt/d/CarrotLogs'])
  pol = source_policy.policy()
  _, resolved, manifest, records, all_source_files = metadata.preflight(source, pol)
  index = read.read_json(derived / 'repeat-1/derived-index.json')
  result = read.read_json(derived / 'repeat-1/results.json')
  admission = read.read_json(derived / 'repeat-1/admission.json')
  contents = [v['content_sha256'] for v in index['segments']]
  denied = set(pol['excluded_qlog_content_sha256'])
  if denied.intersection(contents):
    raise ValueError('QLOG_CAUSAL_ADMISSION_FORBIDDEN')
  if (
    len(contents) != 154
    or len(set(contents)) != 154
    or set(contents) != {v['segment_sha256'] for _, v in records}
    or manifest['receipt_sha256'] != 'c584e2031baf144103c20ca76974c53a9ea614babdf9c865936675474742bba8'
    or index['receipt_sha256'] != '34fba3100273a19b17d28b8bc73e153caaa247a216fa470833bcba95bd36fc18'
    or result['receipt_sha256'] != historical.DERIVED_RESULT_SHA
    or result['admission_sha256'] != admission['receipt_sha256']
    or admission['manifest_sha256'] != manifest['receipt_sha256']
    or historical.derived_receipt_set(index) != result['derived_receipt_set_sha256']
    or resolved['final_dataset_status'] != 'RETROSPECTIVE_CAUSAL_TRAIN_DEV_DATASET_PARTIAL'
  ):
    raise ValueError('HURDLE_EXACT_DERIVED_INPUT_REQUIRED')
  # Bind only authorized numeric fields plus metadata; no rate/raw/qlog reads.
  source_files = {k: v for k, v in all_source_files.items() if k.endswith('.json')}
  derived_files = {f'repeat-1/{n}.json': digest(derived / f'repeat-1/{n}.json') for n in ('results', 'admission', 'derived-index')}
  pins = {v['content_sha256']: v['receipt_sha256'] for v in index['segments']}
  attached = []
  for base, segment in sorted(records, key=lambda pair: (pair[1]['route_id'], pair[1]['segment_sha256'])):
    root = derived / 'repeat-1/segments' / segment['segment_sha256']
    local = read.read_json(root / 'receipt.json')
    if (
      local['receipt_sha256'] != pins[segment['segment_sha256']]
      or local['source_receipt_sha256'] != segment['receipt_sha256']
      or local['policy_sha256'] != pol['receipt_sha256']
    ):
      raise ValueError('HURDLE_EXACT_DERIVED_LINEAGE_REQUIRED')
    derived_files[(root / 'receipt.json').relative_to(derived).as_posix()] = digest(root / 'receipt.json')
    for key in ('angle_tick', 'streak_all', 'model_eligible', 'rail', 's2_ri_causal_run_id', 'within_s2_ri_causal_run_index'):
      derived_files[(root / read.array_name(key)).relative_to(derived).as_posix()] = local['arrays'][key]['file_sha256']
    for key in ('command.normalized', 'state.speed_mps', 'grid_time_ns'):
      source_files[(base / 'arrays' / read.array_name(key)).relative_to(source).as_posix()] = segment['arrays'][key]['file_sha256']
    attached.append((base, segment, root, local))
  public_files = {('empirical-hurdle-' + label + '-v1.json'): digest(p.PUBLIC / ('empirical-hurdle-' + label + '-v1.json')) for label in PINS}
  public_files.update({k: v['file_sha256'] for k, v in frozen.PINS.items()})
  head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=p.PUBLIC, text=True).strip()
  subprocess.run(['git', 'merge-base', '--is-ancestor', BASELINE, head], cwd=p.PUBLIC, check=True)
  auth = p.seal(
    {
      'schema': 'EMPIRICAL_HURDLE_RETROSPECTIVE_FIT_CV_AUTHORIZATION_V1',
      'head': head,
      'policy_receipts': PINS,
      'design_readiness_sha256': frozen.PINS['empirical-hurdle-design-readiness-v1.json']['receipt_sha256'],
      'source_manifest_sha256': manifest['receipt_sha256'],
      'derived_result_sha256': result['receipt_sha256'],
      'derived_index_sha256': index['receipt_sha256'],
      'qlog_deny_content_sha256': sorted(denied),
      'routes': pol['route_ids'],
      'source_file_set_sha256': p.sha(p.canonical(source_files)),
      'derived_file_set_sha256': p.sha(p.canonical(derived_files)),
      'public_input_files': public_files,
      'executor_sources': sources(),
      'output_store_identity': p.sha(str(output).encode()),
      'environment': env,
      'retrospective_fit_cv_authorized': True,
      'array_access_before_seal': False,
      'candidate_order': list(m.CANDIDATES),
      'fold_order': ['FOLD_A', 'FOLD_B'],
      'job_count': 32,
      'stage1_fitting_authorized': True,
      'stage2_move_only_fitting_authorized': True,
      'train_only_threshold_authorized': True,
      'retrospective_selection_authorized': True,
      'model_candidate_expansion_authorized': False,
      'holdout_discovery_authorized': False,
      'rollout_chunk': m.CHUNK,
      'private_array_storage': STORAGE,
      'holdout': 'CLOSED',
      'opening_count': 0,
      'pooled_refit_authorized': False,
      'raw_opening_authorized': False,
      'qlog_opening_authorized': False,
      'vehicle_authority': 'NONE',
    }
  )
  write_json(output / 'authorization.json', auth)
  write_json(output / 'input-pins.json', p.seal({'source': source_files, 'derived': derived_files, 'authorization_sha256': auth['receipt_sha256']}))
  return auth, bundle, attached, source_files, derived_files
