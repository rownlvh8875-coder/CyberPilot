"""Allowlisted future V3 aggregates and synthetic-only implementation evidence.

No source loader or CLI for actual performance publication is provided here.
"""

import math
import re
from openpilot.tools.cyber_autotune import empirical_hurdle_v3_io as io

p = io.p
COUNTS = {'TP', 'TN', 'FP', 'FN', 'tp', 'count', 'train_count', 'reference_tp', 'candidate_count', 'feasible_count',
          'exact_hit_count', 'static_projected_false_move_count', 'within_one_tick_count', 'admissible_count', 'path_moved_count'}
METRICS = {'rmse', 'mae', 'p95', 'exact_hit', 'within_one_tick', 'all_rmse', 'false_move_rate', 'missed_move_rate',
           'precision', 'recall', 'specificity', 'balanced_accuracy', 'predicted_move_fraction'}
STRINGS = {'schema', 'candidate_id', 'fold', 'status', 'receipt_sha256', 'anchor_sha256', 'comparator_anchor_sha256', 'id',
           'authority', 'selected_candidate'}
MAPS = {'threshold', 'objective', 'train_metrics', 'all', 'true_move', 'stage1', 'stage1_diagnostics', 'one_step',
        'candidate', 'comparator', 'rollout', 'overall', 'path_moved', 'move', 'gate', 'comparison', 'train', 'v1', 'v2', 'v3',
        'clauses'} | {str(h) for h in io.verified.HORIZONS}
FLAGS = {'pass', 'evaluated', 'feasible', 'tp_constraint_pass'}
LISTS = {'jobs', 'failures', 'recovered', 'newly_failed', 'unchanged_pass', 'unchanged_fail'}


def validate_public(value):
  """Strict aggregate schema: no numerical sequences or free-form strings."""
  def visit(row):
    io.require(type(row) is dict, 'V3_PUBLICATION_BOUNDARY_CONFLICT')
    for key, item in row.items():
      valid = False
      if key in COUNTS:
        valid = type(item) is int and item >= 0
      elif key in METRICS:
        valid = item is None or type(item) in (int, float) and math.isfinite(item)
      elif key in FLAGS:
        valid = type(item) is bool
      elif key in STRINGS:
        valid = item is None or type(item) is str and re.fullmatch(r'[A-Za-z0-9_:-]+', item) is not None
      elif key in LISTS or key == 'clauses' and type(item) is list:
        valid = type(item) is list
        if valid:
          for child in item:
            if key in ('jobs', 'clauses'):
              visit(child)
            else:
              io.require(type(child) is str and re.fullmatch(r'[A-Z0-9_]+', child) is not None, 'V3_PUBLICATION_BOUNDARY_CONFLICT')
      elif key in MAPS:
        valid = item is None or type(item) is dict
        if type(item) is dict:
          visit(item)
      io.require(valid, 'V3_PUBLICATION_BOUNDARY_CONFLICT')
  visit(value)
  return value


def public_job(job):
  # Never recursively copy an arbitrary private job into public evidence.
  result = {key: job[key] for key in ('candidate_id', 'fold', 'status', 'train_count')}
  result['reference_tp'] = job['reference']['reference_tp']
  decision = job['threshold']
  result['threshold'] = {key: decision[key] for key in ('status', 'receipt_sha256', 'candidate_count', 'feasible_count')}
  objective = decision['objective']
  result['threshold']['objective'] = None if objective is None else {
    key: objective[key] for key in ('tp', 'exact_hit_count', 'static_projected_false_move_count', 'within_one_tick_count', 'feasible')}
  result['tp_constraint_pass'] = objective is not None and objective['tp'] >= result['reference_tp']
  for key in ('train_metrics', 'one_step', 'true_move', 'stage1_diagnostics', 'rollout', 'gate', 'comparison'):
    if key in job:
      result[key] = job[key]
  return validate_public(result)


def implementation_evidence(counts):
  """No actual result: these artifacts describe this source/test increment."""
  io.require(type(counts) is dict and set(counts) == {'focused', 'full', 'combined', 'replay'}
             and all(type(value) is int and value >= 0 for value in counts.values()), 'V3_PUBLICATION_BOUNDARY_CONFLICT')
  names = ('executor-implementation', 'threshold-evaluator-validation', 'authorization-firewall', 'model-reuse-executor',
           'reference-tp-validation', 'development-executor-validation', 'rollout-executor-validation', 'gate-selection-binding',
           'storage-implementation', 'repeatability-implementation', 'resume-implementation', 'executor-readiness', 'executor-validation')
  states = ('HURDLE_STAGE1_V3_EXECUTOR_IMPLEMENTATION_COMPLETE', 'V3_BOUNDED_EXACT_EVALUATOR_READY',
            'V3_PRIVATE_ORCHESTRATOR_IMPLEMENTED_NOT_AUTHORIZED', 'V3_AUTHORIZATION_FIREWALL_VERIFIED',
            'V3_MODEL_REUSE_EXECUTOR_VERIFIED', 'V3_REFERENCE_TP_CONSTRAINT_VERIFIED',
            'V3_DEVELOPMENT_EXECUTOR_VERIFIED_SYNTHETIC', 'V3_ROLLOUT_EXECUTOR_VERIFIED_SYNTHETIC',
            'V3_ACCEPTANCE_GATE_BINDING_VERIFIED', 'V3_SELECTION_BINDING_VERIFIED', 'V3_STORAGE_IMPLEMENTATION_VERIFIED',
            'V3_REPEATABILITY_IMPLEMENTATION_VERIFIED', 'V3_RESUME_IMPLEMENTATION_VERIFIED',
            'V3_READY_FOR_SEPARATE_RETROSPECTIVE_EXECUTION_AUTHORIZATION')
  details = {
    'threshold-evaluator-validation': {'numeric_base': 'UNCHANGED_V2_ORDERED_SUM_AND_EXACT_ORDER_STATISTICS',
                                     'new_numeric_condition': 'PYTHON_INT_TP_GE_FROZEN_REFERENCE', 'memory': 'O_N_PLUS_T_NO_N_BY_T_MATRIX'},
    'authorization-firewall': {'external_trusted_receipt_required': True, 'authorization_minting': False,
                               'scope': 'PROCESS_API_BOUNDARY_NOT_PROTECTION_AGAINST_ARBITRARY_IN_PROCESS_CODE'},
    'model-reuse-executor': {'strategy': 'REUSE_BYTE_IDENTICAL_V1_FITTED_MODELS', 'stage2_train_population': 'ALL_TRAIN'},
    'reference-tp-validation': {'guard': 'PYTHON_INT_20_TIMES_REFERENCE_TP_STRICTLY_GREATER_THAN_P', 'references_recomputed': False},
    'development-executor-validation': {'durable_complete_threshold_receipt_required': True, 'validation_population': 'SYNTHETIC_ONLY'},
    'rollout-executor-validation': {'horizons': [25, 50, 100, 200], 'future_truth': 'SCORING_ONLY', 'validation_population': 'SYNTHETIC_ONLY'},
    'gate-selection-binding': {'gate_clauses_per_fold': 32, 'both_folds_required': True, 'policies': 'UNCHANGED_V1'},
    'storage-implementation': {'output': 'EXPLICIT_D_ROOT_ONLY', 'compression': io.COMPRESSION, 'duplicate_v1_payload': False},
    'repeatability-implementation': {'runs': 2, 'independent_recalculation': True, 'comparison': 'BYTE_EXACT', 'scratch_deletion_this_increment': False},
    'resume-implementation': {'source_following': False, 'recompute': 0, 'trusted_identities_checked_before_member_hashing': True},
  }
  pack = io.contracts()
  return {name: p.seal({'schema': 'HURDLE_STAGE1_V3_EXECUTOR_IMPLEMENTATION_EVIDENCE', 'component': name,
                        'baseline': 'c7514cbea0f87a21acae15593e63c4af70f59dee', 'policy_receipts': pack['receipts'],
                        'executor_sources': io.sources(), 'states': list(states), 'validation_counts': counts,
                        'actual_private_access_count': 0, 'v3_private_execution': 'NOT_RUN',
                        'v3_threshold_or_state_parameter_selection': 'NOT_RUN', 'actual_v3_threshold': 'NOT_COMPUTED',
                        'v3_development': 'NOT_RUN', 'v3_rollout': 'NOT_RUN', 'v3_model_selection': 'NOT_RUN',
                        'historical_states_preserved': ['S2_RI_NO_ADMISSIBLE_CANDIDATE', 'HURDLE_NO_ADMISSIBLE_CANDIDATE',
                                                       'HURDLE_STAGE1_V2_NO_ADMISSIBLE_CANDIDATE', 'MODEL_SELECTION_FAILED_CLOSED',
                                                       'STAGE2_LONG_HORIZON_RESIDUAL_RISK_REMAINS', 'NO_MODEL_ADMITTED_FOR_FUTURE_HOLDOUT',
                                                       'FINAL_POOLED_REFIT_NOT_AUTHORIZED', 'SEARCH_NOT_AUTHORIZED', 'COMPOSITION_NOT_AUTHORIZED'],
                        'holdout': 'CLOSED', 'opening_count': 0, 'holdout_discovery': 0, 'vehicle_authority': 'NONE',
                        **details.get(name, {})}) for name in names}
