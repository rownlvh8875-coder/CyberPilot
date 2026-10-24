"""Pinned TA-only synthetic receipts. No reference/vehicle promotion authority."""
import json
from pathlib import Path

from openpilot.tools.cyber_autotune import candidate_architecture as a
from openpilot.tools.cyber_autotune import candidate_architecture_publication as old
from openpilot.tools.cyber_autotune.native_protocol import digest
from openpilot.tools.cyber_autotune.trajectory_v0_freeze import load as policies
from openpilot.tools.cyber_autotune.trajectory_v0_policy import PUBLIC

PINS = {'binding': ('trajectory-v0-execution-binding-v1.json', '0d294e3c989c8b2adce885a04ac112f5f3511a06a7fac9cd0d9ec8c38fc80b54'),
 'readiness': ('trajectory-v0-readiness-v1.json', 'db2633df48bce8dbce05033eb512527ea2f81e33908c3368aaf0e87bcb31853a'),
 'results': ('trajectory-v0-experiment-results-v1.json', '77bbf44c0bfcce5d7ce0e76a4ea5f488d84e3184fe984c3d92891f9c51a383fb')}


def validate(row):
  if type(row) is not dict or row.get('receipt_sha256') not in {sha for _, sha in PINS.values()}:
    raise ValueError('EXACT_TA_RECEIPT_REQUIRED')
  if a.hash_object({k: v for k, v in row.items() if k != 'receipt_sha256'}) != row['receipt_sha256']:
    raise ValueError('TA_PUBLICATION_DRIFT')
  return row


def load():
  policies()
  result = {}
  for key, (name, sha) in PINS.items():
    path = PUBLIC/name
    if path.is_symlink() or any(p.is_symlink() for p in path.parents):
      raise ValueError('NO_TA_PUBLICATION_SYMLINK')
    row = validate(json.loads(path.read_bytes()))
    if row['receipt_sha256'] != sha:
      raise ValueError('TA_FILE_BINDING_REQUIRED')
    result[key] = row
  binding = result['binding']
  for name, sha in binding['source_sha256'].items():
    if digest((Path(__file__).parent/name).read_bytes()) != sha:
      raise ValueError('TA_SOURCE_DRIFT')
  for name, sha in binding['executed_support_sha256'].items():
    if digest((a.ROOT/name).read_bytes()) != sha:
      raise ValueError('TA_SUPPORT_DRIFT')
  prior = old.load()['readiness']
  ready = result['readiness']
  if (ready['reference_blocker_graph_sha256'] != prior['reference_blocker_graph_sha256']
      or ready['historical_verdicts'] != prior['historical_verdicts']):
    raise ValueError('HISTORICAL_REFERENCE_DRIFT')
  return result
