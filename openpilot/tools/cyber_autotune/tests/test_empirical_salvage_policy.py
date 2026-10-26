"""Predeclared salvage policy and false-untouched rejection."""

import unittest
from openpilot.tools.cyber_autotune import empirical_salvage_policy as s


class TestSalvagePolicy(unittest.TestCase):
  def test_primary_ranking_is_metadata_only(self):
    rows = [
      {
        "generation_id": str(i),
        "generation": {"source_commit": f"{i:040x}"},
        "status_counts": {"ROUTE_DIFFERENT_SOURCE_GENERATION": i % 3},
        "segment_count": 20 - i,
      }
      for i in range(15)
    ]
    result = s.select_sources(rows, set())
    self.assertEqual(len(result), 10)
    self.assertEqual(result[0]["metadata_complete_routes"], 2)
    self.assertEqual(result[0]["source_commit"], f"{2:040x}")

  def test_previously_audited_excluded(self):
    rows = [
      {
        "generation_id": "x",
        "generation": {"source_commit": "a" * 40},
        "status_counts": {"ROUTE_DIFFERENT_SOURCE_GENERATION": 2},
        "segment_count": 30,
      }
    ]
    self.assertEqual(s.select_sources(rows, {"a" * 40}), [])

  def test_policy_no_authority(self):
    row = s.policy()
    self.assertFalse(row["numeric_opening_allowed"])
    self.assertFalse(row["holdout_opening_allowed"])
    self.assertEqual(row["untouched_scope"], "CYBERPILOT_PIPELINE_UNTOUCHED")
    self.assertEqual(row["maximum_additional_generations"], 10)

  def test_unknown_store_closure_prevents_untouched(self):
    self.assertEqual(s.prior_state([], False, True), "PRIOR_USE_UNKNOWN")

  def test_positive_numeric_use_overrides_metadata(self):
    self.assertEqual(s.prior_state([{"numeric_opened": True, "fitting_used": True, "role": "TRAIN"}], True, True), "USED_NUMERIC_TRAIN")

  def test_complete_metadata_only_can_be_pipeline_untouched(self):
    self.assertEqual(
      s.prior_state(
        [
          {
            "metadata_opened": True,
            "numeric_opened": False,
            "fitting_used": False,
            "selection_used": False,
            "evaluation_used": False,
            "holdout_used": False,
          }
        ],
        True,
        True,
      ),
      "PIPELINE_UNTOUCHED_PROVABLE",
    )

  def test_incomplete_identity_never_untouched(self):
    self.assertEqual(s.prior_state([], True, False), "SOURCE_IDENTITY_AMBIGUOUS")

  def test_engineering_holdout_not_independent(self):
    row = s.engineering_contract()
    self.assertFalse(row["independent_qualification_allowed"])
    self.assertEqual(row["opening_state"], "CLOSED")
    self.assertEqual(row["opening_count"], 0)
