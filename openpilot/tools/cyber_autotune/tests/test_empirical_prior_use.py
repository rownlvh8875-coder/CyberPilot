from pathlib import Path
import tempfile
import unittest
from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_prior_use as u


class TestPriorUse(unittest.TestCase):
  def test_explicit_store_only(self):
    with tempfile.TemporaryDirectory() as t:
      with self.assertRaisesRegex(ValueError, "EXPLICIT_STORE"):
        u.safe_path(Path(t), [], "split.json")

  def test_parent_traversal_rejected(self):
    with tempfile.TemporaryDirectory() as t:
      with self.assertRaisesRegex(ValueError, "PATH_ESCAPE"):
        u.safe_path(Path(t), [Path(t)], "../other.json")

  def test_absolute_child_rejected(self):
    with tempfile.TemporaryDirectory() as t:
      with self.assertRaisesRegex(ValueError, "PATH_ESCAPE"):
        u.safe_path(Path(t), [Path(t)], str(Path(t) / "split.json"))

  def test_symlink_rejected(self):
    with tempfile.TemporaryDirectory() as t:
      root = Path(t)
      (root / "a").symlink_to(root / "b")
      with self.assertRaisesRegex(ValueError, "SYMLINK"):
        u.safe_path(root, [root], "a")

  def test_raw_name_never_opened(self):
    with tempfile.TemporaryDirectory() as t:
      with self.assertRaisesRegex(ValueError, "RECEIPT_ALLOWLIST"):
        u.read_receipt(Path(t), [Path(t)], "rlog.zst")

  def test_numeric_cache_never_opened(self):
    with tempfile.TemporaryDirectory() as t:
      with self.assertRaisesRegex(ValueError, "RECEIPT_ALLOWLIST"):
        u.read_receipt(Path(t), [Path(t)], "segments/route/x.json")

  def test_unknown_json_not_opened(self):
    with tempfile.TemporaryDirectory() as t:
      with self.assertRaisesRegex(ValueError, "RECEIPT_ALLOWLIST"):
        u.read_receipt(Path(t), [Path(t)], "unknown.json")

  def test_opening_receipt_verified(self):
    with tempfile.TemporaryDirectory() as t:
      root = Path(t)
      row = p.seal({"schema": "EMPIRICAL_HOLDOUT_OPENED_V1"})
      (root / "holdout-opening.json").write_bytes(p.canonical(row))
      self.assertEqual(u.read_receipt(root, [root], "holdout-opening.json"), row)

  def test_receipt_digest_conflict(self):
    with tempfile.TemporaryDirectory() as t:
      root = Path(t)
      (root / "split.json").write_text('{"receipt_sha256":"bad"}')
      with self.assertRaisesRegex(ValueError, "CORRUPT"):
        u.read_receipt(root, [root], "split.json")

  def test_registry_complete_needs_simulator(self):
    self.assertFalse(u.closure_complete({"carrot_simulator_evidence_registry_complete": False}, []))

  def test_unmapped_receipt_prevents_complete(self):
    self.assertFalse(u.closure_complete({"carrot_simulator_evidence_registry_complete": True}, ["UNKNOWN"]))

  def test_known_complete_closure(self):
    self.assertTrue(u.closure_complete({"carrot_simulator_evidence_registry_complete": True}, []))

  def test_holdout_priority_over_train(self):
    from openpilot.tools.cyber_autotune import empirical_salvage_policy as s

    self.assertEqual(s.prior_state([{"holdout_used": True}, {"fitting_used": True}], True, True), "USED_HOLDOUT")

  def test_global_untouched_never_claimed(self):
    from openpilot.tools.cyber_autotune import empirical_salvage_policy as s

    self.assertFalse(s.policy()["global_never_analyzed_claim"])
