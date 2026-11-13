import http.client
import os
import tempfile
import threading
import unittest
from pathlib import Path

from openpilot.system.cyberpilot_web.server import create_server, init_token, load_token
from openpilot.system.cyberpilot_web.telemetry import HostCollector, Store


class CredentialTests(unittest.TestCase):
  def setUp(self):
    self.temp = tempfile.TemporaryDirectory()
    self.addCleanup(self.temp.cleanup)
    self.path = Path(self.temp.name) / "token"

  def test_random_private_and_reusable(self):
    token = init_token(self.path)
    self.assertGreaterEqual(len(token), 43)
    self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)
    self.assertEqual(load_token(self.path), token)
    self.assertEqual(init_token(self.path), token)

  def test_world_readable_rejected(self):
    init_token(self.path)
    self.path.chmod(0o644)
    with self.assertRaises(ValueError):
      load_token(self.path)

  def test_symlink_rejected(self):
    original = self.path.with_name("original")
    init_token(original)
    self.path.symlink_to(original)
    with self.assertRaises((ValueError, OSError)):
      load_token(self.path)

  def test_weak_and_oversized_rejected(self):
    for value in (b"password", b"a" * 300, b"a" * 43 + b"\nextra"):
      self.path.write_bytes(value)
      self.path.chmod(0o600)
      with self.assertRaises(ValueError):
        load_token(self.path)

  def test_public_parent_rejected(self):
    Path(self.temp.name).chmod(0o755)
    with self.assertRaises(ValueError):
      init_token(self.path)

  def test_repository_secret_rejected(self):
    (Path(self.temp.name) / ".git").mkdir()
    with self.assertRaises(ValueError):
      init_token(self.path)


class ServerTests(unittest.TestCase):
  def setUp(self):
    self.store = Store("host")
    HostCollector(self.store).poll()
    self.server = create_server("127.0.0.1", 0, "a" * 43, self.store, {"commit": "test"})
    self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
    self.thread.start()
    self.addCleanup(self.close)

  def close(self):
    self.server.shutdown()
    self.server.server_close()
    self.thread.join(timeout=2)

  def request(self, path="/api/status", method="GET", token="a" * 43):
    conn = http.client.HTTPConnection(*self.server.server_address, timeout=2)
    headers = {"Authorization": "Bearer " + token} if token else {}
    conn.request(method, path, headers=headers)
    response = conn.getresponse()
    result = response.status, dict(response.getheaders()), response.read()
    conn.close()
    return result

  def test_status_real_host_authenticated(self):
    import json
    status, headers, body = self.request()
    self.assertEqual(status, 200)
    data = json.loads(body)
    self.assertGreater(data["host"]["disk_total_bytes"], 0)
    self.assertIsNone(data["topics"]["carState"]["data"])
    self.assertEqual(headers["Cache-Control"], "no-store")

  def test_missing_and_incorrect_auth(self):
    for token in (None, "wrong"):
      self.assertEqual(self.request(token=token)[0], 401)

  def test_no_query_credentials(self):
    self.assertEqual(self.request("/api/status?token=" + "a" * 43)[0], 400)

  def test_read_only(self):
    for method in ("POST", "PUT", "DELETE", "PATCH", "OPTIONS"):
      self.assertEqual(self.request(method=method)[0], 405)

  def test_assets_and_traversal(self):
    for path in ("/", "/app.js", "/app.css"):
      status, headers, _ = self.request(path, token=None)
      self.assertEqual(status, 200)
      self.assertIn("default-src 'self'", headers["Content-Security-Policy"])
    for path in ("/../server.py", "/%2e%2e/server.py", "/token", "/api/control"):
      self.assertEqual(self.request(path)[0], 404)

  def test_head_and_no_secret_in_response(self):
    self.assertEqual(self.request(method="HEAD")[2], b"")
    self.assertNotIn(b"a" * 43, self.request()[2])
