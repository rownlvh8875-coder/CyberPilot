"""Immutable DEV records. Not native messages, F61 arguments or vehicle inputs."""

from dataclasses import dataclass

from cyberlateral_dev import LateralOutput, LateralState, Limits


class DevBridgeError(ValueError):
    """Closed synthetic bridge rejection, with no partial result."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class DevSourceSnapshotV1:
    schema_version: int
    scope: str
    value_representation: str
    profile_id: str
    source_set_id: str
    fixture_id: str
    sequence_id: str
    offset: int
    model_index: int
    requested_torque: float
    driver_torque_native: float
    steering_angle_deg: float
    lat_active: bool
    limits: Limits


@dataclass(frozen=True, slots=True)
class DevBridgeSessionV1:
    schema_version: int
    scope: str
    profile_id: str
    source_set_id: str
    fixture_id: str
    sequence_id: str
    next_offset: int
    model_state: LateralState


@dataclass(frozen=True, slots=True)
class DevBridgeResultV1:
    contract_id: str
    fixture_id: str
    sequence_id: str
    consumed_offset: int
    diagnostic: LateralOutput
    next_session: DevBridgeSessionV1
