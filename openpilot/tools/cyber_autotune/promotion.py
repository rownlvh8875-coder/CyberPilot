"""Pure offline promotion REHEARSAL, not evidence authentication or activation.

Receipts assert external results. Hashes bind them but cannot prove their truth.
No file IO, profile writer, live controller, vehicle transport or actual rollback.
"""
from dataclasses import asdict, dataclass, fields

from openpilot.tools.cyber_autotune.audit import REASON_CODE
from openpilot.tools.cyber_autotune.contracts import is_sha256
from openpilot.tools.cyber_autotune.native_protocol import canonical, digest


STAGES = ('SIMULATION_SCREEN', 'REPLAY', 'CALIBRATED_SIMULATION', 'SHADOW')
FAULTS = frozenset({'REGRESSION', 'UNEXPECTED_SATURATION', 'PARAMETER_CORRUPTION', 'CONTROLLER_EXCEPTION',
                   'CONFIDENCE_LOSS', 'INVALID_VEHICLE_STATE', 'ROLLBACK_UNAVAILABLE'})


@dataclass(frozen=True)
class PromotionBinding:
  fingerprint: str
  software_sha256: str
  configuration_sha256: str
  parameter_revision_sha256: str
  candidate_profile_sha256: str
  baseline_profile_sha256: str
  rollback_profile_sha256: str
  evaluator_sha256: str
  policy_sha256: str


@dataclass(frozen=True)
class GateReceipt:
  stage: str
  status: str
  artifact_sha256: str
  reasons: tuple[str, ...]
  binding: PromotionBinding
  scope: str = 'LATERAL_AND_LONGITUDINAL'


@dataclass(frozen=True)
class FaultObservation:
  code: str
  active_profile_sha256: str | None
  verified_rollback_sha256: str | None


@dataclass(frozen=True)
class Rehearsal:
  binding: PromotionBinding
  receipts: tuple[GateReceipt, ...]
  fault: FaultObservation | None


def _sha(value):
  return type(value) is str and is_sha256(value)


def _valid_binding(binding):
  if type(binding) is not PromotionBinding:
    return False
  name = binding.fingerprint
  return (type(name) is str and bool(name) and name == name.strip() and name.isprintable() and
          all(_sha(getattr(binding, item.name)) for item in fields(binding) if item.name.endswith('_sha256')) and
          binding.baseline_profile_sha256 == binding.rollback_profile_sha256 and
          binding.candidate_profile_sha256 != binding.baseline_profile_sha256)


def _valid_receipt(receipt):
  return (type(receipt) is GateReceipt and type(receipt.stage) is str and receipt.stage in STAGES and
          type(receipt.status) is str and receipt.status in {'PASS', 'FAIL', 'REVALIDATION_REQUIRED'} and
          _sha(receipt.artifact_sha256) and _valid_binding(receipt.binding) and
          type(receipt.scope) is str and receipt.scope == 'LATERAL_AND_LONGITUDINAL' and
          type(receipt.reasons) is tuple and bool(receipt.reasons) and
          all(type(reason) is str and REASON_CODE.fullmatch(reason) is not None for reason in receipt.reasons) and
          len(set(receipt.reasons)) == len(receipt.reasons))


def _valid_fault(fault):
  return (type(fault) is FaultObservation and type(fault.code) is str and fault.code in FAULTS and
          (fault.active_profile_sha256 is None or _sha(fault.active_profile_sha256)) and
          (fault.verified_rollback_sha256 is None or _sha(fault.verified_rollback_sha256)))


def _validate(state):
  if (type(state) is not Rehearsal or not _valid_binding(state.binding) or type(state.receipts) is not tuple or
      len(state.receipts) > len(STAGES) or (state.fault is not None and not _valid_fault(state.fault))):
    raise ValueError('INVALID_REHEARSAL')
  seen = set()
  for index, receipt in enumerate(state.receipts):
    if (not _valid_receipt(receipt) or receipt.stage != STAGES[index] or receipt.binding != state.binding or
        receipt.artifact_sha256 in seen or (index and state.receipts[index - 1].status != 'PASS')):
      raise ValueError('INVALID_RECEIPT_HISTORY')
    seen.add(receipt.artifact_sha256)


def new_rehearsal(binding: PromotionBinding) -> Rehearsal:
  state = Rehearsal(binding, (), None)
  _validate(state)
  return state


def advance(state: Rehearsal, receipt: GateReceipt) -> Rehearsal:
  _validate(state)
  if state.fault is not None:
    raise ValueError('FAULT_IS_TERMINAL')
  result = Rehearsal(state.binding, (*state.receipts, receipt), None)
  _validate(result)
  return result


def apply_fault(state: Rehearsal, fault: FaultObservation) -> Rehearsal:
  _validate(state)
  if state.fault is not None or not _valid_fault(fault):
    raise ValueError('INVALID_OR_REPEATED_FAULT')
  # Preserve any prior FAIL/REVALIDATION receipt; faults never rewrite that history.
  return Rehearsal(state.binding, state.receipts, fault)


def assess(state: Rehearsal) -> dict:
  """Recompute documentary consistency and advice, never certify a vehicle profile."""
  _validate(state)
  status = 'IN_PROGRESS'
  action = 'CONTINUE_DOCUMENTARY_VALIDATION'
  rollback = None
  reasons = tuple(reason for receipt in state.receipts for reason in receipt.reasons)
  if state.receipts and state.receipts[-1].status != 'PASS':
    status = 'FAILED' if state.receipts[-1].status == 'FAIL' else 'REVALIDATION_REQUIRED'
    action = 'QUARANTINE_CANDIDATE'
  elif len(state.receipts) == len(STAGES):
    status = 'AWAITING_SEPARATE_VEHICLE_APPROVAL'
    action = 'REQUIRE_AUTHENTICATED_EVIDENCE_AND_RUNTIME_REVIEW'
  if state.fault is not None:
    status = 'FAULTED'
    fault = state.fault
    reasons = (*reasons, fault.code)
    if fault.active_profile_sha256 == state.binding.baseline_profile_sha256:
      action = 'QUARANTINE_CANDIDATE'
    elif (fault.active_profile_sha256 == state.binding.candidate_profile_sha256 and
          fault.verified_rollback_sha256 == state.binding.rollback_profile_sha256 and fault.code != 'ROLLBACK_UNAVAILABLE'):
      action = 'REQUEST_ROLLBACK'
      rollback = state.binding.rollback_profile_sha256
    else:
      action = 'STOP_AND_REQUIRE_OPERATOR'
  return {'schema': 'cyber-promotion-rehearsal-v1', 'scope': 'OFFLINE_REHEARSAL_ONLY', 'contract_status': status,
          'recorded_stages': [receipt.stage for receipt in state.receipts], 'reasons': list(dict.fromkeys(reasons)),
          'gate_results': [{'stage': receipt.stage, 'status': receipt.status, 'artifact_sha256': receipt.artifact_sha256,
                            'reasons': list(receipt.reasons)} for receipt in state.receipts],
          'action': action, 'rollback_target_sha256': rollback,
          'state_sha256': digest(canonical({'schema': 'cyber-promotion-rehearsal-v1', 'state': asdict(state)})),
          'missing_authority': 'QUALIFIED_EVIDENCE_AND_RUNTIME_INTEGRATION', 'vehicle_readiness': 'NOT_READY',
          'runtime_accepted': False, 'promotable': False, 'rollback_executed': False}
