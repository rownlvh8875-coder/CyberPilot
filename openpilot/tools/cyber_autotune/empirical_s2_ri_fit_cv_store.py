"""Pre-array admission, immutable receipts and verify-only resume."""
import json
from pathlib import Path

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_causal_dataset_store as storage
from openpilot.tools.cyber_autotune import empirical_identifiability_execution as read
from openpilot.tools.cyber_autotune import empirical_s2_ri_fitting_policy as frozen
from openpilot.tools.cyber_autotune import empirical_s2_ri_policy as design
from openpilot.tools.cyber_autotune import empirical_s2_ri_execution as old
from openpilot.tools.cyber_autotune import empirical_s2_ri_fit_cv_math as m

POLICY_SHA = '05cf63752587105d188bff2f81baec32e8192a689cbf09543caf1f954656ac96'
DERIVED_RESULT_SHA = '58546988e7458ce3406c64e015edee0f2c09ec1af681fb99eb62840ece61526c'
EXECUTOR_FILES = ('empirical_s2_ri_fit_cv_math.py','empirical_s2_ri_fit_cv_gates.py',
                  'empirical_s2_ri_fit_cv_store.py','empirical_s2_ri_fit_cv_execution.py')


def write_json(path,value):
  data = json.dumps(value,sort_keys=True,indent=2,allow_nan=False).encode()+b'\n'
  storage.atomic_bytes(path,data)


def contracts():
  expected = frozen.build()
  values = {name:read.read_json(frozen.PUBLIC/name) for name in expected}
  frozen.validate(values)
  if values[frozen.filename('fitting-policy')]['receipt_sha256'] != POLICY_SHA:
    raise ValueError('EXACT_D954_FITTING_POLICY_REQUIRED')
  candidates = values[frozen.filename('candidate-set')]['candidates']
  if tuple(c['candidate_id'] for c in candidates) != m.CANDIDATES:
    raise ValueError('EXACT_16_CANDIDATES_REQUIRED')
  return values


def finish(root,names,fields):
  if len(names) != len(set(names)):
    raise ValueError('DUPLICATE_RESULT_PATH')
  files = {n:p.sha(storage.safe(root/n).read_bytes()) for n in sorted(names)}
  receipt = p.seal({**fields,'files':files})
  write_json(root/'manifest.json',receipt)
  return receipt


def verify_manifest(root):
  manifest = read.read_json(storage.safe(root/'manifest.json'))
  for name,digest in manifest['files'].items():
    if Path(name).is_absolute():
      raise ValueError('RELATIVE_MANIFEST_PATH_REQUIRED')
    if p.sha(storage.safe(root/name).read_bytes()) != digest:
      raise ValueError('IMMUTABLE_RESULT_CONFLICT')
  return manifest



def derived_receipt_set(index):
  return p.sha(p.canonical([v['receipt_sha256'] for v in index['segments']]))

def admit(source,derived,output):
  """Only JSON metadata until authorization is sealed; qlog rejection is first."""
  source,derived = storage.safe(source),storage.safe(derived)
  output = storage.external(output,[source,derived,'/mnt/d/carrotlog','/mnt/d/CarrotLogs'])
  bundle = contracts()
  pol = design.policy()
  _,resolution,manifest,records,source_files = old.preflight(source,pol)
  result = read.read_json(derived/'repeat-1/results.json')
  admission = read.read_json(derived/'repeat-1/admission.json')
  index = read.read_json(derived/'repeat-1/derived-index.json')
  if (result['receipt_sha256'] != DERIVED_RESULT_SHA or result['admission_sha256'] != admission['receipt_sha256']
      or admission['manifest_sha256'] != manifest['receipt_sha256']
      or derived_receipt_set(index) != result['derived_receipt_set_sha256']):
    raise ValueError('EXACT_IMMUTABLE_DERIVED_IDENTITY_REQUIRED')
  denied = set(pol['excluded_qlog_content_sha256'])
  contents = [s['content_sha256'] for s in index['segments']]
  if denied.intersection(contents):
    raise ValueError('QLOG_CAUSAL_ADMISSION_FORBIDDEN')
  if len(contents) != 154 or set(contents) != {v['segment_sha256'] for _,v in records}:
    raise ValueError('EXACT_DERIVED_154_STREAM_SET_REQUIRED')
  derived_files = {f'repeat-1/{n}':p.sha((derived/'repeat-1'/n).read_bytes())
                   for n in ('results.json','admission.json','derived-index.json')}
  index_pins = {v['content_sha256']:v['receipt_sha256'] for v in index['segments']}
  attached = []
  for base,segment in sorted(records,key=lambda pair: (pair[1]['route_id'],pair[1]['segment_sha256'])):
    digest = segment['segment_sha256']
    local_root = derived/'repeat-1/segments'/digest
    local = read.read_json(local_root/'receipt.json')
    if (local['receipt_sha256'] != index_pins[digest]
        or local['source_receipt_sha256'] != segment['receipt_sha256']
        or local['policy_sha256'] != pol['receipt_sha256']):
      raise ValueError('EXACT_DERIVED_SEGMENT_SOURCE_REQUIRED')
    derived_files[(local_root/'receipt.json').relative_to(derived).as_posix()] = p.sha((local_root/'receipt.json').read_bytes())
    for key,binding in local['arrays'].items():
      name = read.array_name(key)
      derived_files[(local_root/name).relative_to(derived).as_posix()] = binding['file_sha256']
    attached.append((base,segment,local_root,local))
  sources = {n:p.sha(Path(__file__).with_name(n).read_bytes()) for n in EXECUTOR_FILES}
  auth = p.seal({'schema':'EMPIRICAL_S2_RI_RETROSPECTIVE_FIT_CV_AUTHORIZATION_V1',
    'candidate_pins':{c['candidate_id']:c['receipt_sha256'] for c in bundle['empirical-s2-ri-candidate-set-v1.json']['candidates']},
    'policy_sha256':POLICY_SHA,'public_contracts':{n:v['receipt_sha256'] for n,v in bundle.items()},
    'historical_design_pins':frozen.PINS,'rlog_manifest_sha256':manifest['receipt_sha256'],
    'derived_result_sha256':result['receipt_sha256'],'derived_index_sha256':index['receipt_sha256'],
    'source_file_set_sha256':p.sha(p.canonical(source_files)),
    'derived_file_set_sha256':p.sha(p.canonical(derived_files)),
    'routes':pol['route_ids'],'qlog_deny_content_sha256':sorted(denied),'executor_sources':sources,
    'output_store_identity':p.sha(str(output).encode()),'array_access_before_seal':False,
    'metric_clarification':'USER_CONFIRMED_FROZEN_DELTA_ERROR_PRIMITIVE_SHARED_CONTINUOUS_BUFFER',
    'retrospective_fit_cv_authorized':True,'primary_scope':'SCOPE_ALL_ACTIVE_NO_OVERRIDE',
    'final_dataset_status':resolution['final_dataset_status'],'holdout':'CLOSED','opening_count':0,
    'pooled_refit_authorized':False,'raw_opening_authorized':False,'qlog_support':0})
  write_json(output/'authorization.json',auth)
  write_json(output/'input-pins.json',p.seal({'schema':'EMPIRICAL_S2_RI_FIT_INPUT_PINS_V1',
    'source':source_files,'derived':derived_files,'authorization_sha256':auth['receipt_sha256']}))
  return auth,bundle,attached,source_files,derived_files
