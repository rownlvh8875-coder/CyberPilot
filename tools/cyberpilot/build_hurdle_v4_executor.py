"""Publish V4 implementation/synthetic evidence only, never execution authority."""

import argparse
import json
from pathlib import Path

from openpilot.tools.cyber_autotune import empirical_hurdle_v4_authorization as a

p = a.p
PREFIX = 'empirical-hurdle-stage1-v4-'
READY = 'V4_PRIVATE_EXECUTOR_READY_FOR_SEPARATE_RETROSPECTIVE_FITTING_AUTHORIZATION'
BLOCKED = 'V4_PRIVATE_EXECUTOR_IMPLEMENTATION_BLOCKED'
COMPONENTS = (
  'rank-certificate-design',
  'rank-certificate-validation',
  'separation-certificate-design',
  'separation-certificate-validation',
  'certificate-stress',
  'executor-authorization-policy',
  'executor-storage-policy',
  'executor-code-map',
  'executor-synthetic-results',
  'executor-repeatability',
  'executor-resume',
  'executor-readiness',
  'executor-validation',
)
REQUIRED = ('focused', 'prior', 'combined', 'full', 'lateral', 'ruff', 'compileall', 'json', 'publication', 'diff-check', 'scons')
FORBIDDEN = {
  'private_root',
  'source_root',
  'output_root',
  'coefficients',
  'threshold',
  'normalizer_values',
  'probabilities',
  'raw_ticks',
  'row_indices',
  'gps',
  'commands',
  'timestamps',
  'raw_paths',
  'gate_sequence',
}


def filename(component):
  return PREFIX + component + '.json'


def base(component):
  return {
    'schema': 'HURDLE_STAGE1_V4_EXECUTOR_IMPLEMENTATION_REVIEW_V1',
    'component': component,
    'baseline': 'c508cddf833ed7b98b12765f19c68f316f1710fc',
    'scope': 'IMPLEMENTATION_AND_SYNTHETIC_VALIDATION_ONLY',
    'actual_execution_authorized': False,
    'actual_private_numeric_access': 0,
    'actual_model_fit_calls': 0,
    'actual_threshold_search_calls': 0,
    'actual_development_calls': 0,
    'actual_rollout_calls': 0,
    'normalizer_fit_calls': 0,
    'stage2_fit_calls': 0,
    'raw_log_openings': 0,
    'qlog_openings': 0,
    'holdout_openings': 0,
    'holdout_discovery': 0,
    'holdout': 'CLOSED',
    'pooled_refit': 'NOT_AUTHORIZED',
    'vehicle_authority': 'NONE',
    'vehicle': ['NOT_READY', 'REAL_VEHICLE_UNVERIFIED', 'VEHICLE_ACTIVATION_BLOCKED'],
    'v4_actual': dict.fromkeys(('fitting', 'CV', 'development', 'rollout', 'selection', 'performance'), 'NOT_RUN'),
    'actual_coefficients': 'NOT_GENERATED',
    'hugging_face': 'NOT_REQUIRED_NOT_USED',
    'fitting_policy': 'HURDLE_STAGE1_CONTEXT_CONDITIONAL_LOGISTIC_V4_FITTING_POLICY_FROZEN',
    'historical_states_preserved': [
      'GLOBAL_SINGLE_THRESHOLD_FAMILY_RETROSPECTIVELY_EXHAUSTED',
      'V4_TWO_CONTEXT_POLICY_DECISION_INCONCLUSIVE',
      'V4_TWO_CONTEXT_CAUSAL_STATE_CONTRACT_ESTABLISHED',
      'HURDLE_STAGE1_V4_REPRESENTATION_DESIGN_FROZEN',
      'S2_RI_NO_ADMISSIBLE_CANDIDATE',
      'HURDLE_NO_ADMISSIBLE_CANDIDATE',
      'HURDLE_STAGE1_V2_NO_ADMISSIBLE_CANDIDATE',
      'HURDLE_STAGE1_V3_NO_ADMISSIBLE_CANDIDATE',
      'MODEL_SELECTION_FAILED_CLOSED',
      'STAGE2_LONG_HORIZON_RESIDUAL_RISK_REMAINS',
      'NO_MODEL_ADMITTED_FOR_FUTURE_HOLDOUT',
      'FINAL_POOLED_REFIT_NOT_AUTHORIZED',
      'FUTURE_UNTOUCHED_HOLDOUT_REQUIRED',
      'HOLDOUT_OPENING_CLOSED',
      'SEARCH_NOT_AUTHORIZED',
      'COMPOSITION_NOT_AUTHORIZED',
    ],
  }


def build(*, validation=None, reviews=None, stress=None):
  validation, reviews, stress = validation or {}, reviews or {}, stress or {}
  pack = a.contracts()
  bodies = {
    'rank-certificate-design': {
      'algorithm': 'EXACT_INCREMENTAL_ROW_ELIMINATION_THEN_DYADIC_INTEGER_BAREISS_MINOR',
      'input': 'FINITE_FLOAT64_C_ORDER',
      'rank_tolerance': 'sigma_max*max(N,P)*finfo(float64).eps',
      'acceptance': 'NUMERICAL_SVD_FULL_RANK_AND_EXACT_NONZERO_P_BY_P_MINOR',
      'dyadic': 'float.as_integer_ratio_NO_DECIMAL_ROUNDTRIP',
      'minor_row_choice': 'FIRST_EXACTLY_INDEPENDENT_ORIGINAL_ROWS',
      'bindings': ['matrix_content', 'labels_in_separation', 'basis', 'normalizer', 'parent_candidate_fold_source_receipts'],
      'certificate_location': 'PRIVATE_ONLY',
      'extra_empirical_column_drop': False,
      'outcomes': ['RANK_CERTIFICATE_PASS', 'RANK_SVD_FAILURE', 'RANK_EXACT_MINOR_NOT_FOUND', 'RANK_CERTIFICATE_INCONCLUSIVE'],
    },
    'rank-certificate-validation': {
      'cases': [
        'P4_P12_P32_P92_P93',
        'BAREISS_PIVOT_SWAP',
        'EXACT_DUPLICATE_COLUMN',
        'ADJACENT_BINARY64',
        'BAD_DETERMINANT',
        'MATRIX_BASIS_HASH_TAMPER',
        'FULL_SVD_BUT_PROPOSAL_RESOURCE_INCONCLUSIVE',
        'EXTREME_SCALE_EXACT_RANK_NOT_ENOUGH_FOR_SVD',
      ],
      'evidence': validation.get('focused'),
    },
    'separation-certificate-design': {
      'signed_design': 'A_i=(2*y_i-1)*X_i',
      'presence': 'ALL A_i*b>=0 AND SOME A_i*b>0',
      'absence': 'D*SUM_i(A_i)+SUM_active(q_i*A_i)=0 EXACTLY; D>0 INTEGER; q_i>0 INTEGER',
      'sparse_bound': 'AT_MOST_rank(A)_AT_MOST_P',
      'sparse_proof': [
        'Positive lambda rescales to lambda>=1, so -SUM(A) is a nonnegative rational conic combination.',
        'Conic Caratheodory reduces support to at most rank(A); rational independent generators give rational weights.',
        'Clear denominators to positive integer D and nonnegative sparse integers; divide common positive gcd.',
      ],
      'canonicalization': 'SORTED_DISTINCT_ACTIVE_ROWS_NO_ZERO_Q_GCD_ONE; PRESENCE_INTEGER_DIRECTION_POSITIVE_GCD_ONLY',
      'proposal': 'DETERMINISTIC_CONE_ACTIVE_SET_COLUMN_PROPOSAL_EXACT_GRAM_RECONSTRUCTION',
      'proposal_tie': 'SMALLEST_ORIGINAL_ROW_INDEX',
      'active_bound': 'P',
      'generator_completeness': 'INCOMPLETE_ALLOWED',
      'float_authority': False,
      'verification': 'EXACT_DYADIC_COLUMN_SUMS_OR_EXACT_ALL_ROW_MARGINS; EQUAL_ROWS_COMPRESSED_LOSSLESSLY',
      'resource_cap': 'OPERATIONAL_ONLY_DEFAULT_4*P*P_ITERATIONS; EXHAUSTION_INCONCLUSIVE_NEVER_GUESS',
      'presence_does_not_classify_complete_vs_quasi_from_zero_margins_alone': True,
      'large_fraction_matrix': False,
      'new_dependency': False,
    },
    'separation-certificate-validation': {
      'cases': [
        'COMPLETE',
        'QUASI',
        'OVERLAP',
        'DUPLICATES',
        'ZERO_FEATURE_ROWS',
        'INTERCEPT_ONLY',
        'NEAR_ZERO_DYADIC',
        'SIGNED_ZERO',
        'SPARSE_CORRECTION',
        'MANY_ZERO_MARGINS',
        'CORRUPT_D_Q_DIRECTION_HASH',
        'DEPENDENT_ACTIVE_SET',
        'RESOURCE_INCONCLUSIVE',
      ],
      'evidence': validation.get('focused'),
    },
    'certificate-stress': {
      'aggregate': stress,
      'stress_source_sha256': a.prior.digest(Path(__file__).with_name('validate_hurdle_v4_certificates.py')),
      'claim_limit': 'HIGH_N_HIGH_P_CONSTRUCTED_CASES_NOT_GENERAL_RUNTIME_GUARANTEE',
      'asymptotic_memory': 'O(N*P+P*P)_NO_N_BY_THRESHOLD_MATRIX',
      'verification_exactness': 'CERTIFIED_OR_INCONCLUSIVE',
    },
    'executor-authorization-policy': {
      'policies': pack['policies'],
      'schema': a.SCHEMA,
      'authorization_minting': False,
      'external_trusted_receipt_required': True,
      'trusted_sha_source': 'EXTERNAL_CALLER_SEPARATELY_APPROVED_ONE_SHOT',
      'precheck_order': [
        'PUBLIC_POLICY_RECEIPTS',
        'EXECUTION_HEAD',
        'EXECUTOR_SOURCE_HASHES',
        'EXTERNAL_TRUSTED_AUTHORIZATION',
        'E_STORAGE_IDENTITY',
        'ROOT_NON_OVERLAP',
        'CAPACITY',
        'PYTHON_NUMPY_BLAS_ENVIRONMENT',
        'SOURCE_MANIFEST_METADATA',
        'V1_NORMALIZER_IDENTITIES',
        'STAGE2_IDENTITIES',
        'ROUTE_ANCHOR_IDENTITIES',
        'NUMERIC_OPEN_AUTHORITY',
      ],
      'precheck_numeric_opens': 0,
      'schema_fields': sorted(a.AUTH_FIELDS),
      'replicas': ['repeat-1', 'repeat-2'],
      'no_default_roots': True,
      'live_recheck_each_numeric_adapter_and_write': True,
      'environment': {
        'python': '3.12.13',
        'numpy': '2.5.3',
        'BLAS_sha256': a.prior.legacy.BLAS_SHA,
        'OPENBLAS_NUM_THREADS': '1',
        'OMP_NUM_THREADS': '1',
        'dtype': 'float64',
        'order': 'C',
        'rng': 'NONE',
      },
    },
    'executor-storage-policy': {
      'volume': 'E_EXTERNAL_SSD',
      'proof': 'REUSE_V3_EXACT_LIVE_E_VOLUME_PROOF',
      'allow_C_D_F_WSL_OR_ALIAS': False,
      'roots': 'EXTERNAL_MANIFEST_BOUND_EXPLICIT_DISJOINT',
      'capacity': 'TWO_RUNS_PLUS_ATOMIC_PLUS_CERTIFICATE_AND_METADATA_BUDGETS_PLUS_RESERVE',
      'metadata_bound': 'AUTHORIZED_MAXIMUM_ENFORCED_ON_EVERY_JSON_WRITE_NOT_A_GUESSED_ESTIMATE',
      'proof_bit_budget': 'AUTHORIZED_OPERATIONAL_CAP_EXCEEDED_FAILS_CLOSED',
      'output_upper_bound_enforced_each_write': True,
      'format': a.prior.COMPRESSION,
      'source_writes': 0,
      'source_immutability': 'BEFORE_AND_AFTER_MANIFEST_MEMBERS_AND_AUTHORITATIVE_METADATA_BYTES',
      'scratch_deletion': 'NONE',
    },
    'executor-code-map': {
      'source_sha256': a.sources(),
      'source_bindings_are_not_execution_authority': True,
      'unchanged': ['V1_NUMERICAL_FUNCTIONS', 'V4_FITTING_POLICY', 'FINAL_32_CLAUSES', 'FROZEN_SELECTOR'],
      'actual_numeric_flow': [
        'PERMIT',
        'TRAIN_SOURCE',
        'V1_SHARED_NORMALIZER',
        'BOTH_HEAD_SUPPORT_RANK_SEPARATION',
        'INDEPENDENT_FROZEN_NEWTON',
        'ORIGINAL_ROW_COMBINED_SCORE',
        'GLOBAL_TRAIN_BA',
        'DURABLE_TRAIN_FINALIZATION',
        'DEV',
        'PROJECTED_CONTEXT_ROLLOUT',
        '32_CLAUSES',
        'BOTH_FOLD_SELECTION',
      ],
    },
    'executor-synthetic-results': {
      'evidence': validation.get('focused'),
      'coverage': [
        'ALL32_ORDERED_JOBS_TWO_INDEPENDENT_REPLICAS',
        'BOTH_HEAD_SUCCESS',
        'SUPPORT_AND_RANK_FAILURE',
        'COMPLETE_AND_QUASI_FAILURE',
        'CERTIFICATE_UNKNOWN',
        'OPTIMIZER_FAILURE',
        'GLOBAL_BA',
        'TRAIN_BEFORE_DEV',
        'ONE_STEP',
        'ALL_FOUR_ROLLOUT_HORIZONS',
        'GATE_PASS_AND_FAIL',
        'BOTH_FOLD_REQUIRED',
        'GATE_NOT_MOVEMENT_CONTEXT',
      ],
      'private_orchestrator_fixture_boundary': 'EXTERNAL_PROBES_AND_SOURCE_READERS_INJECTED_SYNTHETIC_ONLY',
    },
    'executor-repeatability': {
      'comparison': 'EVERY_SAVED_FILE_HASH_AND_CANONICAL_MANIFEST_BYTE_IDENTITY',
      'includes': ['BASIS', 'CERTIFICATES', 'COEFFICIENTS', 'CONVERGENCE', 'TRAIN_SCORE', 'BA_RECEIPT', 'DEV', 'ROLLOUT', 'GATES', 'SELECTION'],
      'telemetry': 'ELAPSED_RSS_EXCLUDED_FROM_AUTHORITATIVE_CERTIFICATE_BYTES',
      'evidence': validation.get('focused'),
      'actual_repeatability': 'NOT_RUN',
    },
    'executor-resume': {
      'mode': 'VERIFY_ONLY',
      'recompute_calls': 0,
      'checks': [
        'TRUSTED_AUTH_AND_MANIFEST_SHA',
        'LIVE_E_IDENTITY',
        'SCHEMA',
        'DEPENDENCY_GRAPH',
        'ALL_FILE_HASHES',
        'RECEIPT_SEALS',
        'DECODED_NPY_SHAPE_DTYPE_CONTENT',
      ],
      'traps': ['SOURCE_LOADER', 'MODEL_LOADER', 'RANK_GENERATOR', 'SEPARATION_GENERATOR', 'NEWTON', 'PROBABILITY', 'THRESHOLD', 'DEV', 'ROLLOUT', 'SELECTOR'],
      'corruption': 'FAIL_CLOSED_NO_REGENERATION',
      'evidence': validation.get('focused'),
    },
    'executor-validation': {'observed_checks': validation, 'independent_reviews': reviews},
  }
  blockers = [name + '_VALIDATION_MISSING_OR_FAILED' for name in REQUIRED if name not in validation or validation[name].get('exit_code') != 0]
  blockers += [label + '_REVIEW_NOT_APPROVED' for label in ('A', 'B') if reviews.get(label) != 'APPROVED']
  if not stress.get('cases') or not any(row.get('N', 0) >= 200000 and row.get('P', 0) >= 93 for row in stress.get('cases', [])):
    blockers.append('MEANINGFUL_SYNTHETIC_STRESS_MISSING')
  bodies['executor-readiness'] = {
    'status': BLOCKED if blockers else READY,
    'blockers': blockers,
    'implementation_review': 'HURDLE_STAGE1_V4_EXECUTOR_IMPLEMENTATION_REVIEW_COMPLETE',
    'actual_execution_authorized': False,
    'next_step': 'SEPARATE_EXECUTION_POLICY_AND_EXTERNAL_AUTHORIZATION_REVIEW',
    'states': []
    if blockers
    else [
      'V4_EXACT_RANK_CERTIFICATE_IMPLEMENTATION_VERIFIED',
      'V4_EXACT_SEPARATION_CERTIFICATE_IMPLEMENTATION_VERIFIED',
      'V4_AUTHORIZATION_FIREWALL_VERIFIED',
      'V4_E_STORAGE_IMPLEMENTATION_VERIFIED',
      'V4_EXECUTOR_SYNTHETIC_END_TO_END_PASS',
      'V4_EXACT_REPEATABILITY_IMPLEMENTATION_VERIFIED',
      'V4_VERIFY_ONLY_RESUME_IMPLEMENTATION_VERIFIED',
    ],
  }
  return {filename(name): p.seal({**base(name), **bodies[name]}) for name in COMPONENTS}


def validate(rows):
  a.need(set(rows) == {filename(k) for k in COMPONENTS}, 'V4_PUBLICATION_CONFLICT')

  def walk(value):
    if isinstance(value, dict):
      a.need(not FORBIDDEN.intersection(value), 'V4_PUBLICATION_PRIVATE_FIELD')
      for item in value.values():
        walk(item)
    elif isinstance(value, list):
      for item in value:
        walk(item)
    elif isinstance(value, str):
      a.need(not any(s in value.casefold() for s in ('/home/', 'e:\\', 'd:\\', 'c:\\', '/mnt/e/')), 'V4_PUBLICATION_PRIVATE_PATH')

  for row in rows.values():
    walk(row)
    p.verify(row)
    a.need(row['actual_execution_authorized'] is False and row['actual_private_numeric_access'] == 0)


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--evidence', type=Path)
  parser.add_argument('--stress', type=Path)
  parser.add_argument('--reviews', type=Path)
  args = parser.parse_args()

  def read(path):
    return json.loads(path.read_text()) if path else {}

  rows = build(validation=read(args.evidence), reviews=read(args.reviews), stress=read(args.stress))
  validate(rows)
  for name, row in rows.items():
    (p.PUBLIC / name).write_text(json.dumps(row, sort_keys=True, indent=2) + '\n')


if __name__ == '__main__':
  main()
