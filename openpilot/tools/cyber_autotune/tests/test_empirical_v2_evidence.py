"""Public result-chain regression; no private store is needed by CI."""
import unittest

from openpilot.tools.cyber_autotune import empirical_v2_publication as pub
from openpilot.tools.cyber_autotune import empirical_v2_policy as v
from openpilot.tools.cyber_autotune import empirical_plant_policy as p


class TestV2Evidence(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.rows=pub.load()

  def get(self, name):
    return self.rows[name+'.json']

  def test_exact_three_roles(self):
    row=self.get('empirical-plant-v2-train-dev-split-v1')
    self.assertEqual([x['role'] for x in row['routes']],['TRAIN','TRAIN','DEVELOPMENT'])
    self.assertEqual([x['route_id'] for x in row['routes']],sorted(v.ROUTE_BINDINGS))
    self.assertFalse(row['numeric_opened_before_split'])
    self.assertFalse(row['v1_used'])

  def test_split_authorization_binding(self):
    split=self.get('empirical-plant-v2-train-dev-split-v1')
    auth=self.get('empirical-plant-v2-numeric-authorization-v1')
    self.assertEqual(auth['split_sha256'],split['receipt_sha256'])
    self.assertEqual(auth['code_sha256'],v.code_identity())
    self.assertFalse(auth['holdout_opening_allowed'])

  def test_exact_sources_and_whitelist(self):
    auth=self.get('empirical-plant-v2-numeric-authorization-v1')
    split=self.get('empirical-plant-v2-train-dev-split-v1')
    self.assertEqual(set(auth['sources']),set(v.ROUTE_BINDINGS))
    self.assertEqual(auth['signal_whitelist'],v.SIGNALS)
    self.assertEqual(auth,v.authorization(split,auth['sources']))

  def test_three_runtime_bridges(self):
    row=self.get('empirical-plant-v2-command-bridge-v1')
    self.assertEqual(len(row['routes']),3)
    self.assertTrue(row['pooling_allowed'])
    for route in row['routes']:
      self.assertEqual(route['status'],'ROUTE_COMMAND_BRIDGE_CONFIRMED')
      self.assertEqual(route['float32_exact_rate'],1.0)
      self.assertEqual(route['sign_conflicts'],0)
      self.assertEqual(route['domain_conflicts'],0)

  def test_all_segments_accounted(self):
    coverage=self.get('empirical-plant-v2-route-coverage-v1')
    self.assertEqual([x['segment_count'] for x in coverage['routes']],[70,86,1])
    for row in coverage['routes']:
      self.assertEqual(row['segment_count'],row['extracted_segment_count'])
      self.assertEqual(row['rejected_segments'],[])

  def test_coverage_accounting(self):
    coverage=self.get('empirical-plant-v2-route-coverage-v1')
    for row in coverage['routes']:
      self.assertEqual(row['total_grid_samples'],row['diagnostic_valid']+row['unavailable'])
      for b in row['bins'].values():
        self.assertEqual(b['total_grid_samples'],b['diagnostic_valid']+b['unavailable'])
        self.assertEqual(b['ARX1_design_rows'],b['FIR25_design_rows'])
        self.assertEqual(b['common_design_rows'],b['contiguous_45_sample_windows'])

  def test_split_support_is_route_sum(self):
    coverage=self.get('empirical-plant-v2-route-coverage-v1')
    for role, bins in coverage['splits'].items():
      for b, counts in bins.items():
        for key, count in counts.items():
          self.assertEqual(count,sum(x['bins'][b][key] for x in coverage['routes'] if x['role']==role))

  def test_development_empty_remains_unselected(self):
    stage=self.get('empirical-plant-v2-stage-a-selection-v1')
    self.assertEqual(stage['minimum_development_support'],201)
    for row in stage['bins'].values():
      self.assertEqual(row['common_development_rows'],0)
      self.assertEqual(row['state'],'STAGE_A_MODEL_SELECTION_BLOCKED')
      self.assertIsNone(row['selected'])
      self.assertIsNone(row['selected_model_sha256'])

  def test_training_does_not_override_empty_development(self):
    stage=self.get('empirical-plant-v2-stage-a-selection-v1')
    for row in stage['bins'].values():
      self.assertEqual(len(row['candidates']),8)
      self.assertTrue(any(x['fit_status']=='FITTED' for x in row['candidates']))
      self.assertTrue(all(x['development']['count']==0 for x in row['candidates']))

  def test_unknown_limits_are_null(self):
    for row in self.get('empirical-plant-v2-route-coverage-v1')['routes']:
      self.assertIsNone(row['safety_limited'])
      self.assertIsNone(row['curvature_limited'])
      self.assertEqual(row['clean_primary_valid'],0)

  def test_yaw_cannot_admit_empty_development(self):
    yaw=self.get('empirical-plant-v2-yaw-admission-v1')
    self.assertFalse(yaw['admitted'])
    self.assertIsNone(yaw['selection']['hypothesis'])
    self.assertEqual(set(yaw['selection']['candidates']),{'YAW_H1','YAW_H2','YAW_H3','YAW_H4'})
    self.assertNotIn('empirical-plant-v2-stage-b-selection-v1.json',self.rows)

  def test_no_fake_frozen_model(self):
    freeze=self.get('empirical-plant-v2-model-freeze-v1')
    self.assertEqual(freeze['models'],{'STAGE_A':{},'STAGE_B':{}})
    self.assertFalse(freeze['holdout_opened'])

  def test_future_holdout_closed_without_selected_model(self):
    row=self.get('future-empirical-plant-v2-holdout-evaluation-v1')
    self.assertEqual(row['one_time_opening_state'],'CLOSED')
    self.assertEqual(row['future_holdout'],'FUTURE_UNTOUCHED_HOLDOUT_REQUIRED')
    for key in ('reselection_allowed','refit_allowed','threshold_change_allowed','old_routes_holdout_allowed','evaluation_execution_authorized'):
      self.assertFalse(row[key])
    self.assertEqual(row['models'],{'STAGE_A':{},'STAGE_B':{}})

  def test_freeze_to_package_chain(self):
    freeze=self.get('empirical-plant-v2-model-freeze-v1')
    package=self.get('future-empirical-plant-v2-holdout-evaluation-v1')
    ready=self.get('empirical-plant-v2-train-dev-readiness-v1')
    self.assertEqual(package['model_freeze_sha256'],freeze['receipt_sha256'])
    self.assertEqual(ready['holdout_package_sha256'],package['receipt_sha256'])
    self.assertEqual(ready['model_freeze_sha256'],freeze['receipt_sha256'])

  def test_readiness_not_model_readiness(self):
    ready=self.get('empirical-plant-v2-train-dev-readiness-v1')
    self.assertEqual(ready['numeric_route_count'],3)
    self.assertEqual(ready['stage_a_state'],'STAGE_A_MODEL_SELECTION_BLOCKED')
    self.assertEqual(ready['stage_b_state'],'STAGE_B_SIGNAL_ADMISSION_BLOCKED')
    self.assertFalse(ready['plant_ready'])
    self.assertFalse(ready['holdout_evaluated'])

  def test_no_candidate_or_stage_c_execution(self):
    ready=self.get('empirical-plant-v2-train-dev-readiness-v1')
    for key in ('stage_c','candidate_evaluation','ta_empirical_execution','sg_empirical_execution'):
      self.assertEqual(ready[key],'NOT_RUN')
    for row in self.rows.values():
      for key in ('ta_execution','sg_execution','production_authority','vehicle_activation_allowed'):
        self.assertFalse(row[key])

  def test_no_private_publication(self):
    text=p.canonical(self.rows).decode()
    for forbidden in ('coefficients','singular_values','/mnt/','/home/','C:\\\\','D:\\\\','grid_time_ns','sensor_ns','command_pairs','gyro_options'):
      self.assertNotIn(forbidden,text)

  def test_baseline_blockers_preserved(self):
    ready=self.get('empirical-plant-v2-train-dev-readiness-v1')
    self.assertEqual(ready['calibration_blockers'],p.BLOCKERS)
    self.assertEqual(ready['sealed_reference'],'NOT_GENERATED')
    self.assertEqual(ready['vehicle'],['NOT_READY','REAL_VEHICLE_UNVERIFIED','VEHICLE_ACTIVATION_BLOCKED'])
