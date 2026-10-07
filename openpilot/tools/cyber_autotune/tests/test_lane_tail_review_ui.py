import io
import json
from pathlib import Path
import tempfile
import threading
import unittest
import urllib.request
import urllib.error

from PIL import Image
from openpilot.tools.cyber_autotune import lane_tail_review_ui as ui
from openpilot.tools.cyber_autotune import lane_tail_review_contract as c
from openpilot.tools.cyber_autotune.native_protocol import canonical, digest
from openpilot.tools.cyber_autotune.lane_tail_report import seal, unseal
from openpilot.tools.cyber_autotune.tests.test_lane_tail_review import fixture


def make_session(root):
  rows, marker = fixture()
  stream = io.BytesIO()
  Image.new('RGB', (20, 12), (80, 80, 80)).save(stream, format='PNG')
  png = stream.getvalue()
  for row in rows:
    core = unseal(row)
    core['image_sha256'] = digest(png)
    row.clear()
    row.update(seal(core))
  core = unseal(marker)
  core['artifact_file_sha256']['ledger.json'] = digest(canonical(rows) + b'\n')
  marker = seal(core)
  m = c.freeze_review(rows, marker, c.selection_policy(), ui.tool_identity(), scope='TEST_ONLY_BROWSER_VALIDATION')

  def loader(frame):
    return {
      'png': png,
      'data': {
        'frame': frame,
        'geometry': [12, 20],
        'lanes': [[[5, 2], [5, 10]], [[15, 2], [15, 10]]],
        'scores': [0.9, 0.8],
        'components': {'count': 2, 'rows': [[(5, 6, 0), (10, 11, 1)] for _ in range(12)]},
        'support_edges': [[0, 0]],
        'same_point_error': {'p95': 2.0},
      },
    }

  return ui.ReviewSession(m, loader, root), m


class TestLaneTailReviewUI(unittest.TestCase):
  def setUp(self):
    self.temp = tempfile.TemporaryDirectory()
    self.session, self.manifest = make_session(Path(self.temp.name))
    self.server = ui.make_server(self.session)
    self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
    self.thread.start()
    self.base = 'http://127.0.0.1:' + str(self.server.server_port)

  def tearDown(self):
    self.server.shutdown()
    self.server.server_close()
    self.thread.join()
    self.temp.cleanup()

  def request(self, path, body=None, headers=None):
    return urllib.request.urlopen(
      urllib.request.Request(
        self.base + path, data=json.dumps(body).encode() if body is not None else None, headers={'Content-Type': 'application/json', **(headers or {})}
      ),
      timeout=5,
    )

  def body(self, index=0):
    return {'index': index, 'label': 'UNRESOLVED', 'reviewable': True, 'comment': 'TEST', 'human_ack': True, 'token': self.session.token}

  def test_loopback_only(self):
    with self.assertRaises(ValueError):
      ui.make_server(self.session, host='0.0.0.0')

  def test_page_and_local_assets(self):
    page = self.request('/').read().decode()
    self.assertIn('NO INDEPENDENT LANE TRUTH', page)
    self.assertIn('taxonomy', page)
    for path in ('/app.js', '/style.css'):
      self.assertEqual(self.request(path).status, 200)
    self.assertIn("default-src 'self'", self.request('/').headers['Content-Security-Policy'])

  def test_frame_and_overlay_geometry(self):
    data = json.load(self.request('/api/frame/0'))
    self.assertEqual(data['components']['count'], 2)
    self.assertEqual(data['same_point_error']['p95'], 2.0)
    self.assertEqual(self.request('/image/0').read()[:8], b'\x89PNG\r\n\x1a\n')

  def test_host_rebinding_rejected(self):
    with self.assertRaises(urllib.error.HTTPError) as cm:
      self.request('/', headers={'Host': 'evil.test'})
    self.assertEqual(cm.exception.code, 403)

  def test_post_requires_origin_and_nonce(self):
    with self.assertRaises(urllib.error.HTTPError) as cm:
      self.request('/api/save', self.body())
    self.assertEqual(cm.exception.code, 403)
    b = self.body()
    b['token'] = 'wrong'
    with self.assertRaises(urllib.error.HTTPError):
      self.request('/api/save', b, {'Origin': self.base})

  def test_save_restart_and_immutability(self):
    result = json.load(self.request('/api/save', self.body(), {'Origin': self.base}))
    self.assertEqual(result['annotation']['scope'], 'TEST_ONLY_BROWSER_VALIDATION')
    session, _ = make_session(Path(self.temp.name))
    self.assertEqual(len(session.annotations()), 1)
    b = self.body()
    b['label'] = 'OTHER'
    with self.assertRaises(urllib.error.HTTPError) as cm:
      self.request('/api/save', b, {'Origin': self.base})
    self.assertEqual(cm.exception.code, 409)

  def test_no_automatic_label(self):
    cfg = json.load(self.request('/api/config'))
    self.assertEqual(cfg['review_status']['reviewed'], 0)
    self.assertEqual(json.load(self.request('/api/frame/0'))['annotation'], None)

  def test_unknown_paths_and_indices_rejected(self):
    for path in ('/image/../../secret', '/api/frame/-1', '/api/frame/999', '/image/00'):
      with self.subTest(path=path), self.assertRaises(urllib.error.HTTPError):
        self.request(path)

  def test_public_byte_corruption_fail_closed(self):
    self.session.loader = lambda frame: {'png': b'corrupt', 'data': {'frame': frame}}
    with self.assertRaises(urllib.error.HTTPError):
      self.request('/image/0')
    with self.assertRaises(urllib.error.HTTPError):
      self.request('/api/save', self.body(), {'Origin': self.base})

  def test_manifest_tool_mismatch_rejected(self):
    x = unseal(self.manifest)
    x['review_tool_sha256'] = 'f' * 64
    with self.assertRaises(ValueError):
      ui.ReviewSession(seal(x), self.session.loader, Path(self.temp.name) / 'other')

  def test_saved_row_corruption_rejected(self):
    self.request('/api/save', self.body(), {'Origin': self.base}).close()
    path = next((Path(self.temp.name) / 'annotations').glob('*.json'))
    path.write_text('{}')
    with self.assertRaises(ValueError):
      self.session.annotations()

  def test_clean_shutdown(self):
    self.assertEqual(self.server.server_address[0], '127.0.0.1')

  def test_missing_indexed_annotation_cannot_be_replaced(self):
    self.request('/api/save', self.body(), {'Origin': self.base}).close()
    path = next((Path(self.temp.name) / 'annotations').glob('*.json'))
    path.unlink()
    with self.assertRaises(ValueError):
      self.session.annotations()
    with self.assertRaises(ValueError):
      self.session.save(self.body())

  def test_orphan_row_before_index_recovers_without_overwrite(self):
    original = (Path(self.temp.name) / 'review-index.json').read_bytes()
    self.request('/api/save', self.body(), {'Origin': self.base}).close()
    (Path(self.temp.name) / 'review-index.json').write_bytes(original)
    session, _ = make_session(Path(self.temp.name))
    self.assertEqual(len(session.annotations()), 1)
    indexed = json.loads((Path(self.temp.name) / 'review-index.json').read_bytes())
    self.assertEqual(indexed['rows'], [session.annotations()[0]['receipt_sha256']])
    with self.assertRaises(FileExistsError):
      session.save({**self.body(), 'token': session.token})
    next((Path(self.temp.name) / 'annotations').glob('*.json')).unlink()
    with self.assertRaises(ValueError):
      session.annotations()

  def test_overlay_dependencies_bound(self):
    from unittest.mock import patch

    identities = ui.helper_source_hashes()
    self.assertIn('lane_marking_metrics.py', identities)
    changed = {**identities, 'lane_marking_metrics.py': 'f' * 64}
    with patch.object(ui, 'helper_source_hashes', return_value=changed):
      with self.assertRaises(ValueError):
        self.session.frame(0)

  def test_navigation_uses_request_token(self):
    self.assertIn('requestId', ui.JS)
    self.assertIn('await image.decode()', ui.JS)

  def test_non_object_json_rejected(self):
    with self.assertRaises(urllib.error.HTTPError) as cm:
      self.request('/api/save', [], {'Origin': self.base})
    self.assertEqual(cm.exception.code, 400)
