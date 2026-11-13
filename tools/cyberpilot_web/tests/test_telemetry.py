import math
import unittest
from types import SimpleNamespace
from typing import Any, cast

from openpilot.system.cyberpilot_web.telemetry import CerealCollector, HostCollector, Store


class StateTests(unittest.TestCase):
  def setUp(self):
    self.now = 10.0
    self.store = Store("test", clock=lambda: self.now)

  def test_missing_is_null(self):
    for record in self.store.snapshot()["topics"].values():
      self.assertEqual(record["status"], "missing")
      self.assertIsNone(record["data"])

  def test_independent_staleness(self):
    self.store.update("carState", {"can_valid": True}, 1, True)
    self.now += 6
    self.store.update("deviceState", {"started": True}, 1, True)
    data = self.store.snapshot()["topics"]
    self.assertEqual(data["carState"]["status"], "stale")
    self.assertIsNone(data["carState"]["data"])
    self.assertEqual(data["deviceState"]["status"], "live")

  def test_invalid_hides_values(self):
    self.store.update("carState", {"can_valid": True}, 1, False)
    self.assertEqual(self.store.snapshot()["topics"]["carState"]["status"], "invalid")
    self.assertIsNone(self.store.snapshot()["topics"]["carState"]["data"])

  def test_replay_does_not_refresh(self):
    self.store.update("carState", {}, 100, True)
    self.now += 6
    self.assertFalse(self.store.update("carState", {}, 100, True))
    self.assertFalse(self.store.update("carState", {}, 99, True))
    self.assertEqual(self.store.snapshot()["topics"]["carState"]["status"], "stale")

  def test_source_time_exact_string(self):
    stamp = 2**63 - 1
    self.store.update("carState", {}, cast(Any, stamp), True)
    self.assertEqual(self.store.snapshot()["topics"]["carState"]["source_time_ns"], str(stamp))

  def test_bad_timestamps_rejected(self):
    for stamp in (True, -1, 1.5, 2**64):
      with self.assertRaises(ValueError):
        self.store.update("carState", {}, cast(Any, stamp), True)

  def test_unknown_topic_rejected(self):
    with self.assertRaises(ValueError):
      self.store.update("sendcan", {}, 1, True)

  def test_snapshot_is_detached(self):
    payload = {"started": True}
    self.store.update("deviceState", payload, 1, True)
    payload["started"] = False
    self.store.snapshot()["topics"]["deviceState"]["data"]["started"] = False
    self.assertTrue(self.store.snapshot()["topics"]["deviceState"]["data"]["started"])


class CollectorTests(unittest.TestCase):
  def test_host_is_actual_and_vehicle_unknown(self):
    store = Store("host")
    HostCollector(store).poll()
    snap = store.snapshot()
    self.assertEqual(snap["source"], "host")
    self.assertGreater(snap["host"]["disk_total_bytes"], 0)
    self.assertTrue(math.isfinite(snap["host"]["load_1m"]))
    self.assertIsNone(snap["topics"]["carState"]["data"])

  def test_fake_subscriber_mapping(self):
    store = Store("openpilot")
    class Subscriber:
      updated = {"deviceState": True, "selfdriveState": False, "carState": True, "managerState": False}
      valid = dict.fromkeys(updated, True)
      logMonoTime = dict.fromkeys(updated, 10)
      def update(self, timeout):
        self.timeout = timeout
      def __getitem__(self, name):
        return SimpleNamespace(started=True, freeSpacePercent=25.0, memoryUsagePercent=40, cpuTempC=[45.0], canValid=True)
    collector = CerealCollector(store, factory=lambda topics: Subscriber())
    collector.poll()
    snap = store.snapshot()["topics"]
    self.assertTrue(snap["carState"]["data"]["can_valid"])
    self.assertEqual(snap["selfdriveState"]["status"], "missing")

  def test_unavailable_source_is_explicit(self):
    def fail(topics):
      raise ImportError("private system path")
    store = Store("openpilot")
    collector = CerealCollector(store, factory=fail)
    collector.poll()
    self.assertEqual(store.snapshot()["collector_error"], "source_unavailable")
    self.assertNotIn("private", str(store.snapshot()))

  def test_bad_fields_become_null(self):
    from openpilot.system.cyberpilot_web.telemetry import map_topic
    result = map_topic("deviceState", SimpleNamespace(started=1, freeSpacePercent=float("nan"), cpuTempC=[float("inf")]))
    self.assertIsNone(result["started"])
    self.assertIsNone(result["free_space_percent"])
    self.assertEqual(result["cpu_temp_c"], [])
