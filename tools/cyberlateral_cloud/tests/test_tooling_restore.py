"""Real local Git and saved bundles; no network or execution of recovered code."""

import hashlib
import importlib
import json
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
artifacts = importlib.import_module('artifacts')


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()


def make_saved_template(root):
    base = root / 'saved-base'
    base.mkdir()
    producer = importlib.import_module('browser_smoke')
    producer.prepare_reports(TOOLS.parent / 'cyberlateral_dev', Path(sys.executable), base)
    record = importlib.import_module('browser_result_fixture').result_fixture()
    (base / 'captures').mkdir()
    for name in record['captures']:
        (base / 'captures' / name).write_bytes(('synthetic saved ' + name).encode())
    record.update(schema_version=1, source_sha256=producer.source_snapshot(TOOLS.parent / 'cyberlateral_dev'),
                  input_sha256=producer.tree_hashes(base / 'fixture-inputs'),
                  report_sha256=producer.tree_hashes(base / 'reports'), captures=producer.tree_hashes(base / 'captures'))
    producer.publish_result(base, record)
    return {p.relative_to(base).as_posix(): p.read_bytes() for p in base.rglob('*') if p.is_file()}


def reseal(values):
    values['SHA256SUMS.txt'] = artifacts.manifest({n: r for n, r in values.items() if n != 'SHA256SUMS.txt'})


def receipt(values):
    record = json.loads(values['RESULT.json'])
    return {'status': 'R64_SAVED_BROWSER_BUNDLE_VALID', 'recorded_status': record['status'],
            'cases': 10, 'recorded_case_failures': sum(bool(v['failures']) for v in record['cases']),
            'recorded_failure_records': len(record['failures']), 'verified_files': 38,
            'result_sha256': hashlib.sha256(values['RESULT.json']).hexdigest(),
            'reader_browser_model_F61_vehicle_executions': 0, 'source_identity_reauthenticated': False,
            'scope': 'SAVED_BYTES_AND_RECORD_CONSISTENCY_NOT_NEW_BROWSER_OR_ORIGIN_ATTESTATION'}


def archive_fixture(root, saved):
    repo = root / 'repo'
    subprocess.run(['git', 'init', '-q', repo], check=True)
    source = {'tools/cyberlateral_cloud/browser_compare.py': b'raise RuntimeError("SOURCE must not execute")\r\n',
              'tools/cyberlateral_cloud/browser_compare_summary.py': b'original\r\n'}
    for name, raw in source.items():
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        path.chmod(0o755 if name.endswith('/browser_compare.py') else 0o644)
    subprocess.run(['git', '-C', repo, 'add', '.'], check=True)
    subprocess.run(['git', '-C', repo, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                    'commit', '-qm', 'fixture'], check=True)
    commit = subprocess.check_output(['git', '-C', repo, 'rev-parse', 'HEAD']).decode().strip()
    tree = subprocess.check_output(['git', '-C', repo, 'rev-parse', 'HEAD^{tree}']).decode().strip()
    records = {name: {'sha256': hashlib.sha256(raw).hexdigest(), 'byte_size': len(raw),
                     'git_blob': subprocess.check_output(['git', '-C', repo, 'hash-object', repo / name]).decode().strip(),
                     'git_mode': '100755' if name.endswith('/browser_compare.py') else '100644'}
               for name, raw in source.items()}
    identity = {'commit': commit, 'tree': tree, 'files': records,
                'scope': 'COMMITTED_CLOUD_TOOLS_AND_R67_DOCS_NOT_DEV_APP_FULL_REPO_OR_VEHICLE_INSTALL'}
    files = {'SOURCE/' + name: raw for name, raw in source.items()}
    files['SOURCE_IDENTITY.json'] = encoded(identity)
    files['DRIVER/not_executed.py'] = b'raise AssertionError("must not run DRIVER")\n'
    saved_records = {}
    for alias in ['one', 'two', 'fail']:
        values = dict(saved)
        if alias == 'two':
            values['fixture-preparation.log'] = b'changed saved log\n'
            reseal(values)
        elif alias == 'fail':
            record = json.loads(values['RESULT.json'])
            record.update(status='R60_BROWSER_SMOKE_FAIL', failures=[{'codes': ['UNEXPECTED_BROWSER_REQUEST'], 'count': 1}])
            values['RESULT.json'] = encoded(record)
            owned = {n: hashlib.sha256(raw).hexdigest() for n, raw in values.items()
                     if n not in {'RESULT.json', 'SUMMARY_KO.md', 'SHA256SUMS.txt'}}
            values['SUMMARY_KO.md'] = importlib.import_module('browser_summary').render_summary(record, owned)
            reseal(values)
        files.update({'SAVED/' + alias + '/' + name: raw for name, raw in values.items()})
        saved_records[alias] = {'recorded_receipt': receipt(values), 'files': {
            n: {'sha256': hashlib.sha256(raw).hexdigest(), 'byte_size': len(raw), 'mode': 0o644}
            for n, raw in values.items()}}
    files['SAVED_IDENTITY.json'] = encoded(saved_records)
    return repo, commit, identity, files


class ToolingRestoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix='r68-tool-fixture-')
        cls.saved = make_saved_template(Path(cls.temporary.name))

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def module(self):
        self.assertTrue((TOOLS / 'tooling_restore.py').is_file(), 'supplementary tooling recovery missing')
        return importlib.import_module('tooling_restore')

    def recover(self, module, root, repo, commit, files, output=None, digest=None):
        archive = root / 'archive.zip'
        info = artifacts.seal(archive, files)
        return module.recover_tooling(repo, commit, archive, digest or info['archive_sha256'], output or root / 'new')

    # Catch copying dirty bytes, newline conversion, lost modes and archived-code execution.
    def test_git_exact_source_modes_and_saved_statuses_without_driver_execution(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo, commit, identity, files = archive_fixture(root, self.saved)
            dirty = repo / 'tools/cyberlateral_cloud/browser_compare_summary.py'
            dirty.write_bytes(b'user edits')
            (dirty.parent / 'untracked').write_bytes(b'preserve')
            result = self.recover(m, root, repo, commit, files)
            self.assertEqual(result['status'], 'EXACT_GIT_MATCHED_TOOLING_AND_SAVED_RECOVERED')
            self.assertEqual((result['source_files'], result['saved_files']), (2, 114))
            self.assertEqual(result['identity'], identity)
            self.assertEqual((root / 'new/source/tools/cyberlateral_cloud/browser_compare_summary.py').read_bytes(), b'original\r\n')
            self.assertEqual(stat.S_IMODE((root / 'new/source/tools/cyberlateral_cloud/browser_compare.py').stat().st_mode), 0o755)
            self.assertEqual(result['original_receipts']['fail']['recorded_status'], 'R60_BROWSER_SMOKE_FAIL')
            self.assertEqual(result['original_receipts']['fail']['recorded_case_failures'], 0)
            self.assertEqual(result['original_receipts']['fail']['recorded_failure_records'], 1)
            self.assertEqual(result['downloaded_driver_executions'], 0)
            self.assertFalse((root / 'new/DRIVER').exists())
            self.assertEqual(dirty.read_bytes(), b'user edits')
            self.assertEqual((dirty.parent / 'untracked').read_bytes(), b'preserve')

    def test_resealed_source_substitution_is_rejected_before_destination(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo, commit, _, files = archive_fixture(root, self.saved)
            files['SOURCE/tools/cyberlateral_cloud/browser_compare.py'] = b'substituted'
            with self.assertRaisesRegex(ValueError, '^TOOL_SOURCE_GIT_MISMATCH$'):
                self.recover(m, root, repo, commit, files)
            self.assertFalse((root / 'new').exists())

    def test_resealed_missing_extra_source_members_are_not_recovered(self):
        m = self.module()
        for extra in [False, True]:
            with self.subTest(extra=extra), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                repo, commit, _, files = archive_fixture(root, self.saved)
                if extra:
                    files['SOURCE/.git/config'] = b'unexpected'
                else:
                    del files['SOURCE/tools/cyberlateral_cloud/browser_compare.py']
                with self.assertRaisesRegex(ValueError, '^TOOL_SOURCE_MEMBER_SET$'):
                    self.recover(m, root, repo, commit, files)
                self.assertFalse((root / 'new').exists())

    def test_identity_forgery_including_bool_size_does_not_match_git(self):
        m = self.module()
        for field, value in [('tree', '0' * 40), ('commit', '0' * 40), ('scope', 'full vehicle'),
                             ('git_blob', '0' * 40), ('git_mode', '100644'), ('sha256', '0' * 64), ('byte_size', True)]:
            with self.subTest(field=field), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                repo, commit, identity, files = archive_fixture(root, self.saved)
                target = identity if field in ['tree', 'commit', 'scope'] else identity['files']['tools/cyberlateral_cloud/browser_compare.py']
                target[field] = value
                files['SOURCE_IDENTITY.json'] = encoded(identity)
                with self.assertRaisesRegex(ValueError, '^TOOL_SOURCE_IDENTITY_MISMATCH$'):
                    self.recover(m, root, repo, commit, files)
                self.assertFalse((root / 'new').exists())

    def test_duplicate_or_nonfinite_metadata_is_not_accepted(self):
        m = self.module()
        for name, raw in [('SOURCE_IDENTITY.json', b'{"commit":"x","commit":"y"}'),
                          ('SAVED_IDENTITY.json', b'{"value":NaN}')]:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                repo, commit, _, files = archive_fixture(root, self.saved)
                files[name] = raw
                with self.assertRaisesRegex(ValueError, '^TOOL_METADATA_INVALID$'):
                    self.recover(m, root, repo, commit, files)

    def test_saved_member_metadata_hash_size_and_mode_must_match(self):
        m = self.module()
        for field, value in [('sha256', '0' * 64), ('byte_size', True), ('mode', True), ('mode', 0o4755)]:
            with self.subTest(field=field), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                repo, commit, _, files = archive_fixture(root, self.saved)
                meta = json.loads(files['SAVED_IDENTITY.json'])
                meta['one']['files']['fixture-preparation.log'][field] = value
                files['SAVED_IDENTITY.json'] = encoded(meta)
                with self.assertRaisesRegex(ValueError, '^TOOL_SAVED_IDENTITY_MISMATCH$'):
                    self.recover(m, root, repo, commit, files)

    def test_saved_layout_inner_manifest_and_recorded_receipt_are_bound(self):
        m = self.module()
        for kind, code in [('extra', 'TOOL_SAVED_MEMBER_SET'), ('manifest', 'BROWSER_BUNDLE_MANIFEST'),
                           ('receipt', 'TOOL_SAVED_RECEIPT_MISMATCH')]:
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                repo, commit, _, files = archive_fixture(root, self.saved)
                if kind == 'extra':
                    files['SAVED/one/private.log'] = b'extra'
                else:
                    meta = json.loads(files['SAVED_IDENTITY.json'])
                    if kind == 'manifest':
                        files['SAVED/one/fixture-preparation.log'] = b'inner tamper'
                        item = meta['one']['files']['fixture-preparation.log']
                        item.update(sha256=hashlib.sha256(b'inner tamper').hexdigest(), byte_size=12)
                    else:
                        meta['fail']['recorded_receipt']['recorded_status'] = 'R60_BROWSER_SMOKE_PASS'
                    files['SAVED_IDENTITY.json'] = encoded(meta)
                with self.assertRaisesRegex(ValueError, '^' + code + '$'):
                    self.recover(m, root, repo, commit, files)

    def test_output_conflicts_symlinks_and_repo_paths_preserve_existing_data(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo, commit, _, files = archive_fixture(root, self.saved)
            archive = root / 'archive.zip'
            info = artifacts.seal(archive, files)
            existing = root / 'existing'
            existing.mkdir()
            (existing / 'keep').write_bytes(b'keep')
            alias = root / 'alias'
            alias.symlink_to(existing, target_is_directory=True)
            for output, code in [(existing, 'OUTPUT_EXISTS'), (alias / 'new', 'RESTORE_PATH_SYMLINK'),
                                 (repo / 'new', 'EXTERNAL_OUTPUT_REQUIRED')]:
                with self.subTest(code=code), self.assertRaisesRegex((ValueError, FileExistsError), code):
                    m.recover_tooling(repo, commit, archive, info['archive_sha256'], output)
            self.assertEqual((existing / 'keep').read_bytes(), b'keep')
            self.assertEqual(list(existing.iterdir()), [existing / 'keep'])

    def test_changed_archive_digest_never_writes_destination(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo, commit, _, files = archive_fixture(root, self.saved)
            with self.assertRaisesRegex(ValueError, '^ARCHIVE_HASH$'):
                self.recover(m, root, repo, commit, files, digest='0' * 64)
            self.assertFalse((root / 'new').exists())


if __name__ == '__main__':
    unittest.main()
