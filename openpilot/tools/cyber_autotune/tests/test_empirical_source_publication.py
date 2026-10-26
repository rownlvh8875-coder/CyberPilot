import unittest
from openpilot.tools.cyber_autotune import empirical_source_publication as pub, empirical_plant_policy as p


class TestSourcePublication(unittest.TestCase):
  def test_dbc_empty_unit_preserved(self):
    data = b'BO_ 544 ESP12: 8 EPS\n SG_ YAW_RATE : 0|13@1+ (0.01,-40.95) [-40.95|40.96] "" EPS\n'
    row = pub.dbc_signal_definitions(data)['ESP12.YAW_RATE']
    self.assertIn('""', row['definition'])
    self.assertEqual(row['source_slice_sha256'], p.sha(data.decode().strip('\n').encode()))

  def test_schema_field_id_and_type(self):
    self.assertEqual(pub.schema_signal_fields(b'torqueOutputCan @8 :Float32;')['torqueOutputCan'], [('8', 'Float32')])

  def test_missing_field_not_false(self):
    self.assertEqual(pub.schema_signal_fields(b'')['torqueOutputCan'], [])

  def test_yaw_pending_never_physical_truth(self):
    row = pub.source_signal_matrix({'commit':'a', 'receipt_sha256':'b'}, {}, {})
    self.assertEqual(row['signals']['yaw'], 'SEMANTICS_PENDING_DBC_UNIT_EMPTY')
    self.assertIn('NOT_INDEPENDENT', row['gyro_frame'])

  def test_missing_metadata_not_complete(self):
    r = {'source_hashes':['a'], 'generation':{'carparams_sha256':'c'}, 'v1_overlap':False,
         'status':'ROUTE_DIFFERENT_SOURCE_GENERATION', 'route_id':'r', 'prior_analysis':'UNKNOWN', 'segment_count':1}
    row = pub.classify_route(r, [], 's', True)
    self.assertFalse(row['signal_semantics_complete'])
    self.assertFalse(row['profile_complete'])
    self.assertFalse(row['holdout_allowed'])

  def test_safety_reason_not_invented(self):
    row = pub.source_signal_matrix({'commit':'a', 'receipt_sha256':'b'}, {}, {})
    self.assertIn('SEMANTICS_PENDING', row['signals']['safety_curvature_limit_reason'])

  def test_fingerprint_alone_not_runtime(self):
    row = pub.source_signal_matrix({'commit':'a', 'receipt_sha256':'b'}, {}, {})
    self.assertIn('NOT_EPS_ACK', row['command'])
    self.assertIn('PENDING', row['runtime_steer_max'])

  def test_prior_unknown_stays_train_dev_only(self):
    r = {'source_hashes':['a'], 'generation':{'carparams_sha256':'c'}, 'v1_overlap':False,
         'status':'ROUTE_DIFFERENT_SOURCE_GENERATION', 'route_id':'r',
         'prior_analysis':'ROUTE_PRIOR_ANALYSIS_STATUS_UNKNOWN', 'segment_count':1}
    row = pub.classify_route(r, [], 's', True)
    self.assertEqual(row['maximum_future_role'], 'TRAIN_DEV_CANDIDATE_ONLY')
    self.assertFalse(row['untouched'])

  def test_raw_numeric_metrics_never_created(self):
    r = {'source_hashes':['a'], 'generation':{'carparams_sha256':'c'}, 'v1_overlap':False,
         'status':'ROUTE_DIFFERENT_SOURCE_GENERATION', 'route_id':'r', 'prior_analysis':'UNKNOWN', 'segment_count':1}
    self.assertIsNone(pub.classify_route(r, [], 's', True)['numeric_coverage'])

  def test_dbc_duplicate_signal_names_keep_message(self):
    data = (b'BO_ 902 WHL_SPD11: 8 ABS\n SG_ WHL_SPD_FL : 0|14@1+ (0.03125,0) [0|511] "kph" Vector\n'
            + b'BO_ 910 WHL_SPD12_FS: 8 ABS\n SG_ WHL_SPD_FL : 32|16@1+ (0.01,0) [0|655] "" Vector\n')
    rows = pub.dbc_signal_definitions(data)
    self.assertEqual(rows['WHL_SPD11.WHL_SPD_FL']['address'], 902)
    self.assertEqual(rows['WHL_SPD12_FS.WHL_SPD_FL']['address'], 910)
    self.assertIn('0|14', rows['WHL_SPD11.WHL_SPD_FL']['definition'])

  def test_unreviewed_empty_schema_no_availability_claim(self):
    row = pub.source_signal_matrix({'commit': 'a', 'receipt_sha256': 'b'}, {}, {})
    self.assertTrue(all('PENDING' in x for x in row['signals'].values()))

  def test_reviewed_empty_schema_rejected(self):
    with self.assertRaises(ValueError):
      pub.source_signal_matrix({'commit': 'a', 'receipt_sha256': 'b'}, {}, {}, True)

  def test_public_route_raw_identifier_rejected(self):
    fields = ('route_id', 'generation_id', 'original_status', 'classification', 'semantic_class_id',
              'signal_semantics_complete', 'profile_complete', 'empirical_profile_sha256',
              'full_carparams_sha256', 'source_origin_states', 'metadata_source_count',
              'revalidated_source_count', 'segment_count', 'prior_analysis', 'v1_overlap',
              'untouched', 'holdout_allowed', 'maximum_future_role', 'numeric_coverage')
    row = dict.fromkeys(fields)
    row['route_id'] = '/private/identifying-route'
    with self.assertRaises(ValueError):
      pub.publishable_route(row)

class TestPublishedSourceEvidence(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.rows = pub.load()
    cls.ready = cls.rows['empirical-source-audit-readiness-v1.json']

  def test_ten_pinned_receipts(self):
    self.assertEqual(len(self.rows), 10)
    for name, row in self.rows.items():
      self.assertEqual(p.verify(row)['receipt_sha256'], pub.PINS[name])

  def test_exact_triage_pin(self):
    self.assertEqual(self.rows['empirical-source-audit-triage-policy-v1.json']['receipt_sha256'],
                     '43966d3f7a1416653da32907137c8dd223184af252aab97112b2dd37b6f8dd2f')

  def test_primary_only_four(self):
    row = self.rows['empirical-source-audit-selection-v1.json']
    self.assertEqual(row['total_audited_generations'], 4)
    self.assertEqual(len(row['public_source_commits']), 4)
    self.assertEqual(row['executed_secondary'], [])
    self.assertEqual(row['executed_tertiary'], [])

  def test_one_narrow_semantic_pair_two_partial(self):
    classes = self.rows['empirical-source-equivalence-classes-v1.json']['classes']
    self.assertEqual(sum(x['status'] == 'SOURCE_AUDIT_PARTIAL' for x in classes), 2)
    pairs = [x for x in classes if x['status'] == 'EMPIRICAL_SIGNAL_SEMANTICS_EQUIVALENT']
    self.assertEqual(len(pairs), 1)
    self.assertEqual(len(pairs[0]['members']), 2)
    self.assertFalse(pairs[0]['physical_runtime_equivalent'])
    self.assertFalse(pairs[0]['global_behavior_equivalent'])

  def test_three_old_candidates_only(self):
    self.assertEqual(self.ready['old_route_pool_count'], 3)
    rows = self.rows['empirical-source-route-reclassification-v1.json']['routes']
    self.assertEqual(len(rows), 18)
    for row in rows:
      self.assertFalse(row['holdout_allowed'])
      self.assertFalse(row['untouched'])
      self.assertIsNone(row['numeric_coverage'])

  def test_incomplete_not_recovered(self):
    row = self.rows['empirical-source-route-reclassification-v1.json']
    self.assertEqual(row['resolved_ambiguous_routes'], 0)
    self.assertEqual(row['remaining_original_ambiguous_routes'], 77)
    self.assertEqual(row['original_incomplete_route_groups_unchanged'], 95)

  def test_future_holdout_still_required(self):
    self.assertEqual(self.ready['future_holdout'], 'FUTURE_UNTOUCHED_HOLDOUT_REQUIRED')
    self.assertFalse(self.ready['full_route_split_available'])
    self.assertFalse(self.ready['numeric_split_created'])

  def test_numeric_model_operations_not_run(self):
    for key in ('fitting', 'model_selection', 'command_numeric_check', 'yaw_crosscheck'):
      self.assertEqual(self.ready[key], 'NOT_RUN')
    for key in ('numeric_coverage', 'support_rows', 'gyro_correlation', 'model_metrics'):
      self.assertIsNone(self.ready[key])
    self.assertFalse(self.ready['holdout_opened'])

  def test_calibration_and_historical_verdicts(self):
    self.assertEqual(self.ready['calibration_blockers'], p.BLOCKERS)
    h = self.ready['historical']
    self.assertEqual(h['v2'], 'REJECTED')
    self.assertEqual(h['v2_violations'], 37)
    self.assertEqual(h['ta'], 'TA_STANDALONE_TRADEOFF_ONLY')
    self.assertEqual(h['sg'], 'SG_CLOSED_LOOP_TRADEOFF_ONLY')
    self.assertEqual(self.ready['sealed_reference'], 'NOT_GENERATED')

  def test_no_execution_authority(self):
    for row in self.rows.values():
      for key in p.FIREWALL:
        self.assertFalse(row[key])

  def test_no_private_path_or_blob_publication(self):
    import json
    text = json.dumps(self.rows)
    for forbidden in ('/mnt/d/', '/home/', 'logger_start_raw', 'wallTimeNanos', 'dongleId',
                      'first_ns', 'last_ns', 'numeric_traces', 'source_key', 'gyro_values'):
      self.assertNotIn(forbidden, text)

  def test_message_context_wheel_signal(self):
    matrices = self.rows['empirical-source-signal-matrix-v1.json']['matrices']
    for m in matrices:
      self.assertIn('WHL_SPD11.WHL_SPD_FL', m['carstate_selected_dbc'])
      self.assertEqual(m['dbc_signal_definitions']['WHL_SPD11.WHL_SPD_FL']['address'], 902)
      self.assertIn('""', m['dbc_signal_definitions']['ESP12.YAW_RATE']['definition'])
