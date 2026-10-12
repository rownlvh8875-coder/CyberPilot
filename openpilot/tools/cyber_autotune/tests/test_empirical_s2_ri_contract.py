import unittest
from importlib import import_module


class TestS2RIContract(unittest.TestCase):
  def contracts(self):
    return import_module('openpilot.tools.cyber_autotune.empirical_s2_ri_policy').contracts()

  def test_no_rate_schema(self):
    c = self.contracts()['signal']
    self.assertEqual(c['features'], ['logged_normalized_command_history', 'past_angle_tick_increments', 'current_angle_tick', 'current_speed_mps', 'intercept'])
    self.assertEqual(c['steering_rate_dependency'], 'NONE')

  def test_prior_exposure_folds(self):
    c = self.contracts()['route-cv']
    a, b = c['folds']
    self.assertEqual(a['train'], b['development'])
    self.assertEqual(b['train'], a['development'])
    self.assertNotEqual(a['train'], a['development'])
    self.assertFalse(c['holdout_allowed'])
    self.assertEqual(c['normalization'], 'TRAIN_ROUTE_ONLY_NO_POOLED_OR_DEVELOPMENT_STATISTICS')

  def test_metric_no_values(self):
    c = self.contracts()['future-metric']
    self.assertEqual(c['metric_values'], 'NOT_COMPUTED')
    self.assertEqual(c['comparator'], 'HOLD_LAST_ANGLE')
    self.assertEqual(c['rollout_seconds'], [.25, .5, 1., 2.])

  def test_rate_dependency_rejected(self):
    m = import_module('openpilot.tools.cyber_autotune.empirical_s2_ri_policy')
    for key in ('features', 'target', 'admission', 'reset', 'selection'):
      with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'S2_RI_RATE_DEPENDENCY_FORBIDDEN'):
        m.validate_model_spec({key: 'steeringRateDeg'})

  def test_emission_contract_only(self):
    c = self.contracts()['angle-grid']
    self.assertFalse(c['prediction_executed'])
    self.assertEqual(c['emission_rule']['tie_rule'], 'ROUND_HALF_TO_EVEN')
    self.assertEqual(c['historical_verdict'], 'SOURCE_GRID_OBSERVATION_REJECTED')

  def test_emission_tick_to_degree_units_explicit(self):
    c = self.contracts()['angle-grid']
    self.assertEqual(c['future_next_angle'], 'NEXT_ANGLE_DEG=FLOAT64_POINT_ONE*(CURRENT_TICK+CONTINUOUS_DELTA_TICK);THEN_HISTORICAL_DEGREE_GRID_RULE')

  def test_development_normalization_rejected(self):
    from openpilot.tools.cyber_autotune import empirical_plant_policy as p
    from openpilot.tools.cyber_autotune.empirical_s2_ri_schema import public
    for norm in ('POOLED', 'DEVELOPMENT_ROUTE', 'HOLDOUT'):
      c = dict(self.contracts()['route-cv'])
      c['normalization'] = norm
      with self.subTest(norm=norm), self.assertRaises(ValueError):
        public(p.seal({k: v for k, v in c.items() if k != 'receipt_sha256'}))

  def test_rate_free_identity_and_request_exclusion(self):
    from openpilot.tools.cyber_autotune.empirical_s2_ri_admission import identity_contract, row_contract
    c = identity_contract()
    self.assertNotIn('state.rate', c['required'])
    self.assertNotIn('control.requested', c['required'])
    self.assertEqual(c['historical_generic_causal_identity'], 'RATE_DEPENDENT_IMMUTABLE_REFERENCE_ONLY')
    self.assertFalse(row_contract()['steering_rate_required'])
    self.assertFalse(row_contract()['controller_request_required'])

  def test_historical_verdicts_unchanged(self):
    from openpilot.tools.cyber_autotune.empirical_s2_ri_policy import historical, PINS
    x = historical()
    self.assertEqual({k: x[k]['receipt_sha256'] for k in PINS}, PINS)
    self.assertEqual(x['empirical-model-family-identifiability-readiness-v1.json']['family_states']['S3'], 'S3_SOURCE_MECHANISM_BLOCKED')

  def test_no_runtime_authority(self):
    for value in self.contracts().values():
      self.assertFalse(any(value['authority'].values()))
      self.assertFalse(value['qualification_allowed'])
      self.assertFalse(value['vehicle_activation_allowed'])

  def test_no_scope_or_form_selection(self):
    h = self.contracts()['history-reset']
    for key in ('selected_d', 'selected_L_u', 'selected_L_delta', 'selected_scope'):
      self.assertIsNone(h[key])
    self.assertEqual(h['candidate_set'], 'CANDIDATE_SET_MUST_BE_PREDECLARED_BEFORE_FITTING')

  def test_no_physical_command_or_delay_claim(self):
    self.assertEqual(self.contracts()['signal']['physical_eps'], 'PHYSICAL_EPS_APPLICATION_UNAVAILABLE')
    self.assertIn('NOT_PHYSICAL_DELAY', self.contracts()['history-reset']['command_offset_semantics'])
