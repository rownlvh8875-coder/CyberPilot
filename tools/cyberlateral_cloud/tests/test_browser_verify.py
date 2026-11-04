"""Passive consumer tests: real saved reports, synthetic observations, no browser."""

import hashlib
import importlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
COMPONENT = TOOLS.parent / 'cyberlateral_dev'
PUBLICATION = {'RESULT.json', 'SUMMARY_KO.md', 'SHA256SUMS.txt'}


class BrowserVerifyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix='r64-test-fixture-')
        cls.base = Path(cls.temporary.name) / 'base'
        cls.base.mkdir()
        producer = importlib.import_module('browser_smoke')
        producer.prepare_reports(COMPONENT, Path(sys.executable), cls.base)
        record = importlib.import_module('browser_result_fixture').result_fixture()
        (cls.base / 'captures').mkdir()
        for name in record['captures']:
            (cls.base / 'captures' / name).write_bytes(('synthetic capture bytes ' + name).encode())
        record.update(schema_version=1, source_sha256=producer.source_snapshot(COMPONENT),
                      input_sha256=producer.tree_hashes(cls.base / 'fixture-inputs'),
                      report_sha256=producer.tree_hashes(cls.base / 'reports'),
                      captures=producer.tree_hashes(cls.base / 'captures'))
        producer.publish_result(cls.base, record)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def module(self):
        self.assertTrue((TOOLS / 'browser_verify.py').is_file(), 'passive saved-browser verifier missing')
        return importlib.import_module('browser_verify')

    def bundle(self, parent):
        return Path(shutil.copytree(self.base, Path(parent) / 'input'))

    def snapshot(self, root):
        return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob('*') if p.is_file()}

    def reseal(self, root):
        files = self.snapshot(root)
        files.pop('SHA256SUMS.txt', None)
        (root / 'SHA256SUMS.txt').write_bytes(importlib.import_module('artifacts').manifest(files))

    def write_record(self, root, record):
        producer = importlib.import_module('browser_smoke')
        owned = {n: raw for n, raw in self.snapshot(root).items() if n not in PUBLICATION}
        hashes = {n: hashlib.sha256(raw).hexdigest() for n, raw in owned.items()}
        (root / 'RESULT.json').write_bytes(producer.json_bytes(record))
        (root / 'SUMMARY_KO.md').write_bytes(importlib.import_module('browser_summary').render_summary(record, hashes))
        self.reseal(root)

    def command(self, *args):
        self.module()
        return subprocess.run([sys.executable, '-B', TOOLS / 'browser_verify.py', *map(str, args)],
                              capture_output=True, timeout=20)

    def test_complete_pass_is_read_only_and_not_a_new_browser_result(self):
        verifier = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = self.bundle(tmp)
            before = self.snapshot(root)
            result = verifier.verify_saved_browser(root)
            self.assertEqual(result, {
                'status': 'R64_SAVED_BROWSER_BUNDLE_VALID', 'recorded_status': 'R60_BROWSER_SMOKE_PASS',
                'cases': 10, 'recorded_case_failures': 0, 'recorded_failure_records': 0, 'verified_files': 38,
                'result_sha256': hashlib.sha256(before['RESULT.json']).hexdigest(),
                'reader_browser_model_F61_vehicle_executions': 0, 'source_identity_reauthenticated': False,
                'scope': 'SAVED_BYTES_AND_RECORD_CONSISTENCY_NOT_NEW_BROWSER_OR_ORIGIN_ATTESTATION'})
            self.assertEqual(self.snapshot(root), before)

    def test_loader_returns_validated_detached_bytes_not_live_paths(self):
        verifier = self.module()
        self.assertTrue(hasattr(verifier, 'load_saved_browser'), 'validated byte loader missing')
        with tempfile.TemporaryDirectory() as tmp:
            root = self.bundle(tmp)
            before = self.snapshot(root)
            receipt, files = verifier.load_saved_browser(root)
            self.assertEqual(files, before)
            self.assertEqual(len(files), 38)
            self.assertTrue(all(type(value) is bytes for value in files.values()))
            self.assertEqual(receipt['status'], 'R64_SAVED_BROWSER_BUNDLE_VALID')
            self.assertEqual(receipt['result_sha256'], hashlib.sha256(before['RESULT.json']).hexdigest())
            (root / 'captures/sign-390-top.png').write_bytes(b'changed after snapshot')
            self.assertEqual(files['captures/sign-390-top.png'], before['captures/sign-390-top.png'])

    def test_loader_never_returns_corrupt_bytes_as_validated(self):
        verifier = self.module()
        self.assertTrue(hasattr(verifier, 'load_saved_browser'), 'validated byte loader missing')
        with tempfile.TemporaryDirectory() as tmp:
            root = self.bundle(tmp)
            (root / 'captures/sign-390-top.png').write_bytes(b'bad')
            before = self.snapshot(root)
            with self.assertRaisesRegex(ValueError, '^BROWSER_BUNDLE_MANIFEST$'):
                verifier.load_saved_browser(root)
            self.assertEqual(self.snapshot(root), before)

    def test_cli_pass_is_deterministic_and_needs_no_browser_or_credentials(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.bundle(tmp)
            before = self.snapshot(root)
            first, second = self.command('--input', root), self.command('--input', root)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual((first.stdout, first.stderr), (second.stdout, b''))
            self.assertEqual(json.loads(first.stdout)['verified_files'], 38)
            self.assertEqual(self.snapshot(root), before)

    def test_help_and_reader_do_not_import_optional_or_product_modules(self):
        self.module()
        help_result = self.command('--help')
        self.assertEqual(help_result.returncode, 0, help_result.stderr)
        self.assertIn(b'--input', help_result.stdout)
        query = ("import sys; sys.path.insert(0,sys.argv[1]); import browser_verify; "
                 "from pathlib import Path; browser_verify.verify_saved_browser(Path(sys.argv[2])); "
                 "forbidden={'playwright','numpy','huggingface_hub','cyberlateral_dev','openpilot','opendbc',"
                 "'capnp','cereal','synthetic_rate_constraint_feasibility_v1'}; "
                 "assert not {n.split('.')[0] for n in sys.modules}&forbidden; print('PASS')")
        result = subprocess.run([sys.executable, '-I', '-B', '-c', query, str(TOOLS), str(self.base)],
                                capture_output=True, timeout=20)
        self.assertEqual((result.returncode, result.stdout), (0, b'PASS\n'), result.stderr)

    def test_global_only_recorded_failure_remains_exit_one(self):
        verifier = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = self.bundle(tmp)
            record = json.loads((root / 'RESULT.json').read_bytes())
            record.update(status='R60_BROWSER_SMOKE_FAIL',
                          failures=[{'codes': ['UNEXPECTED_BROWSER_REQUEST'], 'count': 1}])
            self.write_record(root, record)
            before = self.snapshot(root)
            result = self.command('--input', root)
            self.assertEqual(result.returncode, 1, result.stderr)
            saved = verifier.verify_saved_browser(root)
            self.assertEqual(saved['recorded_status'], 'R60_BROWSER_SMOKE_FAIL')
            self.assertEqual((saved['recorded_case_failures'], saved['recorded_failure_records']), (0, 1))
            self.assertEqual(self.snapshot(root), before)

    def test_case_failures_unknown_codes_and_nulls_are_preserved_not_rejudged(self):
        verifier = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = self.bundle(tmp)
            record = json.loads((root / 'RESULT.json').read_bytes())
            record.update(status='R60_BROWSER_SMOKE_FAIL',
                          failures=[{'profile': 'sign', 'width': 320, 'codes': ['FUTURE_CHECK']}])
            record['cases'][0]['failures'] = ['FUTURE_CHECK']
            record['cases'][0]['metrics']['table_position'] = None
            record['cases'][0]['metrics'].pop('min_chart_font')
            self.write_record(root, record)
            before = self.snapshot(root)
            result = verifier.verify_saved_browser(root)
            self.assertEqual((result['recorded_case_failures'], result['recorded_failure_records']), (1, 1))
            self.assertEqual(self.command('--input', root).returncode, 1)
            self.assertEqual(self.snapshot(root), before)

    def test_missing_completion_manifest_summary_or_extra_failure_is_rejected(self):
        verifier = self.module()
        for name in ['RESULT.json', 'SHA256SUMS.txt', 'SUMMARY_KO.md', 'FAILURE.json']:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                root = self.bundle(tmp)
                if name == 'FAILURE.json':
                    (root / name).write_bytes(b'{}')
                    self.reseal(root)
                else:
                    (root / name).unlink()
                before = self.snapshot(root)
                with self.assertRaisesRegex(ValueError, 'BROWSER_BUNDLE_LAYOUT'):
                    verifier.verify_saved_browser(root)
                self.assertEqual(self.snapshot(root), before)

    def test_unlisted_files_and_unexpected_empty_directories_are_not_ignored(self):
        verifier = self.module()
        for directory in [False, True]:
            with self.subTest(directory=directory), tempfile.TemporaryDirectory() as tmp:
                root = self.bundle(tmp)
                extra = root / 'unexpected'
                extra.mkdir() if directory else extra.write_bytes(b'not owned')
                with self.assertRaisesRegex(ValueError, 'BROWSER_BUNDLE_LAYOUT'):
                    verifier.verify_saved_browser(root)

    def test_corrupt_capture_fails_even_though_result_exists(self):
        verifier = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = self.bundle(tmp)
            (root / 'captures/sign-390-top.png').write_bytes(b'changed')
            before = self.snapshot(root)
            with self.assertRaisesRegex(ValueError, 'BROWSER_BUNDLE_MANIFEST'):
                verifier.verify_saved_browser(root)
            self.assertEqual(self.snapshot(root), before)

    def test_resealed_capture_still_must_match_result_hash_association(self):
        verifier = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = self.bundle(tmp)
            (root / 'captures/sign-390-top.png').write_bytes(b'changed')
            self.reseal(root)
            with self.assertRaisesRegex(ValueError, 'BROWSER_BUNDLE_RECORD'):
                verifier.verify_saved_browser(root)

    def test_nested_and_duplicate_or_escaping_root_manifest_are_rejected(self):
        verifier = self.module()
        mutations = [lambda root: (root / 'fixture-inputs/sign/SHA256SUMS.txt').write_bytes(b'bad\n'),
                     lambda root: (root / 'reports/resumed/SHA256SUMS.txt').write_bytes(b'bad\n')]
        for mutate in mutations:
            with tempfile.TemporaryDirectory() as tmp:
                root = self.bundle(tmp)
                mutate(root)
                self.reseal(root)
                with self.assertRaisesRegex(ValueError, 'BROWSER_BUNDLE_MANIFEST'):
                    verifier.verify_saved_browser(root)
        for member in ['RESULT.json', '../outside']:
            with self.subTest(member=member), tempfile.TemporaryDirectory() as tmp:
                root = self.bundle(tmp)
                path = root / 'SHA256SUMS.txt'
                path.write_bytes(path.read_bytes() + ('0' * 64 + '  ' + member + '\n').encode())
                with self.assertRaisesRegex(ValueError, 'BROWSER_BUNDLE_MANIFEST'):
                    verifier.verify_saved_browser(root)

    def test_duplicate_nonfinite_overflow_malformed_and_deep_json_are_rejected(self):
        verifier = self.module()
        original = (self.base / 'RESULT.json').read_bytes().strip()
        values = [original[:-1] + b',"status":"R60_BROWSER_SMOKE_PASS"}',
                  original[:-1] + b',"unused":NaN}', original[:-1] + b',"unused":1e9999}',
                  b'\xff', b'{bad', b'{"deep":' + b'[' * 2000 + b'0' + b']' * 2000 + b'}']
        for value in values:
            with self.subTest(prefix=value[:30]), tempfile.TemporaryDirectory() as tmp:
                root = self.bundle(tmp)
                (root / 'RESULT.json').write_bytes(value)
                self.reseal(root)
                with self.assertRaisesRegex(ValueError, 'BROWSER_BUNDLE_RECORD'):
                    verifier.verify_saved_browser(root)

    def test_schema_scope_flags_and_hash_maps_are_exact_not_coerced(self):
        verifier = self.module()
        base = json.loads((self.base / 'RESULT.json').read_bytes())
        mutations = [{'schema_version': True}, {'schema_version': 2},
                     {'model_F61_r_dt_native_vehicle_executions': False},
                     {'source_selected_files_unchanged': 1}, {'fixture_runtime_attestation': 0},
                     {'source_sha256': {}}, {'input_sha256': {}}, {'report_sha256': {}}, {'captures': {}}]
        for change in mutations:
            with self.subTest(change=change), tempfile.TemporaryDirectory() as tmp:
                root = self.bundle(tmp)
                (root / 'RESULT.json').write_text(json.dumps(base | change))
                self.reseal(root)
                with self.assertRaisesRegex(ValueError, 'BROWSER_BUNDLE_RECORD'):
                    verifier.verify_saved_browser(root)

    def test_incomplete_reordered_and_contradictory_records_are_rejected(self):
        verifier = self.module()
        base = json.loads((self.base / 'RESULT.json').read_bytes())
        values = [deepcopy(base) for _ in range(3)]
        values[0]['cases'].pop()
        values[1]['cases'].reverse()
        values[2]['failures'] = [{'codes': ['UNEXPECTED_BROWSER_REQUEST'], 'count': 1}]
        for value in values:
            with tempfile.TemporaryDirectory() as tmp:
                root = self.bundle(tmp)
                (root / 'RESULT.json').write_text(json.dumps(value))
                self.reseal(root)
                with self.assertRaisesRegex(ValueError, 'BROWSER_BUNDLE_RECORD'):
                    verifier.verify_saved_browser(root)

    def test_resealed_summary_disagreement_is_not_repaired(self):
        verifier = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = self.bundle(tmp)
            (root / 'SUMMARY_KO.md').write_bytes(b'false success summary\n')
            self.reseal(root)
            before = self.snapshot(root)
            with self.assertRaisesRegex(ValueError, 'BROWSER_BUNDLE_SUMMARY'):
                verifier.verify_saved_browser(root)
            self.assertEqual(self.snapshot(root), before)

    def test_root_parent_and_file_symlinks_are_not_followed(self):
        verifier = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = self.bundle(tmp)
            alias = Path(tmp) / 'alias'
            alias.symlink_to(root, target_is_directory=True)
            for path in [alias, alias / 'reports']:
                with self.subTest(path=path), self.assertRaisesRegex(ValueError, 'BROWSER_BUNDLE_PATH'):
                    verifier.verify_saved_browser(path)
            capture = root / 'captures/sign-390-top.png'
            capture.unlink()
            capture.symlink_to(self.base / 'captures/sign-390-top.png')
            with self.assertRaisesRegex(ValueError, 'BROWSER_BUNDLE_LAYOUT'):
                verifier.verify_saved_browser(root)

    def test_fifo_is_rejected_without_waiting_for_a_writer(self):
        self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = self.bundle(tmp)
            capture = root / 'captures/sign-390-top.png'
            capture.unlink()
            os.mkfifo(capture)
            result = self.command('--input', root)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn(b'BROWSER_BUNDLE_LAYOUT', result.stderr)

    def test_file_and_total_size_bounds_precede_content_reads(self):
        verifier = self.module()
        for count, size in [(1, 8 * 1024 * 1024 + 1), (5, 7 * 1024 * 1024)]:
            with self.subTest(count=count), tempfile.TemporaryDirectory() as tmp:
                root = self.bundle(tmp)
                for path in sorted((root / 'captures').iterdir())[:count]:
                    with path.open('wb') as stream:
                        stream.truncate(size)
                with self.assertRaisesRegex(ValueError, 'BROWSER_BUNDLE_LIMIT'):
                    verifier.verify_saved_browser(root)

    def test_invalid_cli_has_no_traceback_path_leak_or_new_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'private-marker-missing'
            result = self.command('--input', path)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, b'')
            self.assertEqual(result.stderr, b'REJECTED: BROWSER_BUNDLE_PATH\n')
            self.assertFalse(path.exists())
            self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_relative_path_io_failure_is_bounded_even_if_working_directory_disappears(self):
        self.module()
        query = ("import sys,os,tempfile; from pathlib import Path; sys.path.insert(0,sys.argv[1]); "
                 "import browser_verify; "
                 "tmp=tempfile.TemporaryDirectory(); dead=Path(tmp.name)/'gone'; dead.mkdir(); "
                 "os.chdir(dead); dead.rmdir(); raise SystemExit(browser_verify.main(['--input','relative']))")
        result = subprocess.run([sys.executable, '-I', '-B', '-c', query, str(TOOLS)],
                                capture_output=True, timeout=20)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(result.stdout, b'')
        self.assertEqual(result.stderr, b'REJECTED: BROWSER_BUNDLE_IO\n')


if __name__ == '__main__':
    unittest.main()
