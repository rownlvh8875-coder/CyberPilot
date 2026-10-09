"""Loopback-only synthetic target capture UI contracts."""
import io
import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from PIL import Image
from openpilot.tools.cyber_autotune import stationary_target_calibration as t
from openpilot.tools.cyber_autotune.tests.test_stationary_target_calibration import capture
from openpilot.tools.cyber_autotune.native_protocol import digest, canonical
try:
  from openpilot.tools.cyber_autotune import stationary_target_ui as ui
except ImportError:
  ui = None


class TestTargetUI(unittest.TestCase):
  def setUp(self):
    self.assertIsNotNone(ui, 'target UI missing')
    self.tmp = tempfile.TemporaryDirectory()
    self.session = t.CaptureSession(Path(self.tmp.name) / 'capture', scope='TEST_ONLY')
    self.server = ui.make_server(self.session)
    self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
    self.thread.start()
    self.url = 'http://127.0.0.1:' + str(self.server.server_port)

  def tearDown(self):
    if hasattr(self, 'server'):
      self.server.shutdown()
      self.thread.join()
      self.server.server_close()
      self.tmp.cleanup()

  def request(self, path, data=None, binary=False, token=True):
    headers = {}
    if data is not None:
      data = data if binary else canonical(data)
      headers.update({'Content-Type': 'application/octet-stream' if binary else 'application/json', 'Origin': self.url})
      if token:
        headers['X-Target-Token'] = self.server.token
    return urlopen(Request(self.url + path, data=data, headers=headers), timeout=5)

  def test_page_local_assets_stages_blank_measured_inputs(self):
    page = self.request('/').read().decode()
    self.assertIn('CALIBRATION_MEASUREMENT_PENDING', page)
    self.assertIn('width=device-width', page)
    self.assertNotIn('https://', page)
    self.assertIn('data-stage="4"', page)
    script = self.request('/app.js').read().decode()
    self.assertNotIn('liveCalibration', script)
    self.assertNotIn('value="1.40"', page)

  def test_host_origin_nonce_restrictions(self):
    with self.assertRaises(ValueError):
      ui.make_server(self.session, host='0.0.0.0')
    with self.assertRaises(HTTPError) as exc:
      self.request('/api/draft', {}, token=False)
    self.assertEqual(exc.exception.code, 403)
    with self.assertRaises(HTTPError):
      urlopen(Request(self.url + '/', headers={'Host': 'evil.invalid'}), timeout=5)

  def test_editable_draft_save_reload(self):
    d = {'fields': {'height1': ''}, 'points': []}
    self.request('/api/draft', d).read()
    x = json.load(self.request('/api/state'))
    self.assertEqual(x['draft'], d)
    self.assertEqual(t.CaptureSession(self.session.root, scope='TEST_ONLY').state()['draft'], d)

  def test_image_import_hash_binding_and_unknown_resource(self):
    data = io.BytesIO()
    Image.new('RGB', (1344, 760), 'white').save(data, format='PNG')
    raw = data.getvalue()
    x = json.load(self.request('/api/image', raw, binary=True))
    self.assertEqual(x['sha256'], digest(raw))
    self.assertEqual(self.request('/image/' + x['sha256']).read(), raw)
    with self.assertRaises(HTTPError):
      self.request('/image/' + 'a' * 64)

  def test_solver_preview_no_automatic_admission(self):
    d, i, _, _ = capture()
    data = io.BytesIO()
    Image.new('RGB', tuple(d['image_wh']), 'white').save(data, format='PNG')
    image = json.load(self.request('/api/image', data.getvalue(), binary=True))
    d['image_sha256'] = image['sha256']
    x = json.load(self.request('/api/solve', {'capture': d, 'intrinsics_sha256': i['receipt_sha256']}))
    self.assertEqual(x['status'], 'CALIBRATION_SOLVED')
    self.assertFalse(x['sealed_reference_allowed'])
    self.assertFalse((self.session.root / 'admitted.json').exists())

  def test_immutable_capture_and_restart(self):
    d, i, _, _ = capture()
    data = io.BytesIO()
    Image.new('RGB', tuple(d['image_wh']), 'white').save(data, format='PNG')
    raw = data.getvalue()
    x = json.load(self.request('/api/image', raw, binary=True))
    d['image_sha256'] = x['sha256']
    result = json.load(self.request('/api/freeze', {'capture': d, 'intrinsics_sha256': i['receipt_sha256']}))
    with self.assertRaises(HTTPError):
      self.request('/api/freeze', {'capture': d, 'intrinsics_sha256': i['receipt_sha256']})
    self.assertTrue((self.session.root / (result['receipt_sha256'] + '.json')).exists())
    state = t.CaptureSession(self.session.root, scope='TEST_ONLY').state()
    self.assertEqual(state['status'], 'CALIBRATION_SOLVED')
    self.assertEqual(state['measurement_admission'], 'CALIBRATION_MEASUREMENT_PENDING')
    self.assertEqual(state['completed_captures'], 1)
    self.assertEqual(json.load(self.request('/export/local-captures.json'))['captures'][0], result)

  def test_browser_numeric_serialization_cannot_corrupt_intrinsics_receipt(self):
    d, i, _, _ = capture()
    data = io.BytesIO()
    Image.new('RGB', tuple(d['image_wh']), 'white').save(data, format='PNG')
    image = json.load(self.request('/api/image', data.getvalue(), binary=True))
    d['image_sha256'] = image['sha256']
    result = json.load(self.request('/api/solve', {'capture': d, 'intrinsics_sha256': i['receipt_sha256']}))
    self.assertEqual(result['intrinsics_sha256'], i['receipt_sha256'])

  def test_test_session_cannot_preview_independent_physical_scope(self):
    d, i, _, _ = capture()
    data = io.BytesIO()
    Image.new('RGB', tuple(d['image_wh']), 'white').save(data, format='PNG')
    image = json.load(self.request('/api/image', data.getvalue(), binary=True))
    d['image_sha256'] = image['sha256']
    d['scope'] = 'INDEPENDENT_PHYSICAL'
    with self.assertRaises(HTTPError):
      self.request('/api/solve', {'capture': d, 'intrinsics_sha256': i['receipt_sha256']})

  def test_missing_measurements_preflight_no_defaults(self):
    with self.assertRaises(HTTPError):
      self.request('/api/prepare', {'fields': {}, 'points': [], 'image': None})
    self.assertFalse((self.session.root / 'capture.json').exists())


if __name__ == '__main__':
  unittest.main()
