"""Actual saved-campaign differences, source verdicts and exclusive publication."""

import hashlib
import importlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scenario_campaign_compare_fixture import change_saved_trace, copy_campaign, edit, real_campaign, sha
from v1_helpers import ROOT


class CampaignCompareRunTests(unittest.TestCase):
    def module(self):
        self.assertTrue((ROOT / 'integration_tools/scenario_campaign_compare_run.py').is_file(), 'Missing R44 runner')
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        return importlib.import_module('integration_tools.scenario_campaign_compare_run')

    def test_real_match_preserves_all_inputs_without_producer_or_reference_calls(self):
        m = self.module()
        source = real_campaign()
        before = {p.relative_to(source).as_posix(): sha(p) for p in source.rglob('*') if p.is_file()}
        campaign = importlib.import_module('integration_tools.scenario_campaign_run')
        with tempfile.TemporaryDirectory() as tmp, \
                patch.object(campaign.exploration, 'run_exploration', side_effect=AssertionError('no producer')), \
                patch.object(campaign.exploration.workflow.reference.reference, '_launch', side_effect=AssertionError('no reference')):
            result = m.run_campaign_comparison(source, source, Path(tmp) / 'out')
            self.assertEqual((result['status'], result['regression_status'], result['compared_sample_count'],
                              result['difference_count'], m.exit_code(result)), ('MATCH', 'MATCH', 32, 0, 0))
            self.assertEqual((result['new_model_executions'], result['new_reference_executions']), (0, 0))
            self.assertEqual(result['source_error_runs'], [])
            self.assertTrue(result['all_observed_producer_identities_match'])
            self.assertEqual(before, {p.relative_to(source).as_posix(): sha(p) for p in source.rglob('*') if p.is_file()})

    def test_repaired_saved_trace_change_is_one_exact_difference_not_new_reference_proof(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old, new = copy_campaign(root / 'before'), copy_campaign(root / 'after')
            change_saved_trace(new)
            result = m.run_campaign_comparison(old, new, root / 'out')
            self.assertEqual((result['status'], result['regression_status'], result['difference_count'],
                              result['compared_sample_count'], m.exit_code(result)), ('DIFFERENT', 'DIFFERENT', 1, 32, 1))
            detail = result['first_difference']
            self.assertEqual((detail['run_id'], detail['case_id'], detail['sample_index']), ('seed-001', 'case-001', 0))
            self.assertEqual(detail['field'], 'batch.rows[0].model_output.trace.downstream.limited_command')
            self.assertEqual((detail['before'], detail['after']), (2, -7))
            self.assertIn('RECORDED', result['comparison_claim'])

    def test_identical_failed_sources_never_become_overall_match(self):
        m = self.module()
        for status, code in [('ERROR', 2), ('DIFFERENT', 1)]:
            with self.subTest(status=status), tempfile.TemporaryDirectory() as tmp:
                source = real_campaign(seeds=(42,), status=status)
                record = m.run_campaign_comparison(source, source, Path(tmp) / 'out')
                self.assertEqual((record['status'], record['regression_status'], record['difference_count'], m.exit_code(record)),
                                 (status, 'MATCH', 0, code))
                alerts = record['source_error_runs'] if status == 'ERROR' else record['source_difference_runs']
                self.assertEqual([row['side'] for row in alerts], ['baseline', 'candidate'])
                self.assertEqual([row['seed'] for row in alerts], [42, 42])

    def test_reordered_seeds_preserve_position_and_do_not_count_different_inputs_as_samples(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            record = m.run_campaign_comparison(real_campaign(), real_campaign(seeds=(43, 42)), Path(tmp) / 'out')
            self.assertEqual(record['status'], 'DIFFERENT')
            self.assertEqual(record['compared_sample_count'], 0)
            self.assertEqual([(r['baseline_seed'], r['candidate_seed']) for r in record['runs']], [(42, 43), (43, 42)])
            self.assertEqual(record['alignment'], 'EXPLICIT_RUN_AND_CASE_POSITION_NOT_SEED_SORTING')

    def test_added_removed_runs_and_changed_steps_are_visible(self):
        m = self.module()
        one, two = real_campaign(seeds=(42,)), real_campaign()
        for old, new, classification in [(one, two, 'RUN_ADDED'), (two, one, 'RUN_REMOVED')]:
            with self.subTest(classification=classification), tempfile.TemporaryDirectory() as tmp:
                record = m.run_campaign_comparison(old, new, Path(tmp) / 'out')
                self.assertEqual(record['status'], 'DIFFERENT')
                self.assertEqual(record['compared_sample_count'], 16)
                self.assertEqual(len(record['runs']), 2)
                self.assertEqual(record['runs'][1]['classification'], classification)
                self.assertIsNone(record['runs'][1]['comparison_report'])
        with tempfile.TemporaryDirectory() as tmp:
            record = m.run_campaign_comparison(one, real_campaign(seeds=(42,), steps=32), Path(tmp) / 'out')
            self.assertEqual(record['status'], 'DIFFERENT')
            self.assertEqual(record['compared_sample_count'], 0)
            self.assertIn('parameters.steps', [d['field'] for d in record['differences']])
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'out'
            record = m.run_campaign_comparison(one, real_campaign(seeds=(42,), cases=2), output)
            self.assertEqual((record['status'], record['compared_sample_count']), ('DIFFERENT', 16))
            self.assertIn('parameters.cases', [d['field'] for d in record['differences']])
            child = json.loads((output / 'comparisons/seed-001/COMPARE.json').read_bytes())
            self.assertEqual(child['cases'][1]['classification'], 'CASE_ADDED')

    def test_identity_only_change_is_reported_separately_from_values(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = copy_campaign(root / 'changed')
            edit(source, 'CAMPAIGN.json',
                 lambda r: r['observed_source_identity']['campaign'].update({'tools/scenario_campaign.py': '0' * 64}))
            record = m.run_campaign_comparison(real_campaign(), source, root / 'out')
            self.assertEqual((record['status'], record['difference_count']), ('MATCH', 0))
            self.assertFalse(record['all_observed_producer_identities_match'])
            self.assertNotEqual(record['baseline_producer_identity_sha256'], record['candidate_producer_identity_sha256'])

    def test_global_details_truncate_without_truncating_true_difference_count(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old = real_campaign(seeds=(42,), cases=2, steps=256)
            new = copy_campaign(root / 'after', seeds=(42,), cases=2, steps=256)
            change_saved_trace(new, many=True)
            record = m.run_campaign_comparison(old, new, root / 'out')
            self.assertEqual(record['difference_count'], 512)
            self.assertEqual(len(record['differences']), 256)
            self.assertTrue(record['details_truncated'])
            child = json.loads((root / 'out/comparisons/seed-001/COMPARE.json').read_bytes())
            self.assertEqual(child['difference_count'], 512)

    def test_output_guards_run_before_reading_inputs_and_preserve_existing_data(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp, patch.object(m, 'read_campaign', side_effect=AssertionError('no read')):
            root = Path(tmp)
            (root / 'exists').mkdir()
            (root / 'exists/keep').write_bytes(b'keep')
            (root / 'dangling').symlink_to(root / 'absent')
            (root / 'link').symlink_to(root / 'exists', target_is_directory=True)
            for output in [root / 'exists', root / 'dangling', root / 'missing/out', root / 'link/out', ROOT / 'new-r44']:
                with self.subTest(output=output), self.assertRaises(m.CampaignCompareError):
                    m.run_campaign_comparison(root / 'missing-input', root / 'missing-input', output)
            self.assertEqual((root / 'exists/keep').read_bytes(), b'keep')

    def test_late_input_and_comparator_changes_prevent_completion(self):
        m = self.module()
        for kind in ['input', 'source']:
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                source = copy_campaign(root / 'input')
                if kind == 'input':
                    real = m.compare_batches

                    def late(old, new, real=real, source=source):
                        result = real(old, new)
                        with (source / 'SUMMARY_KO.md').open('ab') as stream:
                            stream.write(b'late change')
                        return result

                    context = patch.object(m, 'compare_batches', side_effect=late)
                else:
                    context = patch.object(m, '_source_hashes', side_effect=[{'x': '0' * 64}, {'x': '1' * 64}])
                with context, self.assertRaises(m.CampaignCompareError):
                    m.run_campaign_comparison(source, source, root / 'out')
                self.assertFalse((root / 'out/CAMPAIGN_COMPARE.json').exists())

    def test_publication_error_preserves_partial_files_without_completion_marker(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'out'
            real = m._write

            def fail_manifest(path, raw):
                if path == output / 'SHA256SUMS.txt':
                    raise OSError('controlled disk failure')
                real(path, raw)

            with patch.object(m, '_write', side_effect=fail_manifest), self.assertRaises(m.CampaignCompareError):
                m.run_campaign_comparison(real_campaign(), real_campaign(), output)
            self.assertTrue((output / 'SUMMARY_KO.md').is_file())
            self.assertFalse((output / 'CAMPAIGN_COMPARE.json').exists())

    def test_input_change_during_publication_cannot_publish_completion_marker(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = copy_campaign(root / 'input')
            output = root / 'out'
            real = m._write

            def change_after_summary(path, raw):
                real(path, raw)
                if path == output / 'SUMMARY_KO.md':
                    with (source / 'SUMMARY_KO.md').open('ab') as stream:
                        stream.write(b'late mutation')

            with patch.object(m, '_write', side_effect=change_after_summary), self.assertRaises(m.CampaignCompareError):
                m.run_campaign_comparison(source, source, output)
            self.assertFalse((output / 'CAMPAIGN_COMPARE.json').exists())

    def test_repeat_is_path_free_with_closed_manifests_and_separate_private_receipts(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for alias in ['one', 'two']:
                m.run_campaign_comparison(real_campaign(), real_campaign(), root / alias)
            for name in ['CAMPAIGN_COMPARE.json', 'SUMMARY_KO.md']:
                self.assertEqual((root / 'one' / name).read_bytes(), (root / 'two' / name).read_bytes())
                self.assertNotIn(str(root).encode(), (root / 'one' / name).read_bytes())
            self.assertNotEqual((root / 'one/RECEIPT.json').read_bytes(), (root / 'two/RECEIPT.json').read_bytes())
            folder = root / 'one'
            files = {p.relative_to(folder).as_posix(): p.read_bytes() for p in folder.rglob('*') if p.is_file()}
            recorded = {line.split('  ')[1]: line.split('  ')[0] for line in (folder / 'SHA256SUMS.txt').read_text().splitlines()}
            self.assertEqual(recorded, {n: hashlib.sha256(raw).hexdigest() for n, raw in files.items() if n != 'SHA256SUMS.txt'})
