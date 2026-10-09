"""Exact frozen architecture publication; new contracts cannot authorize algorithms."""
import json
from pathlib import Path

from openpilot.tools.cyber_autotune import candidate_architecture as a
from openpilot.tools.cyber_autotune.native_protocol import digest

PUBLIC = a.ROOT / "docs/cyberpilot/changes"
FILES = {'decision': ('candidate-architecture-decision-v1.json', '50f5a8f3d07e6819ecd4937222592b2a4af08c3db8b619f352328040bcf05e6f'),
 'trajectory': ('trajectory-authority-contract-v1.json', '6332e70a53698abe07cf6209e7d3e2796e473f75bf698a13cda6c18b09bd77f0'),
 'smoothness': ('smoothness-governor-contract-v1.json', '8ca2829af7fe5e905f10cee016745a62d9d7876506f185aaece70d6ebf15ed67'),
 'composed': ('composed-candidate-contract-v1.json', 'c64122725bdc9d3bc5fce03fe5528ba125d6ecbc9cc705c92533c078c636f622'),
 'matrix': ('candidate-experiment-matrix-v1.json', '6021a6c11b764c32a88f7f4d7f839b620fab5eff6537abb8b24a3b90019bd818'),
 'probe': ('candidate-architecture-probe-v1.json', '477f68bcf4377e1276fa2d25f005b829ccebd0cf991c1203a52bd049d5ab9aa8'),
 'readiness': ('candidate-architecture-readiness-v1.json', 'b0de51af8f38aaa6e2c5a601ef8d95abee60c7b674abfd4b89f0bdc12c0ee520')}

ALLOWED = frozenset(sha for _, sha in FILES.values())


def validate(row):
  if type(row) is not dict or row.get('receipt_sha256') not in ALLOWED:
    raise ValueError('EXACT_FROZEN_ARCHITECTURE_RECEIPT_REQUIRED')
  if a.hash_object({k: v for k, v in row.items() if k != 'receipt_sha256'}) != row['receipt_sha256']:
    raise ValueError('ARCHITECTURE_PUBLICATION_DRIFT')
  return row


def load():
  reports = {}
  for key, (name, sha) in FILES.items():
    path = PUBLIC / name
    if path.is_symlink() or any(p.is_symlink() for p in path.parents):
      raise ValueError('NO_PUBLICATION_SYMLINK')
    row = validate(json.loads(path.read_bytes()))
    if row['receipt_sha256'] != sha:
      raise ValueError('ARCHITECTURE_FILE_BINDING_REQUIRED')
    reports[key] = row
  return reports


def validate_sources(reports):
  for name, sha in reports['decision']['sources'].items():
    path = Path(__file__).parent / name
    if path.is_symlink() or digest(path.read_bytes()) != sha:
      raise ValueError('ARCHITECTURE_SOURCE_DRIFT')
  for row in reports['decision']['injection_points']:
    if digest((a.ROOT / row['source_path']).read_bytes()) != row['source_sha256']:
      raise ValueError('INJECTION_SOURCE_DRIFT')
