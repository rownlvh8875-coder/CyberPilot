"""Synthetic status publishers for private host-native tests only."""

import gc
import time

from openpilot.system.cyberpilot_web.telemetry import CerealCollector, Store
from tools.cyberpilot_web_native.isolation import TOPICS, validate_namespace


class SyntheticPublisher:
  def __init__(self, run):
    validate_namespace(run)  # before importing native code or opening sockets
    from openpilot.cereal import messaging
    self.run = run
    self.messaging = messaging
    self.pm = messaging.PubMaster(list(TOPICS))

  def publish(self, topic, stamp=None, valid=True, fields=None):
    validate_namespace(self.run)
    if topic not in TOPICS:
      raise ValueError('status_topics_only')
    data = {
      'deviceState': {'started': True, 'freeSpacePercent': 50.0, 'memoryUsagePercent': 25, 'cpuTempC': [42.5]},
      'selfdriveState': {'enabled': True, 'active': True, 'alertText1': '합성 native 통신 검증 · 차량 데이터 아님', 'alertText2': ''},
      'carState': {'canValid': True},
      'managerState': {'processes': [{'name': 'synthetic-worker', 'pid': 123, 'running': True, 'shouldBeRunning': True, 'exitCode': 0}]},
    }[topic]
    message = self.messaging.new_message(topic, valid=valid, logMonoTime=time.monotonic_ns() if stamp is None else stamp)
    setattr(message, topic, {**data, **(fields or {})})
    self.pm.send(topic, message)

  def close(self):
    self.pm.sock.clear()
    gc.collect()


class NativeFixture:
  def __init__(self, run, clock=time.monotonic):
    self.publisher = SyntheticPublisher(run)
    self.store = Store('openpilot', clock=clock)
    self.collector = CerealCollector(self.store)  # real default factory, no double
    self.collector.poll()
    if self.collector.sm is None:
      self.publisher.close()
      raise RuntimeError('native_subscriber_unavailable')

  def push(self, topic, stamp, valid=True, fields=None):
    self.publisher.publish(topic, stamp, valid, fields)
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
      self.collector.poll()
      sm = self.collector.sm
      assert sm is not None
      if sm.updated[topic] and sm.logMonoTime[topic] == stamp:
        return
      time.sleep(0.005)
    raise TimeoutError('synthetic_native_receive_timeout')

  def close(self):
    self.collector.sm = None
    self.publisher.close()
    gc.collect()
