"""Lossless, hash-bound aggregate sharding within the existing publication cap."""

import json
from pathlib import Path

from openpilot.tools.cyber_autotune import declared_meter_evidence as e
from openpilot.tools.cyber_autotune import declared_meter_diagnostic as m
from openpilot.tools.cyber_autotune.native_protocol import canonical, digest

TABLES = ('fixed_distance', 'holdout_projection', 'scenario_attribution', 'all_declared_envelopes')
INDEX = 'declared-hypothesis-meter-envelope-v1.json'
MAX_PART_BYTES = 1_048_576  # Existing publication scanner limit, never expanded.
SOURCE_SHA = digest(Path(__file__).read_bytes())


def identity():
  if digest(Path(__file__).read_bytes()) != SOURCE_SHA:
    raise ValueError('RUNNING_METER_SNAPSHOT_SOURCE_CHANGED')
  return SOURCE_SHA


def part_name(table):
  if table not in TABLES:
    raise ValueError('FIXED_PUBLIC_TABLE_NAME_REQUIRED')
  return 'declared-meter-' + table.replace('_', '-') + '-v1.json'


def write(report, destination):
  e.validate_public(report)
  root = Path(destination)
  refs = {}
  for table in TABLES:
    part = m.output({'schema': 'DECLARED_METER_PUBLIC_TABLE_V1', 'table': table, 'rows': report[table], 'aggregate_sha256': report['receipt_sha256']})
    data = canonical(part)
    if len(data) > MAX_PART_BYTES:
      raise ValueError('PUBLICATION_PART_SIZE_EXCEEDED')
    refs[table] = {'filename': part_name(table), 'file_sha256': digest(data), 'receipt_sha256': part['receipt_sha256']}
    e.immutable_write(root / part_name(table), data)
  index = m.output(
    {
      'schema': 'DECLARED_HYPOTHESIS_METER_PUBLIC_INDEX_V1',
      'publication_source_sha256': identity(),
      'aggregate_sha256': report['receipt_sha256'],
      'header': {k: v for k, v in report.items() if k not in TABLES},
      'tables': refs,
    }
  )
  e.immutable_write(root / INDEX, canonical(index))
  return index


def load(root):
  root = Path(root)
  index = json.loads((root / INDEX).read_bytes())
  m.unseal(index)
  if index['schema'] != 'DECLARED_HYPOTHESIS_METER_PUBLIC_INDEX_V1' or index['publication_source_sha256'] != identity():
    raise ValueError('EXACT_PUBLIC_INDEX_SOURCE_REQUIRED')
  if set(index['tables']) != set(TABLES):
    raise ValueError('ALL_FOUR_AGGREGATE_TABLES_REQUIRED')
  report = dict(index['header'])
  for table in TABLES:
    ref = index['tables'][table]
    if ref['filename'] != part_name(table):
      raise ValueError('FIXED_PUBLIC_CHUNK_FILENAME_REQUIRED')
    p = root / part_name(table)
    if p.is_symlink():
      raise ValueError('PUBLIC_CHUNK_SYMLINK_REJECTED')
    data = p.read_bytes()
    if len(data) > MAX_PART_BYTES or digest(data) != ref['file_sha256']:
      raise ValueError('PUBLIC_CHUNK_BYTES_CHANGED')
    part = json.loads(data)
    e.checked(part, ref['receipt_sha256'])
    if part['table'] != table or part['aggregate_sha256'] != index['aggregate_sha256']:
      raise ValueError('PUBLIC_CHUNK_AGGREGATE_BINDING')
    report[table] = part['rows']
  if report['receipt_sha256'] != index['aggregate_sha256']:
    raise ValueError('PUBLIC_AGGREGATE_IDENTITY_CHANGED')
  return e.validate_public(report)
