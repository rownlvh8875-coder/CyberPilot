"""F70U boundary tests: reject false vehicle authority and malformed static records."""
import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, cast

from tools.cyberpilot.f70u.context_contract import (
  StaticContextContract, canonicalize_context_contract, hash_context_contract, load_context_contract, validate_context_contract,
)

ROOT = Path(__file__).resolve().parents[3]
CONTRACT_PATH = ROOT / 'artifacts/f70u/static_context_contract.json'


def record():
  return json.loads(CONTRACT_PATH.read_text())


def replace_field(data, path, value):
  parts = path.split('.')
  target = data
  for part in parts[:-1]:
    target = target[part]
  target[parts[-1]] = value


class StaticContextTests(unittest.TestCase):
  def test_valid_schema_does_not_resolve_vehicle(self):
    result = validate_context_contract(load_context_contract(CONTRACT_PATH))
    self.assertTrue(result.schema_valid, result.errors)
    self.assertEqual(result.instance_status, 'STATIC_CONTEXT_INSTANCE_UNRESOLVED')
    self.assertEqual(result.schema_status, 'CONTRACT_SCHEMA_VALID')
    self.assertEqual(result.errors, ())
    self.assertIn('platform_binding.selected_candidate', result.unresolved_fields)

  def test_null_vehicle_fields_are_not_defaulted(self):
    contract = load_context_contract(CONTRACT_PATH)
    before = copy.deepcopy(contract.data)
    validate_context_contract(contract)
    self.assertEqual(contract.data, before)
    self.assertIsNone(contract.data['safety_binding']['safety_param'])
    self.assertIsNone(contract.data['platform_binding']['selected_candidate'])

  def test_canonical_utf8_sorted_single_lf(self):
    value = StaticContextContract({'z': 1, 'a': '한'})
    self.assertEqual(canonicalize_context_contract(value), '{"a":"한","z":1}\n'.encode())

  def test_hash_is_sha256_of_exact_canonical_bytes(self):
    value = StaticContextContract({'z': 1, 'a': '한'})
    expected = hashlib.sha256('{"a":"한","z":1}\n'.encode()).hexdigest()
    self.assertEqual(hash_context_contract(value), expected)

  def test_independent_key_order_has_identical_canonical_bytes(self):
    first = record()
    second = dict(reversed(list(first.items())))
    self.assertEqual(canonicalize_context_contract(StaticContextContract(first)),
                     canonicalize_context_contract(StaticContextContract(second)))

  def test_contract_change_changes_hash(self):
    first, second = record(), record()
    second['owner_vehicle_description']['trim'] = 'unapproved variant'
    self.assertNotEqual(hash_context_contract(StaticContextContract(first)), hash_context_contract(StaticContextContract(second)))

  def test_schema_missing_required_group_is_rejected(self):
    value = record()
    del value['signal_binding']
    result = validate_context_contract(StaticContextContract(value))
    self.assertFalse(result.schema_valid)
    self.assertTrue(any('SCHEMA' in e for e in result.errors))

  def test_unknown_nested_field_is_rejected(self):
    value = record()
    value['safety_binding']['fallback_safety_param'] = 0
    self.assertFalse(validate_context_contract(StaticContextContract(value)).schema_valid)

  def test_conflicting_provenance_is_rejected(self):
    value = record()
    value['provenance']['fields'][0]['evidence_class'] = 'CONFLICTING'
    self.assertFalse(validate_context_contract(StaticContextContract(value)).schema_valid)

  def test_test_only_cannot_authorize_binding(self):
    value = record()
    value['provenance']['fields'][0]['evidence_class'] = 'TEST_ONLY'
    self.assertFalse(validate_context_contract(StaticContextContract(value)).schema_valid)

  def test_inferred_cannot_authorize_required_value(self):
    value = record()
    value['provenance']['fields'][0]['evidence_class'] = 'INFERRED'
    self.assertFalse(validate_context_contract(StaticContextContract(value)).schema_valid)

  def test_source_hash_mutation_is_detected(self):
    value = record()
    value['provenance']['sources'][0]['sha256'] = '0' * 64
    self.assertFalse(validate_context_contract(StaticContextContract(value)).schema_valid)

  def test_excerpt_hash_mutation_is_detected(self):
    value = record()
    value['provenance']['sources'][0]['excerpt_sha256'] = '0' * 64
    self.assertFalse(validate_context_contract(StaticContextContract(value)).schema_valid)

  def test_dynamic_value_cannot_be_laundered_by_static_annotation(self):
    value = record()
    field = next(f for f in value['provenance']['fields'] if f['path'] == 'limiter_binding.required_dynamic_inputs')
    field['static_or_dynamic'] = 'STATIC_CONTRACT'
    self.assertFalse(validate_context_contract(StaticContextContract(value)).schema_valid)

  def test_loading_valid_utf8_preserves_exact_data(self):
    loaded = load_context_contract(CONTRACT_PATH)
    self.assertEqual(loaded.data, record())

  def check_bad_json(self, raw):
    with tempfile.TemporaryDirectory() as directory:
      path = Path(directory) / 'context.json'
      path.write_bytes(raw)
      with self.assertRaises(ValueError):
        load_context_contract(path)

  def test_duplicate_json_keys_rejected(self):
    self.check_bad_json(b'{"a":1,"a":2}')

  def test_non_utf8_rejected(self):
    self.check_bad_json(b'{"a":"\xff"}')

  def test_float_json_rejected(self):
    self.check_bad_json(b'{"a":0.1}')

  def test_nan_json_rejected(self):
    self.check_bad_json(b'{"a":NaN}')

  def test_infinite_json_rejected(self):
    self.check_bad_json(b'{"a":Infinity}')

  def test_boolean_cannot_be_integer(self):
    value = record()
    value['platform_binding']['candidate_count'] = True
    self.assertFalse(validate_context_contract(StaticContextContract(value)).schema_valid)

  def test_non_string_key_not_canonicalizable(self):
    with self.assertRaises(ValueError):
      canonicalize_context_contract(StaticContextContract(cast(Any, {1: 'bad'})))

  def test_cli_generates_two_identical_unresolved_bundles(self):
    with tempfile.TemporaryDirectory() as directory:
      first, second = Path(directory) / 'first', Path(directory) / 'second'
      for target in [first, second]:
        done = subprocess.run([sys.executable, '-B', '-m', 'tools.cyberpilot.f70u.validate_context_contract',
                               '--output-dir', str(target)], cwd=ROOT, capture_output=True, check=False)
        self.assertEqual(done.returncode, 0, done.stderr.decode())
        self.assertTrue(json.loads(done.stdout)['schema_valid'])
      names = {'static_context_schema.json', 'static_context_input_template.json', 'F70U_PLATFORM_CANDIDATES.json',
               'context_validation_result.json', 'canonical_context_contract.json', 'context_contract.sha256', 'F70U_FINAL_RESULT.json'}
      self.assertEqual({p.name for p in first.iterdir()}, names)
      for name in names:
        self.assertEqual((first / name).read_bytes(), (second / name).read_bytes())
      final = json.loads((first / 'F70U_FINAL_RESULT.json').read_text())
      self.assertFalse(final['F71_authorized'])
      self.assertTrue(final['R_BUDGET_UNRESOLVED'])
      self.assertEqual(final['validation']['static_context_instance'], 'STATIC_CONTEXT_INSTANCE_UNRESOLVED')

  def test_cli_does_not_write_bundle_for_false_resolved_input(self):
    with tempfile.TemporaryDirectory() as directory:
      path, output = Path(directory) / 'invalid.json', Path(directory) / 'result'
      value = record()
      value['static_context_instance'] = 'STATIC_CONTEXT_INSTANCE_RESOLVED'
      path.write_text(json.dumps(value))
      done = subprocess.run([sys.executable, '-B', '-m', 'tools.cyberpilot.f70u.validate_context_contract',
                             '--contract', str(path), '--output-dir', str(output)], cwd=ROOT, capture_output=True, check=False)
      self.assertEqual(done.returncode, 1)
      self.assertFalse(json.loads(done.stdout)['schema_valid'])
      self.assertFalse(output.exists())

  def test_cli_parse_failure_reports_fixed_diagnostic(self):
    with tempfile.TemporaryDirectory() as directory:
      path = Path(directory) / 'invalid.json'
      path.write_text('{"private_marker":NaN}')
      done = subprocess.run([sys.executable, '-B', '-m', 'tools.cyberpilot.f70u.validate_context_contract',
                             '--contract', str(path)], cwd=ROOT, capture_output=True, check=False)
      self.assertEqual(done.returncode, 1)
      self.assertEqual(json.loads(done.stdout), {'errors': ['F70U_CONTRACT_INPUT_INVALID'], 'schema_valid': False})


# Each case catches a distinct false binding, type confusion or missing boundary.
MUTATIONS = {
  'baseline_sha_mutation': ('baseline_commit', '0' * 40, 'SCHEMA'),
  'repository_mismatch': ('repository', 'other/repository', 'SCHEMA'),
  'owner_description_missing': ('owner_vehicle_description', None, 'SCHEMA'),
  'unknown_top_field': ('unapproved_field', 'value', 'SCHEMA'),
  'null_required_evaluation_signal': ('signal_binding.evaluation_signal', None, 'SCHEMA'),
  'multiple_selected_platforms': ('platform_binding.selected_candidate', ['HYUNDAI_SANTA_FE', 'HYUNDAI_SANTA_FE_2022'], 'SELECTION'),
  'candidate_count_mismatch': ('platform_binding.candidate_count', 1, 'CANDIDATE_COUNT'),
  'classic_can_cannot_be_can_fd': ('can_architecture.is_can_fd', True, 'UNREGISTERED_BINDING'),
  'hda_generation_without_authority': ('can_architecture.hda_generation', 'HDA2', 'UNREGISTERED_BINDING'),
  'camera_scc_without_authority': ('can_architecture.camera_scc', True, 'UNREGISTERED_BINDING'),
  'safety_model_unknown_stays_null': ('safety_binding.safety_model', 'hyundai', 'UNREGISTERED_BINDING'),
  'safety_param_without_provenance': ('safety_binding.safety_param', 0, 'UNREGISTERED_BINDING'),
  'unapproved_mode': ('control_modes.longitudinal_control_mode', 'openpilot', 'UNREGISTERED_BINDING'),
  'stage_missing': ('signal_binding.pre_or_post_limiter', None, 'SCHEMA'),
  'normalization_reversed': ('signal_binding.normalization_min', 2, 'NORMALIZATION'),
  'normalization_outside_domain': ('signal_binding.normalization_max', 3, 'NORMALIZATION'),
  'control_period_negative': ('time_binding.control_period_ns', -1, 'PERIOD'),
  'control_period_zero': ('time_binding.control_period_ns', 0, 'PERIOD'),
  'limiter_commit_missing': ('limiter_binding.commit', None, 'SCHEMA'),
  'historical_data_dependency': ('dependency_policy.historical_source_payload_dependency', True, 'DEPENDENCY'),
  'candidate_output_dependency': ('dependency_policy.candidate_output_dependency', True, 'DEPENDENCY'),
  'controller_output_dependency': ('dependency_policy.controller_output_dependency', True, 'DEPENDENCY'),
  'runtime_output_dependency': ('dependency_policy.runtime_output_dependency', True, 'DEPENDENCY'),
  'vehicle_data_dependency': ('dependency_policy.real_vehicle_data_dependency', True, 'DEPENDENCY'),
  'false_resolved_claim': ('static_context_instance', 'STATIC_CONTEXT_INSTANCE_RESOLVED', 'RESOLUTION'),
  'unresolved_omission': ('unresolved_fields', [], 'UNRESOLVED_SET'),
  'conflict_must_fail': ('conflicts', [{'field': 'platform', 'reason': 'incompatible evidence'}], 'CONFLICT'),
}


def mutation_test(path, replacement, diagnostic):
  def test(self):
    value = record()
    replace_field(value, path, copy.deepcopy(replacement))
    result = validate_context_contract(StaticContextContract(value))
    self.assertFalse(result.schema_valid, 'false static authority accepted')
    self.assertTrue(any(diagnostic in error for error in result.errors), result.errors)
  return test


for case, args in MUTATIONS.items():
  setattr(StaticContextTests, 'test_reject_' + case, mutation_test(*args))


class CrossFieldTests(unittest.TestCase):
  def test_classic_can_and_can_fd_contradiction(self):
    value = record()
    value['can_architecture'].update(architecture='CLASSIC_CAN', is_can_fd=True)
    result = validate_context_contract(StaticContextContract(value))
    self.assertTrue(any('ARCHITECTURE' in error for error in result.errors), result.errors)

  def test_hda2_needs_applicable_architecture_authority(self):
    value = record()
    value['can_architecture'].update(architecture='CLASSIC_CAN', hda_generation='HDA2')
    result = validate_context_contract(StaticContextContract(value))
    self.assertTrue(any('HDA_AUTHORITY' in error for error in result.errors), result.errors)

  def test_scc_origin_cannot_be_both_camera_and_radar(self):
    value = record()
    value['can_architecture'].update(camera_scc=True, radar_scc=True)
    result = validate_context_contract(StaticContextContract(value))
    self.assertTrue(any('SCC_ORIGIN' in error for error in result.errors), result.errors)

  def test_pcm_cruise_conflicts_with_openpilot_longitudinal(self):
    value = record()
    value['control_modes'].update(pcm_cruise=True, openpilot_longitudinal_enabled=True)
    result = validate_context_contract(StaticContextContract(value))
    self.assertTrue(any('LONGITUDINAL_MODE' in error for error in result.errors), result.errors)


if __name__ == '__main__':
  unittest.main()
