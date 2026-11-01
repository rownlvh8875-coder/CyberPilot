"""Required immutable data only; no semantic mapping or validation algorithm."""

from dataclasses import dataclass

from cyberlateral_dev import LateralInput, LateralState

from .owned_message_boundary import Stamp


@dataclass(frozen=True, slots=True)
class ScalarReadback:
    stamp: Stamp
    cc_sha256: str
    cs_sha256: str
    representation: str
    request: float
    driver: float
    angle_deg: float
    lat_active: bool


@dataclass(frozen=True, slots=True)
class PreparedSemanticInput:
    contract_id: str
    stamp: Stamp
    sample: LateralInput
    state: LateralState
    custody_claim: str
    precision_claim: str
    time_semantics: str
