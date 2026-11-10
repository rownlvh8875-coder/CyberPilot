"""Fixed regression aggregation must preserve verdicts, work and failure boundaries."""

import importlib
import os
import sys
import unittest
from dataclasses import replace
from typing import Any
from unittest.mock import patch

from v1_helpers import ROOT, package_feature

ORDER = [('CORE30', 'sign-cycle'), ('CORE30', 'declared-difference'), ('CORE30', 'late-invalid'),
         ('CORE31', 'inactive-resume'), ('CORE31', 'fault-reset'), ('CORE31', 'rounding-ties')]


class CoreReferenceSuiteTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue((ROOT / 'integration_tools/core_reference_suite.py').is_file(), 'Missing CORE32 closed reference suite')
        self.model = package_feature()
        if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
        self.m: Any = importlib.import_module('integration_tools.core_reference_suite')

    def run_suite(self): return self.m.run_reference_suite()
    def reject(self, code):
        with self.assertRaises(self.m.ReferenceSuiteError) as found: self.run_suite()
        self.assertEqual((found.exception.code, str(found.exception)), (code, code))
    def invalid(self, change):
        original = self.m.audit_rollout_case
        def backend(case):
            r = original(case)
            if case == 'sign-cycle': change(r)
            return r
        with patch.object(self.m, 'audit_rollout_case', side_effect=backend): self.reject('REFERENCE_SUITE_RECEIPT_INVALID:CORE30:sign-cycle:WORK_MAY_BE_NONZERO')
    def different(self, r, count=1):
        r.update(audit_status='CLOSED_REFERENCE_DIFFERENT', audit_exit_code=1, difference_count=count,
                 reported_difference_count=min(count, 256), differences_truncated=count > 256,
                 difference_paths=['/changed/' + str(i) for i in range(min(count, 256))])

    def test_baseline_six_audits_match_despite_observed_difference_and_rejection(self):
        r = self.run_suite()
        self.assertEqual((r['suite_status'], r['suite_exit_code'], r['case_count']), ('CLOSED_REFERENCE_SUITE_MATCH', 0, 6))
        self.assertEqual(r['audit_counts'], {'MATCH': 6, 'DIFFERENT': 0})
        self.assertEqual(r['observed_rollout_counts'], {'MATCH': 4, 'DIFFERENT': 1, 'REJECTED': 1})
        self.assertEqual((r['reported_synthetic_model_steps'], r['difference_count'], r['reported_difference_count']), (19, 0, 0))
        self.assertEqual([x['report']['synthetic_model_steps'] for x in r['reports']], [3, 3, 0, 3, 4, 6])

    def test_fixed_order_once_and_actual_model_quantizer_calls(self):
        order = []; original30, original31 = self.m.audit_rollout_case, self.m.audit_boundary_case
        def a30(case): order.append(('CORE30', case)); return original30(case)
        def a31(case): order.append(('CORE31', case)); return original31(case)
        calls = {'model': 0, 'quantize': 0, 'rollout': 0, 'capture': 0}; previous = sys.getprofile()
        def profile(frame, event, arg):
            table = {('cyberlateral_dev.api', 'step'): 'model', ('cyberlateral_dev._r4.request_quantizer', 'quantize'): 'quantize',
                ('integration_tools.synthetic_sequence_rollout', 'rollout_synthetic_sequence'): 'rollout', ('integration_tools.core_sequence_run_inspect', '_read_file'): 'capture'}
            key = frame.f_globals.get('__name__'), frame.f_code.co_name
            if event == 'call' and key in table: calls[table[key]] += 1
        try:
            sys.setprofile(profile)
            with patch.object(self.m, 'audit_rollout_case', side_effect=a30), patch.object(self.m, 'audit_boundary_case', side_effect=a31): r = self.run_suite()
        finally: sys.setprofile(previous)
        self.assertEqual(order, ORDER); self.assertEqual([(x['group'], x['case_id']) for x in r['reports']], ORDER)
        self.assertEqual(calls, {'model': 19, 'quantize': 40, 'rollout': 6, 'capture': 6})

    def test_complete_child_receipts_are_preserved_not_replaced_with_totals(self):
        r = self.run_suite()
        for item in r['reports']:
            expected = self.m.audit_rollout_case(item['case_id']) if item['group'] == 'CORE30' else self.m.audit_boundary_case(item['case_id'])
            self.assertEqual(item['report'], expected)

    def test_real_projection_corruption_affects_five_audits_and_runs_all_six(self):
        original = self.model.step
        def changed(sample, state):
            output = original(sample, state); return replace(output, projection=replace(output.projection, status='CORRUPTED'))
        with patch.object(self.model, 'step', side_effect=changed): r = self.run_suite()
        self.assertEqual((r['suite_status'], r['suite_exit_code']), ('CLOSED_REFERENCE_SUITE_DIFFERENT', 1))
        self.assertEqual(r['audit_counts'], {'MATCH': 1, 'DIFFERENT': 5})
        self.assertEqual((r['difference_count'], r['reported_difference_count'], len(r['reports'])), (19, 19, 6))

    def test_early_normal_mismatch_does_not_skip_remaining_cases(self):
        original = self.m.audit_rollout_case
        def backend(case):
            r = original(case)
            if case == 'sign-cycle': self.different(r)
            return r
        with patch.object(self.m, 'audit_rollout_case', side_effect=backend): r = self.run_suite()
        self.assertEqual((r['audit_counts'], r['difference_count'], r['case_count']), ({'MATCH': 5, 'DIFFERENT': 1}, 1, 6))
        self.assertTrue(r['all_cases_processed'])

    def test_underlying_truncation_and_full_counts_are_separately_aggregated(self):
        original = self.m.audit_rollout_case
        def backend(case):
            r = original(case)
            if case == 'sign-cycle': self.different(r, 300)
            return r
        with patch.object(self.m, 'audit_rollout_case', side_effect=backend): r = self.run_suite()
        self.assertEqual((r['difference_count'], r['reported_difference_count'], r['differences_truncated']), (300, 256, True))
        self.assertEqual(len(r['reports'][0]['report']['difference_paths']), 256)

    def test_wrong_receipt_types_or_noninteger_counts_fail_closed(self):
        for key, value in (('schema_version', True), ('audit_exit_code', False), ('synthetic_model_steps', True),
                           ('difference_count', -1), ('expected_reference_model_steps', 1)):
            with self.subTest(key=key): self.invalid(lambda r, k=key, v=value: r.__setitem__(k, v))
        with patch.object(self.m, 'audit_rollout_case', return_value=[]): self.reject('REFERENCE_SUITE_RECEIPT_INVALID:CORE30:sign-cycle:WORK_MAY_BE_NONZERO')

    def test_contract_case_reference_and_scope_drift_are_rejected(self):
        for key, value in (('contract_id', 'OTHER'), ('case_id', 'late-invalid'), ('reference_sha256', '0' * 64),
                           ('reference_contract_id', 'OTHER'), ('scope', 'ACTUAL_VEHICLE_ALLOWED')):
            with self.subTest(key=key): self.invalid(lambda r, k=key, v=value: r.__setitem__(k, v))

    def test_forged_authority_flags_cannot_be_summarized_as_pass(self):
        for key in ('source_identity_reauthenticated', 'prehistory_checked', 'v4_payload_allowed', 'f61_input_allowed', 'actual_activation_allowed'):
            with self.subTest(key=key): self.invalid(lambda r, k=key: r.__setitem__(k, True))

    def test_gates_compare_exact_types_and_deny_extra_authority(self):
        self.invalid(lambda r: r['gates'].__setitem__('F61_calculator_executions', False))
        self.invalid(lambda r: r['gates'].__setitem__('Candidate', 'GO'))
        self.invalid(lambda r: r['gates'].__setitem__('extra_authority', True))

    def test_inconsistent_verdict_detail_and_truncation_are_rejected(self):
        for key, value in (('audit_status', 'OTHER'), ('audit_exit_code', 1), ('difference_count', 1),
                           ('reported_difference_count', 1), ('differences_truncated', True)):
            with self.subTest(key=key): self.invalid(lambda r, k=key, v=value: r.__setitem__(k, v))

    def test_malformed_paths_input_identity_or_extra_fields_are_rejected(self):
        self.invalid(lambda r: r.__setitem__('input_identity', {'byte_size': True, 'sha256': '0' * 64}))
        self.invalid(lambda r: r.__setitem__('input_identity', {'byte_size': 1, 'sha256': 'BAD'}))
        self.invalid(lambda r: r.__setitem__('unexpected', None))
        def malformed(r): self.different(r); r['difference_paths'] = ['not-a-pointer']
        self.invalid(malformed)

    def test_match_with_wrong_nominal_steps_or_observed_status_is_rejected(self):
        self.invalid(lambda r: r.__setitem__('synthetic_model_steps', 0))
        self.invalid(lambda r: r.update(observed_rollout_status='DIFFERENT', observed_rollout_exit_code=1))
        self.invalid(lambda r: r.__setitem__('observed_rollout_exit_code', 2))

    def test_late_operational_failure_stops_without_partial_success(self):
        original = self.m.audit_rollout_case; order = []
        def backend(case):
            order.append(case)
            if case == 'late-invalid': raise ValueError('PRIVATE')
            return original(case)
        with patch.object(self.m, 'audit_rollout_case', side_effect=backend), patch.object(self.m, 'audit_boundary_case', side_effect=AssertionError('must not continue')): self.reject('REFERENCE_SUITE_CASE_FAILED:CORE30:late-invalid:WORK_MAY_BE_NONZERO')
        self.assertEqual(order, ['sign-cycle', 'declared-difference', 'late-invalid'])

    def test_baseexception_is_not_converted_to_a_receipt(self):
        with patch.object(self.m, 'audit_rollout_case', side_effect=KeyboardInterrupt), self.assertRaises(KeyboardInterrupt): self.run_suite()

    def test_unexpected_backend_error_never_leaks_private_message(self):
        with patch.object(self.m, 'audit_rollout_case', side_effect=AssertionError('PRIVATE')): self.reject('REFERENCE_SUITE_CASE_FAILED:CORE30:sign-cycle:WORK_MAY_BE_NONZERO')

    def test_earlier_receipt_is_snapshotted_before_later_backend_mutation(self):
        original = self.m.audit_rollout_case; saved = {}
        def backend(case):
            r = original(case)
            if case == 'sign-cycle': saved['first'] = r
            elif case == 'declared-difference': saved['first']['gates']['Candidate'] = 'GO'
            return r
        with patch.object(self.m, 'audit_rollout_case', side_effect=backend): r = self.run_suite()
        self.assertEqual(r['reports'][0]['report']['gates']['Candidate'], 'NO_GO')

    def test_returns_detached_records_and_fresh_results_each_run(self):
        r = self.run_suite(); r['reports'][0]['report']['gates']['Candidate'] = 'GO'
        self.assertEqual(self.run_suite()['reports'][0]['report']['gates']['Candidate'], 'NO_GO')

    def test_api_writes_no_files_or_temp_during_synthetic_execution(self):
        original = os.open
        def opening(path, flags, *a, **kw): self.assertEqual(flags & os.O_ACCMODE, os.O_RDONLY); return original(path, flags, *a, **kw)
        with patch('os.open', side_effect=opening), patch('os.mkdir', side_effect=AssertionError('mkdir')), patch('tempfile.gettempdir', side_effect=AssertionError('temp')): self.assertEqual(self.run_suite()['suite_exit_code'], 0)

    def test_canonical_repeated_summaries_are_byte_identical(self):
        from integration_tools.scenario_output import canonical
        self.assertEqual(canonical(self.run_suite()), canonical(self.run_suite()))

    def test_suite_denies_generic_source_vehicle_and_runtime_attestation(self):
        r = self.run_suite()
        for key in ('reported_work_is_runtime_attestation', 'source_identity_reauthenticated', 'prehistory_checked', 'v4_payload_allowed', 'f61_input_allowed', 'actual_activation_allowed'): self.assertIs(r[key], False)
        self.assertTrue(r['execution_requested']); self.assertEqual(r['expected_reference_model_steps'], 0)
        self.assertEqual((r['gates']['R_BUDGET'], r['gates']['STATIC_EVIDENCE_GATE']), ('UNRESOLVED', 'FAIL'))
