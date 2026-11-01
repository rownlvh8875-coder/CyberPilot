"""Explicit immutable synthetic carriers, never native messages or history proof."""

from dataclasses import dataclass

from cyberlateral_dev import LateralInput, LateralState, Limits


class MessageBoundaryError(ValueError):
    """Pure boundary rejection with stable code and no partial result."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class SyntheticActuatorsV1:
    torque: float


@dataclass(frozen=True, slots=True)
class SyntheticCarControlV1:
    actuators: SyntheticActuatorsV1
    latActive: bool


@dataclass(frozen=True, slots=True)
class SyntheticCarStateValuesV1:
    steeringTorque: float
    steeringAngleDeg: float


@dataclass(frozen=True, slots=True)
class SyntheticCarStateWrapperV1:
    out: SyntheticCarStateValuesV1


@dataclass(frozen=True, slots=True)
class SyntheticPreviousV1:
    snapshot_stage: str
    sequence_id: str
    previous_invocation_index: int | None
    source_previous_applied: int
    source_angle_counter: int
    model_state: LateralState


@dataclass(frozen=True, slots=True)
class SyntheticBoundaryFrameV1:
    schema_version: int
    scope: str
    profile_id: str
    source_set_id: str
    value_representation: str
    sequence_id: str
    invocation_index: int
    static_context_reference: str
    consumed_settings_origin: str
    cc: SyntheticCarControlV1
    cs: SyntheticCarStateWrapperV1
    consumed_limits: Limits
    previous: SyntheticPreviousV1


@dataclass(frozen=True, slots=True)
class PreparedLateralInputV1:
    contract_id: str
    source_set_id: str
    sequence_id: str
    sample: LateralInput
    state: LateralState
    custody_claim: str
    precision_claim: str
    time_semantics: str
