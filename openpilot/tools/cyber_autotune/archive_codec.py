"""Strict offline proposal/audit envelopes. Integrity is not evidence authority."""
from dataclasses import asdict, fields
import json

from openpilot.tools.cyber_autotune.audit import AuditEvent, AuditRecord, verify_chain
from openpilot.tools.cyber_autotune.native_protocol import _unique_pairs, canonical, digest
from openpilot.tools.cyber_autotune.profiles import ProposalBinding, ProposalInput, UpdateReview, inspect_proposal


MAX_ARCHIVE_BYTES = 1024 * 1024  # local artifact resource cap, not evidence quality
PROPOSAL_SCHEMA = 'cyber-proposal-archive-v1'
AUDIT_SCHEMA = 'cyber-job-audit-archive-v1'


def _keys(value, expected):
  if type(value) is not dict or set(value) != set(expected):
    raise ValueError('INVALID_ARCHIVE_FIELDS')


def _record(cls, value):
  _keys(value, (item.name for item in fields(cls)))
  return cls(**value)


def _nonfinite(_):
  raise ValueError('NONFINITE_ARCHIVE_VALUE')


def _pack(document):
  payload = canonical(dict(document, content_sha256=digest(canonical(document))))
  if len(payload) > MAX_ARCHIVE_BYTES:
    raise ValueError('ARCHIVE_TOO_LARGE')
  return payload


def _unpack(payload, schema, expected):
  if type(payload) is not bytes or not 0 < len(payload) <= MAX_ARCHIVE_BYTES:
    raise ValueError('INVALID_ARCHIVE_BYTES')
  try:
    document = json.loads(payload, object_pairs_hook=_unique_pairs, parse_constant=_nonfinite)
    _keys(document, (*expected, 'schema', 'content_sha256'))
    if document['schema'] != schema or canonical(document) != payload:
      raise ValueError('NONCANONICAL_ARCHIVE')
    claimed = document.pop('content_sha256')
    if type(claimed) is not str or claimed != digest(canonical(document)):
      raise ValueError('ARCHIVE_DIGEST_MISMATCH')
    return document
  except (TypeError, UnicodeError, RecursionError) as error:
    raise ValueError('INVALID_ARCHIVE_ENCODING') from error


def encode_proposal(proposal: ProposalInput) -> bytes:
  assessment = inspect_proposal(proposal)
  if not assessment.contracts_ready:
    raise ValueError('INVALID_PROPOSAL_CONTRACT')
  return _pack({'schema': PROPOSAL_SCHEMA, 'proposal': asdict(proposal), 'profile_sha256': assessment.profile_sha256,
                'runtime_accepted': False, 'offline_evaluable': False})


def decode_proposal(payload: bytes) -> ProposalInput:
  document = _unpack(payload, PROPOSAL_SCHEMA, ('proposal', 'profile_sha256', 'runtime_accepted', 'offline_evaluable'))
  if document['runtime_accepted'] is not False or document['offline_evaluable'] is not False:
    raise ValueError('INVALID_ARCHIVE_AUTHORITY')
  raw = document['proposal']
  _keys(raw, (item.name for item in fields(ProposalInput)))
  proposal = _record(ProposalInput, dict(raw, binding=_record(ProposalBinding, raw['binding']), review=_record(UpdateReview, raw['review'])))
  assessment = inspect_proposal(proposal)
  if not assessment.contracts_ready or document['profile_sha256'] != assessment.profile_sha256:
    raise ValueError('INVALID_PROPOSAL_CONTRACT')
  return proposal


def encode_audit(chain: tuple[AuditRecord, ...]) -> bytes:
  if not verify_chain(chain) or not chain:
    raise ValueError('INVALID_AUDIT_CHAIN')
  return _pack({'schema': AUDIT_SCHEMA, 'chain': [asdict(record) for record in chain],
                'run_sha256': chain[0].event.run_sha256, 'runtime_accepted': False})


def decode_audit(payload: bytes) -> tuple[AuditRecord, ...]:
  document = _unpack(payload, AUDIT_SCHEMA, ('chain', 'run_sha256', 'runtime_accepted'))
  if document['runtime_accepted'] is not False or type(document['chain']) is not list or not 1 <= len(document['chain']) <= 2:
    raise ValueError('INVALID_AUDIT_ENVELOPE')
  records = []
  for raw in document['chain']:
    _keys(raw, ('event', 'sha256'))
    event = raw['event']
    _keys(event, (item.name for item in fields(AuditEvent)))
    if type(event['reasons']) is not list:
      raise ValueError('INVALID_AUDIT_REASONS')
    records.append(AuditRecord(_record(AuditEvent, dict(event, reasons=tuple(event['reasons']))), raw['sha256']))
  chain = tuple(records)
  if not verify_chain(chain) or document['run_sha256'] != chain[0].event.run_sha256:
    raise ValueError('INVALID_AUDIT_CHAIN')
  return chain
