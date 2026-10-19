"""Writer-produced public fixtures; never private input discovery."""

import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from openpilot.tools.cyber_autotune import empirical_hurdle_fit_cv_execution as writer
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_v2_q1_reader_repair as repaired
from openpilot.tools.cyber_autotune.tests.test_empirical_hurdle_v4_e2_v2_q1_diagnostic import planned_provider

WRITER_SHA = 'a952eb4986f47e0335bf355ee74868755f14b592d05070008a0b117979d4e635'


def writer_fixture(root, singular=False, constant=False):
  x = np.column_stack((np.ones(10), np.eye(10, 4, dtype=np.float64) + np.arange(10, dtype=np.float64)[:, None]))
  if constant:
    x[:, -1] = 7.0
  norm = writer.m.normalizer(x, role='TRAIN', stage='STAGE2')
  effective = len(norm['effective'])
  model = {
    'normalizer': norm,
    'coefficients': np.arange(1, effective + 1, dtype=np.float64),
    'nominal_coefficients': np.array([1.0, 2.0, 3.0, 4.0, 5.0]),
    'rank': effective,
    'effective_x_sha_input': x,
  }
  if singular:
    model['singular_values'] = np.arange(effective, 0, -1, dtype=np.float64)
  reference = writer.save_model(root, model, 'HRI_D00_L01', {'fold': 'FOLD_A', 'train': 'a' * 64}, '4' * 64, 10, {'receipt_sha256': '9' * 64}, 'STAGE2')
  norm = json.loads((root / 'normalizer/receipt.json').read_bytes())
  receipt = json.loads((root / 'model/receipt.json').read_bytes())
  return norm, receipt, reference


def provider_fixture(norm, model, reference):
  from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_inputs as inp
  from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e_inputs as e1

  old, metadata, events = planned_provider()
  klass = repaired.provider_type({'empirical_hurdle_v4_e2_inputs': inp, 'empirical_hurdle_v4_e_inputs': e1})
  provider = klass.__new__(klass)
  provider.__dict__.update(old.__dict__)
  prefix = 'candidates/HRI_D00_L01/FOLD_A/stage2/'
  metadata['V1', prefix + 'normalizer/receipt.json'] = norm
  metadata['V1', prefix + 'model/receipt.json'] = model
  provider.references[0]['stage2'] = reference
  provider.references[0].update(train_count=12, train_anchor_sha256='6' * 64)
  for field in provider.bound_jobs[0]['fields']:
    field.update(n=12, anchor_sha256='6' * 64)
    field['descriptor']['shape'] = [12]
  for (owner, _member), row in metadata.items():
    if owner in ('CAUSAL', 'DERIVED') and 'arrays' in row:
      for desc in row['arrays'].values():
        desc['shape'] = [20]
  for role, row in [('normalizer', norm), ('model', model)]:
    for name, desc in row['arrays'].items():
      provider.reader.maps['V1'][prefix + role + '/' + name + '.npy.gz'] = desc['file_sha256']
  return provider, metadata, events


class TestWriterReceipts(unittest.TestCase):
  def setUp(self):
    self.temp = tempfile.TemporaryDirectory()
    self.root = Path(self.temp.name)

  def tearDown(self):
    self.temp.cleanup()

  def test_writer_source_exact(self):
    self.assertEqual(hashlib.sha256(Path(writer.__file__).read_bytes()).hexdigest(), WRITER_SHA)

  def test_writer_required_arrays_pass_metadata_without_extra_numeric_access(self):
    norm, model, reference = writer_fixture(self.root / 'stage2')
    provider, _, _ = provider_fixture(norm, model, reference)
    plan = provider.prepare(0)
    self.assertEqual(set(model['arrays']), {'coefficients', 'nominal_coefficients'})
    self.assertFalse(provider.reader.phase.enabled)
    self.assertNotEqual(provider.references[0]['train_anchor_sha256'], model['train_anchor_sha256'])
    self.assertLess(model['train_count'], provider.references[0]['train_count'])
    self.assertEqual(len(plan), 17)
    self.assertFalse(any('nominal_coefficients' in member for _, member in plan))

  def test_writer_optional_singular_passes_metadata_only(self):
    norm, model, reference = writer_fixture(self.root / 'stage2', True)
    provider, _, _ = provider_fixture(norm, model, reference)
    plan = provider.prepare(0)
    self.assertEqual(set(model['arrays']), {'coefficients', 'nominal_coefficients', 'singular_values'})
    self.assertFalse(any('singular_values' in member or 'nominal_coefficients' in member for _, member in plan))

  def negative(self, mutate, expected=None):
    norm, model, reference = writer_fixture(self.root / 'stage2', True)
    mutate(norm, model, reference)
    provider, _, _ = provider_fixture(norm, model, reference)
    with self.assertRaisesRegex(ValueError, expected or 'Q1_'):
      provider.prepare(0)
    self.assertFalse(provider.reader.phase.enabled)

  @staticmethod
  def reseal(row):
    row.pop('receipt_sha256')
    row.update(repaired.control.sealed(row))

  def test_missing_nominal_rejected(self):
    def change(n, m, r):
      del m['arrays']['nominal_coefficients']
      self.reseal(m)
      r['model_receipt_sha256'] = m['receipt_sha256']

    self.negative(change, 'Q1_MODEL_DESCRIPTOR_SET_CONFLICT')

  def test_unknown_model_key_rejected(self):
    def change(n, m, r):
      m['arrays']['extra'] = copy.deepcopy(m['arrays']['coefficients'])
      self.reseal(m)
      r['model_receipt_sha256'] = m['receipt_sha256']

    self.negative(change, 'Q1_MODEL_DESCRIPTOR_SET_CONFLICT')

  def test_unsealed_descriptor_corruption_rejected(self):
    self.negative(lambda n, m, r: m['arrays']['coefficients'].update(dtype='<f4'), 'Q1_MODEL_SOURCE_HASH_CONFLICT')

  def test_resealed_descriptor_format_corruption_rejected(self):
    def change(n, m, r):
      m['arrays']['coefficients']['storage_format'] = 'NPY'
      self.reseal(m)
      r['model_receipt_sha256'] = m['receipt_sha256']

    self.negative(change, 'Q1_MODEL_DESCRIPTOR_FORMAT_CONFLICT')

  def test_normalizer_model_identity_conflict(self):
    def change(n, m, r):
      m['normalizer_sha256'] = 'f' * 64
      self.reseal(m)
      r['model_receipt_sha256'] = m['receipt_sha256']

    self.negative(change, 'Q1_MODEL_NORMALIZER_IDENTITY_CONFLICT')

  def test_candidate_conflict(self):
    def change(n, m, r):
      m['candidate_id'] = 'HRI_D05_L01'
      self.reseal(m)
      r['model_receipt_sha256'] = m['receipt_sha256']

    self.negative(change, 'Q1_METADATA_BINDING_CONFLICT')

  def test_fold_conflict(self):
    def change(n, m, r):
      m['fold'] = 'FOLD_B'
      self.reseal(m)
      r['model_receipt_sha256'] = m['receipt_sha256']

    self.negative(change, 'Q1_METADATA_BINDING_CONFLICT')

  def test_subset_train_anchor_conflict(self):
    def change(n, m, r):
      m['train_anchor_sha256'] = 'f' * 64
      self.reseal(m)
      r['model_receipt_sha256'] = m['receipt_sha256']

    self.negative(change, 'Q1_METADATA_BINDING_CONFLICT')

  def test_model_not_stage2(self):
    def change(n, m, r):
      m['stage'] = 'STAGE1'
      self.reseal(m)
      r['model_receipt_sha256'] = m['receipt_sha256']

    self.negative(change, 'Q1_MODEL_NORMALIZER_IDENTITY_CONFLICT')

  def test_numeric_allowlist_is_not_metadata_arrays(self):
    norm, model, reference = writer_fixture(self.root / 'stage2', True)
    provider, _, _ = provider_fixture(norm, model, reference)
    phase = provider.reader.phase
    member = 'candidates/HRI_D00_L01/FOLD_A/stage2/model/coefficients.npy.gz'
    with self.assertRaisesRegex(ValueError, 'ALLOWLIST'):
      phase.authorize('V1', member, 'array')
    plan = provider.prepare(0)
    with self.assertRaises(ValueError):
      phase.enable(plan, 'a' * 64, 'b' * 64)
    self.assertFalse(phase.enabled)
    phase.enable(plan, 'a' * 64, 'a' * 64)
    phase.authorize('V1', member, 'array')
    for name in ('nominal_coefficients', 'singular_values'):
      with self.assertRaises(ValueError):
        phase.authorize('V1', member.replace('coefficients', name), 'array')
    with self.assertRaises(ValueError):
      phase.authorize('V1', member.replace('FOLD_A', 'FOLD_B'), 'array')
    with self.assertRaises(ValueError):
      phase.authorize('V1', member.replace('stage2', 'stage1'), 'array')

  def test_cannot_enable_forbidden_array_even_with_valid_metadata(self):
    norm, model, reference = writer_fixture(self.root / 'stage2', True)
    provider, _, _ = provider_fixture(norm, model, reference)
    plan = provider.prepare(0)
    key = ('V1', 'candidates/HRI_D00_L01/FOLD_A/stage2/model/nominal_coefficients.npy.gz')
    plan[key] = dict(next(iter(plan.values())), owner='V1', member=key[1])
    with self.assertRaises(ValueError):
      provider.reader.phase.enable(plan, 'a' * 64, 'a' * 64)
    self.assertFalse(provider.reader.phase.enabled)

  def test_optional_descriptor_metadata_is_verified_without_array_open(self):
    def change(n, m, r):
      m['arrays']['singular_values']['shape'] = [6]
      self.reseal(m)
      r['model_receipt_sha256'] = m['receipt_sha256']

    self.negative(change, 'Q1_MODEL_DESCRIPTOR_FORMAT_CONFLICT')

  def test_manifest_raw_hash_mismatch_denied(self):
    norm, model, reference = writer_fixture(self.root / 'stage2')
    provider, _, _ = provider_fixture(norm, model, reference)
    provider.reader.maps['V1']['candidates/HRI_D00_L01/FOLD_A/stage2/model/nominal_coefficients.npy.gz'] = 'f' * 64
    with self.assertRaisesRegex(ValueError, 'Q1_MODEL_SOURCE_HASH_CONFLICT'):
      provider.prepare(0)


class TestAbortLedger(unittest.TestCase):
  def test_control_metadata_numeric_ledgers_separate(self):
    from types import SimpleNamespace

    ledger = repaired.Telemetry()
    repaired.control.CONTROL_EVENTS.append({'name': 'synthetic.json', 'bytes': 7, 'raw_sha256': 'a' * 64})
    ledger.reader = SimpleNamespace(
      events=[{'kind': 'metadata', 'file_openings': 1, 'bytes_read': 11}, {'kind': 'array', 'file_openings': 1, 'bytes_read': 13}]
    )
    value = ledger.snapshot()
    self.assertEqual(value['control_reads'], {'files': 1, 'bytes': 7, 'scope': 'SUCCESSFULLY_COMPLETED_READS'})
    self.assertEqual(value['input_reads']['metadata'], {'files': 1, 'bytes': 11})
    self.assertEqual(value['input_reads']['array'], {'files': 1, 'bytes': 13})
    self.assertEqual(value['identity']['current_grant_receipt_sha256'], 'NOT_RECORDED')
    self.assertEqual(value['process_peak_rss']['unit'], 'KiB')
    self.assertFalse(value['durable_array_allowlist_enabled'])
    self.assertFalse(value['actual_A_C_started'])
    self.assertTrue(all(v == 0 for v in value['forbidden_operation_counters'].values()))

  def test_predicate_sanitization_never_exposes_error_contents(self):
    for reason in ('/private/path', 'candidate=SECRET', 'Q1_BAD /row', 'some coefficients 42'):
      self.assertEqual(repaired.predicate(ValueError(reason), 'METADATA_PLANNING'), 'Q1_METADATA_BINDING_CONFLICT')
    self.assertEqual(repaired.predicate(ValueError('Q1_MODEL_DESCRIPTOR_SET_CONFLICT'), 'METADATA_PLANNING'), 'Q1_MODEL_DESCRIPTOR_SET_CONFLICT')

  def test_output_is_exclusive_bounded_and_restrictive(self):
    import os

    with tempfile.TemporaryDirectory() as name:
      root = Path(name)
      os.chmod(root, 0o700)
      ledger = repaired.Telemetry()
      value = repaired.control.sealed({'synthetic': True})
      repaired.persist(root, 'attempt.json', value, ledger)
      self.assertEqual((root / 'attempt.json').stat().st_mode & 0o777, 0o600)
      with self.assertRaises(FileExistsError):
        repaired.persist(root, 'attempt.json', value, ledger)
      with self.assertRaises(ValueError):
        repaired.persist(root, '../source.json', value, ledger)
      self.assertEqual(len(ledger.outputs), 1)

  def test_entry_abort_seals_counters_and_does_not_retry(self):
    import os

    with tempfile.TemporaryDirectory() as name:
      root = Path(name)
      os.chmod(root, 0o700)
      root = root / 'v4-e2-v2-q1-reader-repair-diagnostic-v2'
      root.mkdir(mode=0o700)
      protocol = repaired.control.sealed(
        {
          'source_sha256': {},
          'diagnostic_source_sha256': {},
          'resources': {'address_space_bytes': 8589934592, 'cpu_seconds': 900, 'result_bytes_per_file': 8388608, 'wall_seconds': 1800},
        }
      )
      (root / repaired.PROTOCOL).write_bytes(repaired.control.canonical(protocol))
      with (
        patch.object(repaired, 'authorize_output'),
        patch.object(repaired, 'resource_plan'),
        patch.object(repaired.resource, 'setrlimit'),
        patch.object(repaired.signal, 'alarm'),
        patch.object(repaired.signal, 'signal'),
        patch.object(repaired.control, 'PUBLIC', root),
        patch.object(repaired.control, 'git', return_value='a' * 40),
        patch.object(repaired, 'preflight', side_effect=ValueError('Q1_METADATA_BINDING_CONFLICT')) as preflight,
      ):
        self.assertEqual(repaired.run(root), 'E2_Q1_DIAGNOSTIC_INPUT_BINDING_INSUFFICIENT')
        self.assertEqual(preflight.call_count, 1)
        before = (root / 'telemetry.json').read_bytes()
        repaired.run(root)
        self.assertEqual(preflight.call_count, 1)
        self.assertEqual((root / 'telemetry.json').read_bytes(), before)
      value = repaired.control.checked(before)
      self.assertEqual(value['stage'], 'PREFLIGHT')
      self.assertFalse(value['actual_A_C_started'])
      self.assertEqual(value['input_reads']['array']['files'], 0)
      files = ['attempt.json', 'execution-envelope.json', 'telemetry.json']
      self.assertEqual(value['output_files_total'], len(files))
      self.assertEqual(value['output_bytes_total'], sum((root / f).stat().st_size for f in files))
      self.assertGreaterEqual(value['process_cpu_user_seconds'], 0)

  def test_original_reader_and_scientific_sources_immutable(self):
    pins = repaired.control.public('empirical-hurdle-stage1-v4-e2-v2-q1-diagnostic-protocol.json')
    for name, digest in {**pins['source_sha256'], **pins['diagnostic_source_sha256']}.items():
      self.assertEqual(hashlib.sha256((repaired.control.SOURCE / name).read_bytes()).hexdigest(), digest)

  def test_memory_error_is_resource_not_reproduction_conflict(self):
    for phase in ('ENTRY', 'PREFLIGHT', 'METADATA_PLANNING', 'NUMERIC_INPUT', 'A_C_DIAGNOSTIC'):
      self.assertEqual(repaired.predicate(MemoryError(), phase), 'Q1_DIAGNOSTIC_RESOURCE_BOUND')
    self.assertEqual(repaired.predicate(RuntimeError('error'), 'A_C_DIAGNOSTIC'), 'Q1_DIAGNOSTIC_NUMERICAL_EXECUTION_INCOMPLETE')

  def test_wrong_output_authority_causes_no_file_write(self):

    with tempfile.TemporaryDirectory() as name:
      root = Path(name) / 'v4-e2-v2-q1-reader-repair-diagnostic-v2'
      root.mkdir(mode=0o700)
      with (
        patch.object(repaired, 'authorize_output', side_effect=ValueError('Q1_OUTPUT_SCOPE_CONFLICT')),
        patch.object(repaired, 'resource_plan'),
        patch.object(repaired.resource, 'setrlimit'),
        patch.object(repaired.signal, 'alarm'),
        patch.object(repaired.signal, 'signal'),
        patch.object(repaired.control, 'git', return_value='a' * 40),
        patch.object(repaired, 'preflight') as preflight,
      ):
        repaired.run(root)
      self.assertFalse((root / 'attempt.json').exists())
      self.assertFalse((root / 'telemetry.json').exists())
      preflight.assert_not_called()


class TestReducedEffectiveWriter(unittest.TestCase):
  def test_constant_nominal_column_uses_effective_coeff_shape(self):
    with tempfile.TemporaryDirectory() as name:
      norm, model, reference = writer_fixture(Path(name) / 'stage2', True, True)
      provider, _, _ = provider_fixture(norm, model, reference)
      plan = provider.prepare(0)
      self.assertEqual(model['arrays']['coefficients']['shape'], [4])
      self.assertEqual(model['arrays']['nominal_coefficients']['shape'], [5])
      self.assertEqual(model['arrays']['singular_values']['shape'], [4])
      self.assertEqual(plan['V1', 'candidates/HRI_D00_L01/FOLD_A/stage2/model/coefficients.npy.gz']['shape'], [4])


class TestDescriptorAndMissingAccounting(unittest.TestCase):
  def test_each_descriptor_field_tamper_rejected(self):
    with tempfile.TemporaryDirectory() as name:
      norm, model, reference = writer_fixture(Path(name) / 'stage2', True)
      for field, value in [
        ('dtype', '<f4'),
        ('shape', [6]),
        ('order', 'F'),
        ('filename', '../coefficients.npy.gz'),
        ('array_sha256', 'BAD'),
        ('npy_sha256', 'BAD'),
        ('lossless_roundtrip_verified', False),
      ]:
        with self.subTest(field=field):
          n, m, r = copy.deepcopy((norm, model, reference))
          m['arrays']['coefficients'][field] = value
          TestWriterReceipts.reseal(m)
          r['model_receipt_sha256'] = m['receipt_sha256']
          provider, _, _ = provider_fixture(n, m, r)
          with self.assertRaisesRegex(ValueError, 'Q1_MODEL_DESCRIPTOR_FORMAT_CONFLICT'):
            provider.prepare(0)
          self.assertFalse(provider.reader.phase.enabled)

  def test_partial_control_read_never_claims_complete_zero(self):
    ledger = repaired.Telemetry()
    ledger.control_attempts = 1
    value = ledger.snapshot()
    self.assertFalse(value['control_totals_complete'])
    self.assertEqual(value['failed_control_read_bytes'], 'NOT_RECORDED')
    self.assertEqual(value['failed_control_file_openings'], 'NOT_RECORDED')
    self.assertEqual(value['control_reads']['scope'], 'SUCCESSFULLY_COMPLETED_READS')

  def test_unobserved_identity_is_not_zero(self):
    ledger = repaired.Telemetry()
    value = ledger.snapshot()
    self.assertEqual(value['binding_receipt_sha256'], 'NOT_RECORDED')
    self.assertEqual(value['identity']['failed_reference_receipt_sha256'], 'NOT_RECORDED')

  def test_source_writer_and_previous_protocol_hashes_are_pinned(self):
    p = repaired.control.public(repaired.PROTOCOL)
    self.assertEqual(p['writer_source_sha256'], WRITER_SHA)
    self.assertEqual(p['prior_diagnostic_protocol_raw_sha256'], 'f7202811102013c842901d23dae7786debf10d36b0d6553fea3e471c892f20c0')
    self.assertEqual(p['V2_protocol_raw_sha256'], '7a4e02966d921759430a4b6c3c9ca1f343f400a293e4f79f1a9a73fb8aaeeb2f')
    self.assertFalse(p['stop']['retry'])
    self.assertFalse(p['stop']['DEV_rollout'])

  def test_real_writer_coeff_numeric_decode_only_after_durable_allowlist(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_inputs as inp

    with tempfile.TemporaryDirectory() as name:
      root = Path(name) / 'stage2'
      norm, model, reference = writer_fixture(root, True)
      provider, _, _ = provider_fixture(norm, model, reference)
      phase = provider.reader.phase
      plan = provider.prepare(0)
      prefix = 'candidates/HRI_D00_L01/FOLD_A/stage2/model/'
      accesses = []

      class Reader(inp.Reader):
        def raw(self, owner, member, kind, expected_raw, cap):
          phase.authorize(owner, member, kind)
          accesses.append(member)
          self.events.append({'kind': kind, 'file_openings': 1, 'bytes_read': cap})
          return (root / 'model' / model['arrays']['coefficients']['filename']).read_bytes()

      reader = Reader({**provider.reader.roots, **{k: '/synthetic/' + k for k in ('V1_TOP', 'CAUSAL', 'DERIVED')}}, '/synthetic', (0, 0), phase)
      reader.maps = provider.reader.maps
      desc = model['arrays']['coefficients']
      with self.assertRaises(ValueError):
        reader.array('V1', prefix + 'coefficients.npy.gz', desc, shape=(5,), dtype='<f8')
      self.assertEqual(accesses, [])
      phase.enable(plan, 'a' * 64, 'a' * 64)
      value = reader.array('V1', prefix + 'coefficients.npy.gz', desc, shape=(5,), dtype='<f8')
      np.testing.assert_array_equal(value, [1.0, 2.0, 3.0, 4.0, 5.0])
      self.assertEqual(accesses, [prefix + 'coefficients.npy.gz'])
      for field in ('nominal_coefficients', 'singular_values'):
        with self.assertRaises(ValueError):
          reader.array('V1', prefix + field + '.npy.gz', model['arrays'][field], shape=(5,), dtype='<f8')
      self.assertEqual(len(accesses), 1)


class TestOutputGrantBoundary(unittest.TestCase):
  def test_wrong_output_root_rejected_before_latch(self):
    import os
    from types import SimpleNamespace

    with tempfile.TemporaryDirectory() as name:
      home = Path(name)
      root = home / 'v4-e2-v2-q1-reader-repair-diagnostic-v2'
      root.mkdir(mode=0o700)
      ledger = repaired.Telemetry()
      ledger.identity['head'] = 'a' * 40
      gate = {
        'head': 'a' * 40,
        'mission': repaired.MISSION,
        'protocol_raw_sha256': repaired.control.sha(b'{}'),
        'output_root': str(home / 'other'),
        'diagnostic_runs': 1,
        'ci': {'head_sha': 'a' * 40, 'status': 'completed', 'conclusion': 'success'},
        **dict.fromkeys(
          ('DEV_authorized', 'D2_selection_authorized', 'E2_resume_authorized', 'HOLDOUT_authorized', 'vehicle_authorized', 'V5_authorized'), False
        ),
      }
      (root / 'execution-gate.json').write_bytes(repaired.control.canonical(repaired.control.sealed(gate)))
      os.chmod(root / 'execution-gate.json', 0o600)
      with patch('pwd.getpwuid', return_value=SimpleNamespace(pw_dir=str(home))):
        with self.assertRaisesRegex(ValueError, 'Q1_OUTPUT_SCOPE_CONFLICT'):
          repaired.authorize_output(root, b'{}', {}, ledger)
      self.assertFalse((root / 'attempt.json').exists())
      self.assertFalse((root / 'execution-envelope.json').exists())
      self.assertNotEqual(ledger.identity['current_grant_receipt_sha256'], 'NOT_RECORDED')

  def test_historical_or_source_directory_name_rejected_without_private_read(self):
    with patch.object(repaired.control, 'private') as source:
      with self.assertRaisesRegex(ValueError, 'Q1_OUTPUT_SCOPE_CONFLICT'):
        repaired.authorize_output(Path('/synthetic/old-diagnostic'), b'{}', {}, repaired.Telemetry())
    source.assert_not_called()


class TestSharedInputBudget(unittest.TestCase):
  def test_control_read_checks_source_bytes_and_opens(self):
    from types import SimpleNamespace

    for count, size in ((1600, 1), (1, 8 * 1024**3)):
      ledger = repaired.Telemetry()
      ledger.reader = SimpleNamespace(events=[{'file_openings': count, 'bytes_read': size}])
      with self.assertRaisesRegex(ValueError, 'Q1_DIAGNOSTIC_RESOURCE_BOUND'):
        repaired.input_budget(ledger, 1)

  def test_shared_bound_allows_exact_byte_cap(self):
    from types import SimpleNamespace

    ledger = repaired.Telemetry()
    ledger.reader = SimpleNamespace(events=[{'file_openings': 1598, 'bytes_read': 8 * 1024**3 - 17}])
    repaired.control.CONTROL_EVENTS.append({'name': 'synthetic.json', 'bytes': 7, 'raw_sha256': 'a' * 64})
    repaired.input_budget(ledger, 10)
    with self.assertRaisesRegex(ValueError, 'Q1_DIAGNOSTIC_RESOURCE_BOUND'):
      repaired.input_budget(ledger, 11)

  def test_partial_attempt_write_preserves_abort_ownership(self):
    import os

    calls = 0
    original = os.write

    def partial(fd, data):
      nonlocal calls
      calls += 1
      if calls == 1:
        return original(fd, data[:10])
      if calls == 2:
        raise OSError('synthetic write failure')
      return original(fd, data)

    with tempfile.TemporaryDirectory() as name:
      root = Path(name) / 'v4-e2-v2-q1-reader-repair-diagnostic-v2'
      root.mkdir(mode=0o700)
      with (
        patch.object(repaired, 'authorize_output'),
        patch.object(repaired, 'resource_plan'),
        patch.object(repaired.resource, 'setrlimit'),
        patch.object(repaired.signal, 'alarm'),
        patch.object(repaired.signal, 'signal'),
        patch.object(repaired.control, 'git', return_value='a' * 40),
        patch.object(repaired.os, 'write', side_effect=partial),
        patch.object(repaired, 'preflight') as preflight,
      ):
        repaired.run(root)
      preflight.assert_not_called()
      telemetry = repaired.control.checked((root / 'telemetry.json').read_bytes())
      first = telemetry['output_file_records_before_telemetry'][0]
      self.assertEqual(first, {'name': 'attempt.json', 'bytes': 10, 'complete': False})
      self.assertTrue((root / 'execution-envelope.json').is_file())
      self.assertEqual(telemetry['output_bytes_total'], sum((root / n).stat().st_size for n in ('attempt.json', 'execution-envelope.json', 'telemetry.json')))
