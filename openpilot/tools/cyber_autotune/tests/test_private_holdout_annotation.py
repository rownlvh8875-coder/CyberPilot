import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from openpilot.tools.cyber_autotune import private_holdout_annotation as ui
from openpilot.tools.cyber_autotune import private_holdout_contract as h
from openpilot.tools.cyber_autotune.tests.test_private_holdout_contract import setup_package, payload


class TestBlindAnnotation(unittest.TestCase):
  def setUp(self):
    self.temp = tempfile.TemporaryDirectory(dir=Path.home())
    self.root = Path(self.temp.name)
    _, _, self.package = setup_package(self.root)
    h.write_immutable(self.root / 'materialization.json', self.package)
    self.store = ui.ReviewStore(self.root)
    self.addCleanup(self.temp.cleanup)

  def test_zero_human_and_no_hidden_predictions(self):
    self.assertEqual(self.store.progress()['reviewed'], 0)
    serialized = json.dumps(self.store.view())
    for key in ('confidence', 'prediction', 'development_result', 'stratum', 'approx_geometry', 'ai_suggestion'):
      self.assertNotIn(key, serialized)

  def test_immutable_first_decision_and_refresh(self):
    first = self.store.save(0, payload())
    self.assertEqual(ui.ReviewStore(self.root).progress()['reviewed'], 1)
    with self.assertRaises(ValueError):
      self.store.save(0, {**payload(), 'reviewer_id': 'other'})
    self.assertEqual(self.store.first(0), first)

  def test_editable_draft_not_completion(self):
    body = payload()
    body['left'] = [[100., 300.]]
    self.store.draft(0, body)
    body['left'].append([120., 200.])
    self.store.draft(0, body)
    self.assertEqual(ui.ReviewStore(self.root).load_draft(0)['left'], body['left'])
    self.assertEqual(self.store.progress()['reviewed'], 0)

  def test_saved_draft_no_overwrite(self):
    self.store.save(0, payload())
    with self.assertRaises(ValueError):
      self.store.draft(0, payload())

  def test_correction_separate_from_first_and_primary_freeze(self):
    first = self.store.save(0, payload())
    changed = payload()
    changed['left'][0][0] = 95.
    correction = self.store.correct(0, changed, 'manual placement correction')
    self.assertEqual(self.store.first(0), first)
    self.assertEqual(correction['first_decision_sha256'], first['receipt_sha256'])

  def test_incomplete_cannot_reveal_even_saved_frame(self):
    self.store.save(0, payload())
    with self.assertRaises(ValueError):
      self.store.require_comparison()

  def test_sixty_first_decisions_freeze_reference(self):
    for i in range(60):
      self.store.save(i, payload())
    self.store.require_comparison()
    self.assertEqual(self.store.progress()['status'], 'PRIVATE_BLIND_HUMAN_HOLDOUT_COMPLETE')
    self.assertTrue((self.root / 'human-reference.json').exists())

  def test_unknown_extra_annotation_fails_closed(self):
    row = self.store.save(0, payload())
    h.write_immutable(self.root / 'annotations' / 'unknown.json', row)
    with self.assertRaises(ValueError):
      self.store.progress()

  def test_body_extra_detector_field_rejected(self):
    with self.assertRaises(ValueError):
      self.store.save(0, {**payload(), 'detector': {}})

  def test_loopback_required(self):
    with self.assertRaises(ValueError):
      ui.server(self.root, bind='0.0.0.0').__enter__()

  def test_http_detector_403_before_and_after_one_save(self):
    with ui.server(self.root) as server:
      thread = threading.Thread(target=server.serve_forever)
      thread.start()
      base = 'http://127.0.0.1:' + str(server.server_port)
      try:
        data = json.load(urlopen(base + '/data', timeout=3))
        for route in ('/detector/0', '/ai/0', '/development/0'):
          with self.assertRaises(HTTPError) as error:
            urlopen(base + route, timeout=3)
          self.assertEqual(error.exception.code, 403)
        body = {'image_receipt_sha256': self.package['images'][0]['receipt_sha256'], 'annotation': payload()}
        req = Request(base + '/save/0', data=json.dumps(body).encode(), headers={
          'Content-Type': 'application/json', 'X-Review-Token': data['token']})
        row = json.load(urlopen(req, timeout=3))
        self.assertEqual(row['schema'], 'PRIVATE_BLIND_PIXEL_FIRST_DECISION_V1')
        with self.assertRaises(HTTPError) as error:
          urlopen(base + '/detector/0', timeout=3)
        self.assertEqual(error.exception.code, 403)
        with self.assertRaises(HTTPError):
          urlopen(Request(base + '/save/1', data=b'{}', headers={'Content-Type': 'application/json'}), timeout=3)
        self.assertEqual(json.load(urlopen(base + '/data', timeout=3))['progress']['reviewed'], 1)
      finally:
        server.shutdown()
        thread.join()


  def test_sixtieth_row_crash_window_recovers_reference(self):
    for i in range(60):
      self.store.save(i, payload())
    reference = self.root / 'human-reference.json'
    reference.unlink()  # Process died after durable last row, before marker.
    restarted = ui.ReviewStore(self.root)
    restarted.require_comparison()
    self.assertEqual(restarted.progress()['reviewed'], 60)

  def test_saved_set_missing_row_cannot_reveal(self):
    for i in range(60):
      self.store.save(i, payload())
    image = self.package['images'][0]
    (self.root / 'annotations' / (image['sample_id'] + '.json')).unlink()
    with self.assertRaises(ValueError):
      self.store.require_comparison()

  def test_http_stale_frame_envelope_rejected(self):
    with ui.server(self.root) as server:
      thread = threading.Thread(target=server.serve_forever)
      thread.start()
      base = 'http://127.0.0.1:' + str(server.server_port)
      try:
        data = json.load(urlopen(base + '/data', timeout=3))
        body = {'image_receipt_sha256': self.package['images'][0]['receipt_sha256'], 'annotation': payload()}
        req = Request(base + '/save/1', data=json.dumps(body).encode(), headers={
          'Content-Type': 'application/json', 'X-Review-Token': data['token']})
        with self.assertRaises(HTTPError):
          urlopen(req, timeout=3)
        self.assertEqual(self.store.progress()['reviewed'], 0)
      finally:
        server.shutdown()
        thread.join()


  def test_http_raw_bytes_are_same_payload_as_hash_verified(self):
    image = self.package['images'][0]
    path = self.root / 'images' / (image['sample_id'] + '.png')
    def racing_hash(_path):
      path.write_bytes(b'changed-between-reads')
      return image['image_sha256']
    with ui.server(self.root) as server:
      thread = threading.Thread(target=server.serve_forever)
      thread.start()
      try:
        base = 'http://127.0.0.1:' + str(server.server_port)
        with patch.object(ui.encoded, 'hash_file', side_effect=racing_hash):
          response = urlopen(base + '/image/0', timeout=3).read()
        self.assertEqual(h.digest(response), image['image_sha256'])
      finally:
        server.shutdown()
        thread.join()

  def test_asset_policy_and_ui_controls(self):
    self.assertNotIn('https://', ui.HTML)
    self.assertNotIn('http://', ui.HTML)
    for identifier in ('zoom', 'undo', 'clear-left', 'clear-right', 'prev', 'next', 'draft', 'save', 'jump', 'pan-mode'):
      self.assertIn('id="' + identifier + '"', ui.HTML)
    self.assertIn("default-src 'none'", ui.CSP)
