"""Actual loopback endpoints, no real/private camera inputs."""

import json
import threading
import unittest
import urllib.request
import urllib.error
from openpilot.tools.cyber_autotune import approximate_geometry_diagnostic as a

try:
  from openpilot.tools.cyber_autotune import approximate_geometry_visualizer as ui
except ImportError:
  ui = None


class TestApproxVisualizer(unittest.TestCase):
  def setUp(self):
    self.assertIsNotNone(ui, 'Missing local diagnostic visualizer')
    self.server = ui.make_server()
    self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
    self.thread.start()
    self.base = 'http://127.0.0.1:' + str(self.server.server_port)

  def tearDown(self):
    self.server.shutdown()
    self.server.server_close()
    self.thread.join()

  def request(self, path, body=None, headers=None, raw=None):
    return urllib.request.urlopen(
      urllib.request.Request(
        self.base + path,
        data=raw if raw is not None else None if body is None else json.dumps(body).encode(),
        headers={'Content-Type': 'application/json', **(headers or {})},
      ),
      timeout=5,
    )

  def post(self, path, body):
    return self.request(path, body, {'Origin': self.base, 'X-Diagnostic-Token': self.server.diagnostic_token})

  def test_reject_nonloopback(self):
    for host in ('0.0.0.0', 'localhost', '::'):
      with self.assertRaises(ValueError):
        ui.make_server(host=host)

  def test_static_assets_and_state_height_unknown_all_firewalls(self):
    for path in ('/', '/app.js', '/style.css'):
      r = self.request(path)
      self.assertEqual(r.status, 200)
      self.assertIn("connect-src 'self'", r.headers['Content-Security-Policy'])
    x = json.load(self.request('/api/state'))
    self.assertIsNone(x['prior']['camera_height_m'])
    self.assertFalse(x['readiness']['private_input_allowed'])
    self.assertEqual(x['comparison']['status'], 'PHYSICAL_MEASUREMENT_COMPARISON_PENDING')

  def test_mutation_origin_nonce_and_unknown_path(self):
    for headers in ({}, {'Origin': 'https://example.invalid'}):
      with self.assertRaises(urllib.error.HTTPError):
        self.request('/api/sensitivity', {}, headers)
    with self.assertRaises(urllib.error.HTTPError):
      self.request('/', headers={'Host': 'external.invalid'})
    with self.assertRaises(urllib.error.HTTPError):
      self.request('/api/private')

  def test_parametric_request_bound_to_exact_policy_no_nominal_mutation(self):
    body = {'heights_m': [1.0, 2.0], 'rpy_deg_choices': [[0.0, 2.34, 0.2]], 'mount_y_m': [0.0], 'rationale': 'TEST_ONLY parameters not physically observed'}
    x = json.load(self.post('/api/sensitivity', body))
    self.assertEqual(len(x['report']['rows']), 8)
    self.assertEqual(x['report']['policy_sha256'], x['policy']['receipt_sha256'])
    self.assertFalse(x['report']['qualification_allowed'])
    self.assertIsNone(json.load(self.request('/api/state'))['prior']['camera_height_m'])

  def test_empty_height_no_hidden_default_and_unknown_fields(self):
    base = {'heights_m': [], 'rpy_deg_choices': [[0.0, 2.34, 0.2]], 'mount_y_m': [0.0], 'rationale': 'TEST_ONLY'}
    with self.assertRaises(urllib.error.HTTPError):
      self.post('/api/sensitivity', base)
    base['heights_m'] = [1.0]
    base['private_path'] = 'FORBIDDEN'
    with self.assertRaises(urllib.error.HTTPError):
      self.post('/api/sensitivity', base)

  def test_known_ray_projection_or_symbolic_only(self):
    x = json.load(self.post('/api/ray', {'normalized_uv': [0.0, 0.2], 'height_m': None}))
    self.assertEqual(x['scope'], 'SYMBOLIC_HEIGHT_RELATION')
    x = json.load(self.post('/api/ray', {'normalized_uv': [0.0, 0.2], 'height_m': 1.0}))
    self.assertFalse(x['reference_promotable'])

  def test_strict_json_duplicate_nonfinite_and_array_rejected(self):
    for raw in (b'[]', b'{"heights_m":1,"heights_m":2}', b'{"height_m":NaN}'):
      with self.assertRaises(urllib.error.HTTPError):
        self.request('/api/ray', headers={'Origin': self.base, 'X-Diagnostic-Token': self.server.diagnostic_token}, raw=raw)

  def test_future_explicit_physical_receipt_comparison_no_validation(self):
    from openpilot.tools.cyber_autotune.tests.test_camera_calibration_evidence import fixture
    from openpilot.tools.cyber_autotune import camera_calibration_evidence as c

    m, i = fixture()
    r = ui.state(a.prior(), c.admit(m, i))
    self.assertEqual(r['comparison']['physical_scope'], 'TEST_ONLY')
    self.assertFalse(r['comparison']['live_calibration_validated'])
    self.assertFalse(r['readiness']['sealed_reference_allowed'])

  def test_future_wizard_store_explicit_package_integrity(self):
    import tempfile
    from pathlib import Path
    from openpilot.tools.cyber_autotune import physical_calibration_wizard as w
    from openpilot.tools.cyber_autotune.tests.test_physical_calibration_wizard import filled

    with tempfile.TemporaryDirectory() as folder:
      root = Path(folder) / 'test-stationary'
      session = w.MeasurementSession(root, scope='TEST_ONLY')
      session.save_draft(filled(session))
      package = session.admit()
      self.assertEqual(ui.physical_from_wizard(root), package['admission'])
      with self.assertRaises(ValueError):
        ui.physical_from_wizard(Path(folder) / 'not-existing')

  def test_running_handler_rejects_source_or_asset_drift_all_routes(self):
    from pathlib import Path
    from unittest.mock import patch

    original = Path.read_bytes
    for target in (Path(ui.__file__), ui.ASSETS / 'app.js'):

      def changed(path, target=target):
        data = original(path)
        return data + b'\nTEST_ONLY_SOURCE_DRIFT' if path == target else data

      with patch.object(Path, 'read_bytes', changed):
        for route in ('/api/state', '/app.js'):
          with self.assertRaises(urllib.error.HTTPError) as cm:
            self.request(route)
          self.assertEqual(cm.exception.code, 400)
        with self.assertRaises(urllib.error.HTTPError):
          self.post('/api/ray', {'normalized_uv': [0.0, 0.2], 'height_m': None})
