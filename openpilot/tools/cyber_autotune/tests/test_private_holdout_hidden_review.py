import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from openpilot.tools.cyber_autotune import private_holdout_contract as h
from openpilot.tools.cyber_autotune import private_holdout_annotation as old
from openpilot.tools.cyber_autotune.tests.test_private_holdout_contract import setup_package, payload
from openpilot.tools.cyber_autotune.tests.test_private_holdout_hidden import prediction
from openpilot.tools.cyber_autotune.tests.test_private_pixel_execution import STAMP, SHA


class TestHiddenReview(unittest.TestCase):
  def setUp(self):
    try:
      from openpilot.tools.cyber_autotune import private_holdout_hidden_review as review
      from openpilot.tools.cyber_autotune import private_holdout_hidden as hidden
    except ImportError:
      self.fail('Per-frame first-save hidden comparison interface is not implemented')
    self.review, self.hidden = review, hidden
    self.temp = tempfile.TemporaryDirectory(dir=Path.home())
    self.addCleanup(self.temp.cleanup)
    self.root = Path(self.temp.name) / 'raw'
    self.output = Path(self.temp.name) / 'hidden'
    self.root.mkdir()
    self.output.mkdir()
    _, _, self.package = setup_package(self.root)
    h.write_immutable(self.root / 'materialization.json', self.package)
    self.auth = hidden.authorize(self.package, SHA[:40], STAMP, acknowledged=True)
    h.write_immutable(self.output / 'authorization.json', self.auth)
    self.row = hidden.detector_row(self.package, self.auth, 0, prediction(), prediction(), STAMP)
    h.write_immutable(self.output / 'rows' / (self.row['sample_id'] + '.json'), self.row)
    self.store = review.ComparisonStore(self.root, self.output)

  def test_pre_save_cannot_read_even_computed_row(self):
    with self.assertRaises(ValueError):
      self.store.visible(0)
    self.assertEqual(self.store.human.progress()['reviewed'], 0)

  def test_after_save_one_frame_only_reveal_no_sixty_requirement(self):
    self.store.human.save(0, payload())
    value = self.store.visible(0)
    self.assertEqual(value['detector']['lanes'], prediction()['lanes'])
    self.assertTrue(value['provenance']['blind_human_review'])
    self.assertFalse(value['provenance']['ai_exposed_before_human'])
    with self.assertRaises(ValueError):
      self.store.visible(1)
    self.assertEqual(self.store.human.progress()['reviewed'], 1)

  def test_pre_save_response_has_no_hint(self):
    raw = json.dumps(self.store.human.view())
    for word in ('confidence', 'suggested_state', 'prediction', 'lane_count', 'development_result'):
      self.assertNotIn(word, raw)

  def test_missing_hidden_artifact_does_not_prevent_blind_human_save(self):
    self.store.human.save(1, payload())
    self.assertEqual(self.store.human.progress()['reviewed'], 1)
    with self.assertRaises(ValueError):
      self.store.visible(1)

  def test_stale_prediction_cannot_reveal(self):
    self.store.human.save(0, payload())
    path = self.output / 'rows' / (self.row['sample_id'] + '.json')
    row = h.unseal(self.row)
    row['image_sha256'] = 'b' * 64
    path.write_bytes(h.canonical(h.seal(row)))
    with self.assertRaises(ValueError):
      self.store.visible(0)

  def test_http_403_pre_save_and_success_after_save(self):
    with self.review.server(self.root, self.output) as server:
      thread = threading.Thread(target=server.serve_forever)
      thread.start()
      base = 'http://127.0.0.1:' + str(server.server_port)
      try:
        data = json.load(urlopen(base + '/data', timeout=3))
        for endpoint in ('/detector/0', '/ai/0', '/comparison/0'):
          with self.assertRaises(HTTPError) as err:
            urlopen(base + endpoint, timeout=3)
          self.assertEqual(err.exception.code, 403)
        req = Request(
          base + '/save/0',
          data=json.dumps({'image_receipt_sha256': self.package['images'][0]['receipt_sha256'], 'annotation': payload()}).encode(),
          headers={'Content-Type': 'application/json', 'X-Review-Token': data['token']},
        )
        first = json.load(urlopen(req, timeout=3))
        visible = json.load(urlopen(base + '/comparison/0', timeout=3))
        self.assertEqual(visible['provenance']['first_decision_sha256'], first['receipt_sha256'])
        with self.assertRaises(HTTPError) as err:
          urlopen(base + '/detector/1', timeout=3)
        self.assertEqual(err.exception.code, 403)
        restart = self.review.ComparisonStore(self.root, self.output)
        self.assertEqual(restart.human.first(0), first)
      finally:
        server.shutdown()
        thread.join()

  def test_comparison_cannot_overwrite_annotation(self):
    first = self.store.human.save(0, payload())
    self.store.visible(0)
    self.assertEqual(old.ReviewStore(self.root).first(0), first)

  def test_no_external_assets_and_overlay_hidden_default(self):
    self.assertNotIn('https://', self.review.HTML)
    self.assertNotIn('http://', self.review.HTML)
    self.assertIn('hiddenComparison=null', self.review.HTML)
    self.assertIn('stamp!==generation', self.review.HTML)

  def test_no_private_store_inside_raw_root(self):
    with self.assertRaises(ValueError):
      self.review.ComparisonStore(self.root, self.root / 'hidden')

  def test_human_save_binds_provenance_without_revealing_output(self):
    with self.review.server(self.root, self.output) as server:
      thread = threading.Thread(target=server.serve_forever)
      thread.start()
      base = 'http://127.0.0.1:' + str(server.server_port)
      try:
        data = json.load(urlopen(base + '/data', timeout=3))
        req = Request(
          base + '/save/0',
          data=json.dumps({'image_receipt_sha256': self.package['images'][0]['receipt_sha256'], 'annotation': payload()}).encode(),
          headers={'Content-Type': 'application/json', 'X-Review-Token': data['token']},
        )
        first = json.load(urlopen(req, timeout=3))
        self.assertNotIn('prediction', first)
        self.assertNotIn('confidence', first)
        receipts = list((self.output / 'relations' / first['receipt_sha256']).glob('*.json'))
        self.assertEqual(len(receipts), 1)
        relation = h.read(receipts[0])
        self.assertTrue(relation['blind_human_review'])
        self.assertTrue(relation['detector_computed_before_human'])
      finally:
        server.shutdown()
        thread.join()

  def test_missing_prediction_does_not_turn_valid_human_save_into_error(self):
    with self.review.server(self.root, self.output) as server:
      thread = threading.Thread(target=server.serve_forever)
      thread.start()
      base = 'http://127.0.0.1:' + str(server.server_port)
      try:
        data = json.load(urlopen(base + '/data', timeout=3))
        req = Request(
          base + '/save/1',
          data=json.dumps({'image_receipt_sha256': self.package['images'][1]['receipt_sha256'], 'annotation': payload()}).encode(),
          headers={'Content-Type': 'application/json', 'X-Review-Token': data['token']},
        )
        first = json.load(urlopen(req, timeout=3))
        self.assertEqual(first['schema'], 'PRIVATE_BLIND_PIXEL_FIRST_DECISION_V1')
        pending = self.output / 'relation-pending' / (first['receipt_sha256'] + '.json')
        self.assertTrue(pending.exists())
        with self.assertRaises(HTTPError) as err:
          urlopen(base + '/comparison/1', timeout=3)
        self.assertEqual(err.exception.code, 409)
      finally:
        server.shutdown()
        thread.join()

  def test_pending_storage_error_preserves_durable_human_save(self):
    (self.output / 'relation-pending').write_text('synthetic conflicting file')
    with self.review.server(self.root, self.output) as server:
      thread = threading.Thread(target=server.serve_forever)
      thread.start()
      base = 'http://127.0.0.1:' + str(server.server_port)
      try:
        data = json.load(urlopen(base + '/data', timeout=3))
        req = Request(
          base + '/save/1',
          data=json.dumps({'image_receipt_sha256': self.package['images'][1]['receipt_sha256'], 'annotation': payload()}).encode(),
          headers={'Content-Type': 'application/json', 'X-Review-Token': data['token']},
        )
        first = json.load(urlopen(req, timeout=3))
        self.assertEqual(self.store.human.first(1), first)
        with self.assertRaises(HTTPError) as err:
          urlopen(base + '/comparison/1', timeout=3)
        self.assertEqual(err.exception.code, 409)
      finally:
        server.shutdown()
        thread.join()
