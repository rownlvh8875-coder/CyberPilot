"""Offline, read-only parameter registry. This version admits NO proposals.

No dependency on Params/CP/native/CAN and no application/writeback path.
None bounds mean unreviewed and forbidden, never unlimited. Vehicle-dependent
stock defaults must be read from a qualified snapshot, not invented here.
"""
import math
from types import MappingProxyType

from openpilot.selfdrive.controls.lib.cyber_long.types import (
  ParameterBinding, ParameterMetadata, ParameterProposal, ProposalAssessment,
)

_UPSTREAM = 'https://github.com/commaai/openpilot/tree/c8fb906815530460ed156f14e09e1f312bb0f851/'
_OPENDBC = 'https://github.com/commaai/opendbc/tree/4134c0d1f5e8f695e35ea5fedbe88f6d0c3afb76/'

PARAMETER_METADATA = MappingProxyType({
  item.name: item for item in (
    ParameterMetadata(
      name='vehicle.longitudinal_actuator_delay', unit='s',
      source=_UPSTREAM + 'openpilot/selfdrive/controls/lib/longitudinal_planner.py:CP.longitudinalActuatorDelay',
      default=None, vehicle_specific=True, category=('vehicle_physics', 'offline_research_only'),
    ),
    ParameterMetadata(
      name='controller.acceleration_integral_gain', unit='1/s',
      source=_UPSTREAM + 'openpilot/selfdrive/controls/lib/longcontrol.py:CP.longitudinalTuning.kiV',
      default=None, vehicle_specific=True, category=('controller', 'offline_research_only'),
    ),
    ParameterMetadata(
      name='user.personality', unit='enum', source=_UPSTREAM + 'openpilot/cereal/log.capnp:LongitudinalPersonality',
      default=None, vehicle_specific=False, category=('user_preference', 'autotune_forbidden'),
    ),
    ParameterMetadata(
      name='safety.accel_min', unit='m/s^2', source=_OPENDBC + 'opendbc/car/interfaces.py:ACCEL_MIN',
      default=None, vehicle_specific=False, category=('safety_limit', 'autotune_forbidden'), safety_related=True,
    ),
    ParameterMetadata(
      name='safety.accel_max', unit='m/s^2', source=_OPENDBC + 'opendbc/car/interfaces.py:ACCEL_MAX',
      default=None, vehicle_specific=False, category=('safety_limit', 'autotune_forbidden'), safety_related=True,
    ),
  )
})


def _finite_number(value) -> bool:
  # bool is not a numeric tuning value; format errors must fail closed too.
  if type(value) not in (int, float):
    return False
  try:
    return math.isfinite(value)
  except OverflowError:
    return False


def assess_tuning_proposal(proposal: ParameterProposal, expected_binding: ParameterBinding) -> ProposalAssessment:
  """Classify rejection only. Caller-supplied metadata cannot grant permission.

  Binding/evidence labels are necessary format checks, NOT provenance proof.
  Even fully labeled proposals are denied pending separately reviewed bounds,
  confidence, validation evidence and a future approved application design.
  """
  metadata = PARAMETER_METADATA.get(proposal.name) if isinstance(proposal.name, str) else None
  if metadata is None:
    reason = 'unknown_parameter'
  elif metadata.safety_related or 'autotune_forbidden' in metadata.category:
    reason = 'forbidden_category'
  elif not _finite_number(proposal.value):
    reason = 'invalid_value'
  elif proposal.unit != metadata.unit:
    reason = 'unit_mismatch'
  elif not _finite_number(proposal.confidence) or not 0. <= proposal.confidence <= 1.:
    reason = 'invalid_confidence'
  elif (not isinstance(proposal.binding, ParameterBinding) or not isinstance(expected_binding, ParameterBinding) or
        not proposal.binding.complete or not expected_binding.complete):
    reason = 'incomplete_binding'
  elif proposal.binding != expected_binding:
    reason = 'binding_mismatch'
  elif not isinstance(proposal.evidence_id, str) or not proposal.evidence_id.strip():
    reason = 'missing_evidence'
  elif any(value is None for value in (metadata.min, metadata.max, metadata.rate_of_change_limit, metadata.confidence_requirement)):
    reason = 'unreviewed_bounds'
  else:
    reason = 'tuning_disabled'
  return ProposalAssessment(accepted=False, reason=reason)
