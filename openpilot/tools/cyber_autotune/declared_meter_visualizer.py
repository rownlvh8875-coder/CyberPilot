"""Additive meter tab around the unchanged loopback geometry visualizer."""

import argparse
import json
from pathlib import Path

from openpilot.tools.cyber_autotune import approximate_geometry_visualizer as old
from openpilot.tools.cyber_autotune import declared_meter_diagnostic as m
from openpilot.tools.cyber_autotune import declared_meter_evidence as e
from openpilot.tools.cyber_autotune import declared_meter_snapshot as snapshot

ASSETS = Path(__file__).with_name('declared_meter_assets')
SOURCE_SHA = m.q.digest(Path(__file__).read_bytes())
ASSET_BYTES = {name: (ASSETS / name).read_bytes() for name in ('index.html', 'app.js', 'style.css')}


def guard():
  old.guard()
  m.policy()
  e.executor_identity()
  snapshot.identity()
  if m.q.digest(Path(__file__).read_bytes()) != SOURCE_SHA:
    raise ValueError('METER_VISUALIZER_SOURCE_CHANGED')
  if {p.name for p in ASSETS.iterdir()} != set(ASSET_BYTES):
    raise ValueError('METER_VISUALIZER_ASSET_SET_CHANGED')
  for name, data in ASSET_BYTES.items():
    if (ASSETS / name).is_symlink() or (ASSETS / name).read_bytes() != data:
      raise ValueError('METER_VISUALIZER_ASSET_CHANGED')


def synthetic_report():
  return m.output(
    {
      'status': 'CONDITIONAL_DIAGNOSTIC_COMPLETE',
      'fixed_distance': [],
      'holdout_projection': [],
      'scenarios': m.scenarios(),
      'open_terms': list(m.OPEN_TERMS),
      'coverage': {'total_frames': 0, 'both_visible': 0, 'both_matched': 0, 'center_unavailable': 0},
    }
  )


def make_server(*, host='127.0.0.1', port=0, report=None, scope='ACTUAL'):
  if host != '127.0.0.1':
    raise ValueError('LOOPBACK_ONLY_REQUIRED')
  guard()
  if report is not None and (scope != 'TEST_ONLY' or report != synthetic_report()):
    raise ValueError('NO_ARBITRARY_UI_REPORT_INJECTION')
  if report is None:
    report = snapshot.load(m.ROOT)
    e.validate_public(report)
    if report['source_bindings'] != e.frozen_bindings() or report['coverage'] != e.frozen_coverage():
      raise ValueError('HISTORICAL_METER_BINDINGS_REQUIRED')
    for key in ('fixed_distance', 'holdout_projection', 'scenario_attribution', 'all_declared_envelopes'):
      e.safe_numbers(report[key])
    if report['policy'] != m.policy() or any(report[k] is not False for k in m.FIREWALL):
      raise ValueError('EXACT_NONQUALIFYING_METER_POLICY_REQUIRED')
  server = old.make_server(host=host, port=port)
  parent = server.RequestHandlerClass
  assets = {name: data.decode() for name, data in ASSET_BYTES.items()}
  report = json.loads(m.q.canonical(report))

  class Handler(parent):
    def do_GET(self):
      try:
        guard()
      except (ValueError, OSError):
        return self.reply(400, {'error': 'METER_VISUALIZER_SOURCE_CHANGED'})
      if not self.allowed():
        return self.reply(403, {'error': 'LOOPBACK_ORIGIN_REQUIRED'})
      if self.path == '/api/meter':
        return self.reply(200, report)
      if self.path == '/meter':
        return self.reply(200, assets['index.html'], 'text/html')
      if self.path == '/meter.css':
        return self.reply(200, assets['style.css'], 'text/css')
      if self.path == '/meter.js':
        return self.reply(200, assets['app.js'], 'text/javascript')
      if self.path == '/':
        page = old.ASSET_BYTES['index.html'].decode()
        nav = '<nav><a href="/meter">APPROXIMATE METER DIAGNOSTIC</a></nav>'
        page = page.replace('<body>', '<body>' + nav)
        return self.reply(200, page, 'text/html')
      return super().do_GET()

  server.RequestHandlerClass = Handler
  return server


def main():
  parser = argparse.ArgumentParser(description='Local declared-hypothesis approximate meter diagnostic')
  parser.add_argument('--port', type=int, default=0)
  args = parser.parse_args()
  s = make_server(port=args.port)
  print('Open http://127.0.0.1:' + str(s.server_port) + '/meter', flush=True)
  try:
    s.serve_forever()
  except KeyboardInterrupt:
    pass
  finally:
    s.server_close()


if __name__ == '__main__':
  main()
