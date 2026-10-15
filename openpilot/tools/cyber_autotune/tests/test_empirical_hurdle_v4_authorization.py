"""V4 public policy lock and pre-numeric authorization failures."""

import unittest
from pathlib import Path
from unittest.mock import patch
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_authorization as a


class TestAuthorization(unittest.TestCase):
  def test_policy_receipts(self):
    pack = a.contracts()
    self.assertEqual(len(pack['jobs']), 32)
    self.assertEqual(
      pack['policies']['empirical-hurdle-stage1-v4-fitting-policy-decision.json'], 'f63a046c8e40606921852e5709349b140d229cfc1714df97e837105826505268'
    )

  def test_missing(self):
    with patch.object(a, 'metadata', side_effect=AssertionError('numeric/metadata premature')):
      with self.assertRaisesRegex(ValueError, 'V4_PRIVATE_EXECUTION_NOT_AUTHORIZED'):
        a.preflight(None, None, replica='repeat-1')

  def test_capacity(self):
    jobs = a.contracts()['jobs']
    budget = {'certificate_integer_bits': 4096, 'metadata_bytes_per_job': 65536, 'reserve_bytes': 1048576}
    r = a.capacity(jobs, budget)
    self.assertEqual(r['run1_upper_bytes'], r['run2_upper_bytes'])
    self.assertEqual(
      r['required_bytes'], sum(r[k] for k in ('run1_upper_bytes', 'run2_upper_bytes', 'atomic_upper_bytes', 'metadata_upper_bytes', 'reserve_bytes'))
    )
    with self.assertRaises(ValueError):
      a.capacity(jobs, {**budget, 'certificate_integer_bits': 0})

  def test_forbidden_volume(self):
    for root in ('/mnt/c/example', '/mnt/d/example', '/mnt/f/example', '/home/example'):
      with self.subTest(root=root), self.assertRaises(ValueError):
        a.storage_roots({k: Path(root) / k for k in a.ROOTS}, {})


class TestFirewallMutations(unittest.TestCase):
  def setUp(self):
    # Synthetic external identity, independent of CI's detached checkout.
    self.enterContext(patch.object(a, 'repository_identity', return_value=(a.REPOSITORY, a.BRANCH)))

  def fixture(self):
    """SYNTHETIC_AUTHORIZATION_ONLY: external probes are mocked, no real grant."""
    from openpilot.tools.cyber_autotune import empirical_plant_policy as p

    pack = a.contracts()
    amendment, migration = a.prior.external.contracts()
    budget = {'certificate_integer_bits': 4096, 'metadata_bytes_per_job': 65536, 'reserve_bytes': 1048576}
    estimate = a.capacity(pack['jobs'], budget)
    auth = {
      'schema': a.SCHEMA,
      'head': a.prior.current_head(),
      'repository': a.REPOSITORY,
      'branch': a.BRANCH,
      'policies': pack['policies'],
      'executor_contract_receipts': pack['executor_contract_receipts'],
      'jobs': [a.prior.job_identity(j) for j in pack['jobs']],
      'executor_sources': a.sources(),
      'v1_manifest_sha256': a.prior.verified.SOURCE_SHA,
      'v1_authorization_sha256': a.prior.verified.AUTH_SHA,
      'v1_repeatability_sha256': a.prior.verified.REPEAT_SHA,
      'firewall_sha256': a.FIREWALL,
      'compression': a.prior.COMPRESSION,
      'output_schema': a.OUTPUT_SCHEMA,
      'replicas': ['repeat-1', 'repeat-2'],
      'numeric_access_authorized': True,
      'stage1_train_fit_authorized': True,
      'train_only_decision_authorized': True,
      'stage2_refit_authorized': False,
      'normalizer_refit_authorized': False,
      'pooled_refit_authorized': False,
      'raw_qlog_authorized': False,
      'holdout': 'CLOSED',
      'vehicle_authority': 'NONE',
      'opening_count': 0,
      'holdout_discovery': 0,
      'storage_volume': 'E_EXTERNAL_SSD',
      'storage_amendment_receipt_sha256': amendment['receipt_sha256'],
      'storage_migration_receipt_sha256': migration['receipt_sha256'],
      'mount_identity_sha256': '1' * 64,
      'volume_identity_sha256': '2' * 64,
      'root_identities': {**migration['destination_root_sha256'], 'output': '3' * 64},
      'environment': {
        'python': '3.12.13',
        'numpy': '2.5.3',
        'OPENBLAS_NUM_THREADS': '1',
        'OMP_NUM_THREADS': '1',
        'blas_build_identity_sha256': a.prior.legacy.BLAS_SHA,
        'private_build_metadata': 'SYNTHETIC_AUTHORIZATION_ONLY',
        'dtype': 'float64',
        'order': 'C',
        'rng': 'NONE',
        'zlib_runtime_version': 'SYNTHETIC_ONLY',
      },
      'resource_budget': budget,
      'capacity_preflight': {**estimate, 'free_bytes': estimate['required_bytes']},
      'source_manifests': dict.fromkeys(a.prior.MANIFEST_KEYS, '4' * 64),
    }
    auth['certificate_generator_sha256'] = auth['executor_sources']['empirical_hurdle_v4_certificate.py']
    auth['certificate_verifier_sha256'] = auth['certificate_generator_sha256']
    return p.seal(auth)

  def test_negative_prechecks_no_metadata(self):
    import copy

    mutations = [
      ('head', '0' * 40),
      ('repository', 'wrong'),
      ('branch', 'main'),
      ('policies', {}),
      ('executor_contract_receipts', {}),
      ('executor_sources', {}),
      ('v1_manifest_sha256', '0' * 64),
      ('v1_authorization_sha256', '0' * 64),
      ('replicas', ['repeat-1']),
      ('storage_amendment_receipt_sha256', '0' * 64),
      ('storage_migration_receipt_sha256', '0' * 64),
      ('stage2_refit_authorized', True),
      ('normalizer_refit_authorized', True),
      ('holdout', 'OPEN'),
      ('jobs', []),
      ('vehicle_authority', 'WRITE'),
      ('certificate_verifier_sha256', '0' * 64),
    ]
    for key, value in mutations:
      with self.subTest(key=key):
        auth = copy.deepcopy(self.fixture())
        auth[key] = value
        auth = a.p.seal({k: v for k, v in auth.items() if k != 'receipt_sha256'})
        with patch.object(a, 'metadata', side_effect=AssertionError('premature metadata')), self.assertRaises(ValueError):
          a.preflight(auth, auth['receipt_sha256'], replica='repeat-1', roots={})

  def test_wrong_trusted_hash(self):
    auth = self.fixture()
    with patch.object(a, 'metadata', side_effect=AssertionError('premature metadata')), self.assertRaises(ValueError):
      a.preflight(auth, '0' * 64, replica='repeat-1', roots={})

  def test_storage_and_capacity_environment_stop_before_metadata(self):
    auth = self.fixture()
    roots = {k: Path('/synthetic') / k for k in a.ROOTS}
    for probe in ('storage_roots', 'environment_valid'):
      with (
        self.subTest(probe=probe),
        patch.object(a, 'storage_roots', return_value=roots),
        patch.object(a, probe, side_effect=ValueError('SYNTHETIC_FAIL')),
        patch.object(a, 'metadata', side_effect=AssertionError('premature metadata')),
        self.assertRaises(ValueError),
      ):
        a.preflight(auth, auth['receipt_sha256'], replica='repeat-1', roots=roots)
    with (
      patch.object(a, 'storage_roots', return_value=roots),
      patch.object(a.prior, 'free_bytes', return_value=0),
      patch.object(a, 'metadata', side_effect=AssertionError('premature metadata')),
      self.assertRaisesRegex(ValueError, 'CAPACITY_FAILURE'),
    ):
      a.preflight(auth, auth['receipt_sha256'], replica='repeat-1', roots=roots)

  def test_unauthorized_replica(self):
    auth = self.fixture()
    with patch.object(a, 'metadata', side_effect=AssertionError('premature metadata')), self.assertRaises(ValueError):
      a.preflight(auth, auth['receipt_sha256'], replica='repeat-3', roots={})

  def test_extra_authority_rejected(self):
    auth = self.fixture()
    auth = a.p.seal({**{k: v for k, v in auth.items() if k != 'receipt_sha256'}, 'holdout_path': 'SYNTHETIC_FORBIDDEN'})
    with patch.object(a, 'metadata', side_effect=AssertionError('premature metadata')), self.assertRaises(ValueError):
      a.preflight(auth, auth['receipt_sha256'], replica='repeat-1', roots={})

  def test_wrong_model_and_anchor_before_numeric(self):
    from contextlib import ExitStack

    roots = {k: Path('/synthetic') / k for k in a.ROOTS}
    for status in ('V4_MODEL_IDENTITY_CONFLICT', 'V4_ANCHOR_IDENTITY_CONFLICT'):
      auth = self.fixture()
      with ExitStack() as stack:
        stack.enter_context(patch.object(a, 'storage_roots', return_value=roots))
        stack.enter_context(patch.object(a.prior, 'free_bytes', return_value=auth['capacity_preflight']['free_bytes']))
        stack.enter_context(patch.object(a, 'environment_valid'))
        stack.enter_context(patch.object(a, 'metadata', side_effect=ValueError(status)))
        with self.assertRaisesRegex(ValueError, status):
          a.preflight(auth, auth['receipt_sha256'], replica='repeat-1', roots=roots)

  def test_malformed_authorization(self):
    for malformed in ([], 42, 'bad'):
      with self.subTest(malformed=malformed), self.assertRaisesRegex(ValueError, 'V4_EXECUTION_AUTHORIZATION_CONFLICT'):
        a.preflight(malformed, 'a' * 64, replica='repeat-1')

  def test_precheck_sequence_and_permit_mutation(self):
    from contextlib import ExitStack
    import copy

    auth = self.fixture()
    roots = {k: Path('/synthetic') / k for k in a.ROOTS}
    lineage = {'jobs': [], 'pins': {}, 'records': (), 'source_policy': {}, 'receipts': {}, 'metadata_pins': {}}
    events = []
    original_contracts = a.contracts
    original_sources = a.sources
    with ExitStack() as stack:
      stack.enter_context(patch.object(a, 'contracts', side_effect=lambda: (events.append('PUBLIC'), original_contracts())[1]))
      stack.enter_context(patch.object(a.prior, 'current_head', side_effect=lambda: (events.append('HEAD'), auth['head'])[1]))
      stack.enter_context(patch.object(a, 'sources', side_effect=lambda: (events.append('SOURCE'), original_sources())[1]))
      stack.enter_context(patch.object(a, 'storage_roots', side_effect=lambda *args: (events.append('E_ROOTS'), roots)[1]))
      stack.enter_context(
        patch.object(a.prior, 'free_bytes', side_effect=lambda *args: (events.append('CAPACITY'), auth['capacity_preflight']['free_bytes'])[1])
      )
      stack.enter_context(patch.object(a, 'environment_valid', side_effect=lambda *args: events.append('ENV')))
      stack.enter_context(patch.object(a, 'metadata', side_effect=lambda *args: (events.append('METADATA'), copy.deepcopy(lineage))[1]))
      permit = a.preflight(auth, auth['receipt_sha256'], replica='repeat-1', roots=roots)
      self.assertEqual(events[:7], ['PUBLIC', 'HEAD', 'SOURCE', 'E_ROOTS', 'CAPACITY', 'ENV', 'METADATA'])
      permit.pack['policies']['bad'] = 'mutated'
      with self.assertRaises(ValueError):
        a.valid(permit)

  def test_synthetic_fixture_never_probes_actual_execution_environment(self):
    with patch.object(a.prior, 'environment', side_effect=ValueError('CI_IS_NOT_PRIVATE_FITTING_ENVIRONMENT')):
      auth = self.fixture()
      self.assertEqual(auth['environment']['python'], '3.12.13')
      self.assertEqual(auth['environment']['private_build_metadata'], 'SYNTHETIC_AUTHORIZATION_ONLY')

  def test_actual_environment_gate_still_rejects_mismatch(self):
    auth = self.fixture()
    for key, value in (('python', 'WRONG'), ('numpy', 'WRONG'), ('blas_build_identity_sha256', '0' * 64)):
      with self.subTest(key=key), patch.object(a.prior, 'environment', return_value={**auth['environment'], key: value}):
        with self.assertRaisesRegex(ValueError, 'V4_EXECUTION_ENVIRONMENT_CONFLICT'):
          a.environment_valid(auth)
