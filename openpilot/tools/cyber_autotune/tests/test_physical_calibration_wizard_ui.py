"""Loopback requests and TEST_ONLY session; no raw private inputs."""

import json
from pathlib import Path
import tempfile
import threading
import unittest
import urllib.request
import urllib.error
from openpilot.tools.cyber_autotune import physical_calibration_wizard as w
from openpilot.tools.cyber_autotune.tests.test_physical_calibration_wizard import filled

try:
  from openpilot.tools.cyber_autotune import physical_calibration_wizard_ui as ui
except ImportError:
  ui = None


class TestWizardUI(unittest.TestCase):
  def setUp(self):
    self.assertIsNotNone(ui, 'Missing physical wizard UI')
    self.temp = tempfile.TemporaryDirectory()
    self.session = w.MeasurementSession(Path(self.temp.name) / 'test-session', scope='TEST_ONLY')
    self.server = ui.make_server(self.session)
    self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
    self.thread.start()
    self.base = 'http://127.0.0.1:' + str(self.server.server_port)

  def tearDown(self):
    self.server.shutdown()
    self.server.server_close()
    self.thread.join()
    self.temp.cleanup()

  def request(self, path, body=None, headers=None, raw=None):
    data = raw if raw is not None else json.dumps(body).encode() if body is not None else None
    return urllib.request.urlopen(
      urllib.request.Request(self.base + path, data=data, headers={'Content-Type': 'application/json', **(headers or {})}), timeout=5
    )

  def post(self, path, body=None, raw=None):
    return self.request(
      path,
      body,
      {'Origin': self.base, 'X-Wizard-Token': self.server.wizard_token, 'Content-Type': 'application/octet-stream' if raw is not None else 'application/json'},
      raw,
    )

  def test_loopback_only(self):
    for host in ('0.0.0.0', 'localhost', '::'):
      with self.assertRaises(ValueError):
        ui.make_server(self.session, host=host)

  def test_local_assets_and_security_headers(self):
    for path in ('/', '/app.js', '/style.css', '/measurement-sheet'):
      response = self.request(path)
      self.assertEqual(response.status, 200)
      self.assertIn("connect-src 'self'", response.headers['Content-Security-Policy'])
      self.assertIn('no-store', response.headers['Cache-Control'])
    self.assertIn('STATIC_SOURCE_INTRINSICS', self.request('/').read().decode())

  def test_blank_stages_without_defaults(self):
    config = json.load(self.request('/api/config'))
    self.assertEqual(len(config['stages']), 8)
    self.assertIsNone(config['state']['draft']['observations']['height_m']['value'])
    self.assertFalse(config['state']['independent_calibration_validated'])

  def test_origin_host_nonce_guards(self):
    for headers in ({}, {'Origin': 'http://external.invalid', 'X-Wizard-Token': self.server.wizard_token}, {'Origin': self.base, 'X-Wizard-Token': 'bad'}):
      with self.assertRaises(urllib.error.HTTPError) as cm:
        self.request('/api/draft', w.blank_draft(), headers)
      self.assertEqual(cm.exception.code, 403)
    with self.assertRaises(urllib.error.HTTPError):
      self.request('/', headers={'Host': 'external.invalid'})

  def test_draft_save_reload_and_preflight_errors(self):
    d = w.blank_draft()
    d['general']['note'] = 'Explicit TEST'
    self.post('/api/draft', d).close()
    self.assertEqual(json.load(self.request('/api/state'))['draft'], d)
    result = json.load(self.post('/api/preflight', d))
    self.assertFalse(result['valid'])
    self.assertIn('GROUND_SURVEY_PENDING', result['errors'])

  def test_attachment_is_local_opaque_hash(self):
    x = json.load(self.post('/api/attachment', raw=b'Explicit TEST evidence'))
    self.assertEqual(x['status'], 'LOCAL_PRIVATE_ONLY')
    self.assertNotIn('filename', x)

  def test_static_preview_and_receipt_export(self):
    d = filled(self.session)
    x = json.load(self.post('/api/intrinsics', d['camera']))
    self.assertEqual(x['provenance_role'], 'STATIC_INTRINSICS')
    self.assertEqual(x['distortion_model'], 'UNKNOWN_NOT_ASSUMED_ZERO')
    self.post('/api/draft', d).close()
    self.assertTrue(json.load(self.post('/api/preflight', d))['valid'])
    p = json.load(self.post('/api/admit', {}))
    self.assertFalse(p['independent_calibration_validated'])
    self.assertEqual(json.load(self.request('/export/local.json')), p)
    summary = json.load(self.request('/export/public.json'))
    self.assertNotIn('original_input', summary)

  def test_unknown_and_traversal_endpoints_rejected(self):
    for path in ('/../../etc/passwd', '/export/raw.bin', '/api/model-import', '/api/private'):
      with self.assertRaises(urllib.error.HTTPError):
        self.request(path)

  def test_nonobject_duplicate_keys_and_nonfinite_rejected(self):
    for raw in (b'[]', b'{"camera":1,"camera":2}', b'{"value":NaN}'):
      with self.assertRaises(urllib.error.HTTPError):
        self.post('/api/draft', raw=None, body=json.loads(raw) if raw == b'[]' else None) if raw == b'[]' else self.request(
          '/api/draft', headers={'Origin': self.base, 'X-Wizard-Token': self.server.wizard_token}, raw=raw
        )

  def test_server_has_no_automatic_input_discovery(self):
    config = json.load(self.request('/api/config'))
    self.assertEqual(config['state']['private_comma4'], 'NOT_OPENED')
    self.assertEqual(config['state']['sealed_reference'], 'NOT_GENERATED')

  def test_save_immutable_requires_new_workspace(self):
    d = filled(self.session)
    self.post('/api/draft', d).close()
    self.post('/api/admit', {}).close()
    with self.assertRaises(urllib.error.HTTPError):
      self.post('/api/draft', d)
    with self.assertRaises(urllib.error.HTTPError):
      self.post('/api/admit', {})

  def test_printed_nominal_not_physical_truth(self):
    sheet = self.request('/measurement-sheet').read().decode()
    self.assertIn('NOMINAL PRINT GEOMETRY', sheet)
    self.assertIn('100 mm', sheet)
    self.assertIn('실제로 재측정', sheet)
