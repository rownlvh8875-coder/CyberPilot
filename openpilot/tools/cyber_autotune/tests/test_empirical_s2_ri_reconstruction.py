"""Frozen model replay tests use constructed coefficients, never fitting."""
import unittest
import numpy as np
from openpilot.tools.cyber_autotune import empirical_s2_ri_reconstruction_math as r
from openpilot.tools.cyber_autotune import empirical_s2_ri_fit_cv_math as old


def model(length=1):
  n = 2*length+3
  return {'coefficients':np.arange(n,dtype=np.float64)/100000,
          'normalizer':{'mean':np.zeros(n),'std':np.ones(n),'effective':np.arange(n),'constant':np.zeros(n,bool)}}


def segment(n=250):
  return {'segment_sha256':'a'*64,'route_id':'b'*64,'tick':(np.arange(n)%17-8).astype(np.int64),
          'streak':np.arange(1,n+1),'command':np.full(n,.2),'speed':np.full(n,20.),
          'rail':np.zeros(n,bool),'eligible':np.ones(n,bool),'run':np.zeros(n,dtype=np.int64),
          'within':np.arange(n,dtype=np.int64)}


class TestReplay(unittest.TestCase):
  def test_no_refit(self):
    with r.firewall():
      for fn in (old.fit,old.normalizer,np.linalg.lstsq,np.linalg.solve,np.linalg.pinv):
        with self.assertRaisesRegex(ValueError,'REFIT_FORBIDDEN'):
          fn(None)
      self.assertEqual(len(old.predict(np.ones((2,5)),model())),2)

  def test_one_step_bytes_and_direct_targets(self):
    s=segment()
    ix=old.anchors(s,'S2RI_D00_L01',1)
    arrays,metrics=r.one_step([(s,ix)],'S2RI_D00_L01',model())
    expected,buffers=old.one_step(old.features(s,ix,'S2RI_D00_L01'),s['tick'][ix],s['tick'][ix+1],model())
    self.assertEqual(expected,metrics)
    for key in buffers:
      r.exact(arrays[key],buffers[key],'ONE_STEP')
    np.testing.assert_array_equal(arrays['current_tick'],s['tick'][ix])
    np.testing.assert_array_equal(arrays['target_next_tick'],s['tick'][ix+1])
    np.testing.assert_array_equal(arrays['actual_delta_tick'],np.diff(s['tick'])[ix])

  def test_recursive_paths_exact_endpoints(self):
    for h in old.HORIZONS:
      ticks=np.array([[1,2],[2,3]],dtype=np.int64)
      command=np.full((2,h),.2)
      speed=np.full((2,h),20.)
      path=r.recursive_path(ticks,command,speed,'S2RI_D00_L01',model(),h)
      r.exact(path[:,-1].copy(),old.recursive(ticks,command,speed,'S2RI_D00_L01',model(),h),'ROLLOUT')
      np.testing.assert_array_equal(path[:,0],ticks[:,-1])
      self.assertEqual(path.shape,(2,h+1))

  def test_exact_checks_dtype_shape_bytes(self):
    for value in (np.array([1],dtype=np.int32),np.array([[1]],dtype=np.int64),np.array([2],dtype=np.int64)):
      with self.assertRaisesRegex(ValueError,'DIVERGENCE'):
        r.exact(value,np.array([1],dtype=np.int64),'ONE_STEP')

  def test_rate_context_independence(self):
    base=segment()
    ix=old.anchors(base,'S2RI_D00_L01',1)
    expected,_=r.one_step([(base,ix)],'S2RI_D00_L01',model())
    for rate in (np.full(250,np.nan),np.arange(250)*7.):
      actual,_=r.one_step([({**base,'state.rate':rate,'state.rate.available':np.isfinite(rate)},ix)],'S2RI_D00_L01',model())
      self.assertEqual(set(expected),set(actual))
      for key in expected:
        r.exact(actual[key],expected[key],'RATE')

  def test_context_direct(self):
    s=segment()
    ix=np.array([5,10])
    c=r.context([(s,ix)],'S2RI_D05_L01')
    np.testing.assert_array_equal(c['prior_delta_tick'],s['tick'][ix]-s['tick'][ix-1])
    np.testing.assert_array_equal(c['command_feature_newest'],s['command'][ix-5])
    self.assertTrue(np.all(c['speed_bin_code']==2))


if __name__=='__main__':
  unittest.main()

import tempfile
from pathlib import Path
from unittest.mock import patch
import pytest
from openpilot.tools.cyber_autotune import empirical_s2_ri_reconstruction as execution
from openpilot.tools.cyber_autotune import empirical_causal_dataset_store as storage
from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_s2_ri_fit_cv_gates as gates


@pytest.mark.parametrize('candidate',old.CANDIDATES)
def test_all_frozen_forms_and_rate_free_rollout(candidate):
  d,length=old.parameters(candidate)
  s=segment(550)
  expected=None
  for rate in (None,np.full(550,np.nan),np.arange(550,dtype=float)):
    view=dict(s)
    if rate is not None:
      view.update({'state.rate':rate,'state.rate.available':np.isfinite(rate)})
    blocks,_,_=r.binding([view],candidate,25)
    with r.firewall():
      result,_=r.rollout(blocks,candidate,model(length),25)
    if expected is None:
      expected=result
    else:
      for key in expected:
        r.exact(result[key],expected[key],'RATE')
    ix=blocks[0][1]
    ticks=s['tick'][ix[:,None]+np.arange(-length,1)]
    command=s['command'][ix[:,None]+np.arange(-d-length+1,25-d)]
    speed=s['speed'][ix[:,None]+np.arange(25)]
    r.exact(result['projected'],old.recursive(ticks,command,speed,candidate,model(length),25),'ROLLOUT')
    np.testing.assert_array_equal(result['observed_path'],s['tick'][ix[:,None]+np.arange(26)])


@pytest.mark.parametrize('horizon',(1,*old.HORIZONS))
def test_anchor_divergence_before_prediction(horizon):
  s=segment(550)
  _,digest,n=r.binding([s],'S2RI_D00_L01',horizon)
  hist={'anchor_sha256':digest,'comparator_anchor_sha256':digest,'count':n}
  r.require_anchor([s],'S2RI_D00_L01',horizon,hist)
  for key in hist:
    bad={**hist,key:0 if key=='count' else '0'*64}
    with patch.object(old,'predict',side_effect=AssertionError('prediction before anchor')):
      with pytest.raises(ValueError,match='ANCHOR_DIVERGENCE'):
        r.require_anchor([s],'S2RI_D00_L01',horizon,bad)


@pytest.mark.parametrize('candidate',('S2RI_D01_L01','S2RI_D00_L02','S2RI_D00_L46'))
def test_candidate_expansion_rejected(candidate):
  with pytest.raises(ValueError,match='FROZEN_CANDIDATE'):
    r.binding([segment()],candidate,1)


def test_context_does_not_change_prediction():
  s=segment()
  ix=old.anchors(s,'S2RI_D00_L01',1)
  expected,_=r.one_step([(s,ix)],'S2RI_D00_L01',model())
  changed={**s,'rail':~s['rail'],'run':s['run']+7,'within':s['within']+20}
  actual,_=r.one_step([(changed,ix)],'S2RI_D00_L01',model())
  for key in execution.ONE_FIELDS:
    r.exact(actual[key],expected[key],'CONTEXT')


def test_future_observed_path_not_feature():
  # Change future observation only: initial history and exogenous remain fixed.
  initial=np.array([[0,1]],dtype=np.int64)
  command=np.zeros((1,25))
  speed=np.full((1,25),20.)
  a=r.recursive_path(initial,command,speed,'S2RI_D00_L01',model(),25)
  with patch.object(old,'fit',side_effect=AssertionError('refit')):
    b=r.recursive_path(initial.copy(),command.copy(),speed.copy(),'S2RI_D00_L01',model(),25)
  r.exact(a,b,'PATH')


@pytest.mark.parametrize('horizon',(25,50,100,200))
def test_no_padding(horizon):
  with pytest.raises(ValueError,match='EXACT_ROLLOUT'):
    r.recursive_path(np.zeros((1,2),dtype=np.int64),np.zeros((1,horizon-1)),np.zeros((1,horizon)),
                     'S2RI_D00_L01',model(),horizon)


def test_qlog_pre_array_rejection():
  auth=p.seal({'frozen_replay_authorized':True,'array_open_before_seal':False,'qlog_deny_content_sha256':['x']})
  with patch.object(execution.read,'read_array',side_effect=AssertionError('array opened')):
    with pytest.raises(ValueError,match='QLOG_CAUSAL_ADMISSION_FORBIDDEN'):
      execution.load_routes([(None,{'segment_sha256':'x'},None,None)],auth)


def test_seal_required_before_array():
  with pytest.raises(ValueError,match='SEALED_REPLAY_AUTHORIZATION'):
    execution.load_routes([],p.seal({'frozen_replay_authorized':False,'array_open_before_seal':False}))


def test_selector_trapped():
  with r.firewall(),pytest.raises(ValueError,match='REFIT_FORBIDDEN'):
    gates.select([])


def test_atomic_no_overwrite_and_traversal():
  with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp)
    storage.atomic_bytes(root/'a',b'a')
    storage.atomic_bytes(root/'a',b'a')
    with pytest.raises(ValueError):
      storage.atomic_bytes(root/'a',b'b')
    with pytest.raises(ValueError):
      storage.safe(root/'..'/'escape')
    (root/'link').symlink_to(root/'a')
    with pytest.raises(ValueError):
      storage.safe(root/'link')


def test_store_overlap():
  with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp)
    with pytest.raises(ValueError):
      storage.external(root/'nested',[root])


def test_policy_authority_and_error_primitive():
  pol=execution.policy()
  assert pol['error_primitive']=='PREDICTED_DELTA_MINUS_OBSERVED_DELTA'
  assert pol['refit_authorized'] is False
  assert pol['failure_attribution']=='NOT_RUN'
  assert pol['hurdle_trigger']=='NOT_EVALUATED'
  assert pol['historical_verdict']=='S2_RI_NO_ADMISSIBLE_CANDIDATE'
  assert pol['opening_count']==0


def test_projection_frozen_half_even():
  np.testing.assert_array_equal(old.project(np.array([-.5,.5,1.5,2.5])),[0,0,2,2])


def test_input_pin_immutable():
  assert execution.historical.INPUT_SHA=='9466e4578842b4c8a300bb843338e53b42a2fc75200879360f8212c7c2605c97'
  assert len(execution.m.CANDIDATES)==16


def test_no_execution_import():
  import sys
  with r.firewall():
    assert sys.modules['openpilot.tools.cyber_autotune.empirical_s2_ri_fit_cv_execution'] is None
    assert sys.modules['openpilot.tools.lib.logreader'] is None
    assert sys.modules['scipy.optimize'] is None


def frozen_job_fixture(root):
  candidate='S2RI_D00_L01'
  fold='FOLD_A'
  s=segment(550)
  path=root/'candidates'/candidate/fold
  norm=model()['normalizer']
  nb={k:storage.array_write(path/'normalizer'/(k+'.npy'),v) for k,v in norm.items()}
  nr=p.seal({'candidate_id':candidate,'fold':fold,'train_route':'c'*64,'arrays':nb})
  execution.store.write_json(path/'normalizer/receipt.json',nr)
  mb={k:storage.array_write(path/'model'/(k+'.npy'),model()['coefficients']) for k in ('coefficients','nominal_coefficients')}
  mr=p.seal({'candidate_id':candidate,'fold':fold,'train_route':'c'*64,
    'normalizer_sha256':nr['receipt_sha256'],'policy_sha256':execution.store.POLICY_SHA,
    'arrays':mb,'numpy_version':'2.5.3','pooled_refit':False})
  execution.store.write_json(path/'model/receipt.json',mr)
  job={'candidate_id':candidate,'fold':fold,'train_route':'c'*64,'development_route':s['route_id'],
    'normalizer_receipt_sha256':nr['receipt_sha256'],'model_receipt_sha256':mr['receipt_sha256'],
    'coefficient_sha256':mb['nominal_coefficients']['array_sha256'],'one_step':None,'rollout':{},
    'one_step_buffers':None,'rollout_buffers':{},'gate':{'pass':False,'failed':['ONE_STEP_MAE']}}
  files=['normalizer/receipt.json','model/receipt.json',*[f'normalizer/{k}.npy' for k in nb],*[f'model/{k}.npy' for k in mb]]
  for h in (1,*old.HORIZONS):
    blocks,digest,n=r.binding([s],candidate,h)
    arrays,metric=r.one_step(blocks,candidate,model()) if h==1 else r.rollout(blocks,candidate,model(),h)
    name='one-step' if h==1 else f'rollout-{h}'
    keys=execution.ONE_FIELDS if h==1 else execution.ROLL_FIELDS
    sha={}
    for key in keys:
      sha[key]=storage.array_write(path/name/(key+'.npy'),arrays[key])['array_sha256']
      files.append(name+'/'+key+'.npy')
    metric.update(count=n,anchor_sha256=digest,comparator_anchor_sha256=digest)
    if h==1:
      job.update(one_step=metric,one_step_buffers=sha)
    else:
      job['rollout'][str(h)]=metric
      job['rollout_buffers'][str(h)]=sha
  job=p.seal(job)
  execution.store.write_json(path/'receipt.json',job)
  execution.store.finish(path,[*files,'receipt.json'],{})
  return job,s


def test_job_persistence_and_trapped_resume():
  with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp)
    job,s=frozen_job_fixture(root/'fit')
    auth=p.seal({'schema':'TEST_AUTH'})
    with r.firewall():
      result=execution.job_run(root/'new',root/'fit',job,[s],auth)
    with patch.object(execution,'load_model',side_effect=AssertionError('model reloaded')), \
         patch.object(r,'one_step',side_effect=AssertionError('prediction repeated')), \
         patch.object(r,'rollout',side_effect=AssertionError('rollout repeated')), \
         patch.object(execution.read,'read_array',side_effect=AssertionError('array decoded')):
      resumed=execution.job_run(root/'new',root/'fit',job,[s],auth)
    assert result==resumed
    assert result['context_complete'] and result['path_complete']


@pytest.mark.parametrize('part',('model','normalizer'))
def test_modified_frozen_array_rejected(part):
  with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp)
    job,_=frozen_job_fixture(root)
    path=root/'candidates'/job['candidate_id']/job['fold']/part
    name='coefficients.npy' if part=='model' else 'mean.npy'
    (path/name).write_bytes(b'changed')
    with pytest.raises(ValueError,match='HASH_CONFLICT'):
      execution.load_model(path.parent,job)


def test_missing_model_rejected():
  with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp)
    job,_=frozen_job_fixture(root)
    path=root/'candidates'/job['candidate_id']/job['fold']
    (path/'model/coefficients.npy').unlink()
    with pytest.raises(FileNotFoundError):
      execution.load_model(path,job)


@pytest.mark.parametrize('field',('prediction','projected','error','comparator_error'))
def test_original_buffer_divergence(field):
  with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp)
    a=np.array([1.,2.])
    b=storage.array_write(root/(field+'.npy'),a)
    with pytest.raises(ValueError,match='ONE_STEP_DIVERGENCE'):
      execution.compare_original(root,{field:a+1},{field:b['array_sha256']},
                                  {field+'.npy':b['file_sha256']},'ONE_STEP')


def test_mutated_frozen_anchor_rejected_before_model_load():
  with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp)
    job,s=frozen_job_fixture(root/'fit')
    job['rollout']['200']['anchor_sha256']='0'*64
    with patch.object(execution,'load_model',side_effect=AssertionError('too early')):
      with pytest.raises(ValueError,match='ANCHOR_DIVERGENCE'):
        execution.job_run(root/'new',root/'fit',job,[s],p.seal({}))


def test_prediction_not_used_for_target():
  s=segment()
  ix=old.anchors(s,'S2RI_D00_L01',1)
  a,_=r.one_step([(s,ix)],'S2RI_D00_L01',model())
  changed=model()
  changed['coefficients']=changed['coefficients']+0.001
  b,_=r.one_step([(s,ix)],'S2RI_D00_L01',changed)
  for key in ('current_tick','target_next_tick','actual_delta_tick'):
    r.exact(a[key],b[key],'TARGET')


@pytest.mark.parametrize('key,value',[
  ('dtype','|O'),('shape',{'private_payload':'SECRET'}),('order','F'),('array_sha256','b'*64)])
def test_resume_array_binding_tamper(key,value):
  with tempfile.TemporaryDirectory() as tmp:
    path=Path(tmp)/'array.npy'
    binding=storage.array_write(path,np.array([1,2],dtype=np.int64))
    with pytest.raises(ValueError):
      execution.verify_array_bytes(path,{**binding,key:value})


def test_resume_payload_hash_connected_to_historical():
  with tempfile.TemporaryDirectory() as tmp:
    path=Path(tmp)/'array.npy'
    binding=storage.array_write(path,np.array([1,2],dtype=np.int64))
    with pytest.raises(ValueError,match='DIVERGENCE'):
      execution.verify_array_bytes(path,binding,original_sha='0'*64)


@pytest.mark.parametrize('horizon',old.HORIZONS)
def test_every_projected_path_step_nonconstant(horizon):
  frozen=model()
  frozen['coefficients']=np.array([1.,0.,0.,0.,0.])
  initial=np.array([[-3,-2],[6,7]],dtype=np.int64)
  command=np.zeros((2,horizon))
  speed=np.full((2,horizon),20.)
  with r.firewall():
    path=r.recursive_path(initial,command,speed,'S2RI_D00_L01',frozen,horizon)
  expected=initial[:,-1,None]+np.arange(horizon+1)
  np.testing.assert_array_equal(path,expected)
  r.exact(path[:,-1].copy(),old.recursive(initial,command,speed,'S2RI_D00_L01',frozen,horizon),'ROLLOUT')
