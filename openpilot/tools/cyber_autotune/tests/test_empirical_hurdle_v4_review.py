"""Design evidence and mathematical witnesses; no V4 performance executor."""

import copy
import json
import unittest
from unittest.mock import patch

import numpy as np
from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_hurdle_v3_temporal_math as temporal


class TestV4Review(unittest.TestCase):
  def artifact(self, name):
    return p.verify(json.loads((p.PUBLIC / f'{name}.json').read_bytes()))

  def test_evidence_lock_hashes_and_receipts(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_review as r
    inputs = self.artifact('empirical-hurdle-stage1-v4-architecture-inputs')
    self.assertEqual(len(r.verify_inputs(inputs)), 161)
    bad = copy.deepcopy(inputs)
    key = next(iter(bad['public_inputs']))
    bad['public_inputs'][key]['file_sha256'] = '0' * 64
    with self.assertRaisesRegex(ValueError, 'V4_ARCHITECTURE_INPUT_CONFLICT'):
      r.verify_inputs(p.seal({k: v for k, v in bad.items() if k != 'receipt_sha256'}))

  def test_family_closure_is_empirical_not_universal(self):
    x = self.artifact('empirical-hurdle-stage1-fixed-threshold-family-review')
    self.assertEqual(x['status'], 'GLOBAL_SINGLE_THRESHOLD_FAMILY_RETROSPECTIVELY_EXHAUSTED')
    self.assertFalse(x['mathematical_impossibility_claim'])
    self.assertEqual(x['family'], 'SINGLE_GLOBAL_THRESHOLD_OVER_FIXED_STAGE1_SCORE')
    self.assertEqual(len(x['policies']), 3)
    self.assertTrue(x['same_models_features_score'])

  def test_historical_results_and_denominators(self):
    x = self.artifact('empirical-hurdle-stage1-v4-architecture-inputs')['facts']
    self.assertEqual(x['v2_extreme_suppression_denominator'], 32)
    self.assertEqual(x['v3_comparable_jobs'], 31)
    self.assertEqual(x['v3_exact_hit_worsened_jobs'], 31)
    self.assertEqual(x['v3_no_feasible_jobs'], 1)
    self.assertEqual(x['v3_fold_pass_counts'], {'FOLD_A': 0, 'FOLD_B': 0})

  def test_same_32_jobs_and_v1_v2_model_receipts(self):
    old = self.artifact('empirical-hurdle-fit-cv-results-v1')['jobs']
    v2 = self.artifact('empirical-hurdle-stage1-v2-job-manifest')['jobs']
    v3 = self.artifact('empirical-hurdle-stage1-v3-job-manifest')['jobs']
    refs = self.artifact('empirical-hurdle-stage1-v3-training-policy')['references']
    self.assertEqual(len(old), 32)
    for a, b, c, ref in zip(old, v2, v3, refs, strict=True):
      self.assertEqual([(x['candidate_id'], x['fold']) for x in (a, b, c, ref)], [(a['candidate_id'], a['fold'])] * 4)
      for stage in ('stage1', 'stage2'):
        for key in ('model_receipt_sha256', 'coefficient_sha256', 'normalizer_receipt_sha256'):
          self.assertEqual(a[stage][key], b['models'][stage][key])
      self.assertEqual(ref['stage1_model_sha256'], a['stage1']['model_receipt_sha256'])
      self.assertEqual(ref['train_anchor_sha256'], a['train_anchor_sha256'])

  def test_direct_comparison_counts_are_recomputed_from_public_jobs(self):
    rows = self.artifact('empirical-hurdle-stage1-v3-v1-v2-comparison')['jobs']
    compared = [j['comparison'] for j in rows if j['comparison'].get('status') != 'V3_DECISION_UNAVAILABLE']
    self.assertEqual(len(compared), 31)
    self.assertTrue(all(j['one_step']['v3']['candidate']['exact_hit'] < j['one_step']['v2']['candidate']['exact_hit'] for j in compared))
    dev2 = self.artifact('empirical-hurdle-stage1-v2-development-results')['jobs']
    dev3 = self.artifact('empirical-hurdle-stage1-v3-development-results')['jobs']
    improved = sum(c.get('stage1_diagnostics', {}).get('missed_move_rate', 2) < b['stage1_diagnostics']['missed_move_rate']
                   for b, c in zip(dev2, dev3, strict=True))
    self.assertEqual(improved, 31)

  def test_strict_monotone_witness_including_equality(self):
    scores = np.array([0., .25, .25, .5, .75, 1.])
    for t in scores:
      for f in (lambda x: 3 * x + 2, lambda x: x * x):
        np.testing.assert_array_equal(f(scores) > f(t), scores > t)

  def test_weak_monotone_plateaus_are_upper_cuts(self):
    scores = np.array([0., .2, .4, .6, .8, 1.])
    mapped = np.array([0., 0., .5, .5, 1., 1.])
    for c in (-1., 0., .5, 1.):
      decision = mapped > c
      excluded = scores[~decision]
      cut = max(excluded) if len(excluded) else -np.inf
      np.testing.assert_array_equal(decision, scores > cut)
    # Flat mappings can REMOVE attainable cuts; they do not add state-aware ones.
    self.assertFalse(any(np.array_equal(mapped > c, scores > .4) for c in (-1., 0., .5, 1.)))

  def test_monotone_endpoint_exception_and_decreasing_map(self):
    scores = np.array([0., .5, 1.])
    self.assertFalse(any(np.array_equal(np.ones(3, bool), scores > t) for t in (0., .5, 1.)))
    self.assertFalse(any(np.array_equal(-scores > -.5, scores > t) for t in (-np.inf, 0., .5, 1.)))

  def test_state_gate_is_not_global_cut_and_calibration_can_reparameterize(self):
    scores = np.array([.4, .4])
    state = np.array([False, True])
    cuts = np.array([.6, .2])
    decision = scores > cuts[state.astype(int)]
    np.testing.assert_array_equal(decision, [False, True])
    for t in (0., .4, 1.):
      self.assertFalse(np.array_equal(scores > t, decision))
    # State-specific affine increasing calibration with one common cutoff = two cuts.
    offset = np.array([-.1, .3])[state.astype(int)]
    np.testing.assert_array_equal(scores + offset > .5, decision)

  def test_binary_state_not_affine_signed_history_duplicate(self):
    signed = np.array([-1., 0., 1.])
    binary = signed != 0
    # At -1 and +1 an affine map equal to 1 has zero slope, contradicting zero at 0.
    self.assertEqual(binary[0], binary[2])
    self.assertNotEqual(binary[0], binary[1])

  def test_onset_continuation_partition(self):
    delta = np.array([0, 1, -2, 0, -1, 3])
    prior = np.array([0, 0, 1, -2, 0, -1])
    move, previous = temporal.truth(delta, prior)
    self.assertEqual(int(np.sum(move & ~previous)), 2)
    self.assertEqual(int(np.sum(move & previous)), 2)
    self.assertEqual(int(np.sum(move)), 4)

  def test_fragments_do_not_cross_route_segment_run_or_gaps(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_review as r
    linked = np.array([False, True, False, True, True, False])
    result = r.singleton_fragments(np.array([1, 0, 1, 1, 0, 1]), linked)
    self.assertEqual(result['move_fragment_count'], 3)
    self.assertEqual(result['length_one_count'], 2)
    self.assertEqual(result['uncensored_length_one_count'], 0)
    self.assertEqual(result['boundary_censored_length_one_count'], 2)

  def test_singleton_interior_and_empty_move(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_review as r
    linked = np.array([False, True, True, True])
    self.assertEqual(r.singleton_fragments(np.array([0, 1, 0, 0]), linked)['uncensored_length_one_count'], 1)
    self.assertIsNone(r.singleton_fragments(np.zeros(4), linked)['length_one_fraction'])

  def test_previous_state_timing_and_boundary_fail_closed(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_review as r
    self.assertTrue(r.valid_prior_context(-1, 'OBSERVED_SOURCE_GRID', True))
    for lag, source, continuous in [(0, 'OBSERVED_SOURCE_GRID', True), (-1, 'FUTURE_TRUTH', True),
                                    (-1, 'PREDICTED_GATE', True), (-1, 'OBSERVED_SOURCE_GRID', False)]:
      self.assertFalse(r.valid_prior_context(lag, source, continuous))

  def test_continuity_breaks_each_identity_dimension(self):
    for key in ('anchor_route_id', 'anchor_segment_sha', 's2_ri_run_id', 'anchor_index', 'within_run_index'):
      data = {'anchor_route_id': np.zeros(3, int), 'anchor_segment_sha': np.zeros(3, int), 's2_ri_run_id': np.zeros(3, int),
              'anchor_index': np.arange(3), 'within_run_index': np.arange(3)}
      data[key][2] += 2
      np.testing.assert_array_equal(temporal.continuity(data), [False, True, False])

  def test_grouped_positive_sse_changes_frozen_float_reduction(self):
    squared = np.array([1e16, 1., 1.])
    self.assertNotEqual(np.sum(squared), np.sum(squared[:1]) + np.sum(squared[1:]))

  def test_per_state_p95_does_not_determine_pooled_p95(self):
    # Same per-state percentile and support; different pooled percentile.
    a, b = np.array([0., 20.]), np.array([10., 10.])
    c, d = np.array([19., 19.]), np.array([0., 200. / 19.])
    self.assertEqual(np.percentile(a, 95), np.percentile(c, 95))
    self.assertEqual(np.percentile(b, 95), np.percentile(d, 95))
    self.assertNotEqual(np.percentile(np.r_[a, b], 95), np.percentile(np.r_[c, d], 95))

  def test_selection_requires_all_eligibility_and_unique_lexicographic_minimum(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_review as r
    row = {'id': 'A', 'eligible': True, 'cost': [1, 2, 0]}
    self.assertEqual(r.design_outcome([row])['selected'], 'A')
    self.assertIsNone(r.design_outcome([row, {**row, 'id': 'B'}])['selected'])
    self.assertIsNone(r.design_outcome([{**row, 'eligible': False}])['selected'])
    self.assertEqual(r.design_outcome([row, {'id': 'B', 'eligible': True, 'cost': [2, 0, 0]}])['selected'], 'A')

  def test_inconclusive_is_not_weakly_selected_design(self):
    x = self.artifact('empirical-hurdle-stage1-v4-architecture-decision')
    self.assertEqual(x['status'], 'V4_ARCHITECTURE_REDESIGN_INCONCLUSIVE')
    self.assertIsNone(x['selected_architecture'])
    self.assertFalse((p.PUBLIC / 'empirical-hurdle-stage1-v4-design-contract.json').exists())

  def test_onset_and_conditional_auc_use_different_negative_populations(self):
    x = self.artifact('empirical-hurdle-stage1-v4-onset-continuation-support')
    for route in x['routes'].values():
      self.assertEqual(route['onset_count'] + route['continuation_count'], route['move_count'])
      self.assertEqual(route['onset_fraction'] + route['continuation_fraction'], 1.)
    self.assertIn('STATE_CONDITIONAL', x['conditional_auc_interpretation'])

  def test_state_conditional_score_population_support(self):
    jobs = self.artifact('empirical-hurdle-stage1-v3-onset-continuation-ranking')['jobs']
    for job in jobs:
      for population in ('train', 'development'):
        scores = job[population]['scores']
        for key in ('previous_static', 'previous_move'):
          row = scores[key]
          self.assertGreaterEqual(min(row['positive_count'], row['negative_count']), 201)
          self.assertEqual(row['auc'], row['auc_num2'] / row['auc_den2'])
        self.assertGreater(scores['onset']['negative_count'], scores['previous_static']['negative_count'])

  def test_singleton_counts_reconcile_boundary_censoring(self):
    routes = self.artifact('empirical-hurdle-stage1-v4-onset-continuation-support')['routes']
    self.assertEqual(sorted(row['singleton_fragments']['length_one_count'] for row in routes.values()), [15851, 17638])
    for row in routes.values():
      x = row['singleton_fragments']
      self.assertEqual(x['length_one_count'], x['boundary_censored_length_one_count'] + x['uncensored_length_one_count'])
      self.assertEqual(x['length_one_fraction'], x['length_one_count'] / x['move_fragment_count'])

  def test_route_transfer_keeps_no_feasible_null_and_exact_reference(self):
    rows = self.artifact('empirical-hurdle-stage1-v4-route-transfer-analysis')['jobs']
    self.assertEqual(sum(j['v3_dev_recall'] is None for j in rows), 1)
    for j in rows:
      self.assertLess(j['auc_dev_minus_train'], 0)
      if j['v3_dev_recall'] is not None:
        self.assertEqual(j['v3_dev_minus_reference_recall'], j['v3_dev_recall'] - j['train_reference_recall'])
      else:
        self.assertIsNone(j['v3_train_recall'])
        self.assertEqual(j['status'], 'NO_FEASIBLE_THRESHOLD')

  def test_evidence_lock_rejects_member_traversal(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_review as r
    row = self.artifact('empirical-hurdle-stage1-v4-architecture-inputs')
    row['public_inputs'] = {'../private.json': {'file_sha256': '0' * 64, 'receipt_sha256': '0' * 64}}
    with self.assertRaisesRegex(ValueError, 'V4_ARCHITECTURE_INPUT_CONFLICT'):
      r.verify_inputs(p.seal({k: v for k, v in row.items() if k != 'receipt_sha256'}))

  def test_builder_rejects_missing_repeatability_evidence(self):
    from tools.cyberpilot.build_hurdle_v4_review import build
    inputs = self.artifact('empirical-hurdle-stage1-v4-architecture-inputs')
    lock = p.seal({'baseline': inputs['baseline'], 'public_inputs': inputs['public_inputs']})
    fake = p.seal({'baseline': inputs['baseline'], 'public_input_lock_sha256': lock['receipt_sha256'],
                   'numeric_array_open_count': 12, 'source_writes': 0, 'routes': {}})
    with self.assertRaisesRegex(ValueError, 'V4_ARCHITECTURE_INPUT_CONFLICT'):
      build(lock, fake)

  def test_builder_rejects_raw_route_field_and_mutated_repeat(self):
    from tools.cyberpilot.build_hurdle_v4_review import build
    inputs = self.artifact('empirical-hurdle-stage1-v4-architecture-inputs')
    lock = p.seal({'schema': 'V4_ARCHITECTURE_PUBLIC_INPUT_LOCK', 'baseline': inputs['baseline'], 'public_inputs': inputs['public_inputs']})
    original = self.artifact('empirical-hurdle-stage1-v4-singleton-audit')['audit']
    for mutation in ('raw_ticks', 'repeat'):
      audit = copy.deepcopy(original)
      run = audit['runs'][1]
      if mutation == 'raw_ticks':
        next(iter(run['routes'].values()))['raw_ticks'] = [111, 222]
      else:
        run['source_members_unchanged_sha256'] = '0' * 64
      audit['runs'][1] = p.seal({k: v for k, v in run.items() if k != 'receipt_sha256'})
      audit = p.seal({k: v for k, v in audit.items() if k != 'receipt_sha256'})
      with self.assertRaisesRegex(ValueError, 'V4_ARCHITECTURE_INPUT_CONFLICT'):
        build(lock, audit)

  def test_public_only_builder_repeatability_with_numeric_execution_trapped(self):
    from tools.cyberpilot.build_hurdle_v4_review import build
    inputs = self.artifact('empirical-hurdle-stage1-v4-architecture-inputs')
    lock = p.seal({'schema': 'V4_ARCHITECTURE_PUBLIC_INPUT_LOCK', 'baseline': inputs['baseline'], 'public_inputs': inputs['public_inputs']})
    audit = self.artifact('empirical-hurdle-stage1-v4-singleton-audit')['audit']
    with patch('numpy.load', side_effect=AssertionError('NUMERIC_OPEN_NOT_AUTHORIZED')), \
         patch('numpy.linalg.solve', side_effect=AssertionError('FIT_NOT_AUTHORIZED')), \
         patch('numpy.linalg.lstsq', side_effect=AssertionError('FIT_NOT_AUTHORIZED')):
      one, two = build(lock, audit), build(lock, audit)
    self.assertEqual(p.canonical(one), p.canonical(two))
    for name, row in one.items():
      self.assertEqual(row, p.verify(json.loads((p.PUBLIC / name).read_bytes())))

  def test_readiness_no_actual_v4_authority(self):
    x = self.artifact('empirical-hurdle-stage1-v4-design-readiness')
    for k in ('fitting', 'cv', 'development', 'rollout', 'performance', 'selection'):
      self.assertEqual(x['v4'][k], 'NOT_RUN')
    self.assertEqual(x['holdout'], 'CLOSED')
    self.assertEqual(x['opening_count'], 0)
    self.assertEqual(x['vehicle_authority'], 'NONE')
    self.assertEqual(x['stage1_model_change'], 'NONE_IMPLEMENTED')
    self.assertEqual(x['stage2_model_change'], 'NONE_IMPLEMENTED')

  def test_publication_has_no_private_values_or_paths(self):
    forbidden = {'threshold_value', 'coefficients', 'normalizer_values', 'p_move', 'raw_ticks', 'raw_gates', 'gps'}
    def visit(row):
      if isinstance(row, dict):
        self.assertFalse(forbidden.intersection(row))
        for val in row.values():
          visit(val)
      elif isinstance(row, list):
        for val in row:
          visit(val)
      elif isinstance(row, str):
        for token in ('/mnt/', '/home/', 'E:\\', 'D:\\', 'C:\\'):
          self.assertNotIn(token, row)
    for name in ('architecture-inputs', 'equivalence-analysis', 'onset-continuation-support', 'route-transfer-analysis',
                 'architecture-options', 'architecture-selection-rule', 'architecture-decision', 'future-fitting-requirements',
                 'design-readiness', 'validation'):
      visit(self.artifact('empirical-hurdle-stage1-v4-' + name))


if __name__ == '__main__':
  unittest.main()
