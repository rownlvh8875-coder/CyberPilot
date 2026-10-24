"""Fixed aggregate chain, privacy and historical authority regression tests."""

import json
from pathlib import Path
import unittest
from unittest.mock import patch

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import cyber_h1_pairing as q
from openpilot.tools.cyber_autotune import cyber_h1_comparison_publication as public


class TestPairedPublication(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.rows = public.load()

  def test_exact_eight_fixed_artifacts(self):
    self.assertEqual(len(self.rows), 8)
    self.assertEqual(public.validate(self.rows), self.rows)

  def test_all_historical_public_chains_unchanged(self):
    history = q.historical()
    self.assertEqual(history['composition'], 'COMPOSITION_NOT_AUTHORIZED')
    self.assertEqual(len(history['scenario_rows']), 11)
    self.assertEqual(q.CAMPAIGNS['TA_B'][2], 'TA_STANDALONE_TRADEOFF_ONLY')
    self.assertEqual(q.CAMPAIGNS['SG_A'][2], 'SG_CLOSED_LOOP_TRADEOFF_ONLY')

  def test_no_per_sample_public_payload(self):
    forbidden = {
      'frames',
      'consumed_input_snapshot',
      'native_input',
      'plant_output',
      'capture_time_ns',
      'decision_time_ns',
      'completion_time_ns',
    }

    def walk(obj):
      if isinstance(obj, dict):
        self.assertFalse(forbidden & set(obj))
        for value in obj.values():
          walk(value)
      elif isinstance(obj, list):
        for value in obj:
          walk(value)

    # Schema definitions and policy specify field names, never actual per-row values.
    for name, row in self.rows.items():
      if 'schema-v1' not in name and 'policy-v1' not in name:
        walk(row)

  def test_holdout_and_authority_closed(self):
    for row in self.rows.values():
      for field in (
        'production_authority',
        'publication_raw_data',
        'vehicle_activation_allowed',
        'qualification_allowed',
        'composition_authorized',
        'candidate_search_authorized',
      ):
        self.assertIs(row[field], False)
    ready = self.rows['cyber-h1-comparison-readiness-v1.json']
    self.assertEqual(ready['holdout_opening'], 'CLOSED')
    self.assertEqual(ready['opening_count'], 0)

  def test_calibration_reference_blockers_unchanged(self):
    row = self.rows['cyber-h1-comparison-readiness-v1.json']
    self.assertEqual(row['calibration_blockers'], p.BLOCKERS)

  def test_resealed_public_mutation_rejected(self):
    rows = json.loads(p.canonical(self.rows))
    name = 'cyber-h1-comparison-readiness-v1.json'
    rows[name]['opening_count'] = 1
    rows[name] = q.verify(q.seal({k: v for k, v in rows[name].items() if k != 'receipt_sha256'}))
    with self.assertRaisesRegex(ValueError, 'PAIR_PUBLICATION_PIN_DRIFT'):
      public.validate(rows)

  def test_missing_public_artifact_rejected(self):
    rows = dict(self.rows)
    rows.pop(next(iter(rows)))
    with self.assertRaises(ValueError):
      public.validate(rows)

  def test_public_claim_cannot_escalate_tier(self):
    cat = self.rows['cyber-h1-comparison-catalog-v1.json']
    self.assertTrue(all(c['evidence_tier'] == q.TIER for c in cat['campaigns']))

  def test_no_raw_event_reader_dependency(self):
    # Full publication validation must succeed even if an event reader is unavailable.
    with patch('openpilot.tools.lib.logreader.LogReader', side_effect=AssertionError('RAW_EVENT_REOPENING_PROHIBITED')):
      self.assertEqual(public.load(), self.rows)

  def test_no_production_source_or_device_authority(self):
    root = Path(public.__file__).parent
    for name in (
      'cyber_h1_pairing.py',
      'cyber_h1_pair_producer.py',
      'cyber_h1_paired_visual_adapter.py',
      'cyber_h1_comparison_catalog.py',
      'cyber_h1_comparison_server.py',
    ):
      text = (root / name).read_text()
      for token in ('Params(', 'CarController(', 'subprocess.', 'os.system(', 'LogReader(', 'carrotlog'):
        self.assertNotIn(token, text)
