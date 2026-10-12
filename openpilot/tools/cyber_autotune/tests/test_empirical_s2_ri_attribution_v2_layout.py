"""Lossless public JSON layout, independent of frozen numerical executors."""
import importlib
import importlib.util
import json
import unittest
from openpilot.tools.cyber_autotune import empirical_plant_policy as p


class TestPublicLayout(unittest.TestCase):
  def setUp(self):
    name='openpilot.tools.cyber_autotune.empirical_s2_ri_attribution_v2_layout'
    self.assertIsNotNone(importlib.util.find_spec(name),'Lossless serializer required')
    self.m=importlib.import_module(name)

  def test_small_document_pretty_and_sealed(self):
    value=p.seal({'schema':'TEST','count':2})
    files=self.m.document('empirical-s2-ri-one-step-attribution-v2.json',value)
    self.assertEqual(json.loads(next(iter(files.values()))),value)

  def test_compact_document_preserves_receipt(self):
    value=p.seal({'schema':'TEST','counts':list(range(100))})
    pretty=json.dumps(value,sort_keys=True,indent=2).encode()+b'\n'
    compact=self.m.compact(value)
    limit=(len(pretty)+len(compact))//2
    files=self.m.document('empirical-s2-ri-rollout-attribution-v2.json',value,limit=limit)
    self.assertEqual(next(iter(files.values())),compact)

  def test_context_shards_reconstruct_original(self):
    jobs=[{'candidate_id':f'S2RI_D{d:02d}_L{length:02d}','fold':fold,'count':i}
          for i,(d,length,fold) in enumerate((d,l,f) for d in (0,5,10,20) for l in (1,5,15,45) for f in ('FOLD_A','FOLD_B'))]
    value=p.seal({'schema':'EMPIRICAL_S2_RI_CONTEXT_ATTRIBUTION_V2','jobs':jobs,
                  'input_manifest_sha256':'a'*64,'output_manifest_sha256':'b'*64})
    files=self.m.context_shards('empirical-s2-ri-context-attribution-v2.json',value,1048576)
    index=json.loads(files['empirical-s2-ri-context-attribution-v2.json'])
    restored=[]
    for shard in index['shards']:
      data=files[shard['file']]
      self.assertEqual(p.sha(data),shard['file_sha256'])
      restored.extend(p.verify(json.loads(data))['jobs'])
    self.assertEqual(sorted(restored,key=lambda j:(j['candidate_id'],j['fold'])),jobs)
    self.assertEqual(index['source_bundle_receipt_sha256'],value['receipt_sha256'])

  def test_oversized_other_document_fails(self):
    value=p.seal({'schema':'TEST','text':'x'*1000})
    with self.assertRaisesRegex(ValueError,'PUBLIC_LAYOUT_SIZE'):
      self.m.document('empirical-s2-ri-one-step-attribution-v2.json',value,limit=100)

  def test_path_traversal_rejected(self):
    with self.assertRaisesRegex(ValueError,'PUBLIC_LAYOUT_NAME'):
      self.m.document('../elsewhere.json',p.seal({'count':1}))


if __name__=='__main__':
  unittest.main()
