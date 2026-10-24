import inspect
import unittest
from types import SimpleNamespace

from openpilot.cereal import log
from openpilot.common.realtime import DT_CTRL
from opendbc.car.car_helpers import interfaces
from opendbc.car.honda.values import CAR as HONDA
from opendbc.car.nissan.values import CAR as NISSAN
from opendbc.car.structs import car
from opendbc.car.toyota.values import CAR as TOYOTA
from opendbc.car.vehicle_model import VehicleModel
from opendbc.car.volkswagen.values import CAR as VOLKSWAGEN

from openpilot.selfdrive.controls.controlsd import Controls
from openpilot.selfdrive.controls.lib.cyber_lateral import (
  CyberLateralConfig, CyberLateralCoordinator, CyberLateralMode, LateralBinding,
  LateralContext, NativeLateralResult,
)
from openpilot.selfdrive.controls.lib.latcontrol_angle import LatControlAngle
from openpilot.selfdrive.controls.lib.latcontrol_curvature import LatControlCurvature
from openpilot.selfdrive.controls.lib.latcontrol_pid import LatControlPID
from openpilot.selfdrive.controls.lib.latcontrol_torque import LatControlTorque
from openpilot.selfdrive.modeld.constants import ModelConstants


CONTROLLERS = (
  ('pid', HONDA.HONDA_CIVIC, LatControlPID),
  ('torque', TOYOTA.TOYOTA_RAV4, LatControlTorque),
  ('angle', NISSAN.NISSAN_LEAF, LatControlAngle),
  ('curvature', VOLKSWAGEN.VOLKSWAGEN_ID4_MK1, LatControlCurvature),
)

LANE_STATIONS = tuple(float(value) for value in ModelConstants.X_IDXS)
MODEL_PATH_STATIONS = tuple(value * 0.97 for value in LANE_STATIONS)
MODEL_PATH_Y = tuple(value * 0.005 for value in MODEL_PATH_STATIONS)

SEQUENCE = (
  # active, speed, curvature, steering pressed, safety limited, curvature limited
  (False, 0.0, 0.0, False, False, False),
  (True, 3.0, 0.004, False, False, False),
  (True, 30.0, 0.012, False, False, False),
  (True, 30.0, -0.011, False, False, False),
  (True, 20.0, 0.008, True, False, False),
  (True, 20.0, 0.8, False, True, False),
  (True, 20.0, -0.8, False, False, True),
  (True, 20.0, 0.006, False, False, False),
)


def build_controller(car_name, controller_type):
  CarInterface = interfaces[car_name]
  CP = CarInterface.get_non_essential_params(car_name)
  CI = CarInterface(CP)
  return CP, VehicleModel(CP), controller_type(CP.as_reader(), CI, DT_CTRL)


def controller_state(controller):
  state = [float(controller.sat_time)]
  pid = getattr(controller, 'pid', None)
  if pid is not None:
    state.extend(float(getattr(pid, name)) for name in ('p', 'i', 'd', 'f', 'control', 'speed'))
  if hasattr(controller, 'lat_accel_request_buffer'):
    state.extend(float(value) for value in controller.lat_accel_request_buffer)
    state.append(float(controller.jerk_filter.x))
  return tuple(state)


def make_context(result, binding, controller_kind, timestamp):
  return LateralContext(
    model_mono_time_ns=timestamp,
    car_state_mono_time_ns=timestamp,
    vehicle_parameters_mono_time_ns=timestamp,
    lateral_delay_mono_time_ns=timestamp,
    input_valid=True,
    lat_active=True,
    steering_pressed=False,
    steer_limited_by_safety=False,
    curvature_limited=False,
    v_ego_mps=20.0,
    desired_curvature_1pm=0.006,
    current_curvature_1pm=0.005,
    roll_rad=0.0,
    lateral_delay_s=0.2,
    native_result=NativeLateralResult(float(result[0]), float(result[1]), controller_kind),
    binding=binding,
  )


class TestCyberLateralNativeParity(unittest.TestCase):
  def test_real_native_controllers_are_exact_in_both_modes(self):
    for controller_kind, car_name, controller_type in CONTROLLERS:
      for mode in (CyberLateralMode.DISABLED, CyberLateralMode.OBSERVE_ONLY):
        with self.subTest(controller=controller_kind, mode=mode):
          direct_cp, direct_vm, direct = build_controller(car_name, controller_type)
          wrapped_cp, wrapped_vm, wrapped = build_controller(car_name, controller_type)
          self.assertEqual(direct_cp.to_bytes(), wrapped_cp.to_bytes())

          config = CyberLateralConfig(mode=mode)
          binding = LateralBinding(str(car_name), 'test-fw', 'test-model', controller_kind, 0)
          coordinator = CyberLateralCoordinator(config, binding)
          direct_calls = 0
          wrapped_calls = 0

          for index, step in enumerate(SEQUENCE, start=1):
            active, speed, curvature, steering_pressed, safety_limited, curvature_limited = step
            direct_cs = car.CarState.new_message()
            wrapped_cs = car.CarState.new_message()
            for state in (direct_cs, wrapped_cs):
              state.vEgo = speed
              state.steeringAngleDeg = 1.25
              state.steeringRateDeg = -0.2
              state.steeringPressed = steering_pressed

            direct_params = log.VehicleParameters.new_message()
            wrapped_params = log.VehicleParameters.new_message()
            direct_params.steerRatio = direct_cp.steerRatio
            wrapped_params.steerRatio = wrapped_cp.steerRatio
            if not active:
              direct.reset()
              wrapped.reset()

            direct_calls += 1
            direct_result = direct.update(
              active, direct_cs, direct_vm, direct_params, safety_limited,
              curvature, curvature_limited, 0.2,
            )

            def native_update(controller=wrapped, is_active=active, state=wrapped_cs,
                              vehicle_model=wrapped_vm, vehicle_params=wrapped_params,
                              limited_by_safety=safety_limited, desired_curvature=curvature,
                              is_curvature_limited=curvature_limited):
              nonlocal wrapped_calls
              wrapped_calls += 1
              return controller.update(
                is_active, state, vehicle_model, vehicle_params, limited_by_safety,
                desired_curvature, is_curvature_limited, 0.2,
              )

            wrapped_result = coordinator.run_native(
              native_update,
              lambda result, timestamp=index, current_binding=binding, kind=controller_kind: make_context(
                result, current_binding, kind, timestamp,
              ),
            )
            self.assertEqual(direct_result[0], wrapped_result[0])
            self.assertEqual(direct_result[1], wrapped_result[1])
            self.assertEqual(direct_result[2].to_bytes(), wrapped_result[2].to_bytes())
            self.assertEqual(controller_state(direct), controller_state(wrapped))
            self.assertEqual(direct_calls, wrapped_calls)

          self.assertEqual(wrapped_calls, len(SEQUENCE))


class TestControlsCyberLateralSeam(unittest.TestCase):
  def test_constructor_exposes_backward_compatible_config_injection(self):
    parameter = inspect.signature(Controls.__init__).parameters['cyber_lateral_config']
    self.assertEqual(parameter.kind, inspect.Parameter.KEYWORD_ONLY)
    self.assertIsNone(parameter.default)

  def test_extracted_seam_invokes_native_once_and_preserves_tuple_identity(self):
    native_result = (0.25, -1.0, object())

    class CountingController:
      def __init__(self):
        self.calls = 0

      def update(self, *_args):
        self.calls += 1
        return native_result

    native = CountingController()
    owner = SimpleNamespace(
      LaC=native,
      VM=object(),
      desired_curvature=0.01,
      steer_limited_by_safety=False,
      cyber_lateral=CyberLateralCoordinator(CyberLateralConfig(), LateralBinding()),
    )
    result = Controls._update_lateral_control(
      owner, SimpleNamespace(latActive=True), object(), object(), False, 0.2,
    )

    self.assertIs(result, native_result)
    self.assertEqual(native.calls, 1)

  def test_observe_only_context_uses_current_checked_controlsd_inputs(self):
    native_result = (0.25, -1.0, object())

    class CountingController:
      def __init__(self):
        self.calls = 0

      def update(self, *_args):
        self.calls += 1
        return native_result

    class FakeSubMaster:
      logMonoTime = {
        'modelV2': 101,
        'carState': 102,
        'vehicleParameters': 103,
        'lateralDelay': 104,
      }

      model_reads = 0
      updated = {'modelV2': True}
      model = SimpleNamespace(
        acceleration=SimpleNamespace(t=(0., 1., 2.), y=(0., 1., 2.)),
        position=SimpleNamespace(x=MODEL_PATH_STATIONS, y=MODEL_PATH_Y),
        laneLines=(
          SimpleNamespace(x=LANE_STATIONS, y=(3.,) * len(LANE_STATIONS)),
          SimpleNamespace(x=LANE_STATIONS, y=(1.8,) * len(LANE_STATIONS)),
          SimpleNamespace(x=LANE_STATIONS, y=(-1.8,) * len(LANE_STATIONS)),
          SimpleNamespace(x=LANE_STATIONS, y=(-3.,) * len(LANE_STATIONS)),
        ),
        laneLineProbs=(0.1, 0.9, 0.8, 0.1),
        laneLineStds=(1., 0.1, 0.2, 1.),
        roadEdges=(
          SimpleNamespace(x=LANE_STATIONS, y=(3.,) * len(LANE_STATIONS)),
          SimpleNamespace(x=LANE_STATIONS, y=(-3.,) * len(LANE_STATIONS)),
        ),
        meta=SimpleNamespace(laneChangeState=log.LaneChangeState.off),
      )

      def __getitem__(self, service):
        if service != 'modelV2':
          raise KeyError(service)
        self.model_reads += 1
        return self.model

      def all_checks(self, services):
        return services == ['modelV2', 'carState', 'vehicleParameters', 'lateralDelay']

    binding = LateralBinding('test-car', 'test-fw', 'test-model', 'torque', 0)
    owner = Controls.__new__(Controls)
    owner.LaC = CountingController()
    owner.VM = object()
    owner.sm = FakeSubMaster()
    owner.desired_curvature = 0.012
    owner.curvature = 0.011
    owner.steer_limited_by_safety = True
    owner.cyber_lateral_binding = binding
    owner.cyber_lateral_controller_type = 'torque'
    owner.cyber_lateral = CyberLateralCoordinator(
      CyberLateralConfig(mode=CyberLateralMode.OBSERVE_ONLY), binding,
    )
    CC = SimpleNamespace(latActive=True)
    CS = SimpleNamespace(vEgo=17.0, steeringPressed=False)
    lp = SimpleNamespace(roll=0.03)

    result = owner._update_lateral_control(CC, CS, lp, True, 0.24)

    self.assertIs(result, native_result)
    self.assertEqual(owner.LaC.calls, 1)
    self.assertEqual(owner.sm.model_reads, 0)
    self.assertIsNone(owner.cyber_lateral.last_observation)

    owner._update_cyber_lateral_observation()

    self.assertEqual(owner.sm.model_reads, 1)
    context = owner.cyber_lateral.last_observation.context
    self.assertEqual(
      (context.model_mono_time_ns, context.car_state_mono_time_ns,
       context.vehicle_parameters_mono_time_ns, context.lateral_delay_mono_time_ns),
      (101, 102, 103, 104),
    )
    self.assertTrue(context.input_valid)
    self.assertTrue(context.steer_limited_by_safety)
    self.assertTrue(context.curvature_limited)
    self.assertEqual(context.native_result, NativeLateralResult(0.25, -1.0, 'torque'))
    self.assertTrue(context.future_jerk_observation.valid)
    self.assertEqual(context.future_jerk_observation.jerk_mps3, (1., 1.))
    self.assertTrue(context.path_quality_observation.valid)
    covered_stations = tuple(value for value in LANE_STATIONS if value <= MODEL_PATH_STATIONS[-1])
    self.assertEqual(context.path_quality_observation.sample_count, len(covered_stations))
    self.assertAlmostEqual(
      context.path_quality_observation.model_to_lane_center_bias_m,
      sum(value * 0.005 for value in covered_stations) / len(covered_stations),
    )

    owner.sm.updated['modelV2'] = False
    second_result = owner._update_lateral_control(CC, CS, lp, True, 0.24)
    owner._update_cyber_lateral_observation()
    self.assertIs(second_result, native_result)
    self.assertEqual(owner.LaC.calls, 2)
    self.assertEqual(owner.sm.model_reads, 1)
    self.assertIs(owner.cyber_lateral.last_observation.context, context)


if __name__ == '__main__':
  unittest.main()
