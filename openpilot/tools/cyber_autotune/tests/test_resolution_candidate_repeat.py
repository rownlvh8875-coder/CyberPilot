import copy
import unittest

from openpilot.tools.cyber_autotune import resolution_candidate_repeat as r
from openpilot.tools.cyber_autotune.native_protocol import canonical, digest


class TestHistoricalRecovery(unittest.TestCase):
  def test_no_new_search(self):
    cases = r.archived_cases()
    self.assertEqual(len(cases), 70)
    self.assertEqual(sum(c['role'] == 'EVALUATION' for c in cases), 11)
    self.assertEqual(sum(c['role'] == 'DEVELOPMENT' for c in cases), 36)
    self.assertEqual(sum(c['role'] == 'STRESS' for c in cases), 23)

  def test_existing_configs_only(self):
    self.assertEqual(len({canonical(c['config']) for c in r.archived_cases() if c['role'] == 'DEVELOPMENT'}), 9)

  def test_archive_sha_binding(self):
    with self.assertRaises(ValueError):
      r.checked({'receipt_sha256': '0' * 64}, '0' * 64)

  def test_relocation_copy_only(self):
    x = {'native': {'source': {'root': 'new', 'head': 'abc'}}}
    before = copy.deepcopy(x)
    y = r.original_request(x)
    self.assertEqual(y['native']['source']['root'], r.ORIGINAL_ROOT)
    self.assertEqual(x, before)

  def test_relocation_cannot_change_source(self):
    x = {'native': {'source': {'root': 'new', 'head': 'abc'}}}
    self.assertEqual(r.original_request(x)['native']['source']['head'], 'abc')

  def test_request_drift_rejected(self):
    from openpilot.tools.cyber_autotune import curvature_yaw_v2_search as s

    old = r.archived_cases()[0]
    c = s.build_case(old['scenario'], old['config'], role=old['role'], selection_sha256=old['selection_sha256'])
    with self.assertRaises(ValueError):
      r.verify_reconstruction(c, old)

  def test_immutable_local_write(self):
    from pathlib import Path
    import tempfile

    with tempfile.TemporaryDirectory() as d:
      p = Path(d) / 'row.json'
      r.immutable(p, b'first')
      r.immutable(p, b'first')
      with self.assertRaises(ValueError):
        r.immutable(p, b'second')
      self.assertEqual(p.read_bytes(), b'first')

  def test_receipt_hash_rejects_rehashed_semantics(self):
    d = {'value': 1}
    d['receipt_sha256'] = digest(canonical(d))
    r.checked(d, d['receipt_sha256'])
    d['value'] = 2
    with self.assertRaises(ValueError):
      r.checked(d, d['receipt_sha256'])

  def test_published_reader_cannot_claim_legacy_execution(self):
    from unittest.mock import patch
    from pathlib import Path
    import tempfile

    self.assertNotEqual(r.SOURCE_SHA, r.HISTORICAL_EXECUTOR_SHA)
    plan = r.PUBLIC / 'measurement-resolution-candidate-execution-policy-v1.json'
    with tempfile.TemporaryDirectory() as tmp:
      with (
        patch.object(r.s, 'build_case', side_effect=AssertionError('no execution')),
        patch.object(r.s, 'run_case', side_effect=AssertionError('no execution')),
      ):
        with self.assertRaisesRegex(ValueError, 'EXECUTOR_SOURCE_DRIFT'):
          r.execute(plan, Path(tmp), r.PUBLIC)
