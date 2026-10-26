"""Public F65 tests; Source/metric contracts only, no Controller."""
import importlib
import importlib.util
import json
from pathlib import Path
import unittest

NAME = 'tools.cyberpilot.synthetic_source_separation_f65'
ROOT = Path(__file__).resolve().parents[3]


class TestF65(unittest.TestCase):
  def api(self):
    self.assertIsNotNone(importlib.util.find_spec(NAME), 'F65_API_NOT_IMPLEMENTED')
    return importlib.import_module(NAME)

  def spec(self, family='constant', seed=0, split='PUBLIC', count=17):
    return {'family': family, 'seed': seed, 'split': split, 'count': count}

  def test_uint64_seed_recoverable_from_actual_values_and_time(self):
    m = self.api()
    for seed in [0, 1, 2, 3, 4, 31, 32, 2**32, 2**63, 2**64-1]:
      for family in m.FAMILIES:
        for split in ('PUBLIC', 'EVALUATION'):
          data = m.generate(self.spec(family, seed, split))
          self.assertEqual(m.recover_seed(data), seed)

  def test_deterministic_and_cross_split_disjoint(self):
    m = self.api()
    for family in m.FAMILIES:
      a = m.generate(self.spec(family, 0))
      self.assertEqual(a, m.generate(self.spec(family, 0)))
      b = m.generate(self.spec(family, 0, 'EVALUATION'))
      self.assertNotEqual(m.signal_hash(a), m.signal_hash(b))

  def test_old_modulo_collision_seeds_are_distinct(self):
    m = self.api()
    for family in m.FAMILIES:
      self.assertNotEqual(m.signal_hash(m.generate(self.spec(family, 0))),
                          m.signal_hash(m.generate(self.spec(family, 32))))

  def test_first_observation_is_actual_separated_value(self):
    m = self.api()
    for family in m.FAMILIES:
      for split, sign in [('PUBLIC', 1), ('EVALUATION', -1)]:
        x = json.loads(m.generate(self.spec(family, 2**64-1, split)))
        self.assertEqual(x['numerators'][0], sign*x['denominator'])
        self.assertEqual(x['times_ns'][1], 9999997)

  def test_first_sample_partition_holds_at_minimum_count(self):
    m = self.api()
    for family in m.FAMILIES:
      for split, sign in [('PUBLIC', 1), ('EVALUATION', -1)]:
        x = json.loads(m.generate(self.spec(family, 0, split, 2)))
        self.assertEqual(x['numerators'][0], sign*(1 << 62))

  def test_equivalent_rational_encoding_hashes_equal(self):
    m = self.api()
    from tools.cyberpilot.f64.source import canonical, IDENTITY, SCHEMA, ORIGIN, UNIT
    base = {'source_identity': IDENTITY, 'schema_version': SCHEMA, 'origin': ORIGIN, 'unit': UNIT,
            'times_ns': [0, 10000000], 'denominator': 4, 'numerators': [1, 2]}
    x = canonical(base)
    base.update(denominator=8, numerators=[2, 4])
    self.assertEqual(m.signal_hash(x), m.signal_hash(canonical(base)))

  def test_changed_actual_time_changes_hash(self):
    m = self.api()
    x = json.loads(m.generate(self.spec()))
    a = m.signal_hash(m.canonical(x))
    x['times_ns'] = [i*9999999 for i in range(17)]
    self.assertNotEqual(a, m.signal_hash(m.canonical(x)))

  def test_bounds_minimum_maximum_and_types(self):
    m = self.api()
    for n in (2, 8000):
      self.assertEqual(len(json.loads(m.generate(self.spec(count=n)))['times_ns']), n)
    for spec in [self.spec(seed=True), self.spec(seed=-1), self.spec(seed=2**64), self.spec(count=1),
                 self.spec(count=8001), self.spec(split='HOLDOUT_PRIVATE'), self.spec(family='UNKNOWN')]:
      with self.assertRaisesRegex(m.GateError, '^F65_SPEC$'):
        m.generate(spec)

  def test_all_families_exact_metric_oracle(self):
    m = self.api()
    from tools.cyberpilot.f64 import metrics, oracle
    for family in m.FAMILIES:
      for split in ('PUBLIC', 'EVALUATION'):
        data = m.generate(self.spec(family, 31, split))
        self.assertEqual(metrics.compute(data), oracle.compute(data))

  def test_nan_and_fractional_time_still_rejected(self):
    m = self.api()
    from tools.cyberpilot.f64.source import ContractError
    x = json.loads(m.generate(self.spec()))
    x['times_ns'][1] = 1.0
    with self.assertRaisesRegex(ContractError, '^F64_TIME_TYPE$'):
      m.signal_hash(m.canonical(x))

  def test_f64_failed_status_cannot_pass_new_gate(self):
    m = self.api()
    failed = json.loads((ROOT/'artifacts/f64/F64_FINAL_SEAL.json').read_text())
    with self.assertRaisesRegex(m.GateError, '^F65_GATE_STATUS$'):
      m.final_gate(failed)

  def result(self):
    return {'status': 'F65_SOURCE_SEPARATION_PARTIAL_PASS_R_BUDGET_UNRESOLVED',
            'verified_cases': 14, 'source_overlap': 0, 'metric_mismatches': 0,
            'controller_calls': 0, 'candidate_output': None, 'r_budget': 'R_BUDGET_UNRESOLVED',
            'runtime': 'NO_GO', 'SOURCE_SCHEMA_UNQUALIFIED': 6000,
            'NO_ADMISSIBLE_NEXT_CANDIDATE': True, 'selected_candidate': None,
            'selected_policy': None, 'Vehicle_authority': 'NONE'}

  def test_partial_gate_accepts_only_bounded_contract_scope(self):
    self.assertTrue(self.api().final_gate(self.result()))

  def test_failure_pending_missing_unknown_status_rejected(self):
    m = self.api()
    for state in ('FAIL', 'BLOCKED', 'PENDING', 'UNKNOWN', 'F64_HOLDOUT_FAIL', 'F65_HOLDOUT_FAIL', 'SUCCESS', None):
      x = self.result()
      x['status'] = state
      with self.assertRaisesRegex(m.GateError, '^F65_GATE_STATUS$'):
        m.final_gate(x)

  def test_gate_flags_fail_closed(self):
    m = self.api()
    for field, value in [('verified_cases', 0), ('verified_cases', True), ('source_overlap', 1),
                         ('metric_mismatches', 1), ('controller_calls', 1), ('candidate_output', 0),
                         ('runtime', 'ACTIVE'), ('r_budget', 1), ('SOURCE_SCHEMA_UNQUALIFIED', 0),
                         ('NO_ADMISSIBLE_NEXT_CANDIDATE', False), ('selected_candidate', 'T2'),
                         ('selected_policy', 1), ('Vehicle_authority', 'ACTIVE')]:
      x = self.result()
      x[field] = value
      with self.assertRaises(m.GateError):
        m.final_gate(x)

  def test_missing_gate_field_rejected(self):
    m = self.api()
    for key in self.result():
      x = self.result()
      del x[key]
      with self.assertRaises(m.GateError):
        m.final_gate(x)

  def test_bundle_tampering_rejected(self):
    m = self.api()
    data = m.generate(self.spec())
    record = {'sha256': '0'*64, 'signal_sha256': m.signal_hash(data), 'spec': self.spec()}
    with self.assertRaisesRegex(m.GateError, '^F65_BUNDLE_MISMATCH$'):
      m.verify_record(record, data)

  def test_fake_split_claim_rejected(self):
    m = self.api()
    import hashlib
    data = m.generate(self.spec())
    record = {'sha256': hashlib.sha256(data).hexdigest(), 'signal_sha256': m.signal_hash(data),
              'spec': self.spec(split='EVALUATION')}
    with self.assertRaisesRegex(m.GateError, '^F65_BUNDLE_MISMATCH$'):
      m.verify_record(record, data)

  def test_no_controller_dependency_imports(self):
    import ast
    m = self.api()
    tree = ast.parse(Path(m.__file__).read_text())
    names = [n.module or '' for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
    self.assertFalse(any(x.startswith(('openpilot.selfdrive', 'opendbc', 'panda', 'cereal')) for x in names))

  def app(self):
    name = 'tools.cyberpilot.run_f65_source_separation_v1'
    self.assertIsNotNone(importlib.util.find_spec(name), 'F65_RUNNER_NOT_IMPLEMENTED')
    return importlib.import_module(name)

  def test_public_evaluation_deterministic(self):
    a = self.app().evaluate('PUBLIC', [0, 1])
    b = self.app().evaluate('PUBLIC', [0, 1])
    self.assertEqual(a, b)
    self.assertEqual(a['summary']['verified_cases'], 14)
    self.assertEqual(a['summary']['controller_calls'], 0)

  def test_fake_evaluation_proof_blocks_before_generation(self):
    with self.assertRaisesRegex(self.api().GateError, '^F65_SOURCE_PIN$'):
      self.app().evaluate('EVALUATION', [0, 1], {'pre_commit': '0'*40})

  def test_seed_policy_known_test_vector(self):
    import hashlib
    value = '0123456789abcdef0123456789abcdef01234567'
    d = hashlib.sha256(('F65_HOLDOUT_V1:'+value).encode('ascii')).digest()
    self.assertEqual(self.app().derive_seeds(value), [int.from_bytes(d[:8], 'big'), int.from_bytes(d[8:16], 'big')])

  def test_development_evaluation_shaped_cases_are_exposed(self):
    app = self.app()
    m = self.api()
    known = m.signal_hash(m.generate(self.spec('constant', 31, 'EVALUATION')))
    self.assertIn(known, {r['signal_sha256'] for r in app.exposed_development()})

  def test_failed_bundle_status_rejected_before_source_proof(self):
    import tempfile
    app = self.app()
    with tempfile.TemporaryDirectory() as directory:
      Path(directory, 'final_result.json').write_text('{"status":"F64_HOLDOUT_FAIL"}')
      with self.assertRaisesRegex(self.api().GateError, '^F65_GATE_STATUS$'):
        app.verify_bundle(Path(directory))

  def test_source_manifest_cannot_omit_protected_modules(self):
    app = self.app()
    required = {'tools/cyberpilot/synthetic_source_separation_f65.py', 'tools/cyberpilot/run_f65_source_separation_v1.py'}
    for entries in ([], [{'path': next(iter(required)), 'bytes': 0, 'sha256': '0'*64}]):
      with self.assertRaisesRegex(self.api().GateError, '^F65_SOURCE_PIN$'):
        app.validate_manifest_inventory({'files': entries}, required)

  def test_manifest_duplicate_and_unsafe_path_rejected(self):
    app = self.app()
    item = {'path': 'core.py', 'bytes': 0, 'sha256': '0'*64}
    for entries in ([item, item], [{'path': '../core.py', 'bytes': 0, 'sha256': '0'*64}]):
      with self.assertRaises(self.api().GateError):
        app.validate_manifest_inventory({'files': entries}, {'core.py'})

  def test_bundle_inventory_exact_set_not_just_count(self):
    app = self.app()
    good = [{'path': 'a.json', 'bytes': 1, 'sha256': '0'*64}, {'path': 'b.json', 'bytes': 1, 'sha256': '1'*64}]
    self.assertEqual(set(app.validate_bundle_inventory(good, {'a.json', 'b.json'})), {'a.json', 'b.json'})
    for value in ([good[0], good[0]], [good[0], {'path': 'extra.json', 'bytes': 1, 'sha256': '1'*64}]):
      with self.assertRaises(self.api().GateError):
        app.validate_bundle_inventory(value, {'a.json', 'b.json'})

  def test_bundle_reader_rejects_symlink_ancestor(self):
    import tempfile
    app = self.app()
    with tempfile.TemporaryDirectory() as directory:
      base = Path(directory)
      real = base/'real'
      (real/'nested').mkdir(parents=True)
      (real/'nested/final_result.json').write_text('{}')
      (base/'link').symlink_to(real, target_is_directory=True)
      with self.assertRaises(self.api().GateError):
        app.safe_read(base/'link/nested', 'final_result.json')

  def test_preserved_no_go_contract(self):
    x = json.loads((ROOT/'artifacts/f65/preregistered_contract.json').read_text())
    self.assertEqual(x['r_budget'], 'R_BUDGET_UNRESOLVED')
    self.assertTrue(x['preserved']['NO_ADMISSIBLE_NEXT_CANDIDATE'])
    self.assertEqual(x['preserved']['SOURCE_SCHEMA_UNQUALIFIED'], 6000)


if __name__ == '__main__':
  unittest.main()
