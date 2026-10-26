"""Process-replay configuration for the non-actuating STEP 7 card baseline."""
from openpilot.selfdrive.test.process_replay.process_replay import get_process_config


CYBER_LATERAL_REPLAY_CARD_MODULE = 'openpilot.selfdrive.test.process_replay.cyber_lateral_card'


def get_cyber_lateral_card_process_config():
  config = get_process_config('card')
  config.python_module = CYBER_LATERAL_REPLAY_CARD_MODULE
  return config
