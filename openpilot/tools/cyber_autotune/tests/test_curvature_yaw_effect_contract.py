import copy
import unittest
from openpilot.tools.cyber_autotune import curvature_yaw_effect_contract as effects


class TestEffectContract(unittest.TestCase):
  def frames(self,k):
    return [{'time_ns':i*10_000_000,'speed_mps':15.,'desired_curvature_1pm':k} for i in range(4)]

  def test_two_by_two_freezes_controller_and_input_effects_without_lane_claim(self):
    a=effects.input_manifest(self.frames(.0001),source_role='SYNTHETIC_GENERATOR',source_sha256='a'*64)
    b=effects.input_manifest(self.frames(.0002),source_role='OFFLINE_MODEL_OUTPUT',source_sha256='b'*64)
    result=effects.freeze_experiment(['c'*64,'d'*64],[a,b])
    self.assertEqual(len(result['trials']),4)
    self.assertFalse(result['lane_quality_judgment_permitted'])
    self.assertEqual(result['path_truth_status'],'NOT_PROVIDED')
    self.assertEqual(result,effects.freeze_experiment(['c'*64,'d'*64],[a,b]))
    self.assertNotEqual(a['receipt_sha256'],b['receipt_sha256'])

  def test_no_false_independent_source_role_or_malformed_timebase(self):
    with self.assertRaises(ValueError):
      effects.input_manifest(self.frames(.0001),source_role='INDEPENDENT_LANE_TRUTH',source_sha256='a'*64)
    bad=self.frames(.0001)
    bad[-1]['time_ns']+=1
    with self.assertRaises(ValueError):
      effects.input_manifest(bad,source_role='SYNTHETIC_GENERATOR',source_sha256='a'*64)

  def test_rehashed_input_and_same_controller_pair_fail_closed(self):
    a=effects.input_manifest(self.frames(.0001),source_role='SYNTHETIC_GENERATOR',source_sha256='a'*64)
    b=copy.deepcopy(a)
    b['frames'][0]['speed_mps']=float('nan')
    with self.assertRaises(ValueError):
      effects.freeze_experiment(['c'*64,'d'*64],[a,b])
    with self.assertRaises(ValueError):
      effects.freeze_experiment(['c'*64,'c'*64],[a,a])
