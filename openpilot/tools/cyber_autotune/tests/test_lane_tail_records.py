import json
from pathlib import Path
import unittest

from openpilot.tools.cyber_autotune.native_protocol import canonical, digest
from openpilot.tools.cyber_autotune.lane_tail_report import unseal

ROOT = Path(__file__).resolve().parents[4]
DOC = ROOT / 'docs/cyberpilot/changes'


class TestTailRecords(unittest.TestCase):
  def load(self, name):
    data = json.loads((DOC / name).read_bytes())
    unseal(data)
    return data

  def test_primary_all_119_bound_ledgers(self):
    report = self.load('comma10k-tail-clrernet-report.json')
    ledger = json.loads((DOC / 'comma10k-tail-clrernet-ledger.json').read_bytes())
    manifest = json.loads((DOC / 'public-lane-detector-diagnostic-protocol.json').read_bytes())
    self.assertEqual(len(ledger), 119)
    self.assertEqual([r['frame_id'] for r in ledger], [p['image'] for p in manifest['pairs']])
    self.assertEqual(report['ledger_sha256'], digest(canonical(ledger)))
    for r in ledger:
      unseal(r)

  def test_primary_historical_result_preserved(self):
    report = self.load('comma10k-tail-clrernet-report.json')
    old = json.loads((DOC / 'public-lane-detector-diagnostic-result.json').read_bytes())
    self.assertEqual(report['directions']['pred'], old['localization']['pred_to_gt'])
    self.assertEqual(report['directions']['gt'], old['localization']['gt_to_pred'])
    self.assertFalse(report['legacy_result_invalidated'])

  def test_report_source_binding(self):
    for detector in ('clrernet', 'clrnet'):
      report = self.load(f'comma10k-tail-{detector}-report.json')
      self.assertEqual(report['source_sha256'], digest((ROOT / 'openpilot/tools/cyber_autotune/lane_tail_report.py').read_bytes()))
      self.assertEqual(report['metric_source_sha256'], digest((ROOT / 'openpilot/tools/cyber_autotune/lane_tail_diagnostics.py').read_bytes()))

  def test_secondary_failure_not_resurrected(self):
    report = self.load('comma10k-tail-clrnet-report.json')
    capture = self.load('comma10k-tail-clrnet-capture.json')
    self.assertFalse(report['detector_exact_repeatability'])
    self.assertEqual(capture['detector_status'], 'REJECTED_FOR_EXACT_REPEATABILITY')
    self.assertEqual(len(capture['repeat_differing_frames']), 1)
    self.assertFalse(capture['reference_promotable'])

  def test_semantic_accounting_tail_not_dropped(self):
    report = self.load('comma10k-tail-clrernet-report.json')
    self.assertEqual(sum(report['historical_p95_semantic_tail'].values()), report['historical_p95_tail_points'])
    self.assertEqual(report['historical_p95_tail_points'], 2115)
    self.assertEqual(report['historical_p95_tail_spatially_resolved_points'], 1079)

  def test_private_and_qualification_gates_closed(self):
    gate = self.load('comma10k-tail-private-gate.json')
    self.assertFalse(gate['private_input_allowed'])
    self.assertFalse(gate['reference_promotable'])
    for detector in ('clrernet', 'clrnet'):
      report = self.load(f'comma10k-tail-{detector}-report.json')
      self.assertFalse(report['reference_promotable'])
      self.assertIsNone(report['meter_error'])
      self.assertFalse(report['ego_lane_association_evaluated'])
      self.assertFalse(report['private_input_opened'])
