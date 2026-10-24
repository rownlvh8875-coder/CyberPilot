"""Frozen metadata/source-only audit authority; no numeric executor."""

from openpilot.tools.cyber_autotune import empirical_plant_policy as p

INVENTORY_SHA = 'e4c796ef3211e8c0d7be1094e80e8e4845ba255398764992b1da5db640e46c2b'
MAX_GENERATIONS = 10
SCHEMA_FAILURES = frozenset(('UNKNOWN_SOURCE_SCHEMA', 'SOURCE_SCHEMA_MISMATCH'))


def triage_policy():
  return p.seal({
    'schema': 'EMPIRICAL_SOURCE_AUDIT_TRIAGE_POLICY_V1',
    'inventory_sha256': INVENTORY_SHA,
    'primary_status': 'ROUTE_DIFFERENT_SOURCE_GENERATION',
    'primary_maximum': 5,
    'secondary_condition': 'PRIMARY_ADMITTED_TRAIN_DEV_POOL_ROUTE_COUNT_LESS_THAN_2',
    'secondary_status': 'ROUTE_IDENTITY_AMBIGUOUS',
    'secondary_ranking': ['route_count_DESC', 'segment_count_DESC', 'generation_id_ASC'],
    'secondary_maximum': 3,
    'tertiary_schema_failures_only': sorted(SCHEMA_FAILURES),
    'tertiary_maximum': 2,
    'maximum_generations': MAX_GENERATIONS,
    'numeric_payload_access': False,
    'numeric_coverage': None,
    'old_route_role': 'TRAIN_DEV_CANDIDATE_ONLY',
    'future_holdout': 'FUTURE_UNTOUCHED_HOLDOUT_REQUIRED',
    'generic_parser_fallback': False,
  })


def selection(buckets):
  primary, secondary, tertiary = [], [], []
  for b in buckets:
    counts = b['status_counts']
    if counts.get('ROUTE_DIFFERENT_SOURCE_GENERATION', 0):
      primary.append(b['generation_id'])
    if counts.get('ROUTE_IDENTITY_AMBIGUOUS', 0):
      secondary.append(b)
    reasons = b.get('failure_reasons', [])
    if counts.get('ROUTE_CORRUPT_OR_INCOMPLETE', 0) and reasons and set(reasons) <= SCHEMA_FAILURES:
      tertiary.append(b)
  if len(primary) > 5:
    raise ValueError('PRIMARY_EXCEEDS_FROZEN_MAXIMUM')
  def ranking(b):
    return (-b['route_count'], -b['segment_count'], b['generation_id'])
  secondary = [b['generation_id'] for b in sorted(secondary, key=ranking) if b['generation_id'] not in primary][:3]
  tertiary = [b['generation_id'] for b in sorted(tertiary, key=ranking) if b['generation_id'] not in primary + secondary][:2]
  return p.seal({
    'schema': 'EMPIRICAL_SOURCE_AUDIT_SELECTION_V1',
    'policy_sha256': triage_policy()['receipt_sha256'],
    'primary': sorted(primary), 'secondary_predeclared': secondary, 'tertiary_predeclared': tertiary,
    'tertiary_unproven_failure_taxonomy_excluded': True,
    'selection_basis': 'IMMUTABLE_METADATA_ONLY_BEFORE_SOURCE_AUDIT',
  })


def execution_set(selected, primary_admitted_route_count):
  p.verify(selected)
  if (selected.get('schema') != 'EMPIRICAL_SOURCE_AUDIT_SELECTION_V1'
      or selected.get('policy_sha256') != triage_policy()['receipt_sha256']):
    raise ValueError('EXACT_TRIAGE_POLICY_REQUIRED')
  for key, maximum in (('primary', 5), ('secondary_predeclared', 3), ('tertiary_predeclared', 2)):
    if type(selected.get(key)) is not list or len(selected[key]) > maximum:
      raise ValueError('TRIAGE_TIER_LIMIT')
  if type(primary_admitted_route_count) is not int or primary_admitted_route_count < 0:
    raise ValueError('INVALID_POOL_COUNT')
  extra = [] if primary_admitted_route_count >= 2 else selected['secondary_predeclared'] + selected['tertiary_predeclared']
  result = selected['primary'] + extra
  if len(result) > MAX_GENERATIONS or len(set(result)) != len(result):
    raise ValueError('AUDIT_LIMIT_OR_DUPLICATE')
  return result


def manifest():
  # Alternatives cover known upstream layout migrations, never fuzzy file search.
  files = {
    'logger': ['openpilot/system/loggerd/logger.cc', 'system/loggerd/logger.cc'],
    'logger_header': ['openpilot/system/loggerd/logger.h', 'system/loggerd/logger.h'],
    'logger_start': ['openpilot/system/loggerd/loggerd.cc', 'system/loggerd/loggerd.cc'],
    'logger_config': ['openpilot/system/loggerd/loggerd.h', 'system/loggerd/loggerd.h'],
    'schema_log': ['openpilot/cereal/log.capnp', 'cereal/log.capnp'],
    'schema_custom': ['openpilot/cereal/custom.capnp', 'cereal/custom.capnp'],
    'schema_deprecated': ['openpilot/cereal/deprecated.capnp', 'cereal/deprecated.capnp'],
    'schema_car': ['opendbc_repo/opendbc/car/car.capnp', 'cereal/car.capnp'],
    'services': ['openpilot/cereal/services.py', 'cereal/services.py'],
    'card': ['openpilot/selfdrive/car/card.py', 'selfdrive/car/card.py'],
    'controller': ['opendbc_repo/opendbc/car/hyundai/carcontroller.py', 'selfdrive/car/hyundai/carcontroller.py'],
    'controller_helpers': ['opendbc_repo/opendbc/car/__init__.py', 'selfdrive/car/__init__.py'],
    'controller_limits': ['opendbc_repo/opendbc/car/hyundai/values.py', 'selfdrive/car/hyundai/values.py'],
    'can_builder': ['opendbc_repo/opendbc/car/hyundai/hyundaican.py', 'selfdrive/car/hyundai/hyundaican.py'],
    'canfd_builder': ['opendbc_repo/opendbc/car/hyundai/hyundaicanfd.py', 'selfdrive/car/hyundai/hyundaicanfd.py'],
    'carstate': ['opendbc_repo/opendbc/car/hyundai/carstate.py', 'selfdrive/car/hyundai/carstate.py'],
    'interface': ['opendbc_repo/opendbc/car/hyundai/interface.py', 'selfdrive/car/hyundai/interface.py'],
    'interface_base': ['opendbc_repo/opendbc/car/interfaces.py', 'selfdrive/car/interfaces.py'],
    'dbc': ['opendbc_repo/opendbc/dbc/hyundai_kia_generic.dbc', 'opendbc/hyundai_kia_generic.dbc'],
    'sensor_main': ['openpilot/system/sensord/sensord.cc', 'system/sensord/sensord.cc'],
  }
  return p.seal({
    'schema': 'EMPIRICAL_SOURCE_MANIFEST_V1', 'files': files,
    'sensor_dependency_prefixes': ['openpilot/system/sensord/sensors/', 'system/sensord/sensors/'],
    'schema_dependency_extensions': ['.capnp'],
    'license_paths': ['LICENSE', 'LICENSE.md'],
    'scope': ['LOGGER', 'SCHEMA', 'COMMAND_PATH', 'MEASURED_STATE', 'DBC', 'DIRECT_SENSOR', 'CAR_PARAMS'],
    'completeness': 'ALL_REQUIRED_GROUPS_AND_SCHEMA_IMPORTS_AND_SENSOR_PRODUCERS_REQUIRED',
    'equivalence': 'FULL_RELEVANT_BYTES_OR_REVIEWED_EXACT_SYMBOL_DIFFERENCES_ONLY',
    'unrelated_changes_not_evidence': True,
  })


def future_holdout_contract():
  return p.seal({
    'schema': 'FUTURE_EMPIRICAL_HOLDOUT_ADMISSION_V1',
    'requirements': ['source_equivalent', 'same_empirical_profile', 'source_audit_complete',
                     'metadata_complete', 'numeric_previously_unopened', 'role_frozen_before_numeric',
                     'distinct_route', 'no_prior_analysis', 'complete_lineage', 'required_messages'],
    'old_prior_unknown_allowed': False, 'actual_holdout_created': False,
    'numeric_opening_authorized': False,
  })


def admit_future_holdout(evidence):
  required = set(future_holdout_contract()['requirements'])
  if set(evidence) != required or any(type(x) is not bool for x in evidence.values()):
    raise ValueError('EXACT_HOLDOUT_EVIDENCE_REQUIRED')
  return all(evidence.values())
