import ast
import json
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from typing import Any
from unittest.mock import patch

from openpilot.system.cyberpilot_web import daemon
from openpilot.system.cyberpilot_web.readiness import inspect_readiness
from tools.cyberpilot_web.distribute import build_bundle

ROOT = Path(__file__).resolve().parents[3]


class DeploymentTests(unittest.TestCase):
  def test_launch_resource_paths_exist(self):
    report = inspect_readiness(ROOT)
    self.assertTrue(report["source_resources_complete"], report)
    self.assertFalse(report["device_installation_qualified"])
    self.assertFalse(report["control_activation_allowed"])

  def test_missing_source_is_not_ready(self):
    with tempfile.TemporaryDirectory() as directory:
      report = inspect_readiness(Path(directory))
      self.assertFalse(report["source_resources_complete"])
      self.assertFalse(report["device_installation_qualified"])

  def test_external_resource_symlink_not_accepted(self):
    with tempfile.TemporaryDirectory() as directory:
      root = Path(directory)
      for name in ("launch_openpilot.sh", "launch_chffrplus.sh", "launch_env.sh",
                   "openpilot/system/manager/manager.py", "openpilot/common/hardware/comma/agnos.py",
                   "openpilot/system/hardware/comma/agnos.json"):
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        (root / name).symlink_to(ROOT / name)
      self.assertFalse(inspect_readiness(root)["source_resources_complete"])

  def test_daemon_off_by_default(self):
    self.assertIsNone(daemon.configuration({}))
    self.assertIsNone(daemon.configuration({"CYBERPILOT_WEB": "0"}))

  def test_daemon_requires_explicit_private_credentials(self):
    with self.assertRaises(ValueError):
      daemon.configuration({"CYBERPILOT_WEB": "1"})
    config = daemon.configuration({"CYBERPILOT_WEB": "1", "CYBERPILOT_WEB_TOKEN_FILE": "/private/token"})
    self.assertEqual(config["host"], "127.0.0.1")
    self.assertEqual(config["source"], "openpilot")

  def test_daemon_invalid_port_and_tls_rejected(self):
    for env in ({"CYBERPILOT_WEB_PORT": "0"}, {"CYBERPILOT_WEB_PORT": "invalid"}, {"CYBERPILOT_WEB_TLS_CERT": "/cert"}):
      with self.assertRaises(ValueError):
        daemon.configuration({"CYBERPILOT_WEB": "1", "CYBERPILOT_WEB_TOKEN_FILE": "/token", **env})

  def test_disabled_daemon_does_not_start(self):
    with patch.dict(os.environ, {}, clear=True), patch.object(daemon, "run") as run:
      daemon.main()
      run.assert_not_called()

  def test_manager_registration_opt_in(self):
    tree = ast.parse((ROOT / "openpilot/system/manager/process_config.py").read_text())
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "cyberpilot_web_enabled")
    scope: dict[str, Any] = {"os": os}
    exec(compile(ast.Module(body=[function], type_ignores=[]), "manager-function-only", "exec"), scope)
    for env, expected in (({}, False), ({"CYBERPILOT_WEB": "1"}, False),
                          ({"CYBERPILOT_WEB": "1", "CYBERPILOT_WEB_TOKEN_FILE": "/token"}, True)):
      with patch.dict(os.environ, env, clear=True):
        self.assertIs(scope["cyberpilot_web_enabled"](), expected)
    entries = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
               and n.func.id == "PythonProcess" and n.args and isinstance(n.args[0], ast.Constant) and n.args[0].value == "cyberpilot_web"]
    self.assertEqual(len(entries), 1)
    assert isinstance(entries[0].args[1], ast.Constant)
    self.assertEqual(entries[0].args[1].value, "openpilot.system.cyberpilot_web.daemon")
    self.assertEqual(ast.unparse(entries[0].args[2]), "always_run")
    self.assertEqual(ast.unparse(next(k.value for k in entries[0].keywords if k.arg == "enabled")), "cyberpilot_web_enabled()")

  def test_bundle_deterministic_and_standalone(self):
    with tempfile.TemporaryDirectory() as directory:
      base = Path(directory)
      a, b = base / "one.zip", base / "two.zip"
      build_bundle(ROOT, a)
      build_bundle(ROOT, b)
      self.assertEqual(a.read_bytes(), b.read_bytes())
      with zipfile.ZipFile(a) as archive:
        self.assertIsNone(archive.testzip())
        archive.extractall(base / "extracted")
        manifest = json.loads(archive.read("MANIFEST.json"))
        import hashlib
        for name, expected in manifest["files"].items():
          self.assertEqual(hashlib.sha256(archive.read(name)).hexdigest(), expected)
      result = subprocess.run([sys.executable, "-B", "-m", "openpilot.system.cyberpilot_web", "--help"],
                              cwd=base / "extracted", env={**os.environ, "PYTHONPATH": str(base / "extracted")}, capture_output=True, timeout=10)
      self.assertEqual(result.returncode, 0, result.stderr)
      self.assertTrue(archive.getinfo("run-web.sh").external_attr >> 16 & 0o100)

  def test_extracted_bundle_actual_http(self):
    import http.client
    import queue
    import threading

    from openpilot.system.cyberpilot_web.server import init_token
    with tempfile.TemporaryDirectory() as directory:
      base = Path(directory)
      bundle = base / "bundle.zip"
      build_bundle(ROOT, bundle)
      with zipfile.ZipFile(bundle) as archive:
        archive.extractall(base / "app")
      token_path = base / "token"
      token = init_token(token_path)
      proc = subprocess.Popen([sys.executable, "-B", "-m", "openpilot.system.cyberpilot_web", "serve", "--token-file", str(token_path), "--port", "0"],
                              cwd=base / "app", env={**os.environ, "PYTHONPATH": str(base / "app")}, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
      line = ""
      try:
        lines = queue.Queue()
        stream = proc.stdout
        assert stream is not None
        threading.Thread(target=lambda: lines.put(stream.readline()), daemon=True).start()
        line = lines.get(timeout=8)
        self.assertIn("source=host", line)
        port = int(line.split("127.0.0.1:")[1].split("/")[0])
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
        conn.request("GET", "/api/status", headers={"Authorization": "Bearer " + token})
        response = conn.getresponse()
        self.assertEqual(response.status, 200)
        data = json.loads(response.read())
        conn.close()
        self.assertGreater(data["host"]["disk_total_bytes"], 0)
        self.assertEqual(data["identity"], {"branch": None, "commit": None})
        self.assertIsNone(data["topics"]["carState"]["data"])
      finally:
        proc.terminate()
        stdout, stderr = proc.communicate(timeout=8)
        self.assertNotIn(token, line + stdout + stderr)
