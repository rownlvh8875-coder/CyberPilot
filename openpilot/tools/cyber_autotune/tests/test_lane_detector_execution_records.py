import json
import unittest
from pathlib import Path

from openpilot.tools.cyber_autotune import lane_detector_execution as e
from openpilot.tools.cyber_autotune.native_protocol import canonical, digest


class TestPublicDetectorExecutionRecords(unittest.TestCase):
  def folder(self):
    return Path(__file__).resolve().parents[4] / 'docs/cyberpilot/changes'

  def read(self, name):
    return json.loads((self.folder() / name).read_bytes())

  def test_frozen_environment_and_consumed_public_files_bound(self):
    env = self.read('public-lane-detector-environment.json')
    self.assertEqual(env, e.freeze_environment(e._unseal(env, 'environment_sha256')))
    for field, file in [('public_protocol_file_sha256', 'public-lane-detector-diagnostic-protocol.json'),
                        ('public_input_manifest_file_sha256', 'public-lane-detector-input-manifest.json')]:
      self.assertEqual(env[field], digest((self.folder() / file).read_bytes()))

  def test_actual_diagnostic_is_incomplete_and_never_private_or_meter_qualification(self):
    r = self.read('public-lane-detector-diagnostic-result.json')
    self.assertEqual(r['frames_per_repetition'], 119)
    self.assertTrue(r['exact_repeatability'])
    self.assertEqual(r['evidence_tier'], 'POST_RESULT_ADAPTER_CORRECTION_DIAGNOSTIC_NOT_QUALIFICATION')
    self.assertFalse(r['private_input_opened'])
    self.assertFalse(r['reference_promotable'])
    self.assertIsNone(r['localization']['meter_error'])
    self.assertEqual(r['receipt_sha256'], digest(canonical(e._unseal(r))))
    self.assertEqual(r['runner_source_sha256'], digest(Path(__file__).parents[1].joinpath('lane_detector_runner.py').read_bytes()))

  def test_official_not_run_cannot_be_pass_and_private_gate_remains_closed(self):
    env = self.read('public-lane-detector-environment.json')
    rep = self.read('public-lane-detector-official-reproduction.json')
    self.assertEqual(rep, e.reproduction_receipt(env, rep['run']))
    self.assertIsNone(rep['run']['official_f1_fraction'])
    self.assertIsNone(rep['run']['exit_code'])
    self.assertEqual(rep['run']['evaluated_frames'], 0)
    gate = self.read('public-lane-detector-private-gate.json')
    self.assertEqual(gate, e.private_pixel_gate(env, rep))
    self.assertFalse(gate['private_input_access_allowed'])

  def test_discarded_history_and_initial_protocol_not_overwritten(self):
    old = self.read('public-lane-detector-adapter-v1-discarded.json')
    revision = self.read('public-lane-detector-diagnostic-protocol.json')
    self.assertEqual(revision['prior_result_file_sha256'], digest((self.folder() / 'public-lane-detector-adapter-v1-discarded.json').read_bytes()))
    self.assertEqual(old['geometry_unavailable_frames'], 82)
    self.assertEqual(revision['initial_protocol_file_sha256'],
                     digest((self.folder() / 'public-lane-detector-initial-protocol.json').read_bytes()))
