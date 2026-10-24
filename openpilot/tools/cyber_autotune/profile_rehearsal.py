"""Immutable offline snapshot selection; never a runtime profile loader.

Stages are documentary rehearsal, not authenticated qualification. Operator
confirmation is recorded but cannot enable vehicle activation. Existing archive
primitives provide no-overwrite atomic local receipts. Corruption/missing data
fails closed; no silent repair or guessed rollback is performed.
"""
from dataclasses import dataclass, replace

from openpilot.tools.cyber_autotune import archive
from openpilot.tools.cyber_autotune.archive_codec import _pack, _unpack, decode_proposal, encode_proposal
from openpilot.tools.cyber_autotune.audit import REASON_CODE
from openpilot.tools.cyber_autotune.contracts import is_sha256
from openpilot.tools.cyber_autotune.native_protocol import digest


SCHEMA = 'profile-rehearsal-v1'
NEXT = {('INACTIVE', 'SANDBOX'): 'SANDBOX', ('SANDBOX', 'SHADOW_REHEARSAL'): 'SHADOW_REHEARSAL',
        ('SHADOW_REHEARSAL', 'REVIEW'): 'REVIEW_REQUIRED', ('REVIEW_REQUIRED', 'REQUEST_ACTIVATION'): 'ACTIVATION_BLOCKED',
        ('ROLLBACK_PENDING', 'ROLLBACK'): 'ROLLED_BACK'}


@dataclass(frozen=True)
class SnapshotRehearsal:
  baseline: bytes
  candidate: bytes
  events: tuple[bytes, ...] = ()


def _sha(value):
  return type(value) is str and is_sha256(value)


def _inspect(state):
  if type(state) is not SnapshotRehearsal or type(state.events) is not tuple or len(state.events) > 8:
    raise ValueError('INVALID_REHEARSAL')
  baseline, candidate = decode_proposal(state.baseline), decode_proposal(state.candidate)
  if (baseline.binding != candidate.binding or baseline.name != candidate.name or
      baseline.proposed_value != baseline.baseline_value or baseline.baseline_value != candidate.baseline_value or
      state.baseline == state.candidate):
    raise ValueError('INVALID_SNAPSHOT_BINDING')
  status, previous = 'INACTIVE', digest(state.baseline + state.candidate)
  for payload in state.events:
    event = _unpack(payload, SCHEMA, ('action', 'reason', 'result_sha256', 'previous_sha256', 'operator_confirmed'))
    if (type(event['reason']) is not str or REASON_CODE.fullmatch(event['reason']) is None or
        not _sha(event['result_sha256']) or event['previous_sha256'] != previous or
        type(event['operator_confirmed']) is not bool or type(event['action']) is not str):
      raise ValueError('INVALID_REHEARSAL_EVENT')
    action = event['action']
    if action == 'FAULT' and status not in ('ROLLBACK_PENDING', 'ROLLED_BACK'):
      status = 'ROLLBACK_PENDING'
    elif (status, action) in NEXT:
      status = NEXT[status, action]
    else:
      raise ValueError('ILLEGAL_REHEARSAL_TRANSITION')
    previous = digest(payload)
  return baseline, candidate, status, previous


def new_rehearsal(baseline, candidate) -> SnapshotRehearsal:
  state = SnapshotRehearsal(encode_proposal(baseline), encode_proposal(candidate))
  _inspect(state)
  return state


def advance(state, action: str, reason: str, result_sha256: str, *, operator_confirmed=False) -> SnapshotRehearsal:
  _, _, _, previous = _inspect(state)
  event = _pack({'schema': SCHEMA, 'action': action, 'reason': reason, 'result_sha256': result_sha256,
                 'previous_sha256': previous, 'operator_confirmed': operator_confirmed})
  result = replace(state, events=(*state.events, event))
  _inspect(result)
  return result


def assess(state) -> dict:
  baseline, _, status, event_sha = _inspect(state)
  selected = state.candidate if status in ('SANDBOX', 'SHADOW_REHEARSAL', 'REVIEW_REQUIRED', 'ACTIVATION_BLOCKED') else state.baseline
  return {'state': status, 'scope': 'OFFLINE_SNAPSHOT_SELECTION_ONLY', 'event_sha256': event_sha,
          'software_sha256': baseline.binding.software_sha256, 'configuration_sha256': baseline.binding.configuration_sha256,
          'baseline_snapshot_sha256': digest(state.baseline), 'candidate_snapshot_sha256': digest(state.candidate),
          'selected_snapshot_sha256': digest(selected), 'real_vehicle_verified': False, 'runtime_accepted': False,
          'active_profile_enabled': False, 'vehicle_write_enabled': False, 'can_write_enabled': False,
          'promotable_to_vehicle': False, 'vehicle_rollback_executed': False}


def encode_state(state) -> bytes:
  _inspect(state)
  return _pack({'schema': SCHEMA, 'baseline': state.baseline.decode(), 'candidate': state.candidate.decode(),
                'events': [e.decode() for e in state.events], 'runtime_accepted': False})


def decode_state(payload) -> SnapshotRehearsal:
  record = _unpack(payload, SCHEMA, ('baseline', 'candidate', 'events', 'runtime_accepted'))
  if (record['runtime_accepted'] is not False or type(record['baseline']) is not str or type(record['candidate']) is not str or
      type(record['events']) is not list or any(type(e) is not str for e in record['events'])):
    raise ValueError('INVALID_REHEARSAL_ENVELOPE')
  state = SnapshotRehearsal(record['baseline'].encode(), record['candidate'].encode(), tuple(e.encode() for e in record['events']))
  _inspect(state)
  return state


@archive._boundary
def save_state(root: str, state) -> str:
  payload = encode_state(state)
  key = digest(payload)
  with archive._directory(root) as directory:
    archive._store(directory, 'rehearsal-' + key + '.json', payload, decode_state)
  return key


@archive._boundary
def load_state(root: str, key: str, software_sha256: str, configuration_sha256: str) -> SnapshotRehearsal:
  archive._key(key)
  if not _sha(software_sha256) or not _sha(configuration_sha256):
    raise ValueError('INVALID_EXPECTED_IDENTITY')
  with archive._directory(root) as directory:
    payload = archive._read(directory, 'rehearsal-' + key + '.json')
    if payload is None or digest(payload) != key:
      raise ValueError('MISSING_OR_CORRUPT_REHEARSAL')
    state = decode_state(payload)
    result = assess(state)
    if result['software_sha256'] != software_sha256 or result['configuration_sha256'] != configuration_sha256:
      raise ValueError('REHEARSAL_REVALIDATION_REQUIRED')
    return state
