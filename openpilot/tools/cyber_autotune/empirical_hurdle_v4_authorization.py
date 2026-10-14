"""Externally trusted V4 one-shot authority. Never mints a grant."""

FROZEN_SOURCE_PINS = {
  'empirical_hurdle_fit_cv_data.py': '9e104a83a928c6b997a914a606820f2d2190fa56917e4042856474f747b900ac',
  'empirical_hurdle_fit_cv_gates.py': '7529884d62ee5773bc163a301a9d96c641ff2a2e2e911d3e3e4f0a5c1a6828c2',
  'empirical_hurdle_fit_cv_math.py': 'b410b2f0138848faf4e976094a1bd4f3cc3ac44418b54a24310717c6261e0e73',
  'empirical_hurdle_v3_external_storage.py': 'fddf87bf1837e773c0e00b23d8b9446a6de511bf437b90832c15d94da1331d6c',
  'empirical_hurdle_v3_io.py': '1fb772477eed0be39653d92247edf31cdfab109069afb6b56fbadbb65cd06b3d',
  'empirical_hurdle_v4_fitting_policy.py': '529c6c14832a18bc18eb51409e1637ca2c003892d62aa883f900c238d59be76f',
  'empirical_hurdle_v4_state_contract.py': '3a21944b47ee82f4401b6742742924b7458741f17959e3ed2c2d41df67f68793',
  'empirical_s2_ri_fit_cv_math.py': 'a1c1203c8222df067064ff1891aafa82cdafd997338c7ca7687a321c66777f29',
}
POLICY_PINS = {
  'empirical-hurdle-acceptance-gate-v1.json': [
    '606d5d3f46677d0107298f8b94e0a6d5a73da62f01db0164c4812a9fa2cccee1',
    '1a5198475b7a3843381762078475915a389b2898e950effc171a3df58219ca60',
  ],
  'empirical-hurdle-fit-cv-results-v1.json': [
    '72e0179a96a8885e7ffab57bf1c579ef75536769bc1a03990a007b3b4e2ac272',
    '8d7c45a7a97f73918f927b19b0004c309078239b8b8523e1beac08fa6c53f5c4',
  ],
  'empirical-hurdle-selection-rule-v1.json': [
    'aeb3e51e85039660be702517dfd79e4c932eb72bde0b1a9d9bdc4bbaad36586c',
    '9622e7134b56f0c48153cba1a23dd690bdc6d578a433c6f77b34e3f7a3cf70f0',
  ],
  'empirical-hurdle-stage1-v3-external-storage-amendment.json': [
    'd59da0af6279c33109513848f9c910a484b352a4a530d47da60af32a17d1239d',
    '5b109186575c4b50b7095a4e99d6028fd8a8f21e4e944fb6ca5ec59d6a4a26e5',
  ],
  'empirical-hurdle-stage1-v3-storage-migration-verification.json': [
    'a1b25dd9913c0906a8239af85f09d7db42eb3559b6ed15f408ba14555f5173e4',
    'f147cb4121a5e34f57d663c8fa631ab26805d30c9157515802f7a0cf7529adc9',
  ],
  'empirical-hurdle-stage1-v4-artifact-identity-policy.json': [
    '036a8df831896a62a682fac550637f12565706a7bddd24a17d29dae18b749868',
    '030deec64781d98c36beb015899b58d7e9d954b0a2f79274997423331932f1da',
  ],
  'empirical-hurdle-stage1-v4-causal-state-contract.json': [
    'bdcd62d3e2736a96e4118d1da070b5f0c77aa2a23d57a776888594a6a4db686c',
    'd3df9b9c32043aa01df9f95c6adb126ceab76439bc72aac79c4c06fe86096e39',
  ],
  'empirical-hurdle-stage1-v4-current-feature-contract.json': [
    'a7550eef12d82d15515b2d1fcbf2d6e3c7288d754f321426f23782339397991c',
    '5c7ea2975f7ee2881b028c445a5aa6076669ecf87c1989e91a5d582921850ce0',
  ],
  'empirical-hurdle-stage1-v4-failure-policy.json': [
    '54506e0b18cf581eaed57bd60f725caa04a5d4ba1050943037cd4a617fa1ece6',
    '1b5bf5bceac75e351a448748830dcac4b9b308460feea2e850f341c9b606e3c3',
  ],
  'empirical-hurdle-stage1-v4-fitting-policy-decision.json': [
    '9e579ee9ca12eba41e7b39fea43d7bdd2a58c34b1bcbd018d5f60bde53c1f7e9',
    'f63a046c8e40606921852e5709349b140d229cfc1714df97e837105826505268',
  ],
  'empirical-hurdle-stage1-v4-fitting-policy-readiness.json': [
    'cc0fa2ec0bb1813a7234dc1647cbdcc3aa4190f312dbd26449aff4239a600ddd',
    '5737d4965c22f7f2a6712e3ae0bc931ad9c60a37ca8ce18f2677cfa7646023bf',
  ],
  'empirical-hurdle-stage1-v4-fitting-policy-validation.json': [
    'e52ce75ff2898abcefb6425a81dabb2b1713d32875e76890530cf132dfd41b7e',
    '45b417009d31998bbb4c8c4c603caf75627e4296e6675417a0e0e07d83741127',
  ],
  'empirical-hurdle-stage1-v4-head-fitting-policy.json': [
    '067887b7342b35f680f658b05104ca8087a6d249b2b4becbeb87610f05a0a9f2',
    'e28ce7c17aa828f3366d40b221d5c3074b6c7102e49fba6c3d0489d675018be2',
  ],
  'empirical-hurdle-stage1-v4-identifiable-basis-policy.json': [
    'd0d86b2243de411f2450935910ffecbb4e2f7b7264f188d2e579d3365fdd46cb',
    '6d7c12e30e6004b1189dfd084fa05917b0b457928fe5ac9a923e9274a12ddd9c',
  ],
  'empirical-hurdle-stage1-v4-normalization-policy.json': [
    '5f902107a994a9f7b732db40d95e04f01f15fbf78d631a03f912e507f4539723',
    'b95c2a778123610cfbadfef504ef072bfd660f4655244df42c21df93ff4d35da',
  ],
  'empirical-hurdle-stage1-v4-optimizer-policy.json': [
    'e829217f0d47d6a00bebdc47c0ce677d84e3f621e4f818795a35c12ab6a50157',
    'dff8be0f3da7d6aea0eff81317ce15ce694f8f1bc08e56a1ed9ece23c59320ec',
  ],
  'empirical-hurdle-stage1-v4-regularization-policy.json': [
    'f4bcefcd86900b25eec522911da96b820cbaa712b7327d2e84ed439f1e0fca59',
    '6b4d756727c7fbf7583c31ad06a0298f27e6d3f4f9d945dd420b1bd378d72cfc',
  ],
  'empirical-hurdle-stage1-v4-representation-decision.json': [
    '7f63e587e160318312a6d758c5002ea005182334971c3d299282db6a3b8bdaf5',
    '5c1a64fb49aa0c5eda0ee21f1cd9173653647353b82915fb85fcb001ea3cc74b',
  ],
  'empirical-hurdle-stage1-v4-representation-design-contract.json': [
    'e720a21539da698eb34bb1b69b71f1e6088aaae678eea2c3432dae57a433796e',
    '01b695d8941298066b61acc341a07f2cbedcd8f1df408754d476744fc3e2a1b8',
  ],
  'empirical-hurdle-stage1-v4-rollout-state-contract.json': [
    'efd06a9d9109ce326e96ecc29af480007f85cbbccf398f1c0750164ba266bada',
    '1b503078ac9e5adda34f54650099309c7db718c5181ccdca5dc462d11899542f',
  ],
  'empirical-hurdle-stage1-v4-separation-policy.json': [
    '44ff7760c110a70a1a739ead3c0392b18990019858cb9b8aeefba10efd923d85',
    '840adca399b765f59b8a03e7335b130475ed889b2c21a95459ed3cc89d2c928a',
  ],
  'empirical-hurdle-stage1-v4-support-rank-policy.json': [
    '1fdf2e20fa8b54ea1eae9832097f1aebf28a1851e27e9bf673f1702f31165d5f',
    '8ad397ff95abcb3fc0cfc8b8105aba46c53fdd3fb30f37458976d6c5eff8118c',
  ],
  'empirical-hurdle-stage1-v4-threshold-policy.json': [
    '8d1bb8feaf07b310b53bbd27c5818e2acd1ce5b196cd406f37d576e7b48465c4',
    '8e8896e2a68f85f646741b7471c6becad0a58e3fb80b691b7c9582247487f048',
  ],
}

from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
import copy
import re
import subprocess
import weakref

from openpilot.tools.cyber_autotune import empirical_hurdle_v3_io as prior
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_fitting_policy as f

p = prior.p
AUTH_FIELDS = {
  'branch',
  'capacity_preflight',
  'certificate_generator_sha256',
  'certificate_verifier_sha256',
  'compression',
  'environment',
  'executor_sources',
  'firewall_sha256',
  'head',
  'holdout',
  'holdout_discovery',
  'jobs',
  'mount_identity_sha256',
  'normalizer_refit_authorized',
  'numeric_access_authorized',
  'opening_count',
  'output_schema',
  'policies',
  'pooled_refit_authorized',
  'raw_qlog_authorized',
  'receipt_sha256',
  'replicas',
  'repository',
  'resource_budget',
  'root_identities',
  'schema',
  'source_manifests',
  'stage1_train_fit_authorized',
  'stage2_refit_authorized',
  'storage_amendment_receipt_sha256',
  'storage_migration_receipt_sha256',
  'storage_volume',
  'train_only_decision_authorized',
  'v1_authorization_sha256',
  'v1_manifest_sha256',
  'v1_repeatability_sha256',
  'vehicle_authority',
  'volume_identity_sha256',
} | set(p.FIREWALL)
ROOTS = ('source', 'causal', 'derived', 'output')
REPOSITORY = 'https://github.com/rownlvh8875-coder/CyberPilot'
BRANCH = 'feature/cyber-autotune'
SCHEMA = 'HURDLE_STAGE1_V4_EXTERNAL_ONE_SHOT_AUTHORIZATION'
OUTPUT_SCHEMA = 'V4_PRIVATE_STORE_V1'
FORBIDDEN = ('STAGE2_FIT', 'NORMALIZER_FIT', 'RAW', 'QLOG', 'HOLDOUT', 'POOLED_REFIT', 'VEHICLE')
FIREWALL = p.sha(p.canonical(FORBIDDEN))
_REGISTRY = weakref.WeakKeyDictionary()


def need(ok, status='V4_EXECUTION_AUTHORIZATION_CONFLICT'):
  if not ok:
    raise ValueError(status)


def contracts():
  bodies = {}
  try:
    for name, sha in FROZEN_SOURCE_PINS.items():
      need(prior.digest(Path(__file__).parent / name) == sha)
    for name, (sha, receipt) in POLICY_PINS.items():
      raw = (p.PUBLIC / name).read_bytes()
      need(p.sha(raw) == sha)
      row = p.verify(__import__('json').loads(raw))
      need(row['receipt_sha256'] == receipt)
      bodies[name] = row
    jobs = bodies['empirical-hurdle-fit-cv-results-v1.json']['jobs']
    need([(j['candidate_id'], j['fold']) for j in jobs] == list(prior.JOBS))
    return {
      'policies': {k: v[1] for k, v in POLICY_PINS.items()},
      'bodies': bodies,
      'jobs': jobs,
      'clauses': bodies['empirical-hurdle-acceptance-gate-v1.json']['clauses'],
    }
  except (ValueError, OSError, KeyError, TypeError) as exc:
    raise ValueError('V4_EXECUTOR_POLICY_INPUT_CONFLICT') from exc


def sources():
  root = Path(__file__).parent
  result = prior.sources()
  for name in ('certificate', 'authorization', 'io', 'store', 'execution', 'fitting_policy', 'state_contract'):
    path = root / ('empirical_hurdle_v4_' + name + '.py')
    need(path.is_file(), 'V4_EXECUTOR_SOURCE_CONFLICT')
    result[path.name] = prior.digest(path)
  return result


def capacity(jobs, budget):
  """Output-schema bound; proof integers capped by authorized operational bits."""
  need(set(budget) == {'certificate_integer_bits', 'metadata_bytes_per_job', 'reserve_bytes'})
  need(all(type(v) is int and v > 0 for v in budget.values()))
  bits = budget['certificate_integer_bits']
  # Decimal JSON upper bound: one char per bit plus sign/quotes/comma.
  integer_bytes = bits + 4
  payload, peak, metadata = 0, 0, 0
  for job in jobs:
    _, length = f.old.parameters(job['candidate_id'])
    dim = 2 * length + 3
    n, dev = job['train_count'], job['one_step']['count']
    need(all(type(v) is int and v >= 0 for v in (n, dev)))
    payload += n * 8 + dev * 27 + (2 * dim - 1) * 8  # combined p, DEV, coefficients.
    proof = 2 * (4 * dim + 16) * integer_bytes + 2 * dim * 128
    metadata += proof + budget['metadata_bytes_per_job']
    peak = max(peak, n * 8, dev * 8, proof)
    for h in f.old.HORIZONS:
      count = job['rollout'][str(h)]['overall']['count']
      need(type(count) is int and count >= 0)
      payload += count * (2 * (h + 1) + h + 8)
      peak = max(peak, count * 2 * (h + 1))
  # gzip stored-block expansion bound plus NPY/header allowance per job/population.
  bound = payload + payload // 100 + len(jobs) * 65536 + metadata
  atomic = peak + peak // 100 + 65536
  result = {
    'run1_upper_bytes': bound,
    'run2_upper_bytes': bound,
    'atomic_upper_bytes': atomic,
    'metadata_upper_bytes': metadata,
    'reserve_bytes': budget['reserve_bytes'],
  }
  result['required_bytes'] = sum(result.values())
  return result


def storage_roots(roots, auth):
  need(set(roots) == set(ROOTS), 'V4_EXECUTION_ROOT_CONFLICT')
  roots = {k: prior.safe(Path(v)) for k, v in roots.items()}
  # E proof itself rejects C/D/F/WSL/symlink/nested mount/letter mismatch.
  for root in roots.values():
    prior.external.prove_authorized_external_volume(root, expected_mount=auth.get('mount_identity_sha256'))
  prior.external.check_live_volume(auth['volume_identity_sha256'])
  prior.non_overlap(roots)
  need({k: p.sha(str(v).encode()) for k, v in roots.items()} == auth['root_identities'])
  return roots


@dataclass(frozen=True, eq=False)
class Permit:
  authorization: dict
  trusted_sha256: str
  roots: dict
  pack: dict
  lineage: object
  replica: str


def environment_valid(auth):
  expected = {
    'python': '3.12.13',
    'numpy': '2.5.3',
    'OPENBLAS_NUM_THREADS': '1',
    'OMP_NUM_THREADS': '1',
    'blas_build_identity_sha256': prior.legacy.BLAS_SHA,
    'dtype': 'float64',
    'order': 'C',
    'rng': 'NONE',
  }
  need(all(auth['environment'].get(k) == v for k, v in expected.items()), 'V4_EXECUTION_ENVIRONMENT_CONFLICT')
  need(prior.environment() == auth['environment'], 'V4_EXECUTION_ENVIRONMENT_CONFLICT')


def metadata(roots, auth, pack):
  from openpilot.tools.cyber_autotune import empirical_hurdle_v4_io

  return empirical_hurdle_v4_io.admit_metadata(roots, auth, pack)


def repository_identity():
  root = Path(__file__).resolve().parents[3]
  remote = subprocess.check_output(['git', 'remote', 'get-url', 'origin'], cwd=root, text=True).strip().removesuffix('.git')
  branch = subprocess.check_output(['git', 'branch', '--show-current'], cwd=root, text=True).strip()
  return remote, branch


def lineage_identity(lineage):
  return f.identity(
    {
      'jobs': lineage['jobs'],
      'pins': lineage['pins'],
      'records': prior.records_identity(lineage['records']),
      'source_policy': lineage['source_policy'],
      'receipts': {str(k): v for k, v in lineage['receipts'].items()},
      'metadata_pins': lineage['metadata_pins'],
    }
  )


def preflight(authorization, trusted_sha256, *, replica, roots=None):
  if authorization is None:
    raise ValueError('V4_PRIVATE_EXECUTION_NOT_AUTHORIZED')
  need(type(authorization) is dict and type(trusted_sha256) is str and re.fullmatch('[0-9a-f]{64}', trusted_sha256) is not None)
  pack = contracts()  # 1 public.
  need(prior.current_head() == authorization.get('head'), 'V4_EXECUTION_HEAD_CONFLICT')  # 2
  need(sources() == authorization.get('executor_sources'), 'V4_EXECUTOR_SOURCE_CONFLICT')  # 3
  auth = copy.deepcopy(authorization)
  try:
    need(set(auth) == AUTH_FIELDS)
    p.verify(auth)
    need(auth['receipt_sha256'] == trusted_sha256 and type(trusted_sha256) is str)
    need(repository_identity() == (REPOSITORY, BRANCH), 'V4_EXECUTION_REPOSITORY_CONFLICT')
    need(auth['schema'] == SCHEMA and auth['repository'] == REPOSITORY and auth['branch'] == BRANCH)
    need(auth['policies'] == pack['policies'] and auth['jobs'] == [prior.job_identity(j) for j in pack['jobs']])
    need(
      auth['v1_manifest_sha256'] == prior.verified.SOURCE_SHA
      and auth['v1_authorization_sha256'] == prior.verified.AUTH_SHA
      and auth['v1_repeatability_sha256'] == prior.verified.REPEAT_SHA
    )
    need(
      auth['certificate_generator_sha256'] == auth['executor_sources']['empirical_hurdle_v4_certificate.py']
      and auth['certificate_verifier_sha256'] == auth['certificate_generator_sha256']
    )
    need(auth['firewall_sha256'] == FIREWALL and auth['compression'] == prior.COMPRESSION and auth['output_schema'] == OUTPUT_SCHEMA)
    need(auth['replicas'] == ['repeat-1', 'repeat-2'] and replica in auth['replicas'])
    need(auth['numeric_access_authorized'] is True and auth['stage1_train_fit_authorized'] is True and auth['train_only_decision_authorized'] is True)
    need(all(auth[k] is False for k in ('stage2_refit_authorized', 'normalizer_refit_authorized', 'pooled_refit_authorized', 'raw_qlog_authorized')))
    need(
      auth['holdout'] == 'CLOSED'
      and auth['vehicle_authority'] == 'NONE'
      and type(auth['opening_count']) is int
      and auth['opening_count'] == 0
      and type(auth['holdout_discovery']) is int
      and auth['holdout_discovery'] == 0
    )
    need(auth.get('synthetic') is not True)
    amendment, migration = prior.external.contracts()
    need(
      auth['storage_volume'] == 'E_EXTERNAL_SSD'
      and auth['storage_amendment_receipt_sha256'] == amendment['receipt_sha256']
      and auth['storage_migration_receipt_sha256'] == migration['receipt_sha256']
    )
    need(all(auth['root_identities'][k] == migration['destination_root_sha256'][k] for k in ('source', 'causal', 'derived')))
    checked_roots = storage_roots(roots, auth)  # 5+6
    estimated = capacity(pack['jobs'], auth['resource_budget'])
    need(auth['capacity_preflight'] == {**estimated, 'free_bytes': auth['capacity_preflight']['free_bytes']})
    need(
      auth['capacity_preflight']['free_bytes'] >= estimated['required_bytes'] and prior.free_bytes(checked_roots['output']) >= estimated['required_bytes'],
      'V4_EXECUTION_STORAGE_CAPACITY_FAILURE',
    )  # 7
    environment_valid(auth)  # 8
    lineage = metadata(checked_roots, auth, pack)  # 9..12 JSON only.
  except OSError as exc:
    raise ValueError('V4_PRIVATE_SOURCE_UNRESOLVED') from exc
  except (KeyError, TypeError, AttributeError) as exc:
    raise ValueError('V4_EXECUTION_AUTHORIZATION_CONFLICT') from exc
  permit = Permit(auth, trusted_sha256, MappingProxyType(checked_roots), pack, lineage, replica)
  _REGISTRY[permit] = (p.sha(p.canonical(auth)), lineage_identity(lineage), f.identity(pack))
  valid(permit)
  return permit  # 13 numeric admission only now.


def valid(permit):
  need(isinstance(permit, Permit) and permit in _REGISTRY, 'V4_PRIVATE_EXECUTION_NOT_AUTHORIZED')
  need(
    (p.sha(p.canonical(permit.authorization)), lineage_identity(permit.lineage), f.identity(permit.pack)) == _REGISTRY[permit]
    and permit.authorization['receipt_sha256'] == permit.trusted_sha256
  )
  need(prior.current_head() == permit.authorization['head'] and sources() == permit.authorization['executor_sources'])
  storage_roots(permit.roots, permit.authorization)
  environment_valid(permit.authorization)
  need(permit.replica in permit.authorization['replicas'])
  return permit
