"""Replay-only card entry point for the fixed STEP 7 development vehicle."""
import os

from openpilot.common.realtime import config_realtime_process, Priority
from openpilot.selfdrive.car import card


EXPECTED_CAR_FINGERPRINT = 'HYUNDAI_SANTA_FE_2022'
EXPECTED_CAR_INTERFACE_MODULE = 'opendbc.car.hyundai.interface'
REQUIRED_REPLAY_ENVIRONMENT = {
  'REPLAY': '1',
  'SIMULATION': '1',
  'PROC_NAME': 'card',
  'FINGERPRINT': EXPECTED_CAR_FINGERPRINT,
}


def validate_replay_environment() -> None:
  for key, expected in REQUIRED_REPLAY_ENVIRONMENT.items():
    actual = os.environ.get(key)
    if actual != expected:
      raise RuntimeError(f'Cyber Lateral replay card requires {key}={expected!r}; got {actual!r}')


def validate_replay_vehicle(car_params, interface_module: str) -> None:
  fingerprint = str(getattr(car_params, 'carFingerprint', None))
  if fingerprint != EXPECTED_CAR_FINGERPRINT:
    raise RuntimeError(f'Cyber Lateral replay card requires carFingerprint={EXPECTED_CAR_FINGERPRINT!r}; got {fingerprint!r}')
  if interface_module != EXPECTED_CAR_INTERFACE_MODULE:
    raise RuntimeError(f'Cyber Lateral replay card requires interface={EXPECTED_CAR_INTERFACE_MODULE!r}; got {interface_module!r}')
  if getattr(car_params, 'openpilotLongitudinalControl', None) is not True:
    raise RuntimeError('Cyber Lateral replay card requires openpilotLongitudinalControl=True')
  if getattr(car_params, 'pcmCruise', None) is not False:
    raise RuntimeError('Cyber Lateral replay card requires pcmCruise=False')
  if str(getattr(car_params, 'steerControlType', None)) != 'torque':
    raise RuntimeError('Cyber Lateral replay card requires steerControlType=torque')


def install_replay_init_bypass(replay_car) -> None:
  """Replace only the hardware ECU initializer inside fixed process replay."""
  validate_replay_environment()
  interface_module = type(replay_car.CI).__module__
  validate_replay_vehicle(replay_car.CP, interface_module)

  def replay_only_init(car_params, *_callbacks) -> None:
    validate_replay_environment()
    validate_replay_vehicle(car_params, interface_module)

  replay_car.CI.init = replay_only_init


def main() -> None:
  validate_replay_environment()
  config_realtime_process(4, Priority.CTRL_HIGH)
  replay_car = card.Car()
  install_replay_init_bypass(replay_car)
  replay_car.card_thread()


if __name__ == '__main__':
  main()
