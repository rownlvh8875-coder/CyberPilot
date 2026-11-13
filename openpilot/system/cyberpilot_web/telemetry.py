"""Small read-only telemetry boundary. Receipt age is not an apply timestamp."""

import copy
import math
import os
import platform
import shutil
import threading
import time
from typing import Any

TOPICS = ("deviceState", "selfdriveState", "carState", "managerState")
FRESHNESS_S = 5.0


class Store:
  def __init__(self, source: str, clock=time.monotonic):
    self.source = source
    self.clock = clock
    self.lock = threading.Lock()
    self.records: dict[str, dict[str, Any]] = {}
    self.host: dict[str, Any] | None = None
    self.host_received: float | None = None
    self.error: str | None = None

  def update(self, topic: str, data: dict, event_ns: int, valid: bool) -> bool:
    if topic not in TOPICS:
      raise ValueError("unsupported_topic")
    if type(event_ns) is not int or not 0 <= event_ns < 2**64:
      raise ValueError("invalid_source_timestamp")
    with self.lock:
      old = self.records.get(topic)
      if old and event_ns <= old["event_ns"]:
        return False
      self.records[topic] = {"event_ns": event_ns, "received": self.clock(), "valid": valid is True,
                             "data": copy.deepcopy(data)}
      return True

  def set_error(self, error: str | None):
    with self.lock:
      self.error = error

  def set_host(self, data: dict):
    with self.lock:
      self.host = copy.deepcopy(data)
      self.host_received = self.clock()

  def snapshot(self) -> dict:
    with self.lock:
      now = self.clock()
      topics = {}
      for name in TOPICS:
        record = self.records.get(name)
        age = max(0.0, now - record["received"]) if record else None
        status = "missing" if record is None else (
          "invalid" if not record["valid"] else "stale" if age is not None and age >= FRESHNESS_S else "live")
        topics[name] = {"status": status, "age_s": age,
                        "source_time_ns": str(record["event_ns"]) if record else None,
                        "data": copy.deepcopy(record["data"]) if record and status == "live" else None}
      host_age = max(0.0, now - self.host_received) if self.host_received is not None else None
      return {"schema_version": 1, "source": self.source, "freshness_s": FRESHNESS_S,
              "host": copy.deepcopy(self.host) if host_age is not None and host_age < FRESHNESS_S else None,
              "host_age_s": host_age, "topics": topics, "collector_error": self.error,
              "control_qualification": "NOT_QUALIFIED"}


def number(value, minimum=None, maximum=None):
  if type(value) not in (int, float) or not math.isfinite(value):
    return None
  if minimum is not None and value < minimum or maximum is not None and value > maximum:
    return None
  return value


def boolean(value):
  return value if type(value) is bool else None


def text(value):
  return value[:256] if isinstance(value, str) else None


def map_topic(name: str, msg) -> dict:
  if name == "deviceState":
    temps = getattr(msg, "cpuTempC", [])
    return {"started": boolean(getattr(msg, "started", None)),
            "free_space_percent": number(getattr(msg, "freeSpacePercent", None), 0, 100),
            "memory_usage_percent": number(getattr(msg, "memoryUsagePercent", None), 0, 100),
            "cpu_temp_c": [v for x in list(temps)[:32] if (v := number(x, -100, 200)) is not None]}
  if name == "selfdriveState":
    return {"enabled": boolean(getattr(msg, "enabled", None)), "active": boolean(getattr(msg, "active", None)),
            "alert_text_1": text(getattr(msg, "alertText1", None)), "alert_text_2": text(getattr(msg, "alertText2", None))}
  if name == "carState":
    # canValid is consumed at openpilot/selfdrive/car/card.py:212; no speed/unit inference.
    return {"can_valid": boolean(getattr(msg, "canValid", None))}
  if name == "managerState":
    return {"processes": [{"name": text(getattr(p, "name", None)),
                           "running": boolean(getattr(p, "running", None)),
                           "should_be_running": boolean(getattr(p, "shouldBeRunning", None))}
                          for p in list(getattr(msg, "processes", []))[:128]]}
  raise ValueError("unsupported_topic")


class HostCollector:
  def __init__(self, store: Store):
    self.store = store

  def poll(self):
    disk = shutil.disk_usage("/")
    memory = None
    try:
      with open("/proc/meminfo", encoding="ascii") as stream:
        info = {line.split(":")[0]: int(line.split()[1]) for line in stream if ":" in line}
      memory = number(100 * (1 - info["MemAvailable"] / info["MemTotal"]), 0, 100)
    except (OSError, ValueError, KeyError, ZeroDivisionError):
      pass
    self.store.set_host({"platform": platform.system(), "architecture": platform.machine(),
                         "cpu_count": os.cpu_count(), "load_1m": number(os.getloadavg()[0], 0),
                         "memory_usage_percent": memory,
                         "disk_total_bytes": disk.total, "disk_free_bytes": disk.free})


def subscriber(topics):
  # Optional native dependencies must never be imported for host monitoring.
  from openpilot.cereal import messaging
  return messaging.SubMaster(topics)


class CerealCollector:
  def __init__(self, store: Store, factory=subscriber):
    self.store = store
    self.factory = factory
    self.sm = None

  def poll(self):
    try:
      if self.sm is None:
        self.sm = self.factory(list(TOPICS))
      self.sm.update(0)
      for name in TOPICS:
        if self.sm.updated[name]:
          self.store.update(name, map_topic(name, self.sm[name]), self.sm.logMonoTime[name], self.sm.valid[name])
      self.store.set_error(None)
    except (ImportError, OSError, RuntimeError, ValueError, TypeError, AttributeError, KeyError):
      self.store.set_error("source_unavailable")
