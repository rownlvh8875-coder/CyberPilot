"""Real HTTP comparison boundary tests over independently generated synthetic packages."""

import http.client
import json
import socket
import tempfile
from threading import Thread
import unittest

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import cyber_h1_pairing as q
from openpilot.tools.cyber_autotune import cyber_h1_pair_producer as producer
from openpilot.tools.cyber_autotune import cyber_h1_paired_visual_adapter as adapter
from openpilot.tools.cyber_autotune import cyber_h1_comparison_catalog as catalog
from openpilot.tools.cyber_autotune import cyber_h1_comparison_server as server
from openpilot.tools.cyber_autotune import cyber_h1_comparison_publication as public


class TestComparisonHTTP(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.tmp = tempfile.TemporaryDirectory()
    context = q.policy()
    entries = []
    for kind, info in q.CAMPAIGNS.items():
      for spec in context['scenario_rows']:
        name = spec['id']
        packages = [producer.run(kind, arm, name, context)[1] for arm in (q.BASELINE, info[1])]
        pair = q.pair(*packages)
        fs = adapter.convert(*packages)
        catalog.persist_run(cls.tmp.name, kind, name, packages, pair, fs)
        entries.append({'kind': kind, 'scenario': name, 'pair': pair, 'frameset': {k: v for k, v in fs.items() if k != 'frames'}})
    catalog.finish(cls.tmp.name, entries)
    cls.http = server.create_server(cls.tmp.name)
    cls.thread = Thread(target=cls.http.serve_forever, daemon=True)
    cls.thread.start()
    cls.port = cls.http.server_port
    cls.campaign = q.CAMPAIGNS['SG_A'][0]
    cls.prefix = '/api/campaigns/' + cls.campaign + '/scenarios/driver_events'

  @classmethod
  def tearDownClass(cls):
    cls.http.shutdown()
    cls.http.server_close()
    cls.thread.join()
    cls.tmp.cleanup()

  def request(self, path, method='GET', headers=None):
    conn = http.client.HTTPConnection('127.0.0.1', self.port, timeout=10)
    conn.request(method, path, headers=headers or {})
    response = conn.getresponse()
    result = response.status, dict(response.getheaders()), response.read()
    conn.close()
    return result

  def test_two_campaigns_eleven_scenarios(self):
    status, _, body = self.request('/api/campaigns')
    self.assertEqual(status, 200)
    data = json.loads(body)
    self.assertEqual(len(data['campaigns']), 2)
    self.assertTrue(all(len(c['scenarios']) == 11 for c in data['campaigns']))

  def test_both_campaign_metadata_and_scenario_catalog(self):
    for info in q.CAMPAIGNS.values():
      prefix = '/api/campaigns/' + info[0]
      self.assertEqual(self.request(prefix)[0], 200)
      scenarios = json.loads(self.request(prefix + '/scenarios')[2])['scenarios']
      self.assertEqual(len(scenarios), 11)
      for item in scenarios:
        self.assertEqual(self.request(prefix + '/scenarios/' + item['scenario'])[0], 200)

  def test_all_800_frames_paged_in_order(self):
    frames = []
    for offset in range(0, 800, 100):
      status, _, body = self.request(self.prefix + f'/frames?offset={offset}&limit=100')
      self.assertEqual(status, 200)
      frames.extend(json.loads(body)['frames'])
    self.assertEqual([f['frame_index'] for f in frames], list(range(800)))
    self.assertEqual(frames[-1]['completion_time_ns'], 8_000_000_000)

  def test_first_middle_final_frame(self):
    for index in (0, 400, 799):
      status, _, body = self.request(self.prefix + '/frame/' + str(index))
      self.assertEqual(status, 200)
      self.assertEqual(json.loads(body)['frame_index'], index)

  def test_head_no_body_same_length(self):
    for path in (
      '/',
      '/api/campaigns',
      '/api/health',
      '/api/campaigns/' + self.campaign,
      '/api/campaigns/' + self.campaign + '/scenarios',
      self.prefix,
      self.prefix + '/frames',
      self.prefix + '/frame/799',
    ):
      get = self.request(path)
      head = self.request(path, 'HEAD')
      self.assertEqual(head[0], 200)
      self.assertEqual(head[2], b'')
      self.assertEqual(head[1]['Content-Length'], get[1]['Content-Length'])

  def test_mutations_rejected(self):
    for method in ('POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS', 'TRACE', 'CONNECT', 'PROPFIND'):
      self.assertEqual(self.request('/api/campaigns', method)[0], 405)

  def test_host_origin_rejected(self):
    for headers in ({'Host': 'evil.example'}, {'Origin': 'https://evil.example'}, {'Sec-Fetch-Site': 'cross-site'}):
      self.assertEqual(self.request('/api/campaigns', headers=headers)[0], 403)

  def test_duplicate_origin_rejected(self):
    conn = http.client.HTTPConnection('127.0.0.1', self.port)
    conn.putrequest('GET', '/api/campaigns')
    conn.putheader('Origin', f'http://127.0.0.1:{self.port}')
    conn.putheader('Origin', f'http://127.0.0.1:{self.port}')
    conn.endheaders()
    response = conn.getresponse()
    self.assertEqual(response.status, 403)
    response.read()
    conn.close()

  def test_path_traversal_rejected(self):
    for path in ('/../secret', '/%2e%2e/secret', '//evil.example/x', '/api\\secret', 'http://evil.example/api/campaigns'):
      self.assertEqual(self.request(path, headers={'Host': f'127.0.0.1:{self.port}'})[0], 400)

  def test_invalid_bounds_rejected(self):
    for query in (
      'offset=-1',
      'offset=800',
      'offset=01',
      'offset=1.0',
      'offset=true',
      'limit=0',
      'limit=101',
      'limit=100&limit=1',
      'unknown=1',
      'offset=0&',
      'offset=1=2',
    ):
      self.assertEqual(self.request(self.prefix + '/frames?' + query)[0], 400)

  def test_unknown_resources_404(self):
    for path in (
      '/api/campaigns/unknown',
      '/api/campaigns/' + self.campaign + '/scenarios/unknown',
      self.prefix + '/frame/800',
      self.prefix + '/frame/-1',
      '/optimizer',
      '/api/params',
      '/api/device',
      '/api/upload',
    ):
      self.assertEqual(self.request(path)[0], 404)

  def test_security_headers_and_no_cors(self):
    _, headers, _ = self.request('/')
    self.assertIn("default-src 'none'", headers['Content-Security-Policy'])
    self.assertIn("connect-src 'self'", headers['Content-Security-Policy'])
    self.assertEqual(headers['X-Content-Type-Options'], 'nosniff')
    self.assertEqual(headers['Referrer-Policy'], 'no-referrer')
    self.assertNotIn('Access-Control-Allow-Origin', headers)

  def test_nonloopback_bind_rejected(self):
    for host in ('0.0.0.0', '192.168.1.2', 'example.com', '127.0.0.2'):
      with self.assertRaises(ValueError):
        server.create_server(self.tmp.name, host)

  def test_local_catalog_joint_reseal_rejected(self):
    cat = json.loads(p.canonical(self.http.comparison_data['catalog']))
    cat['campaigns'][0]['scenarios'][0]['paired_frameset_sha256'] = '0' * 64
    with self.assertRaisesRegex(ValueError, 'PAIR_FIXED_OUTPUT_DIGEST_SET_DRIFT'):
      public.validate_catalog(q.verify(q.seal({k: v for k, v in cat.items() if k != 'receipt_sha256'})))

  def test_unchanged_single_arm_server_contract(self):
    from openpilot.tools.cyber_autotune.cyber_h1_visual_publication import validate_server_contract

    self.assertEqual(validate_server_contract()['schema'], 'CYBER_H1_VISUAL_SERVER_CONTRACT_V1')

  def test_health_holdout_and_readonly(self):
    row = json.loads(self.request('/api/health')[2])
    self.assertTrue(row['read_only'])
    self.assertEqual(row['opening_count'], 0)
    self.assertEqual(row['holdout_opening'], 'CLOSED')

  def test_no_sensor_value_fabrication_in_api(self):
    frame = json.loads(self.request(self.prefix + '/frame/400')[2])
    for arm in ('baseline', 'candidate'):
      self.assertIsNone(frame[arm]['steering_angle_deg'])
      self.assertIsNone(frame[arm]['torque_output_can'])
      self.assertEqual(frame[arm]['unavailable']['torque_output_can'], 'NO_CARCONTROLLER_OR_CAN_IN_OFFLINE_EXPERIMENT')

  def test_server_shutdown_closes_port(self):
    # The separate secondary socket is closed without disturbing other HTTP tests.
    second = server.ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
    port = second.server_port
    second.server_close()
    with socket.socket() as sock:
      self.assertNotEqual(sock.connect_ex(('127.0.0.1', port)), 0)
