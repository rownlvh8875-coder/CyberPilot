"""Standalone tests for source-side immutable diagnostic capture."""

import dataclasses
import unittest

from openpilot.cereal import log
from openpilot.selfdrive.controls.lib.cyber_lateral.diagnostic_capture import (
  capture_native_inputs,
)
from openpilot.selfdrive.controls.lib.cyber_lateral.types import LateralBinding


def fixture_capture(**changes):
  model = log.ModelDataV2.new_message(frameId=101, frameIdExtra=201, timestampEof=300)
  model.position.x = [0.0, 10.0, 20.0]
  model.position.y = [0.1, 0.1, 0.1]
  values = {
    "model": model,
    "controller_cycle_id": 1,
    "message_times_ns": (400, 400, 390, 390),
    "current_curvature_1pm": 0.002,
    "final_desired_curvature_1pm": 0.001,
    "curvature_limited": False,
    "native_result": (0.2, 0.3),
    "actuator_bytes": b"synthetic",
    "binding": LateralBinding(vehicle="SYNTHETIC", controller_type="pid"),
    "lat_active": True,
    "driver_override": False,
    "input_valid": True,
  }
  values.update(changes)
  return capture_native_inputs(**values)


class CaptureReviewTests(unittest.TestCase):
  def test_frozen_scalar_record(self):
    value = fixture_capture()
    with self.assertRaises(dataclasses.FrozenInstanceError):
      value.driver_override = True

  def test_typed_identity_and_units(self):
    value = fixture_capture()
    self.assertEqual((value.model_frame_id, value.model_frame_id_extra), (101, 201))
    self.assertEqual(value.current_curvature_1pm - value.final_desired_curvature_1pm, 0.001)

  def test_nonfinite_curvature_rejected(self):
    with self.assertRaises(ValueError):
      fixture_capture(current_curvature_1pm=float("nan"))

  def test_invalid_cycle_rejected(self):
    with self.assertRaises(ValueError):
      fixture_capture(controller_cycle_id=-1)

  def test_reset_and_measurement_not_invented(self):
    value = fixture_capture()
    self.assertEqual(value.reset_identity, "UNAVAILABLE")
    self.assertEqual(value.measurement_qualification, "UNQUALIFIED")
    self.assertEqual(value.source_binding[1:3], (None, None))

  def test_mutable_native_result_copied(self):
    result = [0.2, 0.3]
    value = fixture_capture(native_result=result)
    result[0] = 0.9
    self.assertEqual(value.native_result, (0.2, 0.3))

  def test_wrong_schema_rejected(self):
    with self.assertRaises(ValueError):
      fixture_capture(model=log.VehicleParameters.new_message())

  def test_mutable_message_time_copied(self):
    times = [400, 400, 390, 390]
    value = fixture_capture(message_times_ns=times)
    times[0] = 0
    self.assertEqual(value.message_times_ns[0], 400)
