"""Catch stage conflation, source drift, hidden units and lossy report flattening."""
import copy
import hashlib
import unittest

from normalized_reference import NormalizedReference
from test_source_contract import REFERENCE
from trace_reference import reference_rows
from v1_helpers import package_feature


class TraceAnalysisTests(unittest.TestCase):
    def parts(self):
        return package_feature('cyberlateral_dev.trace_analysis'), package_feature('cyberlateral_dev.reporting')

    def test_exact_rows_against_independent_original_helper_reference(self):
        module, source = self.parts()
        analysis = module.analyze_trace(source.catalog_report())
        reference = NormalizedReference((REFERENCE/'carcontroller.py').read_bytes(),(REFERENCE/'lateral.py').read_bytes())
        scenarios = package_feature('cyberlateral_dev.synthetic_catalog').fixed_catalog()
        for scenario, record in zip(scenarios,analysis['scenarios'],strict=True):
            self.assertEqual(record['rows'],reference_rows(scenario,reference))

    def test_source_identity_purity_and_description_not_policy(self):
        module, reporting = self.parts()
        source=reporting.catalog_report();before=copy.deepcopy(source)
        a=module.analyze_trace(source)
        self.assertEqual(source,before)
        self.assertEqual(a,module.analyze_trace(source))
        self.assertEqual(a['source_report_sha256'],hashlib.sha256(reporting.canonical_report(source)).hexdigest())
        self.assertEqual(a['package_version'],'0.3.0')
        self.assertEqual(a['gates'],source['gates'])
        self.assertEqual(a['units']['delta_from_previous_command'],'model_command_difference_per_invocation_NOT_per_second')
        self.assertNotIn('rate_budget_per_s',a)
        self.assertNotIn('duration_seconds',a)

    def test_descriptive_totals_match_hand_derived_limiter_and_gate_counts(self):
        module, reporting=self.parts()
        a=module.analyze_trace(reporting.catalog_report())
        self.assertEqual(a['summary'],{'steps':112,'limiter_adjusted':19,'inactive_calls':2,'inactive_gate_changed':2,
                                      'fault_request_suppressed':2,'normalized_outside_unit_interval':1})
        cases={s['id']:s for s in a['scenarios']}
        self.assertEqual(cases['ramp']['summary']['limiter_adjusted'],3)
        self.assertEqual(cases['fault-cycle']['summary']['limiter_adjusted'],7)

    def test_inactive_and_fault_request_suppression_are_not_same_event(self):
        module, reporting=self.parts()
        cases={s['id']:s for s in module.analyze_trace(reporting.catalog_report())['scenarios']}
        self.assertEqual([r['final_command'] for r in cases['inactive']['rows']],[2,0,0,2])
        suppressed=[r for r in cases['fault-cycle']['rows'] if r['fault_request_suppressed']]
        self.assertEqual([r['invocation_index'] for r in suppressed],[89,90])
        self.assertEqual([r['final_command'] for r in suppressed],[16,16])
        self.assertTrue(all(not r['inactive_gate_changed'] for r in suppressed))

    def test_history_19_signed_zero_and_exact_float32_words_preserved(self):
        module, reporting=self.parts()
        cases={s['id']:s for s in module.analyze_trace(reporting.catalog_report())['scenarios']}
        row=cases['history-scale']['rows'][0]
        self.assertEqual((row['previous_applied'],row['final_command'],row['delta_from_previous_command']),(100,95,-5))
        self.assertEqual(row['normalized_expression_hex'],19.0.hex())
        self.assertEqual((row['torque_f32_bits'],row['torque_output_can_f32_bits']),('41980000','42be0000'))
        zero=cases['signed-zero']['rows'][0]
        self.assertEqual((zero['request_hex'],zero['normalized_expression_hex']),('-0x0.0p+0','0x0.0p+0'))

    def test_unknown_schema_or_mismatched_counts_rejected(self):
        module, reporting=self.parts()
        for key,value in [('schema_version',2),('contract_id','OTHER'),('scope','PRODUCTION'),('scenario_count',8),('total_steps',113)]:
            source=reporting.catalog_report();source[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):module.analyze_trace(source)
        source=reporting.catalog_report();source['scenarios'][0]['result']['outputs']=()
        with self.assertRaises(ValueError):module.analyze_trace(source)


if __name__=='__main__':unittest.main()
