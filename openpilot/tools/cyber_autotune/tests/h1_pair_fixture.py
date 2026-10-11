"""Reusable real synthetic pair fixture; no private or raw reader dependency."""

from functools import lru_cache
from openpilot.tools.cyber_autotune import cyber_h1_pairing as q
from openpilot.tools.cyber_autotune import cyber_h1_pair_producer as producer


@lru_cache(maxsize=1)
def pairs():
  context = q.policy()
  return {kind: [producer.run(kind, arm, 'driver_events', context)[1] for arm in (q.BASELINE, info[1])] for kind, info in q.CAMPAIGNS.items()}
