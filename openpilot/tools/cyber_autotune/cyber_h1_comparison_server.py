"""Manual loopback read-only paired inspector. No mutation, optimizer or device."""

from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import re
import socket
from urllib.parse import urlsplit

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import cyber_h1_pairing as q
from openpilot.tools.cyber_autotune import cyber_h1_comparison_catalog as catalog
from openpilot.tools.cyber_autotune.cyber_h1_visual_server import Handler as ReadOnlyHandler, HOSTS, CSP, bounded

STATIC = Path(__file__).parent / 'static'
ASSETS = {'/': 'cyber_h1_compare.html', '/static/cyber_h1_compare.js': 'cyber_h1_compare.js', '/static/cyber_h1_compare.css': 'cyber_h1_compare.css'}


def contract():
  return q.seal(
    {
      'schema': 'CYBER_H1_COMPARISON_SERVER_CONTRACT_V1',
      'hosts': list(HOSTS),
      'methods': ['GET', 'HEAD'],
      'csp': CSP,
      'cors': False,
      'mutation_status': 405,
      'host_origin_validation': True,
      'source_files': {
        str(path.relative_to(Path(__file__).parent)): p.sha(path.read_bytes()) for path in (Path(__file__), *(STATIC / name for name in ASSETS.values()))
      },
      'single_arm_server_unchanged': True,
      'optimizer_endpoint': False,
      'holdout_opening': 'CLOSED',
      'opening_count': 0,
    }
  )


class Handler(ReadOnlyHandler):
  server_version = 'CyberH1Paired'

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
    if self.requestline.split()[1].startswith('//') or '%' in self.path or '\\' in self.path or '..' in self.path or len(self.path) > 512:
      return self.reply(400, {'error': 'INVALID_PATH'})
    url = urlsplit(self.path)
    if url.scheme or url.netloc or url.fragment:
      return self.reply(400, {'error': 'INVALID_PATH'})
    parts = url.path.split('/')
    data = self.server.comparison_data
    try:
      if len(parts) >= 4 and parts[1:3] == ['api', 'campaigns']:
        campaign = next((c for c in data['catalog']['campaigns'] if c['campaign_id'] == parts[3]), None)
        if campaign is None:
          return self.reply(404, {'error': 'UNKNOWN_CAMPAIGN'})
        if len(parts) >= 6 and parts[4] == 'scenarios':
          run = data['runs'][parts[3]].get(parts[5])
          if run is None:
            return self.reply(404, {'error': 'UNKNOWN_SCENARIO'})
          if parts[6:] == ['frames']:
            query = {}
            for item in url.query.split('&') if url.query else []:
              bits = item.split('=')
              if len(bits) != 2 or bits[0] not in ('offset', 'limit') or bits[0] in query:
                raise ValueError('INVALID_QUERY')
              query[bits[0]] = bits[1]
            total = run['frameset']['frame_count']
            offset = bounded(query.get('offset', '0'), 0, total - 1)
            limit = bounded(query.get('limit', '100'), 1, 100)
            frames = run['frames'][offset : offset + limit]
            return self.reply(
              200,
              {
                'offset': offset,
                'limit': limit,
                'count': len(frames),
                'total': total,
                'frames': frames,
                'frameset_receipt_sha256': run['frameset']['receipt_sha256'],
                'evidence_tier': q.TIER,
              },
              immutable=True,
            )
          if url.query:
            raise ValueError('INVALID_QUERY')
          if len(parts) == 8 and parts[6] == 'frame':
            if re.fullmatch(r'0|[1-9][0-9]{0,3}', parts[7]) is None or int(parts[7]) >= len(run['frames']):
              return self.reply(404, {'error': 'UNKNOWN_FRAME'})
            return self.reply(200, run['frames'][int(parts[7])], immutable=True)
          if len(parts) == 6:
            return self.reply(200, {'frameset': run['frameset'], 'pair': run['pair']}, immutable=True)
        if url.query:
          raise ValueError('INVALID_QUERY')
        if len(parts) == 5 and parts[4] == 'scenarios':
          return self.reply(200, {'scenarios': campaign['scenarios']})
        if len(parts) == 4:
          return self.reply(200, campaign)
      if url.query:
        raise ValueError('INVALID_QUERY')
      if url.path in self.server.assets:
        raw, kind = self.server.assets[url.path]
        return self.reply(200, raw, kind)
      if url.path == '/favicon.ico':
        return self.reply(204, b'')
      if url.path == '/api/campaigns':
        return self.reply(200, data['catalog'])
      if url.path == '/api/health':
        return self.reply(200, {'status': 'ok', 'read_only': True, 'campaigns': 2, 'external_assets': False, 'holdout_opening': 'CLOSED', 'opening_count': 0})
    except ValueError:
      return self.reply(400, {'error': 'STRICT_QUERY_BOUNDS'})
    return self.reply(404, {'error': 'UNKNOWN_READ_ONLY_RESOURCE'})


def create_server(store, host='127.0.0.1', port=0):
  if host not in HOSTS or type(port) is not int or not 0 <= port <= 65535:
    raise ValueError('LOOPBACK_BIND_ONLY')
  from openpilot.tools.cyber_autotune.cyber_h1_comparison_publication import validate_server_contract

  validate_server_contract()
  data = catalog.load(store)
  from openpilot.tools.cyber_autotune.cyber_h1_comparison_publication import validate_catalog

  validate_catalog(data['catalog'])
  assets = {}
  for route, name in ASSETS.items():
    path = STATIC / name
    if any(x.is_symlink() for x in (path, *path.parents)):
      raise ValueError('PAIR_ASSET_SYMLINK')
    kind = 'text/html' if name.endswith('.html') else 'text/css' if name.endswith('.css') else 'application/javascript'
    assets[route] = (path.read_bytes(), kind + '; charset=utf-8')

  class Server(ThreadingHTTPServer):
    address_family = socket.AF_INET6 if host == '::1' else socket.AF_INET
    daemon_threads = True

  server = Server(('127.0.0.1' if host == 'localhost' else host, port), Handler)
  server.comparison_data = data
  server.assets = assets
  return server


def main():
  import argparse

  parser = argparse.ArgumentParser(description='Manual loopback synchronized H1 inspector; GET/HEAD only.')
  parser.add_argument('--store', type=Path, required=True)
  parser.add_argument('--host', default='127.0.0.1', choices=HOSTS)
  parser.add_argument('--port', type=int, default=0)
  args = parser.parse_args()
  server = create_server(args.store, args.host, args.port)
  host = '[::1]' if args.host == '::1' else '127.0.0.1'
  print(json.dumps({'url': f'http://{host}:{server.server_port}', 'read_only': True}), flush=True)
  try:
    server.serve_forever()
  except KeyboardInterrupt:
    pass
  finally:
    server.server_close()


if __name__ == '__main__':
  main()
