"""Coarse UI state remains separate from original unknown-height evidence."""

from openpilot.tools.cyber_autotune.tests import test_approximate_geometry_visualizer as base
import unittest
import json


class TestCoarseVisualizer(unittest.TestCase):
  def setUp(self):
    self.fixture = base.TestApproxVisualizer()
    self.fixture.setUp()

  def tearDown(self):
    self.fixture.tearDown()

  def request(self, path):
    return self.fixture.request(path)

  def test_coarse_nominal_and_envelope_bound_to_separate_prior(self):
    state = json.load(self.request('/api/state'))
    self.assertIsNone(state['prior']['camera_height_m'])
    self.assertEqual(state['coarse']['height_prior']['nominal_height_m'], 1.4)
    self.assertEqual(len(state['coarse']['result']['sensitivity_envelope']['matrix']), 84)
    self.assertEqual(len(state['coarse']['result']['nominal_result']['rows']), 4)
    self.assertEqual(state['coarse']['readiness']['private_comma4'], 'NOT_OPENED')
    self.assertFalse(state['coarse']['result']['sealed_reference_allowed'])

  def test_coarse_source_drift_fail_closed_at_handler(self):
    from pathlib import Path
    from unittest.mock import patch
    from openpilot.tools.cyber_autotune import coarse_camera_height_diagnostic as h
    import urllib.error
    original = Path.read_bytes

    def changed(path):
      return original(path) + (b'TEST_ONLY_DRIFT' if path == Path(h.__file__) else b'')

    with patch.object(Path, 'read_bytes', changed):
      with self.assertRaises(urllib.error.HTTPError) as cm:
        self.request('/api/state')
      self.assertEqual(cm.exception.code, 400)
