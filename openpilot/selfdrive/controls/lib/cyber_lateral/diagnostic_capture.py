"""Read-only immutable diagnostic capture; never produce control commands.

Frame labels are source fields, not evidence of camera authenticity or freshness.
The cycle counter is local software correlation, not an acquisition timestamp.
"""

import math
from dataclasses import dataclass

from openpilot.cereal import log
from openpilot.selfdrive.controls.lib.cyber_lateral.types import LateralBinding

CAPTURE_PHASE = "POST_NATIVE_FINAL_ACTUATORS_PRE_PUBLICATION"


@dataclass(frozen=True, slots=True)
class NativeDiagnosticCapture:
  controller_cycle_id: int
  model_frame_id: int
  model_frame_id_extra: int
  model_timestamp_eof_ns: int
  message_times_ns: tuple[int, int, int, int]
  model_message: bytes
  current_curvature_1pm: float
  final_desired_curvature_1pm: float
  curvature_limited: bool
  native_result: tuple[float, float]
  actuator_bytes: bytes
  source_binding: tuple[str | None, str | None, str | None, str | None, int]
  lat_active: bool
  driver_override: bool
  input_valid: bool
  capture_phase: str = CAPTURE_PHASE
  reset_identity: str = "UNAVAILABLE"
  calibration_status: str = "UNAVAILABLE"
  freshness_status: str = "UNVERIFIED"
  measurement_qualification: str = "UNQUALIFIED"
  source_contract: str = "F18_TYPED_CAPTURE_PROPOSAL_V1"
  diagnostic_only: bool = True


def capture_native_inputs(
  *,
  model,
  controller_cycle_id,
  message_times_ns,
  current_curvature_1pm,
  final_desired_curvature_1pm,
  curvature_limited,
  native_result,
  actuator_bytes,
  binding,
  lat_active,
  driver_override,
  input_valid,
):
  """Copy one typed ModelDataV2 and scalar values without retaining Native objects."""
  if model.schema.node.id != log.ModelDataV2.schema.node.id:
    raise ValueError("TYPED_MODEL_SCHEMA_REQUIRED")
  if type(controller_cycle_id) is not int or controller_cycle_id < 1:
    raise ValueError("LOCAL_CYCLE_ID_REQUIRED")
  if len(message_times_ns) != 4 or any(type(v) is not int or v < 0 for v in message_times_ns):
    raise ValueError("MESSAGE_TIMES_REQUIRED")
  values = (current_curvature_1pm, final_desired_curvature_1pm, *native_result)
  if len(native_result) != 2 or any(type(v) not in (int, float) or not math.isfinite(v) for v in values):
    raise ValueError("FINITE_SOURCE_VALUES_REQUIRED")
  if not isinstance(binding, LateralBinding) or type(actuator_bytes) is not bytes:
    raise ValueError("IMMUTABLE_SOURCE_VALUES_REQUIRED")
  identities = (
    binding.vehicle,
    binding.firmware,
    binding.model,
    binding.controller_type,
  )
  if any(v is not None and type(v) is not str for v in identities):
    raise ValueError("SCALAR_BINDING_REQUIRED")
  if type(binding.configuration_epoch) is not int:
    raise ValueError("CONFIGURATION_EPOCH_REQUIRED")
  flags = (curvature_limited, lat_active, driver_override, input_valid)
  if any(type(v) is not bool for v in flags):
    raise ValueError("BOOLEAN_SOURCE_VALUES_REQUIRED")
  # A fresh builder makes an owned typed byte value; no mutable reader survives.
  reader = model.as_reader() if hasattr(model, "as_reader") else model
  message = reader.as_builder().to_bytes()
  with log.ModelDataV2.from_bytes(message) as decoded:
    frame_id = int(decoded.frameId)
    frame_extra = int(decoded.frameIdExtra)
    eof = int(decoded.timestampEof)
  return NativeDiagnosticCapture(
    controller_cycle_id,
    frame_id,
    frame_extra,
    eof,
    tuple(message_times_ns),
    message,
    float(current_curvature_1pm),
    float(final_desired_curvature_1pm),
    curvature_limited,
    tuple(float(v) for v in native_result),
    bytes(actuator_bytes),
    (*identities, binding.configuration_epoch),
    lat_active,
    driver_override,
    input_valid,
  )
