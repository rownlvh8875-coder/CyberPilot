"""Immutable external visual pages/catalog. Never reads a raw/private route."""

import json

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import cyber_lateral_h1_producer as h
from openpilot.tools.cyber_autotune import cyber_h1_visual_adapter as a


def root_path(store):
  return h.store_path(store).parent


def catalog(fs):
  return p.seal(
    {
      'schema': 'CYBER_VISUAL_RUN_CATALOG_V1',
      'runs': [
        {
          'run_id': fs['run_id'],
          'title': 'Offline H1 · driver_events · baseline only',
          'scenario': fs['scenario'],
          'arm_names': fs['arms'],
          'frame_count': fs['frame_count'],
          'duration_ns': fs['duration_ns'],
          'tier': fs['evidence_tier'],
          'source_trace_sha256': fs['source_trace_sha256'],
          'frameset_receipt_sha256': fs['receipt_sha256'],
          'comparison_ready': False,
          'comparison_reason': a.REASON,
          'availability_summary': fs['unavailable_fields'],
          'blockers': p.BLOCKERS,
          'verdict': fs['verdict'],
        }
      ],
    }
  )


def persist_exact(path, row):
  expected = (json.dumps(row, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()
  for candidate in (path, path.with_name(path.name + '.atomic')):
    if candidate.is_symlink():
      raise ValueError('VISUAL_STORE_SYMLINK')
    if candidate.exists() and candidate.read_bytes() != expected:
      raise ValueError('VISUAL_IMMUTABLE_FILE_BYTES')
  p.persist(path, row)
  if path.read_bytes() != expected:
    raise ValueError('VISUAL_IMMUTABLE_FILE_BYTES')


def persist(store, fs):
  a.validate_frameset(fs)
  root = root_path(store)
  persist_exact(root / 'policy.json', a.policy())
  persist_exact(root / 'schema.json', a.schema())
  from openpilot.tools.cyber_autotune.cyber_h1_visual_server import contract

  persist_exact(root / 'server-contract.json', contract())
  pages = []
  for offset in range(0, a.COUNT, a.PAGE_SIZE):
    rows = fs['frames'][offset : offset + a.PAGE_SIZE]
    page = p.seal(
      {
        'schema': 'CYBER_H1_VISUAL_PAGE_V1',
        'run_id': fs['run_id'],
        'offset': offset,
        'count': len(rows),
        'frames_sha256': p.sha(p.canonical(rows)),
        'frames': rows,
      }
    )
    name = f'page-{len(pages):03d}.json'
    persist_exact(root / name, page)
    pages.append({'name': name, 'offset': offset, 'count': len(rows), 'receipt_sha256': page['receipt_sha256']})
  manifest = p.seal(
    {
      'schema': 'CYBER_H1_VISUAL_STORE_V1',
      'frameset': {k: v for k, v in fs.items() if k != 'frames'},
      'pages': pages,
      'catalog': catalog(fs),
      'frame_count': a.COUNT,
      'run_id': fs['run_id'],
    }
  )
  # Manifest last: an interrupted partial store never becomes a valid catalog.
  persist_exact(root / 'manifest.json', manifest)
  loaded = load(root)
  if p.canonical(loaded['frames']) != p.canonical(fs['frames']):
    raise ValueError('VISUAL_EXACT_RESUME_BYTES')
  return manifest


def read_json(root, name):
  path = root / name
  if any(x.is_symlink() for x in (path, *path.parents)) or not path.is_file() or path.stat().st_size > 8 * 1024 * 1024:
    raise ValueError('VISUAL_STORE_FILE_SYMLINK_SIZE')
  raw = path.read_bytes()
  row = json.loads(raw)
  if raw != (json.dumps(row, sort_keys=True, indent=2, allow_nan=False) + '\n').encode():
    raise ValueError('VISUAL_NONCANONICAL_FILE_BYTES')
  return row


def load(store):
  root = root_path(store)
  if read_json(root, 'policy.json') != a.policy() or read_json(root, 'schema.json') != a.schema():
    raise ValueError('VISUAL_STALE_SOURCE_OR_SCHEMA')
  from openpilot.tools.cyber_autotune.cyber_h1_visual_server import contract

  if read_json(root, 'server-contract.json') != contract():
    raise ValueError('VISUAL_SERVER_ASSET_SOURCE_DRIFT')
  m = read_json(root, 'manifest.json')
  p.verify(m)
  h.keys(m, ('schema', 'frameset', 'pages', 'catalog', 'frame_count', 'run_id', *p.FIREWALL, 'receipt_sha256'))
  if m['schema'] != 'CYBER_H1_VISUAL_STORE_V1' or m['frame_count'] != a.COUNT or len(m['pages']) != 8:
    raise ValueError('VISUAL_PAGE_RECONCILIATION')
  frames = []
  for i, entry in enumerate(m['pages']):
    if entry['name'] != f'page-{i:03d}.json' or entry['offset'] != i * a.PAGE_SIZE or entry['count'] != a.PAGE_SIZE:
      raise ValueError('VISUAL_PAGE_LINEAGE')
    h.keys(entry, ('name', 'offset', 'count', 'receipt_sha256'))
    page = read_json(root, entry['name'])
    p.verify(page)
    h.keys(page, ('schema', 'run_id', 'offset', 'count', 'frames_sha256', 'frames', *p.FIREWALL, 'receipt_sha256'))
    if page['schema'] != 'CYBER_H1_VISUAL_PAGE_V1':
      raise ValueError('VISUAL_PAGE_SCHEMA')
    if (
      page['receipt_sha256'] != entry['receipt_sha256']
      or page['run_id'] != m['run_id']
      or page['offset'] != entry['offset']
      or page['count'] != len(page['frames'])
      or type(page['count']) is not int
      or page['count'] != entry['count']
      or page['frames_sha256'] != p.sha(p.canonical(page['frames']))
    ):
      raise ValueError('VISUAL_PAGE_SHA_DRIFT')
    frames.extend(page['frames'])
  fs = {**m['frameset'], 'frames': frames}
  a.validate_frameset(fs)
  if m['catalog'] != catalog(fs) or m['run_id'] != fs['run_id']:
    raise ValueError('VISUAL_CATALOG_DRIFT')
  return {**m, 'frames': frames}
