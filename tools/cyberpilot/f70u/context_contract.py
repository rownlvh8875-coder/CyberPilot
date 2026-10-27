"""Versioned static evidence validation; no vehicle discovery or control imports."""
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
ARTIFACTS = ROOT / 'artifacts/f70u'
MAX_DOCUMENT_BYTES = 2 * 1024 * 1024
MAX_DOCUMENT_DEPTH = 64


@dataclass(frozen=True)
class StaticContextContract:
  data: dict[str, Any]


@dataclass(frozen=True)
class ValidationResult:
  schema_valid: bool
  schema_status: str
  instance_status: str
  errors: tuple[str, ...]
  unresolved_fields: tuple[str, ...]
  contract_sha256: str | None

  def as_dict(self) -> dict[str, Any]:
    return {'schema_valid': self.schema_valid, 'context_schema_status': self.schema_status,
            'static_context_instance': self.instance_status, 'errors': list(self.errors),
            'unresolved_fields': list(self.unresolved_fields), 'unresolved_count': len(self.unresolved_fields),
            'contract_sha256': self.contract_sha256}


def _json_value(value: Any, depth: int = 0) -> None:
  if depth > MAX_DOCUMENT_DEPTH:
    raise ValueError('F70U_JSON_DEPTH')
  if type(value) is dict:
    if not all(type(key) is str for key in value):
      raise ValueError('F70U_JSON_KEY')
    for item in value.values():
      _json_value(item, depth + 1)
  elif type(value) is list:
    for item in value:
      _json_value(item, depth + 1)
  elif value is not None and type(value) not in (str, int, bool):
    raise ValueError('F70U_JSON_TYPE')


def _bytes(value: Any) -> bytes:
  _json_value(value)
  try:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode('utf-8')
  except (ValueError, UnicodeError, RecursionError):
    raise ValueError('F70U_JSON_ENCODING') from None


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
  result: dict[str, Any] = {}
  for key, value in pairs:
    if key in result:
      raise ValueError('F70U_DUPLICATE_KEY')
    result[key] = value
  return result


def _forbidden_number(value: str) -> Any:
  raise ValueError('F70U_NONINTEGER_JSON_NUMBER')


def _read_json(path: Path) -> dict[str, Any]:
  try:
    with path.open('rb') as handle:
      raw = handle.read(MAX_DOCUMENT_BYTES + 1)
    if len(raw) > MAX_DOCUMENT_BYTES:
      raise ValueError('F70U_JSON_SIZE')
    value = json.loads(raw.decode('utf-8'), object_pairs_hook=_pairs, parse_float=_forbidden_number, parse_constant=_forbidden_number)
    if type(value) is not dict:
      raise ValueError('F70U_JSON_OBJECT')
    _json_value(value)
    return value
  except (UnicodeError, json.JSONDecodeError, RecursionError):
    raise ValueError('F70U_JSON_PARSE') from None


def load_context_contract(path: str | Path) -> StaticContextContract:
  return StaticContextContract(_read_json(Path(path)))


def canonicalize_context_contract(contract: StaticContextContract) -> bytes:
  return _bytes(contract.data)


def hash_context_contract(contract: StaticContextContract) -> str:
  return hashlib.sha256(canonicalize_context_contract(contract)).hexdigest()


def _matches_type(value: Any, kind: str) -> bool:
  types = {'object': dict, 'array': list, 'string': str, 'integer': int, 'boolean': bool, 'null': type(None)}
  return kind in types and type(value) is types[kind]


def _shape(value: Any, schema: dict[str, Any], path: str, errors: list[str]) -> None:
  kinds = schema.get('type')
  if kinds is not None:
    names = kinds if type(kinds) is list else [kinds]
    if not any(_matches_type(value, name) for name in names):
      errors.append('SCHEMA_TYPE:' + path)
      return
  if 'const' in schema and _bytes(value) != _bytes(schema['const']):
    errors.append('SCHEMA_CONST:' + path)
  if type(value) is dict:
    properties = schema.get('properties', {})
    for name in schema.get('required', []):
      if name not in value:
        errors.append('SCHEMA_REQUIRED:' + path + '.' + name)
    for name, item in value.items():
      if name in properties:
        _shape(item, properties[name], path + '.' + name, errors)
      elif schema.get('additionalProperties') is False:
        errors.append('SCHEMA_UNKNOWN:' + path + '.' + name)
  if type(value) is list and 'items' in schema:
    for index, item in enumerate(value):
      _shape(item, schema['items'], path + '[' + str(index) + ']', errors)


def _get(data: dict[str, Any], path: str) -> Any:
  value: Any = data
  for part in path.split('.'):
    if type(value) is not dict or part not in value:
      return None
    value = value[part]
  return value


def _semantic(data: dict[str, Any], schema: dict[str, Any], errors: list[str]) -> list[str]:
  registered = schema['x-registered-values']
  for path, expected in registered.items():
    if _bytes(_get(data, path)) != _bytes(expected):
      errors.append('UNREGISTERED_BINDING:' + path)
  selected = _get(data, 'platform_binding.selected_candidate')
  if selected is not None:
    errors.append('SELECTION_AUTHORITY_UNREGISTERED')
  if _get(data, 'platform_binding.candidate_count') != registered['platform_binding.candidate_count']:
    errors.append('CANDIDATE_COUNT')
  architecture, can_fd = _get(data, 'can_architecture.architecture'), _get(data, 'can_architecture.is_can_fd')
  if (architecture == 'CLASSIC_CAN' and can_fd is True) or (architecture == 'CAN_FD' and can_fd is False):
    errors.append('ARCHITECTURE_CONFLICT')
  if _get(data, 'can_architecture.hda_generation') == 'HDA2':
    errors.append('HDA_AUTHORITY_NOT_REGISTERED_FOR_OWNER')
  if _get(data, 'can_architecture.camera_scc') is True and _get(data, 'can_architecture.radar_scc') is True:
    errors.append('SCC_ORIGIN_CONFLICT')
  enabled, pcm = _get(data, 'control_modes.openpilot_longitudinal_enabled'), _get(data, 'control_modes.pcm_cruise')
  if type(enabled) is bool and type(pcm) is bool and enabled == pcm:
    errors.append('LONGITUDINAL_MODE_CONFLICT')
  lower, upper = _get(data, 'signal_binding.normalization_min'), _get(data, 'signal_binding.normalization_max')
  if type(lower) is not int or type(upper) is not int or lower >= upper or lower != -1 or upper != 1:
    errors.append('NORMALIZATION_DOMAIN')
  period = _get(data, 'time_binding.control_period_ns')
  if period is not None and (type(period) is not int or period <= 0):
    errors.append('PERIOD_NOT_POSITIVE_INTEGER_NS')
  dependencies = _get(data, 'dependency_policy')
  if type(dependencies) is not dict or any(value is not False for value in dependencies.values()):
    errors.append('DEPENDENCY_FORBIDDEN_OR_MISSING')
  if data.get('conflicts') != []:
    errors.append('CONFLICTS_PRESENT')
  unresolved = sorted(path for path in registered if _get(data, path) is None or
                      (type(_get(data, path)) is str and _get(data, path) in schema['x-unresolved-markers']))
  if data.get('unresolved_fields') != unresolved:
    errors.append('UNRESOLVED_SET_MISMATCH')
  expected_status = 'STATIC_CONTEXT_INSTANCE_UNRESOLVED' if unresolved else 'STATIC_CONTEXT_INSTANCE_RESOLVED'
  if data.get('static_context_instance') != expected_status:
    errors.append('RESOLUTION_CLAIM_FALSE')
  return unresolved


def validate_context_contract(contract: StaticContextContract) -> ValidationResult:
  errors: list[str] = []
  unresolved: list[str] = []
  digest = None
  try:
    digest = hash_context_contract(contract)
    schema = _read_json(ARTIFACTS / 'static_context_schema.json')
    _shape(contract.data, schema, '$', errors)
    unresolved = _semantic(contract.data, schema, errors)
  except (ValueError, TypeError, AttributeError):
    errors.append('SCHEMA_JSON_INVALID')
  valid = not errors
  state = 'STATIC_CONTEXT_INSTANCE_UNRESOLVED' if unresolved else 'STATIC_CONTEXT_INSTANCE_RESOLVED'
  return ValidationResult(valid, 'CONTRACT_SCHEMA_VALID' if valid else 'INVALID', state if valid else 'NOT_VALIDATED',
                          tuple(sorted(set(errors))), tuple(unresolved), digest)


def generate_contract_bundle(contract: StaticContextContract, output_dir: Path) -> dict[str, str]:
  result = validate_context_contract(contract)
  if not result.schema_valid:
    raise ValueError('F70U_INVALID_CONTEXT_CONTRACT')
  output_dir.mkdir(parents=True, exist_ok=True)
  outputs = {name: _bytes(_read_json(ARTIFACTS / name)) for name in
             ['static_context_schema.json', 'static_context_input_template.json', 'F70U_PLATFORM_CANDIDATES.json']}
  outputs.update({'context_validation_result.json': _bytes(result.as_dict()),
                  'canonical_context_contract.json': canonicalize_context_contract(contract),
                  'context_contract.sha256': (hash_context_contract(contract) + '\n').encode(),
                  'F70U_FINAL_RESULT.json': _bytes({'identity': 'F70U_DETERMINISTIC_STATIC_RESULT_V1',
                                                   'status': 'F70U_STATIC_CONTEXT_SCHEMA_LOCAL_PASS_INSTANCE_UNRESOLVED',
                                                   'validation': result.as_dict(), 'R_BUDGET_UNRESOLVED': True,
                                                   'SOURCE_SCHEMA_UNQUALIFIED': 6000, 'candidate_NO_GO': True,
                                                   'RUNTIME_NO_GO': True, 'F71_authorized': False,
                                                   'next_allowed_step': 'F70U-A_OWNER_STATIC_CONTEXT_DECISION_AND_APPROVAL'})})
  for name, raw in outputs.items():
    (output_dir / name).write_bytes(raw)
  return {name: hashlib.sha256(raw).hexdigest() for name, raw in sorted(outputs.items())}
