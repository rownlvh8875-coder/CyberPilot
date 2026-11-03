"""Reader behavior: reject closed-hash contradictions, not merely damaged bytes."""

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path

from scenario_campaign_compare_fixture import edit, rehash_all
from scenario_campaign_report_fixture import copy_comparison, real_comparison
from v1_helpers import ROOT


class CampaignReportDataTests(unittest.TestCase):
    def read(self, path):
        from integration_tools.scenario_campaign_report_data import read_comparison
        return read_comparison(path)

    def rejected(self, path):
        from integration_tools.scenario_campaign_report_schema import CampaignReportError
        with self.assertRaises(CampaignReportError):
            self.read(path)

    def test_real_complete_comparisons_preserve_statuses_counts(self):
        for kind, status, regression, count, samples in [
            ('match', 'MATCH', 'MATCH', 0, 32), ('difference', 'DIFFERENT', 'DIFFERENT', 1, 32),
            ('error', 'ERROR', 'MATCH', 0, 16), ('source_different', 'DIFFERENT', 'MATCH', 0, 16),
            ('added', 'DIFFERENT', 'DIFFERENT', 2, 16), ('truncated', 'DIFFERENT', 'DIFFERENT', 512, 512),
        ]:
            with self.subTest(kind=kind):
                source = real_comparison(kind)
                snapshot = self.read(source)
                record = snapshot['view']['comparison']
                self.assertEqual((record['status'], record['regression_status'], record['difference_count'],
                                  record['compared_sample_count']), (status, regression, count, samples))
                self.assertEqual(record, json.loads((source / 'CAMPAIGN_COMPARE.json').read_bytes()))
                self.assertEqual(snapshot['hashes'], snapshot['view']['source_file_hashes'])
                for name, digest in snapshot['hashes'].items():
                    self.assertEqual(hashlib.sha256((source / name).read_bytes()).hexdigest(), digest)
                self.assertNotIn(str(source), json.dumps(snapshot['view']))

    def test_rehashed_parent_contradictions_rejected(self):
        mutations = [
            lambda r: r.update(status='ERROR'), lambda r: r.update(compared_sample_count=33),
            lambda r: r.update(difference_count=1), lambda r: r.update(details_truncated=True),
            lambda r: r.update(all_observed_producer_identities_match=False),
            lambda r: r.update(new_model_executions=False), lambda r: r.update(schema_version=True),
            lambda r: r['runs'][0].update(baseline_seed=44),
            lambda r: r['runs'][0].update(comparison_report='../COMPARE.json'),
            lambda r: r['baseline_parameters'].update(seeds=[42, 42]),
            lambda r: r['runs'][0].update(classification='RUN_ADDED'),
            lambda r: r.update(source_error_runs=[{'side': 'baseline'}]),
            lambda r: r['gates'].update(R_BUDGET='APPROVED'),
        ]
        for number, mutate in enumerate(mutations):
            with self.subTest(number=number), tempfile.TemporaryDirectory() as tmp:
                source = copy_comparison(Path(tmp) / 'input')
                edit(source, 'CAMPAIGN_COMPARE.json', mutate)
                self.rejected(source)

    def test_rehashed_child_contradictions_rejected(self):
        mutations = [
            lambda r: r.update(status='DIFFERENT'), lambda r: r.update(compared_sample_count=True),
            lambda r: r.update(difference_count=1), lambda r: r['cases'][0].update(difference_count=1),
            lambda r: r['cases'][0].update(producer_identity_changed=True),
            lambda r: r.update(batch_producer_identity_changed=True),
            lambda r: r['cases'][0].update(case_id='case-002'), lambda r: r.update(extra=1),
        ]
        for number, mutate in enumerate(mutations):
            with self.subTest(number=number), tempfile.TemporaryDirectory() as tmp:
                source = copy_comparison(Path(tmp) / 'input')
                edit(source, 'comparisons/seed-001/COMPARE.json', mutate)
                self.rejected(source)

    def test_detail_context_presence_and_child_binding_rejected(self):
        for mutate in [lambda r: r['differences'][0].update(case_id='case-002'),
                       lambda r: r['differences'][0].update(before_present=False),
                       lambda r: r['differences'][0].update(after=-8),
                       lambda r: r.update(first_difference=None)]:
            with self.subTest(mutate=mutate), tempfile.TemporaryDirectory() as tmp:
                source = copy_comparison(Path(tmp) / 'input', 'difference')
                edit(source, 'CAMPAIGN_COMPARE.json', mutate)
                self.rejected(source)

    def test_source_alerts_cannot_disappear(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = copy_comparison(Path(tmp) / 'input', 'error')
            edit(source, 'CAMPAIGN_COMPARE.json', lambda r: r.update(source_error_runs=[]))
            self.rejected(source)

    def test_malformed_detail_context_never_leaks_type_error(self):
        for field, value in [('run_id', []), ('case_id', []), ('baseline_seed', True)]:
            with self.subTest(field=field), tempfile.TemporaryDirectory() as tmp:
                source = copy_comparison(Path(tmp) / 'input', 'difference')

                def change(record, field=field, value=value):
                    record['differences'][0][field] = value
                    record['first_difference'][field] = value

                edit(source, 'CAMPAIGN_COMPARE.json', change)
                self.rejected(source)

    def test_wrong_json_container_types_are_bounded_rejections(self):
        for field in ['baseline_status', 'classification']:
            with self.subTest(field=field), tempfile.TemporaryDirectory() as tmp:
                source = copy_comparison(Path(tmp) / 'input')
                edit(source, 'CAMPAIGN_COMPARE.json', lambda r, field=field: r['runs'][0].update({field: []}))
                self.rejected(source)

    def test_unnecessary_empty_directories_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = copy_comparison(Path(tmp) / 'input')
            (source / 'unrecorded').mkdir()
            self.rejected(source)

    def test_extra_missing_and_unhashed_files_rejected(self):
        for mode in ['extra', 'missing', 'corrupt']:
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as tmp:
                source = copy_comparison(Path(tmp) / 'input')
                if mode == 'extra':
                    (source / 'extra.txt').write_text('not allowed')
                    rehash_all(source)
                elif mode == 'missing':
                    (source / 'comparisons/seed-001/COMPARE.json').unlink()
                    rehash_all(source)
                else:
                    (source / 'SUMMARY_KO.md').write_text('changed')
                self.rejected(source)

    def test_noncanonical_duplicate_nonfinite_and_deep_json_rejected(self):
        for raw in [b'{"schema_version":1,"schema_version":1}\n', b'{"x":NaN}\n',
                    b'{ }\n', b'[' * 100 + b'0' + b']' * 100 + b'\n']:
            with self.subTest(raw=raw[:30]), tempfile.TemporaryDirectory() as tmp:
                source = copy_comparison(Path(tmp) / 'input')
                (source / 'CAMPAIGN_COMPARE.json').write_bytes(raw)
                rehash_all(source)
                self.rejected(source)

    def test_symlinks_root_ancestors_and_fifo_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            source = copy_comparison(home / 'input')
            (home / 'alias').symlink_to(home, target_is_directory=True)
            self.rejected(home / 'alias/input')
            (home / 'rootlink').symlink_to(source, target_is_directory=True)
            self.rejected(home / 'rootlink')
            target = source / 'SUMMARY_KO.md'
            target.unlink()
            target.symlink_to(ROOT / 'README.md')
            self.rejected(source)
            target.unlink()
            os.mkfifo(target)
            self.rejected(source)

    def test_oversized_sparse_file_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = copy_comparison(Path(tmp) / 'input')
            with (source / 'SUMMARY_KO.md').open('wb') as stream:
                stream.truncate(16 * 1024 * 1024 + 1)
            self.rejected(source)

    def test_receipt_paths_are_metadata_not_opened_or_copied(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = copy_comparison(Path(tmp) / 'input')
            edit(source, 'RECEIPT.json', lambda r: r.update(baseline_directory='/nonexistent/private-secret'))
            self.assertNotIn('private-secret', json.dumps(self.read(source)['view']))


if __name__ == '__main__':
    unittest.main()
