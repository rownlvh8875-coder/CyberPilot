"""Exact byte comparison of real saved bundles; synthetic observations, no browser."""

import hashlib
import importlib
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))


class BrowserCompareTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix='r66-fixture-')
        cls.base = Path(cls.temporary.name) / 'base'
        cls.base.mkdir()
        producer = importlib.import_module('browser_smoke')
        component = TOOLS.parent / 'cyberlateral_dev'
        producer.prepare_reports(component, Path(sys.executable), cls.base)
        record = importlib.import_module('browser_result_fixture').result_fixture()
        (cls.base / 'captures').mkdir()
        for name in record['captures']:
            (cls.base / 'captures' / name).write_bytes(('saved capture ' + name).encode())
        record.update(schema_version=1, source_sha256=producer.source_snapshot(component),
                      input_sha256=producer.tree_hashes(cls.base / 'fixture-inputs'),
                      report_sha256=producer.tree_hashes(cls.base / 'reports'),
                      captures=producer.tree_hashes(cls.base / 'captures'))
        producer.publish_result(cls.base, record)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def module(self):
        self.assertTrue((TOOLS / 'browser_compare.py').is_file(), 'saved browser comparator missing')
        return importlib.import_module('browser_compare')

    def pair(self, parent):
        return tuple(Path(shutil.copytree(self.base, Path(parent) / name)) for name in ['baseline', 'candidate'])

    def files(self, root):
        return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob('*') if p.is_file()}

    def state(self, root):
        return (self.files(root), sorted(p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_dir()),
                {p.relative_to(root).as_posix(): stat.S_IMODE(p.stat().st_mode) for p in root.rglob('*')})

    def reseal(self, root):
        values = self.files(root)
        values.pop('SHA256SUMS.txt')
        (root / 'SHA256SUMS.txt').write_bytes(importlib.import_module('artifacts').manifest(values))

    def write_record(self, root, record):
        producer = importlib.import_module('browser_smoke')
        owned = {n: raw for n, raw in self.files(root).items() if n not in {'RESULT.json', 'SUMMARY_KO.md', 'SHA256SUMS.txt'}}
        (root / 'RESULT.json').write_bytes(producer.json_bytes(record))
        (root / 'SUMMARY_KO.md').write_bytes(importlib.import_module('browser_summary').render_summary(
            record, {n: hashlib.sha256(raw).hexdigest() for n, raw in owned.items()}))
        self.reseal(root)

    def fail_record(self, root):
        record = json.loads((root / 'RESULT.json').read_bytes())
        record.update(status='R60_BROWSER_SMOKE_FAIL', failures=[{'codes': ['UNEXPECTED_BROWSER_REQUEST'], 'count': 1}])
        self.write_record(root, record)

    def command(self, *args):
        self.module()
        return subprocess.run([sys.executable, '-B', TOOLS / 'browser_compare.py', *map(str, args)],
                              capture_output=True, timeout=20)

    def test_equal_copies_compare_all_owned_bytes_without_mutation(self):
        comparator = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            left, right = self.pair(tmp)
            before = self.state(left), self.state(right)
            result = comparator.compare_saved_browser(left, right)
            self.assertEqual(result['status'], 'R66_SAVED_BROWSER_EXACT_BYTES_MATCH')
            self.assertEqual((result['compared_files'], result['changed_files'], result['unchanged_files']), (38, 0, 38))
            self.assertEqual(result['differences'], [])
            self.assertEqual(result['comparison'], 'EXACT_SAVED_BYTES')
            self.assertEqual(result['quality_assessment'], 'NOT_PERFORMED')
            self.assertIs(result['source_identity_reauthenticated'], False)
            self.assertEqual(result['comparator_browser_model_F61_vehicle_executions'], 0)
            self.assertEqual((self.state(left), self.state(right)), before)

    def test_same_path_is_allowed_but_does_not_skip_validation(self):
        comparator = self.module()
        result = comparator.compare_saved_browser(self.base, self.base)
        self.assertEqual((result['changed_files'], result['unchanged_files']), (0, 38))
        with tempfile.TemporaryDirectory() as tmp:
            left, _ = self.pair(tmp)
            (left / 'RESULT.json').unlink()
            with self.assertRaisesRegex(ValueError, '^BASELINE_BROWSER_BUNDLE_LAYOUT$'):
                comparator.compare_saved_browser(left, left)

    def test_log_difference_is_found_even_when_result_receipts_are_equal(self):
        comparator = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            left, right = self.pair(tmp)
            (right / 'fixture-preparation.log').write_bytes(b'exact new log\n')
            self.reseal(right)
            result = comparator.compare_saved_browser(left, right)
            self.assertEqual(result['status'], 'R66_SAVED_BROWSER_BYTES_DIFFERENT')
            self.assertEqual(result['baseline_verification'], result['candidate_verification'])
            self.assertEqual((result['changed_files'], result['unchanged_files']), (2, 36))
            self.assertEqual([d['path'] for d in result['differences']], ['SHA256SUMS.txt', 'fixture-preparation.log'])
            difference = result['differences'][1]
            self.assertEqual(difference['candidate'], {'sha256': hashlib.sha256(b'exact new log\n').hexdigest(), 'byte_size': 14})

    def test_resealed_capture_change_reports_exact_size_and_hash(self):
        comparator = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            left, right = self.pair(tmp)
            name = 'captures/sign-390-top.png'
            old = (left / name).read_bytes()
            (right / name).write_bytes(b'new')
            record = json.loads((right / 'RESULT.json').read_bytes())
            record['captures']['sign-390-top.png'] = hashlib.sha256(b'new').hexdigest()
            self.write_record(right, record)
            result = comparator.compare_saved_browser(left, right)
            self.assertEqual([d['path'] for d in result['differences']], ['RESULT.json', 'SHA256SUMS.txt', name])
            self.assertEqual(result['differences'][2], {'path': name,
                'baseline': {'sha256': hashlib.sha256(old).hexdigest(), 'byte_size': len(old)},
                'candidate': {'sha256': hashlib.sha256(b'new').hexdigest(), 'byte_size': 3}})

    def test_json_spelling_is_not_silently_normalized(self):
        comparator = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            left, right = self.pair(tmp)
            path = right / 'RESULT.json'
            path.write_bytes(path.read_bytes() + b' \n')
            self.reseal(right)
            result = comparator.compare_saved_browser(left, right)
            self.assertEqual([d['path'] for d in result['differences']], ['RESULT.json', 'SHA256SUMS.txt'])

    def test_difference_order_is_sorted_not_creation_or_argument_order(self):
        comparator = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            left, right = self.pair(tmp)
            for name in ['sign-render.log', 'fixture-preparation.log', 'resumed-render.log']:
                (right / name).write_bytes(b'different')
            self.reseal(right)
            forward = comparator.compare_saved_browser(left, right)
            reverse = comparator.compare_saved_browser(right, left)
            wanted = ['SHA256SUMS.txt', 'fixture-preparation.log', 'resumed-render.log', 'sign-render.log']
            self.assertEqual([d['path'] for d in forward['differences']], wanted)
            self.assertEqual([d['path'] for d in reverse['differences']], wanted)
            self.assertEqual(forward['differences'][1]['candidate'], reverse['differences'][1]['baseline'])

    def test_identical_recorded_fail_is_match_not_new_quality_pass(self):
        self.module()
        with tempfile.TemporaryDirectory() as tmp:
            left, right = self.pair(tmp)
            self.fail_record(left)
            self.fail_record(right)
            result = self.command('--baseline', left, '--candidate', right)
            self.assertEqual((result.returncode, result.stderr), (0, b''))
            record = json.loads(result.stdout)
            self.assertEqual(record['status'], 'R66_SAVED_BROWSER_EXACT_BYTES_MATCH')
            for side in ['baseline_verification', 'candidate_verification']:
                self.assertEqual(record[side]['recorded_status'], 'R60_BROWSER_SMOKE_FAIL')
                self.assertEqual(record[side]['recorded_failure_records'], 1)
            self.assertEqual(record['quality_assessment'], 'NOT_PERFORMED')

    def test_original_pass_fail_difference_is_preserved_without_rejudging_metrics(self):
        self.module()
        with tempfile.TemporaryDirectory() as tmp:
            left, right = self.pair(tmp)
            self.fail_record(right)
            result = self.command('--baseline', left, '--candidate', right)
            self.assertEqual((result.returncode, result.stderr), (1, b''))
            record = json.loads(result.stdout)
            self.assertEqual(record['baseline_verification']['recorded_status'], 'R60_BROWSER_SMOKE_PASS')
            self.assertEqual(record['candidate_verification']['recorded_status'], 'R60_BROWSER_SMOKE_FAIL')
            self.assertEqual(record['changed_files'], 3)
            self.assertEqual(record['quality_assessment'], 'NOT_PERFORMED')

    def test_cli_is_deterministic_path_free_and_read_only_for_match_and_difference(self):
        self.module()
        with tempfile.TemporaryDirectory() as tmp:
            left, right = self.pair(tmp)
            for changed in [False, True]:
                if changed:
                    (right / 'sign-render.log').write_bytes(b'new log')
                    self.reseal(right)
                before = self.state(left), self.state(right)
                one = self.command('--baseline', left, '--candidate', right)
                two = self.command('--baseline', left, '--candidate', right)
                self.assertEqual(one.returncode, 1 if changed else 0, one.stderr)
                self.assertEqual((one.stdout, one.stderr), (two.stdout, b''))
                self.assertNotIn(str(Path(tmp)).encode(), one.stdout)
                self.assertEqual((self.state(left), self.state(right)), before)

    def test_corrupt_operand_is_side_specific_rejection_not_difference(self):
        comparator = self.module()
        for side in [0, 1]:
            with self.subTest(side=side), tempfile.TemporaryDirectory() as tmp:
                pair = self.pair(tmp)
                (pair[side] / 'captures/sign-390-top.png').write_bytes(b'corrupt')
                code = ('BASELINE' if side == 0 else 'CANDIDATE') + '_BROWSER_BUNDLE_MANIFEST'
                with self.assertRaisesRegex(ValueError, '^' + code + '$'):
                    comparator.compare_saved_browser(*pair)
                result = self.command('--baseline', pair[0], '--candidate', pair[1])
                self.assertEqual((result.returncode, result.stdout, result.stderr), (2, b'', ('REJECTED: ' + code + '\n').encode()))

    def test_partial_or_extra_input_on_either_side_is_not_compared(self):
        comparator = self.module()
        for side in [0, 1]:
            for extra in [False, True]:
                with self.subTest(side=side, extra=extra), tempfile.TemporaryDirectory() as tmp:
                    pair = self.pair(tmp)
                    (pair[side] / 'extra').mkdir() if extra else (pair[side] / 'RESULT.json').unlink()
                    with self.assertRaisesRegex(ValueError, '^(BASELINE|CANDIDATE)_BROWSER_BUNDLE_LAYOUT$'):
                        comparator.compare_saved_browser(*pair)

    def test_bad_records_are_rejected_before_partial_stdout(self):
        self.module()
        for side in [0, 1]:
            for raw in [b'{"schema_version":true}', b'{"x":1,"x":2}', b'{"x":NaN}', b'{bad']:
                with self.subTest(side=side, raw=raw), tempfile.TemporaryDirectory() as tmp:
                    pair = self.pair(tmp)
                    (pair[side] / 'RESULT.json').write_bytes(raw)
                    self.reseal(pair[side])
                    result = self.command('--baseline', pair[0], '--candidate', pair[1])
                    code = ('BASELINE' if side == 0 else 'CANDIDATE') + '_BROWSER_BUNDLE_RECORD'
                    self.assertEqual((result.returncode, result.stdout, result.stderr), (2, b'', ('REJECTED: ' + code + '\n').encode()))

    def test_root_and_leaf_symlinks_on_either_side_are_rejected(self):
        comparator = self.module()
        for side in [0, 1]:
            for leaf in [False, True]:
                with self.subTest(side=side, leaf=leaf), tempfile.TemporaryDirectory() as tmp:
                    pair = list(self.pair(tmp))
                    if leaf:
                        path = pair[side] / 'captures/sign-390-top.png'
                        path.unlink()
                        path.symlink_to(self.base / 'captures/sign-390-top.png')
                    else:
                        alias = Path(tmp) / 'alias'
                        alias.symlink_to(pair[side], target_is_directory=True)
                        pair[side] = alias
                    with self.assertRaisesRegex(ValueError, '^(BASELINE|CANDIDATE)_BROWSER_BUNDLE_(PATH|LAYOUT)$'):
                        comparator.compare_saved_browser(*pair)

    def test_fifo_operand_rejects_without_waiting_for_writer(self):
        self.module()
        with tempfile.TemporaryDirectory() as tmp:
            left, right = self.pair(tmp)
            path = right / 'captures/sign-390-top.png'
            path.unlink()
            os.mkfifo(path)
            result = self.command('--baseline', left, '--candidate', right)
            self.assertEqual((result.returncode, result.stdout, result.stderr), (2, b'', b'REJECTED: CANDIDATE_BROWSER_BUNDLE_LAYOUT\n'))

    def test_file_and_total_bounds_apply_to_each_operand(self):
        comparator = self.module()
        for side in [0, 1]:
            for count, size in [(1, 8 * 1024 * 1024 + 1), (5, 7 * 1024 * 1024)]:
                with self.subTest(side=side, count=count), tempfile.TemporaryDirectory() as tmp:
                    pair = self.pair(tmp)
                    for path in sorted((pair[side] / 'captures').iterdir())[:count]:
                        with path.open('wb') as stream:
                            stream.truncate(size)
                    with self.assertRaisesRegex(ValueError, '^(BASELINE|CANDIDATE)_BROWSER_BUNDLE_LIMIT$'):
                        comparator.compare_saved_browser(*pair)

    def test_help_and_api_do_not_import_optional_or_product_modules(self):
        self.module()
        help_result = self.command('--help')
        self.assertEqual(help_result.returncode, 0, help_result.stderr)
        self.assertIn(b'--baseline', help_result.stdout)
        self.assertIn(b'--candidate', help_result.stdout)
        query = ("import sys;sys.path.insert(0,sys.argv[1]);import browser_compare;from pathlib import Path;"
                 "browser_compare.compare_saved_browser(Path(sys.argv[2]),Path(sys.argv[2]));"
                 "bad={'playwright','numpy','huggingface_hub','cyberlateral_dev','openpilot','opendbc','capnp','cereal',"
                 "'synthetic_rate_constraint_feasibility_v1'};assert not {n.split('.')[0] for n in sys.modules}&bad;print('PASS')")
        result = subprocess.run([sys.executable, '-I', '-B', '-c', query, str(TOOLS), str(self.base)],
                                capture_output=True, timeout=20)
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, b'PASS\n', b''))

    def test_missing_baseline_precedes_missing_candidate_without_path_leak(self):
        self.module()
        with tempfile.TemporaryDirectory() as tmp:
            result = self.command('--baseline', Path(tmp) / 'private-left', '--candidate', Path(tmp) / 'private-right')
            self.assertEqual((result.returncode, result.stdout, result.stderr), (2, b'', b'REJECTED: BASELINE_BROWSER_BUNDLE_PATH\n'))
            self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_cli_requires_full_flags_and_both_operands(self):
        self.module()
        for args in [[], ['--baseline', self.base], ['--base', self.base, '--candidate', self.base]]:
            with self.subTest(args=args):
                result = self.command(*args)
                self.assertEqual((result.returncode, result.stdout), (2, b''))
                self.assertNotIn(b'Traceback', result.stderr)


if __name__ == '__main__':
    unittest.main()
