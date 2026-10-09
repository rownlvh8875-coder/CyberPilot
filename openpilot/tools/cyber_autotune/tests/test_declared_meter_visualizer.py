import json
import threading
import unittest
from urllib.request import urlopen, Request
from urllib.error import HTTPError

from openpilot.tools.cyber_autotune import declared_meter_visualizer as v


class TestDeclaredMeterVisualizer(unittest.TestCase):
  def test_loopback_only(self):
    with self.assertRaises(ValueError):
      v.make_server(host='0.0.0.0')

  def test_loopback_meter_section(self):
    s = v.make_server(report=v.synthetic_report(), scope='TEST_ONLY')
    t = threading.Thread(target=s.serve_forever, daemon=True)
    t.start()
    root = 'http://127.0.0.1:' + str(s.server_port)
    try:
      with urlopen(root + '/meter') as r:
        data = r.read().decode()
        self.assertIn('CONDITIONAL / NON-QUALIFYING', data)
        self.assertIn('NO INDEPENDENT METER TRUTH', data)
        self.assertNotIn('https://', data)
        self.assertIn("script-src 'self'", r.headers['Content-Security-Policy'])
      with urlopen(root + '/api/meter') as r:
        self.assertEqual(json.load(r)['status'], 'CONDITIONAL_DIAGNOSTIC_COMPLETE')
      with urlopen(root + '/') as r:
        self.assertIn('href="/meter"', r.read().decode())
      with self.assertRaises(HTTPError) as err:
        urlopen(Request(root + '/api/meter', headers={'Host': 'evil.invalid'}))
      self.assertEqual(err.exception.code, 403)
    finally:
      s.shutdown()
      s.server_close()
      t.join(3)
      self.assertFalse(t.is_alive())

  def test_arbitrary_report_injection_rejected(self):
    x = v.synthetic_report()
    x['private_path'] = '/synthetic/private'
    with self.assertRaises(ValueError):
      v.make_server(report=x, scope='TEST_ONLY')


if __name__ == '__main__':
  unittest.main()
