"""Local parameter visualization; no camera/log import and no qualification route."""

import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import secrets
from openpilot.tools.cyber_autotune import approximate_geometry_diagnostic as a
from openpilot.tools.cyber_autotune import camera_calibration_evidence as c
from openpilot.tools.cyber_autotune import coarse_camera_height_diagnostic as h
from openpilot.tools.cyber_autotune import lane_public_storage as storage
from openpilot.tools.cyber_autotune import physical_calibration_wizard as w
from openpilot.tools.cyber_autotune.physical_calibration_wizard_ui import strict_json, MAX_JSON_BYTES
from openpilot.tools.cyber_autotune.native_protocol import canonical, digest

ASSETS = Path(__file__).with_name('approximate_geometry_assets')
EXECUTED_SOURCE_SHA = digest(Path(__file__).read_bytes())
ASSET_BYTES = {name: (ASSETS / name).read_bytes() for name in ('index.html', 'app.js', 'style.css')}
ASSET_SHA = {name: digest(data) for name, data in ASSET_BYTES.items()}


def guard():
  a.identity()
  h.identity()
  if digest(Path(__file__).read_bytes()) != EXECUTED_SOURCE_SHA:
    raise ValueError('RUNNING_VISUALIZER_SOURCE_CHANGED')
  if {p.name for p in ASSETS.iterdir()} != set(ASSET_BYTES):
    raise ValueError('RUNNING_ASSET_SET_CHANGED')
  for name, sha in ASSET_SHA.items():
    path = ASSETS / name
    if path.is_symlink() or digest(path.read_bytes()) != sha:
      raise ValueError('RUNNING_VISUALIZER_ASSET_CHANGED')


def state(prior, physical=None):
  guard()
  return {
    'prior': prior,
    'readiness': a.readiness(prior),
    'comparison': a.compare_physical(prior, physical),
    'effective_physical_euler_rad': a.physical_euler(prior['orientation']['converted_rad']),
    'visualizer_source_sha256': EXECUTED_SOURCE_SHA,
    'assets_sha256': dict(ASSET_SHA),
    'coarse': {
      'height_prior': h.height_prior(),
      'vehicle_context': h.vehicle_context(),
      'policy': h.frozen_policy(),
      'result': h.evaluate(h.height_prior(), h.frozen_policy()),
      'comparison': h.compare_physical(h.height_prior(), physical),
      'readiness': h.readiness(h.height_prior()),
    },
  }


def physical_from_wizard(workspace):
  """Only an explicitly named stationary wizard store; never discover/input routes."""
  root = Path(workspace)
  if not (root / 'binding.json').is_file():
    raise ValueError('EXPLICIT_EXISTING_STATIONARY_WIZARD_STORE_REQUIRED')
  scope = storage.read_json(root / 'binding.json')['scope']
  return w.MeasurementSession(root, scope=scope).package()['admission']


def make_server(*, host='127.0.0.1', port=0, physical=None):
  if host != '127.0.0.1' or type(port) is not int or not 0 <= port <= 65535:
    raise ValueError('LOOPBACK_ONLY_REQUIRED')
  guard()
  prior = a.prior()
  if physical is not None:
    a.compare_physical(prior, physical)

  class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
      pass

    def origin(self):
      return 'http://127.0.0.1:' + str(self.server.server_port)

    def allowed(self, post=False):
      return (
        self.client_address[0] == '127.0.0.1'
        and self.headers.get('Host') == self.origin()[7:]
        and self.headers.get('Origin', self.origin()) == self.origin()
        and (
          not post
          or self.headers.get('Origin') == self.origin()
          and secrets.compare_digest(self.headers.get('X-Diagnostic-Token', ''), self.server.diagnostic_token)
        )
      )

    def reply(self, code, value, mime='application/json'):
      data = canonical(value) if mime == 'application/json' else value.encode()
      self.send_response(code)
      for k, v in {
        'Content-Type': mime + '; charset=utf-8',
        'Content-Length': str(len(data)),
        'Cache-Control': 'no-store',
        'X-Content-Type-Options': 'nosniff',
        'Referrer-Policy': 'no-referrer',
        'Content-Security-Policy': (
          "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; "
          + "img-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
        ),
      }.items():
        self.send_header(k, v)
      self.end_headers()
      self.wfile.write(data)

    def do_GET(self):
      if not self.allowed():
        return self.reply(403, {'error': 'LOOPBACK_ORIGIN_REQUIRED'})
      try:
        guard()
        if self.path == '/api/state':
          return self.reply(200, {**state(prior, physical), 'token': self.server.diagnostic_token})
        assets = {'/': ('index.html', 'text/html'), '/app.js': ('app.js', 'text/javascript'), '/style.css': ('style.css', 'text/css')}
        if self.path in assets:
          name, mime = assets[self.path]
          return self.reply(200, ASSET_BYTES[name].decode(), mime)
        self.reply(404, {'error': 'FIXED_DIAGNOSTIC_ROUTE_ONLY'})
      except (ValueError, KeyError, TypeError, OSError):
        self.reply(400, {'error': 'DIAGNOSTIC_SOURCE_OR_INPUT_INVALID'})

    def do_POST(self):
      if not self.allowed(True):
        return self.reply(403, {'error': 'LOOPBACK_ORIGIN_NONCE_REQUIRED'})
      self.connection.settimeout(5)
      try:
        guard()
        if self.headers.get('Transfer-Encoding') is not None or self.headers.get('Content-Type') != 'application/json':
          raise ValueError('JSON_ONLY')
        size = int(self.headers.get('Content-Length', '-1'))
        if not 0 < size <= MAX_JSON_BYTES:
          raise ValueError('BOUNDED_JSON_REQUIRED')
        body = strict_json(self.rfile.read(size))
        if self.path == '/api/sensitivity':
          c.exact(body, ('heights_m', 'rpy_deg_choices', 'mount_y_m', 'rationale'))
          policy = a.parameter_policy(**body)
          return self.reply(200, {'policy': policy, 'report': a.sensitivity(prior, policy)})
        if self.path == '/api/ray':
          c.exact(body, ('normalized_uv', 'height_m'))
          report = a.symbolic_height(prior, body['normalized_uv']) if body['height_m'] is None else a.project(prior, body['normalized_uv'], body['height_m'])
          return self.reply(200, report)
        self.reply(404, {'error': 'FIXED_DIAGNOSTIC_ROUTE_ONLY'})
      except (ValueError, KeyError, TypeError, OverflowError, OSError):
        self.reply(400, {'error': 'EXPLICIT_FINITE_BOUNDED_DIAGNOSTIC_PARAMETERS_REQUIRED'})

  server = HTTPServer((host, port), Handler)
  server.diagnostic_token = secrets.token_hex(32)
  return server


def main():
  parser = argparse.ArgumentParser(description='Approximate geometry NON-QUALIFYING loopback visualization')
  parser.add_argument('--port', type=int, default=0)
  parser.add_argument('--physical-wizard-workspace', help='Explicit existing stationary wizard store; optional future comparison only')
  args = parser.parse_args()
  physical = None if args.physical_wizard_workspace is None else physical_from_wizard(args.physical_wizard_workspace)
  server = make_server(port=args.port, physical=physical)
  print(f'Open http://127.0.0.1:{server.server_port} — APPROXIMATE/NON-QUALIFYING; Ctrl-C to close', flush=True)
  try:
    server.serve_forever()
  except KeyboardInterrupt:
    pass
  finally:
    server.server_close()


if __name__ == '__main__':
  main()
