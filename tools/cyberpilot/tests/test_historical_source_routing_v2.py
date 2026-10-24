"""Real isolated source/receipt/result negative controls. No authority."""
from copy import deepcopy
import importlib.util
import json
import sys
import os
from pathlib import Path
import shutil
import tempfile
import unittest
import zlib

ROOT = Path(__file__).resolve().parents[3]
ROUTER = ROOT / "tools/cyberpilot/historical_source_routing_v2.py"
CONTRACT = ROOT / "docs/cyberpilot/changes/historical-source-routing-v2.json"


class HistoricalRoutingTests(unittest.TestCase):
  def api(self):
    spec = importlib.util.spec_from_file_location("f32_test_router", ROUTER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

  def setUp(self):
    self.mod = self.api()
    self.contract = self.mod.load_contract(CONTRACT)
    self.case = tempfile.TemporaryDirectory(prefix="f32-case-")
    self.base = Path(os.environ["F32_B1_CAPSULE"])
    self.root = Path(self.case.name) / "B1"
    shutil.copytree(self.base, self.root, copy_function=shutil.copyfile)

  def tearDown(self):
    self.case.cleanup()

  def mutate(self, name, content=None):
    p = self.root / name
    p.write_bytes(p.read_bytes() + b" " if content is None else content)

  def payload(self):
    ids = self.contract["test_ids"]["legacy"]
    return {
      "collected_ids": ids, "test_exit_code": 0,
      "records": [{"id": n, "status": "passed", "detail": ""} for n in ids],
      "raw_unittest_counts": {"run": len(ids), "passed": len(ids), "failed": 0, "error": 0,
                              "skipped": 0, "xfailed": 0, "xpassed": 0},
    }

  def test_exact_historical_capsule(self):
    row = self.mod.inspect_capsule(self.root, self.contract, "B1")
    self.assertEqual(row["base_commit"], self.mod.HISTORICAL)
    self.assertFalse(row["runtime_authorized"])

  def test_current_a_pins_executed_v1_test_bytes(self):
    anchor = self.root / self.contract["anchor"]
    anchor.write_bytes((Path(os.environ["F32_SOURCE_REPO"]) / self.contract["anchor"]).read_bytes())
    self.mod.verify_current(self.root, self.contract)
    name = self.contract["test_files"]["legacy"]
    self.mutate(name, (self.root / name).read_bytes() + b"\n# changed body bytes; test IDs remain unchanged\n")
    with self.assertRaisesRegex(self.mod.BindingError, "^CURRENT_A_SOURCE_MISMATCH$"):
      self.mod.verify_current(self.root, self.contract)

  def test_wrong_historical_commit_blocked(self):
    with self.assertRaisesRegex(self.mod.BindingError, "^HISTORICAL_COMMIT_MISMATCH$"):
      self.mod.build_capsule(Path(os.environ["F32_SOURCE_REPO"]), self.contract, "B1",
                             Path(self.case.name) / "bad", commit="51c1cdb3327f442d026e5ba3bdcc173438a6aae1")

  def test_missing_git_object_blocked(self):
    empty = Path(self.case.name) / "empty"
    self.mod.initialize_thin_git(empty, self.mod.HISTORICAL)
    with self.assertRaisesRegex(self.mod.BindingError, "^GIT_OBJECT_UNAVAILABLE$"):
      self.mod.object_bytes(empty, "commit", self.mod.HISTORICAL)

  def test_corrupt_git_blob_blocked(self):
    oid = self.contract["origins"][self.contract["anchor"]]["blob_oid"]
    obj = self.root / ".git/objects" / oid[:2] / oid[2:]
    obj.write_bytes(zlib.compress(b"blob 7\0changed"))
    with self.assertRaisesRegex(self.mod.BindingError, "^GIT_OBJECT_HASH_MISMATCH$"):
      self.mod.object_bytes(self.root, "blob", oid)

  def test_b1_cannot_use_b2_capture_sha(self):
    self.mutate(self.contract["capture"], (ROOT / self.contract["capture"]).read_bytes())
    with self.assertRaisesRegex(self.mod.BindingError, "^CAPSULE_SOURCE_MISMATCH$"):
      self.mod.inspect_capsule(self.root, self.contract, "B1")

  def test_b1_cannot_be_relabelled_b2(self):
    with self.assertRaisesRegex(self.mod.BindingError, "^CAPSULE_SOURCE_MISMATCH$"):
      self.mod.inspect_capsule(self.root, self.contract, "B2")

  def test_historical_receipt_tamper(self):
    self.mutate(next(iter(self.contract["historical_receipts"])))
    with self.assertRaisesRegex(self.mod.BindingError, "^HISTORICAL_RECEIPT_MISMATCH$"):
      self.mod.inspect_capsule(self.root, self.contract, "B1")

  def test_v1_contract_tamper(self):
    self.mutate("docs/cyberpilot/changes/capture-only-source-version-v1.json")
    with self.assertRaisesRegex(self.mod.BindingError, "^V1_SOURCE_OR_CONTRACT_MISMATCH$"):
      self.mod.inspect_capsule(self.root, self.contract, "B1")

  def test_v2_contract_tamper(self):
    path = Path(self.case.name) / "changed-contract.json"
    path.write_bytes(CONTRACT.read_bytes() + b" ")
    with self.assertRaisesRegex(self.mod.BindingError, "^CONTRACT_IDENTITY_MISMATCH$"):
      self.mod.load_contract(path)

  def test_frozen_source_mutation(self):
    self.mutate(".gitattributes")
    with self.assertRaisesRegex(self.mod.BindingError, "^FROZEN_SOURCE_MISMATCH$"):
      self.mod.inspect_capsule(self.root, self.contract, "B1")

  def test_missing_source_file(self):
    (self.root / self.contract["anchor"]).unlink()
    with self.assertRaisesRegex(self.mod.BindingError, "^CAPSULE_FILE_SET_MISMATCH$"):
      self.mod.inspect_capsule(self.root, self.contract, "B1")

  def test_source_import_mix(self):
    with self.assertRaisesRegex(self.mod.BindingError, "^IMPORT_ROOT_MIXED$"):
      self.mod.verify_origin_paths({"openpilot.x": "/unrelated/B2/x.py"}, self.root)

  def test_parent_path_import_alias_mix(self):
    with self.assertRaisesRegex(self.mod.BindingError, "^IMPORT_ROOT_MIXED$"):
      self.mod.verify_origin_paths({"openpilot.x": str(self.root / "../other/x.py")}, self.root)

  def test_missing_test_id(self):
    p = self.payload()
    p["records"].pop()
    with self.assertRaisesRegex(self.mod.BindingError, "^MISSING_OR_UNKNOWN_TEST_ID$"):
      self.mod.validate_records(p, self.contract["test_ids"]["legacy"])

  def test_duplicate_test_id(self):
    p = self.payload()
    p["records"].append(deepcopy(p["records"][0]))
    with self.assertRaisesRegex(self.mod.BindingError, "^DUPLICATE_TEST_ID$"):
      self.mod.validate_records(p, self.contract["test_ids"]["legacy"])

  def test_error_not_pass(self):
    p = self.payload()
    p["records"][0]["status"] = "error"
    p["test_exit_code"] = 1
    with self.assertRaises(self.mod.BindingError):
      self.mod.validate_records(p, self.contract["test_ids"]["legacy"])

  def test_raw_failure_cannot_be_laundered_as_pass(self):
    p = self.payload()
    p["raw_unittest_counts"]["passed"] -= 1
    p["raw_unittest_counts"]["failed"] += 1
    with self.assertRaisesRegex(self.mod.BindingError, "^RAW_RESULT_CONFLICT$"):
      self.mod.validate_records(p, self.contract["test_ids"]["legacy"])

  def test_skipped_not_pass(self):
    p = self.payload()
    p["records"][0]["status"] = "skipped"
    with self.assertRaises(self.mod.BindingError):
      self.mod.validate_records(p, self.contract["test_ids"]["legacy"])

  def test_authority_escalation(self):
    lanes = {
      "A": {"lane": "A", "source_identity": self.mod.verify_current_identity(self.contract),
            "source_version": "CURRENT_A_COMPATIBLE_CONTROLSD_NOT_WHOLE_HISTORICAL_A",
            "anchor_sha256": self.contract["source_a_anchor"]["sha256"], **self.mod.AUTHORITY},
      **{k: self.mod.inspect_capsule(Path(os.environ["F32_CAPSULE_ROOT"]) / k, self.contract, k) for k in ("B1", "B2")},
    }
    lanes["B2"]["runtime_authorized"] = True
    with self.assertRaisesRegex(self.mod.BindingError, "^AUTHORITY_ESCALATION$"):
      self.mod.aggregate(lanes, self.contract)

  def test_a_result_cannot_be_used_as_b2(self):
    lanes = {
      "A": {"lane": "A", "source_identity": self.mod.verify_current_identity(self.contract),
            "source_version": "CURRENT_A_COMPATIBLE_CONTROLSD_NOT_WHOLE_HISTORICAL_A",
            "anchor_sha256": self.contract["source_a_anchor"]["sha256"], **self.mod.AUTHORITY},
      **{k: self.mod.inspect_capsule(Path(os.environ["F32_CAPSULE_ROOT"]) / k, self.contract, k) for k in ("B1", "B2")},
    }
    lanes["B2"] = deepcopy(lanes["A"])
    with self.assertRaisesRegex(self.mod.BindingError, "^LANE_RESULT_BINDING_MISMATCH$"):
      self.mod.aggregate(lanes, self.contract)

  def test_b2_version_label_cannot_be_spoofed(self):
    lanes = {
      "A": {"lane": "A", "source_identity": self.mod.verify_current_identity(self.contract),
            "source_version": "CURRENT_A_COMPATIBLE_CONTROLSD_NOT_WHOLE_HISTORICAL_A",
            "anchor_sha256": self.contract["source_a_anchor"]["sha256"], **self.mod.AUTHORITY},
      **{k: self.mod.inspect_capsule(Path(os.environ["F32_CAPSULE_ROOT"]) / k, self.contract, k) for k in ("B1", "B2")},
    }
    lanes["B2"]["source_version"] = lanes["B1"]["source_version"]
    with self.assertRaisesRegex(self.mod.BindingError, "^SOURCE_VERSION_METADATA_MISMATCH$"):
      self.mod.aggregate(lanes, self.contract)

  def test_source_sha_metadata_cannot_be_spoofed(self):
    lanes = {
      "A": {"lane": "A", "source_identity": self.mod.verify_current_identity(self.contract),
            "source_version": "CURRENT_A_COMPATIBLE_CONTROLSD_NOT_WHOLE_HISTORICAL_A",
            "anchor_sha256": self.contract["source_a_anchor"]["sha256"], **self.mod.AUTHORITY},
      **{k: self.mod.inspect_capsule(Path(os.environ["F32_CAPSULE_ROOT"]) / k, self.contract, k) for k in ("B1", "B2")},
    }
    lanes["B1"]["anchor_sha256"] = "0" * 64
    with self.assertRaisesRegex(self.mod.BindingError, "^SOURCE_SHA_METADATA_MISMATCH$"):
      self.mod.aggregate(lanes, self.contract)

  def test_suite_source_metadata_spoofing_is_blocked(self):
    payload = json.loads((Path(os.environ["F32_CAPSULE_ROOT"]) / "result.json").read_text())
    for key, value, reason in [
      ("source_version", "HISTORICAL_F19_B1_D94", "SOURCE_VERSION_METADATA_MISMATCH"),
      ("anchor_sha256", "0" * 64, "SOURCE_SHA_METADATA_MISMATCH"),
      ("capture_sha256", "0" * 64, "SOURCE_SHA_METADATA_MISMATCH"),
    ]:
      with self.subTest(field=key):
        suites = deepcopy(payload["suite_results"])
        suites[-1][key] = value
        with self.assertRaisesRegex(self.mod.BindingError, "^" + reason + "$"):
          self.mod.aggregate(payload["lanes"], self.contract, suites)

  def test_aggregate_cannot_omit_actual_suites(self):
    lanes = {
      "A": {"lane": "A", "source_identity": self.mod.verify_current_identity(self.contract),
            "source_version": "CURRENT_A_COMPATIBLE_CONTROLSD_NOT_WHOLE_HISTORICAL_A",
            "anchor_sha256": self.contract["source_a_anchor"]["sha256"], **self.mod.AUTHORITY},
      **{k: self.mod.inspect_capsule(Path(os.environ["F32_CAPSULE_ROOT"]) / k, self.contract, k) for k in ("B1", "B2")},
    }
    with self.assertRaisesRegex(self.mod.BindingError, "^ACTUAL_SUITES_REQUIRED$"):
      self.mod.aggregate(lanes, self.contract)

  def test_existing_f21_exact_capsule_import(self):
    row = self.mod.run_group(self.base, CONTRACT, self.contract, "B1", "f21")
    self.assertEqual(row["counts"], {"passed": 38})
    self.assertEqual(row["test_exit_code"], 0)

  def test_historical_legacy_error_remains_error(self):
    row = self.mod.run_group(self.base, CONTRACT, self.contract, "B1", "legacy")
    self.assertEqual(row["counts"], {"passed": 6, "error": 1})
    self.assertEqual(row["test_exit_code"], 1)

  def test_execution_receipt_mutation_is_rejected(self):
    receipt = self.mod.seal({"lane": "B1", "test_exit_code": 1, "authority": False})
    self.mod.verify_receipt(receipt)
    receipt["test_exit_code"] = 0
    with self.assertRaisesRegex(self.mod.BindingError, "^RESULT_RECEIPT_MISMATCH$"):
      self.mod.verify_receipt(receipt)

  def test_no_capture_call_in_a_compatible_controlsd(self):
    data = (Path(os.environ["F32_SOURCE_REPO"]) / self.contract["anchor"]).read_text()
    self.assertNotIn("capture_native_inputs", data)

def capture_probe(root, native_path=None):
  """One process/one schema root. Never import Controls or a controller."""
  import dataclasses
  import hashlib
  import sys
  root = Path(root).resolve()
  sys.path[:0] = [str(root), str(root / "opendbc_repo")]
  spec = importlib.util.spec_from_file_location(
    "f32_exact_capture_fixture", root / "tools/cyberpilot/tests/test_native_diagnostic_capture_v1.py")
  fixture = importlib.util.module_from_spec(spec)
  spec.loader.exec_module(fixture)
  cases = {
    "pair": (0.2, 0.3), "list": [0.2, 0.3], "integers": (1, 2),
    "set": {0.2, 0.3}, "mapping": {0.2: "a", 0.3: "b"},
    "empty": (), "one": (0.2,), "three": (0.2, 0.3, 0.4),
    "nan": (float("nan"), 0.3), "infinity": (float("inf"), 0.3),
    "boolean": (True, 0.3), "string": ("0.2", 0.3), "none": None,
  }
  outcomes = {}
  for name, value in cases.items():
    try:
      captured = fixture.fixture_capture(native_result=value)
    except (ValueError, TypeError) as error:
      outcomes[name] = {"error": type(error).__name__, "message": str(error)}
    else:
      outcomes[name] = {"native_result": list(captured.native_result),
                        "actuator_hex": captured.actuator_bytes.hex(),
                        "model_sha256": hashlib.sha256(captured.model_message).hexdigest()}
  vectors = [{"pair": [0.2, 0.3], "actuator_hex": "00010203"}]
  kind = "DECLARED_SYNTHETIC_SCALAR_RETURN_FIXTURE"
  native_sha = None
  if native_path:
    raw = Path(native_path).read_bytes()
    data = json.loads(raw)
    if data["source_file_sha256"] != "f2857c1ffac0a7e3f6835cc235c510f0ee979eaaca6b6ace7291f3e00ad13dc1":
      raise ValueError("NATIVE_INPUT_SOURCE_MISMATCH")
    native_sha = hashlib.sha256(raw).hexdigest()
    kind = "ACTUAL_STOCK_NATIVE_FAKE_IO_TRACE_NOT_VEHICLE"
    vectors = [{"pair": r["native_return"][:2],
                "actuator_hex": dict(r["serialized_publications"])["actuators"]} for r in data["rows"]]
  projection = []
  for vector in vectors:
    pair = list(vector["pair"])
    byte_value = bytes.fromhex(vector["actuator_hex"])
    captured = fixture.fixture_capture(native_result=pair, actuator_bytes=byte_value)
    assert captured.native_result == tuple(pair) and captured.actuator_bytes == byte_value
    assert pair == vector["pair"]
    projection.append({"native_result": list(captured.native_result), "actuator_hex": captured.actuator_bytes.hex()})
  value = fixture.fixture_capture()
  frozen = False
  try:
    value.driver_override = True
  except dataclasses.FrozenInstanceError:
    frozen = True
  assert frozen and value.diagnostic_only and value.measurement_qualification == "UNQUALIFIED"
  origins = {}
  for name, module in sys.modules.copy().items():
    if name.startswith(("openpilot", "opendbc")):
      file = getattr(module, "__file__", None)
      if file:
        assert Path(file).resolve().is_relative_to(root), (name, file)
        origins[name] = str(Path(file).relative_to(root))
  assert "openpilot.selfdrive.controls.controlsd" not in sys.modules
  return {"cases": outcomes, "projection": projection, "frozen": frozen, "diagnostic_only": True,
          "runtime_measurement_qualified": False, "controller_imported": False,
          "input_kind": kind, "input_sha256": native_sha, "module_origins": origins}


class TypeFixOracleTests(unittest.TestCase):
  def probe(self, lane):
    import subprocess
    import sys
    command = [sys.executable, "-I", "-B", str(Path(__file__).resolve()), "--capture-probe",
               str(Path(os.environ["F32_CAPSULE_ROOT"]) / lane)]
    native = os.environ.get("F32_NATIVE_TRACE")
    if native:
      command.append(native)
    child = subprocess.run(command, capture_output=True, text=True)
    self.assertEqual(child.returncode, 0, child.stderr)
    return json.loads(child.stdout)

  def test_exact_native_return_and_actuator_bytes_projection(self):
    a, b = self.probe("B1"), self.probe("B2")
    self.assertEqual(a["projection"], b["projection"])
    self.assertEqual(a["input_sha256"], b["input_sha256"])
    self.assertTrue(b["projection"])

  def test_invalid_and_historical_iterable_behaviour_preserved(self):
    a, b = self.probe("B1"), self.probe("B2")
    self.assertEqual(a["cases"], b["cases"])
    for name in ("empty", "one", "three", "nan", "infinity", "boolean", "string", "none"):
      self.assertIn("error", b["cases"][name])

  def test_capture_is_frozen_and_never_imports_controller(self):
    row = self.probe("B2")
    self.assertTrue(row["frozen"])
    self.assertTrue(row["diagnostic_only"])
    self.assertFalse(row["controller_imported"])
    self.assertFalse(row["runtime_measurement_qualified"])


class WorkflowSecurityTests(unittest.TestCase):
  def test_manual_only_and_full_action_pins(self):
    api = HistoricalRoutingTests().api()
    result = api.audit_workflow(ROOT / ".github/workflows/cyberpilot-historical-source-routing-v2.yaml")
    self.assertEqual(result["events"], ["workflow_dispatch"])
    self.assertEqual(result["permissions"], {"contents": "read"})

  def test_automatic_trigger_is_rejected(self):
    api = HistoricalRoutingTests().api()
    path = ROOT / ".github/workflows/cyberpilot-historical-source-routing-v2.yaml"
    with tempfile.TemporaryDirectory() as temp:
      changed = Path(temp) / "bad.yaml"
      changed.write_text(path.read_text().replace("  workflow_dispatch:", "  push:"))
      with self.assertRaisesRegex(api.BindingError, "^WORKFLOW_AUTOMATIC_TRIGGER$"):
        api.audit_workflow(changed)


if __name__ == "__main__":
  if len(sys.argv) > 1 and sys.argv[1] == "--capture-probe":
    print(json.dumps(capture_probe(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None), sort_keys=True))
  else:
    unittest.main()
