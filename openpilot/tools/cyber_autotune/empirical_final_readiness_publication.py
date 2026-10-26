"""Publish additive final-readiness contracts from pinned public aggregates only."""
import argparse
from pathlib import Path
import re
from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_final_readiness as r

FILES = ('empirical-final-readiness-precedence-v1.json', 'empirical-final-readiness-resolution-v2.json',
         'empirical-causal-support-partition-v1.json', 'empirical-causal-support-admission-policy-v1.json',
         'empirical-development-data-admission-contract-v1.json', 'empirical-final-readiness-repeatability-v2.json')


def validate_public(row):
  p.verify(row)
  forbidden = {'rows', 'targets', 'predictions', 'residuals', 'coefficients', 'local_path', 'path',
               'grid_time_ns', 'state_time_ns', 'row_origin', 'raw_command', 'xyz'}
  def visit(value):
    if isinstance(value, dict):
      if forbidden & value.keys():
        raise ValueError('PRIVATE_ROWS_OR_ORIGINS_NOT_PUBLISHABLE')
      for child in value.values():
        visit(child)
    elif isinstance(value, list):
      for child in value:
        visit(child)
    elif isinstance(value, str) and (value.startswith('/') or re.match(r'^[A-Za-z]:[\\/]', value) or '\\\\' in value):
      raise ValueError('PRIVATE_PATH_NOT_PUBLISHABLE')
  visit(row)
  return row


def build(evidence):
  x = r.validate_inputs(evidence)
  resolution, partition = r.resolve(x), r.partition(x)
  code = {n: p.sha((Path(__file__).parent/(n+'.py')).read_bytes()) for n in (
    'empirical_final_readiness', 'empirical_causal_support_guard', 'empirical_final_readiness_publication')}
  precedence = p.seal({'schema': 'EMPIRICAL_FINAL_READINESS_PRECEDENCE_V1', 'generation': r.GENERATION,
    'precedence': r.PRECEDENCE, 'authoritative_source': r.FINAL, 'authoritative_sha256': r.PINS[r.FINAL],
    'historical_execution_source': r.EXECUTION, 'historical_execution_sha256': r.PINS[r.EXECUTION],
    'intermediate_source': r.INTERMEDIATE, 'intermediate_sha256': r.PINS[r.INTERMEDIATE],
    'fallback_allowed': False, 'missing_final_behavior': 'FAIL_CLOSED_NO_READY_FALLBACK',
    'latest_filename_or_mtime_is_not_authority': True, 'historical_receipts_rewritten': False,
    'source_identities': code})
  required = x['empirical-causal-context-schema-v2-execution-v1.json']['required_fields']
  admission = p.seal({'schema': 'EMPIRICAL_CAUSAL_SUPPORT_ADMISSION_POLICY_V1',
    'resolution_sha256': resolution['receipt_sha256'], 'partition_sha256': partition['receipt_sha256'],
    'rlog_manifest_sha256': resolution['rlog_dataset_manifest_sha256'],
    'admitted_input_role': r.ROLE, 'admitted_stream': 'rlog.zst',
    'denied_stream': 'qlog.zst', 'qlog_reason': 'HISTORICAL_ACCOUNTING_ONLY_NOT_MODEL_SUPPORT',
    'guard_sha256': code['empirical_causal_support_guard'],
    'required_field_names': required, 'actual_rate_value_required': True,
    'age_limit_ns': 20_000_000, 'grid_step_ns': 10_000_000, 'minimum_development_support': 201,
    'age_policy_changed': False, 'interpolation_allowed': False, 'forward_fill_allowed': False,
    'stale_admission_allowed': False, 'qlog_promotion_allowed': False,
    'segment_admission_before_arrays': 'PINNED_RLOG_MANIFEST_EXACT_MEMBER_RECEIPT_CONTENT_IDENTITY',
    'row_gate': 'SEALED_ARRAY_IDENTITIES_AND_CAUSAL_VALID_AND_LEGACY_DIAGNOSTIC_VALID_REQUIRED',
    'history_gate': 'SAME_ROUTE_SEGMENT_CAUSAL_RUN_CONTIGUOUS_INTEGER_GRID_VALID_WINDOW',
    'unknown_or_missing': 'FAIL_CLOSED_NEVER_ZERO_FALSE_FILL',
    'coverage_is_not_model_support': True, 'actual_support_calculation': 'NOT_RUN',
    'model_operations_authorized': False, 'cv_scoring_authorized': False,
    'holdout_allowed': False, 'independent_validation_allowed': False})
  families = x['future-model-family-readiness-v1.json']['families']
  contract = p.seal({'schema': 'EMPIRICAL_DEVELOPMENT_DATA_ADMISSION_CONTRACT_V1',
    'generation': r.GENERATION, 'resolution_sha256': resolution['receipt_sha256'],
    'partition_sha256': partition['receipt_sha256'], 'admission_policy_sha256': admission['receipt_sha256'],
    'causal_schema_sha256': x['empirical-causal-context-schema-v2-execution-v1.json']['base_sha256'],
    'h1_mapping_sha256': x['empirical-causal-h1-mapping-v1.json']['receipt_sha256'],
    'model_shortlist_sha256': x['future-model-family-readiness-v1.json']['receipt_sha256'],
    'families': [{'family': f['family'], 'name': f['name'], 'required_concepts': f['fields'],
      'implementation_allowed': False, 'selected': False,
      'additional_source_gate': 'ACTUAL_STEERING_RATE_UNIT_SIGN_AUDIT_REQUIRED' if f['family'] != 'S3'
                                else 'RATE_UNIT_SIGN_AND_SOURCE_DEFINED_DEADZONE_HYSTERESIS_AUDIT_REQUIRED'} for f in families],
    'family_selection': 'NOT_RUN', 'model_fitting_allowed': False, 'cv_scoring_allowed': False,
    'dataset_role': r.ROLE, 'prior_numeric_exposure': True,
    'retrospective_development_only': True, 'holdout_allowed': False, 'independent_validation_allowed': False,
    'steering_rate_values': 'ACTUAL_VALUES_PRESERVED_IN_RLOG_SUBSET',
    'steering_rate_unit': 'DBC_UNIT_EMPTY_PHYSICAL_RATE_SEMANTICS_UNRESOLVED',
    'request_output_linkage': 'PUBLISH_ALIGNED_DIFFERENCE_NOT_SAME_TRANSACTION',
    'physical_eps_acknowledgement': None, 'unknown_limiter_reasons': None,
    'future_prerequisites': ['SEPARATE_MODEL_IMPLEMENTATION_AND_FITTING_AUTHORIZATION',
      'SOURCE_BOUND_RATE_UNIT_SIGN_CONTRACT', 'PREDECLARED_FAMILY_CONFIG_RESET_HISTORY_METRIC_SUPPORT_POLICY',
      'ROUTE_DISJOINT_RETROSPECTIVE_DEVELOPMENT_POLICY', 'EXACT_RLOG_ROW_ADMISSION_GUARD',
      'FUTURE_UNTOUCHED_HOLDOUT_BEFORE_QUALIFICATION'],
    'new_model_implementation': False, 'model_coefficients_generated': False, 'model_support_computed': False,
    'model_selection': 'NOT_RUN', 'holdout': 'HOLDOUT_OPENING_CLOSED', 'opening_count': 0,
    'future_holdout': 'FUTURE_UNTOUCHED_HOLDOUT_REQUIRED', 'stage_b': 'STAGE_B_SIGNAL_ADMISSION_BLOCKED',
    'calibration_blockers': p.BLOCKERS, 'source_identities': code})
  return dict(zip(FILES[:-1], (precedence, resolution, partition, admission, contract), strict=True))


def bundle(evidence=None):
  x = r.load() if evidence is None else evidence
  first, second = build(x), build(x)
  if p.canonical(first) != p.canonical(second):
    raise ValueError('FINAL_READINESS_EXACT_REPEATABILITY_CONFLICT')
  first[FILES[-1]] = p.seal({'schema': 'EMPIRICAL_FINAL_READINESS_REPEATABILITY_V2',
    'repeats': 2, 'exact': True, 'bundle_sha256': p.sha(p.canonical(first)),
    'receipts': {n: row['receipt_sha256'] for n, row in first.items()},
    'raw_logs_opened': False, 'private_arrays_opened': False, 'private_stores_written': False,
    'historical_receipts_modified': False, 'source_age_policy_changed': False,
    'model_fitting': 'NOT_RUN', 'model_selection': 'NOT_RUN', 'cv_scoring': 'NOT_RUN',
    'holdout': 'HOLDOUT_OPENING_CLOSED', 'opening_count': 0})
  for row in first.values():
    validate_public(row)
  return first


def publish(directory=p.PUBLIC, evidence=None):
  directory = Path(directory)
  if not directory.is_absolute() or '..' in directory.parts:
    raise ValueError('ABSOLUTE_NO_TRAVERSAL_OUTPUT_REQUIRED')
  result = bundle(evidence)
  # Preflight all targets before any write; exact resume, never partial stale overwrite.
  for name, row in result.items():
    path = directory/name
    if any(x.is_symlink() for x in (path, *path.parents)):
      raise ValueError('NO_SYMLINK_PUBLICATION')
    if path.exists():
      import json
      if json.loads(path.read_bytes()) != row:
        raise ValueError('IMMUTABLE_READINESS_PUBLICATION_CONFLICT')
  for name, row in result.items():
    p.persist(directory/name, row)
  return result


def main():
  parser = argparse.ArgumentParser(description='Publish final readiness; no private input or numeric operations.')
  parser.add_argument('--output', type=Path, default=p.PUBLIC)
  args = parser.parse_args()
  result = publish(args.output)
  print(result[FILES[1]]['final_dataset_status'])


if __name__ == '__main__':
  main()
