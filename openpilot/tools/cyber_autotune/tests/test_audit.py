from dataclasses import FrozenInstanceError, fields, replace
import unittest

from openpilot.tools.cyber_autotune.audit import AuditEvent, AuditRecord, append_event, verify_chain


def started():
  return AuditEvent(0, '1' * 64, '2' * 64, '3' * 64, '4' * 64, '5' * 64, '6' * 64,
                    'STARTED', ('SYNTHETIC_ONLY',), '0' * 64)


def terminal(chain, status='COMPLETED'):
  return replace(started(), sequence=1, previous_sha256=chain[-1].sha256, status=status)


class TestAuditChain(unittest.TestCase):
  def test_start_and_terminal_are_deterministic_immutable_records(self):
    chain = append_event((), started())
    finished = append_event(chain, terminal(chain))
    self.assertTrue(verify_chain(()))
    self.assertTrue(verify_chain(chain))
    self.assertTrue(verify_chain(finished))
    self.assertEqual(len(chain), 1)
    self.assertEqual(len(finished), 2)
    self.assertEqual(finished, append_event(append_event((), started()), terminal(chain)))
    self.assertEqual(finished[1].event.previous_sha256, chain[0].sha256)
    self.assertNotEqual(finished[0].sha256, finished[1].sha256)
    with self.assertRaises(FrozenInstanceError):
      chain[0].event.status = 'COMPLETED'

  def test_failure_and_timeout_are_preserved_terminal_outcomes(self):
    for status in ('BLOCKED', 'FAILED', 'TIMEOUT', 'STRUCTURAL_PREVIEW', 'COMPLETED'):
      chain = append_event((), started())
      finished = append_event(chain, terminal(chain, status))
      self.assertEqual(finished[-1].event.status, status)
      self.assertTrue(verify_chain(finished))
      with self.assertRaises(ValueError):
        append_event(finished, replace(terminal(finished), sequence=2))

  def test_genesis_must_start_at_zero_with_genesis_hash(self):
    for changes in ({'sequence': 1}, {'sequence': True}, {'sequence': 0.}, {'sequence': -1},
                    {'previous_sha256': '7' * 64}, {'status': 'COMPLETED'}, {'status': 'PASS'}):
      with self.assertRaises(ValueError):
        append_event((), replace(started(), **changes))

  def test_restart_gap_and_incorrect_previous_hash_are_rejected(self):
    chain = append_event((), started())
    for changes in ({'sequence': 0}, {'sequence': 2}, {'previous_sha256': '7' * 64}, {'status': 'STARTED'}):
      with self.assertRaises(ValueError):
        append_event(chain, replace(terminal(chain), **changes))

  def test_run_and_all_bound_identities_cannot_change_midchain(self):
    chain = append_event((), started())
    for item in fields(started()):
      if item.name.endswith('_sha256') and item.name != 'previous_sha256':
        with self.subTest(field=item.name), self.assertRaises(ValueError):
          append_event(chain, replace(terminal(chain), **{item.name: '9' * 64}))

  def test_changed_record_content_digest_and_order_are_detected(self):
    chain = append_event((), started())
    finished = append_event(chain, terminal(chain))
    for corrupt in (tuple(reversed(finished)), (finished[1],),
                    (replace(chain[0], sha256='9' * 64),),
                    (replace(chain[0], event=replace(started(), reasons=('EDITED',))),)):
      self.assertFalse(verify_chain(corrupt))
      with self.assertRaises(ValueError):
        append_event(corrupt, terminal(finished))

  def test_digest_fields_require_exact_sha256(self):
    for item in fields(started()):
      if item.name.endswith('_sha256'):
        for value in ('', None, 'A' * 64, [], 'x' * 64):
          with self.subTest(field=item.name), self.assertRaises(ValueError):
            append_event((), replace(started(), **{item.name: value}))

  def test_reasons_are_unique_codes_not_raw_paths_or_free_text(self):
    for reasons in ((), [], ('A', 'A'), ('/mnt/d/private/rlog',), ('raw data here',),
                    ('X\nSECRET',), (None,), ('',), ('X' * 129,)):
      with self.subTest(reasons=reasons), self.assertRaises(ValueError):
        append_event((), replace(started(), reasons=reasons))

  def test_invalid_input_shapes_fail_closed(self):
    for value in (None, [], {}, True, 'chain'):
      self.assertFalse(verify_chain(value))
      with self.assertRaises(ValueError):
        append_event(value, started())
      with self.assertRaises(ValueError):
        append_event((), value)
    for value in ((None,), (AuditRecord(None, '1' * 64),), (AuditRecord(started(), None),)):
      self.assertFalse(verify_chain(value))

  def test_same_event_in_other_run_has_different_identity(self):
    first = append_event((), started())
    other = append_event((), replace(started(), run_sha256='9' * 64))
    self.assertNotEqual(first[0].sha256, other[0].sha256)


if __name__ == '__main__':
  unittest.main()
