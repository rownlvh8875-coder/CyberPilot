"""Metadata-only contract tests; no vehicle payload or controller execution."""
import copy
import importlib.util
import json
import socket
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent


class SourceBoundaryTests(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    path = ROOT / 'source_boundary.py'
    if not path.exists():
      cls.api = None
      return
    spec = importlib.util.spec_from_file_location('boundary', path)
    cls.api = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cls.api)
    cls.contract_bytes = (ROOT / 'artifacts/source_boundary_contract.json').read_bytes()
    cls.static = json.loads((ROOT / 'artifacts/static_metadata_envelope.json').read_bytes())
    cls.synthetic = json.loads((ROOT / 'artifacts/synthetic_descriptor_envelope.json').read_bytes())

  def setUp(self):
    self.assertIsNotNone(self.api, 'Missing source-boundary implementation')

  def contract(self):
    return self.api.validate_contract(self.api.load_json(self.contract_bytes))

  def reject(self, record, code=None):
    with self.assertRaises(self.api.BoundaryError) as caught:
      self.api.validate_record(record, self.contract())
    if code is not None:
      self.assertEqual(caught.exception.code, code)

  def test_static_metadata_is_admitted_without_instance_promotion(self):
    value = self.api.validate_record(self.static, self.contract())
    self.assertEqual(value['admission'], 'STATIC_METADATA_ONLY')
    self.assertFalse(value['context_instance_resolved'])
    self.assertFalse(value['r_budget_resolved'])
    self.assertFalse(value['F70V_allowed'])
    self.assertFalse(value['F71_allowed'])
    self.assertFalse(value['calculator_input_created'])

  def test_reference_descriptor_is_not_numeric_sample_admission(self):
    value = self.api.validate_record(self.synthetic, self.contract())
    self.assertEqual(value['admission'], 'REFERENCE_DESCRIPTOR_ONLY')
    self.assertFalse(value['numeric_sample_admitted'])
    self.assertFalse(value['production_sample_admitted'])

  def test_production_sample_class_rejected(self):
    value = copy.deepcopy(self.static)
    value['source_class'] = 'PRODUCTION_SAMPLE'
    self.reject(value, 'SOURCE_CLASS_NOT_ADMITTED')

  def test_log_sample_class_rejected(self):
    value = copy.deepcopy(self.static)
    value['source_class'] = 'RLOG_NUMERIC_SAMPLE'
    self.reject(value, 'SOURCE_CLASS_NOT_ADMITTED')

  def test_candidate_output_class_rejected(self):
    value = copy.deepcopy(self.static)
    value['source_class'] = 'CANDIDATE_OUTPUT'
    self.reject(value, 'SOURCE_CLASS_NOT_ADMITTED')

  def test_legacy_synthetic_vector_class_is_not_rerouted_here(self):
    value = copy.deepcopy(self.synthetic)
    value['source_class'] = 'PREREGISTERED_SYNTHETIC_INTERVAL'
    self.reject(value, 'SOURCE_CLASS_NOT_ADMITTED')

  def test_relabel_static_metadata_as_synthetic_descriptor_rejected(self):
    value = copy.deepcopy(self.static)
    value['source_class'] = 'REGISTERED_SYNTHETIC_REFERENCE_DESCRIPTOR'
    self.reject(value, 'RECORD_CLASS_MISMATCH')

  def test_relabel_and_forge_registered_id_still_rejected(self):
    value = copy.deepcopy(self.static)
    value['source_class'] = self.synthetic['source_class']
    value['record_id'] = self.synthetic['record_id']
    value['payload']['record_id'] = self.synthetic['record_id']
    self.reject(value, 'PAYLOAD_HASH_MISMATCH')

  def test_injected_numeric_command_rejected(self):
    value = copy.deepcopy(self.static)
    value['payload']['native_command'] = {'numerator': '1', 'denominator': '2'}
    self.reject(value, 'PAYLOAD_HASH_MISMATCH')

  def test_injected_data_path_rejected(self):
    value = copy.deepcopy(self.static)
    value['payload']['data_path'] = '/forbidden/rlog.zst'
    self.reject(value, 'PAYLOAD_HASH_MISMATCH')

  def test_unregistered_record_rejected(self):
    value = copy.deepcopy(self.static)
    value['record_id'] = 'NEW_UNAPPROVED_RECORD'
    self.reject(value, 'UNREGISTERED_RECORD')

  def test_baseline_tampering_rejected(self):
    value = copy.deepcopy(self.static)
    value['payload']['baseline_commit'] = '0' * 40
    self.reject(value, 'PAYLOAD_HASH_MISMATCH')

  def test_producer_tampering_rejected(self):
    value = copy.deepcopy(self.static)
    value['payload']['producer_commit'] = '0' * 40
    self.reject(value, 'PAYLOAD_HASH_MISMATCH')

  def test_post_limiter_stage_substitution_rejected(self):
    value = copy.deepcopy(self.static)
    value['payload']['production_stage'] = 'AFTER_LIMITER'
    self.reject(value, 'PAYLOAD_HASH_MISMATCH')

  def test_unknown_fields_cannot_be_erased_to_claim_resolution(self):
    value = copy.deepcopy(self.static)
    value['payload']['unresolved_fields'] = []
    value['payload']['instance_resolved'] = True
    self.reject(value, 'PAYLOAD_HASH_MISMATCH')

  def test_boolean_is_not_equivalent_to_integer_in_registry_hash(self):
    value = copy.deepcopy(self.static)
    value['payload']['resolved_field_count'] = True
    self.reject(value, 'PAYLOAD_HASH_MISMATCH')

  def test_unknown_envelope_field_rejected(self):
    value = copy.deepcopy(self.static)
    value['extra'] = 'not allowed'
    self.reject(value, 'ENVELOPE_FIELDS')

  def test_missing_envelope_field_rejected(self):
    value = copy.deepcopy(self.static)
    del value['payload']
    self.reject(value, 'ENVELOPE_FIELDS')

  def test_wrong_root_type_rejected(self):
    self.reject([], 'JSON_ROOT_TYPE')

  def test_null_payload_rejected(self):
    value = copy.deepcopy(self.static)
    value['payload'] = None
    self.reject(value, 'PAYLOAD_TYPE')

  def test_duplicate_root_key_rejected(self):
    with self.assertRaises(self.api.BoundaryError) as caught:
      self.api.load_json(b'{"a":1,"a":2}')
    self.assertEqual(caught.exception.code, 'DUPLICATE_JSON_KEY')

  def test_duplicate_nested_key_rejected(self):
    with self.assertRaises(self.api.BoundaryError):
      self.api.load_json(b'{"a":{"b":1,"b":2}}')

  def test_invalid_utf8_rejected(self):
    with self.assertRaises(self.api.BoundaryError):
      self.api.load_json(b'{"a":"\xff"}')

  def test_float_and_nonfinite_json_rejected(self):
    for token in [b'0.5', b'NaN', b'Infinity', b'-Infinity']:
      with self.subTest(token=token), self.assertRaises(self.api.BoundaryError):
        self.api.load_json(b'{"a":' + token + b'}')

  def test_non_string_object_key_rejected(self):
    with self.assertRaises(self.api.BoundaryError):
      self.api.canonicalize_record({'a': {1: 'bad'}})

  def test_oversized_document_rejected_before_parsing(self):
    with self.assertRaises(self.api.BoundaryError) as caught:
      self.api.load_json(b'x' * 300000)
    self.assertEqual(caught.exception.code, 'DOCUMENT_TOO_LARGE')

  def test_deeply_nested_document_rejected(self):
    raw = b'{"a":' + b'[' * 80 + b'0' + b']' * 80 + b'}'
    with self.assertRaises(self.api.BoundaryError) as caught:
      self.api.load_json(raw)
    self.assertEqual(caught.exception.code, 'DEPTH_LIMIT')

  def test_contract_registry_mutation_rejected(self):
    contract = self.contract()
    row = contract['registered_records'][self.static['record_id']]
    row['source_class'] = 'PRODUCTION_SAMPLE'
    with self.assertRaises(self.api.BoundaryError) as caught:
      self.api.validate_record(self.static, contract)
    self.assertEqual(caught.exception.code, 'CONTRACT_HASH_MISMATCH')

  def test_contract_cannot_whitelist_a_tampered_payload(self):
    value = copy.deepcopy(self.static)
    value['payload']['instance_resolved'] = True
    contract = self.contract()
    contract['registered_records'][value['record_id']]['canonical_payload_sha256'] = self.api.hash_record(value['payload'])
    with self.assertRaises(self.api.BoundaryError) as caught:
      self.api.validate_record(value, contract)
    self.assertEqual(caught.exception.code, 'CONTRACT_HASH_MISMATCH')

  def test_input_objects_are_not_modified(self):
    value = copy.deepcopy(self.static)
    contract = self.contract()
    before = copy.deepcopy((value, contract))
    self.api.validate_record(value, contract)
    self.assertEqual((value, contract), before)

  def test_canonical_bytes_and_hash_ignore_key_order(self):
    one = {'z': 1, 'a': {'b': False}}
    two = {'a': {'b': False}, 'z': 1}
    self.assertEqual(self.api.canonicalize_record(one), b'{"a":{"b":false},"z":1}\n')
    self.assertEqual(self.api.canonicalize_record(one), self.api.canonicalize_record(two))
    self.assertEqual(self.api.hash_record(one), self.api.hash_record(two))

  def test_core_validation_has_no_file_or_network_io(self):
    contract = self.contract()
    with patch('builtins.open', side_effect=AssertionError('Forbidden file IO')), patch.object(socket, 'socket', side_effect=AssertionError('Forbidden network IO')):
      value = self.api.validate_record(self.static, contract)
    self.assertEqual(value['admission'], 'STATIC_METADATA_ONLY')

  def test_error_diagnostics_do_not_echo_untrusted_values(self):
    value = copy.deepcopy(self.static)
    value['source_class'] = 'SECRET_SHOULD_NOT_APPEAR'
    with self.assertRaises(self.api.BoundaryError) as caught:
      self.api.validate_record(value, self.contract())
    self.assertNotIn('SECRET_SHOULD_NOT_APPEAR', str(caught.exception))

  def test_document_input_must_be_bytes(self):
    with self.assertRaises(self.api.BoundaryError) as caught:
      self.api.load_json('{}')
    self.assertEqual(caught.exception.code, 'DOCUMENT_TYPE')

  def test_empty_document_rejected(self):
    with self.assertRaises(self.api.BoundaryError):
      self.api.load_json(b'')

  def test_unpaired_unicode_surrogate_rejected(self):
    with self.assertRaises(self.api.BoundaryError) as caught:
      self.api.canonicalize_record({'x': '\ud800'})
    self.assertEqual(caught.exception.code, 'INVALID_UNICODE')

  def test_node_resource_limit_enforced(self):
    with self.assertRaises(self.api.BoundaryError) as caught:
      self.api.load_json(json.dumps({'items': [0] * 12000}).encode())
    self.assertEqual(caught.exception.code, 'NODE_LIMIT')

  def test_schema_version_boolean_rejected(self):
    value = copy.deepcopy(self.static)
    value['schema_version'] = True
    self.reject(value, 'ENVELOPE_VERSION')

  def test_unhashable_record_id_is_a_fixed_diagnostic(self):
    value = copy.deepcopy(self.static)
    value['record_id'] = []
    self.reject(value, 'ENVELOPE_VALUE_TYPE')

  def test_synthetic_descriptor_cannot_declare_embedded_samples(self):
    value = copy.deepcopy(self.synthetic)
    value['payload']['sample_values_included'] = True
    value['payload']['sample'] = [0, 1]
    self.reject(value, 'PAYLOAD_HASH_MISMATCH')

  def test_reformatted_contract_retains_same_identity(self):
    value = json.loads(self.contract_bytes)
    text = json.dumps(value, sort_keys=False, indent=3, ensure_ascii=True).encode()
    self.assertEqual(self.api.validate_contract(self.api.load_json(text)), self.contract())


if __name__ == '__main__':
  unittest.main(verbosity=2)
