"""Atomic immutable local source/pair/pages/catalog storage, manifest committed last."""

import json
import os
from pathlib import Path

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import cyber_lateral_h1_producer as h
from openpilot.tools.cyber_autotune import cyber_h1_pairing as q
from openpilot.tools.cyber_autotune import cyber_h1_paired_visual_adapter as a
from openpilot.tools.cyber_autotune.cyber_h1_visual_catalog import read_json

PAGE_SIZE = 100


def persist_exact(path, row):
  q.verify(row)
  path = Path(path)
  expected = (json.dumps(row, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()
  for part in (path, *path.parents, path.with_name(path.name + '.atomic')):
    if part.is_symlink():
      raise ValueError('PAIR_STORE_SYMLINK')
  path.parent.mkdir(parents=True, exist_ok=True)
  if path.exists():
    if path.read_bytes() != expected:
      raise ValueError('PAIR_IMMUTABLE_BYTES_CONFLICT')
    return
  temporary = path.with_name(path.name + '.atomic')
  if temporary.exists():
    if temporary.read_bytes() != expected:
      raise ValueError('PAIR_STALE_ATOMIC_FILE')
  else:
    with temporary.open('xb') as handle:
      handle.write(expected)
      handle.flush()
      os.fsync(handle.fileno())
  os.link(temporary, path)
  temporary.unlink()


def persist_run(store, kind, scenario, packages, manifest, fs):
  if manifest != q.pair(*packages):
    raise ValueError('PAIR_MANIFEST_SOURCE_DRIFT')
  a.validate(fs, *packages)
  root = h.store_path(store).parent / kind / scenario
  for arm, package in zip((q.BASELINE, q.CAMPAIGNS[kind][1]), packages, strict=True):
    persist_exact(root / arm / 'h1-package.json', package)
  persist_exact(root / 'pair.json', manifest)
  pages = []
  for offset in range(0, fs['frame_count'], PAGE_SIZE):
    frames = fs['frames'][offset : offset + PAGE_SIZE]
    page = q.seal(
      {
        'schema': 'CYBER_H1_PAIRED_PAGE_V1',
        'run_id': fs['run_id'],
        'offset': offset,
        'count': len(frames),
        'frames': frames,
        'frames_sha256': p.sha(p.canonical(frames)),
      }
    )
    name = f'page-{len(pages):03d}.json'
    persist_exact(root / name, page)
    pages.append({'name': name, 'offset': offset, 'count': len(frames), 'receipt_sha256': page['receipt_sha256']})
  manifest = q.seal(
    {
      'schema': 'CYBER_H1_PAIRED_LOCAL_STORE_V1',
      'frameset': {k: v for k, v in fs.items() if k != 'frames'},
      'pages': pages,
      'pair_manifest_sha256': manifest['receipt_sha256'],
    }
  )
  persist_exact(root / 'manifest.json', manifest)
  return manifest


def catalog(entries):
  return q.seal(
    {
      'schema': 'CYBER_VISUAL_CAMPAIGN_CATALOG_V1',
      'campaigns': [
        {
          'campaign_id': info[0],
          'kind': kind,
          'title': 'Trajectory Authority · TA-B' if kind == 'TA_B' else 'Smoothness Governor · SG-A',
          'candidate_arm': info[1],
          'historical_verdict': info[2],
          'scenario_count': sum(e['kind'] == kind for e in entries),
          'evidence_tier': q.TIER,
          'comparison_ready': True,
          'blockers': p.BLOCKERS,
          'campaign_receipt_sha256': p.sha(p.canonical([e['pair']['receipt_sha256'] for e in entries if e['kind'] == kind])),
          'scenarios': [
            {
              'scenario': e['scenario'],
              'sample_count': e['pair']['sample_count'],
              'duration_ns': e['pair']['duration_ns'],
              'baseline_trace_sha256': e['pair']['baseline_trace_sha256'],
              'candidate_trace_sha256': e['pair']['candidate_trace_sha256'],
              'pair_receipt_sha256': e['pair']['receipt_sha256'],
              'paired_frameset_sha256': e['frameset']['receipt_sha256'],
              'exact_pairing': True,
              'availability_summary': e['frameset']['unavailable_fields'],
              'verdict': info[2],
            }
            for e in entries
            if e['kind'] == kind
          ],
        }
        for kind, info in q.CAMPAIGNS.items()
      ],
      'holdout_opening': 'CLOSED',
      'opening_count': 0,
    }
  )


def finish(store, entries):
  root = h.store_path(store).parent
  row = catalog(entries)
  persist_exact(root / 'catalog.json', row)
  from openpilot.tools.cyber_autotune.cyber_h1_comparison_server import contract

  persist_exact(root / 'server-contract.json', contract())
  return row


def load_run(root, kind, name, entry):
  folder = root / kind / name
  packages = [q.validate_package(read_json(folder / arm, 'h1-package.json')) for arm in (q.BASELINE, q.CAMPAIGNS[kind][1])]
  pair = q.pair(*packages)
  if read_json(folder, 'pair.json') != pair or pair['receipt_sha256'] != entry['pair_receipt_sha256']:
    raise ValueError('PAIR_STORED_SOURCE_MANIFEST_DRIFT')
  manifest = q.verify(read_json(folder, 'manifest.json'))
  frames = []
  count = pair['sample_count']
  if len(manifest['pages']) != (count + PAGE_SIZE - 1) // PAGE_SIZE:
    raise ValueError('PAIR_PAGE_COUNT_RECONCILIATION')
  for i, page_entry in enumerate(manifest['pages']):
    offset = i * PAGE_SIZE
    if page_entry['name'] != f'page-{i:03d}.json' or type(page_entry['offset']) is not int or page_entry['offset'] != offset:
      raise ValueError('PAIR_PAGE_LINEAGE')
    page = q.verify(read_json(folder, page_entry['name']))
    if (
      page['schema'] != 'CYBER_H1_PAIRED_PAGE_V1'
      or page['run_id'] != manifest['frameset']['run_id']
      or page['receipt_sha256'] != page_entry['receipt_sha256']
      or type(page['count']) is not int
      or page['count'] != min(PAGE_SIZE, count - offset)
      or page_entry['count'] != page['count']
      or page['offset'] != offset
      or page['count'] != len(page['frames'])
      or page['frames_sha256'] != p.sha(p.canonical(page['frames']))
    ):
      raise ValueError('PAIR_PAGE_SHA_OR_COUNT_DRIFT')
    frames.extend(page['frames'])
  fs = {**manifest['frameset'], 'frames': frames}
  a.validate(fs, *packages)
  if fs['receipt_sha256'] != entry['paired_frameset_sha256'] or manifest['pair_manifest_sha256'] != pair['receipt_sha256']:
    raise ValueError('PAIR_FRAMESET_RECEIPT_DRIFT')
  return {'frameset': {k: v for k, v in fs.items() if k != 'frames'}, 'frames': frames, 'pair': pair}


def load(store):
  root = h.store_path(store).parent
  cat = q.verify(read_json(root, 'catalog.json'))
  from openpilot.tools.cyber_autotune.cyber_h1_comparison_server import contract

  if read_json(root, 'server-contract.json') != contract():
    raise ValueError('PAIR_SERVER_SOURCE_DRIFT')
  context = q.policy()
  expected = [r['id'] for r in context['scenario_rows']]
  if cat['schema'] != 'CYBER_VISUAL_CAMPAIGN_CATALOG_V1' or len(cat['campaigns']) != 2 or cat['holdout_opening'] != 'CLOSED' or cat['opening_count'] != 0:
    raise ValueError('PAIR_CATALOG_SCOPE')
  result, entries = {}, []
  for (kind, info), campaign in zip(q.CAMPAIGNS.items(), cat['campaigns'], strict=True):
    if campaign['campaign_id'] != info[0] or campaign['scenario_count'] != len(expected) or [s['scenario'] for s in campaign['scenarios']] != expected:
      raise ValueError('PAIR_CATALOG_FROZEN_CAMPAIGNS_SCENARIOS')
    result[info[0]] = {}
    for entry in campaign['scenarios']:
      name = entry['scenario']
      data = load_run(root, kind, name, entry)
      if data['pair']['policy_sha256'] != context['receipt_sha256']:
        raise ValueError('PAIR_STALE_EXECUTION_POLICY')
      result[info[0]][name] = data
      entries.append({'kind': kind, 'scenario': name, 'pair': data['pair'], 'frameset': data['frameset']})
  if cat != catalog(entries):
    raise ValueError('PAIR_CATALOG_METADATA_DRIFT')
  return {'catalog': cat, 'runs': result}
