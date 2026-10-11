"""Explicit loopback GET/HEAD server over a verified immutable in-memory frameset."""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import re
import socket
from urllib.parse import urlsplit

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import cyber_h1_visual_catalog as cat

STATIC = Path(__file__).parent / 'static'
ASSETS = {'/': 'cyber_h1_visual.html', '/static/cyber_h1_visual.js': 'cyber_h1_visual.js', '/static/cyber_h1_visual.css': 'cyber_h1_visual.css'}
CSP = "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
HOSTS = ('127.0.0.1', 'localhost', '::1')


def contract():
  return p.seal(
    {
      'schema': 'CYBER_H1_VISUAL_SERVER_CONTRACT_V1',
      'hosts': list(HOSTS),
      'methods': ['GET', 'HEAD'],
      'csp': CSP,
      'cors': False,
      'mutation_status': 405,
      'host_origin_validation': True,
      'source_files': {
        str(path.relative_to(Path(__file__).parent)): p.sha(path.read_bytes()) for path in (Path(__file__), *(STATIC / name for name in ASSETS.values()))
      },
      'optimizer_endpoint': False,
      'holdout_opener_implemented': False,
      'holdout_opening': 'CLOSED',
      'opening_count': 0,
    }
  )


def bounded(value, minimum, maximum):
  if type(value) is not str or re.fullmatch(r'0|[1-9][0-9]{0,3}', value) is None or not minimum <= int(value) <= maximum:
    raise ValueError('STRICT_BOUNDED_INTEGER')
  return int(value)


class Handler(BaseHTTPRequestHandler):
  server_version = 'CyberH1'
  sys_version = ''
  protocol_version = 'HTTP/1.1'

  def log_message(self, *args):
    pass

  def __getattr__(self, name):
    if name.startswith('do_'):
      return self.mutation
    raise AttributeError(name)

  def mutation(self):
    self.reply(405, {'error': 'READ_ONLY_GET_HEAD_ONLY'})

  def reply(self, status, body, kind='application/json; charset=utf-8', immutable=False):
    raw = body if isinstance(body, bytes) else p.canonical(body)
    self.send_response(status)
    self.send_header('Content-Type', kind)
    self.send_header('Content-Length', str(len(raw)))
    self.send_header('Content-Security-Policy', CSP)
    self.send_header('X-Content-Type-Options', 'nosniff')
    self.send_header('Referrer-Policy', 'no-referrer')
    self.send_header('Cache-Control', 'private, max-age=31536000, immutable' if immutable else 'no-store')
    self.send_header('Allow', 'GET, HEAD')
    self.send_header('Connection', 'close')
    self.end_headers()
    self.close_connection = True
    if self.command != 'HEAD' and status != 204:
      self.wfile.write(raw)

  def do_HEAD(self):
    self.do_GET()

  def do_GET(self):
    host = self.headers.get('Host')
    allowed = {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}', f'[::1]:{self.server.server_port}'}
    if (
      host not in allowed
      or len(self.headers.get_all('Host', [])) != 1
      or len(self.headers.get_all('Origin', [])) > 1
      or self.headers.get('Origin', f'http://{host}') != f'http://{host}'
      or self.headers.get('Sec-Fetch-Site') == 'cross-site'
    ):
      return self.reply(403, {'error': 'LOOPBACK_HOST_ORIGIN_REQUIRED'})
    if (
      self.requestline.split()[1].startswith('//')
      or '%' in self.path
      or '\\' in self.path
      or '..' in self.path
      or self.path.startswith('//')
      or len(self.path) > 512
    ):
      return self.reply(400, {'error': 'INVALID_PATH'})
    url = urlsplit(self.path)
    if url.scheme or url.netloc or url.fragment:
      return self.reply(400, {'error': 'INVALID_PATH'})
    path = url.path
    data = self.server.visual_data
    fs = data['frameset']
    prefix = '/api/runs/' + data['run_id']
    try:
      if path == prefix + '/frames':
        pairs = url.query.split('&') if url.query else []
        query = {}
        for pair in pairs:
          bits = pair.split('=')
          if len(bits) != 2 or bits[0] not in ('offset', 'limit') or bits[0] in query:
            raise ValueError('INVALID_QUERY')
          query[bits[0]] = bits[1]
        offset = bounded(query.get('offset', '0'), 0, 799)
        limit = bounded(query.get('limit', '100'), 1, 100)
        frames = data['frames'][offset : offset + limit]
        return self.reply(
          200,
          {
            'run_id': data['run_id'],
            'offset': offset,
            'limit': limit,
            'count': len(frames),
            'total': 800,
            'frames': frames,
            'frameset_receipt_sha256': fs['receipt_sha256'],
            'evidence_tier': fs['evidence_tier'],
          },
          immutable=True,
        )
      if url.query:
        raise ValueError('INVALID_QUERY')
      if path in self.server.assets:
        raw, kind = self.server.assets[path]
        return self.reply(200, raw, kind)
      if path == '/favicon.ico':
        return self.reply(204, b'')
      if path == '/api/health':
        return self.reply(200, {'status': 'ok', 'read_only': True, 'frame_count': 800, 'external_assets': False})
      if path == '/api/catalog':
        return self.reply(200, data['catalog'])
      if path == prefix:
        return self.reply(200, fs, immutable=True)
      if path.startswith(prefix + '/frame/'):
        index_text = path.removeprefix(prefix + '/frame/')
        if re.fullmatch(r'0|[1-9][0-9]{0,3}', index_text) is None or int(index_text) >= 800:
          return self.reply(404, {'error': 'UNKNOWN_FRAME'})
        return self.reply(200, data['frames'][int(index_text)], immutable=True)
    except ValueError:
      return self.reply(400, {'error': 'STRICT_QUERY_BOUNDS'})
    return self.reply(404, {'error': 'UNKNOWN_READ_ONLY_RESOURCE'})


def create_server(store, host='127.0.0.1', port=0):
  if host not in HOSTS or type(port) is not int or not 0 <= port <= 65535:
    raise ValueError('LOOPBACK_BIND_ONLY')
  from openpilot.tools.cyber_autotune.cyber_h1_visual_publication import validate_server_contract

  validate_server_contract()
  data = cat.load(store)
  assets = {}
  for route, name in ASSETS.items():
    path = STATIC / name
    if any(x.is_symlink() for x in (path, *path.parents)):
      raise ValueError('VISUAL_ASSET_SYMLINK')
    kind = 'text/html' if name.endswith('.html') else 'text/css' if name.endswith('.css') else 'application/javascript'
    assets[route] = (path.read_bytes(), kind + '; charset=utf-8')

  class Server(ThreadingHTTPServer):
    address_family = socket.AF_INET6 if host == '::1' else socket.AF_INET
    daemon_threads = True

  server = Server(('127.0.0.1' if host == 'localhost' else host, port), Handler)
  server.visual_data = data
  server.assets = assets
  return server


def main():
  import argparse

  parser = argparse.ArgumentParser(description='Manual loopback H1 synthetic viewer; GET/HEAD only.')
  parser.add_argument('--store', required=True, type=Path)
  parser.add_argument('--host', default='127.0.0.1', choices=HOSTS)
  parser.add_argument('--port', type=int, default=0)
  args = parser.parse_args()
  server = create_server(args.store, args.host, args.port)
  display_host = '[::1]' if args.host == '::1' else '127.0.0.1'
  print(json.dumps({'url': f'http://{display_host}:{server.server_port}', 'read_only': True}), flush=True)
  try:
    server.serve_forever()
  except KeyboardInterrupt:
    pass
  finally:
    server.server_close()


if __name__ == '__main__':
  main()
