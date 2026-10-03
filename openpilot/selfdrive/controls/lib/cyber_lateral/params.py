"""Read-only Cyber Lateral parameter metadata and fail-closed admission.

There is deliberately no Params handle, controller callback or application
function in this module. Every proposal is rejected in this version.
"""
from dataclasses import dataclass
import math
from types import MappingProxyType

from openpilot.selfdrive.controls.lib.cyber_lateral.types import LateralBinding


OPENPILOT_COMMIT = 'c8fb906815530460ed156f14e09e1f312bb0f851'
SUNNYPILOT_COMMIT = 'a5f44653d7f43ad57fef2f546f3916ec4cbf3c56'
CARROTPILOT_COMMIT = 'c57d0ff11f766b7fd70e9a9eaec1247b623ffbea'


@dataclass(frozen=True)
class LateralParameterMetadata:
  name: str
  unit: str
  source_commit: str
  source_symbol: str
  default: float | None
  vehicle_specific: bool
  owner: str
  parameter_class: str
  stage: str
  controller_binding: str | None
  online_learn: bool
  offline_tune: bool
  minimum: float | None
  maximum: float | None
  rate_of_change_limit: float | None
  confidence_requirement: float
  valid_domain: str
  safety_related: bool
  read_only: bool = True


@dataclass(frozen=True)
class LateralParameterProposal:
  name: str
  value: float
  unit: str
  binding: LateralBinding
  evidence_identity: str
  confidence: float


@dataclass(frozen=True)
class ProposalAssessment:
  accepted: bool
  reason: str


def _metadata(name, unit, symbol, default, *, vehicle_specific=True,
              owner='vehicle_parameter', parameter_class='vehicle_physical', stage='controller_input',
              controller_binding=None, online=False, offline=False, minimum=None, maximum=None,
              rate=None, confidence=0.9, domain='qualified_vehicle_domain', safety=False,
              source=OPENPILOT_COMMIT):
  return LateralParameterMetadata(
    name, unit, source, symbol, default, vehicle_specific, owner, parameter_class,
    stage, controller_binding, online, offline, minimum, maximum, rate,
    confidence, domain, safety,
  )


_REGISTRY = {
  'steer_ratio': _metadata(
    'steer_ratio', 'ratio', 'CarParams.steerRatio', None, online=True, offline=True,
  ),
  'stiffness_factor': _metadata(
    'stiffness_factor', 'ratio', 'VehicleParameters.stiffnessFactor', 1.0, online=True, offline=True,
  ),
  'angle_offset_deg': _metadata(
    'angle_offset_deg', 'deg', 'VehicleParameters.angleOffsetDeg', 0.0, online=True, offline=False,
  ),
  'roll_rad': _metadata(
    'roll_rad', 'rad', 'VehicleParameters.roll', 0.0, online=True, offline=False,
  ),
  'lat_accel_factor': _metadata(
    'lat_accel_factor', 'm/s^2/Nm', 'TorqueTuning.latAccelFactor', None,
    controller_binding='torque', online=True, offline=True, minimum=0.1, maximum=10.0,
  ),
  'lat_accel_offset': _metadata(
    'lat_accel_offset', 'm/s^2', 'TorqueTuning.latAccelOffset', 0.0,
    controller_binding='torque', online=True, offline=True, minimum=-2.0, maximum=2.0,
  ),
  'friction': _metadata(
    'friction', 'Nm', 'TorqueTuning.friction', 0.0,
    controller_binding='torque', online=True, offline=True, minimum=0.0, maximum=1.0,
  ),
  'lateral_delay_s': _metadata(
    'lateral_delay_s', 's', 'LateralDelay.lateralDelay', None,
    stage='timing_alignment', online=True, offline=True, minimum=0.0, maximum=1.0,
  ),
  'torque_kp': _metadata(
    'torque_kp', 'ratio', 'latcontrol_torque.KP', 0.8,
    owner='controller', parameter_class='controller_gain', controller_binding='torque',
    offline=True, minimum=0.0, maximum=5.0,
  ),
  'torque_ki': _metadata(
    'torque_ki', '1/s', 'latcontrol_torque.KI', 0.15,
    owner='controller', parameter_class='controller_gain', controller_binding='torque',
    offline=True, minimum=0.0, maximum=2.0,
  ),
  'jerk_gain_s': _metadata(
    'jerk_gain_s', 's', 'latcontrol_torque.JERK_GAIN', 0.3,
    owner='controller', parameter_class='controller_compensation', controller_binding='torque',
    offline=True, minimum=0.0, maximum=1.0,
  ),
  'jerk_lookahead_s': _metadata(
    'jerk_lookahead_s', 's', 'latcontrol_torque.JERK_LOOKAHEAD_SECONDS', 0.19,
    owner='controller', parameter_class='controller_timing', controller_binding='torque',
    offline=True, minimum=0.0, maximum=1.0,
  ),
  'jerk_filter_cutoff_hz': _metadata(
    'jerk_filter_cutoff_hz', 'Hz', 'latcontrol_torque.LP_FILTER_CUTOFF_HZ', 1.2,
    owner='controller', parameter_class='controller_filter', controller_binding='torque',
    offline=True, minimum=0.1, maximum=10.0,
  ),
  'sunny_future_jerk_persistence': _metadata(
    'sunny_future_jerk_persistence', 'm/s^3', 'latcontrol_torque_jerk_aware.update_calculations', None,
    owner='observer', parameter_class='research_observation', stage='offline_observer',
    vehicle_specific=False, online=False, offline=True, domain='unreviewed', source=SUNNYPILOT_COMMIT,
  ),
  'carrot_path_quality_bias': _metadata(
    'carrot_path_quality_bias', 'm', 'lateral_planner.lane/path quality concept', None,
    owner='observer', parameter_class='research_observation', stage='offline_observer',
    vehicle_specific=False, online=False, offline=False, domain='diagnostic_only', source=CARROTPILOT_COMMIT,
  ),
}

for _name, _unit, _parameter_class in (
  ('steering_limit', 'ratio', 'safety_limit'),
  ('curvature_limit', '1/m', 'safety_limit'),
  ('lateral_jerk_limit', 'm/s^3', 'safety_limit'),
  ('torque_limit', 'Nm', 'safety_limit'),
  ('can_driver_allowance', 'raw', 'safety_limit'),
  ('driver_override_gate', 'bool', 'engagement_gate'),
  ('engagement_gate', 'bool', 'engagement_gate'),
  ('user_lane_offset', 'm', 'user_preference'),
):
  _REGISTRY[_name] = _metadata(
    _name, _unit, 'forbidden_by_cyber_lateral_design', None,
    owner='safety_or_user', parameter_class=_parameter_class, stage='authority_gate',
    vehicle_specific=False, online=False, offline=False, domain='forbidden',
    safety=_parameter_class != 'user_preference',
  )

LATERAL_PARAMETER_REGISTRY = MappingProxyType(_REGISTRY)


def assess_lateral_proposal(proposal: LateralParameterProposal,
                            expected_binding: LateralBinding) -> ProposalAssessment:
  if not isinstance(proposal, LateralParameterProposal):
    return ProposalAssessment(False, 'invalid_proposal')
  if not isinstance(proposal.name, str):
    return ProposalAssessment(False, 'invalid_proposal')
  metadata = LATERAL_PARAMETER_REGISTRY.get(proposal.name)
  if metadata is None:
    return ProposalAssessment(False, 'unknown_parameter')
  if metadata.safety_related or metadata.parameter_class in {'user_preference', 'engagement_gate'}:
    return ProposalAssessment(False, 'forbidden_parameter')
  if type(proposal.value) not in (int, float) or not math.isfinite(proposal.value):
    return ProposalAssessment(False, 'invalid_number')
  if proposal.unit != metadata.unit:
    return ProposalAssessment(False, 'unit_mismatch')
  if (type(proposal.confidence) not in (int, float) or not math.isfinite(proposal.confidence) or
      not 0. <= proposal.confidence <= 1.):
    return ProposalAssessment(False, 'invalid_confidence')
  if proposal.confidence < metadata.confidence_requirement:
    return ProposalAssessment(False, 'insufficient_confidence')
  if (not isinstance(expected_binding, LateralBinding) or not expected_binding.complete or
      not isinstance(proposal.binding, LateralBinding) or not proposal.binding.complete):
    return ProposalAssessment(False, 'incomplete_binding')
  if proposal.binding != expected_binding:
    return ProposalAssessment(False, 'binding_mismatch')
  if (metadata.controller_binding is not None and
      proposal.binding.controller_type != metadata.controller_binding):
    return ProposalAssessment(False, 'parameter_controller_mismatch')
  if not isinstance(proposal.evidence_identity, str) or not proposal.evidence_identity.strip():
    return ProposalAssessment(False, 'missing_evidence')
  if metadata.minimum is None or metadata.maximum is None:
    return ProposalAssessment(False, 'unreviewed_bounds')
  if not metadata.minimum <= proposal.value <= metadata.maximum:
    return ProposalAssessment(False, 'out_of_bounds')
  return ProposalAssessment(False, 'tuning_disabled')
