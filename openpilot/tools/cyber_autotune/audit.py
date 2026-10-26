"""Pure two-event offline job audit. Hash consistency is NOT authenticity.

A chain is STARTED then exactly one terminal job outcome. COMPLETED means the
job ended, never qualification PASS. No files, clocks, transport or actuation.
An external trusted checkpoint/signature is required against full-chain rewriting.
"""
from dataclasses import asdict, dataclass, fields
import hashlib
import json
import re

from openpilot.tools.cyber_autotune.contracts import is_sha256


GENESIS_SHA256 = '0' * 64
TERMINAL_STATUSES = frozenset({'STRUCTURAL_PREVIEW', 'BLOCKED', 'FAILED', 'TIMEOUT', 'COMPLETED'})
# Diagnostic codes, not free-text logs, paths or serialized inputs.
REASON_CODE = re.compile(r'[A-Z][A-Z0-9_]{0,127}')


@dataclass(frozen=True)
class AuditEvent:
  sequence: int
  run_sha256: str
  profile_sha256: str
  source_sha256: str
  configuration_sha256: str
  inputs_sha256: str
  evaluator_sha256: str
  status: str
  reasons: tuple[str, ...]
  previous_sha256: str


@dataclass(frozen=True)
class AuditRecord:
  event: AuditEvent
  sha256: str


def _valid_event(event) -> bool:
  if (type(event) is not AuditEvent or type(event.sequence) is not int or event.sequence not in (0, 1)
      or type(event.status) is not str or event.status not in TERMINAL_STATUSES | {'STARTED'}):
    return False
  if not all(type(getattr(event, item.name)) is str and is_sha256(getattr(event, item.name))
             for item in fields(event) if item.name.endswith('_sha256')):
    return False
  return (type(event.reasons) is tuple and bool(event.reasons)
          and all(type(reason) is str and REASON_CODE.fullmatch(reason) is not None for reason in event.reasons)
          and len(set(event.reasons)) == len(event.reasons))


def _digest(event: AuditEvent) -> str:
  payload = {'schema': 'cyber-autotune-audit-v1', 'event': asdict(event)}
  return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def verify_chain(chain: tuple[AuditRecord, ...]) -> bool:
  """Validate structure, content hashes and single-run continuity, not truth.

An empty or STARTED-only chain is valid structure but not a finished job. At most
two records are allowed; callers cannot merge different profiles into one run.
"""
  if type(chain) is not tuple or len(chain) > 2:
    return False
  for index, record in enumerate(chain):
    if type(record) is not AuditRecord or not _valid_event(record.event):
      return False
    if type(record.sha256) is not str or not is_sha256(record.sha256) or record.sha256 != _digest(record.event):
      return False
    event = record.event
    if event.sequence != index:
      return False
    if index == 0:
      if event.status != 'STARTED' or event.previous_sha256 != GENESIS_SHA256:
        return False
    else:
      if event.status not in TERMINAL_STATUSES or event.previous_sha256 != chain[index - 1].sha256:
        return False
      if any(getattr(event, item.name) != getattr(chain[0].event, item.name) for item in fields(event)
             if item.name.endswith('_sha256') and item.name != 'previous_sha256'):
        return False
  return True


def append_event(chain: tuple[AuditRecord, ...], event: AuditEvent) -> tuple[AuditRecord, ...]:
  """Return a new chain or raise ValueError; never overwrite invalid history."""
  if not verify_chain(chain) or not _valid_event(event):
    raise ValueError('Invalid audit chain or event')
  extended = (*chain, AuditRecord(event, _digest(event)))
  if not verify_chain(extended):
    raise ValueError('Invalid audit sequence, identity binding or state transition')
  return extended
