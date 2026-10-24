"""Read-only attribution contracts; standard unittest discovery, no pytest dependency."""
import importlib
import importlib.util
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch
import numpy as np


def module():
  name = 'openpilot.tools.cyber_autotune.empirical_s2_ri_attribution_v2_math'
  return importlib.import_module(name) if importlib.util.find_spec(name) else None


def one_fixture():
  current = np.array([0, 1, 0, 0, 0, 0], dtype=np.int64)
  delta = np.array([0, 0, 1, -1, 2, -2], dtype=np.int64)
  pred = np.array([0.5, 0.5, 0.0, 1.0, 1.5, -1.5])
  projected = np.rint(current + pred).astype(np.int64)
  return {'current_tick': current, 'target_next_tick': current + delta, 'actual_delta_tick': delta,
          'prediction': pred, 'projected': projected, 'error': pred - delta,
          'comparator_error': -delta.astype(float), 'hold_last_next_tick': current.copy(),
          'speed_bin_code': np.array([1, 2, 3, 1, 2, 3], dtype=np.int8),
          'speed_mps': np.array([10., 20., 30., 10., 20., 30.]),
          'rail': np.array([False, True, False, False, True, False]),
          'prior_delta_tick': np.array([0, 1, 0, 1, -1, -1]),
          'command_current': np.arange(6, dtype=float)/10,
          'command_feature_newest': np.arange(6, dtype=float)/10}


def roll_fixture():
  observed = np.array([[0, 0, 0, 0], [0, 1, 0, 0], [0, 1, 1, 2], [1, 1, 1, 1]], dtype=np.int64)
  projected = np.array([[0, 1, 1, 2], [0, 0, 0, 0], [0, 1, 0, 2], [1, 1, 1, 1]], dtype=np.int64)
  hold = np.repeat(observed[:, :1], 4, axis=1)
  return {'observed_path': observed, 'projected_path': projected, 'hold_last_path': hold,
          'initial_tick': observed[:, 0], 'target_endpoint_tick': observed[:, -1],
          'projected': projected[:, -1], 'error': (projected[:, -1]-observed[:, -1]).astype(float),
          'comparator_error': (hold[:, -1]-observed[:, -1]).astype(float)}


class TestAttributionMath(unittest.TestCase):
  def setUp(self):
    self.m = module()
    self.assertIsNotNone(self.m, 'Pure attribution implementation required')

  def test_partitions_and_confusion(self):
    result, arrays = self.m.one_step(one_fixture())
    self.assertEqual(result['classes']['STATIC']['count'], 2)
    self.assertEqual(result['classes']['MOVE']['count'], 4)
    self.assertEqual(result['confusion']['counts'], {'STATIC_CORRECT_HOLD': 1, 'STATIC_FALSE_MOVE': 1, 'MOVE_MISSED': 1, 'MOVE_DETECTED': 3})
    self.assertEqual(sum(result['confusion']['counts'].values()), 6)
    self.assertEqual(result['sign']['counts'], {'SIGN_CORRECT': 2, 'SIGN_WRONG': 1, 'PREDICTED_ZERO': 1})
    self.assertEqual(arrays['static_mask'].tolist(), [True, True, False, False, False, False])

  def test_sae_sse_and_stored_errors(self):
    a = one_fixture()
    result, _ = self.m.one_step(a)
    for name, mask in [('STATIC', a['actual_delta_tick']==0), ('MOVE', a['actual_delta_tick']!=0)]:
      c = result['classes'][name]
      self.assertEqual(c['candidate']['sae'], float(np.sum(np.abs(a['error'][mask]))))
      self.assertEqual(c['delta_sse'], float(np.sum(a['error'][mask]**2)-np.sum(a['comparator_error'][mask]**2)))
    self.assertEqual(result['partition_accounting']['counts_exact'], True)

  def test_half_tick_parity(self):
    result, _ = self.m.one_step(one_fixture())
    b = result['projection_boundary']
    self.assertEqual(b['exact_half_count'], 2)
    self.assertEqual(b['half_tick_held'], 1)
    self.assertEqual(b['half_tick_moved'], 1)

  def test_source_tick_conflict_rejected(self):
    a = one_fixture()
    a['actual_delta_tick'][0] = 9
    with self.assertRaisesRegex(ValueError, 'INPUT_CONFLICT'):
      self.m.one_step(a)

  def test_static_holdlast_verified(self):
    a = one_fixture()
    a['comparator_error'][0] = 1.
    with self.assertRaisesRegex(ValueError, 'INPUT_CONFLICT'):
      self.m.one_step(a)

  def test_empty_metrics_are_null(self):
    result = self.m.metrics(np.array([], dtype=float))
    self.assertEqual(result, {'count':0,'sae':None,'sse':None,'rmse':None,'mae':None,'p95':None})

  def test_p95_linear(self):
    self.assertEqual(self.m.metrics(np.array([0., 1., 2.]))['p95'], 1.9)

  def test_nonfinite_rejected(self):
    with self.assertRaisesRegex(ValueError, 'INPUT_CONFLICT'):
      self.m.metrics(np.array([np.nan]))

  def test_rollout_classes(self):
    result, a = self.m.rollout(roll_fixture())
    self.assertEqual(result['classes']['PATH_FLAT']['count'], 2)
    self.assertEqual(result['classes']['PATH_MOVED']['count'], 2)
    self.assertEqual(result['classes']['PATH_MOVED_ENDPOINT_STATIC']['count'], 1)
    self.assertEqual(a['first_divergence'].tolist(), [1, 1, 2, 0])
    self.assertEqual(a['first_false_move'].tolist(), [1, 0, 0, 0])

  def test_motion_and_reversals(self):
    result, a = self.m.rollout(roll_fixture())
    self.assertEqual(a['projected_move_count'].tolist(), [2, 0, 3, 0])
    self.assertEqual(a['observed_reversal_count'].tolist(), [0, 1, 0, 0])
    self.assertEqual(a['projected_reversal_count'].tolist(), [0, 0, 2, 0])
    self.assertEqual(result['false_motion']['count'], 1)
    self.assertEqual(result['missed_motion']['count'], 1)

  def test_rollout_endpoint_conflict(self):
    a = roll_fixture()
    a['error'][0] += 1
    with self.assertRaisesRegex(ValueError, 'INPUT_CONFLICT'):
      self.m.rollout(a)

  def test_tail_ties(self):
    result, _ = self.m.rollout(roll_fixture())
    self.assertEqual(result['tail_composition']['count'], 1)
    self.assertEqual(result['tail_composition']['PATH_FLAT'], 1)

  def test_rollout_chunk_independent(self):
    a = roll_fixture()
    x, xa = self.m.rollout(a, chunk=1)
    y, ya = self.m.rollout(a, chunk=512)
    self.assertEqual(x, y)
    for key in xa:
      np.testing.assert_array_equal(xa[key], ya[key])


  def test_exact_boundary_no_epsilon(self):
    a=one_fixture()
    a['prediction'][:2]=[np.nextafter(.5,0),np.nextafter(.5,1)]
    a['projected']=np.rint(a['current_tick']+a['prediction']).astype(np.int64)
    a['error']=a['prediction']-a['actual_delta_tick']
    r,_=self.m.one_step(a)
    self.assertEqual(r['projection_boundary']['exact_half_count'],0)
    self.assertEqual(r['projection_boundary']['less_than_half_count'],1)
    self.assertEqual(r['projection_boundary']['greater_than_half_count'],1)

  def test_all_static_zero_move_support(self):
    a=one_fixture()
    a['actual_delta_tick'][:]=0
    a['target_next_tick']=a['current_tick'].copy()
    a['error']=a['prediction'].copy()
    a['comparator_error']=np.zeros(6)
    r,_=self.m.one_step(a)
    self.assertIsNone(r['classes']['MOVE']['delta_sse'])
    self.assertFalse(r['zero_transition_job_pattern'])

  def test_all_move_zero_static_support(self):
    a=one_fixture()
    a['actual_delta_tick'][:]=1
    a['target_next_tick']=a['current_tick']+1
    a['error']=a['prediction']-1
    a['comparator_error']=np.full(6,-1.)
    r,_=self.m.one_step(a)
    self.assertEqual(r['projection_boundary']['static_count'],0)
    self.assertFalse(r['zero_transition_job_pattern'])

  def test_partition_direction_and_magnitude(self):
    r,_=self.m.one_step(one_fixture())
    self.assertEqual(r['classes']['MOVE_POSITIVE']['count']+r['classes']['MOVE_NEGATIVE']['count'],4)
    self.assertEqual(r['classes']['ONE_TICK_MOVE']['count']+r['classes']['MULTI_TICK_MOVE']['count'],4)
    self.assertGreater(r['classes']['STATIC']['delta_sae'],0)

  def test_context_frozen_counts(self):
    r,_=self.m.one_step(one_fixture())
    self.assertEqual(sum(r['context'][k]['metrics']['count'] for k in ('LOW','MEDIUM','HIGH')),6)
    self.assertEqual(r['context']['RAIL']['metrics']['count'],2)
    self.assertEqual(r['context']['REVERSAL']['metrics']['count'],2)
    self.assertEqual(r['context']['SAME_DIRECTION']['metrics']['count'],1)

  def test_unknown_speed_code_rejected(self):
    a=one_fixture()
    a['speed_bin_code'][0]=4
    with self.assertRaisesRegex(ValueError,'INPUT_CONFLICT'):
      self.m.one_step(a)

  def test_reversal_ignores_zero(self):
    count=self.m.reversal_count(np.array([[1,0,-1,0,1],[0,0,0,0,0],[1,0,1,0,1]]))
    np.testing.assert_array_equal(count,[2,0,0])

  def test_all_zero_tail_includes_ties(self):
    a=roll_fixture()
    a['projected_path']=a['observed_path'].copy()
    a['projected']=a['observed_path'][:,-1].copy()
    a['error']=np.zeros(4)
    r,_=self.m.rollout(a)
    self.assertEqual(r['tail_composition']['count'],4)
    self.assertEqual(r['first_divergence']['no_event_count'],4)

  def test_holdlast_path_tamper_rejected(self):
    a=roll_fixture()
    a['hold_last_path'][0,1]=1
    with self.assertRaisesRegex(ValueError,'INPUT_CONFLICT'):
      self.m.rollout(a)

  def test_projected_initial_state_tamper(self):
    a=roll_fixture()
    a['projected_path'][0,0]=1
    with self.assertRaisesRegex(ValueError,'INPUT_CONFLICT'):
      self.m.rollout(a)

  def test_return_to_anchor_and_endpoint_partition(self):
    r,_=self.m.rollout(roll_fixture())
    self.assertEqual(r['classes']['PATH_MOVED_ENDPOINT_STATIC']['count'],1)
    self.assertEqual(sum(r['classes'][k]['count'] for k in ('ENDPOINT_STATIC','ENDPOINT_ONE_TICK','ENDPOINT_MULTI_TICK')),4)

  def test_path_chunk_boundary_513(self):
    a={k:np.concatenate([v]*129,axis=0) for k,v in roll_fixture().items()}
    r,x=self.m.rollout(a,chunk=512)
    s,y=self.m.rollout(a,chunk=7)
    self.assertEqual(r,s)
    for key in x:
      np.testing.assert_array_equal(x[key],y[key])


  def test_rollout_partition_float_accounting(self):
    result,_=self.m.rollout(roll_fixture())
    account=result['partition_accounting']
    for partition in ('path_partition','endpoint_partition'):
      for side in ('candidate','hold_last'):
        for metric in ('sae','sse'):
          self.assertEqual(account[partition][side][metric],0.)
    self.assertFalse(account['p95_additive'])
  def test_trigger_strict(self):
    result = self.m.trigger([True]*32)
    self.assertEqual(result['one_step_outcome'], 'ZERO_STATIC_TRANSITION_TRADEOFF_STRICT')
    self.assertTrue(result['hurdle_design_review_supported'])
    self.assertFalse(result['hurdle_implementation_authorized'])

  def test_trigger_mixed(self):
    self.assertEqual(self.m.trigger([True]*31+[False])['hurdle_state'], 'HURDLE_FAMILY_DESIGN_REVIEW_INCONCLUSIVE')

  def test_trigger_none(self):
    self.assertEqual(self.m.trigger([False]*32)['hurdle_state'], 'HURDLE_FAMILY_DESIGN_REVIEW_NOT_SUPPORTED_BY_V2')

  def test_trigger_requires_all_jobs(self):
    with self.assertRaisesRegex(ValueError, '32_JOBS_REQUIRED'):
      self.m.trigger([True]*31)



class TestAttributionStore(unittest.TestCase):
  def setUp(self):
    name = 'openpilot.tools.cyber_autotune.empirical_s2_ri_attribution_v2'
    self.assertIsNotNone(importlib.util.find_spec(name), 'Read-only admission implementation required')
    self.e = importlib.import_module(name)

  def test_exact_manifest(self):
    with self.assertRaisesRegex(ValueError, 'EXACT_RECONSTRUCTION_MANIFEST'):
      self.e.require_manifest(self.e.p.seal({'job_count':32,'files':{}}))

  def test_exact_jobs(self):
    jobs = [{'candidate_id':c,'fold':f} for c in self.e.CANDIDATES for f in ('FOLD_A','FOLD_B')]
    self.e.require_jobs(jobs)
    for invalid in (jobs[:-1], jobs+jobs[:1], list(reversed(jobs))):
      with self.assertRaisesRegex(ValueError, '32_JOBS_REQUIRED'):
        self.e.require_jobs(invalid)

  def test_readiness_requires_all_states(self):
    value = {'status':self.e.READY_STATES[0], 'states':list(self.e.READY_STATES)}
    self.e.require_readiness(value)
    value['states'].pop()
    with self.assertRaisesRegex(ValueError, 'INPUT_NOT_READY'):
      self.e.require_readiness(value)

  def test_firewall_solvers(self):
    with self.e.firewall(()):
      for method in (np.linalg.lstsq,np.linalg.solve,np.linalg.pinv):
        with self.assertRaisesRegex(ValueError, 'EXECUTION_FORBIDDEN'):
          method(None,None)

  def test_firewall_execution_imports(self):
    with self.e.firewall(()):
      for suffix in ('empirical_s2_ri_fit_cv_execution','empirical_s2_ri_reconstruction',
                     'empirical_s2_ri_reconstruction_math','empirical_s2_ri_execution'):
        with self.assertRaisesRegex(ValueError, 'EXECUTION_FORBIDDEN'):
          importlib.import_module('openpilot.tools.cyber_autotune.'+suffix)

  def test_no_source_array_open(self):
    with self.e.firewall(()):
      for name in ('/tmp/rlog.zst','/tmp/qlog.npy','/tmp/causal.npy'):
        with self.assertRaisesRegex(ValueError, 'EXECUTION_FORBIDDEN'):
          np.load(name)

  def test_array_is_readonly_and_exact(self):
    with tempfile.TemporaryDirectory() as folder:
      path=Path(folder)/'x.npy'
      b=self.e.storage.array_write(path,np.arange(3,dtype=np.int64))
      with self.e.firewall((path,)):
        a=self.e.open_array(path,b,(path,))
        self.assertFalse(a.flags.writeable)
        np.testing.assert_array_equal(a,[0,1,2])

  def test_hash_drift_before_decode(self):
    with tempfile.TemporaryDirectory() as folder:
      path=Path(folder)/'x.npy'
      b=self.e.storage.array_write(path,np.arange(3,dtype=np.int64))
      path.write_bytes(path.read_bytes()+b'bad')
      with patch.object(np,'load',side_effect=AssertionError('decode before hash')):
        with self.assertRaisesRegex(ValueError,'INPUT_CONFLICT'):
          self.e.open_array(path,b,(path,))

  def test_shape_conflict(self):
    with tempfile.TemporaryDirectory() as folder:
      path=Path(folder)/'x.npy'
      b=self.e.storage.array_write(path,np.arange(3,dtype=np.int64))
      b['shape']=[4]
      with self.assertRaisesRegex(ValueError,'INPUT_CONFLICT'):
        self.e.open_array(path,b,(path,))

  def test_traversal_rejected(self):
    with self.assertRaises(ValueError):
      self.e.h.relative_file(Path('/tmp'), '../outside.npy')

  def test_symlink_rejected(self):
    with tempfile.TemporaryDirectory() as folder:
      path=Path(folder)
      (path/'target').mkdir()
      (path/'alias').symlink_to(path/'target',target_is_directory=True)
      with self.assertRaises(ValueError):
        self.e.storage.safe(path/'alias'/'x.npy')

  def test_overlap_rejected(self):
    with tempfile.TemporaryDirectory() as folder:
      path=Path(folder)
      with self.assertRaisesRegex(ValueError,'OVERLAP'):
        self.e.storage.external(path/'output',[path])

  def test_no_overwrite(self):
    with tempfile.TemporaryDirectory() as folder:
      path=Path(folder)/'x.json'
      self.e.write(path,self.e.p.seal({'value':1}))
      with self.assertRaisesRegex(ValueError,'IMMUTABLE'):
        self.e.write(path,self.e.p.seal({'value':2}))

  def test_public_historical_gate_reconciliation(self):
    values=self.e.public_inputs()
    self.assertEqual(values['historical']['selection-result']['admissible_count'],0)
    self.assertEqual(self.e.h.failure_counts(values['historical']['fit-cv-results']['jobs']),self.e.h.EXPECTED_FAILURES)

  def test_resume_without_loader_or_compute(self):
    with tempfile.TemporaryDirectory() as folder:
      root=Path(folder)
      value=self.e.p.seal({'schema':'TEST','jobs':[]})
      self.e.write(root/'summary.json',value)
      manifest=self.e.finish(root,['summary.json'],{'schema':'TEST','summary_sha256':value['receipt_sha256']})
      with (patch.object(self.e,'open_array',side_effect=AssertionError('numeric loader')),
            patch.object(self.e.math,'one_step',side_effect=AssertionError('compute'))):
        self.assertEqual(self.e.resume(root),manifest)
      (root/'summary.json').write_text('changed')
      with self.assertRaises(ValueError):
        self.e.resume(root)


  def test_descriptive_group_membership(self):
    one,_=module().one_step(one_fixture())
    roll,_=module().rollout(roll_fixture())
    jobs=[{'candidate_id':c,'fold':f,'one_step':one,'rollout':{str(h):roll for h in self.e.HORIZONS}}
          for c in self.e.CANDIDATES for f in ('FOLD_A','FOLD_B')]
    summary=self.e.family_summary(jobs)
    for axis in ('d','L'):
      self.assertEqual([v['jobs'] for v in summary['descriptive_groups'][axis].values()],[8]*4)

  def test_population_field_layout(self):
    for key in self.e.ONE+self.e.CONTEXT:
      b={'dtype':'<f8','shape':[5],'order':'C','file_sha256':'a'*64,'array_sha256':'b'*64}
      if key in ('current_tick','target_next_tick','actual_delta_tick','hold_last_next_tick','projected',
                 'anchor_index','anchor_order_index','prior_delta_tick','s2_ri_run_id','within_run_index'):
        b['dtype']='<i8'
      if key in ('anchor_route_id','anchor_segment_sha'):
        b['dtype']='|S64'
      if key in ('rail','model_eligible'):
        b['dtype']='|b1'
      if key=='speed_bin_code':
        b['dtype']='|i1'
      if key=='command_history':
        b['shape']=[5,1]
      self.e.require_binding(key,b,5,1,1)
      b['shape']=[6]
      with self.assertRaisesRegex(ValueError,'INPUT_CONFLICT'):
        self.e.require_binding(key,b,5,1,1)

  def test_firewall_cached_prediction_and_selection(self):
    from openpilot.tools.cyber_autotune import empirical_s2_ri_fit_cv_math as old
    from openpilot.tools.cyber_autotune import empirical_s2_ri_fit_cv_gates as gates
    with self.e.firewall(()):
      for method in (old.fit,old.normalizer,old.predict,gates.select):
        with self.assertRaisesRegex(ValueError,'EXECUTION_FORBIDDEN'):
          method(None)


  def test_cached_recursive_rejected(self):
    from openpilot.tools.cyber_autotune import empirical_s2_ri_fit_cv_math as old
    with self.e.firewall(()):
      with self.assertRaisesRegex(ValueError,'EXECUTION_FORBIDDEN'):
        old.recursive(None,None,None,None,None,None)

  def test_incomplete_context_path_fields(self):
    fields=set(self.e.ROLL)|set(self.e.CONTEXT)
    self.e.require_fields(fields,25)
    for key in ('observed_path','projected_path','prior_delta_tick','rail','speed_bin_code'):
      with self.assertRaisesRegex(ValueError,'INPUT_CONFLICT'):
        self.e.require_fields(fields-{key},25)


  def test_root_authorization_resume_lineage(self):
    with tempfile.TemporaryDirectory() as folder:
      root=Path(folder)
      policy=self.e.policy()
      auth=self.e.p.seal({'input_manifest_sha256':self.e.INPUT_SHA,'policy_sha256':policy['receipt_sha256'],
        'executor_sources':self.e.sources(),'output_store_identity':self.e.p.sha(str(root).encode()),
        'public_file_sha256':self.e.PUBLIC_PINS})
      self.e.write(root/'authorization.json',auth)
      self.e.write(root/'policy.json',policy)
      manifest={'authorization_sha256':auth['receipt_sha256'],'input_manifest_sha256':self.e.INPUT_SHA,
                'policy_sha256':policy['receipt_sha256'],'executor_sources':self.e.sources()}
      self.assertEqual(self.e.verify_authorization(root,manifest),auth)
      altered={**manifest,'authorization_sha256':'0'*64}
      with self.assertRaisesRegex(ValueError,'INPUT_CONFLICT'):
        self.e.verify_authorization(root,altered)
      (root/'policy.json').unlink()
      with self.assertRaisesRegex(ValueError,'INPUT_CONFLICT'):
        self.e.verify_authorization(root,manifest)

  def test_root_authorization_deleted_rejected(self):
    with tempfile.TemporaryDirectory() as folder:
      with self.assertRaisesRegex(ValueError,'INPUT_CONFLICT'):
        self.e.verify_authorization(Path(folder),{})
  def test_closed_authority(self):
    value=self.e.policy()
    self.assertFalse(value['candidate_ranking'])
    self.assertFalse(value['gate_reevaluation'])
    self.assertFalse(value['hurdle_implementation_authorized'])
    self.assertEqual(value['holdout'],'CLOSED')
    self.assertEqual(value['opening_count'],0)



class TestAttributionPublication(unittest.TestCase):
  def setUp(self):
    name='openpilot.tools.cyber_autotune.empirical_s2_ri_attribution_v2_publication'
    self.assertIsNotNone(importlib.util.find_spec(name),'Closed publication required')
    self.pub=importlib.import_module(name)

  def test_raw_lists_rejected(self):
    with self.assertRaisesRegex(ValueError,'PUBLIC_AGGREGATE'):
      self.pub.validate_aggregate({'values':[1.,2.]})

  def test_private_keys_rejected(self):
    for key in ('coefficients','normalizer','private_path','raw_angles','anchor_ids'):
      with self.assertRaisesRegex(ValueError,'PUBLIC_AGGREGATE'):
        self.pub.validate_aggregate({key:1})

  def test_real_aggregate_accepted(self):
    one,_=module().one_step(one_fixture())
    roll,_=module().rollout(roll_fixture())
    self.pub.validate_aggregate(one)
    self.pub.validate_aggregate(roll)

  def test_nonfinite_public_rejected(self):
    with self.assertRaisesRegex(ValueError,'PUBLIC_AGGREGATE'):
      self.pub.validate_aggregate({'count':float('inf')})


if __name__ == '__main__':
  unittest.main()
