"""Public/synthetic only; the private capability is exercised with fake records."""

import importlib.util
import unittest


class TestDiagnosticPresent(unittest.TestCase):
  def test_additive_diagnostic_is_required(self):
    self.assertIsNotNone(importlib.util.find_spec('openpilot.tools.cyber_autotune.empirical_hurdle_v4_e2_v2_q1_diagnostic'))


from unittest.mock import patch
import numpy as np
from openpilot.tools.cyber_autotune.tests.test_empirical_hurdle_v4_e2_v2_execution import population, identity


class TestA_CDiagnostic(unittest.TestCase):
  def setUp(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_v2_q1_diagnostic as diag

    self.diag = diag
    self.blocks, self.p, self.y, self.prior, self.model = population(n=1030)

  def call(self, **kwargs):
    return self.diag.diagnose_training(self.blocks, 'HRI_D00_L01', self.model, self.p, self.y, self.prior, identity(), **kwargs)

  def test_real_frozen_calls_and_original_order(self):
    result, counters = self.call()
    self.assertTrue(result['input_rows_byte_equal'])
    self.assertTrue(result['transformed_rows_byte_equal'])
    self.assertTrue(result['coefficient_normalizer_unchanged'])
    self.assertEqual(counters['D0_TRAIN_reconstruction_calls'], 1)
    self.assertEqual(counters['TRAIN_counterfactual_Stage2_calls'], 3)
    self.assertEqual(counters['D0_full_subset_qualification_calls'], 1)
    self.assertEqual(result['calls'], {'A': 3, 'C': 1, 'B': 0, 'W': 0, 'canonical_private': 0})

  def test_private_trace_cannot_rebatch_or_add_paths(self):
    math = self.diag.q.decision.frozen.m
    original = math.predict_delta
    sizes = []

    def observed(x, model):
      sizes.append(len(x))
      return original(x, model)

    with patch.object(math, 'predict_delta', side_effect=observed):
      result, _ = self.call()
    self.assertEqual(sizes[:3], [512, 512, 4])
    self.assertEqual(len(sizes), 4)
    self.assertEqual(result['calls']['B'], 0)

  def test_signed_zero_diagnostic_is_not_byte_pass(self):
    a = np.array([0.0, 1.0])
    b = np.array([-0.0, 1.0])
    current = np.zeros(2, np.int64)
    value = self.diag.classify(a, b, current, input_equal=True, transform_equal=True, model_unchanged=True)
    self.assertIn('SIGNED_ZERO_ONLY_MISMATCH', value['cases'])
    self.assertFalse(value['comparisons']['raw_byte_equal'])
    self.assertTrue(value['comparisons']['exact_float_equal'])

  def test_one_ulp_boundary_can_change_tick(self):
    a = np.array([0.5])
    b = np.nextafter(a, np.inf)
    value = self.diag.classify(a, b, np.zeros(1, np.int64), input_equal=True, transform_equal=True, model_unchanged=True)
    self.assertIn('PROJECTED_TICK_CHANGED', value['cases'])
    self.assertEqual(value['comparisons']['max_ULP_distance'], 1)

  def test_equal_ticks_do_not_pass_delta_bytes(self):
    a = np.array([0.1])
    b = np.nextafter(a, np.inf)
    value = self.diag.classify(a, b, np.zeros(1, np.int64), input_equal=True, transform_equal=True, model_unchanged=True)
    self.assertEqual(value['comparisons']['projected_tick_mismatch_count'], 0)
    self.assertIn('BATCH_LAYOUT_SENSITIVE_MATMUL_DIFFERENCE', value['cases'])
    self.assertFalse(value['comparisons']['raw_byte_equal'])

  def test_changed_transform_has_priority(self):
    value = self.diag.classify(np.array([0.1]), np.array([0.2]), np.zeros(1, np.int64), input_equal=True, transform_equal=False, model_unchanged=True)
    self.assertIn('INPUT_OR_TRANSFORM_CONFLICT', value['cases'])
    self.assertNotIn('BATCH_LAYOUT_SENSITIVE_MATMUL_DIFFERENCE', value['cases'])

  def test_exact_equality_is_reproduction_conflict(self):
    result, _ = self.call()
    self.assertEqual(self.diag.outcome(result), 'E2_V2_Q1_DIAGNOSTIC_REPRODUCTION_CONFLICT')

  def test_invalid_prior_fails_without_repair(self):
    self.prior[0] += 1
    with self.assertRaises(ValueError):
      self.call()

  def test_nonfinite_model_fails(self):
    self.model['coefficients'][0] = np.nan
    with self.assertRaises(ValueError):
      self.call()

  def test_transformed_coefficient_identity_unchanged(self):
    before = self.model['coefficients'].tobytes()
    self.call()
    self.assertEqual(before, self.model['coefficients'].tobytes())

  def test_canonical_reference_is_synthetic_only_and_fixed_order(self):
    value = self.diag.canonical_synthetic(np.array([[1.0, 2.0, 3.0], [-1.0, 0.0, 1.0]]), np.array([4.0, 5.0, 6.0]))
    np.testing.assert_array_equal(value, [32.0, 2.0])

  def test_wrong_identity_rejected(self):
    other = identity()
    other['job'] = ['HRI_D05_L01', 'FOLD_A']
    with self.assertRaises(ValueError):
      self.diag.diagnose_training(self.blocks, 'HRI_D00_L01', self.model, self.p, self.y, self.prior, other)


class TestOneJobCapability(unittest.TestCase):
  def test_private_adapter_is_required(self):
    self.assertIsNotNone(importlib.util.find_spec('openpilot.tools.cyber_autotune.empirical_hurdle_v4_e2_v2_q1_diagnostic_private'))


class TestCapabilityBoundaries(unittest.TestCase):
  def setUp(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_v2_q1_diagnostic_private as adapter

    self.a = adapter
    self.route, self.segment = 'a' * 64, 'b' * 64
    self.phase = adapter.Phase(['HRI_D00_L01', 'FOLD_A'], self.route)
    self.phase.bind_segments([self.segment])
    self.member = 'repeat-1/routes/' + self.route + '/segments/' + self.segment + '/arrays/command.normalized.npy'
    self.phase.register('CAUSAL', self.member, 'array')

  def plan(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e_inputs as inp

    return {
      ('CAUSAL', self.member): {
        'owner': 'CAUSAL',
        'member': self.member,
        'raw_sha256': 'c' * 64,
        'cap': inp.caps((10,), '<f8')[1],
        'dtype': '<f8',
        'shape': [10],
        'compressed': False,
      }
    }

  def test_numeric_before_durable_allowlist_denied(self):
    with self.assertRaises(ValueError):
      self.phase.authorize('CAUSAL', self.member, 'array')

  def test_exact_array_after_readback_allowed(self):
    self.phase.enable(self.plan(), 'd' * 64, 'd' * 64)
    self.phase.authorize('CAUSAL', self.member, 'array')

  def test_readback_mismatch_does_not_enable(self):
    with self.assertRaises(ValueError):
      self.phase.enable(self.plan(), 'd' * 64, 'e' * 64)
    self.assertFalse(self.phase.enabled)

  def test_unbound_derived_segment_denied(self):
    with self.assertRaises(ValueError):
      self.phase.register('DERIVED', 'repeat-1/segments/' + 'c' * 64 + '/angle_tick.npy', 'array')

  def test_wrong_route_denied(self):
    with self.assertRaises(ValueError):
      self.phase.register('CAUSAL', self.member.replace(self.route, 'd' * 64), 'array')

  def test_duplicate_segment_binding_denied(self):
    with self.assertRaises(ValueError):
      self.phase.bind_segments([self.segment])

  def test_coefficients_outside_exact_job_denied(self):
    self.phase.enable(self.plan(), 'd' * 64, 'd' * 64)
    with self.assertRaises(ValueError):
      self.phase.authorize('V1', 'candidates/HRI_D00_L01/FOLD_B/stage2/model/receipt.json', 'metadata')

  def test_sensitive_mixed_carrier_blocked(self):
    with self.assertRaises(ValueError):
      self.phase.authorize('V4', 'candidates/HRI_D00_L01/FOLD_A/train/receipt.json', 'metadata')

  def test_unapproved_source_field_denied(self):
    with self.assertRaises(ValueError):
      self.phase.register('CAUSAL', self.member.replace('command.normalized', 'GPS'), 'array')

  def test_path_traversal_denied(self):
    with self.assertRaises(ValueError):
      self.phase.authorize('V4', '../manifest.json', 'metadata')

  def test_dev_never_unlocked(self):
    self.phase.enable(self.plan(), 'd' * 64, 'd' * 64)
    with self.assertRaises(ValueError):
      self.phase.require_dev()
    with self.assertRaises(ValueError):
      self.phase.authorize('V4', 'candidates/HRI_D00_L01/FOLD_A/dev/manifest.json', 'metadata')

  def test_allowlist_cannot_include_other_job(self):
    plan = self.plan()
    key = ('V1', 'candidates/HRI_D00_L01/FOLD_B/stage2/model/coefficients.npy.gz')
    plan[key] = dict(next(iter(plan.values())), owner=key[0], member=key[1])
    with self.assertRaises(ValueError):
      self.phase.enable(plan, 'd' * 64, 'd' * 64)
    self.assertFalse(self.phase.enabled)

  def test_invalid_cap_and_pickle_dtype_denied(self):
    for field, value in [('cap', 1), ('dtype', '|O')]:
      with self.subTest(field=field):
        plan = self.plan()
        plan['CAUSAL', self.member][field] = value
        with self.assertRaises(ValueError):
          self.phase.enable(plan, 'd' * 64, 'd' * 64)
        self.assertFalse(self.phase.enabled)

  def test_current_grant_cannot_be_prior_e2_grant(self):
    gate = {'head': 'a' * 40, 'mission': 'STAGE1_V4_E2_V2_ADDITIVE_RUNNER_AND_FRESH_EXECUTION', 'protocol_raw_sha256': 'b' * 64}
    with self.assertRaises(ValueError):
      self.a.verify_current_gate(gate, 'a' * 40, 'b' * 64)

  def valid_gate(self):
    return {
      'head': 'a' * 40,
      'mission': self.a.MISSION,
      'protocol_raw_sha256': 'b' * 64,
      'ci': {'head_sha': 'a' * 40, 'status': 'completed', 'conclusion': 'success'},
      'diagnostic_runs': 1,
      **dict.fromkeys(
        ('DEV_authorized', 'D2_selection_authorized', 'E2_resume_authorized', 'HOLDOUT_authorized', 'vehicle_authorized', 'V5_authorized'), False
      ),
    }

  def test_exact_grant_and_ci_required(self):
    gate = self.valid_gate()
    self.a.verify_current_gate(gate, 'a' * 40, 'b' * 64)
    gate['ci']['conclusion'] = 'failure'
    with self.assertRaises(ValueError):
      self.a.verify_current_gate(gate, 'a' * 40, 'b' * 64)

  def test_boolean_is_not_single_diagnostic_count(self):
    gate = self.valid_gate()
    gate['diagnostic_runs'] = True
    with self.assertRaises(ValueError):
      self.a.verify_current_gate(gate, 'a' * 40, 'b' * 64)


def planned_provider():
  """Complete synthetic metadata; one TRAIN segment, 153 other-route segments."""
  from types import SimpleNamespace
  from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_v2_q1_diagnostic_private as a
  from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_inputs as inp
  from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e_inputs as e1

  route, other, segment = 'a' * 64, 'b' * 64, 'c' * 64
  ids = [segment, *[format(i, '064x') for i in range(1, 154)]]
  phase = a.Phase(['HRI_D00_L01', 'FOLD_A'], route)
  prefix = 'candidates/HRI_D00_L01/FOLD_A'

  def desc(n, dtype):
    return {'shape': [n], 'dtype': dtype, 'order': 'C', 'file_sha256': 'd' * 64, 'array_sha256': 'e' * 64}

  source = {'route_id': route, 'segment_sha256': segment, 'receipt_sha256': '1' * 64, 'arrays': {name: desc(10, '<f8') for name in a.CAUSAL}}
  derived = {
    'source_receipt_sha256': '1' * 64,
    'policy_sha256': '2' * 64,
    'arrays': {name: desc(10, '|b1' if name in ('rail', 'model_eligible') else '<i8') for name in a.DERIVED},
  }
  norm = {
    'candidate_id': 'HRI_D00_L01',
    'fold': 'FOLD_A',
    'stage': 'STAGE2',
    'receipt_sha256': '3' * 64,
    'arrays': {name: desc(5, '|b1' if name == 'constant' else '<i8' if name == 'effective' else '<f8') for name in a.NORMALIZER},
  }
  model = {'candidate_id': 'HRI_D00_L01', 'fold': 'FOLD_A', 'normalizer_sha256': '3' * 64, 'arrays': {'coefficients': desc(5, '<f8')}}
  references = [
    {
      'train_route': route,
      'train_count': 4,
      'train_anchor_sha256': '4' * 64,
      'stage2': {'normalizer_receipt_sha256': '3' * 64, 'model_receipt_sha256': '5' * 64, 'coefficient_sha256': 'e' * 64},
    }
  ]
  fields = []
  roots = {'V4': '/synthetic/v4', 'V1': '/synthetic/v1'}
  for owner, tail, dtype in [('V4', 'combined_probability', '<f8'), ('V1', 'move_label', '|b1'), ('V1', 'prior_delta_tick', '<i8')]:
    fields.append(
      {
        'owner': owner,
        'role': 'TRAIN',
        'path': roots[owner] + '/' + prefix + '/train/' + tail + '.npy.gz',
        'anchor_sha256': '4' * 64,
        'descriptor': desc(4, dtype),
        'n': 4,
        'dtype': dtype,
      }
    )
  metadata = {
    ('CAUSAL', 'repeat-1/manifest.json'): {'receipt_sha256': '6' * 64},
    ('CAUSAL', 'authorization.json'): {'segments': {route: [segment], other: ids[1:]}},
    ('DERIVED', 'repeat-1/derived-index.json'): {'segments': [{'content_sha256': i, 'receipt_sha256': '7' * 64} for i in ids]},
    ('DERIVED', 'repeat-1/results.json'): {'admission_sha256': '8' * 64},
    ('DERIVED', 'repeat-1/admission.json'): {'manifest_sha256': '6' * 64},
    ('CAUSAL', 'repeat-1/routes/' + route + '/segments/' + segment + '/receipt.json'): source,
    ('DERIVED', 'repeat-1/segments/' + segment + '/receipt.json'): derived,
    ('V1', prefix + '/stage2/normalizer/receipt.json'): norm,
    ('V1', prefix + '/stage2/model/receipt.json'): model,
  }
  maps = {owner: {} for owner in ('V4', 'V1', 'CAUSAL', 'DERIVED')}
  for field in fields:
    member = field['path'][len(roots[field['owner']]) + 1 :]
    maps[field['owner']][member] = 'd' * 64
  for name in a.NORMALIZER:
    maps['V1'][prefix + '/stage2/normalizer/' + name + '.npy.gz'] = 'd' * 64
  maps['V1'][prefix + '/stage2/model/coefficients.npy.gz'] = 'd' * 64
  for name in a.CAUSAL:
    maps['CAUSAL']['repeat-1/routes/' + route + '/segments/' + segment + '/arrays/' + name + '.npy'] = 'd' * 64
  for name in a.DERIVED:
    maps['DERIVED']['repeat-1/segments/' + segment + '/' + name + '.npy'] = 'd' * 64
  events = []

  def read(owner, member, **_kwargs):
    phase.authorize(owner, member, 'metadata')
    events.append((owner, member))
    return metadata[owner, member]

  reader = SimpleNamespace(phase=phase, roots=roots, maps=maps, metadata=read)
  klass = a.provider_type({'empirical_hurdle_v4_e2_inputs': inp, 'empirical_hurdle_v4_e_inputs': e1})
  provider = klass.__new__(klass)
  provider.reader, provider.references = reader, references
  provider.bound_jobs = [{'candidate_id': 'HRI_D00_L01', 'fold': 'FOLD_A', 'fields': fields}]
  provider.v4_auth = {'source_manifests': {'causal': '6' * 64, 'derived_index': '7' * 64, 'derived_result': '8' * 64}}
  provider.source_policy = {'route_ids': [route, other], 'excluded_qlog_content_sha256': [], 'receipt_sha256': '2' * 64}
  return provider, metadata, events


class TestMetadataPlan(unittest.TestCase):
  def test_only_failed_train_route_planned_no_numeric_open(self):
    provider, _, events = planned_provider()
    plan = provider.prepare(0)
    self.assertEqual(len(plan), 17)
    self.assertEqual(sum(owner in ('CAUSAL', 'DERIVED') for owner, _ in plan), 8)
    self.assertEqual(len(provider.source_plan), 1)
    self.assertEqual(len(events), 9)
    self.assertFalse(provider.reader.phase.enabled)
    for owner, member in plan:
      with self.assertRaises(ValueError):
        provider.reader.phase.authorize(owner, member, 'array')
    provider.reader.phase.enable(plan, 'f' * 64, 'f' * 64)
    for owner, member in plan:
      provider.reader.phase.authorize(owner, member, 'array')

  def test_anchor_count_dtype_metadata_mutation_prevents_numeric(self):
    for field, value in [('anchor_sha256', 'f' * 64), ('n', 5), ('dtype', '<i8')]:
      with self.subTest(field=field):
        provider, _, _ = planned_provider()
        provider.bound_jobs[0]['fields'][0][field] = value
        with self.assertRaises(ValueError):
          provider.prepare(0)
        self.assertFalse(provider.reader.phase.enabled)

  def test_model_receipt_identity_and_dimension_rejected(self):
    for field, value in [('fold', 'FOLD_B'), ('normalizer_sha256', 'f' * 64)]:
      provider, metadata, _ = planned_provider()
      metadata['V1', 'candidates/HRI_D00_L01/FOLD_A/stage2/model/receipt.json'][field] = value
      with self.assertRaises(ValueError):
        provider.prepare(0)
      self.assertFalse(provider.reader.phase.enabled)

  def test_bad_coefficients_descriptor_denied_before_arrays(self):
    for key, value in [('dtype', '<f4'), ('shape', [6]), ('order', 'F'), ('array_sha256', 'f' * 64)]:
      provider, metadata, _ = planned_provider()
      metadata['V1', 'candidates/HRI_D00_L01/FOLD_A/stage2/model/receipt.json']['arrays']['coefficients'][key] = value
      with self.assertRaises(ValueError):
        provider.prepare(0)
      self.assertFalse(provider.reader.phase.enabled)

  def test_route_mismatch_blocks_segment_reads(self):
    provider, _, events = planned_provider()
    provider.references[0]['train_route'] = 'f' * 64
    with self.assertRaises(ValueError):
      provider.prepare(0)
    self.assertEqual(len(events), 5)


class TestReferenceAndPreflight(unittest.TestCase):
  def setUp(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_v2_q1_diagnostic_private as a

    self.a = a

  def reference_fixture(self):
    a = self.a
    p = a.control.public('empirical-hurdle-stage1-v4-e2-execution-protocol-v2.json')
    index = 2  # Public, fabricated abort fixture; never a private failed-job lookup.
    j = p['jobs'][index]
    job = [j['candidate_id'], j['fold']]
    reference = a.control.public('empirical-hurdle-fit-cv-results-v1.json')['jobs'][index]
    identity = {
      'job': job,
      'anchor_sha256': reference['train_anchor_sha256'],
      'stage2_receipts': {k: reference['stage2'][k] for k in ('normalizer_receipt_sha256', 'model_receipt_sha256', 'coefficient_sha256')},
      'source_map_sha256': a.control.sha(a.control.canonical(p['source_sha256'])),
    }
    binding = {'head': a.FAILED_HEAD, 'gate_receipt_sha256': 'a' * 64, 'receipt_sha256': 'b' * 64}
    abort = {
      'schema': 'V4_E2_V2_ABORT_ENVELOPE_V1',
      'source_writes': 0,
      'forbidden_attempts': 0,
      'binding_receipt_sha256': 'b' * 64,
      'protocol_raw_sha256': a.v2.PROTOCOL_SHA,
      'receipt_sha256': 'c' * 64,
      'status': 'E2_D0_TRAIN_NUMERICAL_EQUIVALENCE_NOT_PROVEN_FAIL_CLOSED',
      'stage': 'Q1',
      'qualified_TRAIN_jobs': 2,
      'failed_job': job,
      'last_qualification_attempt': {
        'job': job,
        'identity': identity,
        'kind': 'Q1',
        'status': 'BYTE_EXACT_MISMATCH',
        'dtype': '<f8',
        'nonempty': True,
        'numerical_calls': 1,
        'Q2': 'NOT_EXECUTED_DIAGNOSTIC',
      },
    }
    ref = {
      'schema': 'V4_E2_V2_Q1_EXACT_FAILED_REFERENCE_V1',
      'role': 'TRAIN',
      'job': job,
      'job_index_zero_based': index,
      'identity': identity,
      'failed_binding_receipt_sha256': 'b' * 64,
      'failed_abort_receipt_sha256': 'c' * 64,
      'protocol_raw_sha256': a.v2.PROTOCOL_SHA,
      'protocol_receipt_sha256': p['receipt_sha256'],
      'expected_train_count': reference['train_count'],
    }
    verified = {'abort_receipt_sha256': 'c' * 64, 'binding_receipt_sha256': 'b' * 64}
    return ref, binding, abort, verified, {'receipt_sha256': 'a' * 64}, p, {}, b''

  def test_abort_identity_authenticates_against_public_model_and_source(self):
    with patch.object(self.a.v2, 'validate_binding'):
      self.a.authenticate_reference(*self.reference_fixture())

  def test_resealed_identity_model_anchor_source_count_mutations_denied(self):
    for field in ('anchor_sha256', 'stage2_receipts', 'source_map_sha256', 'expected_train_count'):
      args = self.reference_fixture()
      ref = args[0]
      if field == 'expected_train_count':
        ref[field] += 1
      elif field == 'stage2_receipts':
        ref['identity'][field]['coefficient_sha256'] = 'f' * 64
      else:
        ref['identity'][field] = 'f' * 64
      # Shared synthetic abort identity is changed too, proving public pins matter.
      with patch.object(self.a.v2, 'validate_binding'):
        with self.assertRaises(ValueError):
          self.a.authenticate_reference(*args)

  def test_current_ci_review_policy_failure_precedes_historical_controls(self):
    from pathlib import Path
    from types import SimpleNamespace

    a = self.a
    p = a.control.public('empirical-hurdle-stage1-v4-e2-v2-q1-diagnostic-protocol.json')
    raw = a.control.canonical(p)
    head = 'a' * 40
    for failure in ('ci', 'review', 'source_policy'):
      gate = {
        'head': head,
        'mission': a.MISSION,
        'protocol_raw_sha256': a.control.sha(raw),
        'diagnostic_runs': 1,
        'ci': {'head_sha': head, 'status': 'completed', 'conclusion': 'failure' if failure == 'ci' else 'success'},
        **dict.fromkeys(
          ('DEV_authorized', 'D2_selection_authorized', 'E2_resume_authorized', 'HOLDOUT_authorized', 'vehicle_authorized', 'V5_authorized'), False
        ),
      }
      modules = {'empirical_s2_ri_policy': SimpleNamespace(policy=lambda: {'receipt_sha256': 'b' * 64})}

      def git(*args):
        if args == ('branch', '--show-current'):
          return 'feature/cyber-autotune'
        if args[0] == 'status':
          return ''
        if args[0] == 'merge-base':
          return a.BASELINE
        return head

      def private(path, *_args, gate=gate):
        return a.control.canonical(a.control.sealed(gate if path.name == 'execution-gate.json' else {}))

      with (
        patch.object(a.control, 'git', side_effect=git),
        patch.object(a, 'load_sources', return_value=(p, raw, {'source_policy_receipt_sha256': 'c' * 64}, {}, b'', modules)),
        patch.object(a.control, 'private', side_effect=private),
        patch.object(a.control, 'verify_reviews', side_effect=ValueError('REVIEW') if failure == 'review' else None),
        patch.object(a.control, 'controls', side_effect=AssertionError('ORIGINAL_METADATA_READ')) as controls,
      ):
        with self.assertRaises(ValueError):
          a.preflight(Path('/synthetic'))
        controls.assert_not_called()


class TestFrozenPublicContract(unittest.TestCase):
  def test_protocol_receipt_and_source_bytes(self):
    from pathlib import Path
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_execution as control

    p = control.checked((control.PUBLIC / 'empirical-hurdle-stage1-v4-e2-v2-q1-diagnostic-protocol.json').read_bytes())
    self.assertEqual(p['synthetic']['fixed_count'], 180)
    self.assertEqual(p['private_scope']['D2'], False)
    self.assertEqual(p['private_scope']['DEV'], False)
    # Source hashes are a runtime boundary; the protocol itself has no self-hash cycle.
    for name, digest in {**p['source_sha256'], **p['diagnostic_source_sha256']}.items():
      self.assertEqual(control.sha((Path(control.SOURCE) / name).read_bytes()), digest, name)

  def test_frozen_resource_bound_includes_observation_matrices(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_v2_q1_diagnostic_private as adapter

    p = adapter.control.public('empirical-hurdle-stage1-v4-e2-v2-q1-diagnostic-protocol.json')
    self.assertEqual(adapter.resource_plan(p['resources']), 6086568806)
    bad = dict(p['resources'], analytical_live_bound_bytes=5574680630)
    with self.assertRaises(ValueError):
      adapter.resource_plan(bad)

  def test_no_subprocess_inside_numeric_run(self):
    import inspect
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_v2_q1_diagnostic_private as adapter

    self.assertNotIn('control.git(', inspect.getsource(adapter.run))


if __name__ == '__main__':
  unittest.main()
