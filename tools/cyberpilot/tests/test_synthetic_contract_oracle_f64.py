"""F64 public tests. No Controller module is imported or initialized."""
import importlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest

PREFIX = 'tools.cyberpilot.f64.'
ROOT = Path(__file__).resolve().parents[3]


def raw(value):
  return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


def fixture(times=(0, 1000000, 2000000), values=(0, 1, 2), denominator=1000):
  return {'schema_version': 'F64_SYNTHETIC_SOURCE_V1',
          'source_identity': 'F64_CONTROLLER_FREE_SYNTHETIC_OBSERVATIONS_V1',
          'origin': 'PUBLIC_SYNTHETIC_FIXTURE', 'unit': 'normalized_command',
          'times_ns': list(times), 'numerators': list(values), 'denominator': denominator}


class F64Test(unittest.TestCase):
  def api(self, name):
    try:
      found = importlib.util.find_spec(PREFIX + name)
    except ModuleNotFoundError:
      found = None
    self.assertIsNotNone(found, 'F64_API_NOT_IMPLEMENTED:' + name)
    return importlib.import_module(PREFIX + name)

  def reject(self, obj, code):
    s = self.api('source')
    with self.assertRaises(s.ContractError) as cm:
      s.decode_source(raw(obj))
    self.assertEqual(str(cm.exception), code)


class TestSourceTime(F64Test):
  def test_valid_source_preserves_order(self):
    s = self.api('source')
    x = fixture()
    self.assertEqual(s.decode_source(raw(x)), x)
    self.assertEqual(s.encode_source(x), raw(x))

  def test_all_integer_time_units_and_inverse(self):
    s = self.api('source')
    for unit, factor in [('ns', 1), ('us', 1000), ('ms', 1000000), ('s', 1000000000)]:
      with self.subTest(unit=unit):
        self.assertEqual(s.to_ns(2, unit), 2 * factor)
        self.assertEqual(s.from_ns(2 * factor, unit), 2)
        self.assertEqual(s.to_ns(0, unit), 0)

  def test_time_float_nan_inf_bool_str_rejected(self):
    s = self.api('source')
    for value in (1.0, 1.5, float('nan'), float('inf'), -float('inf'), True, '1', None):
      with self.subTest(value_type=type(value).__name__), self.assertRaisesRegex(s.ContractError, '^F64_TIME_TYPE$'):
        s.to_ns(value, 's')

  def test_time_overflow_and_negative(self):
    s = self.api('source')
    for value, unit, code in [(2**63, 'ns', 'F64_TIME_OVERFLOW'), (-2**63, 'ns', 'F64_TIME_NEGATIVE'),
                              (-2**63-1, 'ns', 'F64_TIME_NEGATIVE'), (2**63-1, 's', 'F64_TIME_OVERFLOW')]:
      with self.subTest(code=code), self.assertRaisesRegex(s.ContractError, '^' + code + '$'):
        s.to_ns(value, unit)

  def test_time_nonintegral_inverse_and_unknown_unit(self):
    s = self.api('source')
    with self.assertRaisesRegex(s.ContractError, '^F64_TIME_NONINTEGRAL$'):
      s.from_ns(1, 'us')
    with self.assertRaisesRegex(s.ContractError, '^F64_TIME_UNIT$'):
      s.to_ns(1, 'minutes')

  def test_duplicate_time(self):
    self.reject(fixture((0, 0, 2)), 'F64_TIME_DUPLICATE')

  def test_descending_time(self):
    self.reject(fixture((3, 2, 1)), 'F64_TIME_ORDER')

  def test_partial_reversal(self):
    self.reject(fixture((0, 2, 1)), 'F64_TIME_ORDER')

  def test_gap_below_equal_above_boundary(self):
    s = self.api('source')
    for gap in (9999999, 10000000):
      self.assertEqual(s.decode_source(raw(fixture((0, gap), (0, 1))))['times_ns'][1], gap)
    self.reject(fixture((0, 10000001), (0, 1)), 'F64_TIME_GAP')

  def test_near_int64_maximum_preserved(self):
    x = fixture((2**63-3, 2**63-2, 2**63-1))
    self.assertEqual(self.api('source').decode_source(raw(x)), x)

  def test_minimum_one_ns_and_zero_gap(self):
    self.assertEqual(self.api('source').decode_source(raw(fixture((0, 1), (0, 1))))['times_ns'], [0, 1])
    self.reject(fixture((0, 0), (0, 1)), 'F64_TIME_DUPLICATE')

  def test_missing_and_unknown_fields(self):
    x = fixture()
    del x['unit']
    self.reject(x, 'F64_SCHEMA_KEYS')
    x = fixture()
    x['controller'] = 'forbidden'
    self.reject(x, 'F64_SCHEMA_KEYS')

  def test_wrong_schema_source_origin_and_unit(self):
    for key, value, code in [('schema_version', 'OTHER', 'F64_SCHEMA_VERSION'),
                             ('source_identity', 'F61_PUBLIC_SYNTHETIC_RATE_INPUT_V1', 'F64_SOURCE_IDENTITY'),
                             ('origin', 'RLOG', 'F64_SOURCE_IDENTITY'), ('unit', 'deg', 'F64_UNIT')]:
      x = fixture()
      x[key] = value
      self.reject(x, code)

  def test_empty_arrays(self):
    self.reject(fixture((), ()), 'F64_EMPTY_INPUT')

  def test_length_and_wrong_shape(self):
    self.reject(fixture((0, 1), (0,)), 'F64_LENGTH')
    x = fixture()
    x['times_ns'] = [[0], [1], [2]]
    self.reject(x, 'F64_TIME_TYPE')
    x = fixture()
    x['numerators'] = 'abc'
    self.reject(x, 'F64_VALUE_TYPE')

  def test_value_dtype_bool_float_and_range(self):
    for value in (True, '1', 1.0, None):
      self.reject(fixture(values=(0, value, 2)), 'F64_VALUE_TYPE')
    self.reject(fixture(values=(0, 1001, 0)), 'F64_VALUE_RANGE')
    self.reject(fixture(denominator=0), 'F64_VALUE_RANGE')

  def test_domain_boundary_below_equal_above(self):
    s = self.api('source')
    for v in (999, 1000, -1000):
      s.decode_source(raw(fixture((0,), (v,))))
    self.reject(fixture((0,), (1001,)), 'F64_VALUE_RANGE')

  def test_nan_inf_input_bytes_rejected(self):
    s = self.api('source')
    for word in (b'NaN', b'Infinity', b'-Infinity'):
      with self.assertRaisesRegex(s.ContractError, '^F64_JSON$'):
        s.decode_source(b'{"bad":' + word + b'}\n')

  def test_json_duplicate_noncanonical_invalid(self):
    s = self.api('source')
    for data, code in [(b'{"x":1,"x":2}\n', 'F64_JSON_DUPLICATE'),
                        (json.dumps(fixture()).encode(), 'F64_NONCANONICAL'), (b'not json', 'F64_JSON')]:
      with self.assertRaisesRegex(s.ContractError, '^' + code + '$'):
        s.decode_source(data)

  def test_maximum_length_and_one_over(self):
    s = self.api('source')
    x = fixture(tuple(i*10000000 for i in range(8000)), (0,)*8000)
    self.assertEqual(len(s.decode_source(raw(x))['times_ns']), 8000)
    x['times_ns'].append(80000000000)
    x['numerators'].append(0)
    self.reject(x, 'F64_LENGTH')

  def test_generator_determinism_and_seed_variation(self):
    s = self.api('source')
    for family in s.FAMILIES:
      a = s.generate({'family': family, 'seed': 0, 'count': 17, 'start_ns': 0})
      self.assertEqual(a, s.generate({'family': family, 'seed': 0, 'count': 17, 'start_ns': 0}))
      self.assertNotEqual(a, s.generate({'family': family, 'seed': 1, 'count': 17, 'start_ns': 0}))
      s.decode_source(a)

  def test_generator_minimum_and_maximum(self):
    s = self.api('source')
    for count in (1, 8000):
      x = s.decode_source(s.generate({'family': 'constant', 'seed': 0, 'count': count, 'start_ns': 0}))
      self.assertEqual(len(x['times_ns']), count)
      self.assertEqual(x['numerators'], [0]*count)

  def test_generator_bad_spec_and_timestamp_overflow(self):
    s = self.api('source')
    for spec in [{'family': 'UNKNOWN', 'seed': 0, 'count': 17, 'start_ns': 0},
                 {'family': 'constant', 'seed': True, 'count': 17, 'start_ns': 0},
                 {'family': 'constant', 'seed': 0, 'count': 0, 'start_ns': 0}]:
      with self.assertRaisesRegex(s.ContractError, '^F64_SPEC$'):
        s.generate(spec)
    with self.assertRaisesRegex(s.ContractError, '^F64_TIME_OVERFLOW$'):
      s.generate({'family': 'constant', 'seed': 0, 'count': 2, 'start_ns': 2**63-1})

  def test_irregular_valid_has_two_explicit_intervals(self):
    s = self.api('source')
    x = s.decode_source(s.generate({'family': 'irregular_valid', 'seed': 0, 'count': 17, 'start_ns': 0}))
    self.assertEqual({b-a for a, b in zip(x['times_ns'], x['times_ns'][1:], strict=False)}, {5000000, 10000000})


class TestMetrics(F64Test):
  def test_constant_zero_and_one_sample(self):
    m = self.api('metrics')
    a = m.compute(raw(fixture(values=(0, 0, 0))))
    self.assertEqual(a['rate_mean_square'], {'numerator': '0', 'denominator': '1'})
    b = m.compute(raw(fixture((0,), (0,))))
    self.assertEqual(b['pair_count'], 0)
    self.assertIsNone(b['rate_mean_square'])
    self.assertEqual(b['status'], 'INSUFFICIENT_PAIRS')

  def test_linear_closed_form(self):
    a = self.api('metrics').compute(raw(fixture()))
    one = {'numerator': '1', 'denominator': '1'}
    for key in ('rate_mean_square', 'abs_rate_p95', 'abs_rate_p99', 'max_abs_rate'):
      self.assertEqual(a[key], one)
    self.assertEqual(a['pair_count'], 2)
    self.assertEqual(a['rate_rms_exact'], {'sqrt_of': one})

  def test_step_exact_square_and_quantiles(self):
    a = self.api('metrics').compute(raw(fixture((0, 10000000, 20000000), (0, 0, 1), 1)))
    self.assertEqual(a['rate_mean_square'], {'numerator': '5000', 'denominator': '1'})
    self.assertEqual(a['abs_rate_p95'], {'numerator': '95', 'denominator': '1'})
    self.assertEqual(a['abs_rate_p99'], {'numerator': '99', 'denominator': '1'})

  def test_rate_rms_exact_threshold_below_equal_above(self):
    m = self.api('metrics')
    a = m.compute(raw(fixture()))
    self.assertEqual(m.classify_rms(a, 999, 1000), 'ABOVE')
    self.assertEqual(m.classify_rms(a, 1, 1), 'EQUAL')
    self.assertEqual(m.classify_rms(a, 1001, 1000), 'BELOW')

  def test_rate_threshold_negative_and_no_support(self):
    m = self.api('metrics')
    with self.assertRaisesRegex(self.api('source').ContractError, '^F64_VALUE_RANGE$'):
      m.classify_rms(m.compute(raw(fixture())), -1, 1)
    self.assertEqual(m.classify_rms(m.compute(raw(fixture((0,), (0,)))), 1, 1), 'UNAVAILABLE')

  def test_no_initial_prepend(self):
    a = self.api('metrics').compute(raw(fixture((0, 10000000), (1, 1), 1)))
    self.assertEqual(a['rate_mean_square'], {'numerator': '0', 'denominator': '1'})
    self.assertEqual(a['pair_count'], 1)

  def test_irregular_equal_pair_weight(self):
    a = self.api('metrics').compute(raw(fixture((0, 1000000, 3000000), (0, 1, 2), 1000)))
    self.assertEqual(a['rate_mean_square'], {'numerator': '5', 'denominator': '8'})

  def test_independent_oracle_all_families(self):
    s, m, o = self.api('source'), self.api('metrics'), self.api('oracle')
    for family in s.FAMILIES:
      for seed in (0, 1):
        data = s.generate({'family': family, 'seed': seed, 'count': 17, 'start_ns': 0})
        self.assertEqual(m.compute(data), o.compute(data), family)

  def test_independent_oracle_no_production_helper_import(self):
    module = self.api('oracle')
    import ast
    tree = ast.parse(Path(module.__file__).read_text())
    imports = [n.module or '' for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
    imports += [a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names]
    self.assertEqual(set(imports), {'json', 'math'})

  def test_f60_uniform_numeric_compatibility(self):
    s, m = self.api('source'), self.api('metrics')
    for family in s.FAMILIES:
      data = s.generate({'family': family, 'seed': 1, 'count': 17, 'start_ns': 0})
      check = m.check_f60(data)
      if family == 'irregular_valid':
        self.assertEqual(check, {'status': 'NOT_APPLICABLE_IRREGULAR_GRID'})
      else:
        self.assertEqual(check['status'], 'EXACT_MSE_AND_SUPPORT_MATCH')

  def test_original_data_not_mutated(self):
    m = self.api('metrics')
    data = raw(fixture())
    before = data[:]
    m.compute(data)
    self.assertEqual(data, before)


class TestIsolationAndProtocol(F64Test):
  def test_static_graph_clean(self):
    g = self.api('isolation')
    result = g.inspect_project(ROOT)
    self.assertEqual(result['controller_dependencies'], [])
    self.assertGreater(result['project_modules_checked'], 3)

  def test_static_forbidden_imports_and_dynamic_calls(self):
    g = self.api('isolation')
    for text in ('import openpilot.selfdrive.controls.controlsd',
                 'from opendbc.car import structs', '__import__("controller")', 'exec("bad")'):
      self.assertFalse(g.inspect_text(text)['allowed'])

  def test_runtime_forbidden_import_is_blocked_before_load(self):
    g = self.api('isolation')
    with g.Guard() as guard:
      with self.assertRaisesRegex(g.IsolationError, '^F64_ISOLATION_IMPORT$'):
        importlib.import_module('openpilot.selfdrive.controls.controlsd')
    self.assertEqual(guard.counts['forbidden_import_attempts'], 1)
    self.assertNotIn('openpilot.selfdrive.controls.controlsd', sys.modules)
    self.assertEqual(guard.counts['controller_calls'], 0)

  def test_runtime_process_network_native_private_probes_blocked(self):
    g = self.api('isolation')
    with g.Guard() as guard:
      for event, args, code in [('subprocess.Popen', ('x', [], None, None), 'F64_ISOLATION_PROCESS'),
                                ('socket.__new__', (), 'F64_ISOLATION_NETWORK'),
                                ('ctypes.dlopen', ('x',), 'F64_ISOLATION_NATIVE'),
                                ('open', ('/private_e2/CANARY.rlog', 'r', 0), 'F64_ISOLATION_PRIVATE')]:
        with self.assertRaisesRegex(g.IsolationError, '^'+code+'$'):
          sys.audit(event, *args)
    self.assertEqual(guard.counts['controller_calls'], 0)

  def test_preregistered_contract_unresolved_budget_and_no_runtime(self):
    p = json.loads((ROOT/'artifacts/f64/preregistered_contract.json').read_text())
    self.assertEqual(p['r_budget']['status'], 'R_BUDGET_UNRESOLVED')
    self.assertIsNone(p['r_budget']['value'])
    self.assertEqual(p['preserved']['SOURCE_SCHEMA_UNQUALIFIED'], 6000)
    self.assertIsNone(p['preserved']['selected_candidate'])

  def test_holdout_derivation_known_independent_hash(self):
    import hashlib
    r = self.api('runner')
    sha = '0123456789abcdef0123456789abcdef01234567'
    expected = hashlib.sha256(('F64_HOLDOUT_V1:'+sha).encode('ascii')).digest()
    self.assertEqual(r.derive_seeds(sha), [int.from_bytes(expected[:8], 'big'), int.from_bytes(expected[8:16], 'big')])

  def test_invalid_fixture_error_codes_and_public_case_count(self):
    r = self.api('runner')
    cases = r.case_records([0, 1])
    self.assertEqual(len(cases), 22)
    self.assertEqual(sum(x['expected_error'] is None for x in cases), 14)
    self.assertEqual(sum(x['expected_error'] is not None for x in cases), 8)

  def test_public_outputs_are_canonical_and_repeatable(self):
    r = self.api('runner')
    a = r.evaluate_cases([0, 1], 'PUBLIC')
    b = r.evaluate_cases([0, 1], 'PUBLIC')
    self.assertEqual(a, b)
    self.assertEqual(a['summary']['candidate_output'], None)
    self.assertEqual(a['summary']['controller_calls'], 0)
    self.assertTrue(a['summary']['all_contract_checks_pass'])

  def test_oracle_mismatch_blocks(self):
    r = self.api('runner')
    with self.assertRaisesRegex(self.api('source').ContractError, '^F64_ORACLE_MISMATCH$'):
      r.require_equal({'a': 1}, {'a': 2})

  def test_source_dependency_pin(self):
    self.assertTrue(self.api('runner').verify_f60_pin(ROOT))

class TestReviewHardening(F64Test):
  def test_large_legal_irregular_rationals(self):
    import math
    gaps, value = [], 10007
    while len(gaps) < 700:
      if all(value % d for d in range(2, math.isqrt(value)+1)):
        gaps.append(value)
      value += 1
    times = [0]
    for gap in gaps:
      times.append(times[-1]+gap)
    data = raw(fixture(times, [i % 2 for i in range(701)], 1))
    self.api('source').decode_source(data)
    actual = self.api('metrics').compute(data)
    expected = self.api('oracle').compute(data)
    self.assertEqual(actual, expected)
    self.assertGreater(len(actual['rate_mean_square']['denominator']), 4300)
    self.assertEqual(self.api('metrics').classify_rms(actual, 0, 1), 'ABOVE')

  def test_extreme_json_numbers_fixed_error(self):
    s = self.api('source')
    for data in (b'{"x":1e999}\n', b'{"x":'+b'1'*5000+b'}\n', b'['*(sys.getrecursionlimit()+100)+b'0'+b']'*(sys.getrecursionlimit()+99)):
      with self.assertRaisesRegex(s.ContractError, '^F64_JSON$'):
        s.decode_source(data)

  def test_from_import_controller_alias_blocked(self):
    self.assertFalse(self.api('isolation').inspect_text('from openpilot import selfdrive')['allowed'])

  def test_static_graph_has_transitive_and_unsafe_checks(self):
    result = self.api('isolation').inspect_project(ROOT)
    self.assertTrue(result['transitive_local_graph'])
    self.assertEqual(result['unapproved_imports'], [])
    self.assertEqual(result['unsafe_dynamic_calls'], [])

  def test_actual_harmless_network_loader_and_file_probes(self):
    import _ctypes
    import socket
    g = self.api('isolation')
    for action, code in [(lambda: socket.socket(), 'F64_ISOLATION_NETWORK'),
                         (lambda: _ctypes.dlopen('F64_NONEXISTENT_CANARY_LIBRARY'), 'F64_ISOLATION_NATIVE'),
                         (lambda: open('/private_e2/F64_CANARY.rlog'), 'F64_ISOLATION_PRIVATE')]:
      with g.Guard(), self.assertRaisesRegex(g.IsolationError, '^'+code+'$'):
        action()

  def test_runner_requires_guard_before_import_path(self):
    self.assertTrue(self.api('runner').GUARDED_IMPORT_VERIFIED)

  def test_invalid_holdout_commit_does_not_derive(self):
    with self.assertRaisesRegex(self.api('source').ContractError, '^F64_SOURCE_PIN$'):
      self.api('entry').verify_holdout_source(ROOT, '0'*40)

  def test_cli_alias_cannot_derive_before_proof(self):
    from unittest.mock import patch
    runner = self.api('runner')
    with patch.object(runner, 'derive_seeds', side_effect=AssertionError('DERIVATION_MUST_NOT_RUN')):
      with self.assertRaisesRegex(self.api('source').ContractError, '^F64_SOURCE_PIN$'):
        runner.main(['--pre-holdout='+'0'*40, '--output', '/F64_SYNTHETIC_CANARY'])

  def test_forged_holdout_proof_is_rejected(self):
    with self.assertRaisesRegex(self.api('source').ContractError, '^F64_SOURCE_PIN$'):
      self.api('runner').evaluate_cases([0, 1], 'HOLDOUT', {'pre_holdout_commit': '0'*40})

  def test_source_manifest_tamper_is_rejected_by_comparison(self):
    entry = self.api('entry')
    self.assertFalse(entry.hashes_equal(b'a', '0'*64))
    self.assertTrue(entry.hashes_equal(b'a', 'ca978112ca1bbdcafac231b39a23dc4da786eff8147c4e72b9807785afee48bb'))


if __name__ == '__main__':
  unittest.main()
