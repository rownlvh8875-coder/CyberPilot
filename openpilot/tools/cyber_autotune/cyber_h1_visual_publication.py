"""Aggregate-only visual evidence pins; no experiment or private-store execution."""

import json
from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import cyber_lateral_h1_publication as historical
from openpilot.tools.cyber_autotune import cyber_h1_visual_adapter as a
from openpilot.tools.cyber_autotune import cyber_h1_visual_server as server

PINS = {
  'cyber-h1-visual-browser-validation-v1.json': '8551ef7a8f18fd14407444d24e98a755fe1a56ebaaae51349e38e3fa3d2f9d4a',
  'cyber-h1-visual-catalog-v1.json': '9b4533e9459ad3de3a2be99b13629f36c67df5cecff970114cfeaa4cf65d4a38',
  'cyber-h1-visual-frame-schema-v1.json': '192c38f449ee8b13412168a6516a3ed96e8c74f1186e0c94d73b2931dd853188',
  'cyber-h1-visual-frameset-policy-v1.json': '981cbcf6ef65210b0cce4fe4d45488b7ce1cc55b2595f98a1c6eb98967ed4222',
  'cyber-h1-visual-readiness-v1.json': '9d6a5f34337fb2c0862e7af975b7ea4aaf942cc830b57e2666b569bd7ab1c72f',
  'cyber-h1-visual-server-contract-v1.json': 'ff53ad8a530a062157d02dfbec33e8e90c35628700cef9d05a75930b37a22d25',
}


def validate_server_contract():
  name = 'cyber-h1-visual-server-contract-v1.json'
  path = p.PUBLIC / name
  if any(x.is_symlink() for x in (path, *path.parents)):
    raise ValueError('VISUAL_SERVER_CONTRACT_SYMLINK')
  row = json.loads(path.read_bytes())
  p.verify(row)
  if row['receipt_sha256'] != PINS.get(name) or row != server.contract():
    raise ValueError('VISUAL_SERVER_FIXED_PUBLICATION_SOURCE_DRIFT')
  return row


def validate(rows):
  if type(rows) is not dict or set(rows) != set(PINS) or len(rows) != 6:
    raise ValueError('VISUAL_EXACT_SIX_PUBLIC_ARTIFACTS')
  for name, row in rows.items():
    p.verify(row)
    if row['receipt_sha256'] != PINS[name]:
      raise ValueError('VISUAL_PUBLICATION_PIN_DRIFT')
  if (
    rows['cyber-h1-visual-frameset-policy-v1.json'] != a.policy()
    or rows['cyber-h1-visual-frame-schema-v1.json'] != a.schema()
    or rows['cyber-h1-visual-server-contract-v1.json'] != server.contract()
  ):
    raise ValueError('VISUAL_SOURCE_POLICY_DRIFT')
  cat = rows['cyber-h1-visual-catalog-v1.json']
  browser = rows['cyber-h1-visual-browser-validation-v1.json']
  ready = rows['cyber-h1-visual-readiness-v1.json']
  if (
    len(cat['runs']) != 1
    or cat['runs'][0]['frame_count'] != 800
    or cat['runs'][0]['comparison_ready'] is not False
    or browser['status'] != 'ACTUAL_BROWSER_VALIDATED'
    or browser['frames_loaded'] != 800
    or browser['pages_loaded'] != 8
    or any(browser[k] != 0 for k in ('javascript_errors', 'network_errors', 'external_network_requests'))
    or browser['server_contract_sha256'] != server.contract()['receipt_sha256']
    or browser['frameset_receipt_sha256'] != cat['runs'][0]['frameset_receipt_sha256']
    or ready['holdout_opening'] != 'CLOSED'
    or ready['opening_count'] != 0
    or ready['comparison_ready'] is not False
    or ready['arm_count'] != 1
    or ready['calibration_blockers'] != p.BLOCKERS
  ):
    raise ValueError('VISUAL_READINESS_OR_BROWSER_DRIFT')
  return rows


def load():
  historical.load()
  rows = {}
  for name in PINS:
    path = p.PUBLIC / name
    if any(x.is_symlink() for x in (path, *path.parents)):
      raise ValueError('VISUAL_PUBLICATION_SYMLINK')
    rows[name] = json.loads(path.read_bytes())
  return validate(rows)
