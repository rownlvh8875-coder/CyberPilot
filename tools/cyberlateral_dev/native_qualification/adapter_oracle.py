"""Expected conversion from explicit scalars, never imports the R28 adapter."""

from integration_tools.owned_message_boundary import OwnedFrame
from integration_tools.semantic_oracle import oracle_prepare
from integration_tools.semantic_types import ScalarReadback


def expected(frame: OwnedFrame, request: float, driver: float, angle_deg: float, lat_active: bool):
    return oracle_prepare(frame, ScalarReadback(frame.stamp, frame.cc.payload_sha256, frame.cs.payload_sha256,
                                               'NATIVE_FLOAT32_DECLARATION', request, driver, angle_deg, lat_active))
