"""Fixed read-only routes and private bearer credentials. No request logging."""

import hmac
import json
import os
import re
import secrets
import socket
import stat
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

ASSETS = Path(__file__).with_name("assets")


def private_parent(path: Path):
  parent = path.absolute().parent
  if parent.resolve() != parent or any((p / ".git").exists() for p in (parent, *parent.parents)):
    raise ValueError("credential_path_unsafe")
  info = parent.stat()
  if info.st_mode & 0o077 or info.st_uid != os.getuid():
    raise ValueError("credential_directory_must_be_private")


def load_token(path: Path) -> str:
  private_parent(path)
  fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
  with os.fdopen(fd, "rb") as stream:
    info = os.fstat(stream.fileno())
    if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077 or info.st_uid != os.getuid() or info.st_size > 256:
      raise ValueError("credential_file_unsafe")
    value = stream.read(257).decode("ascii").strip()
  if not re.fullmatch(r"[A-Za-z0-9_-]{43,128}", value):
    raise ValueError("credential_format_invalid")
  return value


def init_token(path: Path) -> str:
  # Only create the explicitly requested credential directory, never repo content.
  if not path.parent.exists():
    path.parent.mkdir(mode=0o700)
  private_parent(path)
  if path.exists() or path.is_symlink():
    return load_token(path)
  fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
  with os.fdopen(fd, "w", encoding="ascii") as stream:
    stream.write(secrets.token_urlsafe(32) + "\n")
  return load_token(path)


class StatusServer(ThreadingHTTPServer):
  daemon_threads = True
  allow_reuse_address = True
  request_queue_size = 16

  def __init__(self, address, handler):
    self.slots = threading.BoundedSemaphore(8)
    super().__init__(address, handler)

  def get_request(self):
    connection, address = super().get_request()
    connection.settimeout(5)
    return connection, address

  def process_request(self, request, client_address):
    if not self.slots.acquire(blocking=False):
      self.shutdown_request(request)
      return
    try:
      super().process_request(request, client_address)
    except Exception:
      self.slots.release()
      raise

  def process_request_thread(self, request, client_address):
    try:
      super().process_request_thread(request, client_address)
    finally:
      self.slots.release()

  def handle_error(self, request, client_address):
    # Do not emit request headers, secrets, paths or traceback to device logs.
    pass


def create_server(host, port, token, store, identity):
  if not re.fullmatch(r"[A-Za-z0-9_-]{43,128}", token):
    raise ValueError("credential_format_invalid")

  class Handler(BaseHTTPRequestHandler):
    server_version = "CyberPilotStatus/1"
    sys_version = ""

    def log_message(self, *_args):
      pass

    def reply(self, code, content, content_type="application/json; charset=utf-8"):
      self.send_response(code)
      self.send_header("Content-Type", content_type)
      self.send_header("Content-Length", str(len(content)))
      self.send_header("Cache-Control", "no-store")
      self.send_header("X-Content-Type-Options", "nosniff")
      self.send_header("Referrer-Policy", "no-referrer")
      self.send_header("Content-Security-Policy", "default-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
      self.send_header("Connection", "close")
      self.end_headers()
      if self.command != "HEAD":
        self.wfile.write(content)

    def do_GET(self):
      parsed = urlsplit(self.path)
      if parsed.query or parsed.fragment or parsed.scheme or parsed.netloc:
        return self.reply(400, b'{"error":"invalid_path"}')
      if parsed.path == "/api/status":
        auth = self.headers.get_all("Authorization", [])
        if len(auth) != 1 or not hmac.compare_digest(auth[0].encode(), ("Bearer " + token).encode()):
          return self.reply(401, b'{"error":"unauthorized"}')
        payload = store.snapshot()
        payload["identity"] = identity
        return self.reply(200, json.dumps(payload, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode())
      routes = {"/": ("index.html", "text/html; charset=utf-8"),
                "/app.css": ("app.css", "text/css; charset=utf-8"), "/app.js": ("app.js", "text/javascript; charset=utf-8")}
      if parsed.path not in routes:
        return self.reply(404, b'{"error":"not_found"}')
      name, mime = routes[parsed.path]
      return self.reply(200, (ASSETS / name).read_bytes(), mime)

    do_HEAD = do_GET

    def reject(self):
      self.reply(405, b'{"error":"read_only"}')

    do_POST = do_PUT = do_DELETE = do_PATCH = do_OPTIONS = reject

  return StatusServer((host, port), Handler)
