from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError, replace
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from openpilot.tools.cyber_autotune import archive
from openpilot.tools.cyber_autotune.archive_codec import encode_proposal
from openpilot.tools.cyber_autotune.audit import append_event
from openpilot.tools.cyber_autotune.preview_job import inspect_preview, persist_preview
from openpilot.tools.cyber_autotune.tests.test_profiles import proposal
from openpilot.tools.cyber_autotune.tests.test_search import grid


EVALUATOR = '7' * 64


def template():
  return replace(proposal(), proposed_value=2.3)


class TestPreviewJob(unittest.TestCase):
  def setUp(self):
    temporary = tempfile.TemporaryDirectory()
    self.addCleanup(temporary.cleanup)
    self.root = Path(temporary.name)

  def run_job(self, root=None, p=None, g=None, evaluator=EVALUATOR):
    return persist_preview(str(root or self.root), template() if p is None else p,
                           grid() if g is None else g, evaluator_sha256=evaluator)

  def inspect(self):
    return inspect_preview(str(self.root), template(), grid(), evaluator_sha256=EVALUATOR)

  def snapshot(self):
    return {p.name: (p.stat().st_ino, p.read_bytes()) for p in self.root.iterdir()}

  def test_invalid_requests_touch_no_archive(self):
    cases = [(None, grid(), EVALUATOR), (template(), None, EVALUATOR), (template(), grid(), True),
             (template(), grid(), 'x'), (proposal(), grid(), EVALUATOR),
             (replace(template(), name='steer_max'), grid(), EVALUATOR),
             (template(), replace(grid(), values=(2.2, 2.4)), EVALUATOR),
             (template(), replace(grid(), values=(2.3, 2.5)), EVALUATOR),
             (template(), replace(grid(), values=(float('nan'),)), EVALUATOR)]
    for p, g, evaluator in cases:
      for function in (persist_preview, inspect_preview):
        with self.subTest(function=function.__name__, p=p, g=g), \
             patch.object(archive, '_directory', side_effect=AssertionError('Invalid input accessed archive')):
          result = function(str(self.root), p, g, evaluator_sha256=evaluator)
          self.assertEqual(result.status, 'BLOCKED')
          self.assertIsNone(result.run_sha256)
          self.assertIsNone(result.preview_sha256)
          self.assertEqual(result.profile_sha256s, ())
    self.assertEqual(list(self.root.iterdir()), [])

  def test_complete_job_reopens_exact_order_and_false_authority(self):
    initial = self.inspect()
    self.assertEqual(initial.status, 'NOT_STARTED')
    self.assertEqual(list(self.root.iterdir()), [])
    result = self.run_job()
    self.assertEqual(result.status, 'STRUCTURAL_PREVIEW')
    self.assertEqual(result.run_sha256, initial.run_sha256)
    self.assertEqual(result.reasons, ('EVIDENCE_VALIDATION_PENDING', 'NO_EVALUATOR_EXECUTED'))
    self.assertEqual(len(result.profile_sha256s), 3)
    stored = tuple(archive.load_proposal(str(self.root), key) for key in result.profile_sha256s)
    self.assertEqual(tuple(p.proposed_value for p in stored), (2.2, 2.3, 2.4))
    self.assertEqual(stored[1], template())
    chain = archive.load_audit(str(self.root), result.run_sha256)
    self.assertEqual(tuple(record.event.status for record in chain), ('STARTED', 'STRUCTURAL_PREVIEW'))
    self.assertEqual(chain[0].event.profile_sha256, result.profile_sha256s[1])
    self.assertEqual(chain[0].event.source_sha256, 'a' * 64)
    self.assertEqual(chain[0].event.configuration_sha256, 'c' * 64)
    self.assertEqual(chain[0].event.evaluator_sha256, EVALUATOR)
    before = self.snapshot()
    self.assertEqual(self.inspect(), result)
    self.assertEqual(self.snapshot(), before)
    self.assertFalse(result.candidate_generation_allowed)
    self.assertFalse(result.offline_evaluable)
    self.assertFalse(result.runtime_accepted)
    with self.assertRaises(FrozenInstanceError):
      result.runtime_accepted = True
    with self.assertRaises(ValueError):
      replace(result, offline_evaluable=True)

  def test_identical_retry_preserves_bytes_and_rechecks_artifacts(self):
    first = self.run_job()
    before = self.snapshot()
    self.assertEqual(self.run_job(), first)
    self.assertEqual(self.snapshot(), before)
    # Dropping the post-terminal artifact check would falsely succeed or repair.
    victim = self.root / f'proposal-{first.profile_sha256s[0]}.json'
    victim.unlink()
    after_deletion = self.snapshot()
    for result in (self.inspect(), self.run_job()):
      self.assertEqual(result.status, 'BLOCKED')
      self.assertEqual(result.profile_sha256s, ())
    self.assertEqual(self.snapshot(), after_deletion)

  def test_corrupt_terminal_proposal_is_preserved_not_repaired(self):
    first = self.run_job()
    victim = self.root / f'proposal-{first.profile_sha256s[1]}.json'
    victim.write_bytes(b'corrupted')
    before = self.snapshot()
    self.assertEqual(self.inspect().status, 'BLOCKED')
    self.assertEqual(self.run_job().status, 'BLOCKED')
    self.assertEqual(self.snapshot(), before)

  def test_interruption_boundaries_never_return_partial_success(self):
    real_store = archive._store
    for fail_at in range(1, 6):
      with self.subTest(fail_at=fail_at):
        root = self.root / str(fail_at)
        root.mkdir(mode=0o700)
        calls = 0
        def fail_store(*args, fail_at=fail_at):
          nonlocal calls
          calls += 1
          if calls == fail_at:
            raise archive.ArchiveError('IO_ERROR')
          return real_store(*args)
        with patch.object(archive, '_store', side_effect=fail_store):
          result = self.run_job(root=root)
        self.assertEqual(result.status, 'BLOCKED')
        self.assertEqual(result.reasons, ('ARCHIVE_IO_ERROR',))
        self.assertEqual(result.profile_sha256s, ())
        state = inspect_preview(str(root), template(), grid(), evaluator_sha256=EVALUATOR)
        self.assertEqual(state.status, 'NOT_STARTED' if fail_at == 1 else 'INCOMPLETE')
        self.assertEqual(state.profile_sha256s, ())
        self.assertEqual(self.run_job(root=root).status, 'STRUCTURAL_PREVIEW')

  def test_postpublication_failure_is_not_acknowledged_as_success(self):
    real_store = archive._store
    calls = 0
    def fail_after_store(*args):
      nonlocal calls
      calls += 1
      real_store(*args)
      if calls == 5:
        raise archive.ArchiveError('IO_ERROR')
    with patch.object(archive, '_store', side_effect=fail_after_store):
      result = self.run_job()
    self.assertEqual(result.status, 'BLOCKED')
    self.assertEqual(result.profile_sha256s, ())
    # A valid published object can exist despite failed durability acknowledgement.
    self.assertEqual(self.inspect().status, 'STRUCTURAL_PREVIEW')
    self.assertEqual(self.run_job().status, 'STRUCTURAL_PREVIEW')

  def test_unexpected_terminal_cannot_be_retried_into_success(self):
    with patch.object(archive, 'save_proposal', side_effect=archive.ArchiveError('IO_ERROR')):
      initial = self.run_job()
    first = archive.load_audit(str(self.root), initial.run_sha256)
    failed = append_event(first, replace(first[0].event, sequence=1, previous_sha256=first[0].sha256,
                                         status='FAILED', reasons=('EXPLICIT_FAILURE',)))
    archive.save_audit(str(self.root), failed)
    before = self.snapshot()
    self.assertEqual(self.inspect().status, 'BLOCKED')
    self.assertEqual(self.run_job().status, 'BLOCKED')
    self.assertEqual(self.snapshot(), before)

  def test_numeric_spelling_conflict_preserves_original(self):
    first = self.run_job()
    baseline_file = self.root / f'proposal-{first.profile_sha256s[1]}.json'
    previous = baseline_file.read_bytes()
    variant = replace(template(), review=replace(template().review, minimum=2))
    second = self.run_job(p=variant)
    self.assertEqual(second.status, 'BLOCKED')
    self.assertIn('ARCHIVE_CONFLICT', second.reasons)
    self.assertNotEqual(second.run_sha256, first.run_sha256)
    self.assertEqual(baseline_file.read_bytes(), previous)
    self.assertEqual(previous, encode_proposal(template()))
    self.assertEqual(self.inspect(), first)

  def test_run_identity_binds_all_review_and_source_inputs(self):
    first = self.inspect()
    changed = [self.run_job(evaluator='8' * 64), self.run_job(g=replace(grid(), review_sha256='9' * 64)),
               self.run_job(p=replace(template(), binding=replace(template().binding, evidence_sha256='0' * 64))),
               self.run_job(g=replace(grid(), values=(2.3, 2.4)))]
    self.assertEqual(len({first.run_sha256, *(r.run_sha256 for r in changed)}), 5)
    self.assertTrue(all(r.status == 'STRUCTURAL_PREVIEW' for r in changed))

  def test_concurrent_identical_jobs_and_process_reopen(self):
    with ThreadPoolExecutor(max_workers=4) as pool:
      results = list(pool.map(lambda _: self.run_job(), range(4)))
    self.assertTrue(all(r.status == 'STRUCTURAL_PREVIEW' or r.reasons == ('ARCHIVE_BUSY',) for r in results))
    complete = self.run_job()
    self.assertEqual(complete.status, 'STRUCTURAL_PREVIEW')
    self.assertEqual(len(list(self.root.iterdir())), 5)
    script = '''
import json, sys
from openpilot.tools.cyber_autotune.preview_job import inspect_preview
from openpilot.tools.cyber_autotune.tests.test_preview_job import template, EVALUATOR
from openpilot.tools.cyber_autotune.tests.test_search import grid
r = inspect_preview(sys.argv[1], template(), grid(), evaluator_sha256=EVALUATOR)
print(json.dumps([r.status, r.run_sha256, r.runtime_accepted]))
'''
    child = subprocess.run([sys.executable, '-c', script, str(self.root)], capture_output=True, text=True, timeout=10, check=True)
    self.assertEqual(json.loads(child.stdout), ['STRUCTURAL_PREVIEW', complete.run_sha256, False])


if __name__ == '__main__':
  unittest.main()
