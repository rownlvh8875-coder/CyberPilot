"""Real file/contract negative controls. No Native controller or actuation."""

from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
CONTRACT = ROOT / "docs/cyberpilot/changes/capture-only-source-version-v1.json"
VALIDATOR = ROOT / "tools/cyberpilot/source_version_contract_v1.py"
ANCHOR = "openpilot/selfdrive/controls/controlsd.py"
A = "SOURCE_A_HEAD_51C1CDB3_V1"
B = "SOURCE_B_F19_CAPTURE_ONLY_LOCAL_V1"


class TestSourceVersionContract(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.document = json.loads(CONTRACT.read_bytes())
    cls.workspace = tempfile.TemporaryDirectory(prefix="f21-source-tests-")
    cls.base = Path(cls.workspace.name) / "base"
    required = set(cls.document["immutable_source_dependencies"]) | set(cls.document["frozen_source_sha256"])
    required |= set(cls.document["historical_receipts"]) | set(cls.document["modified_file_sha256"])
    required.update(
      [
        "docs/cyberpilot/changes/track-f7-offline-multiobjective-contract.json",
        "docs/cyberpilot/changes/track-f9-f8-evidence-contract-v1.json",
        "docs/cyberpilot/changes/empirical-hurdle-stage1-v4-e2-canonical-native-bounded-contract-v1.json",
      ]
    )
    for name in required:
      target = cls.base / name
      target.parent.mkdir(parents=True, exist_ok=True)
      shutil.copyfile(ROOT / name, target)
    cls.old_anchor = subprocess.check_output(["git", "show", cls.document["original_git_head"] + ":" + ANCHOR], cwd=ROOT)
    if hashlib.sha256(cls.old_anchor).hexdigest() != "f2857c1ffac0a7e3f6835cc235c510f0ee979eaaca6b6ace7291f3e00ad13dc1":
      raise AssertionError("HISTORICAL_GIT_OBJECT_UNAVAILABLE")
    cls.api = None

  @classmethod
  def tearDownClass(cls):
    cls.workspace.cleanup()

  def setUp(self):
    self.case = tempfile.TemporaryDirectory(prefix="f21-case-")
    self.root = Path(self.case.name) / "source"
    shutil.copytree(self.base, self.root)
    self.contract = Path(self.case.name) / "contract.json"
    shutil.copyfile(CONTRACT, self.contract)

  def tearDown(self):
    self.case.cleanup()

  def api_for_test(self):
    self.assertTrue(VALIDATOR.is_file(), "F21 validator implementation is not yet present")
    if self.__class__.api is None:
      spec = importlib.util.spec_from_file_location("f21_validator_under_test", VALIDATOR)
      module = importlib.util.module_from_spec(spec)
      spec.loader.exec_module(module)
      self.__class__.api = module
    return self.__class__.api

  def validate(self, version=B, root=None, contract=None):
    return self.api_for_test().validate_source_version(root or self.root, contract or self.contract, version)

  def blocked(self, code, *, version=B, root=None, contract=None):
    api = self.api_for_test()
    with self.assertRaises(api.SourceVersionError) as caught:
      self.validate(version, root=root, contract=contract)
    self.assertEqual(str(caught.exception), code)

  def make_source_a(self):
    (self.root / ANCHOR).write_bytes(self.old_anchor)
    for name in self.document["source_a_absent_files"]:
      (self.root / name).unlink()

  def changed_contract(self, change):
    document = deepcopy(self.document)
    change(document)
    self.contract.write_text(json.dumps(document, sort_keys=True))

  def test_source_b_exact_valid(self):
    result = self.validate()
    self.assertEqual(result["status"], "STRUCTURALLY_VALID")
    self.assertEqual(result["source_version"], B)
    self.assertFalse(result["runtime_authorized"])
    self.assertFalse(result["performance_qualified"])
    self.assertFalse(result["effective"])
    self.assertEqual(result["vehicle_authority"], "NONE")
    self.assertIn("UNRESOLVED ERROR", result["legacy_source_publication"])

  def test_source_a_explicit_version_valid(self):
    self.make_source_a()
    self.assertEqual(self.validate(A)["source_version"], A)

  def test_wrong_version_cannot_relabel_current_source(self):
    self.blocked("SOURCE_FILE_HASH_MISMATCH", version=A)

  def test_source_b_cannot_accept_source_a(self):
    self.make_source_a()
    self.blocked("SOURCE_FILE_HASH_MISMATCH")

  def test_unknown_version_rejected(self):
    self.blocked("SOURCE_VERSION_UNKNOWN", version="LATEST")

  def test_each_modified_source_file_tamper_rejected(self):
    for name in self.document["modified_file_sha256"]:
      with self.subTest(path=name):
        target = self.root / name
        before = target.read_bytes()
        target.write_bytes(before + b"\n# isolated mutation\n")
        self.blocked("SOURCE_FILE_HASH_MISMATCH")
        target.write_bytes(before)

  def test_missing_source_file_rejected(self):
    (self.root / ANCHOR).unlink()
    self.blocked("REQUIRED_FILE_MISSING")

  def test_dependency_mutation_rejected(self):
    target = self.root / "openpilot/tools/cyber_autotune/candidate_architecture_publication.py"
    target.write_bytes(target.read_bytes() + b"\n# isolated mutation\n")
    self.blocked("SOURCE_DEPENDENCY_MISMATCH")

  def test_missing_dependency_rejected(self):
    (self.root / "openpilot/tools/cyber_autotune/candidate_architecture_probe.py").unlink()
    self.blocked("REQUIRED_FILE_MISSING")

  def test_frozen_file_mutation_rejected(self):
    target = self.root / ".gitattributes"
    target.write_bytes(target.read_bytes() + b"\n# isolated mutation\n")
    self.blocked("FROZEN_SOURCE_MISMATCH")

  def test_historical_receipt_tamper_rejected(self):
    target = self.root / "docs/cyberpilot/changes/candidate-architecture-decision-v1.json"
    target.write_bytes(target.read_bytes() + b" ")
    self.blocked("HISTORICAL_RECEIPT_MISMATCH")

  def test_preserved_evaluation_contracts_cannot_be_changed(self):
    for name in [
      "docs/cyberpilot/changes/track-f7-offline-multiobjective-contract.json",
      "docs/cyberpilot/changes/track-f9-f8-evidence-contract-v1.json",
      "docs/cyberpilot/changes/empirical-hurdle-stage1-v4-e2-canonical-native-bounded-contract-v1.json",
    ]:
      with self.subTest(path=name):
        target = self.root / name
        before = target.read_bytes()
        target.write_bytes(before + b" ")
        try:
          self.blocked("SOURCE_DEPENDENCY_MISMATCH")
        finally:
          target.write_bytes(before)

  def test_contract_hash_tamper_rejected(self):
    self.contract.write_bytes(self.contract.read_bytes() + b" ")
    self.blocked("CONTRACT_IDENTITY_MISMATCH")

  def test_contract_source_hash_rewrite_does_not_admit_mutation(self):
    target = self.root / ANCHOR
    target.write_bytes(target.read_bytes() + b"\n# changed source\n")
    forged_sha = hashlib.sha256(target.read_bytes()).hexdigest()
    self.changed_contract(lambda row: row["modified_file_sha256"].__setitem__(ANCHOR, forged_sha))
    self.blocked("CONTRACT_IDENTITY_MISMATCH")

  def test_all_authority_escalations_rejected(self):
    alterations = {
      "runtime_authorized": True,
      "effective": True,
      "diagnostic_only": False,
      "promotion_enabled": True,
      "performance_qualified": True,
      "vehicle_authority": "CONTROL",
      "selected_candidate": "B",
      "selected_policy": "ACTIVE",
      "historical_receipts_unchanged": False,
    }
    for field, value in alterations.items():
      with self.subTest(field=field):
        self.changed_contract(lambda row, k=field, v=value: row.__setitem__(k, v))
        self.blocked("CONTRACT_IDENTITY_MISMATCH")
    shutil.copyfile(CONTRACT, self.contract)

  def test_schema_guard_does_not_qualify_authority(self):
    api = self.api_for_test()
    doc = deepcopy(self.document)
    doc["runtime_authorized"] = True
    with self.assertRaisesRegex(api.SourceVersionError, "^AUTHORITY_INVARIANT$"):
      api.validate_contract_schema(doc)

  def test_schema_guard_rejects_unknown_fields(self):
    doc = deepcopy(self.document)
    doc["accept_any_sha"] = True
    with self.assertRaisesRegex(self.api_for_test().SourceVersionError, "^CONTRACT_SCHEMA$"):
      self.api_for_test().validate_contract_schema(doc)

  def test_schema_guard_rejects_wrong_metadata_types(self):
    api = self.api_for_test()
    for key, value in [("identity_semantics", None), ("source_a_absent_files", [{}, {}])]:
      with self.subTest(field=key):
        doc = deepcopy(self.document)
        doc[key] = value
        with self.assertRaisesRegex(api.SourceVersionError, "^CONTRACT_SCHEMA$"):
          api.validate_contract_schema(doc)

  def test_duplicate_json_key_rejected(self):
    self.contract.write_text('{"schema_version":1,"schema_version":2}')
    self.blocked("DUPLICATE_JSON_KEY")

  def test_malformed_json_rejected(self):
    self.contract.write_text("{")
    self.blocked("INVALID_CONTRACT_JSON")

  def test_nonfinite_json_rejected(self):
    for payload in ['{"x":NaN}', '{"x":Infinity}', '{"x":1e999}']:
      with self.subTest(payload=payload):
        self.contract.write_text(payload)
        self.blocked("NONFINITE_JSON")

  def test_oversized_integer_returns_structured_api_rejection(self):
    self.contract.write_text('{"n":' + "9" * 5000 + "}")
    self.blocked("INVALID_CONTRACT_JSON")

  def test_oversized_integer_returns_structured_cli_rejection(self):
    self.contract.write_text('{"n":' + "9" * 5000 + "}")
    result = subprocess.run(
      [sys.executable, "-B", str(VALIDATOR), "--source-root", str(self.root), "--contract", str(self.contract), "--source-version", B],
      text=True,
      capture_output=True,
    )
    self.assertEqual(result.returncode, 2, result.stderr)
    row = json.loads(result.stdout)
    self.assertEqual(row["status"], "STRUCTURALLY_BLOCKED")
    self.assertEqual(row["reason"], "INVALID_CONTRACT_JSON")
    self.assertFalse(row["runtime_authorized"])

  def test_nul_in_explicit_source_root_rejected(self):
    self.blocked("UNSAFE_PATH", root=Path(str(self.root) + chr(0)))

  def test_nul_in_explicit_contract_path_rejected(self):
    self.blocked("UNSAFE_PATH", contract=Path(str(self.contract) + chr(0)))

  def test_oversize_contract_rejected(self):
    self.contract.write_bytes(b" " * (self.api_for_test().MAX_CONTRACT_BYTES + 1))
    self.blocked("FILE_SIZE_LIMIT")

  def test_symlink_file_rejected(self):
    path = self.root / ANCHOR
    original = path.read_bytes()
    other = Path(self.case.name) / "elsewhere.py"
    other.write_bytes(original)
    path.unlink()
    path.symlink_to(other)
    self.blocked("UNSAFE_PATH")

  def test_symlink_parent_rejected(self):
    original = self.root / "openpilot/selfdrive/controls"
    other = Path(self.case.name) / "controls"
    original.rename(other)
    original.symlink_to(other, target_is_directory=True)
    self.blocked("UNSAFE_PATH")

  def test_special_file_rejected_without_blocking_read(self):
    import os

    path = self.root / ANCHOR
    path.unlink()
    os.mkfifo(path)
    self.blocked("NON_REGULAR_FILE")

  def test_relative_root_rejected(self):
    self.blocked("ABSOLUTE_PATH_REQUIRED", root=Path("."))

  def test_parent_traversal_rejected(self):
    self.blocked("UNSAFE_PATH", root=self.root / ".." / "source")

  def test_source_a_rejects_candidate_file_present(self):
    self.make_source_a()
    target = self.root / self.document["source_a_absent_files"][0]
    target.write_text("# unexpected source B file")
    self.blocked("UNEXPECTED_SOURCE_FILE_FOR_A", version=A)

  def test_input_bytes_not_modified(self):
    paths = [self.root / ANCHOR, self.contract]
    before = [p.read_bytes() for p in paths]
    self.validate()
    self.assertEqual([p.read_bytes() for p in paths], before)

  def test_repeated_result_has_same_canonical_bytes(self):
    first = json.dumps(self.validate(), sort_keys=True, separators=(",", ":"))
    second = json.dumps(self.validate(), sort_keys=True, separators=(",", ":"))
    self.assertEqual(first, second)

  def test_cli_requires_explicit_version(self):
    self.api_for_test()
    result = subprocess.run(
      [sys.executable, "-B", str(VALIDATOR), "--source-root", str(self.root), "--contract", str(self.contract)],
      text=True,
      capture_output=True,
    )
    self.assertNotEqual(result.returncode, 0)

  def test_cli_reports_blocked_unknown_version_without_authority(self):
    self.api_for_test()
    result = subprocess.run(
      [sys.executable, "-B", str(VALIDATOR), "--source-root", str(self.root), "--contract", str(self.contract), "--source-version", "LATEST"],
      text=True,
      capture_output=True,
    )
    self.assertEqual(result.returncode, 2)
    row = json.loads(result.stdout)
    self.assertEqual(row["status"], "STRUCTURALLY_BLOCKED")
    self.assertEqual(row["reason"], "SOURCE_VERSION_UNKNOWN")
    self.assertFalse(row["runtime_authorized"])

  def test_cli_exact_source_b_is_diagnostic_only(self):
    self.api_for_test()
    result = subprocess.run(
      [sys.executable, "-B", str(VALIDATOR), "--source-root", str(self.root), "--contract", str(self.contract), "--source-version", B],
      text=True,
      capture_output=True,
    )
    self.assertEqual(result.returncode, 0, result.stderr)
    self.assertEqual(json.loads(result.stdout)["status"], "STRUCTURALLY_VALID")
    self.assertIn("UNRESOLVED ERROR", result.stdout)

  def test_original_verifier_accepts_a_and_rejects_b(self):
    self.api_for_test()
    code = (
      "import sys;from pathlib import Path;sys.path.insert(0,sys.argv[1]);"
      + "from openpilot.tools.cyber_autotune import candidate_architecture_publication as p;"
      + "assert p.a.ROOT==Path(sys.argv[1]);p.validate_sources(p.load())"
    )
    b = subprocess.run([sys.executable, "-I", "-B", "-c", code, str(self.root)], text=True, capture_output=True)
    self.assertNotEqual(b.returncode, 0)
    self.assertIn("INJECTION_SOURCE_DRIFT", b.stderr)
    self.make_source_a()
    a = subprocess.run([sys.executable, "-I", "-B", "-c", code, str(self.root)], text=True, capture_output=True)
    self.assertEqual(a.returncode, 0, a.stderr)


if __name__ == "__main__":
  unittest.main()
