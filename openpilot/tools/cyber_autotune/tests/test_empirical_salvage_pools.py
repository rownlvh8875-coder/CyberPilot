import unittest
from openpilot.tools.cyber_autotune import empirical_salvage_execution as e


def route(rid, segments=10, state="PIPELINE_UNTOUCHED_PROVABLE"):
  return {
    "route_id": rid,
    "segment_count": segments,
    "prior_use_state": state,
    "metadata_complete": True,
    "source_compatible": True,
    "required_messages": True,
    "exact_source": True,
    "source_class_sha256": "c" * 64,
    "full_carparams_sha256": "d" * 64,
    "lineage_sha256": "e" * 64,
  }


class TestSalvagePools(unittest.TestCase):
  def test_largest_complete_candidate_reserved(self):
    self.assertEqual(e.reservation_candidate([route("a", 4), route("b", 6)])["route_id"], "b")

  def test_lexical_tie(self):
    self.assertEqual(e.reservation_candidate([route("b"), route("a")])["route_id"], "a")

  def test_unknown_use_not_holdout(self):
    self.assertIsNone(e.reservation_candidate([route("a", state="PRIOR_USE_UNKNOWN")]))

  def test_prior_numeric_not_holdout(self):
    self.assertIsNone(e.reservation_candidate([route("a", state="USED_NUMERIC_TRAIN")]))

  def test_missing_messages_not_holdout(self):
    r = route("a")
    r["required_messages"] = False
    self.assertIsNone(e.reservation_candidate([r]))

  def test_source_incompatible_not_holdout(self):
    r = route("a")
    r["source_compatible"] = False
    self.assertIsNone(e.reservation_candidate([r]))

  def test_metadata_incomplete_not_holdout(self):
    r = route("a")
    r["metadata_complete"] = False
    self.assertIsNone(e.reservation_candidate([r]))

  def test_null_lineage_not_holdout(self):
    r = route("a")
    r["lineage_sha256"] = None
    self.assertIsNone(e.reservation_candidate([r]))

  def test_engineering_seal_stays_closed(self):
    x = e.reservation(route("a" * 64), "b" * 64)
    self.assertEqual(x["opening_count"], 0)
    self.assertEqual(x["opening_state"], "CLOSED")
    self.assertFalse(x["numeric_opened"])
    self.assertFalse(x["independent_qualification_allowed"])

  def test_no_candidate_no_reservation(self):
    self.assertIsNone(e.reservation(None, "b" * 64))

  def test_mapping_is_future_only_nonexecutable(self):
    x = e.future_mapping()
    self.assertEqual(x["scope"], "FUTURE_GENERATIONS_ONLY")
    self.assertFalse(x["numeric_extraction_executed"])
    self.assertFalse(x["production_observer_implemented"])

  def test_two_incompatible_singleton_pools_not_sufficient(self):
    self.assertFalse(e.train_dev_sufficient({('a',): ['r1'], ('b',): ['r2']}))

  def test_two_same_pool_routes_sufficient(self):
    self.assertTrue(e.train_dev_sufficient({('a',): ['r1', 'r2']}))

  def test_unattested_store_reconciliation_blocks_closure(self):
    self.assertIn('LEGACY_NON_EMPIRICAL_PRIVATE_RECEIPT_ROUTE_ALIAS_RECONCILIATION_INCOMPLETE', e.completeness_blockers({}, []))

  def test_positive_closure_attestations_remove_specific_blockers(self):
    self.assertEqual(
      e.completeness_blockers({'carrot_simulator_evidence_registry_complete': True, 'legacy_route_alias_reconciliation_complete': True}, []), []
    )
