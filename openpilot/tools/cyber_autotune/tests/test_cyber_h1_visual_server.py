"""Real loopback HTTP boundary tests; no browser or raw route dependency."""

import http.client
from pathlib import Path
import tempfile
from threading import Thread
import unittest

from openpilot.tools.cyber_autotune import cyber_h1_visual_server as s
from openpilot.tools.cyber_autotune import cyber_h1_visual_adapter as a
from openpilot.tools.cyber_autotune import cyber_h1_visual_catalog as cat
from openpilot.tools.cyber_autotune import cyber_lateral_h1_experiment as e


class TestVisualHTTP(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.tmp = tempfile.TemporaryDirectory()
    _, package = e.run_once()
    cat.persist(cls.tmp.name, a.convert(package))
    cls.server = s.create_server(cls.tmp.name, '127.0.0.1', 0)
    cls.thread = Thread(target=cls.server.serve_forever, daemon=True)
    cls.thread.start()
    cls.port = cls.server.server_port
    cls.route_id = cls.server.visual_data['run_id']

  @classmethod
  def tearDownClass(cls):
    cls.server.shutdown()
    cls.server.server_close()
    cls.thread.join()
    cls.tmp.cleanup()

  def request(self, path, method='GET', headers=None):
    conn = http.client.HTTPConnection('127.0.0.1', self.port, timeout=5)
    conn.request(method, path, headers=headers or {})
    response = conn.getresponse()
    result = response.status, dict(response.getheaders()), response.read()
    conn.close()
    return result

  def test_catalog_run_frame_pages(self):
    import json

    self.assertEqual(self.request('/api/catalog')[0], 200)
    self.assertEqual(self.request('/api/runs/' + self.route_id)[0], 200)
    frames = []
    for offset in range(0, 800, 100):
      status, _, body = self.request('/api/runs/' + self.route_id + f'/frames?offset={offset}&limit=100')
      self.assertEqual(status, 200)
      frames.extend(json.loads(body)['frames'])
    self.assertEqual([f['frame_index'] for f in frames], list(range(800)))
    self.assertEqual(frames[-1]['completion_time_ns'], 8_000_000_000)

  def test_head_same_headers_no_body(self):
    for path in (
      '/',
      '/api/catalog',
      '/api/health',
      '/api/runs/' + self.route_id,
      '/api/runs/' + self.route_id + '/frames',
      '/api/runs/' + self.route_id + '/frame/799',
    ):
      get = self.request(path)
      head = self.request(path, 'HEAD')
      self.assertEqual(head[0], 200)
      self.assertEqual(head[2], b'')
      self.assertEqual(head[1]['Content-Length'], get[1]['Content-Length'])

  def test_mutations_405(self):
    for method in ('POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS', 'TRACE', 'CONNECT', 'PROPFIND'):
      self.assertEqual(self.request('/api/catalog', method)[0], 405)

  def test_wrong_host(self):
    self.assertEqual(self.request('/api/catalog', headers={'Host': 'evil.example'})[0], 403)

  def test_wrong_origin(self):
    self.assertEqual(self.request('/api/catalog', headers={'Origin': 'https://evil.example'})[0], 403)

  def test_cross_site_rejected(self):
    self.assertEqual(self.request('/api/catalog', headers={'Sec-Fetch-Site': 'cross-site'})[0], 403)

  def test_non_loopback_bind_rejected(self):
    for host in ('0.0.0.0', '192.168.1.1', 'example.com', '127.0.0.2'):
      with self.assertRaises(ValueError):
        s.create_server(self.tmp.name, host, 0)

  def test_traversal(self):
    for path in ('/../manifest.json', '/%2e%2e/manifest.json', '//api/catalog', '/static/../../manifest.json'):
      self.assertEqual(self.request(path)[0], 400)

  def test_unknown_routes(self):
    for path in ('/api/runs/' + '0' * 64, '/api/runs/' + self.route_id + '/frame/800', '/api/optimizer', '/api/params', '/api/upload'):
      self.assertEqual(self.request(path)[0], 404)

  def test_bounds(self):
    for query in (
      'offset=-1',
      'offset=800',
      'offset=1.5',
      'offset=01',
      'limit=0',
      'limit=101',
      'limit=abc',
      'offset=0&offset=1',
      'foo=1',
      'offset=%31',
      'limit=99999999999999999',
    ):
      self.assertEqual(self.request('/api/runs/' + self.route_id + '/frames?' + query)[0], 400)

  def test_security_headers(self):
    _, headers, _ = self.request('/')
    self.assertEqual(headers['X-Content-Type-Options'], 'nosniff')
    self.assertEqual(headers['Referrer-Policy'], 'no-referrer')
    self.assertIn("default-src 'none'", headers['Content-Security-Policy'])
    self.assertNotIn('Access-Control-Allow-Origin', headers)

  def test_null_and_tier(self):
    import json

    meta = json.loads(self.request('/api/runs/' + self.route_id)[2])
    frame = json.loads(self.request('/api/runs/' + self.route_id + '/frame/0')[2])
    self.assertIsNone(frame['torque_output_can'])
    self.assertFalse(meta['comparison_ready'])
    self.assertEqual(meta['evidence_tier'], 'T1_DESCRIPTIVE_COUNTERFACTUAL')
    self.assertEqual(meta['opening_count'], 0)

  def test_static_and_health(self):
    for path in ('/', '/static/cyber_h1_visual.js', '/static/cyber_h1_visual.css', '/api/health'):
      self.assertEqual(self.request(path)[0], 200)
    self.assertEqual(self.request('/favicon.ico')[0], 204)

  def test_symlink_store(self):
    with tempfile.TemporaryDirectory() as folder:
      path = Path(folder) / 'link'
      path.symlink_to(self.tmp.name, target_is_directory=True)
      with self.assertRaises(ValueError):
        s.create_server(path, '127.0.0.1', 0)

  def test_duplicate_origin_rejected(self):
    conn = http.client.HTTPConnection('127.0.0.1', self.port, timeout=5)
    conn.putrequest('GET', '/api/health')
    conn.putheader('Origin', f'http://127.0.0.1:{self.port}')
    conn.putheader('Origin', 'http://untrusted.invalid')
    conn.endheaders()
    response = conn.getresponse()
    self.assertEqual(response.status, 403)
    response.read()
    conn.close()
