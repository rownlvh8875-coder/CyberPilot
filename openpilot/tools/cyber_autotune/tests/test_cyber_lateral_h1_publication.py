"""Exact aggregate receipts and no-production/raw authority regressions."""

import ast
from copy import deepcopy
from pathlib import Path
import unittest
from unittest.mock import patch

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import cyber_lateral_h1_contract as c
from openpilot.tools.cyber_autotune import cyber_lateral_h1_publication as pub

ROOT = Path(__file__).resolve().parents[1]


class TestH1Publication(unittest.TestCase):
  def test_exact_publication(self):
    self.assertEqual(len(pub.load()), 5)

  def test_contracts_exact(self):
    rows = pub.load()
    self.assertEqual(rows['cyber-lateral-h1-policy-v1.json'], c.policy())
    self.assertEqual(rows['cyber-lateral-h1-schema-v1.json'], c.schema())

  def test_digest_drift(self):
    rows = deepcopy(pub.load())
    rows['cyber-lateral-h1-readiness-v1.json']['opening_count'] = 1
    with self.assertRaises(ValueError):
      pub.validate(rows)

  def test_resealed_drift(self):
    rows = deepcopy(pub.load())
    name = 'cyber-lateral-h1-readiness-v1.json'
    row = rows[name]
    row.pop('receipt_sha256')
    row['status'] = 'T2_READY'
    rows[name] = p.seal(row)
    with self.assertRaises(ValueError):
      pub.validate(rows)

  def test_no_private_inventory(self):
    with patch.object(p, 'inventory', side_effect=AssertionError('RAW_ACCESS_FORBIDDEN')):
      pub.load()

  def test_producer_no_runtime_imports(self):
    for name in ('cyber_lateral_h1_contract.py', 'cyber_lateral_h1_producer.py', 'cyber_lateral_h1_inspector.py', 'cyber_lateral_h1_publication.py'):
      tree = ast.parse((ROOT / name).read_bytes())
      imports = [node.module or '' for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
      self.assertFalse(any('selfdrive' in mod or 'opendbc' in mod or 'logreader' in mod or 'messaging' in mod for mod in imports))

  def test_no_authority_calls(self):
    for name in (*c.OWN_FILES, 'cyber_lateral_h1_publication.py'):
      tree = ast.parse((ROOT / name).read_bytes())
      forbidden = {'Params', 'LogReader', 'CANPacker', 'PubMaster', 'sendcan', 'put', 'put_bool', 'put_nonblocking', 'Popen', 'run_arm_candidate'}
      calls = [
        node.func.attr if isinstance(node.func, ast.Attribute) else node.func.id if isinstance(node.func, ast.Name) else ''
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
      ]
      self.assertFalse(forbidden.intersection(calls))

  def test_no_raw_values_publication(self):
    rows = pub.load()
    trace = rows['cyber-lateral-h1-synthetic-trace-v1.json']
    self.assertNotIn('rows', trace)
    self.assertNotIn('consumed_input_snapshot', trace)
    self.assertNotIn('signals', trace)
    self.assertEqual(trace['row_count'], 800)

  def test_holdout_closed(self):
    row = pub.load()['cyber-lateral-h1-readiness-v1.json']
    self.assertEqual(row['holdout_opening'], 'CLOSED')
    self.assertEqual(row['opening_count'], 0)
    self.assertFalse(row['holdout_opener_implemented'])
    self.assertEqual(row['model_state'], 'NO_MODEL_ADMITTED_FOR_FUTURE_HOLDOUT')

  def test_historical_blockers(self):
    row = pub.load()['cyber-lateral-h1-readiness-v1.json']
    self.assertEqual(row['calibration_blockers'], p.BLOCKERS)
    self.assertEqual(row['stage_b'], 'STAGE_B_SIGNAL_ADMISSION_BLOCKED')
    self.assertEqual(row['ta'], 'TA_STANDALONE_TRADEOFF_ONLY')
    self.assertEqual(row['sg'], 'SG_CLOSED_LOOP_TRADEOFF_ONLY')

  def test_no_tier_promotion(self):
    row = pub.load()['cyber-lateral-h1-synthetic-trace-v1.json']
    self.assertEqual(row['tier'], c.TIER)
    self.assertFalse(row['qualification_allowed'])

  def test_repeatability_proof(self):
    row = pub.load()['cyber-lateral-h1-repeatability-v1.json']
    self.assertEqual(row['executions'], 2)
    self.assertTrue(row['row_bytes_exact'])
    self.assertEqual(row['experiment_result_sha256'], row['observer_removed_result_sha256'])
