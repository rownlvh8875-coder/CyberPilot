"""Published visual evidence must stay aggregate, pinned and without authority."""

from copy import deepcopy
import unittest
from openpilot.tools.cyber_autotune import cyber_h1_visual_publication as pub
from openpilot.tools.cyber_autotune import empirical_plant_policy as p


class TestVisualPublication(unittest.TestCase):
  def test_exact_six_receipts(self):
    self.assertEqual(len(pub.load()), 6)

  def test_resealed_drift_rejected(self):
    rows = deepcopy(pub.load())
    name = 'cyber-h1-visual-readiness-v1.json'
    row = rows[name]
    row.pop('receipt_sha256')
    row['opening_count'] = 1
    rows[name] = p.seal(row)
    with self.assertRaises(ValueError):
      pub.validate(rows)

  def test_no_frames_or_paths(self):
    rows = pub.load()
    for row in rows.values():
      self.assertNotIn('frames', row)
      self.assertNotIn('private_path', row)
    self.assertEqual(rows['cyber-h1-visual-catalog-v1.json']['runs'][0]['frame_count'], 800)

  def test_readiness_partial_single_arm(self):
    row = pub.load()['cyber-h1-visual-readiness-v1.json']
    self.assertEqual(row['data_completeness'], 'VISUAL_DATA_COMPLETENESS_PARTIAL')
    self.assertFalse(row['comparison_ready'])
    self.assertEqual(row['arm_count'], 1)
    self.assertEqual(row['holdout_opening'], 'CLOSED')
    self.assertEqual(row['opening_count'], 0)
    self.assertFalse(row['production_authority'])
    self.assertFalse(row['holdout_opener_implemented'])
    self.assertEqual(row['calibration_blockers'], p.BLOCKERS)

  def test_actual_browser_proof(self):
    row = pub.load()['cyber-h1-visual-browser-validation-v1.json']
    self.assertEqual(row['status'], 'ACTUAL_BROWSER_VALIDATED')
    self.assertEqual(row['frames_loaded'], 800)
    self.assertEqual(row['pages_loaded'], 8)
    for key in ('javascript_errors', 'network_errors', 'external_network_requests'):
      self.assertEqual(row[key], 0)
    self.assertTrue(row['shutdown_verified'])
    self.assertTrue(row['port_closed_after_shutdown'])
    for name in ('first_middle_final', 'scrubber', 'play_pause', 'frame_step', 'event_jump', 'charts_pose', 'nulls_evidence'):
      self.assertTrue(row['checks'][name])

  def test_runtime_server_asset_pin(self):
    from unittest.mock import patch
    from openpilot.tools.cyber_autotune import cyber_h1_visual_server as server

    original = server.contract()
    changed = deepcopy(original)
    changed['source_files']['static/cyber_h1_visual.js'] = '0' * 64
    changed.pop('receipt_sha256')
    with patch.object(server, 'contract', return_value=p.seal(changed)):
      with self.assertRaisesRegex(ValueError, 'VISUAL_SERVER_FIXED_PUBLICATION_SOURCE_DRIFT'):
        pub.validate_server_contract()

  def test_historical_h1_receipts_unchanged(self):
    from openpilot.tools.cyber_autotune import cyber_lateral_h1_publication as h

    rows = h.load()
    self.assertEqual(rows['cyber-lateral-h1-readiness-v1.json']['visual_readiness'], 'VISUAL_FRAME_CONVERSION_PARTIAL')
    self.assertEqual(rows['cyber-lateral-h1-synthetic-trace-v1.json']['row_count'], 800)

  def test_no_external_assets_or_model_authority(self):
    from openpilot.tools.cyber_autotune import cyber_h1_visual_server as server

    for name in server.ASSETS.values():
      text = (server.STATIC / name).read_text()
      for forbidden in ('https://', 'http://', 'fetch("https:', '<iframe', '<form', 'onclick=', 'eval('):
        # SVG namespace is a vocabulary URI, never a resource request.
        if forbidden == 'http://':
          self.assertNotIn(forbidden, text.replace('http://www.w3.org/2000/svg', ''))
        else:
          self.assertNotIn(forbidden, text)
    self.assertFalse(pub.load()['cyber-h1-visual-server-contract-v1.json']['optimizer_endpoint'])
