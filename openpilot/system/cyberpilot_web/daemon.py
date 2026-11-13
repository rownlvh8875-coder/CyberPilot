"""Opt-in manager entry. No argv parsing, publishers, or control calls."""

import os
import sys
from pathlib import Path

from .cli import run
from .server import load_token


def configuration(env):
  if env.get("CYBERPILOT_WEB") != "1":
    return None
  path = env.get("CYBERPILOT_WEB_TOKEN_FILE")
  if not path or not Path(path).is_absolute():
    raise ValueError("explicit_absolute_credential_path_required")
  port = int(env.get("CYBERPILOT_WEB_PORT", "8099"))
  if not 1 <= port <= 65535:
    raise ValueError("invalid_port")
  cert, key = env.get("CYBERPILOT_WEB_TLS_CERT"), env.get("CYBERPILOT_WEB_TLS_KEY")
  if bool(cert) != bool(key):
    raise ValueError("tls_pair_required")
  return {"host": env.get("CYBERPILOT_WEB_HOST", "127.0.0.1"), "port": port,
          "source": "openpilot", "cert": cert, "key": key, "token_file": Path(path)}


def main():
  try:
    config = configuration(os.environ)
    if config is None:
      return
    token = load_token(config.pop("token_file"))
    run(token=token, **config)
  except (OSError, ValueError, UnicodeError):
    print("CyberPilot monitor configuration unavailable; no telemetry server started.", file=sys.stderr)
