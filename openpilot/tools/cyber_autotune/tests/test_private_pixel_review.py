import json
from pathlib import Path
import tempfile
import unittest
from urllib.request import urlopen
from urllib.error import HTTPError

from openpilot.tools.cyber_autotune import private_pixel_review as ui
from openpilot.tools.cyber_autotune import private_pixel_execution as p
from openpilot.tools.cyber_autotune.tests import test_private_pixel_execution as fixture


class TestPrivateReview(unittest.TestCase):
  def test_page_has_nonqualifying_and_unopened_holdout_labels(self):
    self.assertIn('PRIVATE PIXEL DIAGNOSTIC ONLY', ui.HTML)
    self.assertIn('HOLDOUT NOT OPENED', ui.HTML)
    self.assertNotIn('https://', ui.HTML)
    self.assertNotIn('http://', ui.HTML)
    self.assertNotIn('fetch(', ui.HTML.replace("fetch('/data')", '').replace("fetch('/frame/'+index)", ''))

  def test_server_refuses_external_bind(self):
    with tempfile.TemporaryDirectory() as temp, self.assertRaises(ValueError):
      with ui.server(Path(temp), bind='0.0.0.0'):
        self.fail('external bind allowed')

  def test_http_fixture_navigation_no_external_sources(self):
    case = fixture.TestPrivateExecution()
    case.setUp()
    with tempfile.TemporaryDirectory() as temp:
      root = Path(temp)
      p.immutable_json(root/'manifest.json', case.manifest)
      p.immutable_json(root/'authorization.json', case.auth)
      import threading
      with ui.server(root) as srv:
        worker = threading.Thread(target=srv.serve_forever, daemon=True)
        worker.start()
        try:
          base = f'http://127.0.0.1:{srv.server_port}'
          page = urlopen(base, timeout=5)
          self.assertIn("default-src 'none'", page.headers['Content-Security-Policy'])
          value = json.loads(urlopen(base+'/data', timeout=5).read())
          self.assertEqual(len(value['frames']), 15)
          self.assertEqual(value['human_status'], 'PRIVATE_HUMAN_HOLDOUT_PENDING')
          self.assertNotIn('source_key', str(value))
          with self.assertRaises(HTTPError):
            urlopen(base+'/frame/4', timeout=5)  # HOLDOUT must not materialize.
          with self.assertRaises(HTTPError):
            urlopen(base+'/../manifest.json', timeout=5)
        finally:
          srv.shutdown()
          worker.join()
