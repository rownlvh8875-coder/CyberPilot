import copy
import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from openpilot.tools.cyber_autotune import private_holdout_contract as h
from openpilot.tools.cyber_autotune import private_holdout_assisted as a
from openpilot.tools.cyber_autotune import private_holdout_annotation as blind
from openpilot.tools.cyber_autotune.tests.test_private_holdout_contract import setup_package
from openpilot.tools.cyber_autotune.tests.test_private_pixel_execution import SHA, STAMP


class TestAssistedReview(unittest.TestCase):
  def setUp(self):
    from openpilot.tools.cyber_autotune import private_holdout_assisted_review as ui
    if not hasattr(ui, 'Store'):
      self.fail('Separate assisted review store/UI is not implemented')
    self.ui = ui
    self.temp = tempfile.TemporaryDirectory(dir=Path.home())
    self.addCleanup(self.temp.cleanup)
    self.raw, self.output = Path(self.temp.name) / 'raw', Path(self.temp.name) / 'assisted'
    self.raw.mkdir()
    _, _, self.package = setup_package(self.raw)
    h.write_immutable(self.raw / 'materialization.json', self.package)
    self.auth = a.authorize(self.package, SHA[:40], STAMP, acknowledged=True)
    h.write_immutable(self.output / 'authorization.json', self.auth)
    body = {'state': 'BOTH_EGO_BOUNDARIES_VISIBLE', 'left': [[100, 300], [110, 200], [120, 100]],
            'right': [[400, 300], [390, 200], [380, 100]], 'reason': 'Synthetic fixture', 'confidence': 'LOW'}
    self.ai = a.ai_row(self.package, self.auth, 0, body, STAMP, observation_id='synthetic-test-only')
    h.write_immutable(self.output / 'ai' / (self.ai['sample_id'] + '.json'), self.ai)
    self.body = {'action': 'ACCEPT_AI', 'state': body['state'], 'left': body['left'], 'right': body['right'],
                 'reviewer_id': 'reviewer-1', 'acknowledged_assisted': True, 'comment': ''}
    self.store = ui.Store(self.raw, self.output)

  def test_sixty_ai_not_human_completion(self):
    self.assertEqual(self.store.progress()['human_verified'], 0)
    self.assertEqual(self.store.progress()['ai_generated'], 1)
    with self.assertRaises(ValueError):
      self.store.reference()

  def test_save_does_not_write_blind_history(self):
    self.store.save(0, self.body)
    self.assertEqual(self.store.progress()['human_verified'], 1)
    self.assertEqual(blind.ReviewStore(self.raw).progress()['reviewed'], 0)

  def test_save_immutable_and_restart(self):
    row = self.store.save(0, self.body)
    changed = copy.deepcopy(self.body)
    changed['left'][0][0] += 1
    changed['action'] = 'MODIFY_AI'
    with self.assertRaises(ValueError):
      self.store.save(0, changed)
    self.assertEqual(self.ui.Store(self.raw, self.output).first(0), row)

  def test_unknown_store_rows_rejected(self):
    h.write_immutable(self.output / 'ai' / ('b' * 64 + '.json'), self.ai)
    with self.assertRaises(ValueError):
      self.store.progress()

  def test_draft_editable_not_completion(self):
    self.store.draft(0, self.body)
    changed = copy.deepcopy(self.body)
    changed['action'] = 'MODIFY_AI'
    changed['left'][0][0] += 1
    self.store.draft(0, changed)
    self.assertEqual(self.store.view(0)['draft']['left'][0][0], 101)
    self.assertEqual(self.store.progress()['human_verified'], 0)

  def test_output_cannot_be_nested_in_raw(self):
    with self.assertRaises(ValueError):
      self.ui.Store(self.raw, self.raw / 'assisted')

  def test_http_ai_available_but_detector403_until_explicit_human(self):
    with self.ui.server(self.raw, self.output) as server:
      worker = threading.Thread(target=server.serve_forever)
      worker.start()
      try:
        base = 'http://127.0.0.1:' + str(server.server_port)
        data = json.load(urlopen(base + '/data'))
        view = json.load(urlopen(base + '/annotation/0'))
        self.assertEqual(view['ai']['human_verified'], False)
        with self.assertRaises(HTTPError) as err:
          urlopen(base + '/detector/0')
        self.assertEqual(err.exception.code, 403)
        payload = {'image_receipt_sha256': self.ai['image_receipt_sha256'], 'annotation': self.body}
        req = Request(base + '/save/0', data=json.dumps(payload).encode(),
                      headers={'Content-Type': 'application/json', 'X-Review-Token': data['token']})
        final = json.load(urlopen(req))
        self.assertTrue(final['assisted_human'])
        self.assertFalse(final['blind_human'])
        # No detector cache in this fixture: save remains durable, comparison409.
        with self.assertRaises(HTTPError) as err:
          urlopen(base + '/detector/0')
        self.assertEqual(err.exception.code, 409)
      finally:
        server.shutdown()
        worker.join()

  def test_assisted_server_does_not_recover_or_depend_on_blind_history(self):
    path = self.raw / 'annotations' / ('b' * 64 + '.json')
    path.parent.mkdir()
    path.write_text('Unrelated blind store corruption must not be consumed by assisted reader')
    with self.ui.server(self.raw, self.output):
      pass
    self.assertFalse((self.raw / 'human-reference.json').exists())
    self.assertEqual(path.read_text(), 'Unrelated blind store corruption must not be consumed by assisted reader')

  def test_http_stale_image_and_bad_token(self):
    with self.ui.server(self.raw, self.output) as server:
      worker = threading.Thread(target=server.serve_forever)
      worker.start()
      try:
        base = 'http://127.0.0.1:' + str(server.server_port)
        data = json.load(urlopen(base + '/data'))
        for sha, token, code in (('b' * 64, data['token'], 409), (self.ai['image_receipt_sha256'], 'wrong', 403)):
          req = Request(base + '/save/0', data=json.dumps({'image_receipt_sha256': sha, 'annotation': self.body}).encode(),
                        headers={'Content-Type': 'application/json', 'X-Review-Token': token})
          with self.assertRaises(HTTPError) as err:
            urlopen(req)
          self.assertEqual(err.exception.code, code)
        self.assertEqual(self.store.progress()['human_verified'], 0)
      finally:
        server.shutdown()
        worker.join()


if __name__ == '__main__':
  unittest.main()
