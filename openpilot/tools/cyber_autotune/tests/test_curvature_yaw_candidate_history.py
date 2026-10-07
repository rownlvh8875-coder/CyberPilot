import copy
import unittest
from openpilot.tools.cyber_autotune import curvature_yaw_candidate_history as history
from openpilot.tools.cyber_autotune.native_protocol import canonical,digest


class TestCandidateHistory(unittest.TestCase):
  def entry(self,name,status='REFERENCE'):
    return {'candidate':name,'status':status,'alias_of':None,'source_sha256':'a'*64,'config_sha256':'b'*64,
            'search_policy_sha256':None,'result_sha256':'c'*64,'scenario_set':['synthetic'],
            'rejection_reasons':[],'robustness_result':None,'qualification_status':history.QUALIFICATION}

  def test_append_does_not_mutate_and_preserves_hash_chain(self):
    a=history.append_history([],self.entry('BASELINE'),expected_parent_sha256=None)
    old=copy.deepcopy(a)
    b=history.append_history(a,self.entry('V1','TRADEOFF_ONLY'),expected_parent_sha256=a[-1]['record_sha256'])
    self.assertEqual(a,old)
    self.assertEqual(b[:1],a)
    history.validate_history(b)

  def test_duplicate_or_rejected_resurrection_fails(self):
    a=history.append_history([],self.entry('V2','REJECTED'),expected_parent_sha256=None)
    with self.assertRaises(ValueError):
      history.append_history(a,self.entry('V2','SCREENING_IMPROVED'),expected_parent_sha256=a[-1]['record_sha256'])
    with self.assertRaises(ValueError):
      history.append_history(a,self.entry('V3'),expected_parent_sha256='d'*64)

  def test_rehashed_bad_qualification_or_empty_evidence_rejected(self):
    for key,value in (('qualification_status','REAL_WORLD_IMPROVED'),('source_sha256',None),('status','ACCEPTED_FOR_VEHICLE')):
      entry=self.entry('V2')
      entry[key]=value
      with self.assertRaises(ValueError):
        history.append_history([],entry,expected_parent_sha256=None)

  def test_current_alias_requires_same_source_config_result(self):
    a=history.append_history([],self.entry('BASELINE'),expected_parent_sha256=None)
    current=self.entry('CURRENT')
    current['alias_of']='BASELINE'
    b=history.append_history(a,current,expected_parent_sha256=a[-1]['record_sha256'])
    history.validate_history(b)
    current['config_sha256']='d'*64
    with self.assertRaises(ValueError):
      history.append_history(a,current,expected_parent_sha256=a[-1]['record_sha256'])

  def test_history_change_invalidates_descendant_parent(self):
    a=history.append_history([],self.entry('BASELINE'),expected_parent_sha256=None)
    b=history.append_history(a,self.entry('V1'),expected_parent_sha256=a[-1]['record_sha256'])
    b[0]['entry']['source_sha256']='f'*64
    b[0]['record_sha256']=digest(canonical({k:v for k,v in b[0].items() if k!='record_sha256'}))
    with self.assertRaises(ValueError):
      history.validate_history(b)
