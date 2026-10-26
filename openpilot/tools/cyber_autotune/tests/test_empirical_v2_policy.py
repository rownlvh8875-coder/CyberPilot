import copy
import tempfile
from pathlib import Path
import unittest

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_source_publication as old
from openpilot.tools.cyber_autotune import empirical_v2_policy as v


def bindings(public):
  return copy.deepcopy(v.ROUTE_BINDINGS)


def make_split(public):
  return v.split(public, bindings(public))


class TestV2Policy(unittest.TestCase):
  def test_exact_three_lexical_roles(self):
    public = old.load()
    split = make_split(public)
    self.assertEqual([r['role'] for r in split['routes']], ['TRAIN', 'TRAIN', 'DEVELOPMENT'])
    self.assertEqual([r['route_id'] for r in split['routes']], sorted(r['route_id'] for r in split['routes']))
    self.assertFalse(split['numeric_opened_before_split'])
    self.assertFalse(split['holdout_allowed'])

  def test_partial_route_rejected(self):
    public = copy.deepcopy(old.load())
    x = public['empirical-source-route-reclassification-v1.json']
    rid = x['pools']['pools'][0]['route_ids'][0]
    next(r for r in x['routes'] if r['route_id'] == rid)['signal_semantics_complete'] = False
    public['empirical-source-route-reclassification-v1.json'] = p.seal({k: val for k, val in x.items() if k != 'receipt_sha256'})
    with self.assertRaises(ValueError):
      make_split(public)

  def test_no_other_role(self):
    split = make_split(old.load())
    for role in ('HOLDOUT', 'EMBARGO', 'TRAIN_CANDIDATE'):
      bad = copy.deepcopy(split)
      bad['routes'][0]['role'] = role
      bad = p.seal({k: val for k, val in bad.items() if k != 'receipt_sha256'})
      with self.subTest(role=role), self.assertRaises(ValueError):
        v.validate_split(bad)

  def test_policy_unchanged(self):
    policy = v.policy()
    self.assertEqual(policy['minimum_development_rows'], 201)
    self.assertEqual(policy['family_policy'], p.family_policy())
    self.assertEqual(policy['alignment_policy'], p.alignment_policy())
    self.assertEqual(policy['metric_policy'], p.metric_policy())
    self.assertEqual(policy['data_policy'], p.policy())
    self.assertFalse(policy['holdout_opening_allowed'])

  def test_missing_persisted_authorization_cannot_open(self):
    with tempfile.TemporaryDirectory() as directory:
      with self.assertRaises((ValueError, FileNotFoundError)):
        v.require_open(Path(directory), '0'*64, '0'*64, '0'*64)

  def test_future_package_stays_closed(self):
    package = v.holdout_package(make_split(old.load()), {}, '0'*64)
    self.assertEqual(package['one_time_opening_state'], 'CLOSED')
    self.assertEqual(package['future_holdout'], 'FUTURE_UNTOUCHED_HOLDOUT_REQUIRED')
    for name in ('reselection_allowed', 'refit_allowed', 'threshold_change_allowed'):
      self.assertFalse(package[name])

  def test_forged_route_set_rejected(self):
    frozen=make_split(old.load())
    for i,row in enumerate(frozen['routes']):
      row['route_id']=str(i)*64
    frozen=p.seal({k:val for k,val in frozen.items() if k!='receipt_sha256'})
    with self.assertRaises(ValueError):
      v.validate_split(frozen)

  def test_source_set_tamper_rejected(self):
    frozen=make_split(old.load())
    frozen['routes'][0]['source_set_sha256']='0'*64
    frozen=p.seal({k:val for k,val in frozen.items() if k!='receipt_sha256'})
    with self.assertRaises(ValueError):
      v.validate_split(frozen)
