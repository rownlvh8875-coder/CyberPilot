"""Stdlib fixtures only: no native schema, vehicle process or replay imports."""

import ast
from collections.abc import Callable
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
import sys
import traceback
from typing import cast


RAW = b'synthetic reference\n'
NAME = 'fixture--0_card_' + 'a' * 40 + '.zst'


def fixture():
  return {
    'schema_version': 1,
    'producer_commit': 'a' * 40,
    'artifact_commit': 'b' * 40,
    'source_scope': 'replay-producer-v1',
    'source_fingerprint_sha256': 'c' * 64,
    'opendbc_commit': 'e' * 40,
    'opendbc_schema_git_blob': 'd' * 40,
    'artifacts': {NAME: {'byte_size': 20, 'git_blob_sha1': '4e0e0550a1f06c42843ac3360d8398e3eac10f54',
                         'sha256': '7d8d86a00513278c4edb415dd80e4c72c1be20da1f10a6235e077724eb93a22e'}},
  }


class TestReferenceBundle(unittest.TestCase):
  def setUp(self):
    path = Path(__file__).with_name('reference_bundle.py')
    self.assertTrue(path.is_file(), 'Missing stdlib-only pinned reference validator')
    spec = importlib.util.spec_from_file_location('reference_bundle', path)
    assert spec is not None and spec.loader is not None
    self.module = importlib.util.module_from_spec(spec)
    old = sys.modules.get(spec.name)
    sys.modules[spec.name] = self.module
    def restore_module():
      if old is None:
        sys.modules.pop(spec.name, None)
      else:
        sys.modules[spec.name] = old
    self.addCleanup(restore_module)
    spec.loader.exec_module(self.module)
    self.temp = tempfile.TemporaryDirectory()
    self.addCleanup(self.temp.cleanup)
    self.root = Path(self.temp.name)

  def bundle(self, record=None):
    path = self.root / 'lock.json'
    path.write_text(json.dumps(fixture() if record is None else record))
    return self.module.ReferenceBundle.load(path)

  def test_immutable_url_and_valid_bytes(self):
    bundle = self.bundle()
    expected = 'https://raw.githubusercontent.com/commaai/ci-artifacts/' + 'b' * 40 + '/' + NAME
    self.assertEqual(bundle.reference_url(NAME), expected)
    self.assertEqual(bundle.reference_name('fixture--0', 'card'), NAME)
    self.assertEqual(bundle.verify_bytes(NAME, RAW), RAW)

  def test_modified_reference_bytes_rejected(self):
    bundle = self.bundle()
    for raw in (RAW + b'!', b'X' + RAW[1:]):
      with self.subTest(raw=raw), self.assertRaisesRegex(self.module.ReferenceBundleError, 'REFERENCE_BYTES_MISMATCH'):
        bundle.verify_bytes(NAME, raw)

  def test_each_digest_enforced(self):
    for field, value in [('sha256', 'f' * 64), ('git_blob_sha1', 'f' * 40), ('byte_size', 21)]:
      record = fixture()
      record['artifacts'][NAME][field] = value
      with self.subTest(field=field), self.assertRaisesRegex(self.module.ReferenceBundleError, 'REFERENCE_BYTES_MISMATCH'):
        self.bundle(record).verify_bytes(NAME, RAW)

  def test_unlisted_reference_rejected_before_fetch(self):
    bundle = self.bundle()
    def fetch(_):
      self.fail('Unlisted reference must not reach the network')
    with self.assertRaisesRegex(self.module.ReferenceBundleError, 'REFERENCE_NOT_LISTED'):
      bundle.prepare_references([('fixture--0', 'plannerd')], self.root, fetch)

  def test_local_cache_must_match_and_is_not_silently_replaced(self):
    bundle = self.bundle()
    (self.root / NAME).write_bytes(b'corrupt')
    def fetch(_):
      self.fail('Corrupt local data must not be silently replaced')
    with self.assertRaisesRegex(self.module.ReferenceBundleError, 'REFERENCE_BYTES_MISMATCH'):
      bundle.prepare_references([('fixture--0', 'card')], self.root, fetch)

  def test_local_verified_bytes_returned_without_fetch(self):
    (self.root / NAME).write_bytes(RAW)
    def fetch(_):
      self.fail('Valid local data must not require a network fetch')
    self.assertEqual(self.bundle().prepare_references([('fixture--0', 'card')], self.root, fetch), {NAME: RAW})

  def test_download_uses_immutable_url_and_returns_verified_bytes(self):
    expected = 'https://raw.githubusercontent.com/commaai/ci-artifacts/' + 'b' * 40 + '/' + NAME
    def fetch(url):
      self.assertEqual(url, expected)
      return RAW
    self.assertEqual(self.bundle().prepare_references([('fixture--0', 'card')], self.root, fetch), {NAME: RAW})

  def test_transfer_error_is_explicit(self):
    def fetch(_):
      raise OSError('offline')
    with self.assertRaisesRegex(self.module.ReferenceBundleError, 'REFERENCE_FETCH_FAILED'):
      self.bundle().prepare_references([('fixture--0', 'card')], self.root, fetch)

  def test_all_selected_names_checked_before_any_fetch(self):
    def fetch(_):
      self.fail('Validate complete inventory before first transfer')
    with self.assertRaisesRegex(self.module.ReferenceBundleError, 'REFERENCE_NOT_LISTED'):
      self.bundle().prepare_references([('fixture--0', 'card'), ('absent--0', 'card')], self.root, fetch)

  def test_invalid_lock_variants_rejected(self):
    changes = [('schema_version', True), ('schema_version', 2), ('artifact_commit', 'process-replay'),
               ('source_scope', 'unknown'), ('producer_commit', 'a' * 39), ('source_fingerprint_sha256', 'x' * 64),
               ('opendbc_commit', None), ('artifacts', {}), ('extra', 1)]
    for key, value in changes:
      record = fixture()
      record[key] = value
      with self.subTest(key=key, value=value), self.assertRaisesRegex(self.module.ReferenceBundleError, 'INVALID_REFERENCE_LOCK'):
        self.bundle(record)

  def test_unsafe_or_wrong_producer_names_rejected(self):
    for name in ('../' + NAME, 'dir/' + NAME, 'https://host/' + NAME, NAME.replace('a' * 40, 'b' * 40), NAME + '?x=1'):
      record = fixture()
      record['artifacts'] = {name: record['artifacts'][NAME]}
      with self.subTest(name=name), self.assertRaisesRegex(self.module.ReferenceBundleError, 'INVALID_REFERENCE_LOCK'):
        self.bundle(record)

  def test_invalid_artifact_metadata_rejected(self):
    for key, value in [('byte_size', True), ('byte_size', 0), ('byte_size', -1), ('byte_size', 6_000_000),
                       ('sha256', 'not-a-hash'), ('git_blob_sha1', 'x' * 40), ('extra', 1)]:
      record = fixture()
      record['artifacts'][NAME][key] = value
      with self.subTest(key=key, value=value), self.assertRaisesRegex(self.module.ReferenceBundleError, 'INVALID_REFERENCE_LOCK'):
        self.bundle(record)

  def test_duplicate_json_and_missing_lock_rejected(self):
    path = self.root / 'bad.json'
    path.write_text('{"schema_version":1,"schema_version":1}')
    with self.assertRaisesRegex(self.module.ReferenceBundleError, 'INVALID_REFERENCE_LOCK'):
      self.module.ReferenceBundle.load(path)
    with self.assertRaisesRegex(self.module.ReferenceBundleError, 'REFERENCE_LOCK_UNAVAILABLE'):
      self.module.ReferenceBundle.load(self.root / 'missing')

  def checkout(self):
    def git(*args):
      return subprocess.run(['git', *args], cwd=self.root, capture_output=True, check=True).stdout
    git('init', '-q')
    git('config', 'user.email', 'fixture@example.invalid')
    git('config', 'user.name', 'Fixture')
    (self.root / 'openpilot').mkdir()
    (self.root / 'openpilot/source.py').write_text('value = 1\n')
    git('add', 'openpilot/source.py')
    git('commit', '-qm', 'fixture')
    record = fixture()
    record['source_fingerprint_sha256'] = hashlib.sha256(git('ls-tree', '-r', '-z', 'HEAD', '--', 'openpilot')).hexdigest()
    return record, git

  def test_changed_source_metadata_rejected(self):
    record, _ = self.checkout()
    record['source_fingerprint_sha256'] = 'f' * 64
    with self.assertRaisesRegex(self.module.ReferenceBundleError, 'PRODUCER_SOURCE_MISMATCH'):
      self.bundle(record).validate_checkout(self.root)

  def test_dirty_protected_source_rejected_before_submodule_work(self):
    record, _ = self.checkout()
    (self.root / 'openpilot/source.py').write_text('value = 2\n')
    with self.assertRaisesRegex(self.module.ReferenceBundleError, 'PRODUCER_SOURCE_DIRTY'):
      self.bundle(record).validate_checkout(self.root)

  def test_missing_opendbc_rejected(self):
    record, _ = self.checkout()
    with self.assertRaisesRegex(self.module.ReferenceBundleError, 'OPENDBC_CHECKOUT_UNAVAILABLE'):
      self.bundle(record).validate_checkout(self.root)

  def test_legacy_override_rejected(self):
    bundle = self.bundle()
    path = self.root / 'ref_commit'
    path.write_text('f' * 40)
    with self.assertRaisesRegex(self.module.ReferenceBundleError, 'LEGACY_REFERENCE_OVERRIDE_MISMATCH'):
      bundle.validate_legacy_pin(path)
    path.write_text('a' * 40 + '\n')
    bundle.validate_legacy_pin(path)

  def complete_checkout(self):
    record, git = self.checkout()
    dbc = self.root / 'opendbc_repo'
    (dbc / 'opendbc/car').mkdir(parents=True)
    raw = b'synthetic schema fixture\n'
    (dbc / 'opendbc/car/car.capnp').write_bytes(raw)
    (dbc / 'opendbc/limits.py').write_text('limit = 1\n')
    def dbc_git(*args):
      return subprocess.run(['git', '-C', str(dbc), *args], capture_output=True, check=True).stdout
    dbc_git('init', '-q')
    dbc_git('config', 'user.email', 'fixture@example.invalid')
    dbc_git('config', 'user.name', 'Fixture')
    dbc_git('add', '.')
    dbc_git('commit', '-qm', 'schema')
    git('add', 'opendbc_repo')
    git('commit', '-qm', 'pin schema')
    record['source_fingerprint_sha256'] = hashlib.sha256(git('ls-tree', '-r', '-z', 'HEAD', '--', 'openpilot', 'opendbc_repo')).hexdigest()
    record['opendbc_commit'] = dbc_git('rev-parse', 'HEAD').decode().strip()
    record['opendbc_schema_git_blob'] = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
    return record, git

  def test_compatible_checkout_passes_without_producer_history(self):
    record, _ = self.complete_checkout()
    self.bundle(record).validate_checkout(self.root)

  def test_wrong_opendbc_revision_rejected(self):
    record, _ = self.complete_checkout()
    record['opendbc_commit'] = 'f' * 40
    with self.assertRaisesRegex(self.module.ReferenceBundleError, 'OPENDBC_COMMIT_MISMATCH'):
      self.bundle(record).validate_checkout(self.root)

  def test_wrong_schema_identity_rejected(self):
    record, _ = self.complete_checkout()
    record['opendbc_schema_git_blob'] = 'f' * 40
    with self.assertRaisesRegex(self.module.ReferenceBundleError, 'OPENDBC_SCHEMA_MISMATCH'):
      self.bundle(record).validate_checkout(self.root)

  def test_git_ignore_submodules_config_cannot_hide_tracked_source_changes(self):
    record, git = self.complete_checkout()
    (self.root / 'opendbc_repo/opendbc/limits.py').write_text('limit = 2\n')
    for setting in ('all', 'dirty'):
      git('config', 'diff.ignoreSubmodules', setting)
      with self.subTest(setting=setting), self.assertRaisesRegex(self.module.ReferenceBundleError, 'PRODUCER_SOURCE_DIRTY'):
        self.bundle(record).validate_checkout(self.root)

  def test_harness_and_offline_tooling_commits_do_not_redefine_producer(self):
    record, git = self.complete_checkout()
    for name in ('openpilot/selfdrive/test/process_replay/new.py', 'tools/cyberlateral_dev/new.py', 'tools/cyberlateral_cloud/new.py'):
      path = self.root / name
      path.parent.mkdir(parents=True, exist_ok=True)
      path.write_text('# independent harness fixture\n')
      git('add', name)
    git('commit', '-qm', 'harness only')
    self.bundle(record).validate_checkout(self.root)

  def test_baseline_regeneration_rejected_before_native_imports(self):
    runner = Path(__file__).with_name('test_processes.py')
    result = subprocess.run([sys.executable, '-B', str(runner), '--update-refs'], capture_output=True, text=True, check=False)
    self.assertEqual(result.returncode, 2, result.stderr)
    self.assertIn('REFERENCE_UPDATE_REQUIRES_SEPARATE_APPROVAL', result.stderr)
    self.assertNotIn('ModuleNotFoundError', result.stderr)

  def test_cli_source_mismatch_rejected_before_native_imports(self):
    runner = Path(__file__).with_name('test_processes.py')
    folder = self.root / 'openpilot/selfdrive/test/process_replay'
    folder.mkdir(parents=True)
    for name in ('test_processes.py', 'reference_bundle.py'):
      (folder / name).write_bytes(runner.with_name(name).read_bytes())
    (folder / 'reference_bundle.json').write_text(json.dumps(fixture()))
    subprocess.run(['git', 'init', '-q', str(self.root)], capture_output=True, check=True)
    result = subprocess.run([sys.executable, '-B', str(folder / runner.name)], capture_output=True, text=True, check=False)
    self.assertEqual(result.returncode, 2, result.stderr)
    self.assertIn('CHECKOUT_METADATA_UNAVAILABLE', result.stderr)
    self.assertNotIn('ModuleNotFoundError', result.stderr)

  def test_worker_consumes_verified_bytes_not_a_reopened_reference(self):
    runner = Path(__file__).with_name('test_processes.py')
    tree = ast.parse(runner.read_text())
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'run_test_process')
    seen = []
    class Reader:
      def __init__(self, *_):
        raise AssertionError('Verified reference bytes must not be reopened as a path')

      @staticmethod
      def from_bytes(raw):
        seen.append(raw)
        return ['ref' if raw == RAW else 'input']
    def run(*args):
      self.assertEqual(args[3], ['ref'])
      return [], ['result']
    scope = {'LogReader': Reader, 'test_process': run, 'save_log': lambda *_: None,
             'diff_process': lambda *_: 'diff', 'traceback': traceback}
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(runner), 'exec'), scope)
    args = type('Args', (), {'ignore_fields': [], 'ignore_msgs': []})()
    config = type('Config', (), {'proc_name': 'card'})()
    worker = cast(Callable[[tuple], tuple], scope['run_test_process'])
    self.assertEqual(worker(('fixture--0', config, args, 'new', RAW, b'input')), ('fixture--0', 'card', [], 'diff'))
    self.assertEqual(seen, [RAW, b'input'])

  def test_decode_failure_never_starts_replay(self):
    runner = Path(__file__).with_name('test_processes.py')
    function = next(n for n in ast.parse(runner.read_text()).body if isinstance(n, ast.FunctionDef) and n.name == 'run_test_process')
    class Reader:
      @staticmethod
      def from_bytes(_):
        raise ValueError('synthetic decode failure')
    def forbidden(*_):
      self.fail('Reference decode failure must not start replay or save output')
    scope = {'LogReader': Reader, 'test_process': forbidden, 'save_log': forbidden, 'diff_process': forbidden, 'traceback': traceback}
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(runner), 'exec'), scope)
    worker = cast(Callable[[tuple], tuple], scope['run_test_process'])
    config = type('Config', (), {'proc_name': 'card'})()
    result = worker(('fixture--0', config, None, 'new', RAW, b'input'))
    self.assertEqual(result[:2], ('fixture--0', 'card'))
    self.assertTrue('Failed to decode verified reference' in result[2])

  def test_checked_in_lock_covers_existing_full_process_inventory(self):
    folder = Path(__file__).parent
    bundle = self.module.ReferenceBundle.load(folder / 'reference_bundle.json')
    runner = ast.parse((folder / 'test_processes.py').read_text())
    segments = next(ast.literal_eval(n.value) for n in runner.body if isinstance(n, ast.Assign)
                    and any(isinstance(t, ast.Name) and t.id == 'segments' for t in n.targets))
    configs = ast.parse((folder / 'process_replay.py').read_text())
    processes = {k.value.value for n in ast.walk(configs) if isinstance(n, ast.Call) for k in n.keywords
                 if k.arg == 'proc_name' and isinstance(k.value, ast.Constant)} - {'modeld', 'dmonitoringmodeld'}
    names = {bundle.reference_name(segment, process) for brand, segment in segments for process in processes
             if process in {'card', 'controlsd', 'lagd'} or brand in {'HYUNDAI', 'TOYOTA'}}
    self.assertEqual(len(names), 66)
    self.assertEqual(names, set(bundle.record['artifacts']))


if __name__ == '__main__':
  unittest.main()
