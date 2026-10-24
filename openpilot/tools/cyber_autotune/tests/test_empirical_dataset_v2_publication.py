import copy
from pathlib import Path
import unittest

from openpilot.tools.cyber_autotune import empirical_plant_policy as p


def fixture():
  from openpilot.tools.cyber_autotune import empirical_dataset_v2_policy as v
  return p.seal({
    'schema':'EMPIRICAL_DATASET_V2_PRIVATE_INVENTORY', 'binding_sha256':'a'*64,
    'snapshot':{'file_counts':{'rlog.zst':95,'qcamera.ts':95,'dcamera.hevc':96},'segments':[{}]*95},
    'routes':[{'route_id':'b'*64,'status':'V1_PLANNING_CONTEXT_ONLY','v1_overlap':True,'segment_count':95}],
    'failures':[], 'split':v.split_routes([]), 'numeric_payloads_opened':False, 'new_numeric_route_count':0,
  })


class TestV2Publication(unittest.TestCase):
  def test_waiting_no_fitting(self):
    from openpilot.tools.cyber_autotune import empirical_dataset_v2_publication as pub
    rows=pub.derive(fixture())
    result=rows['empirical-dataset-v2-readiness.json']
    self.assertEqual(result['status'],'EMPIRICAL_DATASET_V2_WAITING_FOR_NEW_ROUTE_DATA')
    self.assertFalse(result['fitting_performed'])
    self.assertFalse(result['holdout_opened'])

  def test_raw_details_not_published(self):
    from openpilot.tools.cyber_autotune import empirical_dataset_v2_publication as pub
    row=fixture()
    row['snapshot']['segments']=[{'source_key':'SECRET_ROUTE','raw_gyro':[123]}]
    row=p.seal({k:v for k,v in row.items() if k!='receipt_sha256'})
    output=p.canonical(pub.derive(row))
    self.assertNotIn(b'SECRET_ROUTE',output)
    self.assertNotIn(b'raw_gyro',output)

  def test_executed_data_cannot_be_labeled_waiting(self):
    from openpilot.tools.cyber_autotune import empirical_dataset_v2_publication as pub
    row=copy.deepcopy(fixture())
    row['numeric_payloads_opened']=True
    row=p.seal({k:v for k,v in row.items() if k!='receipt_sha256'})
    with self.assertRaises(ValueError):
      pub.derive(row)

  def test_calibration_history_and_authority_unchanged(self):
    from openpilot.tools.cyber_autotune import empirical_dataset_v2_publication as pub
    result=pub.derive(fixture())['empirical-dataset-v2-readiness.json']
    self.assertEqual(result['calibration_blockers'],p.BLOCKERS)
    self.assertEqual(result['historical']['v2'],'REJECTED')
    self.assertFalse(result['ta_execution'])
    self.assertFalse(result['sg_execution'])
    self.assertFalse(result['vehicle_activation_allowed'])

  def test_passive_guide(self):
    root=Path(__file__).resolve().parents[4]
    text=(root/'docs/cyberpilot/changes/empirical-dataset-v2-readiness.md').read_text()
    for fragment in ('normal, legal','Do not make sharp','artificial','Traffic','different dates'):
      self.assertIn(fragment,text)


if __name__ == '__main__':
  unittest.main()


class TestV2PrivacyBoundary(unittest.TestCase):
  def test_private_status_string_rejected(self):
    from openpilot.tools.cyber_autotune import empirical_dataset_v2_publication as pub
    row=fixture()
    row['routes'][0]['status']='PRIVATE_PATH_SECRET'
    row=p.seal({k:v for k,v in row.items() if k!='receipt_sha256'})
    with self.assertRaises(ValueError):
      pub.derive(row)

  def test_count_cannot_be_private_string(self):
    from openpilot.tools.cyber_autotune import empirical_dataset_v2_publication as pub
    row=fixture()
    row['routes'][0]['segment_count']='SECRET'
    row=p.seal({k:v for k,v in row.items() if k!='receipt_sha256'})
    with self.assertRaises(ValueError):
      pub.derive(row)


class TestFrozenV2Receipts(unittest.TestCase):
  def test_public_receipts_and_historical_pins(self):
    from openpilot.tools.cyber_autotune import empirical_dataset_v2_publication as pub
    rows=pub.load()
    self.assertEqual(len(rows),6)
    self.assertEqual(rows['empirical-dataset-v2-route-inventory.json']['new_compatible_untouched_routes'],0)

  def test_resealed_public_tamper_rejected(self):
    from openpilot.tools.cyber_autotune import empirical_dataset_v2_publication as pub
    rows=pub.load()
    original=rows['empirical-dataset-v2-readiness.json']
    from unittest.mock import patch
    tampered=p.seal({k:v for k,v in original.items() if k!='receipt_sha256'} | {'holdout_opened':True})
    reader=pub.inv.read
    with patch.object(pub.inv,'read',side_effect=lambda path: tampered if path.name=='empirical-dataset-v2-readiness.json' else reader(path)):
      with self.assertRaisesRegex(ValueError,'IMMUTABLE'):
        pub.load()
