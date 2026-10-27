"""Registered metadata admission only; no calculator, file or network path."""
import hashlib
import json
from typing import Any, cast

EXPECTED_CONTRACT_SHA256 = '6ecb9466a43d3fa748d6f814fe7d992277f4e35623b8e9af22a27eec83981af0'
# Parser resource bounds; these are not vehicle/r-budget acceptance thresholds.
MAX_DOCUMENT_BYTES = 256 * 1024
MAX_TREE_DEPTH = 64
MAX_TREE_NODES = 10000
ENVELOPE_FIELDS = frozenset({'schema_version', 'contract_id', 'source_class', 'record_id', 'payload'})
SOURCE_CLASSES = frozenset({'REGISTERED_STATIC_CONTEXT_METADATA', 'REGISTERED_SYNTHETIC_REFERENCE_DESCRIPTOR'})


class BoundaryError(ValueError):
  """Fixed diagnostic only; never echo caller-supplied content."""

  def __init__(self, code: str):
    self.code = code
    super().__init__(code)


def _need(condition: bool, code: str) -> None:
  if not condition:
    raise BoundaryError(code)


def _json_tree(value: object) -> None:
  _need(type(value) is dict, 'JSON_ROOT_TYPE')
  stack = [(value, 0)]
  nodes = 0
  while stack:
    item, depth = stack.pop()
    nodes += 1
    _need(nodes <= MAX_TREE_NODES, 'NODE_LIMIT')
    _need(depth <= MAX_TREE_DEPTH, 'DEPTH_LIMIT')
    if type(item) is dict:
      mapping = cast(dict[object, object], item)
      _need(all(type(k) is str for k in mapping), 'JSON_KEY_TYPE')
      stack.extend((v, depth + 1) for v in mapping.values())
    elif type(item) is list:
      stack.extend((v, depth + 1) for v in cast(list[object], item))
    elif type(item) is float:
      raise BoundaryError('NON_INTEGER_NUMBER')
    else:
      _need(item is None or type(item) in (str, int, bool), 'JSON_VALUE_TYPE')


def _pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
  result: dict[str, Any] = {}
  for key, value in items:
    _need(key not in result, 'DUPLICATE_JSON_KEY')
    result[key] = value
  return result


def _no_float(_value: str) -> None:
  raise BoundaryError('NON_INTEGER_NUMBER')


def _no_nonfinite(_value: str) -> None:
  raise BoundaryError('NON_FINITE_NUMBER')


def load_json(raw: bytes) -> dict[str, Any]:
  _need(type(raw) is bytes, 'DOCUMENT_TYPE')
  _need(len(raw) <= MAX_DOCUMENT_BYTES, 'DOCUMENT_TOO_LARGE')
  try:
    value = json.loads(raw.decode('utf-8'), object_pairs_hook=_pairs,
                       parse_float=_no_float, parse_constant=_no_nonfinite)
  except BoundaryError:
    raise
  except (ValueError, UnicodeError, RecursionError):
    raise BoundaryError('INVALID_JSON') from None
  _json_tree(value)
  return cast(dict[str, Any], value)


def canonicalize_record(value: object) -> bytes:
  _json_tree(value)
  try:
    raw = (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode('utf-8')
  except UnicodeError:
    raise BoundaryError('INVALID_UNICODE') from None
  except (ValueError, TypeError, RecursionError, RuntimeError):
    raise BoundaryError('INVALID_JSON') from None
  _need(len(raw) <= MAX_DOCUMENT_BYTES, 'DOCUMENT_TOO_LARGE')
  return raw


def hash_record(value: object) -> str:
  return hashlib.sha256(canonicalize_record(value)).hexdigest()


def validate_contract(value: object) -> dict[str, Any]:
  raw = canonicalize_record(value)
  _need(hashlib.sha256(raw).hexdigest() == EXPECTED_CONTRACT_SHA256, 'CONTRACT_HASH_MISMATCH')
  # Return an independent JSON snapshot; validation never caches mutable trust.
  return load_json(raw)


def validate_record(value: object, contract: object) -> dict[str, Any]:
  registered = validate_contract(contract)
  record = load_json(canonicalize_record(value))
  _need(set(record) == ENVELOPE_FIELDS, 'ENVELOPE_FIELDS')
  _need(type(record['schema_version']) is str and record['schema_version'] == '1', 'ENVELOPE_VERSION')
  _need(all(type(record[k]) is str for k in ['contract_id', 'source_class', 'record_id']), 'ENVELOPE_VALUE_TYPE')
  _need(record['contract_id'] == registered['contract_id'], 'CONTRACT_ID_MISMATCH')
  source_class = record['source_class']
  _need(source_class in SOURCE_CLASSES, 'SOURCE_CLASS_NOT_ADMITTED')
  record_id = record['record_id']
  _need(record_id in registered['registered_records'], 'UNREGISTERED_RECORD')
  expected = registered['registered_records'][record_id]
  _need(source_class == expected['source_class'], 'RECORD_CLASS_MISMATCH')
  payload = record['payload']
  _need(type(payload) is dict, 'PAYLOAD_TYPE')
  _need(payload.get('record_id') == record_id, 'PAYLOAD_RECORD_ID')
  payload_sha = hash_record(payload)
  _need(payload_sha == expected['canonical_payload_sha256'], 'PAYLOAD_HASH_MISMATCH')
  return {
    'schema_version': '1', 'contract_id': registered['contract_id'],
    'contract_sha256': EXPECTED_CONTRACT_SHA256, 'record_id': record_id,
    'source_class': source_class, 'canonical_payload_sha256': payload_sha,
    'admission': 'STATIC_METADATA_ONLY' if source_class == 'REGISTERED_STATIC_CONTEXT_METADATA' else 'REFERENCE_DESCRIPTOR_ONLY',
    'calculator_input_created': False, 'numeric_sample_admitted': False,
    'production_sample_admitted': False, 'context_instance_resolved': False,
    'r_budget_resolved': False, 'F70V_allowed': False, 'F71_allowed': False,
    'source_authentication_scope': 'FROZEN_HASH_REGISTRY_ONLY_NOT_PHYSICAL_ATTESTATION',
  }
