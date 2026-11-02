"""Prove Git/source and local execution boundaries before implementing restore."""

import importlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
COMPONENT = TOOLS.parent / 'cyberlateral_dev'
sys.path.insert(0, str(TOOLS))
artifacts = importlib.import_module('artifacts')
export_source, seal = artifacts.export_source, artifacts.seal
portable_files = importlib.import_module('workflow_checks').portable_files


class RestoreTests(unittest.TestCase):
    def module(self):
        self.assertTrue((TOOLS / 'cloud_restore.py').is_file(), 'cloud restore implementation missing')
        return importlib.import_module('cloud_restore')

    def fixture(self, root):
        repo = root / 'repo'
        subprocess.run(['git', 'init', '-q', str(repo)], check=True)
        source = repo / 'tools/cyberlateral_dev/original.txt'
        source.parent.mkdir(parents=True)
        source.write_bytes(b'original\r\n')
        subprocess.run(['git', '-C', repo, 'add', '.'], check=True)
        subprocess.run(['git', '-C', repo, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                        'commit', '-qm', 'fixture'], check=True)
        commit = subprocess.check_output(['git', '-C', repo, 'rev-parse', 'HEAD']).decode().strip()
        identity = export_source(repo, commit, root / 'reference')
        files = {'SOURCE_IDENTITY.json': json.dumps(identity).encode(),
                 'SOURCE/tools/cyberlateral_dev/original.txt': b'original\r\n',
                 'DRIVER/do_not_execute.py': b'raise RuntimeError("must not run")\n'}
        return repo, source, commit, files

    def test_recovered_bytes_come_from_hf_matching_git_not_dirty_worktree(self):
        r = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo, source, commit, files = self.fixture(root)
            source.write_bytes(b'user changes must survive')
            (source.parent / 'untracked.txt').write_bytes(b'not backup input')
            sealed = seal(root / 'archive.zip', files)
            result = r.recover_source(repo, commit, root / 'archive.zip', sealed['archive_sha256'], root / 'new')
            self.assertEqual(result['status'], 'EXACT_GIT_MATCHED_SOURCE_RECOVERED')
            self.assertEqual(result['source_files'], 1)
            self.assertEqual((root / 'new/tools/cyberlateral_dev/original.txt').read_bytes(), b'original\r\n')
            self.assertEqual(source.read_bytes(), b'user changes must survive')
            self.assertFalse((root / 'new/DRIVER').exists())
            self.assertFalse((root / 'new/tools/cyberlateral_dev/untracked.txt').exists())

    def test_consistently_resealed_source_substitution_is_rejected(self):
        r = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo, _, commit, files = self.fixture(root)
            files['SOURCE/tools/cyberlateral_dev/original.txt'] = b'substitution'
            sealed = seal(root / 'archive.zip', files)
            with self.assertRaisesRegex(ValueError, 'SOURCE_GIT_MISMATCH'):
                r.recover_source(repo, commit, root / 'archive.zip', sealed['archive_sha256'], root / 'new')
            self.assertFalse((root / 'new').exists())

    def test_missing_or_extra_source_member_is_rejected(self):
        r = self.module()
        for action in ('missing', 'extra'):
            with self.subTest(action=action), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                repo, _, commit, files = self.fixture(root)
                if action == 'missing':
                    files.pop('SOURCE/tools/cyberlateral_dev/original.txt')
                else:
                    files['SOURCE/.git/config'] = b'extra'
                sealed = seal(root / 'archive.zip', files)
                with self.assertRaisesRegex(ValueError, 'SOURCE_MEMBER_SET'):
                    r.recover_source(repo, commit, root / 'archive.zip', sealed['archive_sha256'], root / 'new')
                self.assertFalse((root / 'new').exists())

    def test_resealed_forged_identity_is_rejected_field_by_field(self):
        r = self.module()
        for field, value in [('tree', '0' * 40), ('commit', '0' * 40), ('scope', 'all vehicle files'),
                             ('byte_size', 1), ('git_mode', '100755'), ('git_blob', '0' * 40), ('sha256', '0' * 64)]:
            with self.subTest(field=field), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                repo, _, commit, files = self.fixture(root)
                identity = json.loads(files['SOURCE_IDENTITY.json'])
                target = identity if field in ('tree', 'commit', 'scope') else identity['files']['tools/cyberlateral_dev/original.txt']
                target[field] = value
                files['SOURCE_IDENTITY.json'] = json.dumps(identity).encode()
                sealed = seal(root / 'archive.zip', files)
                with self.assertRaisesRegex(ValueError, 'SOURCE_IDENTITY_MISMATCH'):
                    r.recover_source(repo, commit, root / 'archive.zip', sealed['archive_sha256'], root / 'new')

    def test_existing_destination_and_symlink_parent_remain_untouched(self):
        r = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo, _, commit, files = self.fixture(root)
            sealed = seal(root / 'archive.zip', files)
            existing = root / 'existing'
            existing.mkdir()
            (existing / 'keep').write_bytes(b'keep')
            (root / 'alias').symlink_to(existing, target_is_directory=True)
            with self.assertRaises(FileExistsError):
                r.recover_source(repo, commit, root / 'archive.zip', sealed['archive_sha256'], existing)
            with self.assertRaisesRegex(ValueError, 'RESTORE_PATH_SYMLINK'):
                r.recover_source(repo, commit, root / 'archive.zip', sealed['archive_sha256'], root / 'alias/new')
            self.assertEqual((existing / 'keep').read_bytes(), b'keep')
            self.assertFalse((existing / 'new').exists())

    def test_source_root_cannot_be_restore_destination(self):
        r = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo, _, commit, files = self.fixture(root)
            sealed = seal(root / 'archive.zip', files)
            with self.assertRaisesRegex(ValueError, 'EXTERNAL_OUTPUT_REQUIRED'):
                r.recover_source(repo, commit, root / 'archive.zip', sealed['archive_sha256'], repo / 'new')

    def test_changed_archive_hash_is_rejected_before_source_write(self):
        r = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo, _, commit, files = self.fixture(root)
            seal(root / 'archive.zip', files)
            with self.assertRaisesRegex(ValueError, 'ARCHIVE_HASH'):
                r.recover_source(repo, commit, root / 'archive.zip', '0' * 64, root / 'new')
            self.assertFalse((root / 'new').exists())

    def cli(self, repo, commit, output, **changes):
        self.module()
        arguments = {'repo-root': str(repo), 'commit': commit, 'archive-sha': '0' * 64,
                     'revision': '9' * 40, 'hf-repo': 'owner/evidence', 'hf-python': '/bin/false',
                     'output': str(output)}
        arguments.update(changes)
        command = [sys.executable, '-B', str(TOOLS / 'cloud_restore.py'), 'run']
        command += [item for key, value in arguments.items() for item in ('--' + key, value)]
        return subprocess.run(command, capture_output=True, timeout=30)

    def test_cli_refuses_existing_output_without_altering_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo, _, commit, _ = self.fixture(root)
            output = root / 'existing'
            output.mkdir()
            (output / 'keep').write_bytes(b'keep')
            result = self.cli(repo, commit, output)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(json.loads(result.stdout)['code'], 'OUTPUT_EXISTS')
            self.assertEqual([p.name for p in output.iterdir()], ['keep'])

    def test_cli_rejects_symbolic_revision_without_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo, _, commit, _ = self.fixture(root)
            result = self.cli(repo, commit, root / 'new', revision='main')
            self.assertEqual(result.returncode, 2)
            self.assertIn('FULL_', json.loads(result.stdout)['code'])
            self.assertFalse((root / 'new').exists())

    def assert_sdk_preflight_failure(self, root, sdk):
        repo, _, commit, _ = self.fixture(root)
        output = root / 'new'
        result = self.cli(repo, commit, output, **{'hf-python': str(sdk)})
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout), {'status': 'FAILED', 'code': 'HF_INTERPRETER_REQUIRED'})
        self.assertTrue((output / 'FAILURE.json').is_file(), 'SDK preflight must persist failure evidence')
        self.assertEqual(json.loads((output / 'FAILURE.json').read_bytes()),
                         {'status': 'FAILED', 'stage': 'SDK_PREFLIGHT', 'code': 'HF_INTERPRETER_REQUIRED',
                          'outputs_preserved': True})
        self.assertEqual([path.name for path in output.iterdir()], ['FAILURE.json'])

    def test_missing_interpreter_records_sdk_preflight_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assert_sdk_preflight_failure(root, root / 'missing-sdk-python')

    def test_nonexecutable_interpreter_records_sdk_preflight_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sdk = root / 'nonexecutable-sdk-python'
            sdk.write_bytes(b'raise AssertionError("this must not execute")\n')
            sdk.chmod(0o644)
            self.assert_sdk_preflight_failure(root, sdk)

    def test_worker_failure_preserves_stage_without_dev_success_or_environment(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo, _, commit, _ = self.fixture(root)
            result = self.cli(repo, commit, root / 'new')
            self.assertEqual(result.returncode, 2)
            record = json.loads((root / 'new/FAILURE.json').read_bytes())
            self.assertEqual(record['stage'], 'FETCH')
            self.assertFalse((root / 'new/RESTORE_RESULT.json').exists())
            self.assertFalse((root / 'new/DEV_START.json').exists())
            self.assertFalse((root / 'new/dev-venv').exists())

    def test_runtime_rejects_wrong_prefix_sdk_and_module_origin(self):
        r = self.module()
        venv = Path('/new/venv')
        valid = {'python': '3.12.13', 'prefix': str(venv), 'numpy_origin': str(venv / 'lib/numpy/__init__.py'),
                 'versions': {'numpy': '2.5.3', 'ruff': '0.16.7', 'ty': '0.0.80', 'codespell': '2.4.3', 'PyYAML': '6.0.3'},
                 'hf_sdk_in_app': False}
        r.validate_runtime(valid, venv)
        for key, value in [('prefix', '/old/venv'), ('hf_sdk_in_app', True), ('python', '3.12.0'),
                           ('numpy_origin', '/old/venv/lib/numpy/__init__.py')]:
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'RESTORED_RUNTIME'):
                r.validate_runtime({**valid, key: value}, venv)


class RestoredWorkflowTests(unittest.TestCase):
    root: Path

    @classmethod
    def setUpClass(cls):
        # Actual fixed workflows, not a mock of model/reference acceptance.
        scratch = tempfile.TemporaryDirectory(prefix='cloud-restore-workflow-unit-')
        cls.addClassCleanup(scratch.cleanup)
        cls.root = Path(scratch.name)
        expected = json.loads((COMPONENT / 'reference/r41_regression_expected_v1.json').read_bytes())
        for alias in ('one', 'two', 'baseline'):
            inputs = [item for name in expected['order'] for item in ('--input', COMPONENT / 'examples/r41' / name)]
            if alias == 'baseline':
                inputs += ['--baseline', cls.root / 'one/batch']
            result = subprocess.run([sys.executable, '-I', '-B', COMPONENT / 'tools/scenario_workflow.py',
                                     *inputs, '--output', cls.root / alias], capture_output=True, timeout=180)
            if result.returncode:
                raise AssertionError('Real R41 restore fixture failed')

    def module(self):
        self.assertTrue((TOOLS / 'cloud_restore.py').is_file(), 'cloud restore implementation missing')
        return importlib.import_module('cloud_restore')

    def test_actual_workflow_files_match_archive_portable_exactly(self):
        r = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            files = {'R41/' + name: raw for name, raw in portable_files(self.root / 'one').items()}
            path = Path(tmp) / 'archive.zip'
            info = seal(path, files)
            result = r.verify_restored_workflows(COMPONENT, self.root, path, info['archive_sha256'])
            self.assertEqual(result['status'], 'HF_RESTORED_R41_EXACT_PASS')
            self.assertEqual(result['portable_files'], 26)
            self.assertEqual(result['explicit_model_steps'], 972)
            self.assertEqual(result['baseline_differences'], 0)

    def test_resealed_wrong_portable_output_is_not_success(self):
        r = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            files = {'R41/' + name: raw for name, raw in portable_files(self.root / 'one').items()}
            files['R41/batch/case-001/data/TRACE.csv'] += b'changed\n'
            path = Path(tmp) / 'archive.zip'
            info = seal(path, files)
            with self.assertRaisesRegex(ValueError, 'HF_PORTABLE_MISMATCH'):
                r.verify_restored_workflows(COMPONENT, self.root, path, info['archive_sha256'])

    def test_extra_portable_member_is_rejected(self):
        r = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            files = {'R41/' + name: raw for name, raw in portable_files(self.root / 'one').items()}
            files['R41/private.log'] = b'not allowlisted'
            path = Path(tmp) / 'archive.zip'
            info = seal(path, files)
            with self.assertRaisesRegex(ValueError, 'HF_R41_MEMBER_SET'):
                r.verify_restored_workflows(COMPONENT, self.root, path, info['archive_sha256'])


if __name__ == '__main__':
    unittest.main()
