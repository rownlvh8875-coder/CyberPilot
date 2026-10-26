import tempfile
from pathlib import Path
import unittest

from openpilot.tools.cyber_autotune import empirical_plant_policy as p


class TestV2Inventory(unittest.TestCase):
  def test_only_logs_are_hashed_media_never_opened(self):
    from openpilot.tools.cyber_autotune import empirical_dataset_v2_inventory as v
    with tempfile.TemporaryDirectory() as d:
      root = Path(d)
      segment = root / 'route--0'
      segment.mkdir()
      (segment/'rlog.zst').write_bytes(b'log')
      (segment/'qcamera.ts').write_bytes(b'media')
      row = v.scan_tree(root)
      self.assertEqual(len(row['segments']), 1)
      self.assertEqual(row['file_counts']['qcamera.ts'], 1)
      self.assertEqual(row['segments'][0]['source_sha256'], p.sha(b'log'))

  def test_symlink_rejected(self):
    from openpilot.tools.cyber_autotune import empirical_dataset_v2_inventory as v
    with tempfile.TemporaryDirectory() as d:
      root = Path(d)
      (root/'alias').symlink_to('/tmp', target_is_directory=True)
      with self.assertRaises(ValueError):
        v.scan_tree(root)

  def test_unknown_log_layout_rejected(self):
    from openpilot.tools.cyber_autotune import empirical_dataset_v2_inventory as v
    with tempfile.TemporaryDirectory() as d:
      (Path(d)/'rlog.zst').write_bytes(b'x')
      with self.assertRaisesRegex(ValueError, 'LINEAGE'):
        v.scan_tree(Path(d))

  def test_route_grouping_uses_logger_start_not_name(self):
    from openpilot.tools.cyber_autotune import empirical_dataset_v2_inventory as v
    from openpilot.tools.cyber_autotune import empirical_dataset_v2_policy as policy
    rows = [
      {'source_sha256': p.sha(str(i).encode()), 'lineage_sha256': p.sha(str(i).encode()), 'ordinal': i,
           'metadata': {'generation': policy.expected_generation(), 'logger_start_sha256': 'a'*64,
                         'first_ns': 100+i*100, 'last_ns': 199+i*100, 'envelope_counts': {'carState': 10, 'carOutput': 10, 'carControl': 10}}}
      for i in range(2)
    ]
    result = v.group_routes(rows, set(), set())
    self.assertEqual(len(result), 1)
    self.assertEqual(result[0]['segment_count'], 2)
    self.assertEqual(result[0]['status'], 'ROUTE_METADATA_COMPATIBLE')

  def test_v1_lineage_excludes_whole_route(self):
    from openpilot.tools.cyber_autotune import empirical_dataset_v2_inventory as v
    from openpilot.tools.cyber_autotune import empirical_dataset_v2_policy as policy
    row = {'source_sha256': 'a'*64, 'lineage_sha256': 'b'*64, 'ordinal': 0,
               'metadata': {'generation': policy.expected_generation(), 'logger_start_sha256': 'c'*64,
                             'first_ns': 1, 'last_ns': 9, 'envelope_counts': {'carState': 2, 'carOutput': 2}}}
    self.assertTrue(v.group_routes([row], set(), {'b'*64})[0]['v1_overlap'])

  def test_overlap_cannot_count_as_two_routes(self):
    from openpilot.tools.cyber_autotune import empirical_dataset_v2_inventory as v
    from openpilot.tools.cyber_autotune import empirical_dataset_v2_policy as policy
    rows = [{'source_sha256': p.sha(str(i).encode()), 'lineage_sha256': 'b'*64, 'ordinal': i,
                 'metadata': {'generation': policy.expected_generation(), 'logger_start_sha256': str(i)*64,
                               'first_ns': 1, 'last_ns': 9, 'envelope_counts': {'carState': 2, 'carOutput': 2}}} for i in range(2)]
    self.assertTrue(all(x['status'] == 'ROUTE_IDENTITY_AMBIGUOUS' for x in v.group_routes(rows, set(), set())))

  def test_atomic_cache_recovery_before_parse(self):
    from openpilot.tools.cyber_autotune import empirical_dataset_v2_inventory as v
    with tempfile.TemporaryDirectory() as d:
      target=Path(d)/'receipt.json'
      row=p.seal({'schema':'TEST', 'binding_sha256':'a'*64})
      p.persist(target.with_name('receipt.json.atomic'),row)
      self.assertEqual(v.cached(target, 'a'*64),row)
      self.assertTrue(target.exists())

  def test_stale_cache_rejected(self):
    from openpilot.tools.cyber_autotune import empirical_dataset_v2_inventory as v
    with tempfile.TemporaryDirectory() as d:
      target=Path(d)/'receipt.json'
      p.persist(target,p.seal({'schema':'TEST', 'binding_sha256':'a'*64}))
      with self.assertRaisesRegex(ValueError,'STALE'):
        v.cached(target,'b'*64)


if __name__ == '__main__':
  unittest.main()


class TestRouteIdentityIntegrity(unittest.TestCase):
  def test_arriving_segments_do_not_rename_route(self):
    from openpilot.tools.cyber_autotune import empirical_dataset_v2_inventory as v
    from openpilot.tools.cyber_autotune import empirical_dataset_v2_policy as policy
    rows = [{'source_sha256':p.sha(str(i).encode()), 'lineage_sha256':'b'*64, 'ordinal':i,
             'metadata':{'generation':policy.expected_generation(), 'logger_start_sha256':'a'*64,
                         'first_ns':100*i, 'last_ns':100*i+99,
                         'envelope_counts':{'carState':10,'carOutput':10,'carControl':10}}} for i in range(2)]
    self.assertEqual(v.group_routes(rows[:1],set(),set())[0]['route_id'],
                     v.group_routes(rows,set(),set())[0]['route_id'])

  def test_old_logger_start_excludes_renamed_new_segment(self):
    from openpilot.tools.cyber_autotune import empirical_dataset_v2_inventory as v
    from openpilot.tools.cyber_autotune import empirical_dataset_v2_policy as policy
    rows = [{'source_sha256':'f'*64, 'lineage_sha256':'b'*64, 'ordinal':100,
             'metadata':{'generation':policy.expected_generation(), 'logger_start_sha256':'a'*64,
                         'first_ns':100, 'last_ns':199,
                         'envelope_counts':{'carState':10,'carOutput':10,'carControl':10}}}]
    self.assertTrue(v.group_routes(rows,set(),set(),{'a'*64})[0]['v1_overlap'])


class TestMetadataPayloadFirewall(unittest.TestCase):
  @staticmethod
  def events(regression=False):
    from types import SimpleNamespace as N
    class Event:
      def __init__(self,kind,time,body=None):
        self.kind,self.logMonoTime,self.body=kind,time,body
      def which(self):
        return self.kind
      def __getattr__(self,name):
        if name in ('carState','gpsLocationExternal','modelV2'):
          raise AssertionError('FORBIDDEN_NUMERIC_OR_LOCATION_BODY')
        return self.body
    init=N(gitCommit='a'*40,osVersion='TEST',dirty=False,wallTimeNanos=1000,bootlogId='BOOT',dongleId='DEVICE')
    profile=N(carFingerprint='TEST',steerControlType='torque',flags=0,as_builder=lambda:N(to_bytes=lambda:b'PROFILE'))
    return [Event('initData',100,init),Event('carParams',100,profile),
            Event('carState',200),Event('gpsLocationExternal',201),Event('modelV2',202),
            Event('carState',199 if regression else 300)]

  def test_metadata_never_dereferences_numeric_or_gps(self):
    from openpilot.tools.cyber_autotune import empirical_dataset_v2_inventory as v
    row=v.metadata(self.events())
    self.assertEqual(row['envelope_counts']['carState'],2)
    self.assertNotIn('BOOT',p.canonical(row).decode())

  def test_metadata_regressing_stream_rejected(self):
    from openpilot.tools.cyber_autotune import empirical_dataset_v2_inventory as v
    with self.assertRaisesRegex(ValueError,'CLOCK'):
      v.metadata(self.events(True))


class TestV1CopyDeduplication(unittest.TestCase):
  def test_renamed_v1_copy_is_not_second_route(self):
    from openpilot.tools.cyber_autotune import empirical_dataset_v2_inventory as v
    from openpilot.tools.cyber_autotune import empirical_dataset_v2_policy as policy
    rows=[{'source_sha256':'f'*64,'lineage_sha256':'b'*64,'ordinal':0,
           'metadata':{'generation':policy.expected_generation(),'logger_start_sha256':'a'*64,
                       'first_ns':100,'last_ns':199,'envelope_counts':{'carState':10,'carOutput':10,'carControl':10}}}]
    fresh=v.group_routes(rows,set(),set(),{'a'*64})
    old=[{'lineage_sha256':'c'*64,'source_sha256':'d'*64}]
    merged=v.merge_v1_routes(fresh,old,{'c'*64:'a'*64})
    self.assertEqual(len(merged),1)
    self.assertEqual(merged[0]['segment_count'],2)
    self.assertTrue(merged[0]['v1_overlap'])


class TestByteIdenticalV1Copy(unittest.TestCase):
  def test_copy_with_new_lineage_maps_through_source_hash(self):
    from openpilot.tools.cyber_autotune import empirical_dataset_v2_inventory as v
    old=[{'lineage_sha256':'c'*64,'source_sha256':'d'*64},
         {'lineage_sha256':'b'*64,'source_sha256':'d'*64}]
    merged=v.merge_v1_routes([],old,{'c'*64:'a'*64},{'d'*64:'a'*64})
    self.assertEqual(len(merged),1)
    self.assertEqual(merged[0]['segment_count'],1)
