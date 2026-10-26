from copy import deepcopy
import unittest

from openpilot.tools.cyber_autotune import smoothness_closed_loop_publication as p
from openpilot.tools.cyber_autotune import smoothness_closed_loop as loop
from openpilot.tools.cyber_autotune.smoothness_closed_loop_policy import seal
from openpilot.tools.cyber_autotune.smoothness_v0_publication import load as historical


class TestClosedLoopPublication(unittest.TestCase):
  def fixture(self):
    binding = loop.binding()
    result = seal({'schema': 'SG_A_CLOSED_LOOP_FEEDBACK_V1', 'status': 'SG_CLOSED_LOOP_STRUCTURAL_PASS',
                   'standalone_verdict': 'SG_CLOSED_LOOP_TRADEOFF_ONLY', 'execution_binding_sha256': binding['receipt_sha256'],
                   'feedback_interaction': 'MIXED_OR_UNRESOLVED', 'composition_recommendation': 'COMPOSITION_NOT_RECOMMENDED',
                   'scenarios': [], 'executions': 66, 'repeatability': 'EXACT_PASS'})
    return result, binding

  def test_reference_track_preserved(self):
    r, b = self.fixture()
    self.assertEqual(p.build(r, b)['readiness']['reference_track'], historical()['readiness']['reference_track'])

  def test_ta_preserved(self):
    r, b = self.fixture()
    self.assertEqual(p.build(r, b)['readiness']['ta_interpretation'], 'TA_STANDALONE_TRADEOFF_ONLY')

  def test_sg_replay_preserved(self):
    r, b = self.fixture()
    self.assertEqual(p.build(r, b)['readiness']['historical_sg_interpretation'], 'SG_STANDALONE_TRADEOFF_ONLY')

  def test_historical_verdicts(self):
    r, b = self.fixture()
    self.assertEqual(p.build(r, b)['readiness']['historical_verdicts'], historical()['readiness']['historical_verdicts'])

  def test_no_composition_authorization(self):
    r, b = self.fixture()
    self.assertFalse(p.build(r, b)['readiness']['composition_authorized'])

  def test_no_search(self):
    r, b = self.fixture()
    self.assertFalse(p.build(r, b)['readiness']['search_authorized'])

  def test_no_meter_result(self):
    r, b = self.fixture()
    self.assertIsNone(p.build(r, b)['readiness']['independent_meter_result'])

  def test_no_total_bound(self):
    r, b = self.fixture()
    self.assertIsNone(p.build(r, b)['readiness']['total_physical_bound'])

  def test_no_sealed_reference(self):
    r, b = self.fixture()
    self.assertEqual(p.build(r, b)['readiness']['sealed_reference'], 'NOT_GENERATED')

  def test_no_stability_proof(self):
    r, b = self.fixture()
    self.assertFalse(p.build(r, b)['readiness']['stability_proof'])

  def test_corrupt_receipt_rejected(self):
    r, _ = self.fixture()
    r['executions'] = 999
    with self.assertRaises(ValueError):
      p.check_receipt(r)

  def test_binding_mismatch_rejected(self):
    r, b = self.fixture()
    bad = deepcopy(b)
    bad['sg_family'] = 'TA-B'
    with self.assertRaises(ValueError):
      p.build(r, bad)

  def test_no_vehicle_authority(self):
    r, b = self.fixture()
    self.assertFalse(p.build(r, b)['readiness']['vehicle_activation_allowed'])

  def test_no_qualification(self):
    r, b = self.fixture()
    self.assertFalse(p.build(r, b)['readiness']['qualification_allowed'])

  def test_source_binding_isolated(self):
    _, b = self.fixture()
    self.assertEqual(b['physical_delay_owner'], 'EACH_ARM_PLANT_ONLY')

  def test_exact_replay_pin(self):
    _, b = self.fixture()
    self.assertEqual(b['frozen_replay_receipt_sha256'], historical()['results']['receipt_sha256'])


class TestFrozenClosedLoopReceipts(unittest.TestCase):
  def test_exact_pins(self):
    rows = p.load()
    self.assertEqual({k: v['receipt_sha256'] for k, v in rows.items()}, p.PINS)

  def test_resealed_mutation_rejected(self):
    row = deepcopy(p.load()['readiness'])
    row['status'] = 'READY_FOR_VEHICLE'
    row = seal({k: v for k, v in row.items() if k != 'receipt_sha256'})
    with self.assertRaises(ValueError):
      p.validate_pinned('readiness', row)


class TestPublicationShards(unittest.TestCase):
  def test_lossless_frozen_results(self):
    row = p.load()['results']
    manifest, shards = p.result_transport(row)
    self.assertEqual(p.reconstruct_result(manifest, shards), row)

  def test_each_file_scannable(self):
    import json
    from tools.cyberpilot.check_publication import MAX_TEXT_BYTES
    manifest, shards = p.result_transport(p.load()['results'])
    for row in (manifest, *shards.values()):
      self.assertLessEqual(len((json.dumps(row, sort_keys=True, indent=2) + '\n').encode()), MAX_TEXT_BYTES)

  def test_modified_shard_rejected(self):
    manifest, shards = p.result_transport(p.load()['results'])
    first = next(iter(shards))
    shards[first]['scenario_result']['scenario'] = 'easier_replacement'
    with self.assertRaises(ValueError):
      p.reconstruct_result(manifest, shards)

  def test_path_escape_rejected(self):
    manifest, shards = p.result_transport(p.load()['results'])
    manifest['scenario_shards'][0]['file'] = '../other.json'
    manifest = seal({k: v for k, v in manifest.items() if k != 'receipt_sha256'})
    with self.assertRaises(ValueError):
      p.reconstruct_result(manifest, shards)

  def test_frozen_full_result_sha_preserved(self):
    manifest, _ = p.result_transport(p.load()['results'])
    self.assertEqual(manifest['full_result_receipt_sha256'], p.PINS['results'])
