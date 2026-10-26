"""Pure, single-parameter proposal contracts. NOT a vehicle profile loader.

Hash bindings and asserted confidence are structural metadata, not proof of
review authority or physical validity. Even structurally valid proposals cannot
be evaluated or applied through this module. No wall clock, file IO or callbacks.
"""
from dataclasses import asdict, dataclass, field, fields
from fractions import Fraction
import hashlib
import json

from openpilot.tools.cyber_autotune.contracts import finite_number, is_sha256
from openpilot.tools.cyber_autotune.policy import lookup_policy, offline_proposal_permitted


@dataclass(frozen=True)
class ProposalBinding:
  fingerprint: str
  software_sha256: str
  parameter_revision: str
  baseline_profile_sha256: str
  previous_profile_sha256: str
  rollback_profile_sha256: str
  configuration_sha256: str
  evidence_sha256: str
  metric_sha256: str
  adapter_sha256: str


@dataclass(frozen=True)
class UpdateReview:
  minimum: float
  maximum: float
  max_delta: float
  minimum_samples: int
  minimum_confidence: float
  max_rate_per_s: float
  minimum_interval_s: float
  review_sha256: str


@dataclass(frozen=True)
class ProposalInput:
  binding: ProposalBinding
  name: str
  unit: str
  baseline_value: float
  proposed_value: float
  sample_count: int
  confidence: float
  elapsed_since_previous_s: float
  review: UpdateReview


@dataclass(frozen=True)
class ProfileAssessment:
  contracts_ready: bool
  reasons: tuple[str, ...]
  profile_sha256: str | None
  runtime_accepted: bool = field(default=False, init=False)
  offline_evaluable: bool = field(default=False, init=False)


def _identity(value) -> bool:
  return type(value) is str and bool(value) and value.strip() == value and value.isprintable()


def _binding_valid(binding) -> bool:
  return (type(binding) is ProposalBinding and _identity(binding.fingerprint) and _identity(binding.parameter_revision)
          and all(type(getattr(binding, item.name)) is str and is_sha256(getattr(binding, item.name))
                  for item in fields(binding) if item.name.endswith('_sha256')))


def _review_valid(review) -> bool:
  if type(review) is not UpdateReview or type(review.review_sha256) is not str or not is_sha256(review.review_sha256):
    return False
  if not all(finite_number(getattr(review, item.name)) for item in fields(review) if item.name != 'review_sha256'):
    return False
  return (_number(review.minimum) < _number(review.maximum) and review.max_delta >= 0
          and type(review.minimum_samples) is int and review.minimum_samples > 0
          and 0 < review.minimum_confidence <= 1 and review.max_rate_per_s > 0 and review.minimum_interval_s > 0)


def _number(value: int | float) -> Fraction:
  # Canonical shortest decimal semantics: 2 and 2.0 match; 2.4-2.3 is exactly .1.
  # Rational arithmetic avoids overflow/tolerance-based relaxation of hard bounds.
  return Fraction(str(value))


def _canonical(value):
  if isinstance(value, dict):
    return {key: _canonical(item) for key, item in value.items()}
  if type(value) in (int, float):
    number = _number(value)
    return f'{number.numerator}/{number.denominator}'
  return value


def inspect_proposal(proposal: ProposalInput) -> ProfileAssessment:
  """Inspect asserted contracts, with mandatory unverified-evidence residual.

Initial history is intentionally limited to previous == rollback == baseline.
No authenticated history store, reviewed real search space or confidence producer
exists here. Invalid shape is a result, never an implicit fallback/default value.
Elapsed time is supplied offline metadata, not an enforced runtime timer.
"""
  def blocked(*reasons):
    return ProfileAssessment(False, reasons, None)

  if type(proposal) is not ProposalInput:
    return blocked('INVALID_PROPOSAL')
  if not _binding_valid(proposal.binding):
    return blocked('INVALID_BINDING')
  binding = proposal.binding
  if not (binding.previous_profile_sha256 == binding.rollback_profile_sha256 == binding.baseline_profile_sha256):
    return blocked('INVALID_INITIAL_HISTORY')
  if not offline_proposal_permitted(proposal.name):
    return blocked('PARAMETER_NOT_PERMITTED')
  policy = lookup_policy(proposal.name)
  if type(proposal.unit) is not str or proposal.unit != policy.unit:
    return blocked('NONCANONICAL_UNIT')
  if not _review_valid(proposal.review):
    return blocked('INVALID_REVIEW')
  review = proposal.review
  numeric = (proposal.baseline_value, proposal.proposed_value, proposal.sample_count,
             proposal.confidence, proposal.elapsed_since_previous_s)
  if (not all(finite_number(value) for value in numeric) or type(proposal.sample_count) is not int or proposal.sample_count < 0
      or not 0 <= proposal.confidence <= 1 or proposal.elapsed_since_previous_s <= 0):
    return blocked('INVALID_NUMERIC_INPUT')
  if ((proposal.name == 'lat_accel_factor' and review.minimum <= 0)
      or (proposal.name == 'friction' and review.minimum < 0)):
    return blocked('INVALID_PARAMETER_DOMAIN')

  reasons = []
  baseline, proposed = _number(proposal.baseline_value), _number(proposal.proposed_value)
  minimum, maximum = _number(review.minimum), _number(review.maximum)
  delta = abs(proposed - baseline)
  if not minimum <= baseline <= maximum or not minimum <= proposed <= maximum:
    reasons.append('OUTSIDE_REVIEWED_RANGE')
  if delta > _number(review.max_delta):
    reasons.append('DELTA_LIMIT_EXCEEDED')
  if delta > _number(review.max_rate_per_s) * _number(proposal.elapsed_since_previous_s):
    reasons.append('RATE_LIMIT_EXCEEDED')
  if proposal.sample_count < review.minimum_samples:
    reasons.append('INSUFFICIENT_SAMPLES')
  if _number(proposal.confidence) < _number(review.minimum_confidence):
    reasons.append('INSUFFICIENT_CONFIDENCE')
  if _number(proposal.elapsed_since_previous_s) < _number(review.minimum_interval_s):
    reasons.append('UPDATE_TOO_SOON')
  if reasons:
    return blocked(*reasons)

  payload = {'schema': 'cyber-autotune-proposal-v1', 'role': 'proposal_only', 'proposal': _canonical(asdict(proposal))}
  digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()).hexdigest()
  return ProfileAssessment(True, ('EVIDENCE_VALIDATION_PENDING',), digest)
