"""Real local restore/comparison state; only external SDK/venv worker boundary doubled."""

import importlib
import json
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from test_tooling_restore import (
    archive_fixture,
    artifacts,
    encoded,
    make_saved_template,
)

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
restore = importlib.import_module('cloud_restore')
fetch = importlib.import_module('hf_archive').fetch
GATES = importlib.import_module('cloud_run').GATES
fixtures = importlib.import_module('test_restore_fetch')
MemoryHub, HF_REPO = fixtures.ReadOnlyHub, fixtures.REPO


class Worker:
    """Model/network/environment work is outside these orchestration unit tests."""

    def __init__(self, root, repo, profile, dev_zip, tool_zip):
        self.root, self.repo, self.profile = root, repo, profile
        self.archives = {'dev': dev_zip, 'tools': tool_zip}
        self.calls, self.fail, self.dev_changes, self.fetch_changes = [], None, {}, {}

    def __call__(self, command, log, cwd, env=None, **kwargs):
        args = list(map(str, command))
        self.calls.append(args)
        assert env is not None
        self.last_env = {k: env[k] for k in ['UV_PYTHON_DOWNLOADS', 'PYTHONDONTWRITEBYTECODE']}
        output = Path(args[args.index('--output') + 1])
        role = 'dev' if Path(args[2]).name == 'cloud_restore.py' else 'tools'
        log.write_bytes(b'external SDK/venv boundary fixture\n')
        if role == self.fail:
            output.mkdir()
            (output / 'partial.log').write_bytes(b'preserve partial worker output')
            raise ValueError('STORAGE_DOWNLOAD_FAILED')
        source = args[args.index('--commit' if role == 'dev' else '--source-commit') + 1]
        repo_id = args[args.index('--hf-repo' if role == 'dev' else '--repo-id') + 1]
        digest, revision = (args[args.index(flag) + 1] for flag in ['--archive-sha', '--revision'])
        hub = MemoryHub()
        prefix = f'runs/{source}/{digest}/'
        hub.snapshots[self.profile[role]['revision']] = {
            prefix + 'EVIDENCE.zip': self.archives[role].read_bytes(),
            prefix + 'SHA256SUMS.txt': (self.profile[role]['sha256'] + '  EVIDENCE.zip\n').encode()}
        if role == 'tools':
            record = fetch(digest, repo_id, source, revision, output, hub)
            record.update(self.fetch_changes)
            return encoded(record)
        output.mkdir()
        fetched = fetch(digest, repo_id, source, revision, output / 'fetched', hub)
        repo = Path(args[args.index('--repo-root') + 1])
        recovered = restore.recover_source(repo, source, output / 'fetched/EVIDENCE.zip', digest, output / 'source')
        python = output / 'dev-venv/bin/python'
        python.parent.mkdir(parents=True)
        python.write_bytes(b'fixture app interpreter, never executed')
        runtime = {'python': '3.12.13', 'prefix': str(output / 'dev-venv'),
                   'numpy_origin': str(output / 'dev-venv/lib/numpy/__init__.py'),
                   'versions': {'numpy': '2.5.3', 'ruff': '0.16.7', 'ty': '0.0.80', 'codespell': '2.4.3', 'PyYAML': '6.0.3'},
                   'hf_sdk_in_app': False}
        r41 = {'status': 'HF_RESTORED_R41_EXACT_PASS', 'portable_files': 26, 'baseline_samples': 324,
               'baseline_differences': 0, 'explicit_model_steps': 972, 'explicit_reference_steps': 972,
               'matches_pinned_hf_portable': True, 'manifests': [], 'portable_sha256': {},
               'unit_gate_work': 'ADDITIONAL_NONZERO_NOT_AGGREGATED'}
        result = {'status': 'PRIVATE_HF_DEV_RESTORE_SYNTHETIC_PASS', 'source_commit': source,
                  'source_tree': recovered['source_tree'], 'source_files': recovered['source_files'],
                  'fetch': fetched, 'runtime': runtime, 'R41': r41, 'gates': deepcopy(GATES),
                  'full_700_test_rerun': False, 'physical_machine_independence': False,
                  'scope': recovered['scope'], 'remote_writes': 0,
                  'F61_Controller_vehicle_Runtime_CAN_actual_r_dt': 0, 'vehicle_installation': 0,
                  'downloaded_driver_executions': 0, 'source_bytes_unchanged': True}
        result.update(self.dev_changes)
        (output / 'SOURCE_RECOVERY.json').write_bytes(encoded(recovered))
        (output / 'RESTORE_RESULT.json').write_bytes(encoded(result))
        (output / 'DEV_START.json').write_bytes(encoded({'source_commit': source, 'source_root': str(output / 'source'),
            'component': str(output / 'source/tools/cyberlateral_dev'), 'python': str(python), 'gates': GATES,
            'scope': recovered['scope'], 'requires': 'RESTORE_RESULT.json status PASS'}))
        return encoded({'status': result['status'], 'source_commit': source,
                        'source_files': recovered['source_files'], 'remote_writes': 0})


class CloudStartTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix='r68-start-fixture-')
        cls.saved = make_saved_template(Path(cls.temporary.name))

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def module(self):
        self.assertTrue((TOOLS / 'cloud_start.py').is_file(), 'pinned cloud start missing')
        return importlib.import_module('cloud_start')

    def fixture(self, root, change_tool=None):
        repo, _, identity, tool_files = archive_fixture(root, self.saved)
        app_file = repo / 'tools/cyberlateral_dev/original.txt'
        app_file.parent.mkdir(parents=True)
        app_file.write_bytes(b'original app\r\n')
        subprocess.run(['git', '-C', repo, 'add', '.'], check=True)
        subprocess.run(['git', '-C', repo, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                        'commit', '-qm', 'app fixture'], check=True)
        commit = subprocess.check_output(['git', '-C', repo, 'rev-parse', 'HEAD']).decode().strip()
        tree = subprocess.check_output(['git', '-C', repo, 'rev-parse', 'HEAD^{tree}']).decode().strip()
        identity.update(commit=commit, tree=tree)
        tool_files['SOURCE_IDENTITY.json'] = encoded(identity)
        if change_tool:
            change_tool(tool_files)
        tool_zip, dev_zip = root / 'tools.zip', root / 'dev.zip'
        tool_info = artifacts.seal(tool_zip, tool_files)
        app_identity = artifacts.export_source(repo, commit, root / 'app-reference')
        app_files = {'SOURCE_IDENTITY.json': encoded(app_identity), 'SOURCE/tools/cyberlateral_dev/original.txt': b'original app\r\n'}
        dev_info = artifacts.seal(dev_zip, app_files)
        profile = {'schema_version': 1, 'profile_id': 'FIXTURE_R67', 'source_commit': commit, 'source_tree': tree,
                   'repo_id': HF_REPO, 'dev': {'sha256': dev_info['archive_sha256'], 'revision': '8' * 40},
                   'tools': {'sha256': tool_info['archive_sha256'], 'revision': '9' * 40}}
        return repo, profile, Worker(root, repo, profile, dev_zip, tool_zip)

    def run_fixture(self, m, root, repo, profile, worker, sdk=None, output=None):
        with patch.object(m, 'run_command', side_effect=worker):
            return m.run_profile(repo, Path(sdk or sys.executable), output or root / 'new', profile)

    def command(self, *args):
        self.module()
        return subprocess.run([sys.executable, '-B', TOOLS / 'cloud_start.py', *map(str, args)], capture_output=True, timeout=30)

    # Catch root success before complete children, wrong pins, hidden upload or quality upgrade.
    def test_complete_real_local_state_preserves_fail_and_normal_difference(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo, profile, worker = self.fixture(root)
            before = deepcopy(profile)
            result = self.run_fixture(m, root, repo, profile, worker)
            self.assertEqual(result['status'], 'R68_PINNED_CLOUD_START_PASS')
            self.assertEqual((result['dev_source_files'], result['tool_source_files'], result['saved_files']), (1, 2, 114))
            self.assertEqual(result['comparisons']['different']['status'], 'R66_SAVED_BROWSER_BYTES_DIFFERENT')
            same_fail = result['comparisons']['same_fail']
            self.assertEqual(same_fail['status'], 'R66_SAVED_BROWSER_EXACT_BYTES_MATCH')
            self.assertEqual(same_fail['baseline_verification']['recorded_status'], 'R60_BROWSER_SMOKE_FAIL')
            self.assertEqual(same_fail['candidate_verification']['recorded_failure_records'], 1)
            self.assertEqual(result['gates'], GATES)
            self.assertEqual(result['remote_writes'], 0)
            self.assertEqual(json.loads((root / 'new/START_RESULT.json').read_bytes()), result)
            self.assertIn('화면 PASS가 아닙니다', (root / 'new/START_KO.md').read_text())
            self.assertTrue((root / 'new/TOOL_RECOVERY.json').is_file())
            self.assertTrue((root / 'new/comparisons/different.json').is_file())
            self.assertIn('R60_BROWSER_SMOKE_FAIL', (root / 'new/comparisons/same_fail_KO.md').read_text())
            self.assertFalse((root / 'new/FAILURE.json').exists())
            self.assertEqual(profile, before)
            self.assertEqual(worker.last_env, {'UV_PYTHON_DOWNLOADS': 'never', 'PYTHONDONTWRITEBYTECODE': '1'})
            # These consumed arguments determine real MemoryHub fetch/Git matching above.
            self.assertEqual([Path(c[2]).name for c in worker.calls], ['cloud_restore.py', 'hf_archive.py'])
            self.assertEqual(worker.calls[1][3], 'fetch')
            self.assertNotIn('backup', [arg for call in worker.calls for arg in call])

    def test_profile_command_is_frozen_deterministic_and_does_not_need_sdk(self):
        first, second = self.command('profile'), self.command('profile')
        self.assertEqual((first.returncode, first.stderr), (0, b''))
        self.assertEqual(first.stdout, second.stdout)
        profile = json.loads(first.stdout)
        self.assertEqual(profile['profile_id'], 'R67_MAIN_V1')
        self.assertEqual(profile['source_commit'], 'f562377abefdc5796f54b4f98c0c3ded9a5a4a3e')
        self.assertEqual(profile['dev'], {'sha256': 'adeaf66e4212ffa350c5b851c684153eac0f5953716f9e9449afd22d5c031c22',
                                          'revision': '5916191894529c579451b21c7f3f18b9f5eee2ed'})
        self.assertEqual(profile['tools'], {'sha256': 'c7ca0b6fd9ed46cd31d3456b39536b35203799070dfee0e89ed485eb7004723d',
                                            'revision': '9d41b3cccacc25fa7c4843b1a1a44f23a33ed16e'})

    def test_get_profile_cannot_be_mutated_through_a_returned_nested_record(self):
        m = self.module()
        before = m.get_profile()
        changed = m.get_profile()
        changed['tools']['revision'] = 'main'
        self.assertEqual(m.get_profile(), before)

    def test_missing_or_nonexecutable_sdk_records_failure_without_worker(self):
        m = self.module()
        for executable in [False, None]:
            with self.subTest(executable=executable), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                repo, profile, worker = self.fixture(root)
                sdk = root / 'invalid-sdk'
                if executable is False:
                    sdk.write_bytes(b'must not run')
                    sdk.chmod(0o644)
                with self.assertRaisesRegex(ValueError, '^HF_INTERPRETER_REQUIRED$'):
                    self.run_fixture(m, root, repo, profile, worker, sdk=sdk)
                failure = json.loads((root / 'new/FAILURE.json').read_bytes())
                self.assertEqual(failure['stage'], 'SDK_PREFLIGHT')
                self.assertFalse((root / 'new/START_RESULT.json').exists())
                self.assertEqual(worker.calls, [])

    def test_existing_symlink_or_internal_output_is_never_replaced(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo, profile, worker = self.fixture(root)
            existing = root / 'existing'
            existing.mkdir()
            (existing / 'keep').write_bytes(b'keep')
            (root / 'alias').symlink_to(existing, target_is_directory=True)
            for output, code in [(existing, 'OUTPUT_EXISTS'), (root / 'alias/new', 'RESTORE_PATH_SYMLINK'),
                                 (repo / 'new', 'EXTERNAL_OUTPUT_REQUIRED')]:
                with self.subTest(code=code), self.assertRaisesRegex((ValueError, FileExistsError), code):
                    self.run_fixture(m, root, repo, profile, worker, output=output)
            self.assertEqual([p.name for p in existing.iterdir()], ['keep'])
            self.assertEqual((existing / 'keep').read_bytes(), b'keep')
            self.assertEqual(worker.calls, [])

    def test_dev_transport_failure_stops_before_fetch_or_completion(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo, profile, worker = self.fixture(root)
            worker.fail = 'dev'
            with self.assertRaisesRegex(ValueError, 'STORAGE_DOWNLOAD_FAILED'):
                self.run_fixture(m, root, repo, profile, worker)
            self.assertEqual(json.loads((root / 'new/FAILURE.json').read_bytes())['stage'], 'DEV_RESTORE')
            self.assertTrue((root / 'new/dev/partial.log').is_file())
            self.assertFalse((root / 'new/START_RESULT.json').exists())
            self.assertEqual(len(worker.calls), 1)

    def test_bad_dev_receipt_is_not_promoted_to_complete_start(self):
        m = self.module()
        for changes in [{'source_commit': '0' * 40}, {'source_files': 2}, {'remote_writes': False},
                        {'gates': GATES | {'R_BUDGET': 0}}, {'source_bytes_unchanged': False},
                        {'runtime': {'python': '3.12.0'}}, {'R41': {'status': 'FAIL'}}]:
            with self.subTest(changes=changes), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                repo, profile, worker = self.fixture(root)
                worker.dev_changes = changes
                with self.assertRaises(ValueError):
                    self.run_fixture(m, root, repo, profile, worker)
                self.assertEqual(json.loads((root / 'new/FAILURE.json').read_bytes())['stage'], 'DEV_RESTORE')
                self.assertFalse((root / 'new/START_RESULT.json').exists())
                self.assertEqual(len(worker.calls), 1)

    def test_tool_fetch_failure_keeps_dev_success_but_no_root_success(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo, profile, worker = self.fixture(root)
            worker.fail = 'tools'
            with self.assertRaisesRegex(ValueError, 'STORAGE_DOWNLOAD_FAILED'):
                self.run_fixture(m, root, repo, profile, worker)
            self.assertTrue((root / 'new/dev/RESTORE_RESULT.json').is_file())
            self.assertTrue((root / 'new/tool-fetched/partial.log').is_file())
            self.assertEqual(json.loads((root / 'new/FAILURE.json').read_bytes())['stage'], 'TOOL_FETCH')
            self.assertFalse((root / 'new/START_RESULT.json').exists())

    def test_wrong_fetch_private_revision_or_write_count_is_rejected(self):
        m = self.module()
        for changes in [{'private': 1}, {'commit_sha': '0' * 40}, {'archive_sha256': '0' * 64}, {'remote_writes': False}]:
            with self.subTest(changes=changes), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                repo, profile, worker = self.fixture(root)
                worker.fetch_changes = changes
                with self.assertRaisesRegex(ValueError, '^START_FETCH_RECEIPT_INVALID$'):
                    self.run_fixture(m, root, repo, profile, worker)
                self.assertEqual(json.loads((root / 'new/FAILURE.json').read_bytes())['stage'], 'TOOL_FETCH')
                self.assertFalse((root / 'new/START_RESULT.json').exists())

    def test_resealed_tool_source_failure_cannot_leave_completion(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            def tamper(files):
                files['SOURCE/tools/cyberlateral_cloud/browser_compare.py'] = b'tampered'
            repo, profile, worker = self.fixture(root, tamper)
            with self.assertRaisesRegex(ValueError, '^TOOL_SOURCE_GIT_MISMATCH$'):
                self.run_fixture(m, root, repo, profile, worker)
            self.assertEqual(json.loads((root / 'new/FAILURE.json').read_bytes())['stage'], 'TOOL_SOURCE')
            self.assertFalse((root / 'new/START_RESULT.json').exists())

    def test_unexpected_saved_pair_contract_is_not_recovery_success(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            def equal_pair(files):
                for name in self.saved:
                    files['SAVED/two/' + name] = files['SAVED/one/' + name]
                metadata = json.loads(files['SAVED_IDENTITY.json'])
                metadata['two'] = deepcopy(metadata['one'])
                files['SAVED_IDENTITY.json'] = encoded(metadata)
            repo, profile, worker = self.fixture(root, equal_pair)
            with self.assertRaisesRegex(ValueError, '^START_COMPARISON_INVALID$'):
                self.run_fixture(m, root, repo, profile, worker)
            self.assertEqual(json.loads((root / 'new/FAILURE.json').read_bytes())['stage'], 'SAVED_COMPARISON')
            self.assertFalse((root / 'new/START_RESULT.json').exists())

    def test_invalid_profile_or_unavailable_git_never_invokes_worker(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo, profile, worker = self.fixture(root)
            for changes in [{'schema_version': True}, {'source_commit': 'HEAD'},
                            {'dev': profile['dev'] | {'revision': 'main'}}, {'tools': profile['tools'] | {'sha256': 'A' * 64}}]:
                with self.subTest(changes=changes), self.assertRaisesRegex(ValueError, '^START_PROFILE_INVALID$'):
                    self.run_fixture(m, root, repo, profile | changes, worker)
                self.assertFalse((root / 'new').exists())
            with self.assertRaisesRegex(ValueError, '^PINNED_GIT_SOURCE_UNAVAILABLE$'):
                self.run_fixture(m, root, repo, profile | {'source_tree': '0' * 40}, worker)
            self.assertFalse((root / 'new/START_RESULT.json').exists())
            self.assertEqual(worker.calls, [])

    def test_cli_missing_sdk_is_safe_json_error_and_preserves_failure(self):
        self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = self.command('run', '--hf-python', root / 'missing', '--output', root / 'new')
            self.assertEqual((result.returncode, result.stderr), (2, b''))
            self.assertEqual(json.loads(result.stdout), {'status': 'FAILED', 'code': 'HF_INTERPRETER_REQUIRED'})
            self.assertTrue((root / 'new/FAILURE.json').is_file())

    def test_help_profile_imports_no_optional_packages_and_rejects_override_flags(self):
        self.module()
        result = self.command('--help')
        self.assertEqual(result.returncode, 0, result.stderr)
        query = ("import sys;sys.path.insert(0,sys.argv[1]);import cloud_start;cloud_start.get_profile();"
                 "bad={'playwright','numpy','huggingface_hub','cyberlateral_dev','openpilot','opendbc','capnp','cereal',"
                 "'synthetic_rate_constraint_feasibility_v1'};assert not {n.split('.')[0] for n in sys.modules}&bad;print('PASS')")
        probe = subprocess.run([sys.executable, '-I', '-B', '-c', query, str(TOOLS)], capture_output=True, timeout=20)
        self.assertEqual((probe.returncode, probe.stdout, probe.stderr), (0, b'PASS\n', b''))
        for args in [[], ['profile', '--revision', 'main'], ['run', '--hf-py', sys.executable, '--output', '/unused'],
                     ['run', '--hf-python', sys.executable, '--output', '/unused', '--profile', 'latest']]:
            with self.subTest(args=args):
                result = self.command(*args)
                self.assertEqual((result.returncode, result.stdout), (2, b''))
                self.assertNotIn(b'Traceback', result.stderr)

    def test_interrupted_completion_write_never_publishes_success_marker(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo, profile, worker = self.fixture(root)
            original = m.write_json

            def interrupted(path, record):
                if path.name.startswith('START_RESULT'):
                    path.write_bytes(b'{"status":"R68_PINNED_CLOUD_START_PASS"')
                    raise OSError('controlled interrupted completion write')
                original(path, record)

            with patch.object(m, 'write_json', side_effect=interrupted), self.assertRaises(ValueError):
                self.run_fixture(m, root, repo, profile, worker)
            self.assertFalse((root / 'new/START_RESULT.json').exists())
            self.assertEqual(json.loads((root / 'new/FAILURE.json').read_bytes())['stage'], 'SEAL')
            self.assertTrue((root / 'new/dev/RESTORE_RESULT.json').is_file())


if __name__ == '__main__':
    unittest.main()
