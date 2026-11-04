"""Literal comparison records, never a new browser, byte comparison or quality oracle."""

import importlib
import sys
import unittest
from copy import deepcopy
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))


def comparison_fixture():
    receipt = {
        'status': 'R64_SAVED_BROWSER_BUNDLE_VALID', 'recorded_status': 'R60_BROWSER_SMOKE_PASS',
        'cases': 10, 'recorded_case_failures': 0, 'recorded_failure_records': 0,
        'verified_files': 38, 'result_sha256': 'a' * 64,
        'reader_browser_model_F61_vehicle_executions': 0, 'source_identity_reauthenticated': False,
        'scope': 'SAVED_BYTES_AND_RECORD_CONSISTENCY_NOT_NEW_BROWSER_OR_ORIGIN_ATTESTATION',
    }
    return {
        'schema_version': 1, 'status': 'R66_SAVED_BROWSER_EXACT_BYTES_MATCH', 'comparison': 'EXACT_SAVED_BYTES',
        'compared_files': 38, 'changed_files': 0, 'unchanged_files': 38, 'differences': [],
        'baseline_verification': deepcopy(receipt), 'candidate_verification': deepcopy(receipt),
        'quality_assessment': 'NOT_PERFORMED', 'source_identity_reauthenticated': False,
        'comparator_browser_model_F61_vehicle_executions': 0,
        'scope': 'SAVED_BYTES_COMPARISON_NOT_VISUAL_OR_ORIGIN_ATTESTATION',
    }


class BrowserCompareSummaryTests(unittest.TestCase):
    def module(self):
        self.assertTrue((TOOLS / 'browser_compare_summary.py').is_file(), 'Korean comparison renderer missing')
        return importlib.import_module('browser_compare_summary')

    def different(self):
        result = comparison_fixture()
        result.update(status='R66_SAVED_BROWSER_BYTES_DIFFERENT', changed_files=2, unchanged_files=36,
                      differences=[{'path': 'SHA256SUMS.txt',
                                    'baseline': {'sha256': 'b' * 64, 'byte_size': 100},
                                    'candidate': {'sha256': 'c' * 64, 'byte_size': 101}},
                                   {'path': 'sign-render.log',
                                    'baseline': {'sha256': 'd' * 64, 'byte_size': 0},
                                    'candidate': {'sha256': 'e' * 64, 'byte_size': 19}}])
        return result

    # Catch lost comparison/quality distinction, not intentional prose rearrangement.
    def test_match_shows_counts_original_status_and_not_a_quality_verdict(self):
        text = self.module().render_comparison_summary(comparison_fixture()).decode('utf-8')
        self.assertIn('R66_SAVED_BROWSER_EXACT_BYTES_MATCH', text)
        self.assertIn('비교 파일: 38 · 변경: 0 · 불변: 38', text)
        self.assertIn('변경 파일 없음', text)
        self.assertIn('| baseline | `R60_BROWSER_SMOKE_PASS` | 10 | 0 | 0 | `' + 'a' * 64 + '` |', text)
        self.assertIn('| candidate | `R60_BROWSER_SMOKE_PASS` | 10 | 0 | 0 | `' + 'a' * 64 + '` |', text)
        self.assertIn('MATCH는 화면 PASS가 아닙니다', text)
        self.assertIn('quality_assessment=NOT_PERFORMED', text)
        self.assertIn('source_identity_reauthenticated=false', text)
        self.assertIn('Static Gate=FAIL', text)
        self.assertIn('r/T2/scale=null', text)

    # Catch truncated hashes, swapped before/after, omitted zero size or reordered rows.
    def test_differences_keep_full_hash_size_and_direction_in_sorted_rows(self):
        text = self.module().render_comparison_summary(self.different()).decode('utf-8')
        rows = [line for line in text.splitlines() if line.startswith('| `')]
        self.assertEqual(rows, [
            '| `SHA256SUMS.txt` | `' + 'b' * 64 + '` | 100 | `' + 'c' * 64 + '` | 101 |',
            '| `sign-render.log` | `' + 'd' * 64 + '` | 0 | `' + 'e' * 64 + '` | 19 |'])
        self.assertIn('R66_SAVED_BROWSER_BYTES_DIFFERENT', text)
        self.assertIn('비교 파일: 38 · 변경: 2 · 불변: 36', text)
        self.assertIn('DIFFERENT는 새 화면 회귀 판정이 아닙니다', text)

    # Catch deriving PASS from zero individual failures and hiding a global FAIL.
    def test_identical_global_fail_is_match_and_both_original_fails_remain(self):
        result = comparison_fixture()
        for key in ['baseline_verification', 'candidate_verification']:
            result[key].update(recorded_status='R60_BROWSER_SMOKE_FAIL', recorded_failure_records=1)
        text = self.module().render_comparison_summary(result).decode('utf-8')
        self.assertIn('R66_SAVED_BROWSER_EXACT_BYTES_MATCH', text)
        for side in ['baseline', 'candidate']:
            self.assertIn('| ' + side + ' | `R60_BROWSER_SMOKE_FAIL` | 10 | 0 | 1 |', text)
        self.assertNotIn('R60_BROWSER_SMOKE_PASS', text)

    def test_different_original_status_and_failure_counts_are_not_merged(self):
        result = self.different()
        result['candidate_verification'].update(recorded_status='R60_BROWSER_SMOKE_FAIL',
                                                recorded_case_failures=2, recorded_failure_records=3,
                                                result_sha256='f' * 64)
        result['differences'].insert(0, {'path': 'RESULT.json',
                                         'baseline': {'sha256': 'a' * 64, 'byte_size': 1000},
                                         'candidate': {'sha256': 'f' * 64, 'byte_size': 1100}})
        result.update(changed_files=3, unchanged_files=35)
        text = self.module().render_comparison_summary(result).decode('utf-8')
        self.assertIn('| baseline | `R60_BROWSER_SMOKE_PASS` | 10 | 0 | 0 |', text)
        self.assertIn('| candidate | `R60_BROWSER_SMOKE_FAIL` | 10 | 2 | 3 | `' + 'f' * 64 + '` |', text)

    def test_deterministic_utf8_final_newline_without_mutation_or_links(self):
        module = self.module()
        result = self.different()
        before = deepcopy(result)
        first = module.render_comparison_summary(result)
        self.assertIs(type(first), bytes)
        self.assertEqual(first, module.render_comparison_summary(result))
        self.assertTrue(first.endswith(b'\n'))
        self.assertNotIn(b'\r', first)
        text = first.decode('utf-8')
        self.assertIn('저장 묶음', text)
        self.assertNotIn('](', text)
        self.assertNotIn('<script', text)
        self.assertEqual(result, before)

    def reject(self, values):
        module = self.module()
        for value in values:
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, '^BROWSER_COMPARISON_SUMMARY_INVALID$'):
                module.render_comparison_summary(value)

    def test_invalid_schema_types_counts_and_scope_are_not_rendered(self):
        valid = comparison_fixture()
        self.reject([None, [], {}, *[valid | {key: value} for key, value in [
            ('schema_version', True), ('schema_version', 2), ('status', 'PASS'),
            ('comparison', 'SEMANTIC'), ('compared_files', True), ('compared_files', 37),
            ('changed_files', True), ('changed_files', -1), ('unchanged_files', 37),
            ('differences', None), ('quality_assessment', 'PASS'),
            ('source_identity_reauthenticated', True), ('source_identity_reauthenticated', 0),
            ('comparator_browser_model_F61_vehicle_executions', False), ('scope', '<script>')]]])

    def test_unsupported_or_unsafe_paths_hashes_sizes_and_order_are_rejected(self):
        values = []
        for key, value in [('path', '../../secret'), ('path', '/absolute'), ('path', 'https://example.invalid'),
                           ('path', 'sign-render.log|`<script>\nspoof'), ('path', None),
                           ('baseline', None), ('candidate', {})]:
            result = self.different()
            result['differences'][0][key] = value
            values.append(result)
        for key, value in [('sha256', 'f343b0ed...fab035'), ('sha256', 'A' * 64), ('sha256', None),
                           ('byte_size', True), ('byte_size', -1), ('byte_size', 8 * 1024 * 1024 + 1)]:
            result = self.different()
            result['differences'][0]['baseline'][key] = value
            values.append(result)
        reversed_rows = self.different()
        reversed_rows['differences'].reverse()
        duplicate = self.different()
        duplicate['differences'][1] = deepcopy(duplicate['differences'][0])
        self.reject([*values, reversed_rows, duplicate, self.different() | {'differences': []},
                     self.different() | {'status': 'R66_SAVED_BROWSER_EXACT_BYTES_MATCH'}])

    def test_receipt_missing_types_counts_status_or_provenance_cannot_be_hidden(self):
        values = []
        for side in ['baseline_verification', 'candidate_verification']:
            for key, value in [('status', 'PASS'), ('recorded_status', 'UNKNOWN'), ('recorded_status', '<script>'),
                               ('cases', True), ('cases', 0), ('recorded_case_failures', 11),
                               ('recorded_case_failures', -1), ('recorded_case_failures', 1),
                               ('recorded_failure_records', True), ('recorded_failure_records', 1),
                               ('verified_files', 37), ('result_sha256', 'bad'),
                               ('reader_browser_model_F61_vehicle_executions', 1),
                               ('source_identity_reauthenticated', True), ('scope', 'ORIGIN_AUTHENTICATED')]:
                result = comparison_fixture()
                result[side][key] = value
                values.append(result)
            result = comparison_fixture()
            result[side] = None
            values.append(result)
            result = comparison_fixture()
            del result[side]['result_sha256']
            values.append(result)
        self.reject(values)

    # Catch stale/edited receipts falsely paired with MATCH or an unrelated log delta.
    def test_absent_result_delta_requires_matching_receipt_facts(self):
        values = []
        for base in [comparison_fixture(), self.different()]:
            for update in [{'result_sha256': 'f' * 64},
                           {'recorded_status': 'R60_BROWSER_SMOKE_FAIL', 'recorded_failure_records': 1}]:
                result = deepcopy(base)
                result['candidate_verification'].update(update)
                values.append(result)
        self.reject(values)

    # Catch swapped or stale RESULT hashes while preserving real raw-byte semantics.
    def test_result_delta_hashes_must_match_their_corresponding_receipts(self):
        values = []
        for side, digest in [('baseline', 'b' * 64), ('candidate', 'c' * 64)]:
            result = self.different()
            result['differences'].insert(0, {'path': 'RESULT.json',
                                             'baseline': {'sha256': 'a' * 64, 'byte_size': 1000},
                                             'candidate': {'sha256': 'a' * 64, 'byte_size': 1001}})
            result.update(changed_files=3, unchanged_files=35)
            result['differences'][0][side]['sha256'] = digest
            values.append(result)
        self.reject(values)


if __name__ == '__main__':
    unittest.main()
