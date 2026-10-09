"""Local stationary calibration field form; assets and observations never leave loopback."""

import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import secrets
import uuid
from openpilot.tools.cyber_autotune import physical_calibration_wizard as w
from openpilot.tools.cyber_autotune import camera_calibration_evidence as c
from openpilot.tools.cyber_autotune.native_protocol import canonical

MAX_JSON_BYTES = 1024 * 1024  # Bounded local form transport, not measurement tolerance.
STAGES = [
  'A — DEVICE',
  'B — HEIGHT / MOUNT',
  'C — PITCH / ROLL / YAW',
  'D — STATIONARY TARGET',
  'E — GROUND / DISTORTION',
  'F — STATIC INTRINSICS',
  'G — LOCAL EVIDENCE',
  'H — PREFLIGHT / RECEIPT',
]
ASSETS = Path(__file__).with_name('physical_calibration_assets')
HTML = (ASSETS / 'wizard.html').read_text()
CSS = (ASSETS / 'wizard.css').read_text()
JS = (ASSETS / 'wizard.js').read_text()


def measurement_sheet():
  squares = ''.join(
    f'<rect x="{x * 20}" y="{y * 20}" width="20" height="20" fill="{"black" if (x + y) % 2 == 0 else "white"}"/>' for y in range(6) for x in range(8)
  )
  return f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>Local target sheet</title><link rel="stylesheet" href="/print.css"></head><body>
<h1>NOMINAL PRINT GEOMETRY / NOT PHYSICAL TRUTH</h1><p>8 × 6 squares; nominal20 mm square; nominal160 ×120 mm board; inner corners7 ×5.
100% / actual-size 인쇄. 페이지 맞춤 금지.
모든 실제 square/board/control bar를 ruler/caliper로 실제로 재측정하고 uncertainty와 target-to-vehicle survey를 기록하세요.
인쇄값 자체를 측정값으로 사용하지 마세요. 이 sheet는 calibration solver나 certified target이 아닙니다.</p>
<svg xmlns="http://www.w3.org/2000/svg" width="160mm" height="120mm" viewBox="0 0 160 120">{squares}</svg>
<p>Control bar: nominal100 mm (실제로 재측정)</p>
<svg xmlns="http://www.w3.org/2000/svg" width="100mm" height="5mm" viewBox="0 0 100 5"><rect width="100" height="5"/></svg>
<p>Actual width ______ m; height ______ m; square ______ m; uncertainty ______ m; instrument ______;
target distance ______ m; surveyed datum ______; evidence hash ______.</p></body></html>"""


def strict_json(raw):
  def pairs(items):
    value = {}
    for k, v in items:
      if k in value:
        raise ValueError('DUPLICATE_FORM_KEY')
      value[k] = v
    return value

  return json.loads(raw, object_pairs_hook=pairs, parse_constant=lambda _: (_ for _ in ()).throw(ValueError('NONFINITE_JSON')))


def make_server(session, *, host='127.0.0.1', port=0):
  if host != '127.0.0.1' or type(port) is not int or not 0 <= port <= 65535:
    raise ValueError('LOOPBACK_ONLY_CALIBRATION_SERVER_REQUIRED')

  class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
      pass

    def origin(self):
      return 'http://127.0.0.1:' + str(self.server.server_port)

    def authorized(self, post=False):
      return (
        self.client_address[0] == '127.0.0.1'
        and self.headers.get('Host') == self.origin()[7:]
        and self.headers.get('Origin', self.origin()) == self.origin()
        and (
          not post or self.headers.get('Origin') == self.origin() and secrets.compare_digest(self.headers.get('X-Wizard-Token', ''), self.server.wizard_token)
        )
      )

    def reply(self, code, body, mime='application/json'):
      data = canonical(body) if mime == 'application/json' else body.encode()
      self.send_response(code)
      for key, value in {
        'Content-Type': mime + '; charset=utf-8',
        'Content-Length': str(len(data)),
        'Cache-Control': 'no-store',
        'X-Content-Type-Options': 'nosniff',
        'Referrer-Policy': 'no-referrer',
        'Content-Security-Policy': (
          "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; "
          + "img-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
        ),
      }.items():
        self.send_header(key, value)
      self.end_headers()
      self.wfile.write(data)

    def do_GET(self):
      if not self.authorized():
        return self.reply(403, {'error': 'LOOPBACK_ORIGIN_REQUIRED'})
      try:
        assets = {
          '/': (HTML, 'text/html'),
          '/app.js': (JS, 'text/javascript'),
          '/style.css': (CSS, 'text/css'),
          '/print.css': ('@page{size:A4;margin:15mm}body{font:12pt sans-serif}svg{display:block;margin:5mm 0}', 'text/css'),
          '/measurement-sheet': (measurement_sheet(), 'text/html'),
        }
        if self.path in assets:
          return self.reply(200, *assets[self.path])
        if self.path == '/api/config':
          return self.reply(
            200,
            {
              'token': self.server.wizard_token,
              'state': session.state(),
              'stages': STAGES,
              'methods': list(c.METHODS),
              'instruments': list(w.INSTRUMENTS),
              'target_keys': list(w.TARGET_KEYS),
              'observation_keys': list({**c.UNITS, **w.EXTRA_UNITS}),
              'observation_fields': list(w.OBS_KEYS),
              'forbidden': list(w.FORBIDDEN),
              'historical_height_observation': w.h.observation(),
              'height_observation_notice': w.h.NOTICE,
              'static_sources': {
                'camera_source_file': c.CAMERA_SOURCE,
                'camera_source_sha256': c.CAMERA_SHA,
                'hardware_source_file': c.HARDWARE_SOURCE,
                'hardware_source_sha256': c.HARDWARE_SHA,
              },
            },
          )
        if self.path == '/api/state':
          return self.reply(200, session.state())
        if self.path == '/export/local.json':
          return self.reply(200, session.package())
        if self.path == '/export/public.json':
          return self.reply(200, session.public_summary())
        self.reply(404, {'error': 'UNKNOWN_LOCAL_RESOURCE'})
      except (ValueError, KeyError, TypeError, OSError):
        self.reply(400, {'error': 'LOCAL_EVIDENCE_OR_STATE_REJECTED'})

    def do_POST(self):
      if not self.authorized(True):
        return self.reply(403, {'error': 'LOOPBACK_ORIGIN_AND_NONCE_REQUIRED'})
      binary = self.path == '/api/attachment'
      maximum = w.MAX_ATTACHMENT_BYTES if binary else MAX_JSON_BYTES
      try:
        if self.headers.get('Transfer-Encoding') or self.headers.get('Content-Type') != ('application/octet-stream' if binary else 'application/json'):
          raise ValueError('EXPLICIT_CONTENT_TYPE_REQUIRED')
        size = int(self.headers.get('Content-Length', '-1'))
        if not 0 < size <= maximum:
          return self.reply(413, {'error': 'LOCAL_REQUEST_RESOURCE_CAP'})
        self.connection.settimeout(5)
        raw = self.rfile.read(size)
        if len(raw) != size:
          raise ValueError('INCOMPLETE_LOCAL_REQUEST')
        body = raw if binary else strict_json(raw)
        if not binary and type(body) is not dict:
          raise ValueError('EXACT_FORM_OBJECT_REQUIRED')
        if self.path == '/api/attachment':
          value = session.attach(body)
        elif self.path == '/api/draft':
          value = session.save_draft(body)
        elif self.path == '/api/preflight':
          value = session.preflight(body)
        elif self.path == '/api/intrinsics':
          c.exact(body, w.blank_draft()['camera'])
          camera = {k: body[k] for k in ('device', 'hardware_generation', 'sensor', 'view')}
          camera.update(unit_id_sha256=w.opaque(body['unit_id']), hardware_evidence_sha256=w.evidence_ref(session.rows(), body['hardware_evidence_id']))
          value = c.intrinsics(camera)
        elif self.path == '/api/load-height-observation':
          c.exact(body, ())
          value = session.load_height_observation()
        elif self.path in ('/api/admit', '/api/recover'):
          c.exact(body, ())
          value = session.admit() if self.path == '/api/admit' else session.recover()
        else:
          return self.reply(404, {'error': 'UNKNOWN_LOCAL_ACTION'})
        self.reply(200, value)
      except (ValueError, TypeError, KeyError, OSError, UnicodeError):
        self.reply(400, {'error': 'EXPLICIT_INPUT_OR_IMMUTABILITY_REJECTED'})

  server = HTTPServer((host, port), Handler)
  server.wizard_token = secrets.token_hex(32)
  return server


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--workspace', type=Path, help='Explicit new local/private directory outside repository; never raw route/log input')
  parser.add_argument('--port', type=int, default=0, help='Loopback port;0 chooses unused port')
  args = parser.parse_args()
  root = args.workspace or Path.home() / '.local/share/cyberpilot-physical-calibration' / uuid.uuid4().hex
  session = w.MeasurementSession(root)
  server = make_server(session, port=args.port)
  print(f'Open http://127.0.0.1:{server.server_port} — local/private observations; Ctrl-C to stop', flush=True)
  try:
    server.serve_forever()
  except KeyboardInterrupt:
    pass
  finally:
    server.server_close()


if __name__ == '__main__':
  main()
