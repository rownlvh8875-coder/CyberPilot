"""Exact published synthetic aggregates only. Reject resealed edits/private fields."""

import json
from pathlib import Path

from openpilot.tools.cyber_autotune.native_protocol import canonical, digest

PUBLIC = Path(__file__).resolve().parents[3] / 'docs/cyberpilot/changes'
FILES = {
  'audit': ('controller-plant-authority-audit-v1.json', '396994f4e0936b9d9253682ae9042184701e874094380e43f4e0a59480ba6c18'),
  'stage': ('controller-plant-stage-attenuation-v1.json', '3f667f341ed30728418281419e3a5e4bb15765de604601a271ca2e817e0bd8ce'),
  'control': ('controller-plant-positive-control-v1.json', '1500bb52e16dc477d91859ac8c8d74fe2b0410c8ea7e8542ab204314f14b2e09'),
  'readiness': ('controller-plant-authority-readiness-v1.json', '7eb14c1aad3a208c144e0dad940e2bb08407ca122d058067d26df4ea8d31d6f0'),
  'findings': ('controller-plant-authority-findings-v1.json', 'c0fde89e072a2d1b8a1ac121a133235e17db2ee5b2adcbc4c5fd85a3fa516145'),
  'policy': ('controller-plant-authority-execution-policy-v1.json', 'fe4642a3dc0551110d2d9d110ff31513c5586477ef1d076bba01c493ec7dc681'),
}
ALLOWED = {sha for _, sha in FILES.values()}


def validate(row):
  if type(row) is not dict or row.get('receipt_sha256') not in ALLOWED:
    raise ValueError('EXACT_PUBLISHED_AUTHORITY_RECEIPT_REQUIRED')
  body = {k: v for k, v in row.items() if k != 'receipt_sha256'}
  if digest(canonical(body)) != row['receipt_sha256']:
    raise ValueError('AUTHORITY_PUBLICATION_CONTENT_DRIFT')
  return row


def load():
  reports = {}
  for key, (name, sha) in FILES.items():
    path = PUBLIC / name
    if path.is_symlink():
      raise ValueError('NO_PUBLICATION_SYMLINK')
    row = validate(json.loads(path.read_bytes()))
    if row['receipt_sha256'] != sha:
      raise ValueError('PUBLICATION_FILE_RECEIPT_MISMATCH')
    reports[key] = row
  return reports
