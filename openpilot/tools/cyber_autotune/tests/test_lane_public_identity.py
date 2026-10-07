import copy
import unittest

from openpilot.tools.cyber_autotune import lane_public_batch as api
from openpilot.tools.cyber_autotune import lane_detector_execution as e
from openpilot.tools.cyber_autotune.lane_tail_report import seal
from openpilot.tools.cyber_autotune.native_protocol import canonical, digest


class TestActivePublicIdentity(unittest.TestCase):
  def fixture(self):
    environment = {'config_sha256': 'a' * 64, 'source_bundle_sha256': 'b' * 64}
    hashes = {'producer_source_sha256': 'c' * 64, 'metric_source_sha256': 'd' * 64, 'report_source_sha256': 'e' * 64}
    frozen_environment = {**environment, 'environment_sha256': digest(canonical(environment))}
    run = seal({'environment': frozen_environment, **hashes})
    return run, environment, hashes

  def test_unchanged_active_identity_passes(self):
    run, environment, hashes = self.fixture()
    api.require_active_run_identity(run, environment, hashes, e.COMMIT)

  def test_each_active_source_change_fails_and_empty_binding_fails(self):
    run, environment, hashes = self.fixture()
    for key in hashes:
      with self.subTest(source=key):
        changed = {**hashes, key: 'f' * 64}
        with self.assertRaisesRegex(ValueError, 'ACTIVE_RUN_SOURCE_IDENTITY_DRIFT'):
          api.require_active_run_identity(run, environment, changed, e.COMMIT)
    for invalid in ({}, {**hashes, 'unbound_extra': 'f' * 64}):
      with self.assertRaises(ValueError):
        api.require_active_run_identity(run, environment, invalid, e.COMMIT)

  def test_config_environment_or_actual_head_change_fails(self):
    run, environment, hashes = self.fixture()
    for key in environment:
      with self.subTest(field=key):
        with self.assertRaisesRegex(ValueError, 'ACTIVE_RUN_SOURCE_IDENTITY_DRIFT'):
          api.require_active_run_identity(run, {**environment, key: 'f' * 64}, hashes, e.COMMIT)
    with self.assertRaises(ValueError):
      api.require_active_run_identity(run, environment, hashes, 'f' * 40)

  def test_frozen_receipt_tampering_fails(self):
    run, environment, hashes = self.fixture()
    changed = copy.deepcopy(run)
    changed['metric_source_sha256'] = hashes['metric_source_sha256'] = 'f' * 64
    with self.assertRaises(ValueError):
      api.require_active_run_identity(changed, environment, hashes, e.COMMIT)

  def test_default_partial_batch_guard_checks_indirect_environment_source(self):
    import json
    from pathlib import Path
    import tempfile

    run, environment, hashes = self.fixture()
    environment['diagnostic_source_sha256'] = '1' * 64
    run = seal(
      {
        **{key: value for key, value in run.items() if key not in ('receipt_sha256', 'environment')},
        'environment': {**environment, 'environment_sha256': digest(canonical(environment))},
      }
    )
    changed = {**environment, 'diagnostic_source_sha256': '2' * 64}
    with tempfile.TemporaryDirectory() as directory:
      output = Path(directory)
      guard = api.make_active_identity_guard(
        run,
        output,
        [{'ordinal': 0, 'receipt_sha256': 'a' * 64}],
        11888,
        lambda: hashes,
        lambda: changed,
        lambda: e.COMMIT,
      )
      with self.assertRaisesRegex(ValueError, 'ACTIVE_RUN_SOURCE_IDENTITY_DRIFT'):
        guard()
      progress = json.loads((output / 'progress.json').read_bytes())
      self.assertEqual(progress['status'], 'FAILED_SOURCE_IDENTITY_DRIFT')
      self.assertEqual(progress['completed_frames'], 1)

  def test_source_drift_never_completes_or_promotes(self):
    progress = api.source_drift_progress('f' * 64, [{'ordinal': 0, 'receipt_sha256': 'a' * 64}], 11888)
    self.assertEqual(progress['status'], 'FAILED_SOURCE_IDENTITY_DRIFT')
    self.assertEqual(progress['completed_frames'], 1)
    self.assertFalse(progress['reference_promotable'])
    self.assertFalse(progress['private_input_opened'])
    self.assertEqual(progress['per_frame_receipts'][0]['ordinal'], 0)


class TestPersistentPublicArtifacts(unittest.TestCase):
  def test_volatile_paths_rejected_before_semantic_reads(self):
    for path in ('/tmp/public-cache', '/run/user/cache', '/dev/shm/reference'):
      with self.subTest(path=path):
        with self.assertRaisesRegex(ValueError, 'PERSISTENT_PUBLIC_ARTIFACT_PATH_REQUIRED'):
          api.require_persistent_path(path)

  def test_persistent_external_path_is_allowed(self):
    self.assertEqual(str(api.require_persistent_path('/opt/offline/public-cache')), '/opt/offline/public-cache')

  def test_guard_writes_failed_status_and_quarantines_summary(self):
    import json
    from pathlib import Path
    import tempfile

    run, environment, hashes = TestActivePublicIdentity().fixture()
    with tempfile.TemporaryDirectory() as directory:
      out = Path(directory)
      original_summary = b'{"completed":true}\n'
      (out / 'summary.json').write_bytes(original_summary)
      guard = api.make_active_identity_guard(
        run,
        out,
        [],
        11888,
        lambda: {**hashes, 'metric_source_sha256': 'f' * 64},
        lambda: environment,
        lambda: e.COMMIT,
      )
      with self.assertRaises(ValueError):
        guard(check_environment=True)
      progress = json.loads((out / 'progress.json').read_bytes())
      self.assertEqual(progress['status'], 'FAILED_SOURCE_IDENTITY_DRIFT')
      self.assertFalse((out / 'summary.json').exists())
      self.assertEqual(next(out.glob('summary-before-identity-drift-*.json')).read_bytes(), original_summary)


if __name__ == '__main__':
  unittest.main()
