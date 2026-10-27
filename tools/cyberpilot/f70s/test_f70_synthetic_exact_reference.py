"""Real exact-reference behavior tests; public vectors are not policy values."""
import ast
import copy
import importlib
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CORPUS = json.loads((ROOT / 'F70S_PUBLIC_CASES.json').read_text())['cases']
GOLD = json.loads((ROOT / 'F70S_EXPECTED_PUBLIC_RESULTS.json').read_text())['expected']

def optional(name):
  try:
    return importlib.import_module(name)
  except ModuleNotFoundError as error:
    if error.name == name:
      return None
    raise

PRIMARY = optional('f70_synthetic_exact_reference')
AUDIT = optional('f70_synthetic_exact_audit')
RUNNER = optional('run_f70_synthetic_exact_reference')

def ratio(n, d=1):
  return {'numerator': str(n), 'denominator': str(d)}

def rational(value):
  from fractions import Fraction
  return Fraction(int(value['numerator']), int(value['denominator']))

class ExactReferenceTests(unittest.TestCase):
  def core(self):
    self.assertIsNotNone(PRIMARY, 'IMPLEMENTATION_MISSING_PRIMARY')
    self.assertIsNotNone(AUDIT, 'IMPLEMENTATION_MISSING_AUDIT')
    return PRIMARY, AUDIT

  def runner(self):
    self.assertIsNotNone(RUNNER, 'IMPLEMENTATION_MISSING_RUNNER')
    return RUNNER

  def request(self, **changes):
    data = copy.deepcopy(CORPUS[0])
    data.update(changes)
    return data

  def bad(self, request, code):
    for module in self.core():
      with self.assertRaises(ValueError) as found:
        module.evaluate(request)
      self.assertEqual(str(found.exception), code)

  def test_reject_malformed_ratio_strings(self):
    for n in ['-0', '+1', '01', 'NaN', 'Infinity', ' 1', '1e0']:
      self.bad(self.request(reference_command={'numerator': n, 'denominator': '1'}), 'F70S_RATIO')

    for d in ['0', '-1', '01', '+1', 'NaN']:
      self.bad(self.request(reference_command={'numerator': '1', 'denominator': d}), 'F70S_RATIO')

    class NonStringKey:
      def __hash__(self):
        return hash('numerator')
      def __eq__(self, other):
        raise RuntimeError('CALLBACK_MUST_NOT_RUN')
    self.bad(self.request(reference_command={NonStringKey(): '1', 'denominator': '1'}), 'F70S_RATIO')

  def test_exact_negative_ns_origin(self):
    for module in self.core():
      self.assertEqual(module.evaluate(CORPUS[8])['dt_s'], ratio(1, 100))
      self.assertEqual(module.evaluate(CORPUS[8])['r'], ratio(100, 3))

  def test_independent_audit_dependencies(self):
    self.core()
    tree = ast.parse((ROOT / 'f70_synthetic_exact_audit.py').read_text())
    names = []
    for node in ast.walk(tree):
      if isinstance(node, ast.Import):
        names.extend(x.name for x in node.names)
      elif isinstance(node, ast.ImportFrom):
        names.append(node.module or '')
    self.assertFalse(any('reference' in x or x == 'fractions' for x in names))

  def test_input_unchanged(self):
    for module in self.core():
      data = self.request()
      saved = copy.deepcopy(data)
      module.evaluate(data)
      self.assertEqual(data, saved)

  def test_canonical_repeat(self):
    for module in self.core():
      data = module.canonical_summary(CORPUS[2])
      self.assertEqual(data, module.canonical_summary(copy.deepcopy(CORPUS[2])))
      self.assertTrue(data.endswith(b'\n'))

  def test_R_contained_in_registered_A(self):
    for module in self.core():
      for data in CORPUS:
        result = module.evaluate(data)
        if result['rate_interval'] is not None:
          self.assertGreaterEqual(rational(result['rate_interval']['lower']), rational(data['admissible_interval']['lower']))
          self.assertLessEqual(rational(result['rate_interval']['upper']), rational(data['admissible_interval']['upper']))

  def test_budget_is_per_context(self):
    for module in self.core():
      self.assertEqual(module.evaluate(CORPUS[0])['r'], ratio(100))
      self.assertEqual(module.evaluate(CORPUS[1])['r'], ratio(50))

  def test_narrowing_A_does_not_increase_r(self):
    data = self.request(admissible_interval={'lower': ratio(-1, 2), 'upper': ratio(1, 2)})
    for module in self.core():
      self.assertEqual(module.evaluate(data)['r'], ratio(50))
      self.assertLessEqual(rational(module.evaluate(data)['r']), rational(module.evaluate(CORPUS[0])['r']))

  def test_zero_capacity_no_command(self):
    for module in self.core():
      result = module.evaluate(CORPUS[3])
      self.assertEqual(result['r'], ratio(0))
      self.assertEqual(result['status'], 'CONSTRAINT_CONFLICT')
      self.assertIsNone(result['candidate_output'])
      self.assertFalse(result['command_generated'])

  def test_no_evaluation_emits_no_capacity(self):
    for module in self.core():
      result = module.evaluate(CORPUS[12])
      for field in ['r', 'dt_s', 'L_up', 'L_down', 'rate_interval', 'intersection_bounds']:
        self.assertIsNone(result[field])
      self.assertEqual(result['reason_codes'], ['RESET_INTERVAL', 'LATERAL_INACTIVE', 'DRIVER_OVERRIDE'])

  def test_errors_do_not_echo_canary(self):
    canary = 'F70S_SYNTHETIC_CANARY_DO_NOT_ECHO'
    for module in self.core():
      with self.assertRaises(ValueError) as found:
        module.evaluate(self.request(reference_command=canary))
      self.assertEqual(str(found.exception), 'F70S_RATIO')
      self.assertNotIn(canary, str(found.exception))

  def test_non_dyadic_ns_exact(self):
    for module in self.core():
      result = module.evaluate(CORPUS[2])
      self.assertEqual(result['dt_s'], ratio(10000001, 1000000000))
      self.assertEqual(result['r'], ratio(1000000000, 30000003))

  def test_zero_discovery_rejected(self):
    with self.assertRaises(ValueError):
      self.runner().validate_discovery([], ['T'])

  def test_duplicate_discovery_rejected(self):
    with self.assertRaises(ValueError):
      self.runner().validate_discovery(['T', 'T'], ['T'])

  def test_missing_discovery_rejected(self):
    with self.assertRaises(ValueError):
      self.runner().validate_discovery(['A'], ['A', 'B'])

  def test_unexpected_discovery_rejected(self):
    with self.assertRaises(ValueError):
      self.runner().validate_discovery(['A', 'X'], ['A'])

  def test_skip_outcome_rejected(self):
    with self.assertRaises(ValueError):
      self.runner().validate_outcome(['T'], ['T'], ['T'], [], ['SKIP'])

  def test_fake_pass_rejected(self):
    with self.assertRaises(ValueError):
      self.runner().validate_outcome(['T'], [], [], ['T'], [])

  def test_error_outcome_rejected(self):
    with self.assertRaises(ValueError):
      self.runner().validate_outcome(['T'], ['T'], ['T'], [], ['ERROR'])

  def test_source_pin_mutation_rejected(self):
    runner = self.runner()
    pins = copy.deepcopy(runner.strict_json((ROOT / 'F70S_SOURCE_PINS.json').read_bytes()))
    pins['files'][0]['sha256'] = '0'*64
    with self.assertRaises(ValueError):
      runner.verify_pins(ROOT, pins)

  def test_malformed_pins_rejected(self):
    with self.assertRaises(ValueError):
      self.runner().verify_pins(ROOT, {'files': []})

  def test_case_hash_mutation_rejected(self):
    runner = self.runner()
    pins = copy.deepcopy(runner.strict_json((ROOT / 'F70S_SOURCE_PINS.json').read_bytes()))
    for entry in pins['files']:
      if entry['name'] == 'F70S_PUBLIC_CASES.json':
        entry['sha256'] = 'f'*64
    with self.assertRaises(ValueError):
      runner.verify_pins(ROOT, pins)

  def test_private_path_denied(self):
    with self.assertRaises(ValueError):
      self.runner().get_guard()
      Path('/F70S_FORBIDDEN_SYNTHETIC_PATH').read_bytes()

  def test_process_network_denied(self):
    self.runner().get_guard()
    import socket
    import subprocess
    with self.assertRaises(ValueError):
      subprocess.Popen(['/bin/true'])
    with self.assertRaises(ValueError), socket.socket():
      pass

  def test_controller_import_request_denied(self):
    with self.assertRaises(ValueError):
      self.runner().get_guard().assert_import_allowed('opendbc.car.controller')

  def test_output_directory_security(self):
    runner = self.runner()
    import os
    for flags in [os.O_RDONLY | os.O_TRUNC, os.O_RDONLY | os.O_CREAT, os.O_RDONLY | os.O_APPEND]:
      with self.assertRaises(ValueError):
        runner.get_guard().audit('open', (str(ROOT / 'f70_synthetic_exact_reference.py'), None, flags))
    with tempfile.TemporaryDirectory(dir=runner.get_guard().test_temp) as td:
      path = Path(td)
      runner.validate_private_directory(path)
      path.chmod(0o777)
      with self.assertRaises(ValueError):
        runner.validate_private_directory(path)
      path.chmod(0o700)

NEGATIVE = {
  'reject_float_command': ('previous_command', 0.5, 'F70S_RATIO'),
  'reject_boolean_time': ('current_time_ns', True, 'F70S_TIME_TYPE'),
  'reject_zero_denominator': ('reference_command', ratio(1, 0), 'F70S_RATIO'),
  'reject_unreduced_ratio': ('reference_command', ratio(2, 4), 'F70S_RATIO'),
  'reject_outside_domain': ('reference_command', ratio(2), 'F70S_DOMAIN'),
  'reject_inverted_interval': ('admissible_interval', {'lower': ratio(1), 'upper': ratio(-1)}, 'F70S_INTERVAL_ORDER'),
  'reject_anchor_outside_interval': ('previous_command', ratio(2, 1), 'F70S_DOMAIN'),
  'reject_duplicate_time': ('current_time_ns', 0, 'F70S_TIME_ORDER'),
  'reject_reversed_time': ('current_time_ns', -1, 'F70S_TIME_ORDER'),
  'reject_dt_overflow': ('DT_OVERFLOW', None, 'F70S_DT_RANGE'),
  'reject_time_bounds': ('current_time_ns', 1 << 63, 'F70S_TIME_RANGE'),
  'reject_sequence_gap': ('current_sequence', 2, 'F70S_SEQUENCE'),
  'reject_sequence_wrap': ('WRAP', None, 'F70S_SEQUENCE'),
  'reject_wrong_units': ('command_unit', 'degrees', 'F70S_UNITS'),
  'reject_wrong_source': ('source_kind', 'HISTORICAL_SOURCE', 'F70S_SOURCE'),
  'reject_extra_path_canary': ('private_path', 'F70S_SYNTHETIC_CANARY_DO_NOT_ECHO', 'F70S_FIELDS'),
  'reject_supplied_budget': ('rate_budget_per_s', ratio(1), 'F70S_FIELDS'),
  'reject_invalid_flags': ('BAD_FLAG', None, 'F70S_FLAGS'),
  'reject_missing_field': ('MISSING', None, 'F70S_FIELDS'),
  'reject_oversized_ratio': ('reference_command', {'numerator': '1', 'denominator': '9'*129}, 'F70S_RATIO'),
}

def negative_test(name, field, value, code):
  def test(self):
    data = self.request()
    if name == 'reject_wrong_units':
      for key, bad in [('command_unit', 'degrees'), ('rate_unit', 'raw_per_step'), ('time_unit', 's')]:
        self.bad(self.request(**{key: bad}), 'F70S_UNITS')
      return
    if name == 'reject_boolean_time':
      for bad in [True, False, 0.5, '1', None]:
        self.bad(self.request(current_time_ns=bad), 'F70S_TIME_TYPE')
      return
    if name == 'reject_anchor_outside_interval':
      data['previous_command'] = ratio(1)
      data['admissible_interval'] = {'lower': ratio(-1, 2), 'upper': ratio(1, 2)}
      self.bad(data, 'F70S_ANCHOR')
      data['current_time_ns'] = True
      self.bad(data, 'F70S_TIME_TYPE')
      data['current_time_ns'] = CORPUS[0]['current_time_ns']
      data['current_sequence'] = 2
      self.bad(data, 'F70S_SEQUENCE')
      return
    if field == 'DT_OVERFLOW':
      data.update(previous_time_ns=-(1 << 63), current_time_ns=(1 << 63)-1)
    elif field == 'WRAP':
      data.update(previous_sequence=(1 << 64)-1, current_sequence=0)
    elif field == 'BAD_FLAG':
      data['gates']['active'] = 1
    elif field == 'MISSING':
      del data['previous_command']
    else:
      data[field] = copy.deepcopy(value)
    self.bad(data, code)
  return test

def public_test(index):
  def test(self):
    raw = []
    for module in self.core():
      result = module.evaluate(CORPUS[index])
      for key, want in GOLD[index].items():
        if key != 'context_id':
          self.assertEqual(result[key], want)
      self.assertIsNone(result['candidate_output'])
      self.assertEqual(result['controller_invocations'], 0)
      self.assertEqual(result['runtime_authority'], 'NONE')
      self.assertFalse(result['source_schema_qualified_for_controller'])
      raw.append(module.canonical_summary(CORPUS[index]))
    self.assertEqual(raw[0], raw[1])
  return test

for name, (field, value, error_code) in NEGATIVE.items():
  setattr(ExactReferenceTests, 'test_'+name, negative_test(name, field, value, error_code))
for index in range(len(CORPUS)):
  setattr(ExactReferenceTests, 'test_public_case_'+str(index+1).zfill(2), public_test(index))
