"""Inspection must validate stored relationships without importing a calculator."""

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

from v1_helpers import ROOT


class CoreSequenceSavedTests(unittest.TestCase):
    def module(self):
        self.assertTrue((ROOT / 'integration_tools/core_sequence_saved.py').is_file(), 'Missing CORE9 saved sequence inspector')
        self.assertTrue((ROOT / 'tools/core_sequence_inspect.py').is_file(), 'Missing CORE9 inspection CLI')
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        return importlib.import_module('integration_tools.core_sequence_saved')

    def fixture(self, root, case='sign-cycle', name='packet'):
        producer = importlib.import_module('integration_tools.core_sequence_run')
        output = root / name
        producer.run_sequence_case(case, output)
        return output

    def refresh(self, folder):
        raw = ''.join(hashlib.sha256((folder / name).read_bytes()).hexdigest() + '  ' + name + '\n'
                      for name in ('INPUT.json', 'RESULTS.json')).encode()
        (folder / 'SHA256SUMS.txt').write_bytes(raw)

    def edit(self, folder, filename, change):
        target = folder / filename
        data = json.loads(target.read_bytes())
        change(data)
        target.write_bytes((json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode())
        self.refresh(folder)

    def reject(self, m, folder, code):
        with self.assertRaises(m.InspectError) as raised:
            m.inspect_saved_sequence(folder)
        self.assertEqual((raised.exception.code, str(raised.exception)), (code, code))

    def command(self, folder, output_format='json'):
        return subprocess.run([sys.executable, '-I', '-B', ROOT / 'tools/core_sequence_inspect.py', '--input', folder,
                               '--format', output_format], capture_output=True, text=True)

    def test_three_saved_outcomes_are_preserved_not_new_numerical_verdicts(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for case, status, steps, differences in [('sign-cycle', 'MATCH', 3, []),
                ('declared-difference', 'DIFFERENT', 3, [0]), ('late-invalid', 'REJECTED', 0, [])]:
                folder = self.fixture(root, case, case)
                result = m.inspect_saved_sequence(folder)
                self.assertEqual(result['inspection_status'], 'SAVED_RECORDS_CONSISTENT')
                self.assertEqual((result['saved_status'], result['recorded_model_steps'], result['differing_transition_indices']),
                                 (status, steps, differences))
                self.assertEqual((result['inspection_model_executions'], result['inspection_reference_executions']), (0, 0))
                self.assertFalse(result['source_identity_reauthenticated'])
                self.assertFalse(result['anchor_transition_checked'])
                self.assertFalse(result['prehistory_checked'])

    def test_stored_declared_and_computed_rows_are_separate(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            result = m.inspect_saved_sequence(self.fixture(Path(tmp), 'declared-difference'))
            self.assertEqual([row['computed_limited_state'] for row in result['rows']], [2, 5, 4])
            self.assertEqual(result['rows'][0]['saved_limited_state'], 10)
            self.assertEqual(result['rows'][0]['differences'], [{'field': 'saved_limited_state', 'declared': 10, 'computed': 2}])

    def test_canonical_json_markdown_and_captured_hashes_are_repeatable(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            folder = self.fixture(Path(tmp))
            raw = m.format_saved_sequence(folder, 'json')
            value = json.loads(raw)
            self.assertEqual(raw, (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode())
            self.assertEqual(raw, m.format_saved_sequence(folder, 'json'))
            self.assertEqual(value['captured_sha256'], {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.iterdir()})
            text = m.format_saved_sequence(folder, 'markdown').decode()
            self.assertIn('MATCH', text)
            self.assertIn('저장', text)
            self.assertIn('0', text)
            self.assertNotIn(str(folder), text)

    def test_inspection_preserves_input_file_set_bytes_and_modes(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            folder = self.fixture(Path(tmp))
            before = {p.name: (p.read_bytes(), p.stat().st_mode) for p in folder.iterdir()}
            m.inspect_saved_sequence(folder)
            self.assertEqual(self.command(folder).returncode, 0)
            self.assertEqual(before, {p.name: (p.read_bytes(), p.stat().st_mode) for p in folder.iterdir()})

    def test_all_valid_saved_outcomes_exit_zero_when_inspection_succeeds(self):
        self.module()
        with tempfile.TemporaryDirectory() as tmp:
            for case, status in [('sign-cycle', 'MATCH'), ('declared-difference', 'DIFFERENT'), ('late-invalid', 'REJECTED')]:
                result = self.command(self.fixture(Path(tmp), case, case))
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(result.stderr, '')
                self.assertEqual(json.loads(result.stdout)['saved_status'], status)

    def test_unchanged_historical_identity_is_not_compared_to_current_source(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            folder = self.fixture(Path(tmp))
            self.edit(folder, 'RESULTS.json', lambda r: r['identity'].update(demo_cli_sha256='0' * 64))
            result = m.inspect_saved_sequence(folder)
            self.assertFalse(result['source_identity_reauthenticated'])
            self.assertEqual(result['saved_status'], 'MATCH')

    def test_bad_format_rejects_before_attempting_to_read_input(self):
        m = self.module()

        class Foreign:
            def __getattribute__(self, _name):
                raise AssertionError('INPUT_READ')

        with self.assertRaisesRegex(m.InspectError, '^INSPECT_FORMAT$'):
            m.format_saved_sequence(Foreign(), 'not-approved')

    def test_missing_file_extra_file_and_directory_member_cannot_pass(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = self.fixture(root)
            (folder / 'extra').write_bytes(b'extra')
            self.reject(m, folder, 'INSPECT_FILES')
            (folder / 'extra').unlink()
            (folder / 'extra-dir').mkdir()
            self.reject(m, folder, 'INSPECT_FILES')
            (folder / 'extra-dir').rmdir()
            (folder / 'RESULTS.json').unlink()
            self.reject(m, folder, 'INSPECT_FILES')

    def test_root_and_member_symlinks_are_not_followed(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = self.fixture(root)
            (root / 'link').symlink_to(folder, target_is_directory=True)
            self.reject(m, root / 'link', 'INSPECT_INPUT_FILE')
            original = (folder / 'RESULTS.json').read_bytes()
            (root / 'result').write_bytes(original)
            (folder / 'RESULTS.json').unlink()
            (folder / 'RESULTS.json').symlink_to(root / 'result')
            self.reject(m, folder, 'INSPECT_INPUT_FILE')

    def test_fifo_member_rejects_without_blocking_and_oversize_is_bounded(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            folder = self.fixture(Path(tmp))
            path = folder / 'INPUT.json'
            path.unlink()
            os.mkfifo(path)
            self.reject(m, folder, 'INSPECT_INPUT_FILE')
            path.unlink()
            path.write_bytes(b' ' * 65537)
            self.reject(m, folder, 'INSPECT_SIZE')

    def test_checksum_corruption_and_unsafe_manifest_names_do_not_traverse(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            folder = self.fixture(Path(tmp))
            (folder / 'INPUT.json').write_bytes((folder / 'INPUT.json').read_bytes() + b' ')
            self.reject(m, folder, 'INSPECT_CHECKSUM')
            self.refresh(folder)
            (folder / 'SHA256SUMS.txt').write_bytes(b'0' * 64 + b'  ../not-opened\n')
            self.reject(m, folder, 'INSPECT_CHECKSUM')

    def test_duplicate_keys_nonfinite_and_float_tokens_are_not_valid_json_records(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            folder = self.fixture(Path(tmp))
            original = (folder / 'INPUT.json').read_bytes()
            for raw in [original.replace(b'{', b'{"schema_version":1,', 1), b'{"x":NaN}\n', b'{"x":1.0}\n', b'\xff']:
                (folder / 'INPUT.json').write_bytes(raw)
                self.refresh(folder)
                self.reject(m, folder, 'INSPECT_JSON')

    def test_depth_and_integer_token_caps_are_enforced_before_schema(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            folder = self.fixture(Path(tmp))
            for raw in [(b'[' * 65) + b'0' + (b']' * 65), b'{"x":' + (b'9' * 33) + b'}\n']:
                (folder / 'INPUT.json').write_bytes(raw)
                self.refresh(folder)
                self.reject(m, folder, 'INSPECT_JSON')

    def test_valid_but_noncanonical_json_is_rejected_after_valid_checksums(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            folder = self.fixture(Path(tmp))
            value = json.loads((folder / 'INPUT.json').read_bytes())
            (folder / 'INPUT.json').write_text(json.dumps(value, indent=2))
            self.refresh(folder)
            self.reject(m, folder, 'INSPECT_CANONICAL')

    def test_unknown_contract_case_schema_extra_keys_and_claims_reject(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for i, change in enumerate([lambda r: r.update(schema_version=True), lambda r: r.update(contract_id='unknown'),
                lambda r: r.update(case_id='vehicle'), lambda r: r.update(runtime_allowed=True),
                lambda r: r.update(source_authenticated=True), lambda r: r.update(anchor_transition_checked=0)]):
                folder = self.fixture(root, name=str(i))
                self.edit(folder, 'RESULTS.json', change)
                self.reject(m, folder, 'INSPECT_RECORD')

    def test_closed_gates_and_nulls_cannot_be_promoted_with_new_manifest(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for i, change in enumerate([lambda r: r['gates'].update(R_BUDGET='RESOLVED'),
                lambda r: r['gates'].update(actual_r=0), lambda r: r['gates'].update(F61_calculator_executions=False)]):
                folder = self.fixture(root, name=str(i))
                self.edit(folder, 'RESULTS.json', change)
                self.reject(m, folder, 'INSPECT_RECORD')

    def test_mismatched_case_or_frame_context_counts_cannot_pass(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for i, change in enumerate([lambda r: r.update(case_id='declared-difference'),
                lambda r: r['frames'].pop(), lambda r: r['contexts'].pop()]):
                folder = self.fixture(root, name=str(i))
                self.edit(folder, 'INPUT.json', change)
                self.reject(m, folder, 'INSPECT_RECORD')

    def test_boolean_counts_and_partial_rejected_rows_cannot_be_zero_work_success(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for i, change in enumerate([lambda r: r.update(model_steps=True),
                lambda r: r.update(completed_transition_count=1), lambda r: r.update(sequence_completed=0),
                lambda r: r.update(rejection_code='SEQUENCE_TRANSITION:2:TRANSITION_MODEL_FAILURE')]):
                folder = self.fixture(root, 'late-invalid', str(i))
                self.edit(folder, 'RESULTS.json', change)
                self.reject(m, folder, 'INSPECT_RECORD')

    def test_saved_row_types_indices_entry_and_links_are_checked(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for i, change in enumerate([lambda r: r['rows'][0].update(transition_index=True),
                lambda r: r['rows'][1].update(model_index=7),
                lambda r: r['rows'][1]['entry_state'].update(previous_applied=10),
                lambda r: r['rows'][0]['computed_next_state'].update(angle_counter=True),
                lambda r: r['rows'][0]['computed_next_state'].update(previous_requested=7)]):
                folder = self.fixture(root, name=str(i))
                self.edit(folder, 'RESULTS.json', change)
                self.reject(m, folder, 'INSPECT_ROWS')

    def test_differences_row_status_and_aggregate_indices_are_exactly_consistent(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for i, change in enumerate([lambda r: r['rows'][0].update(differences=[]),
                lambda r: r['rows'][0].update(status='MATCH'), lambda r: r.update(status='MATCH'),
                lambda r: r.update(differing_transition_indices=[]),
                lambda r: r['rows'][0]['differences'][0].update(computed=3)]):
                folder = self.fixture(root, 'declared-difference', str(i))
                self.edit(folder, 'RESULTS.json', change)
                self.reject(m, folder, 'INSPECT_ROWS')

    def test_coordinated_self_consistent_forgery_is_not_arithmetic_or_origin_proof(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            folder = self.fixture(Path(tmp))
            self.edit(folder, 'INPUT.json', lambda r: r['frames'][3].update(saved_limited_state=99))

            def change(r):
                r['rows'][2]['declared_saved_state']['saved_limited_state'] = 99
                r['rows'][2]['computed_next_state']['previous_applied'] = 99

            self.edit(folder, 'RESULTS.json', change)
            result = m.inspect_saved_sequence(folder)
            self.assertEqual((result['inspection_status'], result['saved_status']), ('SAVED_RECORDS_CONSISTENT', 'MATCH'))
            self.assertEqual(result['rows'][2]['computed_limited_state'], 99)
            self.assertFalse(result['source_identity_reauthenticated'])
            self.assertEqual(result['inspection_model_executions'], 0)

    def test_cli_corrupt_package_exit_two_has_no_partial_stdout(self):
        self.module()
        with tempfile.TemporaryDirectory() as tmp:
            folder = self.fixture(Path(tmp))
            (folder / 'RESULTS.json').write_bytes(b'changed')
            result = self.command(folder)
            self.assertEqual((result.returncode, result.stdout), (2, ''))
            self.assertEqual(result.stderr, 'REJECTED: INSPECT_CHECKSUM\n')

    def test_new_model_imports_are_blocked_in_fresh_api_and_cli_processes(self):
        self.module()
        with tempfile.TemporaryDirectory() as tmp:
            folder = self.fixture(Path(tmp), 'declared-difference')
            script = f'''
import importlib.abc,json,runpy,sys
sys.path.insert(0,{str(ROOT)!r})
blocked=('cyberlateral_dev','numpy','openpilot','selfdrive','opendbc','synthetic_rate_constraint_feasibility',
         'integration_tools.synthetic_model_input','integration_tools.synthetic_transition_check',
         'integration_tools.synthetic_sequence_check','integration_tools.core_sequence_run')
class Block(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.startswith(blocked):
            raise AssertionError('FORBIDDEN_IMPORT:'+fullname)
sys.meta_path.insert(0,Block())
from pathlib import Path
from integration_tools.core_sequence_saved import inspect_saved_sequence
r=inspect_saved_sequence(Path({str(folder)!r}))
assert r['inspection_model_executions']==0 and r['saved_status']=='DIFFERENT'
sys.argv=['inspect','--input',{str(folder)!r}]
runpy.run_path({str(ROOT / 'tools/core_sequence_inspect.py')!r},run_name='__main__')
'''
            result = subprocess.run([sys.executable, '-I', '-B', '-c', script], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(json.loads(result.stdout)['saved_status'], 'DIFFERENT')

    def test_missing_path_and_bad_path_type_do_not_raise_raw_errors(self):
        m = self.module()
        for value in (None, 'not-a-Path', Path('/tmp/nonexistent-core9-path'), Path('/tmp/bad\0path')):
            self.reject(m, value, 'INSPECT_INPUT_FILE')

    def test_mirrored_valid_package_has_identical_summary_without_path_reauth(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = self.fixture(root)
            mirror = root / 'mirror'
            shutil.copytree(folder, mirror)
            self.assertEqual(m.format_saved_sequence(folder), m.format_saved_sequence(mirror))

    def test_cli_help_syntax_unknown_format_and_execution_option_are_no_execution(self):
        self.module()
        for args, code in [(['--help'], 0), ([], 2), (['--input', '/not-read', '--format', 'html'], 2),
                           (['--input', '/not-read', '--execute'], 2)]:
            result = subprocess.run([sys.executable, '-I', '-B', ROOT / 'tools/core_sequence_inspect.py', *args],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, code, result.stdout + result.stderr)
