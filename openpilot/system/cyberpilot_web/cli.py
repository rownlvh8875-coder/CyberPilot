"""Local/LAN monitor commands; never install, launch control, or send CAN."""

import argparse
import json
import signal
import ssl
import subprocess
import sys
import threading
from pathlib import Path

from .server import create_server, init_token, load_token
from .telemetry import CerealCollector, HostCollector, Store

ROOT = Path(__file__).resolve().parents[3]


def source_identity() -> dict:
  result = {"commit": None, "branch": None}
  for key, args in (("commit", ["rev-parse", "HEAD"]), ("branch", ["rev-parse", "--abbrev-ref", "HEAD"])):
    try:
      value = subprocess.run(["git", "--no-optional-locks", *args], cwd=ROOT, capture_output=True, text=True, timeout=2, check=True)
      result[key] = value.stdout.strip()[:256]
    except (OSError, subprocess.SubprocessError):
      pass
  return result


def run(host, port, token, source, cert=None, key=None):
  if bool(cert) != bool(key):
    raise ValueError("tls_certificate_and_key_required_together")
  store = Store(source)
  host_collector = HostCollector(store)
  cereal = CerealCollector(store) if source == "openpilot" else None
  server = create_server(host, port, token, store, source_identity())
  if cert:
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(cert, key)
    # Handshake occurs in bounded request workers, never in the accept loop.
    server.socket = context.wrap_socket(server.socket, server_side=True, do_handshake_on_connect=False)
  stop = threading.Event()

  def collect():
    while not stop.is_set():
      try:
        host_collector.poll()
      except (OSError, ValueError):
        store.set_error("host_unavailable")
      if cereal:
        cereal.poll()
      stop.wait(1)

  worker = threading.Thread(target=collect, daemon=True)
  worker.start()
  scheme = "https" if cert else "http"
  print(f"CyberPilot read-only status: {scheme}://{host}:{server.server_port}/ source={source}", flush=True)
  try:
    server.serve_forever(poll_interval=0.25)
  finally:
    stop.set()
    server.server_close()
    worker.join(timeout=2)


def main(argv=None):
  parser = argparse.ArgumentParser(description="CyberPilot read-only status monitor")
  commands = parser.add_subparsers(dest="command", required=True)
  init = commands.add_parser("init", help="create private credentials outside a repository")
  init.add_argument("--token-file", type=Path, required=True)
  serve = commands.add_parser("serve", help="start read-only monitoring; host source by default")
  serve.add_argument("--token-file", type=Path, required=True)
  serve.add_argument("--host", default="127.0.0.1")
  serve.add_argument("--port", type=int, default=8099)
  serve.add_argument("--source", choices=("host", "openpilot"), default="host")
  serve.add_argument("--tls-cert", type=Path)
  serve.add_argument("--tls-key", type=Path)
  args = parser.parse_args(argv)
  try:
    if args.command == "init":
      init_token(args.token_file)
      print("Private credential ready. Token is not printed; read it locally when pairing.")
    else:
      token = load_token(args.token_file)
      run(args.host, args.port, token, args.source, args.tls_cert, args.tls_key)
    return 0
  except (OSError, ValueError, UnicodeError):
    print("Status monitor configuration failed; check private credentials, bind address and TLS files.", file=sys.stderr)
    return 2


def entrypoint():
  def terminate(_signum, _frame):
    raise KeyboardInterrupt
  signal.signal(signal.SIGTERM, terminate)
  try:
    raise SystemExit(main())
  except KeyboardInterrupt:
    pass
