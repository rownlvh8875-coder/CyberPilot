"""Candidate publication invariants; no controller/runtime execution."""

from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
DRIVER = ROOT / "tools/cyberpilot/dual_source_publication_v1.py"
CONTRACT = ROOT / "docs/cyberpilot/changes/dual-source-publication-v1.json"


class TestDualSourcePublicationReview(unittest.TestCase):
  def module(self):
    spec = importlib.util.spec_from_file_location("dual_publication_review", DRIVER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

  def test_contract_identity_is_pinned(self):
    module = self.module()
    self.assertEqual(hashlib.sha256(CONTRACT.read_bytes()).hexdigest(), module.CONTRACT_PIN)

  def test_no_runtime_or_publication_authority(self):
    row = json.loads(CONTRACT.read_text())
    for field in ["effective", "promotion_enabled", "runtime_authorized", "performance_qualified", "publication_admitted"]:
      self.assertIs(row[field], False)
    self.assertEqual(row["vehicle_authority"], "NONE")
    self.assertIsNone(row["selected_candidate"])
    self.assertIsNone(row["selected_policy"])

  def test_a_success_cannot_be_reused_as_b(self):
    module = self.module()
    module.configure(Path("/explicit/not-created"))
    a = {"lane": "A", "source_identity": module.A_ID}
    with self.assertRaisesRegex(module.AdmissionError, "LANE_RESULT_BINDING_MISMATCH"):
      module.admit(a, deepcopy(a))

  def test_cli_requires_explicit_evidence_root(self):
    p = subprocess.run([sys.executable, "-I", "-B", str(DRIVER), "--run"], text=True, capture_output=True)
    self.assertNotEqual(p.returncode, 0)
    self.assertIn("EVIDENCE_ROOT_REQUIRED", p.stderr)

  def test_modified_contract_cannot_register_itself(self):
    with tempfile.TemporaryDirectory(prefix="dual-publication-contract-") as directory:
      root = Path(directory)
      script = root / "tools/cyberpilot/dual_source_publication_v1.py"
      contract = root / "docs/cyberpilot/changes/dual-source-publication-v1.json"
      script.parent.mkdir(parents=True)
      contract.parent.mkdir(parents=True)
      script.write_bytes(DRIVER.read_bytes())
      contract.write_bytes(CONTRACT.read_bytes() + b" ")
      p = subprocess.run([sys.executable, "-I", "-B", str(script), "--run", "--evidence-root", str(root / "outside")], text=True, capture_output=True)
      self.assertNotEqual(p.returncode, 0)
      self.assertIn("PUBLICATION_CONTRACT_IDENTITY_MISMATCH", p.stderr)

  def test_inactive_source_versions_remain_distinct(self):
    row = json.loads(CONTRACT.read_text())
    self.assertNotEqual(row["lanes"]["A"]["capsule_identity_sha256"], row["lanes"]["B"]["capsule_identity_sha256"])
    self.assertEqual(row["lanes"]["B"]["source_status"], "INACTIVE_CANDIDATE")


if __name__ == "__main__":
  unittest.main()
