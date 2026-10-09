"""Loopback-only surveyed target import and observation front end; no device capture."""
import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer
import io
import math
import re
from pathlib import Path
import secrets
import uuid
from PIL import Image
from openpilot.tools.cyber_autotune import camera_calibration_evidence as c
from openpilot.tools.cyber_autotune import stationary_target_calibration as t
from openpilot.tools.cyber_autotune import physical_calibration_wizard as w
from openpilot.tools.cyber_autotune.physical_calibration_wizard_ui import strict_json
from openpilot.tools.cyber_autotune.native_protocol import canonical, digest
from openpilot.tools.cyber_autotune.lane_projection_validation import _rotation

ASSETS = Path(__file__).with_name('stationary_target_assets')
MAX_JSON_BYTES = 1024 * 1024


def prepare(body, scope='INDEPENDENT_PHYSICAL'):
  c.exact(body, ('fields', 'points', 'image'))
  f = body['fields']

  def val(key):
    if type(f.get(key)) is not str or not f[key].strip():
      raise ValueError('MISSING_OBSERVED_VALUE_' + key)
    out = float(f[key])
    c.number(out)
    return out

  def sha(key):
    return c.sha(f.get(key))

  if f.get('ack') is not True:
    raise ValueError('PHYSICAL_OBSERVATION_CONFIRMATION_REQUIRED')
  camera = {'device': 'mici', 'hardware_generation': 'comma4', 'sensor': f.get('sensor'), 'view': 'narrow_road',
            'unit_id_sha256': w.opaque(f.get('unit')), 'hardware_evidence_sha256': sha('hardware_sha')}
  i = c.intrinsics(camera)
  # Explicit survey of board orientation relative to forward-facing vehicle-axis base.
  target_rotation = _rotation(2, math.radians(val('target_yaw_deg'))) @ _rotation(
    1, math.radians(val('target_pitch_deg'))) @ _rotation(0, math.radians(val('target_roll_deg'))) @ c.BASE_ROTATION
  target = {
    'width_m': val('target_width_m'), 'height_m': val('target_height_m'), 'dimension_bound_m': val('target_dimension_bound_m'),
    'planarity_bound_m': val('target_planarity_bound_m'), 'source_sha256': sha('target_sha'),
    'rotation_target_to_vehicle': target_rotation.tolist(), 'origin_vehicle_m': [val('target_' + axis + '_m') for axis in ('x', 'y', 'z')],
    'placement_translation_bound_m': [val('placement_' + axis + '_bound_m') for axis in ('x', 'y', 'z')],
    'placement_rotation_bound_rad': [math.radians(val('placement_' + axis + '_bound_deg')) for axis in ('roll', 'pitch', 'yaw')],
    'placement_evidence_sha256': sha('placement_sha'),
  }
  image = body['image']
  c.exact(image, ('sha256', 'width', 'height'))
  d = {
    'schema': t.SCHEMA, 'scope': scope, 'camera': camera, 'intrinsics_sha256': i['receipt_sha256'],
    'image_sha256': image['sha256'], 'image_wh': [image['width'], image['height']], 'target': target,
    'corners_px': body['points'], 'corner_bound_px': val('corner_bound_px'),
    'height_repeats_m': [val('height' + str(n)) for n in (1, 2, 3)], 'height_absolute_bound_m': val('height_bound_m'),
    'height_evidence_sha256': sha('height_sha'), 'ground_evidence_sha256': sha('ground_sha'),
    'ground_slope_bound_rad': math.radians(val('ground_slope_bound_deg')),
    'operator_id_sha256': w.opaque(f.get('operator')), 'timestamp': f.get('timestamp'),
    'provenance_role': 'INDEPENDENT_TARGET_OBSERVATION', 'model_outputs_used': False, 'candidate_outputs_used': False,
    'physical_observation_acknowledged': True, 'distortion_state': 'DISTORTION_UNVERIFIED',
  }
  t.validate_capture(d, i)
  return {'capture': d, 'intrinsics_sha256': i['receipt_sha256']}


def make_server(session, *, host='127.0.0.1', port=0):
  if host != '127.0.0.1' or type(port) is not int or not 0 <= port <= 65535:
    raise ValueError('LOOPBACK_ONLY_REQUIRED')

  class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
      pass

    def origin(self):
      return 'http://127.0.0.1:' + str(self.server.server_port)

    def allowed(self, post=False):
      return (self.client_address[0] == '127.0.0.1' and self.headers.get('Host') == self.origin()[7:]
              and self.headers.get('Origin', self.origin()) == self.origin()
              and (not post or self.headers.get('Origin') == self.origin()
                   and secrets.compare_digest(self.headers.get('X-Target-Token', ''), self.server.token)))

    def reply(self, code, value, mime='application/json'):
      data = canonical(value) if mime == 'application/json' else value if isinstance(value, bytes) else value.encode()
      self.send_response(code)
      for k, v in {
        'Content-Type': mime, 'Content-Length': str(len(data)), 'Cache-Control': 'no-store',
        'X-Content-Type-Options': 'nosniff', 'Referrer-Policy': 'no-referrer',
        'Content-Security-Policy': "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self'; connect-src 'self'; "
                                  + "base-uri 'none'; object-src 'none'; frame-ancestors 'none'; form-action 'self'",
      }.items():
        self.send_header(k, v)
      self.end_headers()
      self.wfile.write(data)

    def image(self, sha):
      c.sha(sha)
      session.guard()
      raw = w.read_blob(session.root / (sha + '.image'))
      if digest(raw) != sha:
        raise ValueError('LOCAL_IMAGE_CHANGED')
      return raw

    def do_GET(self):
      if not self.allowed():
        return self.reply(403, {'error': 'LOOPBACK_ORIGIN_REQUIRED'})
      try:
        if self.path == '/api/state':
          return self.reply(200, session.state())
        if self.path == '/export/local-captures.json':
          return self.reply(200, {'schema': 'LOCAL_PRIVATE_TARGET_CAPTURE_PACKAGE_V1', 'captures': session.completed(),
                                  'publish_this_package': False, 'reference_promotable': False})
        if self.path == '/api/config':
          return self.reply(200, {'token': self.server.token, 'policy': t.POLICY, 'policy_sha256': t.POLICY_SHA,
                                  'static_camera_source_sha256': c.CAMERA_SHA, 'state': session.state()})
        if self.path == '/measurement-sheet':
          return self.reply(200, t.target_sheet(), 'text/html; charset=utf-8')
        if self.path == '/print.css':
          return self.reply(200, '@page{size:A4;margin:15mm}svg{display:block;margin:5mm 0}', 'text/css')
        if self.path in ('/', '/app.js', '/style.css'):
          name, mime = {'/': ('index.html', 'text/html; charset=utf-8'), '/app.js': ('app.js', 'text/javascript'),
                        '/style.css': ('style.css', 'text/css')}[self.path]
          return self.reply(200, (ASSETS / name).read_bytes(), mime)
        if self.path.startswith('/image/'):
          return self.reply(200, self.image(self.path[7:]), 'image/png')  # Import is canonically PNG, no EXIF publication.
        self.reply(404, {'error': 'UNKNOWN_LOCAL_RESOURCE'})
      except (ValueError, TypeError, KeyError, OSError):
        self.reply(400, {'error': 'LOCAL_IMAGE_OR_STATE_INVALID'})

    def do_POST(self):
      if not self.allowed(True):
        return self.reply(403, {'error': 'LOOPBACK_ORIGIN_AND_NONCE_REQUIRED'})
      try:
        binary = self.path in ('/api/image', '/api/evidence')
        maximum = w.MAX_ATTACHMENT_BYTES if binary else MAX_JSON_BYTES
        if self.headers.get('Transfer-Encoding') or self.headers.get('Content-Type') != ('application/octet-stream' if binary else 'application/json'):
          raise ValueError('EXPLICIT_CONTENT_TYPE_REQUIRED')
        size = int(self.headers.get('Content-Length', '-1'))
        if not 0 < size <= maximum:
          return self.reply(413, {'error': 'LOCAL_RESOURCE_CAP'})
        self.connection.settimeout(5)
        raw = self.rfile.read(size)
        if len(raw) != size:
          raise ValueError('INCOMPLETE_REQUEST')
        body = raw if binary else strict_json(raw)
        if self.path in ('/api/image', '/api/evidence'):
          session.guard()
          if self.path == '/api/image':
            with Image.open(io.BytesIO(raw)) as image:
              if image.format != 'PNG' or image.width * image.height > 16_000_000:
                raise ValueError('BOUNDED_ORIGINAL_PNG_REQUIRED')
              wh = image.size
              image.verify()
            suffix = '.image'
          else:
            wh = None
            suffix = '.evidence'
          sha = digest(raw)
          path = session.root / (sha + suffix)
          from openpilot.tools.cyber_autotune import lane_public_storage as storage
          with storage.writer_lease(session.root):
            session.guard()
            if path.exists() or path.is_symlink():
              if w.read_blob(path) != raw:
                raise ValueError('IMMUTABLE_ATTACHMENT_CHANGED')
            else:
              w.atomic_blob(path, raw)
          value = {'sha256': sha, 'width': wh[0], 'height': wh[1]} if wh else {'sha256': sha, 'bytes': len(raw)}
        elif self.path == '/api/draft':
          value = session.save_draft(body)
        elif self.path == '/api/prepare':
          value = prepare(body, session.scope)
        elif self.path in ('/api/solve', '/api/freeze'):
          c.exact(body, ('capture', 'intrinsics_sha256'))
          if body['capture']['scope'] != session.scope:
            raise ValueError('CAPTURE_SCOPE_BINDING_MISMATCH')
          intrinsic = c.intrinsics(body['capture']['camera'])
          if body['intrinsics_sha256'] != intrinsic['receipt_sha256']:
            raise ValueError('STATIC_INTRINSICS_RECEIPT_SHA_MISMATCH')
          image = self.image(body['capture']['image_sha256'])
          with Image.open(io.BytesIO(image)) as im:
            if list(im.size) != body['capture']['image_wh']:
              raise ValueError('IMAGE_HASH_DIMENSIONS_MISMATCH')
          value = t.solve(body['capture'], intrinsic) if self.path == '/api/solve' else session.freeze(body['capture'], intrinsic, image)
        else:
          return self.reply(404, {'error': 'UNKNOWN_ACTION'})
        self.reply(200, value)
      except ValueError as exc:
        code = str(exc)
        self.reply(400, {'error': code if re.fullmatch('[A-Z][A-Z0-9_]{1,120}', code) else 'OBSERVED_INPUT_OR_IMMUTABLE_BINDING_REJECTED'})
      except (TypeError, KeyError, OSError, UnicodeError, OverflowError):
        self.reply(400, {'error': 'OBSERVED_INPUT_OR_IMMUTABLE_BINDING_REJECTED'})

  server = HTTPServer((host, port), Handler)
  server.token = secrets.token_hex(32)
  return server


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--workspace', type=Path)
  parser.add_argument('--port', type=int, default=0)
  args = parser.parse_args()
  root = args.workspace or Path.home() / '.local/share/cyberpilot-stationary-target' / uuid.uuid4().hex
  server = make_server(t.CaptureSession(root), port=args.port)
  print(f'Local/private target capture http://127.0.0.1:{server.server_port} — Ctrl-C to stop', flush=True)
  try:
    server.serve_forever()
  except KeyboardInterrupt:
    pass
  finally:
    server.server_close()


if __name__ == '__main__':
  main()
