import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_s2_ri_fit_cv_execution as e
from openpilot.tools.cyber_autotune import empirical_s2_ri_fit_cv_math as m
from openpilot.tools.cyber_autotune import empirical_s2_ri_fit_cv_store as s


def synthetic_segment(identity,n=600):
  k=np.arange(n)
  # Test-only deterministic fixture, never empirical data or a candidate result.
  return {'segment_sha256':identity,'tick':((k*k*7+k*3)%131).astype(np.int64),
    'command':np.sin(k*k*.13),'speed':20+np.cos(k*.19),'streak':k+1}


class TestExecution(unittest.TestCase):
  def test_segment_boundary_never_concatenates_history(self):
    blocks,digest,count=e.anchor_binding([synthetic_segment('a'*64,10),synthetic_segment('b'*64,10)],'S2RI_D00_L05',1)
    self.assertEqual(count,8)
    self.assertEqual(len(digest),64)
    for _,indices in blocks:
      np.testing.assert_array_equal(indices,np.arange(5,9))

  def test_qlog_rejected_before_first_array_access(self):
    auth=p.seal({'retrospective_fit_cv_authorized':True,'array_access_before_seal':False,
                 'qlog_deny_content_sha256':['a'*64],'routes':[]})
    with patch.object(e.read,'read_array',side_effect=AssertionError('NO_ARRAY_OPEN')),self.assertRaisesRegex(ValueError,'QLOG'):
      e.load_routes([(None,{'segment_sha256':'a'*64},None,None)],auth)

  def test_unsealed_authorization_rejected_before_array(self):
    with patch.object(e.read,'read_array',side_effect=AssertionError('NO_ARRAY_OPEN')),self.assertRaises(ValueError):
      e.load_routes([],{'retrospective_fit_cv_authorized':True})

  def test_synthetic_job_has_private_model_and_exact_resume(self):
    with tempfile.TemporaryDirectory() as root:
      path=Path(root)
      cid=m.CANDIDATES[0]
      fold={'name':'FOLD_A','train':'a'*64,'development':'b'*64}
      auth=p.seal({'candidate_pins':{cid:'c'*64}})
      routes={'a'*64:[synthetic_segment('d'*64)],'b'*64:[synthetic_segment('e'*64)]}
      result=e.execute_job(path,cid,fold,routes,auth)
      self.assertTrue(result['solver_executed'])
      self.assertEqual(result['status'],'PASS')
      self.assertEqual(set(result['rollout']),{'25','50','100','200'})
      for pop in (result['one_step'],*result['rollout'].values()):
        self.assertEqual(pop['anchor_sha256'],pop['comparator_anchor_sha256'])
      with patch.object(e,'design',side_effect=AssertionError('NO_COMPUTE')),patch.object(m,'fit',side_effect=AssertionError('NO_FIT')):
        self.assertEqual(e.execute_job(path,cid,fold,routes,auth),result)

  def test_insufficient_support_receipt_not_silent_skip(self):
    with tempfile.TemporaryDirectory() as root:
      cid=m.CANDIDATES[-1]
      fold={'name':'FOLD_A','train':'a'*64,'development':'b'*64}
      auth=p.seal({'candidate_pins':{cid:'c'*64}})
      routes={r:[synthetic_segment('d'*64,10)] for r in (fold['train'],fold['development'])}
      result=e.execute_job(Path(root),cid,fold,routes,auth)
      self.assertEqual(result['status'],'INSUFFICIENT_SUPPORT')
      self.assertFalse(result['gate']['pass'])
      self.assertTrue((Path(root)/'candidates'/cid/'FOLD_A/receipt.json').is_file())


  def test_post_solver_failure_is_accounted(self):
    with tempfile.TemporaryDirectory() as root:
      cid=m.CANDIDATES[0]
      fold={'name':'FOLD_A','train':'a'*64,'development':'b'*64}
      auth=p.seal({'candidate_pins':{cid:'c'*64}})
      routes={r:[synthetic_segment('d'*64)] for r in (fold['train'],fold['development'])}
      with patch.object(np.linalg,'lstsq',return_value=(np.ones(5),np.array([]),1,np.ones(5))):
        result=e.execute_job(Path(root),cid,fold,routes,auth)
      self.assertEqual(result['status'],'NUMERICAL_FAILURE')
      self.assertTrue(result['solver_executed'])

  def test_resume_stale_job_authorization_rejected(self):
    with tempfile.TemporaryDirectory() as root:
      cid=m.CANDIDATES[0]
      fold={'name':'FOLD_A','train':'a'*64,'development':'b'*64}
      auth=p.seal({'candidate_pins':{cid:'c'*64}})
      routes={r:[synthetic_segment('d'*64,10)] for r in (fold['train'],fold['development'])}
      e.execute_job(Path(root),cid,fold,routes,auth)
      with self.assertRaisesRegex(ValueError,'RESUME_JOB_IDENTITY'):
        e.execute_job(Path(root),cid,fold,routes,p.seal({'different':'authorization'}))

  def test_readonly_resume_entire_run_traps_loader_and_fit(self):
    with tempfile.TemporaryDirectory() as root:
      output=Path(root)
      folds=[{'name':'FOLD_A','train':'a'*64,'development':'b'*64},
             {'name':'FOLD_B','train':'b'*64,'development':'a'*64}]
      auth=p.seal({'retrospective_fit_cv_authorized':True,'candidate_pins':dict.fromkeys(m.CANDIDATES,'c'*64)})
      bundle={'empirical-s2-ri-fitting-policy-v1.json':{'folds':folds}}
      routes={r:[synthetic_segment('d'*64,2)] for r in ('a'*64,'b'*64)}
      with patch.object(s,'admit',return_value=(auth,bundle,[],{},{})),patch.dict('os.environ',{'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1'}):
        with patch.object(e,'load_routes',return_value=routes):
          result=e.run(output,output,output,'repeat-1')
        with patch.object(e,'load_routes',side_effect=AssertionError('NO_ARRAY')),patch.object(m,'fit',side_effect=AssertionError('NO_FIT')):
          self.assertEqual(e.run(output,output,output,'repeat-1'),result)
        with patch.object(s,'admit',return_value=(p.seal({'other':'authorization'}),bundle,[],{},{})),self.assertRaises(ValueError):
          e.run(output,output,output,'repeat-1')
