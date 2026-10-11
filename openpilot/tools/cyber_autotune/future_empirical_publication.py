"""Pinned future contracts. No private store is required for CI."""

import json
from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_grid_publication as grid
from openpilot.tools.cyber_autotune import future_empirical_contracts as c

PINS = {
  'future-empirical-generation-policy-v1.json': 'f582c1473460571041dab937943fba60b82fc32476cd2ed5e084f47f484b4761',
  'empirical-causal-context-schema-v2.json': 'b21f2b531dd719ba763c81594de82ac443e3ae9f9f3451fec67cb1065da52159',
  'future-route-admission-v1.json': '0ed1d944561bceefbd680b3a21abc927188ce222c8ee44a53c37092fb4c57c30',
  'future-route-role-assignment-v1.json': '3b82a414cb27cb2fdeb064cc9736d091bcf5c2705d1510bb09cfc3be5b84792c',
  'future-holdout-opening-contract-v1.json': 'f3e08b2dbcace8c89c0b5406b23216b87d104e89736f2d501e64fb5aaac8c649',
  'future-model-family-readiness-v1.json': 'ab86e1206feec5fbcf67a57d488f232dc40c98585fdad125f05466866dc70a22',
  'future-empirical-data-readiness-v1.json': 'f6ff56d3560d891eb48aaeacf33e93fb6e639c322dacb8bc55882885ef23fd2d',
}


def validate(rows):
  if set(rows) != set(c.NAMES):
    raise ValueError('EXACT_SEVEN_FUTURE_CONTRACTS_REQUIRED')
  for row in rows.values():
    p.verify(row)
  if rows != c.artifacts():
    raise ValueError('FUTURE_CONTRACT_SOURCE_AUTHORITY_OR_PUBLICATION_DRIFT')
  return rows


def load():
  grid.load()
  rows = {name: p.verify(json.loads((p.PUBLIC / name).read_bytes())) for name in c.NAMES}
  if {name: row['receipt_sha256'] for name, row in rows.items()} != PINS:
    raise ValueError('FUTURE_CONTRACT_PIN_DRIFT')
  return validate(rows)
