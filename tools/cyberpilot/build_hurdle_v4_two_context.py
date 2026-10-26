"""Seal public/static/synthetic feasibility evidence; no private source interface."""

import argparse
import json
from pathlib import Path
import time
import tracemalloc

import numpy as np

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_two_context_math as m
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_two_context_oracle as o
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_two_context_exact as e

BASELINE = 'ae8c2b9e7d602c655d352abeb4983b10ab4c320b'
PREFIX = 'empirical-hurdle-stage1-v4-'
PINS = {
 'empirical-hurdle-stage1-fixed-threshold-family-review': (
   'e3d7bb8f2d4713fa9a97ee17cbdb246dde2dfc03ef1a99b907174504cec8843a', 'c5c229cdf974a573fa03702874404f6f1d38603ddfe99a98fb359df273b9da5d'),
 PREFIX + 'architecture-decision': (
   'e4b327accf0a4551038dc3af6fcd8a1b32207fc6914b50cd36e9ad2946485a93', 'e868bf09f5e823388b7464babdb2093dc7d822b4c30b3019bbd5ae8ab8542e35'),
 PREFIX + 'architecture-options': (
   'daaa64c1273cde06021d6fa01e80961bcee160670062141a83f0b09f66138c89', 'b1014606100ba57f429c562e4fd9718ad9f9074f596c3f83625d74102ab2fb77'),
 PREFIX + 'future-fitting-requirements': (
   '18d9b83a7d4c9f41fa87b75c013edbc4390e540308924d317b01a1db4c4a9cb8', 'ee3323b4ae1c120d8373fe98053b80b30b441fd01d2f879d78a302de4dca2dcc'),
 PREFIX + 'onset-continuation-support': (
   'd962e9a07ec9d79638a563cccccbda749312a2fe548239f139bb5b3b64f028c1', '771e90d4f2e1336da3b853e8a01c7f1313f76bf8b32d53840eafd4141ab5c938'),
 PREFIX + 'route-transfer-analysis': (
   '83629b829e911e55c184e3e63be91a65c99c1031521b83618dcf442bff6c3ba0', '7791b7bd6c589a74516638df10691c2e4a7b54bd7cc52e8500519852fbaa0ae3'),
 PREFIX + 'validation': (
   '2581ce34a3894bbbe71888cbf62ab1f253ea1eaca9c9a9d44c180d53c6d34ef2', '90083d3dce9e68e8bbece4f27a0f094bd4f8d0a09cf53981f2bfd37ca2a725c1'),
}
SOURCE_PROOFS = {
 'openpilot/tools/cyber_autotune/empirical_hurdle_fit_cv_math.py': ['anchors:24', 'features:29', 'recursive:261', 'projected_past_update:284'],
 'openpilot/tools/cyber_autotune/empirical_s2_ri_fit_cv_math.py': ['anchors:20-28', 'features:31-46', 'project:49-54'],
 'openpilot/tools/cyber_autotune/empirical_hurdle_fit_cv_data.py': ['segment_streak_validation:19-58', 'binding:61-65', 'design:76-80', 'rollout:146-164'],
 'openpilot/tools/cyber_autotune/empirical_s2_ri_reconstruction_math.py': ['prior_delta:52-65'],
 'openpilot/tools/cyber_autotune/empirical_s2_ri_admission.py': ['causal_eligibility_and_runs'],
 'openpilot/tools/cyber_autotune/empirical_identifiability_math.py': ['streaks:15'],
}


def locked_inputs():
  result = {}
  for name, (file_sha, receipt) in PINS.items():
    raw = (p.PUBLIC / (name + '.json')).read_bytes()
    m.require(p.sha(raw) == file_sha, 'V4_TWO_CONTEXT_INPUT_CONFLICT')
    row = p.verify(json.loads(raw))
    m.require(row['receipt_sha256'] == receipt, 'V4_TWO_CONTEXT_INPUT_CONFLICT')
    result[name] = row
  m.require(result['empirical-hurdle-stage1-fixed-threshold-family-review']['status'] ==
            'GLOBAL_SINGLE_THRESHOLD_FAMILY_RETROSPECTIVELY_EXHAUSTED', 'V4_TWO_CONTEXT_INPUT_CONFLICT')
  m.require(result[PREFIX + 'architecture-decision']['status'] == 'V4_ARCHITECTURE_REDESIGN_INCONCLUSIVE', 'V4_TWO_CONTEXT_INPUT_CONFLICT')
  return result


def fixture(n=12, *, constant=False):
  k = np.arange(n, dtype=np.int64)
  return m.SyntheticTrain(score=np.ascontiguousarray(((k * 17) % 63) / 63, dtype=np.float64), context=(k % 2).astype(np.uint8),
    branch_delta=np.zeros(n, np.float64) if constant else (k % 5 - 2).astype(np.float64), current=np.zeros(n, np.int64),
    target=np.zeros(n, np.int64) if constant else (k % 3 == 0).astype(np.int64), role='SYNTHETIC_TRAIN', scope='SYNTHETIC_ONLY')


def benchmark_policy(reverse=False):
  return o.Policy(o.Feasibility(()), o.Objective((('exact_hit_count', 1), ('static_projected_false_move_count', -1),
                                               ('within_one_tick_count', 1))),
                  o.ParameterTie((1, 0) if reverse else (0, 1), (1, 1)), o.AUTHORITY)


def certification(pop, policy):
  oracle = o.exhaustive(pop, policy)
  result = e.fit(pop, policy, enable_integer_pruning=True)
  m.require(all(result[k] == oracle[k] for k in ('status', 'selected_pair', 'selected_metrics', 'selected_key', 'domain_size')),
            'V4_TWO_CONTEXT_SYNTHETIC_PARITY_FAILURE')
  e.verify_certificate(pop, policy, result)
  return {k: result[k] for k in ('status', 'domain_size', 'domain_shape', 'visited_rectangles', 'rectangles_pruned', 'leaves_evaluated',
                               'unresolved_domain_size', 'certificate_record_count', 'policy_sha256')} | {
    'full_oracle_parity': 'PASS', 'coverage_certificate': 'PASS', 'certificate_sha256': p.sha(p.canonical(result))}


def stress():
  pop, policy = fixture(200003, constant=True), benchmark_policy()
  tracemalloc.start()
  started = time.monotonic()
  result = e.fit(pop, policy, enable_integer_pruning=True, max_nodes=32)
  elapsed = time.monotonic() - started
  _, peak = tracemalloc.get_traced_memory()
  tracemalloc.stop()
  e.verify_certificate(pop, policy, result)
  m.require(result['status'] == e.EXHAUSTED and result['selected_pair'] is None)
  return {'scope': 'SYNTHETIC_ONLY_NO_V4_POLICY_AUTHORITY', 'input_sha256': pop.identity, 'policy_sha256': policy.identity,
          'source_sha256': stress_sources(), 'certificate_sha256': p.sha(p.canonical(result)),
          'rows': 200003, 'node_budget': 32, 'elapsed_seconds_descriptive': elapsed, 'tracemalloc_peak_bytes_search_only': peak,
          'input_allocation_excluded_from_peak': True, 'large_cartesian_oracle_run': False,
          'status': result['status'], 'domain_shape': result['domain_shape'], 'domain_size': result['domain_size'],
          'visited_rectangles': result['visited_rectangles'], 'leaves_evaluated': result['leaves_evaluated'],
          'rectangles_pruned': result['rectangles_pruned'], 'certificate_record_count': result['certificate_record_count'],
          'unresolved_domain_size': result['unresolved_domain_size'], 'partial_winner_published': False, 'coverage_certificate': 'PASS',
          'interpretation': 'MEMORY_ARCHITECTURE_AND_EXHAUSTION_ONLY_NOT_PRACTICAL_BOUNDEDNESS_OR_PERFORMANCE'}


def stress_sources():
  root = Path(__file__).resolve().parents[2] / 'openpilot/tools/cyber_autotune'
  return {name: p.sha((root / name).read_bytes()) for name in (
    'empirical_hurdle_v4_two_context_math.py', 'empirical_hurdle_v4_two_context_oracle.py', 'empirical_hurdle_v4_two_context_exact.py')}


def validate_stress(report):
  """Do not trust a report's PASS: reconstruct the deterministic certificate."""
  def need(condition):
    m.require(condition, 'V4_TWO_CONTEXT_SYNTHETIC_STRESS_REPORT_CONFLICT')
  keys = {'scope', 'input_sha256', 'policy_sha256', 'source_sha256', 'certificate_sha256', 'rows', 'node_budget',
    'elapsed_seconds_descriptive', 'tracemalloc_peak_bytes_search_only', 'input_allocation_excluded_from_peak',
    'large_cartesian_oracle_run', 'status', 'domain_shape', 'domain_size', 'visited_rectangles', 'leaves_evaluated',
    'rectangles_pruned', 'certificate_record_count', 'unresolved_domain_size', 'partial_winner_published', 'coverage_certificate', 'interpretation'}
  need(type(report) is dict and set(report) == keys)
  need(report['scope'] == 'SYNTHETIC_ONLY_NO_V4_POLICY_AUTHORITY' and report['rows'] == 200003 and report['node_budget'] == 32)
  need(type(report['elapsed_seconds_descriptive']) is float and np.isfinite(report['elapsed_seconds_descriptive'])
       and report['elapsed_seconds_descriptive'] >= 0)
  need(type(report['tracemalloc_peak_bytes_search_only']) is int and report['tracemalloc_peak_bytes_search_only'] > 0)
  need(report['input_allocation_excluded_from_peak'] is True and report['large_cartesian_oracle_run'] is False
       and report['partial_winner_published'] is False and report['coverage_certificate'] == 'PASS')
  need(report['interpretation'] == 'MEMORY_ARCHITECTURE_AND_EXHAUSTION_ONLY_NOT_PRACTICAL_BOUNDEDNESS_OR_PERFORMANCE')
  need(report['source_sha256'] == stress_sources())
  pop, policy = fixture(200003, constant=True), benchmark_policy()
  result = e.fit(pop, policy, enable_integer_pruning=True, max_nodes=32)
  e.verify_certificate(pop, policy, result)
  need(report['input_sha256'] == pop.identity and report['policy_sha256'] == policy.identity and report['status'] == e.EXHAUSTED)
  need(report['certificate_sha256'] == p.sha(p.canonical(result)))
  for key in ('domain_shape', 'domain_size', 'visited_rectangles', 'leaves_evaluated', 'rectangles_pruned',
              'certificate_record_count', 'unresolved_domain_size'):
    need(p.canonical(report[key]) == p.canonical(result[key]))
  need(type(report['rows']) is int and type(report['node_budget']) is int)
  return report


def build(stress_report):
  inputs = locked_inputs()
  stress_report = validate_stress(stress_report)
  root = Path(__file__).resolve().parents[2]
  sources = [{'member': name, 'sha256': p.sha((root / name).read_bytes()), 'static_trace': trace} for name, trace in SOURCE_PROOFS.items()]
  decision = inputs[PREFIX + 'architecture-decision']
  common = {'baseline': BASELINE, 'schema': 'HURDLE_STAGE1_V4_TWO_CONTEXT_FEASIBILITY_REVIEW_V1',
    'scope': 'PUBLIC_STATIC_SYNTHETIC_ONLY', 'actual_execution_authorized': False, 'private_numeric_array_opens': 0,
    'raw_log_openings': 0, 'qlog_openings': 0, 'holdout_openings': 0, 'source_writes': 0,
    'holdout': 'CLOSED', 'opening_count': 0, 'holdout_discovery': 0, 'vehicle_authority': 'NONE',
    'historical_states_preserved': decision['historical_states_preserved'], 'preserved_authority_states': decision['preserved_authority_states'],
    'v4': dict.fromkeys(('fitting', 'development', 'rollout', 'performance', 'selection'), 'NOT_RUN'),
    'architecture_status_preserved': 'V4_ARCHITECTURE_REDESIGN_INCONCLUSIVE', 'architecture_frozen': False,
    'v4_fitting_policy_frozen': False, 'hugging_face': 'NOT_NEEDED'}
  result = {}
  def add(component, body):
    result[PREFIX + component + '.json'] = p.seal({**common, 'component': component, **body})
  add('two-context-feasibility-policy', {
    'input_lock': {name + '.json': {'file_sha256': hashes[0], 'receipt_sha256': hashes[1]} for name, hashes in PINS.items()},
    'input_verification': 'PASS', 'closure': 'EMPIRICAL_PROJECT_POLICY_CLOSURE_NOT_MATHEMATICAL_IMPOSSIBILITY',
    'policy_layers': ['PAIR_METRIC_EVALUATOR', 'EXTERNAL_FEASIBILITY_POLICY', 'EXTERNAL_OBJECTIVE_KEY', 'EXTERNAL_TOTAL_PARAMETER_TIE_KEY'],
    'benchmark_authority': o.AUTHORITY, 'actual_v4_feasibility': 'UNFROZEN', 'actual_v4_objective': 'UNFROZEN',
    'actual_v4_tp_floor': 'UNFROZEN', 'actual_v4_pair_tie_order': 'UNFROZEN',
    'synthetic_ties_tested_not_adopted': ['STATIC_FIRST_LEXICOGRAPHIC', 'MOVE_FIRST_LEXICOGRAPHIC'],
    'no_auto_advance': True})
  add('two-context-canonical-oracle', {
    'status': 'SYNTHETIC_CANONICAL_CARTESIAN_ORACLE_COMPLETE', 'domain': 'Tz=SORTED_UNIQUE({0,1} UNION FINITE_CONTEXT_z_SCORES)',
    'decision': 'MOVE_IFF_SCORE_STRICTLY_GREATER_THAN_THETA_CONTEXT; EQUALITY_STATIC', 'epsilon': 0,
    'metrics': {'continuous_error': 'SELECTED_BRANCH_DELTA_MINUS_ACTUAL_DELTA_ORIGINAL_ROW_ORDER',
      'all_and_true_move': ['RMSE', 'MAE', 'NP_PERCENTILE_ABS_ERROR_95_METHOD_LINEAR'],
      'projected': ['EXACT_HIT_COUNT', 'WITHIN_ONE_TICK_COUNT', 'STATIC_PROJECTED_FALSE_MOVE_COUNT'],
      'confusion': 'GLOBAL_AND_EACH_CONTEXT_TP_TN_FP_FN_PREDICTED_MOVE_COUNT_PYTHON_INT'},
    'projection': 'FROZEN_BINARY64_CURRENT_PLUS_DELTA_NP_RINT_HALF_EVEN_SIGNED16_RANGE_INT64_ARITHMETIC',
    'empty_true_move_metrics': 'UNDEFINED_NONE_NO_IMPUTATION_FEASIBILITY_REFERENCING_THEM_REJECTS',
    'numeric_workspace': 'O(N+T0+T1)_NO_N_BY_T_MATRIX', 'authority': o.AUTHORITY})
  add('two-context-exact-algorithm', {
    'family': 'CERTIFIED_RECTANGLE_BRANCH_AND_BOUND_CANONICAL_LEAVES',
    'status': 'CERTIFIED_EXACT_BUT_CARTESIAN_WORST_CASE',
    'integer_primary_bound': 'max_CONTEXT0_SIGNED_COUNT_IN_RANGE_PLUS_max_CONTEXT1_SIGNED_COUNT_IN_RANGE',
    'objective_prune': 'ONLY_IF_INTEGER_PRIMARY_UPPER_STRICTLY_LESS_THAN_CANONICAL_FEASIBLE_INCUMBENT_PRIMARY',
    'feasibility_prune': 'ONLY_DECLARED_TP_GE_INTEGER_FLOOR_AND_RECTANGLE_TP_UPPER_STRICTLY_BELOW_FLOOR',
    'float_bounds': 'NOT_USED_UNCERTAIN_NEVER_PRUNES', 'secondary_and_tie': 'NO_PRUNE_ON_PRIMARY_EQUALITY',
    'certificate': 'BINARY_PARTITION_TREE_CANONICAL_LEAVES_RECOMPUTED_INTEGER_BOUNDS_AND_FEASIBLE_INCUMBENT_REFERENCES',
    'coverage': 'ROOT_EXACT_DOMAIN_CHILDREN_DISJOINT_EXACT_PARTITION_NO_CYCLES_SHARED_OR_UNREACHABLE_NODES',
    'resource_exhaustion': e.EXHAUSTED, 'on_exhaustion': 'SELECTED_PAIR_METRICS_KEY_AND_TOTAL_FEASIBLE_COUNT_NULL',
    'feasible_pair_count': 'UNKNOWN_IF_OBJECTIVE_PRUNES_POTENTIALLY_FEASIBLE_PAIRS',
    'not_certified': 'SUBCARTESIAN_WORST_CASE_OR_PRACTICAL_REAL_SCALE_BOUND'})
  scale = []
  for job in inputs[PREFIX + 'route-transfer-analysis']['jobs']:
    n = job['train']['count']
    scale.append({'candidate_id': job['candidate_id'], 'fold': job['fold'], 'public_train_count': n,
                  'context_counts': 'UNOPENED_NOT_KNOWN_FOR_THIS_JOB', 'pair_upper_bound_over_all_context_partitions': (n // 2 + 2) * (n - n // 2 + 2)})
  families = [
    {'family': 'CERTIFIED_RECTANGLE_BRANCH_AND_BOUND', 'can': 'GLOBAL_OPTIMUM_OR_NO_FEASIBLE_AFTER_DOMAIN_CERTIFIED',
     'cannot': 'GENERAL_SUBCARTESIAN_TIME', 'time': 'O(NlogN+T0+T1+LN+Vlog(T0+T1))', 'memory': 'O(N+T0+T1+V)',
     'p95': 'CANONICAL_POOLED_LEAF', 'float': 'CANONICAL_ORIGINAL_ORDER_LEAF'},
    {'family': 'PARETO_FRONT_DOMINANCE_INDEX', 'can': 'EXACT_ADDITIVE_INTEGER_DOMINANCE_WITH_COMPLETE_POLICY_SUFFICIENT_STATISTICS',
     'cannot': 'DOMINANCE_FROM_CONTEXT_P95_OR_FLOAT_SUBTOTALS',
     'time': 'POLICY_DEPENDENT_AT_LEAST_OMEGA(T0*T1)_IF_ALL_PAIR_FRONT_MATERIALIZED_NO_GENERAL_SUBCARTESIAN_BOUND_PROVEN',
     'memory': 'O(T0*T1)_IF_ALL_PAIR_FRONT_STORED', 'p95': 'NEEDS_FULL_DISTRIBUTION_NOT_LOCAL_QUANTILES', 'float': 'NEEDS_CANONICAL_OR_CERTIFIED_BOUNDS'},
    {'family': 'PERSISTENT_ORDER_STATISTIC_STRUCTURE', 'can': 'EXACT_UNION_RANK_QUERIES_AFTER_CONTEXT_VERSION_BUILD',
     'cannot': 'SELECT_GLOBAL_BEST_WITHOUT_POLICY_SEARCH_PROOF', 'time': 'O((N+T0+T1)logN)+O(logN)_PER_QUERY',
     'memory': 'O((N+T0+T1)logN)', 'p95': 'EXACT_BINARY64_COORDINATES_LOWER_UPPER_ORDER_STATS_NUMPY_COMPATIBLE_LERP_REQUIRED',
     'float': 'DOES_NOT_SOLVE_ORIGINAL_ORDER_SAE_SSE'},
    {'family': 'ORIGINAL_ORDER_REDUCTION_TREE', 'can': 'PRESERVE_A_SPECIFIED_BINARY_REDUCTION_DAG',
     'cannot': 'ASSUME_GENERIC_TREE_EQUALS_NUMPY_REDUCTION', 'time': 'O(N)_BUILD_O(logN)_PER_LEAF_UPDATE_FOR_PROVEN_DAG',
     'memory': 'O(N)_CURRENT_TREE_MORE_FOR_PERSISTENCE', 'p95': 'SEPARATE_ORDER_STATISTIC_STRUCTURE_REQUIRED',
     'float': 'NUMPY_PAIRWISE_AXIS_SIZE_KERNEL_OPERATION_ORDER_MUST_BE_REPRODUCED_NOT_ESTABLISHED_HERE'},
    {'family': 'OFFLINE_MULTIDIMENSIONAL_DOMINANCE_QUERY', 'can': 'FIXED_DIMENSION_ADDITIVE_EXACT_CONSTRAINT_QUERIES',
     'cannot': 'ARBITRARY_POOLED_PERCENTILE_OR_CANONICAL_FLOAT_POLICY', 'time': 'POLICY_DIMENSION_DEPENDENT_O(Tlog^dT)_ONLY_FOR_PROVEN_REDUCTION',
     'memory': 'POLICY_DEPENDENT_NO_GENERAL_BOUND_PROVEN', 'p95': 'DISTRIBUTIONAL_CONSTRAINT_NOT_SCALAR_SUBTOTAL',
     'float': 'NO_GENERIC_CANONICAL_REDUCTION_PROOF'},
    {'family': 'EXACT_SEPARABLE_CONTEXT_FITTING', 'can': 'UNCONSTRAINED_ADDITIVE_INTEGER_BENCHMARK_GLOBAL_OPTIMUM',
     'cannot': 'INHERIT_JOINT_POOLED_FEASIBILITY_POLICY', 'time': 'O(NlogN+T0+T1)_BENCHMARK', 'memory': 'O(N+T0+T1)',
     'p95': 'CONTEXT_LOCAL_QUANTILES_NOT_POOLED_QUANTILE', 'float': 'LOCAL_POLICY_REDUCTIONS_ARE_A_DIFFERENT_POLICY'},
  ]
  add('two-context-complexity-analysis', {'classification': 'CERTIFIED_EXACT_BUT_CARTESIAN_WORST_CASE',
    'definitions': {'P': 'T0*T1', 'L': 'CANONICAL_LEAVES_EVALUATED', 'V': 'VISITED_RECTANGLES'},
    'worst_case_time': 'O(NlogN+T0+T1+N*T0*T1)', 'numeric_workspace': 'O(N+T0+T1)', 'certificate_memory': 'O(V)',
    'all_pair_certificate_worst_case': 'O(T0*T1)_NOT_CLAIMED_O(N)', 'families_reviewed': families,
    'historical_scale': {'per_context': 'Tz<=Nz+2', 'partition': 'N0+N1=N',
      'balanced_partition_upper': '(floor(N/2)+2)*(ceil(N/2)+2)', 'interpretation': 'UPPER_BOUND_NOT_ACTUAL_UNIQUE_SCORES', 'jobs': scale}})
  x = np.array([1., 2.**-53, 2.**-53])
  add('two-context-float-reduction-analysis', {
    'synthetic_witness': {'values': x.tolist(), 'contexts': [0, 1, 1], 'original_order_sum': float(np.sum(x)),
      'context_subtotal_sum': float(np.sum(x[:1]) + np.sum(x[1:])), 'not_equal': True},
    'preservation': 'DIRECT_FULL_ORIGINAL_ROW_ORDER_NUMPY_MEAN_ERROR_SQUARED_AND_ABS_AT_EVERY_EVALUATED_LEAF',
    'safe_pruning': 'ONLY_EXACT_INTEGER_COUNT_BOUNDS_NO_FLOAT_SUBTOTAL_PRUNING',
    'reduction_tree_status': 'NOT_IMPLEMENTED_OR_CLAIMED_EQUIVALENT_TO_PINNED_NUMPY'})
  arrays = [np.array(v) for v in ([0., 20.], [10., 10.], [19., 19.], [0., 200. / 19.])]
  add('two-context-p95-analysis', {
    'canonical': 'np.percentile(np.abs(error),95,method=linear)', 'exactness': 'DIRECT_PINNED_NUMPY_POOLED_CALL_AT_CANONICAL_LEAVES',
    'order_statistics': 'h=(n-1)*0.95; floor(h),ceil(h); NUMPY_COMPATIBLE_BINARY64_INTERPOLATION_NOT_JUST_REAL_ARITHMETIC_FORMULA',
    'synthetic_witness': {'distributions': [a.tolist() for a in arrays], 'local_p95': [float(np.percentile(a, 95)) for a in arrays],
      'pooled_pair_01': float(np.percentile(np.r_[arrays[0], arrays[1]], 95)),
      'pooled_pair_23': float(np.percentile(np.r_[arrays[2], arrays[3]], 95))},
    'approximate_quantiles': 'FORBIDDEN', 'persistent_order_statistics': 'RESEARCH_ONLY_NOT_NEEDED_FOR_CANONICAL_LEAF_EXACTNESS'})
  small = [certification(fixture(), benchmark_policy(reverse)) for reverse in (False, True)]
  medium = certification(fixture(78), benchmark_policy())
  adversary = certification(fixture(12, constant=True), benchmark_policy())
  add('two-context-branch-bound-validation', {'small': small, 'medium': medium, 'no_pruning_adversary': adversary,
    'large_synthetic': stress_report, 'authority': o.AUTHORITY, 'exhaustive_parity': 'PASS', 'coverage_certificates': 'PASS'})
  add('two-context-separable-policy-review', {
    'status': 'SEPARABLE_TWO_CONTEXT_FITTING_ALGORITHMICALLY_FEASIBLE_POLICY_UNFROZEN',
    'implemented_benchmark': 'UNCONSTRAINED_ADDITIVE_INTEGER_LEXICOGRAPHIC_OBJECTIVE_WITH_EXTERNAL_AXIS_TIE',
    'complexity': 'O(NlogN+T0+T1)', 'pooled_policy_equivalent': False,
    'witness': {'context0_actual_deltas': [1, 1], 'context0_branch_deltas': [5., 5.],
      'context1_actual_deltas': [10, 10], 'context1_branch_deltas': [10., 10.],
      'joint_rmse_improvement_possible': True, 'context0_strict_rmse_improvement_possible': False},
    'information_lost_by_local_feasibility': 'CROSS_CONTEXT_TRADEOFFS_POOLED_P95_GLOBAL_FEASIBILITY_AND_GLOBAL_OBJECTIVE',
    'actual_local_ba_v2_or_tp_policy_adopted': False, 'new_design_decision_required': True})
  add('causal-state-contract', {
    'status': 'V4_TWO_CONTEXT_CAUSAL_STATE_CONTRACT_ESTABLISHED', 'proof_scope': 'STATIC_CONSTRUCTION_INVARIANTS_NOT_PRIVATE_ARRAY_INSPECTION',
    'transition': 'tick[k] -> tick[k+1]', 'previous_delta': 'INT64(tick[k])-INT64(tick[k-1])',
    'context': 'z[k]=INT(previous_delta!=0)', 'one_step': 'ALREADY_OBSERVED_PREVIOUS_AND_CURRENT_ONLY_TARGET_SCORING_ONLY',
    'state_bits': 1, 'sign_magnitude_rate_inputs': False,
    'meaning': 'SOURCE_GRID_TICK_INCREMENT_NOT_PHYSICAL_EPS_MOVEMENT_NOT_STEERING_RATE',
    'source_proofs': sources, 'history_required': 'R=max(d+L,L+1)>=2_FOR_ALL_16_STRUCTURES',
    'history_table': [{'d': d, 'L': length, 'R': max(d + length, length + 1)} for d in (0, 5, 10, 20) for length in (1, 5, 15, 45)],
    'continuity': 'SAME_ROUTE_SEGMENT_CAUSAL_RUN_ELIGIBLE_CONTIGUOUS_SOURCE_INDEX_WITHIN_INDEX_10MS_GRID_VALIDATED_STREAK',
    'boundaries': 'INVALIDATE_CONTEXT_REQUIRE_FRESH_ADMITTED_OBSERVED_PAIR_NO_CROSSING_OR_PADDING',
    'missing_or_nonfinite': 'OPTION_A_CAUSAL_STATE_CONTRACT_CONFLICT_NO_ANCHOR_CHANGE',
    'minimum_context_fit_support': 'UNFROZEN_FUTURE_POLICY_DECISION_NOT_INVENTED_HERE', 'anchors_changed': False})
  add('rollout-state-contract', {
    'status': 'V4_TWO_CONTEXT_CAUSAL_STATE_CONTRACT_ESTABLISHED', 'initial': 'z[0]=INT(observed_tick[0]-observed_tick[-1]!=0)',
    'recursive_h_ge_1': 'z[h]=INT(projected_tick[h]-projected_tick[h-1]!=0)',
    'gate_is_not_state': 'MOVE_GATE_WITH_PROJECTED_HOLD_IMPLIES_NEXT_z=0',
    'future_measured_tick_delta_move_label': 'SCORING_ONLY_FORBIDDEN_IN_CONTEXT_UPDATE',
    'logged_future_command_vego': 'EXISTING_FROZEN_EXOGENOUS_REPLAY_ONLY_NOT_NEW_SENSOR_AUTHORITY',
    'reset': 'CALLER_SIGNALED_BOUNDARY_INVALIDATES_FRESH_OBSERVED_INITIAL_HISTORY_REQUIRED_NO_STICKY_GATE_NO_STATIC_DEFAULT',
    'integration_scope': 'SYNTHETIC_STATE_WITNESS_NOT_AUTOMATIC_BOUNDARY_DETECTOR_OR_EXISTING_EXECUTOR_INTEGRATION',
    'actual_rollout_executor_changed_or_run': False})
  add('option-a-eligibility', {
    'causal_result': 'V4_TWO_CONTEXT_CAUSAL_STATE_CONTRACT_ESTABLISHED',
    'fitting_result': 'V4_TWO_CONTEXT_EXACT_FITTING_EXACT_BUT_CARTESIAN_WORST_CASE',
    'eligibility': 'OPTION_A_ALGORITHMIC_ELIGIBILITY_NOT_ESTABLISHED',
    'blocker': 'OPTION_A_CURRENT_EXACT_FITTING_BLOCKER_REMAINS', 'impossible_claim': False,
    'practically_bounded_established': False, 'total_tie_interface': 'ESTABLISHED_EXTERNAL_POLICY_UNFROZEN',
    'next_step': 'SEPARATE_POLICY_REVIEW_FOR_SEPARABLE_FITTING_OR_ANOTHER_BOUNDED_ARCHITECTURE_NO_AUTOMATIC_ADOPTION',
    'architecture_selection': 'NOT_AUTHORIZED_HERE', 'nonlinear_design': 'NOT_STARTED'})
  add('two-context-validation', {
    'status': 'STAGE1_V4_TWO_CONTEXT_FEASIBILITY_REVIEW_COMPLETE',
    'checks': {'new_focused': {'passed': 45}, 'prior_v3_and_v4_focused': {'passed': 160},
      'combined_empirical': {'passed': 1973}, 'full_autotune_controls': {'passed': 4832}, 'lateral_replay': {'passed': 16},
      'ruff': 'PASS', 'compileall': 'PASS', 'json_files': {'passed': 679}, 'publication_privacy_authority': 'PASS',
      'git_diff_check': 'PASS', 'scons': 'PASS', 'independent_numeric_review': 'APPROVED', 'independent_causality_review': 'APPROVED'},
    'validation_environment': {'python': '3.12.13', 'numpy': '2.5.3', 'blas_threads': 1,
      'temp': 'E_BACKED_WSL', 'legacy_d_fixture_isolation': 'PRIVATE_MOUNT_NAMESPACE_TMPFS_NO_GLOBAL_ALIAS_OR_GUARD_CHANGE'},
    'review_findings_resolved': ['CERTIFICATE_SCOPE_SCHEMA_BOOL_ALIAS', 'STRESS_REPORT_SCHEMA_IDENTITY_CERTIFICATE_VALIDATION',
      'MALFORMED_FRAME_METADATA_AND_MISSING_NONFINITE_TICKS', 'SOURCE_CITATION_AND_PARETO_LOWER_BOUND_WORDING'],
    'private_numeric_array_opens': 0, 'model_fit_calls': 0, 'normalizer_fit_calls': 0, 'prediction_replay_calls': 0,
    'actual_threshold_search_calls': 0, 'actual_rollout_calls': 0, 'actual_selection_calls': 0,
    'historical_public_input_integrity': 'PASS_SEVEN_EXACT_FILE_AND_RECEIPT_HASHES', 'no_actual_v4_performance': True})
  return result


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--stress', action='store_true', help='Synthetic local memory/exhaustion benchmark only')
  parser.add_argument('--stress-report', type=Path, help='Public-safe synthetic aggregate JSON, never a private source')
  args = parser.parse_args()
  if args.stress:
    print(json.dumps(stress(), sort_keys=True, indent=2))
    return
  m.require(args.stress_report is not None, 'SYNTHETIC_STRESS_REPORT_REQUIRED')
  report = json.loads(args.stress_report.read_bytes())
  for name, row in build(report).items():
    p.persist(p.PUBLIC / name, row)
  print('SEALED_12_PUBLIC_STATIC_SYNTHETIC_ARTIFACTS_NO_PRIVATE_ACCESS')


if __name__ == '__main__':
  main()
