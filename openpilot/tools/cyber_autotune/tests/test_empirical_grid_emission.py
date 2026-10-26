"""Store admission and raw reopening firewall for the fixed grid diagnostic."""
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from openpilot.tools.cyber_autotune import empirical_grid_emission as e
from openpilot.tools.cyber_autotune import empirical_plant_policy as p


class TestPolicy(unittest.TestCase):
  def test_policy_single_rule_and_exact_inputs(self):
    row=e.static_policy()
    self.assertEqual(row['grid']['step_deg'],.1)
    self.assertEqual(row['grid']['code_range'],[-32768,32767])
    self.assertEqual(len(row['selected']),6)
    self.assertEqual(row['projection_count'],1)
    for key in ('raw_opening_allowed','fitting_allowed','rollout_allowed','selector_allowed',
                'holdout_opening_allowed','search_allowed','stage_b_analysis_allowed'):
      self.assertIs(row[key],False)

  def test_four_stores_disjoint_outside_repo_no_symlink(self):
    with tempfile.TemporaryDirectory() as d:
      base=Path(d)
      inputs={n:base/n for n in e.NAMES}
      for x in inputs.values():
        x.mkdir()
      paths,out=e.stores(inputs,base/'out')
      self.assertEqual(set(paths),set(e.NAMES))
      self.assertEqual(out,base/'out')
      with self.assertRaises(ValueError):
        e.stores({**inputs,'v3':inputs['v2']},base/'out')
      with self.assertRaises(ValueError):
        e.stores({k:v for k,v in inputs.items() if k!='v2'},base/'out')
      (base/'link').symlink_to(inputs['v3'],target_is_directory=True)
      with self.assertRaises(ValueError):
        e.stores({**inputs,'v3':base/'link'},base/'out')

  def test_array_identity_checked_before_deserialization(self):
    with tempfile.TemporaryDirectory() as d:
      path=Path(d)/'array.npy'
      path.write_bytes(b'bad bytes')
      with patch.object(np,'load',side_effect=AssertionError('must not deserialize')):
        with self.assertRaisesRegex(ValueError,'DERIVATIVE_HASH_MISMATCH'):
          e.old.load_array(path,'0'*64)

  def test_raw_paths_raise(self):
    for name in ('/'.join(['','mnt','d','synthetic','a']), '/'.join(['D:','synthetic','a']), '/tmp/rlog.zst','/tmp/qlog.bz2'):
      with self.subTest(name=name),self.assertRaises(AssertionError):
        e.raw_guard('open',(name,'r'))
    e.raw_guard('open',('/tmp/cache.npy','r'))

  def test_unfrozen_policy_cannot_deserialize(self):
    with tempfile.TemporaryDirectory() as d:
      base=Path(d)
      inputs={n:base/n for n in e.NAMES}
      for x in inputs.values():
        x.mkdir()
      with patch.object(np,'load',side_effect=AssertionError('no arrays')):
        with self.assertRaises(FileNotFoundError):
          e.run(inputs,base/'out')

  def test_unchanged_array_bytes_preserved(self):
    with tempfile.TemporaryDirectory() as d:
      path=Path(d)/'one.npy'
      data=io.BytesIO()
      np.save(data,np.zeros((201,5)),allow_pickle=False)
      path.write_bytes(data.getvalue())
      raw=path.read_bytes()
      a=e.old.load_array(path,p.sha(raw))
      self.assertEqual(a.tobytes(),np.zeros((201,5)).tobytes())
      self.assertEqual(path.read_bytes(),raw)

  def test_future_contract_not_model_admission(self):
    row=e.readiness({'verdict':'SOURCE_GRID_OBSERVATION_REVIEW_POSSIBLE','strict_pass_scopes':6},'p','r','t')
    self.assertEqual(row['holdout_opening'],'HOLDOUT_OPENING_CLOSED')
    self.assertEqual(row['package_status'],'CLOSED_MISSING_ADMISSIBLE_MODEL')
    self.assertEqual(row['stage_b'],'STAGE_B_SIGNAL_ADMISSION_BLOCKED')
    self.assertEqual(row['model_admission'],'NO_MODEL_ADMITTED_FOR_FUTURE_HOLDOUT')

  def test_public_per_sample_data_rejected(self):
    for key in ('grid_predictions','grid_codes','emitted_values','origins','targets','predictions','residuals','private_path'):
      with self.subTest(key=key),self.assertRaises(ValueError):
        e.validate_public({key:[1,2]})

  def test_policy_freeze_does_not_decode_arrays(self):
    row=e.static_policy()
    self.assertEqual(row['input_v2_use'],'HASH_ONLY_NO_ALIGNED_ARRAY_DESERIALIZATION')
    self.assertEqual(row['metric_extension']['minimum_support'],201)
    self.assertEqual(row['metric_extension']['aggregation'],'MEAN_ROUTE_METRICS_PER_BIN_SAMPLE_WEIGHTED_SUPPORTING_ONLY')

  def test_policy_binds_every_array_and_origin(self):
    row=e.static_policy()
    for scope in row['selected']:
      self.assertEqual(len(scope['array_sha256']['one_step']),64)
      self.assertEqual(len(scope['array_sha256']['design']),64)
    for key in ('v3_policy_sha256','v3_fold_sha256','v3_selected_result_sha256','causal_policy_sha256',
                'causal_result_sha256','origin_map_sha256','source_dbc_sha256','metric_policy_sha256'):
      self.assertEqual(len(row[key]),64)

  def test_historical_blockers_and_no_selector(self):
    row=e.readiness({'verdict':'SOURCE_GRID_OBSERVATION_TRADEOFF_ONLY'},'p','r','t')
    self.assertEqual(row['calibration_blockers'],p.BLOCKERS)
    self.assertEqual(row['historical']['ta'],'TA_STANDALONE_TRADEOFF_ONLY')
    self.assertEqual(row['historical']['sg'],'SG_CLOSED_LOOP_TRADEOFF_ONLY')
    self.assertEqual(row['selector'],'NOT_RUN')
    self.assertEqual(row['rollout'],'NOT_RUN')
    self.assertFalse(row['production_authority'])
    self.assertFalse(row['composition_authorized'])

  def test_no_numeric_opening_before_policy(self):
    self.assertIs(e.static_policy()['arrays_deserialized_before_freeze'],False)

  def test_selected_config_is_exact_historical(self):
    for x in e.static_policy()['selected']:
      self.assertEqual(x['config'],{'family':'ARX1','delay_samples':5,'input_taps':1,'output_lags':1,'intercept':True})


if __name__=='__main__':
  unittest.main()
