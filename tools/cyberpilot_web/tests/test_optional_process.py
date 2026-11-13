"""Exercise exact upstream process methods with inert process/Cereal substitutes."""

import ast
import contextlib
import importlib.util
import io
import os
import signal
import sys
import types
import unittest
from abc import ABC, abstractmethod
from pathlib import Path
from unittest.mock import patch

from openpilot.system.cyberpilot_web import daemon

ROOT = Path(__file__).resolve().parents[3]


class FakeChild:
  def __init__(self, *args, **kwargs):
    self.exitcode = None
    self.pid = 123
    self.alive = False

  def start(self):
    self.alive = True

  def is_alive(self):
    return self.alive


def isolated_process_classes():
  tree = ast.parse((ROOT / "openpilot/system/manager/process.py").read_text())
  future = ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0)
  classes = [node for node in tree.body if isinstance(node, ast.ClassDef) and node.name in ("ManagerProcess", "PythonProcess")]
  def state():
    return types.SimpleNamespace(running=False, shouldBeRunning=False, pid=0, exitCode=0)
  scope = {"ABC": ABC, "abstractmethod": abstractmethod, "Process": FakeChild,
           "launcher": lambda *args: None, "signal": signal,
           "log": types.SimpleNamespace(ManagerState=types.SimpleNamespace(ProcessState=types.SimpleNamespace(new_message=state))),
           "cloudlog": types.SimpleNamespace(info=lambda *args: None)}
  exec(compile(ast.fix_missing_locations(ast.Module(body=[future, *classes], type_ignores=[])), "exact-process-classes-inert-dependencies", "exec"), scope)
  base = scope["PythonProcess"]
  stub = types.ModuleType("openpilot.system.manager.process")
  stub.__dict__["PythonProcess"] = base
  config = ast.parse((ROOT / "openpilot/system/manager/process_config.py").read_text())
  entry = next(n for n in ast.walk(config) if isinstance(n, ast.Call) and n.args and isinstance(n.args[0], ast.Constant) and n.args[0].value == "cyberpilot_web")
  if isinstance(entry.func, ast.Name) and entry.func.id == "PythonProcess":
    return base, types.SimpleNamespace(OptionalStatusProcess=base)
  path = ROOT / "openpilot/system/cyberpilot_web/manager_process.py"
  spec = importlib.util.spec_from_file_location("isolated_optional_process", path)
  assert spec is not None and spec.loader is not None
  module = importlib.util.module_from_spec(spec)
  with patch.dict(sys.modules, {"openpilot.system.manager.process": stub}):
    spec.loader.exec_module(module)
  return base, module


class OptionalProcessTests(unittest.TestCase):
  def test_failed_optional_child_cannot_enter_required_failure_set(self):
    base, module = isolated_process_classes()
    normal = base("normal", "no-execution", lambda *args: True)
    optional = module.OptionalStatusProcess("cyberpilot_web", "no-execution", lambda *args: True)
    for process in (normal, optional):
      process.start()
      process.proc.alive = False
      process.proc.exitcode = 1
    states = [process.get_process_state_msg() for process in (normal, optional)]
    required_failures = {p.name for p in states if not p.running and p.shouldBeRunning}
    self.assertEqual(required_failures, {"normal"})
    self.assertFalse(states[1].running)
    self.assertEqual(states[1].exitCode, 1)

  def test_failed_child_reaped_and_restart_backoff(self):
    _, module = isolated_process_classes()
    now = [100.0]
    process = module.OptionalStatusProcess("web", "no-execution", lambda *args: True)
    if hasattr(module, "time"):
      module.time = types.SimpleNamespace(monotonic=lambda: now[0])
    process.start()
    first = process.proc
    first.alive = False
    first.exitcode = 1
    now[0] = 101.0
    process.start()
    self.assertIsNone(process.proc)
    process.start()
    self.assertIsNone(process.proc)
    now[0] = 131.0
    process.start()
    self.assertIsNot(process.proc, first)
    self.assertTrue(process.proc.is_alive())

  def test_configuration_and_transient_bind_failure_are_local(self):
    with patch.dict(os.environ, {"CYBERPILOT_WEB": "1", "CYBERPILOT_WEB_TOKEN_FILE": "/private/token"}, clear=True):
      for target, error in (("load_token", ValueError("bad token")), ("run", OSError("bind unavailable"))):
        with contextlib.redirect_stderr(io.StringIO()), patch.object(daemon, "load_token", return_value="c" * 43), patch.object(daemon, target, side_effect=error):
          self.assertIsNone(daemon.main())
