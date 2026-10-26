"""Exact source-audit publication pins. No external source/data reader or runtime import."""

import json
from pathlib import Path
from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import simulator_reuse_contracts as c
from openpilot.tools.cyber_autotune import future_empirical_publication as future

PINS = {
  "simulator-reuse-audit-v1.json": "09c5bebb83d89e6a01bc04f58fe59a4e0be2addbd2193f01f4263b2639bbfc7a",
  "simulator-reuse-matrix-v1.json": "3ce6949bfab3a376b1579944e0737888b0874a97594055d64d0d1e0007b6a639",
  "simulator-source-identity-v1.json": "56548fc7734433699349f37e548e7dceb5d5a5062af5d802c6b591a09b4572d3",
  "simulator-overlap-analysis-v1.json": "2882922a3e0268863af66e802aad38fa66640f774bd1d42b719cb520462a64ab",
  "cyber-lateral-observability-contract-v1.json": "2838621b5f9aa1acd7ed0b98de54cdb3a6e49349c5c04702ec2ac1ee2c5b5da0",
  "cyber-simulation-fidelity-contract-v1.json": "d9c152d2b39c96bee17153929aaef9f7b66b801b0c8e87b74fca29dce597b096",
  "cyber-holdout-exposure-contract-v1.json": "f1f8cd3792762d85c02b3b4f78694f311e60c484b84d227da4c95f92d4aacada",
  "cyber-visual-adapter-contract-v1.json": "ba84de4eca66463e02a675921977a589a9afe8781327ed8e16a3a448c3fd8ad6",
}


def validate(rows):
  if type(rows) is not dict or set(rows) != set(PINS):
    raise ValueError('EXACT_EIGHT_REUSE_ARTIFACTS_REQUIRED')
  for name, row in rows.items():
    p.verify(row)
    if row['receipt_sha256'] != PINS[name]:
      raise ValueError('EXACT_SOURCE_CONTRACT_OR_PUBLICATION_PIN_DRIFT')
  if {name: rows[name] for name in c.NAMES} != c.artifacts():
    raise ValueError('REUSE_CONTRACT_SOURCE_DRIFT')
  return rows


def load():
  future.load()
  rows = {}
  for name in PINS:
    path = p.PUBLIC / name
    if any(part.is_symlink() for part in (path, *path.parents)):
      raise ValueError('NO_REUSE_PUBLICATION_SYMLINK')
    rows[name] = json.loads(path.read_bytes())
  validate(rows)
  root = Path(__file__).resolve().parents[3]
  for row in rows['simulator-source-identity-v1.json']['cyberpilot_sources']:
    if row['commit'] == c.IMPLEMENTATION_BASE and row['status'] == 'PRESENT':
      path = root / row['path']
      if path.is_symlink() or p.sha(path.read_bytes()) != row['file_sha256']:
        raise ValueError('HISTORICAL_CYBERPILOT_SOURCE_DRIFT')
  return rows
