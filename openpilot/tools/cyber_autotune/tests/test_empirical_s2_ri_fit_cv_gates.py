"""Frozen directional gate tests with synthetic metric fixtures only."""
import copy
import unittest

from openpilot.tools.cyber_autotune import empirical_s2_ri_fit_cv_gates as g
from openpilot.tools.cyber_autotune import empirical_s2_ri_fit_cv_math as m


def population(grid=False):
  a={'rmse':.5,'mae':.5,'p95':.5}
  b={'rmse':1.,'mae':1.,'p95':1.}
  if grid:
    a.update(exact_hit=.8,within_one_tick=1.)
    b.update(exact_hit=.7,within_one_tick=.9)
  return {'count':300,'anchor_sha256':'a'*64,'comparator_anchor_sha256':'a'*64,'candidate':a,'comparator':b}


def job(cid,fold):
  return {'candidate_id':cid,'fold':fold,'status':'PASS','one_step':population(True),
          'rollout':{str(h):population() for h in m.HORIZONS}}


class TestFrozenGates(unittest.TestCase):
  def test_every_metric_on_every_fold_is_required(self):
    for scope in ('one_step',*[str(h) for h in m.HORIZONS]):
      for key in ('rmse','mae','p95'):
        j=job(m.CANDIDATES[0],'FOLD_A')
        pop=j[scope] if scope=='one_step' else j['rollout'][scope]
        pop['candidate'][key]=1.1
        with self.subTest(scope=scope,key=key):
          self.assertFalse(g.fold_gate(j)['pass'])

  def test_strict_one_step_not_all_ties(self):
    j=job(m.CANDIDATES[0],'FOLD_A')
    j['one_step']['candidate']['rmse']=1.
    self.assertFalse(g.fold_gate(j)['pass'])

  def test_grid_nonworse_both_required(self):
    for key in ('exact_hit','within_one_tick'):
      j=job(m.CANDIDATES[0],'FOLD_A')
      j['one_step']['candidate'][key]=0.
      self.assertFalse(g.fold_gate(j)['pass'])

  def test_anchor_support_and_finite_firewall(self):
    for mutation in ('anchor','support','nan','negative','extra','missing_horizon'):
      j=job(m.CANDIDATES[0],'FOLD_A')
      if mutation=='anchor':
        j['one_step']['comparator_anchor_sha256']='b'*64
      elif mutation=='support':
        j['rollout']['200']['count']=200
      elif mutation=='nan':
        j['one_step']['candidate']['rmse']=float('nan')
      elif mutation=='negative':
        j['one_step']['candidate']['mae']=-1.
      elif mutation=='extra':
        j['one_step']['candidate']['epsilon']=.01
      else:
        del j['rollout']['25']
      with self.subTest(mutation=mutation),self.assertRaises(ValueError):
        g.fold_gate(j)

  def test_failure_cannot_be_overridden(self):
    j=job(m.CANDIDATES[0],'FOLD_A')
    j['status']='NUMERICAL_FAILURE'
    self.assertFalse(g.fold_gate(j)['pass'])

  def test_zero_denominator(self):
    self.assertEqual(g.ratio(0.,0.),1.)
    self.assertEqual(g.ratio(1.,0.),float('inf'))
    for a,b in ((-1.,0.),(float('nan'),1.)):
      with self.assertRaises(ValueError):
        g.ratio(a,b)

  def test_complete_accounting_no_17th_or_fold_swap(self):
    jobs=[job(c,f) for c in m.CANDIDATES for f in ('FOLD_A','FOLD_B')]
    for changed in (jobs[:-1],jobs+[copy.deepcopy(jobs[-1])],jobs[::-1]):
      with self.assertRaises(ValueError):
        g.select(changed)

  def test_all_ties_fail_closed_no_selection(self):
    jobs=[job(c,f) for c in m.CANDIDATES for f in ('FOLD_A','FOLD_B')]
    for j in jobs:
      j['one_step']['candidate']['rmse']=1.
    result=g.select(jobs)
    self.assertIsNone(result['selected_candidate'])
    self.assertEqual(result['status'],'S2_RI_NO_ADMISSIBLE_CANDIDATE')

  def test_both_folds_and_lexical_tie_break(self):
    jobs=[job(c,f) for c in m.CANDIDATES for f in ('FOLD_A','FOLD_B')]
    jobs[1]['one_step']['candidate']['rmse']=1.
    result=g.select(jobs)
    self.assertEqual(result['admissible_count'],15)
    self.assertEqual(result['selected_candidate'],'S2RI_D05_L01')

  def test_primary_ranking_precedes_parameter_count(self):
    jobs=[job(c,f) for c in m.CANDIDATES for f in ('FOLD_A','FOLD_B')]
    for j in jobs:
      if j['candidate_id']=='S2RI_D20_L45':
        for pop in j['rollout'].values():
          pop['candidate']['rmse']=.1
    self.assertEqual(g.select(jobs)['selected_candidate'],'S2RI_D20_L45')
