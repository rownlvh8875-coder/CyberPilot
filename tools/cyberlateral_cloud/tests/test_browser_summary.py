"""Human summary behavior from independent literal observations, no browser."""

import importlib
import sys
import unittest
from copy import deepcopy
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))


class BrowserSummaryTests(unittest.TestCase):
    def module(self):
        self.assertTrue((TOOLS / 'browser_summary.py').is_file(), 'Korean browser summary missing')
        return importlib.import_module('browser_summary')

    def fixture(self):
        f = importlib.import_module('browser_result_fixture')
        return f.result_fixture(), f.file_fixture()

    def test_case_columns_show_recorded_measurements_and_completion_boundary(self):
        s = self.module()
        record, files = self.fixture()
        text = s.render_summary(record, files).decode()
        self.assertIn('R60_BROWSER_SMOKE_PASS', text)
        self.assertIn('| sign / 320 | PASS | `320` / `0` | `2` / `14` | `true` / `500` |', text)
        self.assertIn('| resumed / 1440 | PASS | `1440` / `0` | `2` / `14` | `false` / `0` |', text)
        self.assertIn('RESULT.json', text)
        self.assertIn('SHA256SUMS.txt', text)
        self.assertIn('완료', text)
        self.assertIn('Static Gate=FAIL', text)

    def test_failed_case_measurements_and_reason_are_not_replaced_by_pass(self):
        s = self.module()
        record, files = self.fixture()
        record['status'] = 'R60_BROWSER_SMOKE_FAIL'
        record['cases'][0]['failures'] = ['PAGE_OVERFLOW']
        record['cases'][0]['metrics'].update(document_width=321, pan=1)
        record['failures'] = [{'profile': 'sign', 'width': 320, 'codes': ['PAGE_OVERFLOW']}]
        text = s.render_summary(record, files).decode()
        self.assertIn('| sign / 320 | FAIL | `321` / `1` |', text)
        self.assertIn('PAGE_OVERFLOW', text)
        self.assertIn('페이지', text)
        self.assertIn('R60_BROWSER_SMOKE_FAIL', text)

    def test_global_failure_survives_when_every_case_is_individually_pass(self):
        s = self.module()
        record, files = self.fixture()
        record['status'] = 'R60_BROWSER_SMOKE_FAIL'
        record['failures'] = [{'codes': ['UNEXPECTED_BROWSER_REQUEST'], 'count': 1}]
        text = s.render_summary(record, files).decode()
        self.assertIn('R60_BROWSER_SMOKE_FAIL', text)
        self.assertIn('UNEXPECTED_BROWSER_REQUEST', text)
        self.assertIn('count', text)
        self.assertIn('| sign / 320 | PASS |', text)

    def test_incomplete_duplicate_and_contradictory_records_are_not_success(self):
        s = self.module()
        record, files = self.fixture()
        incomplete = deepcopy(record)
        incomplete['cases'].pop()
        duplicate = deepcopy(record)
        duplicate['cases'][-1] = duplicate['cases'][0]
        contradictory = deepcopy(record)
        contradictory['cases'][0]['failures'] = ['CHARTS']
        global_failure = deepcopy(record)
        global_failure['failures'] = [{'codes': ['UNEXPECTED_BROWSER_REQUEST'], 'count': 1}]
        no_reason = deepcopy(record)
        no_reason['status'] = 'R60_BROWSER_SMOKE_FAIL'
        for value in [record | {'cases': []}, incomplete, duplicate, contradictory, global_failure, no_reason]:
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'BROWSER_SUMMARY_INVALID'):
                s.render_summary(value, files)

    def test_metadata_is_escaped_without_injecting_rows_html_or_code_boundaries(self):
        s = self.module()
        record, files = self.fixture()
        record['browser_version'] = 'Chrome|spoof\n<script>x</script>`tail'
        text = s.render_summary(record, files).decode()
        self.assertNotIn('<script>', text)
        self.assertNotIn('|spoof', text)
        self.assertNotIn('`tail', text)
        self.assertIn('&lt;script&gt;', text)

    def test_missing_and_null_observations_do_not_turn_into_zero_facts(self):
        s = self.module()
        record, files = self.fixture()
        record['status'] = 'R60_BROWSER_SMOKE_FAIL'
        record['cases'][0]['failures'] = ['INVALID_OBSERVATIONS']
        record['cases'][0]['metrics'].pop('min_chart_font')
        record['cases'][0]['metrics']['table_position'] = None
        record['failures'] = [{'profile': 'sign', 'width': 320, 'codes': ['INVALID_OBSERVATIONS']}]
        text = s.render_summary(record, files).decode()
        row = next(line for line in text.splitlines() if line.startswith('| sign / 320 |'))
        self.assertIn('미관측', row)
        self.assertIn('`null`', row)

    def test_only_existing_fixed_local_artifacts_become_links(self):
        s = self.module()
        record, files = self.fixture()
        del files['captures/sign-390-top.png']
        files['../../secret'] = 'c' * 64
        text = s.render_summary(record, files).decode()
        self.assertNotIn('(captures/sign-390-top.png)', text)
        self.assertIn('(captures/sign-390-charts.png)', text)
        self.assertIn('(reports/resumed/VIEW.json)', text)
        self.assertNotIn('../../', text)
        for name in ['../../secret', '/absolute.png', 'https://example.invalid/a.png']:
            bad = deepcopy(record)
            bad['captures'][name] = 'c' * 64
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'BROWSER_SUMMARY_INVALID'):
                s.render_summary(bad, files)

    def test_present_capture_hash_mismatch_is_not_linked_as_consistent_evidence(self):
        s = self.module()
        record, files = self.fixture()
        files['captures/sign-390-charts.png'] = 'c' * 64
        with self.assertRaisesRegex(ValueError, 'BROWSER_SUMMARY_INVALID'):
            s.render_summary(record, files)

    def test_summary_is_deterministic_and_does_not_mutate_its_inputs(self):
        s = self.module()
        record, files = self.fixture()
        before = deepcopy((record, files))
        first = s.render_summary(record, files)
        self.assertEqual(first, s.render_summary(record, files))
        self.assertEqual((record, files), before)


if __name__ == '__main__':
    unittest.main()
