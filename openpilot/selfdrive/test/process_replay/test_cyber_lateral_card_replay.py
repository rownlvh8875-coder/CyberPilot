import importlib
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from openpilot.selfdrive.test.process_replay import cyber_lateral_replay
from openpilot.selfdrive.test.process_replay.process_replay import ProcessContainer
from openpilot.system.manager.process_config import managed_processes


class TestCyberLateralCardReplayConfiguration(unittest.TestCase):
  def test_card_module_override_is_copy_local(self):
    original_module = managed_processes['card'].module
    config = cyber_lateral_replay.get_cyber_lateral_card_process_config()
    container = ProcessContainer(config)

    self.assertEqual(config.proc_name, 'card')
    self.assertEqual(config.python_module, 'openpilot.selfdrive.test.process_replay.cyber_lateral_card')
    self.assertEqual(container.process.module, config.python_module)
    self.assertEqual(managed_processes['card'].module, original_module)
    self.assertEqual(original_module, 'openpilot.selfdrive.car.card')

  def test_environment_requires_replay_simulation_card_and_fixed_fingerprint(self):
    replay_card = importlib.import_module('openpilot.selfdrive.test.process_replay.cyber_lateral_card')
    approved = {
      'REPLAY': '1',
      'SIMULATION': '1',
      'PROC_NAME': 'card',
      'FINGERPRINT': 'HYUNDAI_SANTA_FE_2022',
    }
    with patch.dict(os.environ, approved, clear=True):
      replay_card.validate_replay_environment()

    for key, value in (('REPLAY', '0'), ('SIMULATION', '0'), ('PROC_NAME', 'card-live'), ('FINGERPRINT', 'HYUNDAI_SONATA')):
      with self.subTest(key=key), patch.dict(os.environ, {**approved, key: value}, clear=True):
        with self.assertRaisesRegex(RuntimeError, key):
          replay_card.validate_replay_environment()

  def test_vehicle_requires_fixed_hyundai_torque_control_contract(self):
    replay_card = importlib.import_module('openpilot.selfdrive.test.process_replay.cyber_lateral_card')
    approved = SimpleNamespace(
      carFingerprint='HYUNDAI_SANTA_FE_2022',
      openpilotLongitudinalControl=True,
      pcmCruise=False,
      steerControlType='torque',
    )
    replay_card.validate_replay_vehicle(approved, 'opendbc.car.hyundai.interface')

    invalid = SimpleNamespace(**{**vars(approved), 'steerControlType': 'angle'})
    with self.assertRaisesRegex(RuntimeError, 'steerControlType'):
      replay_card.validate_replay_vehicle(invalid, 'opendbc.car.hyundai.interface')
    with self.assertRaisesRegex(RuntimeError, 'interface'):
      replay_card.validate_replay_vehicle(approved, 'opendbc.car.toyota.interface')

  def test_init_bypass_skips_hardware_call_and_revalidates_authority(self):
    replay_card = importlib.import_module('openpilot.selfdrive.test.process_replay.cyber_lateral_card')
    original_calls = []

    class FakeHyundaiInterface:
      def init(self, *args):
        original_calls.append(args)

    FakeHyundaiInterface.__module__ = 'opendbc.car.hyundai.interface'
    cp = SimpleNamespace(
      carFingerprint='HYUNDAI_SANTA_FE_2022',
      openpilotLongitudinalControl=True,
      pcmCruise=False,
      steerControlType='torque',
    )
    replay_car = SimpleNamespace(CP=cp, CI=FakeHyundaiInterface())
    approved = {
      'REPLAY': '1',
      'SIMULATION': '1',
      'PROC_NAME': 'card',
      'FINGERPRINT': 'HYUNDAI_SANTA_FE_2022',
    }
    with patch.dict(os.environ, approved, clear=True):
      replay_card.install_replay_init_bypass(replay_car)
      replay_car.CI.init(cp, object(), object())
    self.assertEqual(original_calls, [])

    with patch.dict(os.environ, {**approved, 'REPLAY': '0'}, clear=True):
      with self.assertRaisesRegex(RuntimeError, 'REPLAY'):
        replay_car.CI.init(cp, object(), object())

  def test_main_runs_production_card_loop_with_replay_only_bypass(self):
    replay_card = importlib.import_module('openpilot.selfdrive.test.process_replay.cyber_lateral_card')
    original_calls = []
    card_thread_calls = []

    class FakeHyundaiInterface:
      def init(self, *args):
        original_calls.append(args)

    FakeHyundaiInterface.__module__ = 'opendbc.car.hyundai.interface'
    cp = SimpleNamespace(
      carFingerprint='HYUNDAI_SANTA_FE_2022',
      openpilotLongitudinalControl=True,
      pcmCruise=False,
      steerControlType='torque',
    )
    replay_car = SimpleNamespace(CP=cp, CI=FakeHyundaiInterface())

    def card_thread():
      replay_car.CI.init(cp, object(), object())
      card_thread_calls.append(True)

    replay_car.card_thread = card_thread
    approved = {
      'REPLAY': '1',
      'SIMULATION': '1',
      'PROC_NAME': 'card',
      'FINGERPRINT': 'HYUNDAI_SANTA_FE_2022',
    }
    with patch.dict(os.environ, approved, clear=True), \
         patch.object(replay_card, 'config_realtime_process') as configure_realtime, \
         patch.object(replay_card.card, 'Car', return_value=replay_car):
      replay_card.main()

    self.assertEqual(original_calls, [])
    self.assertEqual(card_thread_calls, [True])
    configure_realtime.assert_called_once_with(4, replay_card.Priority.CTRL_HIGH)


if __name__ == '__main__':
  unittest.main()
