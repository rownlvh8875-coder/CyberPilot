"""Exact saved-value differences, distinct provenance, and positional alignment."""

import importlib
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from scenario_compare_fixture import write_batch
from v1_helpers import ROOT


class CompareDataTests(unittest.TestCase):
    def module(self):
        self.assertTrue((ROOT / 'integration_tools/scenario_compare_data.py').is_file(), 'Missing R34 semantic comparison')
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        return importlib.import_module('integration_tools.scenario_compare_data')

    def pair(self, profiles=('sign', 'resumed')):
        from integration_tools.scenario_compare_input import read_batch

        with tempfile.TemporaryDirectory() as tmp:
            baseline = read_batch(write_batch(Path(tmp) / 'batch', profiles))
        return baseline, deepcopy(baseline)

    def test_exact_match_preserves_closed_gates_and_never_counts_saved_work_as_new(self):
        m = self.module()
        a, b = self.pair()
        result = m.compare_batches(a, b)
        self.assertEqual((result['status'], result['difference_count'], result['compared_sample_count']), ('MATCH', 0, 5))
        self.assertEqual(result['new_model_executions'], 0)
        self.assertEqual(result['gates']['R_BUDGET'], 'UNRESOLVED')
        self.assertEqual(result['gates']['STATIC_EVIDENCE_GATE'], 'FAIL')
        self.assertIsNone(result['first_difference'])
        self.assertTrue(result['all_observed_producer_identities_match'])

    def test_first_changed_command_reports_exact_field_index_and_values(self):
        m = self.module()
        a, b = self.pair()
        b['cases'][0]['result']['rows'][2]['model_output']['trace']['downstream']['limited_command'] = -7
        result = m.compare_batches(a, b)
        self.assertEqual(result['status'], 'DIFFERENT')
        self.assertEqual(result['difference_count'], 1)
        self.assertEqual(result['first_difference'], {'case_id': 'case-001', 'sample_index': 2,
                         'field': 'rows[2].model_output.trace.downstream.limited_command',
                         'before_present': True, 'after_present': True, 'before': 2, 'after': -7})

    def test_previous_requested_and_applied_are_distinct_fields(self):
        m = self.module()
        a, b = self.pair()
        b['cases'][0]['result']['rows'][3]['prepared']['state'].update(previous_requested=12, previous_applied=13)
        result = m.compare_batches(a, b)
        self.assertEqual(result['difference_count'], 2)
        self.assertEqual([d['field'] for d in result['differences']], ['rows[3].prepared.state.previous_applied', 'rows[3].prepared.state.previous_requested'])
        self.assertEqual([d['before'] for d in result['differences']], [0, 4])

    def test_clip_precision_kind_float_type_and_signed_zero_are_exact(self):
        m = self.module()
        a, original = self.pair()
        for field, after in [('normalized_expression', -0.0), ('integer_command', 2.0), ('integer_command', True)]:
            with self.subTest(field=field, after=after):
                b = deepcopy(original)
                row = b['cases'][0]['result']['rows'][2 if field == 'normalized_expression' else 0]
                row['model_output']['projection'][field] = after
                self.assertEqual(m.compare_batches(a, b)['difference_count'], 1)
        b = deepcopy(original)
        b['cases'][0]['result']['rows'][0]['model_output']['trace']['downstream']['rate_clip']['result']['kind'] = 'python.int'
        self.assertEqual(m.compare_batches(a, b)['difference_count'], 1)

    def test_input_change_is_not_a_same_input_result_regression(self):
        m = self.module()
        a, b = self.pair()
        b['cases'][0]['metadata']['input_sha256'] = '1' * 64
        b['cases'][0]['input']['samples'][0]['request_hex'] = '0x1.0000000000000p-1'
        b['cases'][0]['result']['rows'][0]['model_output']['projection']['integer_command'] = 999
        result = m.compare_batches(a, b)
        self.assertEqual(result['cases'][0]['classification'], 'INPUT_CHANGED')
        self.assertEqual(result['compared_sample_count'], 1)
        self.assertTrue(any('request_hex' in d['field'] for d in result['differences']))
        self.assertFalse(any('projection.integer_command' in d['field'] for d in result['differences']))

    def test_input_whitespace_raw_identity_change_is_visible(self):
        m = self.module()
        a, b = self.pair()
        b['cases'][0]['metadata']['input_sha256'] = '1' * 64
        result = m.compare_batches(a, b)
        self.assertEqual(result['cases'][0]['classification'], 'INPUT_CHANGED')
        self.assertEqual(result['first_difference']['field'], 'input_raw_sha256')

    def test_matching_rejections_and_unverifiable_missing_inputs_distinguished(self):
        m = self.module()
        a, b = self.pair(('bad',))
        self.assertEqual(m.compare_batches(a, b)['status'], 'MATCH')
        b['cases'][0]['metadata']['rejection_code'] = 'SCENARIO_SIZE'
        result = m.compare_batches(a, b)
        self.assertEqual(result['cases'][0]['classification'], 'REJECTION_CHANGED')
        self.assertEqual(result['first_difference']['field'], 'rejection_code')
        a, b = self.pair(('missing',))
        result = m.compare_batches(a, b)
        self.assertEqual(result['status'], 'DIFFERENT')
        self.assertEqual(result['cases'][0]['classification'], 'UNVERIFIABLE_INPUT')

    def test_status_change_and_added_removed_cases_are_not_silently_ignored(self):
        m = self.module()
        a, b = self.pair()
        b['cases'][0]['metadata']['status'] = 'REJECTED'
        b['cases'][0]['metadata']['rejection_code'] = 'SCENARIO_DOMAIN'
        self.assertEqual(m.compare_batches(a, b)['cases'][0]['classification'], 'STATUS_CHANGED')
        a, b = self.pair()
        b['cases'].pop()
        removed = m.compare_batches(a, b)
        added = m.compare_batches(b, a)
        self.assertEqual(removed['cases'][1]['classification'], 'CASE_REMOVED')
        self.assertEqual(added['cases'][1]['classification'], 'CASE_ADDED')
        self.assertTrue(removed['first_difference']['before_present'])
        self.assertFalse(removed['first_difference']['after_present'])

    def test_duplicate_ids_use_position_not_dictionary_overwrite(self):
        m = self.module()
        a, b = self.pair(('sign', 'sign'))
        b['cases'][1]['result']['rows'][0]['prepared']['state']['angle_counter'] = 1
        result = m.compare_batches(a, b)
        self.assertEqual([c['classification'] for c in result['cases']], ['MATCH', 'RESULT_CHANGED'])
        self.assertEqual(result['first_difference']['case_id'], 'case-002')

    def test_source_identity_change_is_visible_but_not_a_numeric_regression(self):
        m = self.module()
        a, b = self.pair()
        b['cases'][0]['result']['identity']['observed_dev_source_hashes']['integration_tools/historical_only.py'] = '1' * 64
        result = m.compare_batches(a, b)
        self.assertEqual(result['status'], 'MATCH')
        self.assertFalse(result['all_observed_producer_identities_match'])
        self.assertTrue(result['cases'][0]['producer_identity_changed'])
        self.assertEqual(result['comparison_claim'], 'RECORDED_VALUES_ONLY_NOT_ORIGIN_NUMERICAL_OR_VEHICLE_APPROVAL')

    def test_batch_producer_identity_change_visible_even_for_rejected_only_batch(self):
        m = self.module()
        a, b = self.pair(('bad',))
        b['batch_producer_identity_sha256'] = '1' * 64
        result = m.compare_batches(a, b)
        self.assertEqual(result['status'], 'MATCH')
        self.assertFalse(result['all_observed_producer_identities_match'])
        self.assertTrue(result['batch_producer_identity_changed'])

    def test_final_state_and_presence_not_confused_with_null(self):
        m = self.module()
        a, b = self.pair()
        b['cases'][0]['result']['final_state']['previous_applied'] = None
        result = m.compare_batches(a, b)
        self.assertEqual(result['first_difference']['field'], 'final_state.previous_applied')
        self.assertTrue(result['first_difference']['after_present'])
        self.assertIsNone(result['first_difference']['after'])

    def test_detail_limit_preserves_total_and_per_case_first_change(self):
        m = self.module()
        a, b = self.pair()
        original = b['cases'][0]['result']['rows'][0]
        a['cases'][0]['result']['rows'] = [deepcopy(original) for _ in range(300)]
        b['cases'][0]['result']['rows'] = deepcopy(a['cases'][0]['result']['rows'])
        for row in b['cases'][0]['result']['rows']:
            row['model_output']['projection']['integer_command'] = -1
        b['cases'][1]['result']['rows'][0]['model_output']['projection']['integer_command'] = 1
        result = m.compare_batches(a, b)
        self.assertEqual(result['difference_count'], 301)
        self.assertEqual(len(result['differences']), 256)
        self.assertTrue(result['details_truncated'])
        self.assertEqual(result['cases'][1]['first_difference']['before'], -2)
        self.assertEqual(result['cases'][1]['first_difference']['after'], 1)
