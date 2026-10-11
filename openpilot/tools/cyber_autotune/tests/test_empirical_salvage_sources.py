import copy
import unittest
from openpilot.tools.cyber_autotune import empirical_salvage_sources as s


def source():
  return {
    "complete": True,
    "public_available": True,
    "dirty": False,
    "files": {"logger": {"normalized_source_sha256": "a"}, "card": {"normalized_source_sha256": "b"}},
    "closure": {"x": "a"},
  }


class TestSalvageSources(unittest.TestCase):
  def test_exact_relevant_equality(self):
    self.assertEqual(s.compare(source(), source()), "SOURCE_EQUIVALENT")

  def test_relevant_difference_not_equivalent(self):
    b = source()
    b["files"]["card"]["normalized_source_sha256"] = "c"
    self.assertEqual(s.compare(source(), b), "SOURCE_ADAPTER_REQUIRED")

  def test_logger_difference_no_generic_adapter(self):
    b = source()
    b["files"]["logger"]["normalized_source_sha256"] = "c"
    self.assertEqual(s.compare(source(), b), "NOT_EQUIVALENT")

  def test_dependency_difference_not_equivalent(self):
    b = source()
    b["closure"]["x"] = "b"
    self.assertEqual(s.compare(source(), b), "SOURCE_ADAPTER_REQUIRED")

  def test_incomplete_no_equivalence(self):
    b = source()
    b["complete"] = False
    self.assertEqual(s.compare(source(), b), "SOURCE_AUDIT_PARTIAL")

  def test_dirty_not_clean(self):
    b = source()
    b["dirty"] = True
    self.assertEqual(s.compare(source(), b), "SOURCE_AUDIT_PARTIAL")

  def test_public_unavailable(self):
    b = source()
    b["public_available"] = False
    self.assertEqual(s.compare(source(), b), "SOURCE_AUDIT_PARTIAL")

  def test_role_set_difference(self):
    b = source()
    del b["files"]["card"]
    self.assertEqual(s.compare(source(), b), "NOT_EQUIVALENT")

  def test_schema_drift_not_equivalence(self):
    a = source()
    a["files"]["schema_log"] = {"normalized_source_sha256": "a"}
    b = copy.deepcopy(a)
    b["files"]["schema_log"]["normalized_source_sha256"] = "b"
    self.assertEqual(s.compare(a, b), "NOT_EQUIVALENT")

  def test_invalid_python_encoding_is_partial_not_guessed(self):
    row = s.safe_entry("source.py", bytes([0x88]))
    self.assertIsNone(row["normalized_source_sha256"])
    self.assertEqual(row["parse_status"], "SOURCE_AST_UNAVAILABLE")
