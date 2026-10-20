"""Public CI infrastructure: exact coverage, complete stages, no scientific changes."""
import copy
import hashlib
import os
import tempfile
import sys
import types
from pathlib import Path
import unittest

from tools.cyberpilot import full_ci_test_manifest as m
from tools.cyberpilot import verify_full_ci_coverage as v

HEAD = 'a' * 40
IDS = ['example.TestFixture.test_a', 'example.TestFixture.test_b']


def log_for(ids=IDS, status='.'):
  return 'collected 2 tests in 0.10s • 2 workers\n' + ''.join(f'{status} {i} 0.01s\n' for i in ids) + '\n2 passed in 1.00s\n'


def bundle():
  manifest = m.make_manifest(HEAD, IDS, IDS)
  result = m.parse_log(manifest, log_for(), 0)
  return m.seal({'schema': v.SCHEMA, 'head': HEAD, 'run_id': '123', 'manifest': manifest, 'regression': result,
                 'native': {'verified': True, 'source_sha256': m.NATIVE_SOURCE_SHA, 'wrapper_sha256': m.NATIVE_WRAPPER_SHA,
                            'receipt_sha256': 'b' * 64, 'binary_sha256': 'c' * 64, 'compiler_version': '13.3.0',
                            'flags': list(m.NATIVE_FLAGS), 'ABI': m.NATIVE_ABI, 'private_execution_authorized': False,
                            'runtime_integration_authorized': False},
                 'source_integrity': {'frozen_source_pins': 231, 'pointer_count': 252, 'conflicts': []},
                 'stages': {k: {'outcome': 'success', 'conclusion': 'success'} for k in v.REQUIRED_STAGES}})


class TestExactCoverage(unittest.TestCase):
  def test_manifest_is_order_independent_and_retains_baseline(self):
    a = m.make_manifest(HEAD, list(reversed(IDS)), IDS)
    self.assertEqual(a, m.make_manifest(HEAD, IDS, IDS))
    self.assertEqual(a['test_ids'], IDS)
    self.assertEqual(a['count'], 2)
    self.assertEqual(a['sorted_ids_sha256'], hashlib.sha256(('\n'.join(IDS) + '\n').encode()).hexdigest())

  def test_duplicate_collected_id_rejected(self):
    with self.assertRaises(m.CIIntegrityError):
      m.make_manifest(HEAD, IDS + IDS[:1], IDS)

  def test_missing_baseline_id_rejected(self):
    with self.assertRaises(m.CIIntegrityError):
      m.make_manifest(HEAD, IDS[:1], IDS)

  def test_fresh_lfs_index_mapping_rejects_duplicate_or_malformed_members(self):
    oid = 'a' * 64
    self.assertEqual(m.pointer_members(oid + ' * public/asset.png\n'), {'public/asset.png': oid})
    for text in (oid + ' * public/asset.png\n' + oid + ' - public/asset.png\n', 'invalid pointer listing'):
      with self.subTest(text=text), self.assertRaises(m.CIIntegrityError):
        m.pointer_members(text)

  def test_invalid_head_rejected(self):
    with self.assertRaises(m.CIIntegrityError):
      m.make_manifest('main', IDS, IDS)

  def test_exact_original_verbose_output_accepted(self):
    result = m.parse_log(m.make_manifest(HEAD, IDS, IDS), log_for(), 0)
    self.assertEqual([x['id'] for x in result['records']], IDS)
    self.assertEqual(result['counts'], {'passed': 2})

  def test_missing_duplicate_unknown_partial_skip_and_failed_output_rejected(self):
    manifest = m.make_manifest(HEAD, IDS, IDS)
    cases = [log_for(IDS[:1]), log_for(IDS + IDS[:1]), log_for([*IDS, 'other.Test.test_x']),
             log_for().replace('2 passed in 1.00s', ''), log_for(status='s'), log_for(status='x'),
             log_for(status='X'), log_for(status='F'), log_for(status='E'),
             log_for().replace('collected 2', 'collected 3'), log_for() + '\nCOLLECTION ERROR\n']
    for text in cases:
      with self.subTest(text=text), self.assertRaises(m.CIIntegrityError):
        m.parse_log(manifest, text, 0)

  def test_interrupted_word_in_public_test_name_is_not_a_partial_run(self):
    ids = ['example.Test.test_a', 'example.Test.test_interrupted_resume_is_rejected']
    result = m.parse_log(m.make_manifest(HEAD, ids, ids), log_for(ids), 0)
    self.assertEqual(result['counts'], {'passed': 2})

  def test_atomic_evidence_read_rejects_wrong_hash_symlink_and_hardlink(self):
    with tempfile.TemporaryDirectory() as temp:
      path = Path(temp) / 'public.json'
      digest = m.write_json(path, {'public': True})
      self.assertEqual(m.read_json(path, expected_digest=digest), {'public': True})
      with self.assertRaises(m.CIIntegrityError):
        m.read_json(path, expected_digest='0' * 64)
      link = Path(temp) / 'link.json'
      link.symlink_to(path)
      with self.assertRaises((m.CIIntegrityError, OSError)):
        m.read_json(link, expected_digest=digest)
      link.unlink()
      os.link(path, link)
      with self.assertRaises(m.CIIntegrityError):
        m.read_json(path, expected_digest=digest)

  def test_public_baseline_ids_really_are_subset_of_complete_collection(self):
    manifest = m.collect_manifest()
    baseline = (m.ROOT / m.BASELINE_IDS_FILE).read_text().splitlines()
    self.assertEqual(len(baseline), 5927)
    self.assertEqual(m.ids_hash(baseline), m.BASELINE_IDS_SHA)
    self.assertTrue(set(baseline) <= set(manifest['test_ids']))

  def test_actual_original_module_class_setup_and_teardown_run_once(self):
    from tools import test_runner
    name = 'cyberpilot_public_ci_fixture_witness'
    module = types.ModuleType(name)
    code = ''.join([
      'import unittest\n',
      'events=[]\n',
      "def setUpModule(): events.append('module_setup')\n",
      "def tearDownModule(): events.append('module_teardown')\n",
      'class Case(unittest.TestCase):\n',
      ' @classmethod\n',
      " def setUpClass(cls): events.append('class_setup')\n",
      ' @classmethod\n',
      " def tearDownClass(cls): events.append('class_teardown')\n",
      " def test_a(self): events.append('a')\n",
      " def test_b(self): events.append('b')\n",
    ])
    exec(code, module.__dict__)
    sys.modules[name] = module
    try:
      cases = list(unittest.defaultTestLoader.loadTestsFromTestCase(module.Case))
      groups = test_runner.make_batches(cases, 2)
      self.assertEqual(len(groups), 1)
      records = test_runner.run_batch(groups[0], False)
      self.assertEqual([r['status'] for r in records], ['passed', 'passed'])
      self.assertEqual(module.events, ['module_setup', 'class_setup', 'a', 'b', 'class_teardown', 'module_teardown'])
    finally:
      del sys.modules[name]

  def test_nonzero_exit_never_accepted(self):
    with self.assertRaises(m.CIIntegrityError):
      m.parse_log(m.make_manifest(HEAD, IDS, IDS), log_for(), 1)

  def test_manifest_digest_tampering_rejected(self):
    manifest = m.make_manifest(HEAD, IDS, IDS)
    manifest['test_ids'][0] = 'wrong.Test.test_x'
    with self.assertRaises(m.CIIntegrityError):
      m.parse_log(manifest, log_for(), 0)

  def test_original_module_and_class_fixtures_stay_atomic(self):
    from tools import test_runner
    class Fixture(unittest.TestCase):
      @classmethod
      def setUpClass(cls):
        pass
      def test_a(self):
        pass
      def test_b(self):
        pass
    cases = list(unittest.defaultTestLoader.loadTestsFromTestCase(Fixture))
    groups = test_runner.make_batches(cases, 2)
    self.assertEqual(groups, [[t.id() for t in cases]])

  def test_original_fixture_failure_is_unknown_record_and_rejected(self):
    bad = log_for().replace('. example.TestFixture.test_a 0.01s', 'E setUpClass (example.TestFixture) 0.00s')
    with self.assertRaises(m.CIIntegrityError):
      m.parse_log(m.make_manifest(HEAD, IDS, IDS), bad, 1)


class TestCompleteGate(unittest.TestCase):
  def test_complete_same_head_success(self):
    self.assertEqual(v.verify_bundle(bundle(), HEAD, '123', {'validate': {'result': 'success'}})['status'],
                     'CI_BUNDLE_INTERNAL_CONSISTENCY_VERIFIED')

  def test_missing_or_skipped_required_stage_rejected(self):
    for stage in v.REQUIRED_STAGES:
      for action in ('missing', 'skipped', 'cancelled', 'failure'):
        b = bundle()
        if action == 'missing':
          del b['stages'][stage]
        else:
          b['stages'][stage] = {'outcome': action, 'conclusion': action}
        with self.subTest(stage=stage, action=action), self.assertRaises(m.CIIntegrityError):
          v.verify_bundle(m.seal(b), HEAD, '123', {'validate': {'result': 'success'}})

  def test_exact_artifact_id_and_sha_required_before_any_download(self):
    good = {'validate': {'result': 'success', 'outputs': {'artifact_id': '12345', 'evidence_sha256': 'b' * 64}}}
    self.assertEqual(v.artifact_binding(good), {'artifact_id': '12345', 'evidence_sha256': 'b' * 64})
    for value in ('', 'all', '../123', '12,34', '0'):
      bad = copy.deepcopy(good)
      bad['validate']['outputs']['artifact_id'] = value
      with self.subTest(value=value), self.assertRaises(m.CIIntegrityError):
        v.artifact_binding(bad)
    bad = copy.deepcopy(good)
    bad['validate']['outputs']['evidence_sha256'] = ''
    with self.assertRaises(m.CIIntegrityError):
      v.artifact_binding(bad)

  def test_job_timeout_cancelled_missing_or_extra_job_rejected(self):
    for needs in ({}, {'validate': {'result': 'cancelled'}}, {'validate': {'result': 'failure'}},
                  {'validate': {'result': 'skipped'}}, {'validate': {'result': 'success'}, 'extra': {'result': 'success'}}):
      with self.subTest(needs=needs), self.assertRaises(m.CIIntegrityError):
        v.verify_bundle(bundle(), HEAD, '123', needs)

  def test_wrong_head_and_run_rejected(self):
    for head, run in [('d' * 40, '123'), (HEAD, '456')]:
      with self.subTest(head=head, run=run), self.assertRaises(m.CIIntegrityError):
        v.verify_bundle(bundle(), head, run, {'validate': {'result': 'success'}})

  def test_tampered_artifact_and_partial_native_witness_rejected(self):
    for field in ('native', 'regression', 'manifest', 'source_integrity'):
      b = bundle()
      del b[field]
      with self.subTest(field=field), self.assertRaises(m.CIIntegrityError):
        v.verify_bundle(m.seal(b), HEAD, '123', {'validate': {'result': 'success'}})
    b = bundle()
    b['native']['binary_sha256'] = 'wrong'
    with self.assertRaises(m.CIIntegrityError):
      v.verify_bundle(b, HEAD, '123', {'validate': {'result': 'success'}})

  def test_native_compiler_flags_source_and_authority_cannot_change(self):
    for key, value in [('compiler_version', '14.0.0'), ('flags', []), ('source_sha256', '0' * 64),
                       ('wrapper_sha256', '0' * 64), ('ABI', 'other'), ('verified', False),
                       ('runtime_integration_authorized', True), ('private_execution_authorized', True)]:
      b = bundle()
      b['native'][key] = value
      with self.subTest(key=key), self.assertRaises(m.CIIntegrityError):
        v.verify_bundle(m.seal(b), HEAD, '123', {'validate': {'result': 'success'}})

  def test_missing_duplicate_and_nonpassing_resealed_result_rejected(self):
    for action in ('missing', 'duplicate', 'skipped'):
      b = bundle()
      rows = b['regression']['records']
      if action == 'missing':
        rows.pop()
      elif action == 'duplicate':
        rows.append(copy.deepcopy(rows[0]))
      else:
        rows[0]['status'] = 'skipped'
      b['regression'] = m.seal(b['regression'])
      with self.subTest(action=action), self.assertRaises(m.CIIntegrityError):
        v.verify_bundle(m.seal(b), HEAD, '123', {'validate': {'result': 'success'}})

  def test_native_receipt_required_and_wrong_sha_rejected(self):
    with self.assertRaises((m.CIIntegrityError, ValueError, OSError)):
      m.verify_native('', '')
    path = os.environ.get('CYBERPILOT_PUBLIC_NATIVE_RECEIPT', '')
    with self.assertRaises((m.CIIntegrityError, ValueError, OSError)):
      m.verify_native(path, '0' * 64)

  def test_real_explicit_public_native_receipt(self):
    witness = m.verify_native(os.environ['CYBERPILOT_PUBLIC_NATIVE_RECEIPT'],
                              os.environ['CYBERPILOT_PUBLIC_NATIVE_RECEIPT_SHA256'])
    self.assertTrue(witness['verified'])
    self.assertEqual(witness['source_sha256'], m.NATIVE_SOURCE_SHA)

  def test_gate_checkout_contains_historical_baseline_for_source_diff(self):
    root = Path(__file__).resolve().parents[4]
    text = (root / '.github/workflows/cyberpilot-full-validation-v2.yaml').read_text()
    gate = text.split('  complete:', 1)[1]
    self.assertIn('fetch-depth: 0', gate)
    self.assertIn('lfs: false', gate)
    self.assertIn('submodules: false', gate)

  def test_workflow_keeps_all_stages_and_legacy_pin(self):
    root = Path(__file__).resolve().parents[4]
    legacy = (root / '.github/workflows/cyberpilot.yaml').read_bytes()
    self.assertEqual(hashlib.sha256(legacy).hexdigest(), m.LEGACY_SHA)
    text = (root / '.github/workflows/cyberpilot-full-validation-v2.yaml').read_text()
    self.assertIn('timeout-minutes: 45', text)
    self.assertIn('--workers 2', text)
    self.assertIn('pytest==9.1.1 PyYAML==6.0.3', text)
    self.assertIn("assert yaml.__version__ == '6.0.3'", text)
    self.assertIn('if: always()', text)
    self.assertNotIn('continue-on-error', text)
    self.assertNotIn(' -k ', text)
    self.assertIn('run_canonical_runtime_feasibility.py', text)
    for stage in v.REQUIRED_STAGES:
      self.assertIn('id: ' + stage, text)
