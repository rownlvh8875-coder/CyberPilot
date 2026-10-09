"""Additive loopback-only, immutable public synthetic authority visualization."""

import argparse
from pathlib import Path

from openpilot.tools.cyber_autotune import controller_plant_evidence as e
from openpilot.tools.cyber_autotune import controller_plant_findings as findings
from openpilot.tools.cyber_autotune import controller_plant_policy as policy
from openpilot.tools.cyber_autotune import controller_plant_publication as publication
from openpilot.tools.cyber_autotune import resolution_candidate_visualizer as old
from openpilot.tools.cyber_autotune.native_protocol import digest

ASSETS = Path(__file__).with_name('controller_plant_assets')
ASSET_BYTES = {name: (ASSETS / name).read_bytes() for name in ('index.html', 'app.js', 'style.css')}
SOURCE_SHA = digest(Path(__file__).read_bytes())
HELPERS = {x.__file__: digest(Path(x.__file__).read_bytes()) for x in (e, findings, policy, publication)}


def guard():
  old.guard()
  e.validate_policy(e.prepare_policy())
  if digest(Path(__file__).read_bytes()) != SOURCE_SHA or {p.name for p in ASSETS.iterdir()} != set(ASSET_BYTES):
    raise ValueError('AUTHORITY_UI_SOURCE_DRIFT')
  for path, sha in HELPERS.items():
    if digest(Path(path).read_bytes()) != sha:
      raise ValueError('AUTHORITY_UI_HELPER_DRIFT')
  for name, value in ASSET_BYTES.items():
    if (ASSETS / name).is_symlink() or (ASSETS / name).read_bytes() != value:
      raise ValueError('AUTHORITY_UI_ASSET_DRIFT')


def make_server(*, host='127.0.0.1', port=0):
  if host != '127.0.0.1':
    raise ValueError('LOOPBACK_ONLY_REQUIRED')
  guard()
  report = publication.load()
  server = old.make_server(host=host, port=port)
  parent = server.RequestHandlerClass

  class Handler(parent):
    def do_GET(self):
      try:
        guard()
      except (ValueError, OSError):
        return self.reply(400, {'error': 'AUTHORITY_SOURCE_DRIFT'})
      if not self.allowed():
        return self.reply(403, {'error': 'LOOPBACK_ORIGIN_REQUIRED'})
      if self.path == '/api/plant-authority':
        return self.reply(200, report)
      routes = {'/plant-authority': ('index.html', 'text/html'),
                '/plant-authority.js': ('app.js', 'text/javascript'),
                '/plant-authority.css': ('style.css', 'text/css')}
      if self.path in routes:
        name, kind = routes[self.path]
        return self.reply(200, ASSET_BYTES[name].decode(), kind)
      if self.path == '/candidate-resolution':
        page = old.ASSET_BYTES['index.html'].decode().replace(
          '<body>', '<body><nav><a href="/plant-authority">Controller to plant authority</a></nav>')
        return self.reply(200, page, 'text/html')
      return super().do_GET()

  server.RequestHandlerClass = Handler
  return server


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--port', type=int, default=0)
  args = parser.parse_args()
  server = make_server(port=args.port)
  print('Open http://127.0.0.1:' + str(server.server_port) + '/plant-authority', flush=True)
  try:
    server.serve_forever()
  except KeyboardInterrupt:
    pass
  finally:
    server.server_close()


if __name__ == '__main__':
  main()
