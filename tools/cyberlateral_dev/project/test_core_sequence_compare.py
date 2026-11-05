"""Stored comparison catches hidden metadata/input differences without replay."""

import hashlib
import importlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from v1_helpers import ROOT


class CoreSequenceCompareTests(unittest.TestCase):
    def module(self):
        self.assertTrue((ROOT / 'integration_tools/core_sequence_compare.py').is_file(), 'Missing CORE10 saved comparison')
        self.assertTrue((ROOT / 'tools/core_sequence_compare.py').is_file(), 'Missing CORE10 comparison CLI')
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        return importlib.import_module('integration_tools.core_sequence_compare')

    def fixture(self, root, name, case='sign-cycle'):
        producer = importlib.import_module('integration_tools.core_sequence_run')
        path = root / name
        producer.run_sequence_case(case, path)
        return path

    def pair(self, root):
        left = self.fixture(root, 'left')
        right = root / 'right'
        shutil.copytree(left, right)
        return left, right

    def refresh(self, folder):
        (folder / 'SHA256SUMS.txt').write_bytes(''.join(hashlib.sha256((folder / name).read_bytes()).hexdigest()
            + '  ' + name + '\n' for name in ('INPUT.json', 'RESULTS.json')).encode())

    def edit(self, folder, name, change):
        path = folder / name
        value = json.loads(path.read_bytes())
        change(value)
        path.write_bytes((json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode())
        self.refresh(folder)

    def command(self, left, right, fmt='json'):
        return subprocess.run([sys.executable, '-I', '-B', ROOT / 'tools/core_sequence_compare.py',
            '--left', left, '--right', right, '--format', fmt], capture_output=True)

    def test_loader_exposes_same_owned_records_and_preserves_core9_summary(self):
        self.module()
        saved = importlib.import_module('integration_tools.core_sequence_saved')
        with tempfile.TemporaryDirectory() as tmp:
            folder = self.fixture(Path(tmp), 'packet')
            loaded = saved.read_saved_sequence_records(folder)
            self.assertEqual(set(loaded), {'input_record', 'result_record', 'summary'})
            self.assertEqual(loaded['input_record'], json.loads((folder / 'INPUT.json').read_bytes()))
            self.assertEqual(loaded['result_record'], json.loads((folder / 'RESULTS.json').read_bytes()))
            self.assertEqual(loaded['summary'], saved.inspect_saved_sequence(folder))
            self.assertEqual(loaded['summary']['saved_status'], 'MATCH')
            self.assertEqual([r['computed_limited_state'] for r in loaded['summary']['rows']], [2, -2, 2])

    def test_all_three_saved_outcomes_self_compare_identically_not_fresh_verdicts(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            for case, status in [('sign-cycle', 'MATCH'), ('declared-difference', 'DIFFERENT'), ('late-invalid', 'REJECTED')]:
                folder = self.fixture(Path(tmp), case, case)
                r = m.compare_saved_sequences(folder, folder)
                self.assertEqual(r['comparison_status'], 'SAVED_PACKAGES_IDENTICAL')
                self.assertEqual((r['difference_count'], r['reported_difference_count'], r['differences']), (0, 0, []))
                self.assertEqual((r['left']['saved_status'], r['right']['saved_status']), (status, status))
                self.assertFalse(r['differences_truncated'])
                self.assertFalse(r['source_identity_reauthenticated'])
                self.assertFalse(r['arithmetic_recomputed'])
                self.assertEqual((r['comparison_model_executions'], r['comparison_reference_executions']), (0, 0))

    def test_mirror_locations_are_not_portable_differences(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            left, right = self.pair(Path(tmp))
            r = m.compare_saved_sequences(left, right)
            self.assertEqual(r, m.compare_saved_sequences(left, left))
            self.assertNotIn(tmp, m.render_comparison(r).decode())

    def test_every_valid_case_pair_is_diagnostic_not_a_physics_comparability_claim(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            folders = {case: self.fixture(Path(tmp), case, case) for case in ('sign-cycle', 'declared-difference', 'late-invalid')}
            for a, left in folders.items():
                for b, right in folders.items():
                    r = m.compare_saved_sequences(left, right)
                    self.assertEqual(r['same_case_id'], a == b)
                    self.assertEqual(r['comparison_status'], 'SAVED_PACKAGES_IDENTICAL' if a == b else 'SAVED_PACKAGES_DIFFERENT')
                    self.assertEqual(r['difference_count'] == 0, a == b)

    def test_input_change_hidden_from_old_summary_rows_is_localized(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            left, right = self.pair(Path(tmp))
            self.edit(right, 'INPUT.json', lambda r: r['frames'][0]['request'].update(requested_binary32_be_hex='be000000'))
            r = m.compare_saved_sequences(left, right)
            self.assertEqual(r['difference_counts'], {'INPUT': 1, 'RESULT': 0, 'IDENTITY': 0})
            self.assertEqual(r['differences'], [{'path': '/INPUT.json/frames/0/request/requested_binary32_be_hex',
                'section': 'INPUT', 'kind': 'VALUE_CHANGED', 'left_present': True, 'right_present': True,
                'left': 'be800000', 'right': 'be000000'}])

    def test_opaque_identity_boolean_and_integer_are_not_equal(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            left, right = self.pair(Path(tmp))
            self.edit(left, 'RESULTS.json', lambda r: r['identity'].update(marker=False))
            self.edit(right, 'RESULTS.json', lambda r: r['identity'].update(marker=0))
            r = m.compare_saved_sequences(left, right)
            self.assertEqual(r['difference_counts'], {'INPUT': 0, 'RESULT': 0, 'IDENTITY': 1})
            self.assertEqual(r['differences'][0], {'path': '/RESULTS.json/identity/marker', 'section': 'IDENTITY',
                'kind': 'TYPE_CHANGED', 'left_present': True, 'right_present': True, 'left': False, 'right': 0})

    def test_missing_key_is_distinct_from_explicit_null_in_both_directions(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            left, right = self.pair(Path(tmp))
            self.edit(right, 'RESULTS.json', lambda r: r['identity'].update(marker=None))
            for a, b, kind, lp, rp in [(left, right, 'RIGHT_ONLY', False, True), (right, left, 'LEFT_ONLY', True, False)]:
                difference = m.compare_saved_sequences(a, b)['differences'][0]
                self.assertEqual((difference['kind'], difference['left_present'], difference['right_present'],
                                  difference['left'], difference['right']), (kind, lp, rp, None, None))

    def test_json_pointer_escapes_slashes_tildes_and_preserves_unicode_keys(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            left, right = self.pair(Path(tmp))
            self.edit(left, 'RESULTS.json', lambda r: r['identity'].update({'a~/한글': 1}))
            self.edit(right, 'RESULTS.json', lambda r: r['identity'].update({'a~/한글': 2}))
            self.assertEqual(m.compare_saved_sequences(left, right)['differences'][0]['path'], '/RESULTS.json/identity/a~0~1한글')

    def test_lists_compare_positionally_without_realignment(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            left, right = self.pair(Path(tmp))
            self.edit(left, 'RESULTS.json', lambda r: r['identity'].update(items=[1, 2]))
            self.edit(right, 'RESULTS.json', lambda r: r['identity'].update(items=[2, 1]))
            differences = m.compare_saved_sequences(left, right)['differences']
            self.assertEqual([(d['path'], d['left'], d['right']) for d in differences],
                [('/RESULTS.json/identity/items/0', 1, 2), ('/RESULTS.json/identity/items/1', 2, 1)])

    def test_list_tail_absence_has_presence_flags_even_when_value_is_null(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            left, right = self.pair(Path(tmp))
            self.edit(left, 'RESULTS.json', lambda r: r['identity'].update(items=[1, None]))
            self.edit(right, 'RESULTS.json', lambda r: r['identity'].update(items=[1]))
            for a, b, kind in [(left, right, 'LEFT_ONLY'), (right, left, 'RIGHT_ONLY')]:
                d = m.compare_saved_sequences(a, b)['differences'][0]
                self.assertEqual((d['path'], d['kind'], d['left'], d['right']), ('/RESULTS.json/identity/items/1', kind, None, None))

    def test_dict_insertion_order_does_not_create_differences(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            left, right = self.pair(Path(tmp))
            self.edit(left, 'RESULTS.json', lambda r: r['identity'].update(marker={'a': 1, 'b': 2}))
            self.edit(right, 'RESULTS.json', lambda r: r['identity'].update(marker={'b': 2, 'a': 1}))
            self.assertEqual(m.compare_saved_sequences(left, right)['difference_count'], 0)

    def test_container_type_change_is_one_typed_difference(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            left, right = self.pair(Path(tmp))
            self.edit(left, 'RESULTS.json', lambda r: r['identity'].update(marker=[]))
            self.edit(right, 'RESULTS.json', lambda r: r['identity'].update(marker={}))
            r = m.compare_saved_sequences(left, right)
            self.assertEqual((r['difference_count'], r['differences'][0]['kind']), (1, 'TYPE_CHANGED'))

    def test_detail_cap_keeps_full_section_counts_and_difference_exit(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            left, right = self.pair(Path(tmp))
            for folder, value in [(left, 0), (right, 1)]:
                self.edit(folder, 'RESULTS.json', lambda r, value=value: r['identity'].update(marker={f'{i:03}': value for i in range(300)}))
            self.edit(right, 'INPUT.json', lambda r: r['frames'][0]['request'].update(requested_binary32_be_hex='be000000'))
            r = m.compare_saved_sequences(left, right)
            self.assertEqual((r['difference_count'], r['reported_difference_count'], len(r['differences'])), (301, 256, 256))
            self.assertEqual(r['difference_counts'], {'INPUT': 1, 'RESULT': 0, 'IDENTITY': 300})
            self.assertTrue(r['differences_truncated'])
            self.assertEqual(r['differences'][0]['section'], 'INPUT')
            self.assertEqual(r['differences'][-1]['path'], '/RESULTS.json/identity/marker/254')
            self.assertEqual(self.command(left, right).returncode, 1)

    def test_markdown_escapes_untrusted_metadata_html_pipes_backticks_controls(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            left, right = self.pair(Path(tmp))
            text = '<script>|`\n\x1b\u202e'
            self.edit(right, 'RESULTS.json', lambda r: r['identity'].update({text: text}))
            output = m.render_comparison(m.compare_saved_sequences(left, right), 'markdown').decode()
            for escaped in ('&lt;script&gt;', '&#124;', '&#96;', r'\u001b', r'\u202e', '저장'):
                self.assertIn(escaped, output)
            for raw in ('<script>', '\x1b', '\u202e'):
                self.assertNotIn(raw, output)

    def test_format_rejects_before_touching_foreign_record(self):
        m = self.module()

        class Foreign:
            def __getattribute__(self, name):
                raise AssertionError('RESULT_ACCESSED')

        with self.assertRaisesRegex(m.CompareError, '^COMPARE_FORMAT$'):
            m.render_comparison(Foreign(), 'html')

    def test_corrupt_either_side_has_fixed_side_code_and_no_cli_summary(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            left, right = self.pair(Path(tmp))
            (right / 'INPUT.json').write_bytes(b'changed')
            for a, b, side in [(left, right, 'RIGHT'), (right, left, 'LEFT')]:
                code = 'COMPARE_' + side + ':INSPECT_CHECKSUM'
                with self.assertRaisesRegex(m.CompareError, '^' + code + '$'):
                    m.compare_saved_sequences(a, b)
                result = self.command(a, b)
                self.assertEqual((result.returncode, result.stdout, result.stderr), (2, b'', ('REJECTED: ' + code + '\n').encode()))

    def test_refreshed_manifest_cannot_hide_gate_or_row_corruption(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            left = self.fixture(root, 'left')
            for i, (change, code) in enumerate([(lambda r: r['gates'].update(actual_r=0), 'INSPECT_RECORD'),
                    (lambda r: r['rows'][0].update(status='DIFFERENT'), 'INSPECT_ROWS')]):
                right = root / str(i)
                shutil.copytree(left, right)
                self.edit(right, 'RESULTS.json', change)
                with self.assertRaisesRegex(m.CompareError, '^COMPARE_RIGHT:' + code + '$'):
                    m.compare_saved_sequences(left, right)

    def test_filesystem_and_json_rejections_remain_side_qualified(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            left = self.fixture(root, 'left')
            for label, code in [('symlink', 'INSPECT_INPUT_FILE'), ('fifo', 'INSPECT_INPUT_FILE'),
                                 ('oversize', 'INSPECT_SIZE'), ('extra', 'INSPECT_FILES'), ('json', 'INSPECT_JSON')]:
                right = root / label
                shutil.copytree(left, right)
                path = right / 'INPUT.json'
                if label == 'symlink':
                    path.unlink(); path.symlink_to(left / 'INPUT.json')
                elif label == 'fifo':
                    path.unlink(); os.mkfifo(path)
                elif label == 'oversize':
                    path.write_bytes(b' ' * 65537)
                elif label == 'extra':
                    (right / 'extra').write_bytes(b'')
                else:
                    path.write_bytes(b'{"x":NaN}\n'); self.refresh(right)
                with self.assertRaisesRegex(m.CompareError, '^COMPARE_RIGHT:' + code + '$'):
                    m.compare_saved_sequences(left, right)

    def test_each_side_opens_members_once_readonly_without_validation_reopen(self):
        m = self.module()
        original = os.open
        with tempfile.TemporaryDirectory() as tmp:
            left, right = self.pair(Path(tmp))
            calls = []

            def observe(path, flags, mode=0o777, *, dir_fd=None):
                calls.append((path, flags, dir_fd))
                return original(path, flags, mode, dir_fd=dir_fd)

            with patch('os.open', observe):
                r = m.compare_saved_sequences(left, right)
            self.assertEqual(r['difference_count'], 0)
            self.assertEqual(len(calls), 8)
            self.assertEqual([str(p) for p, _, _ in calls if str(p) in ('INPUT.json', 'RESULTS.json', 'SHA256SUMS.txt')],
                             ['INPUT.json', 'RESULTS.json', 'SHA256SUMS.txt'] * 2)
            self.assertTrue(all(flags & os.O_NOFOLLOW and not flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)
                                for _, flags, _ in calls))

    def test_same_path_is_captured_independently_not_short_circuit_equal(self):
        m = self.module()
        original = os.open
        with tempfile.TemporaryDirectory() as tmp:
            folder = self.fixture(Path(tmp), 'packet')
            with patch('os.open', wraps=original) as observed:
                self.assertEqual(m.compare_saved_sequences(folder, folder)['difference_count'], 0)
            self.assertEqual(observed.call_count, 8)

    def test_comparison_preserves_both_inputs_names_bytes_and_modes(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            left, right = self.pair(Path(tmp))
            before = {str(f): {p.name: (p.read_bytes(), p.stat().st_mode) for p in f.iterdir()} for f in (left, right)}
            m.compare_saved_sequences(left, right)
            self.assertEqual(self.command(left, right).returncode, 0)
            self.assertEqual(before, {str(f): {p.name: (p.read_bytes(), p.stat().st_mode) for p in f.iterdir()} for f in (left, right)})

    def test_cli_codes_follow_comparison_not_saved_status(self):
        self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folders = [self.fixture(root, case, case) for case in ('sign-cycle', 'declared-difference', 'late-invalid')]
            for folder in folders:
                result = self.command(folder, folder)
                self.assertEqual((result.returncode, result.stderr), (0, b''))
                self.assertEqual(json.loads(result.stdout)['comparison_status'], 'SAVED_PACKAGES_IDENTICAL')
            for fmt in ('json', 'markdown'):
                result = self.command(folders[0], folders[1], fmt)
                self.assertEqual((result.returncode, result.stderr), (1, b''))
                self.assertTrue(result.stdout)

    def test_stdout_full_device_has_fixed_error_for_buffered_and_unbuffered_modes(self):
        self.module()
        with tempfile.TemporaryDirectory() as tmp:
            left, right = self.pair(Path(tmp))
            for fmt in ('json', 'markdown'):
                for unbuffered in (False, True):
                    with open('/dev/full', 'wb') as full:
                        result = subprocess.run([sys.executable, '-I', '-B', *(['-u'] if unbuffered else []),
                            ROOT / 'tools/core_sequence_compare.py', '--left', left, '--right', right, '--format', fmt],
                            stdout=full, stderr=subprocess.PIPE)
                    self.assertEqual((result.returncode, result.stderr), (2, b'REJECTED: COMPARE_OPERATION_FAILED\n'))

    def test_cli_help_invalid_format_abbreviation_and_execution_option(self):
        self.module()
        for args, expected in [(['--help'], 0), ([], 2), (['--le', 'x', '--right', 'x'], 2),
            (['--left', 'x', '--right', 'x', '--format', 'html'], 2), (['--left', 'x', '--right', 'x', '--execute'], 2)]:
            result = subprocess.run([sys.executable, '-I', '-B', ROOT / 'tools/core_sequence_compare.py', *args], capture_output=True)
            self.assertEqual(result.returncode, expected)

    def test_fresh_api_and_cli_never_import_execution_path_or_model(self):
        self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            left = self.fixture(root, 'left')
            right = self.fixture(root, 'right', 'late-invalid')
            script = f'''
import importlib.abc,json,runpy,sys
sys.path.insert(0,{str(ROOT)!r})
blocked=('cyberlateral_dev','numpy','openpilot','selfdrive','opendbc','synthetic_rate_constraint_feasibility',
 'integration_tools.synthetic_model_input','integration_tools.synthetic_transition_check',
 'integration_tools.synthetic_sequence_check','integration_tools.core_sequence_run')
class Block(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if fullname.startswith(blocked): raise AssertionError('FORBIDDEN_IMPORT:'+fullname)
sys.meta_path.insert(0,Block())
from pathlib import Path
from integration_tools.core_sequence_compare import compare_saved_sequences
r=compare_saved_sequences(Path({str(left)!r}),Path({str(right)!r}))
assert r['comparison_model_executions']==r['comparison_reference_executions']==0
assert r['right']['saved_status']=='REJECTED'
sys.argv=['compare','--left',{str(left)!r},'--right',{str(right)!r}]
runpy.run_path({str(ROOT / 'tools/core_sequence_compare.py')!r},run_name='__main__')
'''
            result = subprocess.run([sys.executable, '-I', '-B', '-c', script], capture_output=True)
            self.assertEqual((result.returncode, result.stderr), (1, b''))
            self.assertEqual(json.loads(result.stdout)['comparison_status'], 'SAVED_PACKAGES_DIFFERENT')

    def test_canonical_json_and_markdown_repeat_without_location_metadata(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            left, right = self.pair(Path(tmp))
            r = m.compare_saved_sequences(left, right)
            raw = m.render_comparison(r)
            self.assertEqual(raw, (json.dumps(r, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode())
            for fmt in ('json', 'markdown'):
                self.assertEqual(m.render_comparison(r, fmt), m.render_comparison(m.compare_saved_sequences(left, right), fmt))
                self.assertNotIn(tmp.encode(), m.render_comparison(r, fmt))

    def test_coherent_stored_arithmetic_change_is_reported_not_recomputed(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            left, right = self.pair(Path(tmp))
            self.edit(right, 'INPUT.json', lambda r: r['frames'][3].update(saved_limited_state=99))

            def change(r):
                r['rows'][2]['computed_next_state']['previous_applied'] = 99
                r['rows'][2]['declared_saved_state']['saved_limited_state'] = 99

            self.edit(right, 'RESULTS.json', change)
            r = m.compare_saved_sequences(left, right)
            self.assertEqual(r['difference_counts'], {'INPUT': 1, 'RESULT': 2, 'IDENTITY': 0})
            self.assertEqual((r['left']['saved_status'], r['right']['saved_status']), ('MATCH', 'MATCH'))
            self.assertFalse(r['arithmetic_recomputed'])
            self.assertFalse(r['source_identity_reauthenticated'])

    def test_unexpected_api_exception_is_fixed_cli_error_not_difference(self):
        self.module()
        script = f'''
import runpy,sys
sys.path.insert(0,{str(ROOT)!r})
import integration_tools.core_sequence_compare as m
def fail(*args): raise TypeError('PRIVATE_VALUE')
m.compare_saved_sequences=fail
sys.argv=['compare','--left','unused','--right','unused']
runpy.run_path({str(ROOT / 'tools/core_sequence_compare.py')!r},run_name='__main__')
'''
        result = subprocess.run([sys.executable, '-I', '-B', '-c', script], capture_output=True)
        self.assertEqual((result.returncode, result.stdout, result.stderr), (2, b'', b'REJECTED: COMPARE_OPERATION_FAILED\n'))

    def test_bad_paths_have_fixed_side_errors_without_raw_path_leak(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            folder = self.fixture(Path(tmp), 'packet')
            for bad in (None, 'not-a-Path', Path(tmp) / 'missing', Path(tmp) / 'bad\0path'):
                for left, right, side in [(bad, folder, 'LEFT'), (folder, bad, 'RIGHT')]:
                    code = 'COMPARE_' + side + ':INSPECT_INPUT_FILE'
                    with self.assertRaisesRegex(m.CompareError, '^' + code + '$'):
                        m.compare_saved_sequences(left, right)

    def test_difference_order_uses_sorted_keys_and_numeric_list_indices(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            left, right = self.pair(Path(tmp))
            self.edit(left, 'RESULTS.json', lambda r: r['identity'].update(marker={'2': 0, '10': 0}, values=[0] * 12))
            self.edit(right, 'RESULTS.json', lambda r: r['identity'].update(marker={'2': 1, '10': 1}, values=[0, 0, 1] + [0] * 7 + [1, 0]))
            paths = [d['path'] for d in m.compare_saved_sequences(left, right)['differences']]
            self.assertEqual(paths, ['/RESULTS.json/identity/marker/10', '/RESULTS.json/identity/marker/2',
                                     '/RESULTS.json/identity/values/2', '/RESULTS.json/identity/values/10'])
