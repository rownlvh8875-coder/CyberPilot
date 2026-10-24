"""Synthetic-only exact certification and causal state regression."""

import copy
import unittest
from unittest.mock import patch

import numpy as np


class TestTwoContext(unittest.TestCase):
  def population(self, scores=(.2, .8, .2, .8), contexts=(0, 0, 1, 1), delta=(0., 1., 0., 1.), target=(0, 1, 0, 1)):
    from openpilot.tools.cyber_autotune.empirical_hurdle_v4_two_context_math import SyntheticTrain
    return SyntheticTrain(score=np.array(scores, np.float64), context=np.array(contexts, np.uint8),
                          branch_delta=np.array(delta, np.float64), current=np.zeros(len(scores), np.int64),
                          target=np.array(target, np.int64), role='SYNTHETIC_TRAIN', scope='SYNTHETIC_ONLY')

  def policy(self, *, reverse=False, clauses=(), terms=(('exact_hit_count', 1),)):
    from openpilot.tools.cyber_autotune.empirical_hurdle_v4_two_context_oracle import Policy, Feasibility, Objective, ParameterTie
    return Policy(Feasibility(clauses), Objective(terms), ParameterTie((1, 0) if reverse else (0, 1), (1, 1)),
                  authority='FEASIBILITY_BENCHMARK_ONLY_NO_V4_POLICY_AUTHORITY')

  def test_strict_gate_and_half_even_projection(self):
    from openpilot.tools.cyber_autotune.empirical_hurdle_v4_two_context_math import evaluate_pair
    pop = self.population(scores=(.5, .5, 1., 0.), contexts=(0, 1, 0, 1), delta=(.5, 1.5, 2.5, 3.), target=(0, 2, 2, 0))
    row = evaluate_pair(pop, (.5, 0.))
    self.assertEqual(row['counts']['predicted_move_count'], 2)
    self.assertEqual(row['counts']['exact_hit_count'], 4)
    self.assertEqual(row['contexts'][0]['FN'], 0)

  def test_oracle_domain_and_manual_metrics(self):
    from openpilot.tools.cyber_autotune.empirical_hurdle_v4_two_context_math import evaluate_pair, threshold_sets
    from openpilot.tools.cyber_autotune.empirical_hurdle_v4_two_context_oracle import exhaustive
    pop = self.population()
    sets = threshold_sets(pop)
    self.assertEqual([len(x) for x in sets], [4, 4])
    result = exhaustive(pop, self.policy())
    self.assertEqual(result['domain_size'], 16)
    self.assertEqual(result['feasible_pair_count'], 16)
    row = evaluate_pair(pop, (.2, .2))
    self.assertEqual(row['all']['rmse'], 0.)
    self.assertEqual(row['counts']['TP'], 2)
    self.assertEqual(row['counts']['TN'], 2)

  def test_external_tie_orders_are_different_legitimate_winners(self):
    from openpilot.tools.cyber_autotune.empirical_hurdle_v4_two_context_oracle import exhaustive
    pop = self.population(scores=(.5, .5), contexts=(0, 1), delta=(.4, .4), target=(0, 0))
    clauses = (('counts.predicted_move_count', '==', 1),)
    a = exhaustive(pop, self.policy(clauses=clauses))
    b = exhaustive(pop, self.policy(reverse=True, clauses=clauses))
    self.assertEqual(a['selected_pair'], [1., 0.])
    self.assertEqual(b['selected_pair'], [0., 1.])

  def test_bound_certificate_and_no_pruning_parity(self):
    from openpilot.tools.cyber_autotune.empirical_hurdle_v4_two_context_oracle import exhaustive
    from openpilot.tools.cyber_autotune.empirical_hurdle_v4_two_context_exact import fit, verify_certificate
    pop, policy = self.population(), self.policy()
    expected = exhaustive(pop, policy)
    for prune in (False, True):
      got = fit(pop, policy, enable_integer_pruning=prune)
      self.assertEqual(got['selected_pair'], expected['selected_pair'])
      self.assertEqual(got['selected_metrics'], expected['selected_metrics'])
      self.assertTrue(verify_certificate(pop, policy, got))

  def test_exhaustion_never_returns_partial_winner(self):
    from openpilot.tools.cyber_autotune.empirical_hurdle_v4_two_context_exact import fit, verify_certificate
    pop, policy = self.population(), self.policy()
    got = fit(pop, policy, max_nodes=0)
    self.assertEqual(got['status'], 'V4_TWO_CONTEXT_FITTING_INCONCLUSIVE_RESOURCE_BOUND')
    self.assertIsNone(got['selected_pair'])
    self.assertGreater(got['unresolved_domain_size'], 0)
    self.assertTrue(verify_certificate(pop, policy, got))

  def test_rejects_private_development_holdout_roles(self):
    from openpilot.tools.cyber_autotune.empirical_hurdle_v4_two_context_math import SyntheticTrain
    for role, scope in [('DEVELOPMENT', 'SYNTHETIC_ONLY'), ('HOLDOUT', 'SYNTHETIC_ONLY'), ('SYNTHETIC_TRAIN', 'PRIVATE')]:
      with self.assertRaisesRegex(ValueError, 'SYNTHETIC_ONLY'):
        SyntheticTrain(score=np.array([.1]), context=np.array([0], np.uint8), branch_delta=np.array([0.]),
                       current=np.array([0], np.int64), target=np.array([0], np.int64), role=role, scope=scope)

  def test_context_subtotal_float_counterexample(self):
    x = np.array([1., 2.**-53, 2.**-53])
    self.assertNotEqual(float(np.sum(x)), float(np.sum(x[:1]) + np.sum(x[1:])))

  def test_pooled_percentile_counterexample(self):
    a, b, c, d = np.array([0., 20.]), np.array([10., 10.]), np.array([19., 19.]), np.array([0., 200./19.])
    self.assertEqual(np.percentile(a, 95, method='linear'), np.percentile(c, 95, method='linear'))
    self.assertEqual(np.percentile(b, 95, method='linear'), np.percentile(d, 95, method='linear'))
    self.assertNotEqual(np.percentile(np.r_[a, b], 95, method='linear'), np.percentile(np.r_[c, d], 95, method='linear'))

  def compare(self, pop, policy):
    from openpilot.tools.cyber_autotune.empirical_hurdle_v4_two_context_oracle import exhaustive
    from openpilot.tools.cyber_autotune.empirical_hurdle_v4_two_context_exact import fit, verify_certificate
    expected = exhaustive(pop, policy)
    got = fit(pop, policy, enable_integer_pruning=True)
    for field in ('status', 'selected_pair', 'selected_metrics', 'selected_key', 'domain_size'):
      self.assertEqual(got[field], expected[field])
    if got['feasible_pair_count'] is not None:
      self.assertEqual(got['feasible_pair_count'], expected['feasible_pair_count'])
    self.assertTrue(verify_certificate(pop, policy, got))
    return got

  def test_deterministic_fixture_matrix(self):
    # Endpoints, equality, empty context, rare context, interleaved/grouped order,
    # opposite context optima, all-static/all-move, repeated and signed-zero scores.
    fixtures = [
      ((0., 1.), (0, 1), (1., 1.), (1, 1)),
      ((.5,) * 4, (0, 0, 1, 1), (1.,) * 4, (0, 1, 0, 1)),
      ((.1, .2, .3, .4), (0,) * 4, (0., 1., 2., -2.), (0, 1, 2, -2)),
      ((.1, .2, .3, .4), (1,) * 4, (0., 1., 2., -2.), (0, 1, 2, -2)),
      ((.2, .8, .2, .8), (0, 1, 0, 1), (1.,) * 4, (1, 0, 1, 0)),
      ((.2, .8, .2, .8), (0, 0, 0, 1), (1.,) * 4, (0, 1, 0, 1)),
      ((-0., 0., np.nextafter(.5, 1.), .5), (0, 1, 0, 1), (.5, 1.5, -1.5, -2.5), (0, 2, -2, -2)),
      ((.1, .4, .8, .9), (0, 1, 0, 1), (.4,) * 4, (0,) * 4),
    ]
    for scores, contexts, delta, target in fixtures:
      pop = self.population(scores, contexts, delta, target)
      for reverse in (False, True):
        with self.subTest(scores=scores, reverse=reverse):
          self.compare(pop, self.policy(reverse=reverse, terms=(('exact_hit_count', 1), ('static_projected_false_move_count', -1),
                                                              ('within_one_tick_count', 1))))

  def test_integer_tables_equal_every_canonical_pair(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_two_context_math as m
    pop = self.population((0., .5, 1., .5, .2), (0, 1, 0, 1, 0), (1., -2., .4, 1.5, 2.5), (1, -2, 0, 2, 3))
    table = m.IntegerTables(pop)
    for i in range(len(table.domain[0])):
      for j in range(len(table.domain[1])):
        self.assertEqual(table.additive((i, j)), m.evaluate_pair(pop, table.pair((i, j)))['counts'])

  def test_all_range_bounds_exact(self):
    from openpilot.tools.cyber_autotune.empirical_hurdle_v4_two_context_math import RangeMaximum
    values = [9, -2, 0, 7, 3, 20, 20]
    table = RangeMaximum(values)
    for lo in range(len(values)):
      for hi in range(lo, len(values)):
        self.assertEqual(table.query(lo, hi), max(values[lo:hi + 1]))

  def test_no_feasible_and_exact_tp_boundary(self):
    for floor in (2, 3):
      pop = self.population()
      got = self.compare(pop, self.policy(clauses=(('TP', '>=', floor),)))
      self.assertEqual(got['status'], 'SYNTHETIC_EXACT_OPTIMUM_CERTIFIED' if floor == 2 else 'SYNTHETIC_NO_FEASIBLE_PAIR')
      if floor == 2:
        self.assertEqual(got['selected_metrics']['counts']['TP'], 2)

  def test_single_feasible_pair(self):
    # Both scores are 1: only (0,0) opens both gates.
    pop = self.population((1., 1.), (0, 1), (1., 1.), (1, 1))
    got = self.compare(pop, self.policy(clauses=(('TP', '>=', 2),)))
    self.assertEqual(got['feasible_pair_count'], 1)
    self.assertEqual(got['selected_pair'], [0., 0.])

  def test_no_pruning_adversary_is_cartesian(self):
    pop = self.population((.2, .4, .6, .8), (0, 1, 0, 1), (0.,) * 4, (0,) * 4)
    got = self.compare(pop, self.policy())
    self.assertEqual(got['leaves_evaluated'], got['domain_size'])
    self.assertEqual(got['rectangles_pruned'], 0)

  def test_heavy_pruning_is_certified_not_feasible_count(self):
    pop = self.population((.2, .4, .6, .8), (0, 1, 0, 1), (1.,) * 4, (1,) * 4)
    got = self.compare(pop, self.policy())
    self.assertGreater(got['rectangles_pruned'], 0)
    self.assertLess(got['leaves_evaluated'], got['domain_size'])
    self.assertIsNone(got['feasible_pair_count'])

  def test_float_primary_never_prunes_uncertain_bounds(self):
    got = self.compare(self.population(), self.policy(terms=(('all.rmse', -1),)))
    self.assertEqual(got['objective_prunes'], 0)
    self.assertEqual(got['leaves_evaluated'], got['domain_size'])

  def test_negative_integer_primary_bound(self):
    self.compare(self.population(), self.policy(terms=(('static_projected_false_move_count', -1), ('TP', 1))))

  def test_original_order_float_metrics_preserved(self):
    from openpilot.tools.cyber_autotune.empirical_hurdle_v4_two_context_math import evaluate_pair
    branch = np.array([1., 2.**-53, 2.**-53])
    pop = self.population((.5,) * 3, (0, 1, 1), tuple(branch), (0,) * 3)
    row = evaluate_pair(pop, (0., 0.))
    self.assertEqual(row['all']['mae'], float(np.mean(np.abs(branch))))
    self.assertNotEqual(row['all']['mae'], float((np.sum(branch[:1]) + np.sum(branch[1:])) / 3))
    self.compare(pop, self.policy(terms=(('all.mae', -1),)))

  def test_p95_fractional_repeated_and_adjacent_values(self):
    from openpilot.tools.cyber_autotune.empirical_hurdle_v4_two_context_math import evaluate_pair
    branch = np.array([0., 1., 1., np.nextafter(1., 2.), 2., 2., 3.])
    pop = self.population((.5,) * 7, (0, 1, 0, 1, 0, 1, 0), tuple(branch), (0,) * 7)
    self.assertEqual(evaluate_pair(pop, (0., 0.))['all']['p95'], float(np.percentile(branch, 95, method='linear')))
    self.compare(pop, self.policy(terms=(('all.p95', -1),)))

  def test_resource_exhaustion_after_incumbent_hides_winner(self):
    from openpilot.tools.cyber_autotune.empirical_hurdle_v4_two_context_exact import fit, verify_certificate, EXHAUSTED
    pop, policy = self.population(delta=(0.,) * 4, target=(0,) * 4), self.policy()
    got = fit(pop, policy, enable_integer_pruning=True, max_nodes=8)
    self.assertEqual(got['status'], EXHAUSTED)
    self.assertGreater(got['leaves_evaluated'], 0)
    for field in ('selected_pair', 'selected_metrics', 'selected_key', 'feasible_pair_count'):
      self.assertIsNone(got[field])
    self.assertTrue(verify_certificate(pop, policy, got))

  def test_certificate_mutations_rejected(self):
    from openpilot.tools.cyber_autotune.empirical_hurdle_v4_two_context_exact import fit, verify_certificate
    pop, policy = self.population(delta=(1.,) * 4, target=(1,) * 4), self.policy()
    got = fit(pop, policy, enable_integer_pruning=True)
    mutations = []
    bad = copy.deepcopy(got)
    bad['nodes'][0]['children'][0] = 0
    mutations.append(bad)
    bad = copy.deepcopy(got)
    bad['nodes'][0]['children'][1] = bad['nodes'][0]['children'][0]
    mutations.append(bad)
    bad = copy.deepcopy(got)
    bad['nodes'].append(copy.deepcopy(bad['nodes'][-1]))
    mutations.append(bad)
    bad = copy.deepcopy(got)
    bad['policy_sha256'] = '0' * 64
    mutations.append(bad)
    bad = copy.deepcopy(got)
    bad['domain_size'] += 1
    mutations.append(bad)
    bad = copy.deepcopy(got)
    next(n for n in bad['nodes'] if n['kind'] == 'PRUNE_OBJECTIVE')['bound'] -= 1
    mutations.append(bad)
    bad = copy.deepcopy(got)
    next(n for n in bad['nodes'] if n['kind'] == 'LEAF')['metrics']['counts']['TP'] += 1
    mutations.append(bad)
    for bad in mutations:
      with self.assertRaisesRegex(ValueError, 'CERTIFICATE_CONFLICT'):
        verify_certificate(pop, policy, bad)

  def test_policy_no_callbacks_mutable_clauses_or_implicit_tie(self):
    from openpilot.tools.cyber_autotune.empirical_hurdle_v4_two_context_oracle import Feasibility, Objective, ParameterTie, Policy
    for constructor, args in [(Feasibility, ([],)), (Objective, ([('TP', 1)],)), (ParameterTie, ((0, 0), (1, 1))),
                              (Feasibility, ((('DEVELOPMENT.score', '>', 0),),))]:
      with self.assertRaises(ValueError):
        constructor(*args)
    with self.assertRaises(TypeError):
      Policy(Feasibility(()), Objective((('TP', 1),)))

  def test_certificate_scope_extra_fields_and_bool_alias_rejected(self):
    from openpilot.tools.cyber_autotune.empirical_hurdle_v4_two_context_exact import fit, verify_certificate
    pop, policy = self.population((.5,), (0,), (1.,), (1,)), self.policy()
    got = fit(pop, policy)
    bad_rows = []
    bad = copy.deepcopy(got)
    bad['scope'] = 'ACTUAL_V4'
    bad_rows.append(bad)
    bad = copy.deepcopy(got)
    del bad['scope']
    bad_rows.append(bad)
    bad = copy.deepcopy(got)
    bad['actual_execution_authorized'] = True
    bad_rows.append(bad)
    bad = copy.deepcopy(got)
    bad['selected_metrics']['counts']['exact_hit_count'] = True
    bad_rows.append(bad)
    for bad in bad_rows:
      with self.assertRaisesRegex(ValueError, 'CERTIFICATE_CONFLICT'):
        verify_certificate(pop, policy, bad)

  def test_synthetic_authority_only(self):
    from openpilot.tools.cyber_autotune.empirical_hurdle_v4_two_context_oracle import Policy
    a = self.policy()
    with self.assertRaisesRegex(ValueError, 'NO_V4_POLICY_AUTHORITY'):
      Policy(a.feasibility, a.objective, a.tie, authority='ACTUAL_V4')

  def test_input_mutation_rejected(self):
    pop = self.population()
    pop.score.setflags(write=True)
    pop.score[0] = .7
    with self.assertRaises(ValueError):
      pop.verify()

  def test_invalid_scores_ticks_projection_rejected(self):
    for scores, delta, target in [((np.nan, .5), (0., 0.), (0, 0)), ((-.1, .5), (0., 0.), (0, 0)),
                                   ((.1, .5), (40000., 0.), (0, 0)), ((.1, .5), (0., 0.), (40000, 0))]:
      with self.assertRaises(ValueError):
        self.population(scores, (0, 1), delta, target)

  def test_tick_subtraction_widens_before_arithmetic(self):
    from openpilot.tools.cyber_autotune.empirical_hurdle_v4_two_context_math import SyntheticTrain, evaluate_pair
    pop = SyntheticTrain(score=np.array([0.]), context=np.array([0], np.uint8), branch_delta=np.array([0.]),
                         current=np.array([-32768], np.int64), target=np.array([32767], np.int64),
                         role='SYNTHETIC_TRAIN', scope='SYNTHETIC_ONLY')
    self.assertEqual(evaluate_pair(pop, (1., 1.))['all']['mae'], 65535.)

  def test_separable_additive_integer_benchmark_exact(self):
    from openpilot.tools.cyber_autotune.empirical_hurdle_v4_two_context_oracle import exhaustive, separable_integer_benchmark
    for reverse in (False, True):
      pop, policy = self.population(), self.policy(reverse=reverse, terms=(('exact_hit_count', 1), ('TP', 1)))
      a, b = exhaustive(pop, policy), separable_integer_benchmark(pop, policy)
      self.assertEqual(a['selected_pair'], b['selected_pair'])
      self.assertEqual(a['selected_metrics'], b['selected_metrics'])

  def test_separable_constraints_are_different_policy(self):
    from openpilot.tools.cyber_autotune.empirical_hurdle_v4_two_context_oracle import exhaustive, separable_integer_benchmark
    clauses = (('all.rmse', '<', 'hold_all.rmse'), ('move.mae', '<=', 'hold_move.mae'), ('move.p95', '<=', 'hold_move.p95'))
    pop = self.population((.5,) * 4, (0, 0, 1, 1), (5., 5., 10., 10.), (1, 1, 10, 10))
    self.assertIsNotNone(exhaustive(pop, self.policy(clauses=clauses))['selected_pair'])
    local = self.population((.5, .5), (0, 0), (5., 5.), (1, 1))
    self.assertIsNone(exhaustive(local, self.policy(clauses=clauses))['selected_pair'])
    with self.assertRaisesRegex(ValueError, 'SEPARABLE_BENCHMARK'):
      separable_integer_benchmark(pop, self.policy(clauses=clauses))

  def test_medium_exhaustive_certification(self):
    n = 78
    scores = tuple(((i * 17) % 41) / 41 for i in range(n))
    pop = self.population(scores, tuple(i % 2 for i in range(n)), tuple(float(i % 5 - 2) for i in range(n)),
                          tuple(1 if i % 3 == 0 else 0 for i in range(n)))
    self.compare(pop, self.policy(clauses=(('TP', '>=', 3), ('all.p95', '<=', 'hold_all.p95'))))

  def test_bounded_certificate_stress_no_matrix(self):
    from openpilot.tools.cyber_autotune.empirical_hurdle_v4_two_context_exact import fit, verify_certificate
    n = 3001
    pop = self.population(tuple((i % 63) / 63 for i in range(n)), tuple(i % 2 for i in range(n)), (0.,) * n, (0,) * n)
    policy = self.policy()
    got = fit(pop, policy, enable_integer_pruning=True, max_nodes=32)
    self.assertIsNone(got['selected_pair'])
    self.assertLessEqual(got['certificate_record_count'], 65)
    self.assertTrue(verify_certificate(pop, policy, got))

  def test_no_source_prediction_fitting_or_rollout_calls(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_fit_cv_math as old
    with patch.object(old, 'recursive', side_effect=AssertionError('rollout')), \
         patch.object(old, 'normalizer', side_effect=AssertionError('normalizer')), \
         patch.object(old, 'threshold', side_effect=AssertionError('threshold')), \
         patch('numpy.load', side_effect=AssertionError('private loader')), \
         patch.object(old, 'probability', side_effect=AssertionError('predictor')), \
         patch('numpy.linalg.solve', side_effect=AssertionError('fit')), \
         patch('numpy.linalg.lstsq', side_effect=AssertionError('fit')):
      self.compare(self.population(), self.policy())


class TestCausalState(unittest.TestCase):
  def frames(self):
    from openpilot.tools.cyber_autotune.empirical_hurdle_v4_state_contract import Frame
    return Frame('R', 'S', 'RUN', 4, 4, 40_000_000, True, 5), Frame('R', 'S', 'RUN', 5, 5, 50_000_000, True, 6)

  def state(self, previous_tick=0, current_tick=0):
    from openpilot.tools.cyber_autotune.empirical_hurdle_v4_state_contract import ProjectedContext
    previous, current = self.frames()
    return ProjectedContext(previous=previous, current=current, previous_tick=previous_tick, current_tick=current_tick, scope='SYNTHETIC_ONLY')

  def test_initial_observed_move_static(self):
    self.assertEqual(self.state().context(), 0)
    self.assertEqual(self.state(previous_tick=-1).context(), 1)

  def test_gate_move_can_project_hold(self):
    from openpilot.tools.cyber_autotune.empirical_s2_ri_fit_cv_math import project
    state = self.state(previous_tick=-1)
    projected = int(project(np.array([0. + .5]))[0])  # MOVE branch, half-even holds zero.
    self.assertEqual(state.advance(projected_tick=projected, provenance='PROJECTED_INFERENCE'), 0)

  def test_projected_alternating_and_stationary_state(self):
    state = self.state()
    bits = [state.advance(projected_tick=t, provenance='PROJECTED_INFERENCE') for t in (1, 1, 0, 0, 0, -1)]
    self.assertEqual(bits, [1, 0, 1, 0, 0, 1])

  def test_future_observed_feedback_rejected(self):
    for provenance in ('FUTURE_MEASURED', 'TRUE_MOVE_LABEL', 'PREDICTED_GATE', 'OBSERVED_AFTER_ANCHOR'):
      with self.assertRaisesRegex(ValueError, 'CAUSAL_STATE'):
        self.state().advance(projected_tick=1, provenance=provenance)
    with self.assertRaises(TypeError):
      self.state().advance(projected_tick=1, provenance='PROJECTED_INFERENCE', future_truth=1)

  def test_boundaries_invalidate_no_static_padding(self):
    for boundary in ('ROUTE', 'SEGMENT', 'CAUSAL_RUN', 'ELIGIBILITY', 'GRID'):
      state = self.state(previous_tick=-1)
      state.boundary(boundary)
      self.assertIsNone(state.bit)
      with self.assertRaises(ValueError):
        state.context()
      with self.assertRaises(ValueError):
        state.advance(projected_tick=1, provenance='PROJECTED_INFERENCE')
      self.assertEqual(self.state().context(), 0)  # Fresh observed initialization only.

  def test_predecessor_continuity_required(self):
    from dataclasses import replace
    from openpilot.tools.cyber_autotune.empirical_hurdle_v4_state_contract import observed_context
    previous, current = self.frames()
    for change in ({'route': 'OTHER'}, {'segment': 'OTHER'}, {'causal_run': 'OTHER'}, {'index': 7}, {'within_index': 7},
                   {'grid_ns': 70_000_000}, {'eligible': False}, {'streak': 1}):
      with self.assertRaises(ValueError):
        observed_context(previous=previous, current=replace(current, **change), previous_tick=0, current_tick=1, scope='SYNTHETIC_ONLY')
    with self.assertRaises(ValueError):
      observed_context(previous=None, current=current, previous_tick=0, current_tick=1, scope='SYNTHETIC_ONLY')

  def test_all_frozen_history_lengths_have_predecessor(self):
    from openpilot.tools.cyber_autotune.empirical_s2_ri_fit_cv_math import anchors
    for d in (0, 5, 10, 20):
      for length in (1, 5, 15, 45):
        required = max(d + length, length + 1)
        streak = np.arange(1, 301, dtype=np.int64)
        got = anchors({'streak': streak}, f'S2RI_D{d:02d}_L{length:02d}', 1)
        self.assertGreaterEqual(int(got[0]), required - 1)
        self.assertTrue((got >= 1).all())

  def test_malformed_frame_and_missing_nonfinite_tick(self):
    from dataclasses import replace
    from openpilot.tools.cyber_autotune.empirical_hurdle_v4_state_contract import observed_context
    previous, current = self.frames()
    for prior in (replace(previous, index=-1), replace(previous, within_index=-1), replace(previous, grid_ns=-1),
                  replace(previous, streak=8)):
      with self.assertRaises(ValueError):
        observed_context(previous=prior, current=current, previous_tick=0, current_tick=1, scope='SYNTHETIC_ONLY')
    for t in (None, np.nan, np.inf, True, 0.5, 32768):
      with self.assertRaises(ValueError):
        self.state(previous_tick=t)


class TestPublicFeasibility(unittest.TestCase):
  def test_stress_report_extra_private_fields_or_wrong_source_rejected(self):
    import json
    from openpilot.tools.cyber_autotune import empirical_plant_policy as p
    from tools.cyberpilot.build_hurdle_v4_two_context import validate_stress
    row = json.loads((p.PUBLIC / 'empirical-hurdle-stage1-v4-two-context-branch-bound-validation.json').read_bytes())['large_synthetic']
    for change in ({'private_path': 'FORBIDDEN'}, {'source_sha256': {}}, {'rows': 12}, {'scope': 'ACTUAL'}, {'status': 'NO_FEASIBLE'}):
      with self.assertRaisesRegex(ValueError, 'STRESS_REPORT_CONFLICT'):
        validate_stress({**row, **change})

  def test_seven_locked_historical_receipts(self):
    from tools.cyberpilot.build_hurdle_v4_two_context import locked_inputs, PINS
    self.assertEqual(len(locked_inputs()), 7)
    name = next(iter(PINS))
    with patch.dict(PINS, {name: ('0' * 64, PINS[name][1])}), self.assertRaisesRegex(ValueError, 'INPUT_CONFLICT'):
      locked_inputs()

  def test_twelve_new_artifacts_and_authority(self):
    import json
    from openpilot.tools.cyber_autotune import empirical_plant_policy as p
    from tools.cyberpilot.build_hurdle_v4_two_context import build
    report = json.loads((p.PUBLIC / 'empirical-hurdle-stage1-v4-two-context-branch-bound-validation.json').read_bytes())['large_synthetic']
    rows = build(report)
    self.assertEqual(len(rows), 12)
    for name, row in rows.items():
      self.assertEqual(p.verify(row), json.loads((p.PUBLIC / name).read_bytes()))
      self.assertEqual(row['private_numeric_array_opens'], 0)
      self.assertFalse(row['actual_execution_authorized'])
      self.assertFalse(row['architecture_frozen'])
      self.assertEqual(row['vehicle_authority'], 'NONE')
      self.assertEqual(set(row['v4'].values()), {'NOT_RUN'})

  def test_public_preserves_inconclusive_and_cartesian_result(self):
    import json
    from openpilot.tools.cyber_autotune import empirical_plant_policy as p
    r = p.verify(json.loads((p.PUBLIC / 'empirical-hurdle-stage1-v4-option-a-eligibility.json').read_bytes()))
    self.assertEqual(r['eligibility'], 'OPTION_A_ALGORITHMIC_ELIGIBILITY_NOT_ESTABLISHED')
    self.assertEqual(r['fitting_result'], 'V4_TWO_CONTEXT_EXACT_FITTING_EXACT_BUT_CARTESIAN_WORST_CASE')
    self.assertEqual(r['architecture_status_preserved'], 'V4_ARCHITECTURE_REDESIGN_INCONCLUSIVE')
    self.assertFalse(r['impossible_claim'])

  def test_new_modules_have_no_private_io_or_model_calls(self):
    import ast
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    for name in ('math', 'oracle', 'exact'):
      tree = ast.parse((root / ('empirical_hurdle_v4_two_context_' + name + '.py')).read_text())
      forbidden = {'open', 'read_bytes', 'read_text', 'load', 'probability', 'predict_delta', 'fit_stage1', 'fit_stage2', 'recursive',
                   'normalizer', 'lstsq', 'solve'}
      calls = {n.func.id if isinstance(n.func, ast.Name) else n.func.attr for n in ast.walk(tree)
               if isinstance(n, ast.Call) and isinstance(n.func, (ast.Name, ast.Attribute))}
      self.assertFalse(calls & forbidden)


if __name__ == '__main__':
  unittest.main()
