"""Loopback-only public synthetic candidate effect comparison tab."""

import argparse
import json
from pathlib import Path

from openpilot.tools.cyber_autotune import declared_meter_visualizer as old
from openpilot.tools.cyber_autotune import resolution_candidate_evidence as e
from openpilot.tools.cyber_autotune import resolution_candidate_publication as publication
from openpilot.tools.cyber_autotune.native_protocol import digest

ASSETS = Path(__file__).with_name('resolution_candidate_assets')
ASSET_BYTES = {n: (ASSETS / n).read_bytes() for n in ('index.html', 'app.js', 'style.css')}
SOURCE_SHA = digest(Path(__file__).read_bytes())
PUBLICATION_SOURCE_SHA = digest(Path(publication.__file__).read_bytes())


def guard():
  e.guard()
  if digest(Path(publication.__file__).read_bytes()) != PUBLICATION_SOURCE_SHA:
    raise ValueError('PUBLICATION_SOURCE_DRIFT')
  old.guard()
  if digest(Path(__file__).read_bytes()) != SOURCE_SHA or {p.name for p in ASSETS.iterdir()} != set(ASSET_BYTES):
    raise ValueError('CANDIDATE_VISUALIZER_SOURCE_DRIFT')
  for name, data in ASSET_BYTES.items():
    p = ASSETS / name
    if p.is_symlink() or p.read_bytes() != data:
      raise ValueError('CANDIDATE_VISUALIZER_ASSET_DRIFT')


def load():
  guard()
  p = e.PUBLIC / 'measurement-resolution-candidate-audit-v1.json'
  if p.is_symlink():
    raise ValueError('NO_PUBLICATION_SYMLINK')
  return e.validate_public(json.loads(p.read_bytes()))


def make_server(*, host='127.0.0.1', port=0):
  if host != '127.0.0.1':
    raise ValueError('LOOPBACK_ONLY_REQUIRED')
  report = load()
  server = old.make_server(host=host, port=port)
  parent = server.RequestHandlerClass

  class Handler(parent):
    def do_GET(self):
      try:
        guard()
      except (OSError, ValueError):
        return self.reply(400, {'error': 'AUDIT_SOURCE_CHANGED'})
      if not self.allowed():
        return self.reply(403, {'error': 'LOOPBACK_ORIGIN_REQUIRED'})
      if self.path == '/api/candidate-resolution':
        return self.reply(200, report)
      routes = {
        '/candidate-resolution': ('index.html', 'text/html'),
        '/candidate-resolution.js': ('app.js', 'text/javascript'),
        '/candidate-resolution.css': ('style.css', 'text/css'),
      }
      if self.path in routes:
        name, kind = routes[self.path]
        return self.reply(200, ASSET_BYTES[name].decode(), kind)
      if self.path == '/meter':
        page = old.ASSET_BYTES['index.html'].decode()
        page = page.replace('<body>', '<body><nav><a href="/candidate-resolution">Candidate effect vs diagnostic resolution</a></nav>')
        return self.reply(200, page, 'text/html')
      return super().do_GET()

  server.RequestHandlerClass = Handler
  return server


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--port', type=int, default=0)
  args = parser.parse_args()
  server = make_server(port=args.port)
  print('Open http://127.0.0.1:' + str(server.server_port) + '/candidate-resolution', flush=True)
  try:
    server.serve_forever()
  except KeyboardInterrupt:
    pass
  finally:
    server.server_close()


if __name__ == '__main__':
  main()
