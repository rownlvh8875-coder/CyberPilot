import unittest
from openpilot.tools.cyber_autotune import private_pixel_cache_audit as audit
from openpilot.tools.cyber_autotune.lane_tail_report import seal


class TestCompletedCacheAudit(unittest.TestCase):
  def test_integer_dictionary_keys_equal_json_string_keys(self):
    first = seal({'counts':{0:37,1:9,2:49,3:96,4:49}})
    loaded = seal({'counts':{'0':37,'1':9,'2':49,'3':96,'4':49}})
    self.assertTrue(audit.require_same_aggregate(first, loaded))

  def test_aggregate_change_cannot_be_normalized_away(self):
    with self.assertRaises(ValueError):
      audit.require_same_aggregate(seal({'count':240}),seal({'count':239}))

  def test_no_completion_without_marker(self):
    with self.assertRaises(ValueError):
      audit.require_complete_marker(None)

  def test_nonqualification_required(self):
    marker = seal({'storage_status':'COMPLETED','processed':240,'reference_promotable':True})
    with self.assertRaises(ValueError):
      audit.require_complete_marker(marker)

  def test_private_diagnostic_not_a_reference(self):
    from openpilot.tools.cyber_autotune import curvature_yaw_reference_input as reference
    from openpilot.tools.cyber_autotune.native_protocol import canonical
    with self.assertRaises(ValueError):
      reference._decode_payload(canonical(seal({
        'schema': 'PRIVATE_PIXEL_DIAGNOSTIC_PUBLIC_AGGREGATE_V1',
        'qualification_allowed': False, 'sealed_reference_allowed': False,
      })), grant=None, sample_count=1, coverage_policy=None)

  def completed_fixture(self, root):
    from openpilot.tools.cyber_autotune.tests import test_private_pixel_execution as fixture
    from openpilot.tools.cyber_autotune import private_pixel_execution as p, lane_public_storage as s
    case = fixture.TestPrivateExecution()
    case.setUp()
    dev = [r for r in case.manifest['selected'] if r['role']=='DEVELOPMENT']
    store = s.DurableRun(root, case.auth, [r['sample_id'] for r in dev])
    def validator(row):
      p.validate_frame(row, case.manifest, case.auth)
    rows=[]
    for sample in dev:
      row=p.frame_receipt(case.manifest,case.auth,sample['sample_id'],fixture.SHA,
                          {'image_geometry':[330,526],'lane_count':0,'points':[],'lanes':[]})
      store.put(row['ordinal'],row,validator)
      rows.append(row)
    store.complete({'summary.json':p.progress_summary(case.manifest,case.auth,rows)},validator)
    return case,validator

  def test_failed_readonly_audit_never_writes_original_index(self):
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as temp:
      root=Path(temp)
      case,validator=self.completed_fixture(root)
      before={p.name:p.read_bytes() for p in root.glob('*.json')}
      def failing(_row):
        raise ValueError('SYNTHETIC_IMAGE_DRIFT')
      with self.assertRaises(ValueError):
        audit.verify_readonly_cache(root,case.manifest,case.auth,failing)
      self.assertEqual(before,{p.name:p.read_bytes() for p in root.glob('*.json')})

  def test_successful_readonly_audit_no_rewrite(self):
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as temp:
      root=Path(temp)
      case,validator=self.completed_fixture(root)
      before={p.name:p.read_bytes() for p in root.glob('*.json')}
      marker,rows=audit.verify_readonly_cache(root,case.manifest,case.auth,validator)
      self.assertEqual(len(rows),12)
      self.assertEqual(marker['processed'],12)
      self.assertEqual(before,{p.name:p.read_bytes() for p in root.glob('*.json')})
