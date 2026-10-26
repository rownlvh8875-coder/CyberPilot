"""Bounded, deterministic structural preview; no evaluator or real search authority."""
from dataclasses import dataclass, field, replace
from fractions import Fraction
import hashlib
import json

from openpilot.tools.cyber_autotune.contracts import finite_number, is_sha256
from openpilot.tools.cyber_autotune.profiles import ProposalInput, inspect_proposal


# Tool resource ceiling, NOT a vehicle parameter or scientific search threshold.
MAX_PREVIEW_ENTRIES = 256


@dataclass(frozen=True)
class GridReview:
  values: tuple[float, ...]
  step: float
  max_proposals: int
  review_sha256: str


@dataclass(frozen=True)
class PreviewEntry:
  value: float
  changed: bool
  profile_sha256: str


@dataclass(frozen=True)
class GridPreview:
  status: str
  reasons: tuple[str, ...]
  entries: tuple[PreviewEntry, ...]
  preview_sha256: str | None
  candidate_generation_allowed: bool = field(default=False, init=False)
  offline_evaluable: bool = field(default=False, init=False)
  runtime_accepted: bool = field(default=False, init=False)


def preview_grid(template: ProposalInput, review: GridReview) -> GridPreview:
  """All reviewed values or none. Never filter failures into a smaller search.

The returned proposals are structurally representable, not evaluable. Baseline
is included and labeled unchanged. Only finite immutable tuples are consumed;
no iteration over arbitrary generators and no controller callbacks or file IO.
"""
  def blocked(*reasons):
    return GridPreview('BLOCKED', reasons, (), None)

  if type(template) is not ProposalInput:
    return blocked('INVALID_TEMPLATE')
  assessment = inspect_proposal(template)
  if not assessment.contracts_ready:
    return blocked(*assessment.reasons)
  if type(review) is not GridReview or type(review.review_sha256) is not str or not is_sha256(review.review_sha256):
    return blocked('INVALID_GRID_REVIEW')
  if type(review.max_proposals) is not int or not 0 < review.max_proposals <= MAX_PREVIEW_ENTRIES:
    return blocked('INVALID_GRID_BUDGET')
  if type(review.values) is not tuple or not review.values:
    return blocked('INVALID_GRID_VALUES')
  if len(review.values) > review.max_proposals:
    return blocked('GRID_BUDGET_EXCEEDED')
  if not finite_number(review.step) or review.step <= 0:
    return blocked('INVALID_GRID_STEP')
  if not all(finite_number(value) for value in review.values):
    return blocked('INVALID_GRID_VALUES')
  values = tuple(Fraction(str(value)) for value in review.values)
  if any(left >= right for left, right in zip(values, values[1:], strict=False)):
    return blocked('GRID_NOT_STRICTLY_ASCENDING')
  baseline, step = Fraction(str(template.baseline_value)), Fraction(str(review.step))
  if baseline not in values:
    return blocked('BASELINE_MISSING')
  if any(((value - baseline) / step).denominator != 1 for value in values):
    return blocked('OFF_GRID_VALUE')

  entries = []
  for original_value, canonical_value in zip(review.values, values, strict=True):
    result = inspect_proposal(replace(template, proposed_value=original_value))
    if not result.contracts_ready:
      return blocked(*result.reasons)
    entries.append(PreviewEntry(original_value, canonical_value != baseline, result.profile_sha256))
  payload = {
    'schema': 'cyber-autotune-grid-preview-v1', 'template': assessment.profile_sha256,
    'review': review.review_sha256, 'budget': review.max_proposals,
    'step': str(step), 'profiles': tuple(entry.profile_sha256 for entry in entries),
  }
  digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
  return GridPreview('STRUCTURAL_PREVIEW', ('EVIDENCE_VALIDATION_PENDING',), tuple(entries), digest)
