import json
import threading
import unittest
import urllib.error
import urllib.request

from openpilot.tools.cyber_autotune import controller_plant_visualizer as v


class TestAuthorityVisualizer(unittest.TestCase):
  def test_loopback_only(self):
    with self.assertRaises(ValueError):
      v.make_server(host='0.0.0.0')

  def test_hidden_network_assets(self):
    page = v.ASSET_BYTES['index.html'].decode()
    self.assertNotIn('https://', page)
    self.assertIn('NOT CANDIDATE ACCEPTANCE', page)

  def test_api_and_shutdown(self):
    server = v.make_server()
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    base = 'http://127.0.0.1:' + str(server.server_port)
    try:
      with urllib.request.urlopen(base + '/api/plant-authority') as response:
        row = json.load(response)
      self.assertFalse(row['audit']['qualification_allowed'])
      self.assertEqual(len(row['stage']['rows']), 33)
      request = urllib.request.Request(base + '/api/plant-authority', headers={'Origin': 'https://example.invalid'})
      with self.assertRaises(urllib.error.HTTPError) as err:
        urllib.request.urlopen(request)
      self.assertEqual(err.exception.code, 403)
    finally:
      server.shutdown()
      server.server_close()
      thread.join(3)
    self.assertFalse(thread.is_alive())
