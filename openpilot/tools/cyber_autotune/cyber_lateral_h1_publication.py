"""Pinned aggregate-only H1 evidence. Never opens raw inputs or executes experiments."""

import json

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import cyber_lateral_h1_contract as c
from openpilot.tools.cyber_autotune import simulator_reuse_publication as reuse

PINS = {
  'cyber-lateral-h1-policy-v1.json': 'a9a2f5476d8d19dbc3a83491b69eeb47e39008367a46b7d66223e78455c133b8',
  'cyber-lateral-h1-schema-v1.json': '737127aa4371fc3f4772f0dceb71069384684d107b86aace19193281e8cd4169',
  'cyber-lateral-h1-synthetic-trace-v1.json': 'f8ce35ee98b667ff8d83836afc4f38231fce71f366dadd68bbc96bef6e81da1a',
  'cyber-lateral-h1-repeatability-v1.json': '6dc1a280340e35812ff8c5525cc6f63bd4b3088d84070507419960a96e303d8c',
  'cyber-lateral-h1-readiness-v1.json': '140081912d18936df21489ba82c89986a0838f584acea2048605534a651b0413',
}


def validate(rows):
  if type(rows) is not dict or set(rows) != set(PINS) or len(rows) != 5:
    raise ValueError('H1_EXACT_FIVE_PUBLIC_ARTIFACTS')
  for name, row in rows.items():
    p.verify(row)
    if row['receipt_sha256'] != PINS[name]:
      raise ValueError('H1_PUBLICATION_PIN_DRIFT')
  if rows['cyber-lateral-h1-policy-v1.json'] != c.policy() or rows['cyber-lateral-h1-schema-v1.json'] != c.schema():
    raise ValueError('H1_POLICY_SCHEMA_SOURCE_DRIFT')
  trace = rows['cyber-lateral-h1-synthetic-trace-v1.json']
  repeat = rows['cyber-lateral-h1-repeatability-v1.json']
  ready = rows['cyber-lateral-h1-readiness-v1.json']
  if (
    trace['row_count'] != 800
    or trace['tier'] != c.TIER
    or repeat['executions'] != 2
    or repeat['experiment_result_sha256'] != repeat['observer_removed_result_sha256']
    or repeat['trace_sha256'] != trace['trace_sha256']
    or repeat['trace_receipt_sha256'] != trace['trace_receipt_sha256']
    or ready['holdout_opening'] != 'CLOSED'
    or ready['opening_count'] != 0
    or ready['visual_readiness'] != 'VISUAL_FRAME_CONVERSION_PARTIAL'
  ):
    raise ValueError('H1_REPEATABILITY_OR_AUTHORITY_DRIFT')
  return rows


def load():
  reuse.load()
  rows = {}
  for name in PINS:
    path = p.PUBLIC / name
    if any(part.is_symlink() for part in (path, *path.parents)):
      raise ValueError('H1_PUBLICATION_SYMLINK')
    rows[name] = json.loads(path.read_bytes())
  return validate(rows)
