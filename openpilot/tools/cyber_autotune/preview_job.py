"""Restartable OFFLINE structural preview, not optimization or evaluation.

All numeric reviews/identities remain caller assertions. Only immutable proposal
artifacts are published; no controller callback, active profile or data reader.
Partial publication is retained for explicit retry. A failed archive operation
does not imply an outcome was durably logged: inspect after recovery.
"""
from dataclasses import asdict, dataclass, field, replace
from fractions import Fraction

from openpilot.tools.cyber_autotune import archive
from openpilot.tools.cyber_autotune.archive_codec import encode_proposal
from openpilot.tools.cyber_autotune.audit import AuditEvent, AuditRecord, GENESIS_SHA256, append_event
from openpilot.tools.cyber_autotune.contracts import is_sha256
from openpilot.tools.cyber_autotune.native_protocol import canonical, digest
from openpilot.tools.cyber_autotune.profiles import ProposalInput, inspect_proposal
from openpilot.tools.cyber_autotune.search import GridReview, preview_grid


PREVIEW_REASONS = ('EVIDENCE_VALIDATION_PENDING', 'NO_EVALUATOR_EXECUTED')


@dataclass(frozen=True)
class PreviewJobResult:
  status: str
  reasons: tuple[str, ...]
  run_sha256: str | None
  preview_sha256: str | None
  profile_sha256s: tuple[str, ...]
  candidate_generation_allowed: bool = field(default=False, init=False)
  offline_evaluable: bool = field(default=False, init=False)
  runtime_accepted: bool = field(default=False, init=False)


@dataclass(frozen=True)
class _Prepared:
  proposals: tuple[ProposalInput, ...]
  profile_sha256s: tuple[str, ...]
  preview_sha256: str
  chain: tuple[AuditRecord, ...]


def _result(status, reasons, prepared=None):
  return PreviewJobResult(status, reasons,
                          None if prepared is None else prepared.chain[0].event.run_sha256,
                          None if prepared is None else prepared.preview_sha256,
                          prepared.profile_sha256s if status == 'STRUCTURAL_PREVIEW' else ())


def _prepare(template, review, evaluator):
  if type(evaluator) is not str or not is_sha256(evaluator):
    return _result('BLOCKED', ('INVALID_EVALUATOR_IDENTITY',))
  preview = preview_grid(template, review)
  if preview.status != 'STRUCTURAL_PREVIEW':
    return _result('BLOCKED', preview.reasons)
  if Fraction(str(template.proposed_value)) != Fraction(str(template.baseline_value)):
    return _result('BLOCKED', ('TEMPLATE_NOT_BASELINE',))
  proposals = tuple(replace(template, proposed_value=entry.value) for entry in preview.entries)
  try:
    # Check every envelope before any filesystem access. Do not retain a grid's
    # worth of potentially large byte buffers; frozen proposals share bindings.
    for proposal in proposals:
      encode_proposal(proposal)
    inputs = digest(canonical({'schema': 'cyber-structural-preview-job-input-v1',
                               'template': encode_proposal(template).decode('utf-8'), 'grid_review': asdict(review)}))
    profile = inspect_proposal(template).profile_sha256
    binding = template.binding
    run = digest(canonical({'schema': 'cyber-structural-preview-job-v1', 'inputs': inputs, 'profile': profile,
                            'source': binding.software_sha256, 'configuration': binding.configuration_sha256, 'evaluator': evaluator}))
    first = append_event((), AuditEvent(0, run, profile, binding.software_sha256, binding.configuration_sha256,
                                       inputs, evaluator, 'STARTED', ('STRUCTURAL_PREVIEW_REQUESTED',), GENESIS_SHA256))
    chain = append_event(first, replace(first[0].event, sequence=1, previous_sha256=first[0].sha256,
                                       status='STRUCTURAL_PREVIEW', reasons=PREVIEW_REASONS))
  except (ValueError, TypeError, UnicodeError, RecursionError, OverflowError):
    return _result('BLOCKED', ('INVALID_SERIALIZED_REQUEST',))
  return _Prepared(proposals, tuple(entry.profile_sha256 for entry in preview.entries), preview.preview_sha256, chain)


def _checked_state(root, prepared):
  try:
    state = archive.load_audit(root, prepared.chain[0].event.run_sha256)
  except archive.ArchiveError as error:
    if error.code == 'NOT_FOUND':
      return None
    raise
  if state[:1] != prepared.chain[:1]:
    raise archive.ArchiveError('JOB_BINDING_MISMATCH')
  if len(state) == 2:
    if state != prepared.chain:
      raise archive.ArchiveError('UNEXPECTED_JOB_TERMINAL')
    for profile, expected in zip(prepared.profile_sha256s, prepared.proposals, strict=True):
      stored = archive.load_proposal(root, profile)
      if encode_proposal(stored) != encode_proposal(expected):
        raise archive.ArchiveError('JOB_PROPOSAL_MISMATCH')
  return state


def _inspect(root, prepared):
  state = _checked_state(root, prepared)
  if state is None:
    return _result('NOT_STARTED', ('AUDIT_NOT_STARTED',), prepared)
  if len(state) == 1:
    return _result('INCOMPLETE', ('AUDIT_INCOMPLETE',), prepared)
  return _result('STRUCTURAL_PREVIEW', PREVIEW_REASONS, prepared)


def inspect_preview(root: str, template: ProposalInput, review: GridReview, *, evaluator_sha256: str) -> PreviewJobResult:
  """Read/revalidate artifacts only; terminal status alone never suffices."""
  prepared = _prepare(template, review, evaluator_sha256)
  if type(prepared) is PreviewJobResult:
    return prepared
  try:
    return _inspect(root, prepared)
  except archive.ArchiveError as error:
    return _result('BLOCKED', ('ARCHIVE_' + error.code,), prepared)


def persist_preview(root: str, template: ProposalInput, review: GridReview, *, evaluator_sha256: str) -> PreviewJobResult:
  """Durably publish all preview artifacts or report BLOCKED, never a subset.

Caller supplies an existing archive directory. Retry is explicit and idempotent;
incomplete artifacts are not removed. Existing terminal history is checked before
any publication, so missing/corrupt terminal artifacts are never silently repaired.
No evaluator is invoked and no actual candidate-generation permission is granted.
"""
  prepared = _prepare(template, review, evaluator_sha256)
  if type(prepared) is PreviewJobResult:
    return prepared
  try:
    _checked_state(root, prepared)
    archive.save_audit(root, prepared.chain[:1])
    # A cooperating caller may have reached a terminal between these operations.
    _checked_state(root, prepared)
    for proposal in prepared.proposals:
      archive.save_proposal(root, proposal)
    archive.save_audit(root, prepared.chain)
    return _inspect(root, prepared)
  except archive.ArchiveError as error:
    return _result('BLOCKED', ('ARCHIVE_' + error.code,), prepared)
