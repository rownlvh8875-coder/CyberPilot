"""R40 must preserve owned inputs, real stage verdicts and non-vacuous counts."""

import hashlib
import importlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scenario_compare_fixture import refresh, write_batch
from scenario_report_fixture import edit_json
from v1_helpers import ROOT


class WorkflowTests(unittest.TestCase):
    def module(self):
        self.assertTrue((ROOT / 'integration_tools/scenario_workflow_run.py').is_file(), 'Missing R40 owned workflow')
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        return importlib.import_module('integration_tools.scenario_workflow_run')

    def sign(self):
        return ROOT / 'examples/synthetic_sign_cycle_v1.json'

    def resumed(self):
        return ROOT / 'examples/synthetic_resumed_v1.json'

    def check(self, m, inputs, output, status='VERIFIED', baseline=None):
        result = m.run_workflow(inputs, output, baseline)
        self.assertEqual(result['status'], status)
        self.assertEqual(json.loads((output / 'WORKFLOW.json').read_bytes()), result)
        self.assertEqual(result['gates']['R_BUDGET'], 'UNRESOLVED')
        self.assertEqual(result['gates']['STATIC_EVIDENCE_GATE'], 'FAIL')
        for key in ['actual_r', 'T2', 'vehicle_scale']:
            self.assertIsNone(result['gates'][key])
        for sums in output.rglob('*SHA256SUMS.txt'):
            for line in sums.read_text().splitlines():
                digest, name = line.split('  ')
                self.assertEqual(hashlib.sha256((sums.parent / name).read_bytes()).hexdigest(), digest)
        listed = {line.split('  ')[1] for line in (output / 'SHA256SUMS.txt').read_text().splitlines()}
        self.assertEqual(listed, {p.relative_to(output).as_posix() for p in output.rglob('*')
                                 if p.is_file() and p != output / 'SHA256SUMS.txt'})
        self.assertEqual((output / 'WORKFLOW.json').read_bytes(),
                         (json.dumps(result, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode())
        return result

    def test_two_valid_files_get_real_reports_and_independent_state_counts(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            r = self.check(m, [self.sign(), self.resumed()], root / 'out')
            self.assertEqual((r['input_count'], r['completed'], r['rejected'], r['model_steps'], r['reference_steps']), (2, 2, 0, 5, 5))
            self.assertEqual((r['reference_status'], r['regression_status'], m.exit_code(r)), ('MATCH', None, 0))
            self.assertEqual(r['reference_helper_counts']['limiter_traced'], 5)
            self.assertTrue((root / 'out' / r['batch_index']).is_file())
            validation = json.loads((root / 'out/VALIDATION.json').read_bytes())
            self.assertEqual([c['validation']['sample_count'] for c in validation['cases']], [4, 1])
            self.assertEqual([c['validation']['first_index'] for c in validation['cases']], [0, 5])
            self.assertEqual(validation['model_executions'], 0)
            self.assertNotIn(str(root).encode(), (root / 'out/WORKFLOW.json').read_bytes())

    def test_mixed_inputs_retain_parser_rejection_and_exit_one(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bad = root / 'bad.json'
            bad.write_bytes(b'{')
            r = self.check(m, [self.sign(), bad], root / 'out', 'VERIFIED_WITH_INPUT_REJECTIONS')
            self.assertEqual((r['completed'], r['rejected'], r['model_steps'], r['reference_steps']), (1, 1, 4, 4))
            self.assertEqual(m.exit_code(r), 1)
            cases = json.loads((root / 'out/VALIDATION.json').read_bytes())['cases']
            self.assertEqual(cases[1]['validation']['rejection_code'], 'SCENARIO_JSON')
            self.assertIsNone(cases[1]['validation']['input_raw_sha256'])

    def test_all_rejected_is_not_vacuous_success(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bad = root / 'bad.json'
            bad.write_bytes(b'{')
            r = self.check(m, [bad], root / 'out', 'NO_COMPLETED_CASES')
            self.assertEqual((r['model_steps'], r['reference_steps'], m.exit_code(r)), (0, 0, 1))

    def test_unreadable_symlink_fifo_and_oversize_never_create_output(self):
        m = self.module()
        from integration_tools.scenario_input import MAX_BYTES

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'link').symlink_to(self.sign())
            os.mkfifo(root / 'fifo')
            (root / 'large').write_bytes(b' ' * (MAX_BYTES + 1))
            for name in ['missing', 'link', 'fifo', 'large']:
                with self.subTest(name=name), self.assertRaisesRegex(m.WorkflowError, 'WORKFLOW_INPUT_UNAVAILABLE'):
                    m.run_workflow([root / name], root / ('out-' + name))
                self.assertFalse((root / ('out-' + name)).exists())

    def test_existing_dangling_parent_component_and_duplicate_guards(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'exists').mkdir()
            (root / 'exists/keep').write_bytes(b'keep')
            (root / 'dangling').symlink_to(root / 'missing')
            for target in [root / 'exists', root / 'dangling', root / 'no-parent/out', ROOT / 'new-r40-out']:
                with self.subTest(target=target), self.assertRaises(ValueError):
                    m.run_workflow([self.sign()], target)
            self.assertEqual((root / 'exists/keep').read_bytes(), b'keep')
            with self.assertRaisesRegex(ValueError, 'BATCH_DUPLICATE_INPUT'):
                m.run_workflow([self.sign(), self.sign()], root / 'new')
            self.assertFalse((root / 'new').exists())

    def test_complete_baseline_is_match_without_requiring_producer_identity(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            baseline = write_batch(root / 'baseline')
            before = {p.relative_to(baseline): p.read_bytes() for p in baseline.rglob('*') if p.is_file()}
            r = self.check(m, [self.sign(), self.resumed()], root / 'out', baseline=baseline)
            self.assertEqual(r['regression_status'], 'MATCH')
            self.assertEqual(r['regression_difference_count'], 0)
            self.assertEqual(before, {p.relative_to(baseline): p.read_bytes() for p in baseline.rglob('*') if p.is_file()})

    def test_coherent_baseline_difference_is_distinct_from_reference_difference(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            baseline = write_batch(root / 'baseline', ('sign',))
            edit_json(baseline / 'case-001/data', 'RESULTS.json',
                      lambda r: r['rows'][0]['model_output']['projection']['torque_float32'].update(bits_hex='00000000'))
            refresh(baseline)
            r = self.check(m, [self.sign()], root / 'out', 'REGRESSION_DIFFERENT', baseline)
            self.assertEqual((r['reference_status'], r['regression_status'], r['regression_difference_count'], m.exit_code(r)), ('MATCH', 'DIFFERENT', 1, 1))

    def test_corrupt_portable_or_nested_baseline_rejects_before_output(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            baseline = write_batch(root / 'baseline')
            with self.assertRaises(ValueError):
                m.run_workflow([self.sign()], baseline / 'nested', baseline)
            (baseline / 'RECEIPT.json').unlink()
            with self.assertRaises(ValueError):
                m.run_workflow([self.sign()], root / 'out', baseline)
            self.assertFalse((root / 'out').exists())

    def test_original_inputs_and_baseline_are_not_reopened_after_owned_capture(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original = root / 'user.json'
            original.write_bytes(self.sign().read_bytes())
            baseline = write_batch(root / 'baseline', ('sign',))
            run = m.batch.run_batch

            def after_snapshot(inputs, output):
                original.write_bytes(b'changed after owned capture')
                (baseline / 'BATCH.json').write_bytes(b'changed after owned capture')
                return run(inputs, output)

            with patch.object(m.batch, 'run_batch', side_effect=after_snapshot):
                r = self.check(m, [original], root / 'out', baseline=baseline)
            self.assertEqual((r['status'], r['regression_status'], r['model_steps']), ('VERIFIED', 'MATCH', 4))

    def test_reference_mutation_is_not_masked_by_successful_batch(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            check = m.reference.check_batch

            def mutate_then_check(source, output):
                edit_json(source / 'case-001/data', 'RESULTS.json',
                          lambda r: r['rows'][0]['model_output']['projection']['torque_float32'].update(bits_hex='00000000'))
                refresh(source)
                return check(source, output)

            with patch.object(m.reference, 'check_batch', side_effect=mutate_then_check):
                r = self.check(m, [self.sign()], root / 'out', 'REFERENCE_DIFFERENT')
            self.assertEqual((r['reference_status'], r['reference_difference_count'], m.exit_code(r)), ('DIFFERENT', 1, 1))

    def test_reference_worker_error_keeps_error_and_unknown_failed_work(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch.object(m.reference.reference, '_launch', side_effect=m.reference.reference.ReferenceCheckError('REFERENCE_WORKER_FAILED')):
                r = self.check(m, [self.sign()], root / 'out', 'ERROR')
            self.assertEqual(m.exit_code(r), 2)
            self.assertEqual((r['model_steps'], r['reference_steps']), (4, 0))
            self.assertIn('FAILED_WORK_MAY_BE_NONZERO', r['reference_steps_accounting'])

    def test_partial_worker_failure_preserves_folder_without_completion_marker(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch.object(m.batch, '_worker', side_effect=m.batch.BatchError('BATCH_WORKER_FAILED')):
                with self.assertRaisesRegex(ValueError, 'BATCH_WORKER_FAILED'):
                    m.run_workflow([self.sign()], root / 'out')
            self.assertTrue((root / 'out/VALIDATION.json').is_file())
            self.assertFalse((root / 'out/WORKFLOW.json').exists())
            self.assertFalse((root / 'out/SHA256SUMS.txt').exists())

    def test_changed_source_or_owned_input_prevents_final_publication(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            identity = m._source_identity()
            with patch.object(m, '_source_identity', side_effect=[identity, {'changed': '0' * 64}]):
                with self.assertRaisesRegex(m.WorkflowError, 'WORKFLOW_SOURCE_CHANGED'):
                    m.run_workflow([self.sign()], root / 'source-out')
            check = m.reference.check_batch

            def alter_owned(source, output):
                r = check(source, output)
                (source.parent / 'inputs/case-001.json').write_bytes(b'changed')
                return r

            with patch.object(m.reference, 'check_batch', side_effect=alter_owned):
                with self.assertRaisesRegex(m.WorkflowError, 'WORKFLOW_INPUT_CHANGED'):
                    m.run_workflow([self.sign()], root / 'input-out')
            self.assertFalse((root / 'source-out/WORKFLOW.json').exists())
            self.assertFalse((root / 'input-out/WORKFLOW.json').exists())

    def test_portable_root_repeats_but_private_full_receipts_need_not(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.check(m, [self.resumed()], root / 'one')
            self.check(m, [self.resumed()], root / 'two')
            for name in ['WORKFLOW.json', 'SUMMARY_KO.md', 'VALIDATION.json']:
                self.assertEqual((root / 'one' / name).read_bytes(), (root / 'two' / name).read_bytes())
            self.assertNotEqual((root / 'one/RECEIPT.json').read_bytes(), (root / 'two/RECEIPT.json').read_bytes())

    def test_status_precedence_never_promotes_errors_or_unknowns_to_verified(self):
        m = self.module()
        for reference, regression, rejected, want in [
            ('ERROR', 'DIFFERENT', 1, 'ERROR'), ('DIFFERENT', 'DIFFERENT', 1, 'REFERENCE_DIFFERENT'),
            ('MATCH', 'DIFFERENT', 0, 'REGRESSION_DIFFERENT'), ('INCOMPLETE', None, 1, 'INCOMPLETE'),
            ('NO_COMPLETED_CASES', None, 1, 'NO_COMPLETED_CASES'),
            ('MATCH_WITH_INPUT_REJECTIONS', 'MATCH', 1, 'VERIFIED_WITH_INPUT_REJECTIONS'),
            ('MATCH', None, 0, 'VERIFIED')]:
            with self.subTest(reference=reference, regression=regression):
                self.assertEqual(m._status(reference, regression, rejected), want)
        with self.assertRaisesRegex(m.WorkflowError, 'WORKFLOW_STAGE_STATUS'):
            m._status('UNKNOWN', None, 0)

    def test_changed_snapshot_between_validation_and_batch_cannot_be_verified(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run = m.batch.run_batch

            def alter_then_run(inputs, output):
                inputs[0].write_bytes(self.resumed().read_bytes())
                return run(inputs, output)

            with patch.object(m.batch, 'run_batch', side_effect=alter_then_run):
                with self.assertRaisesRegex(m.WorkflowError, 'WORKFLOW_INPUT_CHANGED'):
                    m.run_workflow([self.sign()], root / 'out')
            self.assertFalse((root / 'out/WORKFLOW.json').exists())


if __name__ == '__main__':
    unittest.main()
