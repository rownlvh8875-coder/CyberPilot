"""Batch reference classification must not confuse missing evidence with parity."""

import hashlib
import importlib
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scenario_compare_fixture import edit_batch, refresh, rehash_portable, write_batch
from scenario_report_fixture import edit_json
from v1_helpers import ROOT


class BatchReferenceTests(unittest.TestCase):
    def module(self):
        self.assertTrue((ROOT / 'integration_tools/scenario_batch_reference_run.py').is_file(), 'Missing R39 saved-batch independent checker')
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        return importlib.import_module('integration_tools.scenario_batch_reference_run')

    def check(self, module, source, output, status='MATCH'):
        result = module.check_batch(source, output)
        self.assertEqual(result['status'], status)
        self.assertEqual(result['new_model_executions'], 0)
        self.assertEqual(result['gates']['R_BUDGET'], 'UNRESOLVED')
        self.assertEqual(result['gates']['STATIC_EVIDENCE_GATE'], 'FAIL')
        for field in ['actual_r', 'T2', 'vehicle_scale']:
            self.assertIsNone(result['gates'][field])
        self.assertEqual(json.loads((output / 'BATCH_REFERENCE_CHECK.json').read_bytes()), result)
        for sums in output.rglob('SHA256SUMS.txt'):
            for line in sums.read_text().splitlines():
                digest, name = line.split('  ')
                self.assertEqual(hashlib.sha256((sums.parent / name).read_bytes()).hexdigest(), digest)
        root_members = {line.split('  ')[1] for line in (output / 'SHA256SUMS.txt').read_text().splitlines()}
        self.assertEqual(root_members, {p.relative_to(output).as_posix() for p in output.rglob('*')
                                       if p.is_file() and p != output / 'SHA256SUMS.txt'})
        return result

    def test_complete_and_mixed_batches_preserve_independent_case_state(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = write_batch(root / 'saved', ('sign', 'resumed', 'bad'))
            before = {p.relative_to(source): p.read_bytes() for p in source.rglob('*') if p.is_file()}
            r = self.check(m, source, root / 'out', 'MATCH_WITH_INPUT_REJECTIONS')
            self.assertEqual((r['input_count'], r['matched_cases'], r['input_rejections_confirmed'], r['reference_steps']), (3, 2, 1, 5))
            self.assertEqual([c['status'] for c in r['cases']], ['MATCH', 'MATCH', 'INPUT_REJECTION_CONFIRMED'])
            self.assertEqual([c['reference_steps'] for c in r['cases']], [4, 1, 0])
            self.assertEqual(r['reference_helper_counts'], {'compile_calls': 2, 'selected_definitions_compiled': 4,
                'limiter_direct': 0, 'limiter_traced': 5, 'fault_explicit': 5, 'fault_default': 0, 'traced_clip_calls': 10})
            self.assertEqual(before, {p.relative_to(source): p.read_bytes() for p in source.rglob('*') if p.is_file()})
            self.assertEqual(m.exit_code(r), 0)

    def test_coherent_saved_arithmetic_change_is_one_difference(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = write_batch(root / 'saved')
            edit_json(source / 'case-001/data', 'RESULTS.json',
                      lambda r: r['rows'][0]['model_output']['projection']['torque_float32'].update(bits_hex='00000000'))
            refresh(source)
            r = self.check(m, source, root / 'out', 'DIFFERENT')
            self.assertEqual((r['matched_cases'], r['different_cases'], r['numerical_difference_count']), (1, 1, 1))
            self.assertEqual(r['first_difference']['case_id'], 'case-001')
            self.assertEqual(r['first_difference']['field'], 'rows[0].model_output.projection.torque_float32.bits_hex')
            self.assertEqual(m.exit_code(r), 1)

    def test_rejected_only_batch_is_not_vacuous_numerical_match(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = write_batch(root / 'saved', ('bad',))
            r = self.check(m, source, root / 'out', 'NO_COMPLETED_CASES')
            self.assertEqual((r['matched_cases'], r['input_rejections_confirmed'], r['reference_steps']), (0, 1, 0))
            self.assertEqual(m.exit_code(r), 1)

    def test_missing_raw_rejection_stays_incomplete_even_with_matching_case(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = write_batch(root / 'saved', ('sign', 'missing'))
            r = self.check(m, source, root / 'out', 'INCOMPLETE')
            self.assertEqual((r['matched_cases'], r['input_rejections_unverified']), (1, 1))
            self.assertEqual(r['cases'][1]['status'], 'INPUT_REJECTION_UNVERIFIED')
            self.assertEqual(m.exit_code(r), 1)

    def test_recorded_rejection_code_must_match_actual_parser_rejection(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = write_batch(root / 'saved', ('bad',))
            edit_batch(source, lambda r: r['cases'][0].update(rejection_code='SCENARIO_KEYS'))
            rehash_portable(source)
            r = self.check(m, source, root / 'out', 'DIFFERENT')
            self.assertEqual((r['rejection_mismatch_cases'], r['numerical_difference_count']), (1, 0))
            self.assertEqual(r['cases'][0]['observed_rejection_code'], 'SCENARIO_JSON')
            self.assertEqual(r['cases'][0]['status'], 'REJECTION_MISMATCH')

    def test_valid_raw_cannot_be_mislabeled_as_rejected(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = write_batch(root / 'saved', ('bad',))
            raw = (ROOT / 'examples/synthetic_resumed_v1.json').read_bytes()
            (source / 'inputs/case-001.json').write_bytes(raw)
            edit_batch(source, lambda r: r['cases'][0].update(input_sha256=hashlib.sha256(raw).hexdigest()))
            rehash_portable(source)
            r = self.check(m, source, root / 'out', 'DIFFERENT')
            self.assertEqual(r['rejection_mismatch_cases'], 1)
            self.assertIsNone(r['cases'][0]['observed_rejection_code'])
            self.assertEqual(r['reference_steps'], 0)

    def test_late_corrupt_case_prevents_all_independent_computation(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = write_batch(root / 'saved')
            (source / 'case-002/data/RESULTS.json').write_bytes(b'{}')
            edit_batch(source, lambda r: None)
            with patch.object(m.reference, 'check_saved', side_effect=AssertionError('REFERENCE_MUST_NOT_RUN')):
                with self.assertRaises(ValueError):
                    m.check_batch(source, root / 'out')
            self.assertFalse((root / 'out').exists())

    def test_output_guards_precede_input_reads(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = write_batch(root / 'saved')
            (root / 'exists').mkdir()
            (root / 'dangling').symlink_to(root / 'absent')
            for target in [root / 'exists', root / 'dangling', root / 'missing-parent/out', source / 'out', ROOT / 'new-r39-output']:
                with self.subTest(target=target), patch.object(m, '_owned_files', side_effect=AssertionError('INPUT_READ')):
                    with self.assertRaises(m.BatchReferenceError):
                        m.check_batch(source, target)

    def test_loop_symlink_fifo_and_resource_limits_reject_before_reference(self):
        m = self.module()
        from integration_tools import scenario_compare_input as reader

        for mode in ['loop', 'root-link', 'member-link', 'fifo', 'limit']:
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                source = write_batch(root / 'saved')
                if mode in ('loop', 'root-link'):
                    link = root / 'link'
                    link.symlink_to('link' if mode == 'loop' else source)
                    source = link
                elif mode in ('member-link', 'fifo'):
                    member = source / 'case-001/producer.log'
                    member.unlink()
                    if mode == 'fifo':
                        os.mkfifo(member)
                    else:
                        member.symlink_to('/dev/zero')
                with (patch.object(reader, 'MAX_TOTAL_BYTES', 1024 if mode == 'limit' else 128 * 1024 * 1024),
                      patch.object(m.reference, 'check_saved', side_effect=AssertionError('REFERENCE_MUST_NOT_RUN'))):
                    with self.assertRaises(ValueError):
                        m.check_batch(source, root / 'out')
                self.assertFalse((root / 'out').exists())

    def test_worker_consumes_owned_snapshot_if_original_changes(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = write_batch(root / 'saved')
            check_saved = m.reference.check_saved

            def mutate_then_check(saved, output):
                self.assertFalse(saved.is_relative_to(source))
                (source / 'BATCH.json').write_bytes(b'changed after bounded snapshot')
                return check_saved(saved, output)

            with patch.object(m.reference, 'check_saved', side_effect=mutate_then_check):
                r = self.check(m, source, root / 'out')
            self.assertEqual(r['reference_steps'], 5)

    def test_worker_failure_is_error_not_difference_or_proven_zero_work(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = write_batch(root / 'saved')
            launch = m.reference._launch

            def failed_first(raw):
                if json.loads(raw)['scenario_id'] == 'R31_sign_cycle':
                    raise m.reference.ReferenceCheckError('REFERENCE_WORKER_FAILED')
                return launch(raw)

            with patch.object(m.reference, '_launch', side_effect=failed_first):
                r = self.check(m, source, root / 'out', 'ERROR')
            self.assertEqual((r['error_cases'], r['matched_cases'], r['reference_steps']), (1, 1, 1))
            self.assertEqual(r['cases'][0]['error_code'], 'REFERENCE_WORKER_FAILED')
            self.assertIsNone(r['cases'][0]['reference_steps'])
            self.assertIn('FAILED_WORK_MAY_BE_NONZERO', r['reference_steps_accounting'])
            self.assertFalse((root / 'out/case-001').exists())
            self.assertEqual(m.exit_code(r), 2)

    def test_source_change_blocks_final_publication(self):
        m = self.module()
        identity = m._source_identity()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = write_batch(root / 'saved', ('resumed',))
            with patch.object(m, '_source_identity', side_effect=[identity, {'changed': True}]):
                with self.assertRaisesRegex(m.BatchReferenceError, '^BATCH_REFERENCE_SOURCE_CHANGED$'):
                    m.check_batch(source, root / 'out')
            self.assertFalse((root / 'out').exists())

    def test_failed_child_read_does_not_publish_half_a_successful_case(self):
        m = self.module()
        original_read = Path.read_bytes

        def fail_child_checksum(path):
            if (path.name == 'SHA256SUMS.txt' and path.parent.name == 'case-001'
                    and path.parent.parent.name.startswith('cyberlateral-r39-owned-')):
                raise OSError('synthetic local read failure')
            return original_read(path)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = write_batch(root / 'saved', ('resumed',))
            with patch.object(Path, 'read_bytes', fail_child_checksum):
                r = self.check(m, source, root / 'out', 'ERROR')
            self.assertEqual(r['error_cases'], 1)
            self.assertIsNone(r['cases'][0]['difference_count'])
            self.assertFalse((root / 'out/case-001').exists())

    def test_publication_failure_keeps_partial_and_retry_never_overwrites(self):
        m = self.module()
        original_open = Path.open
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = write_batch(root / 'saved', ('bad',))
            target = root / 'out'

            def fail_marker(path, *args, **kwargs):
                if path == target / 'BATCH_REFERENCE_CHECK.json':
                    raise OSError('synthetic publication failure')
                return original_open(path, *args, **kwargs)

            with patch.object(Path, 'open', fail_marker):
                with self.assertRaisesRegex(m.BatchReferenceError, '^BATCH_REFERENCE_PUBLICATION_FAILED$'):
                    m.check_batch(source, target)
            self.assertTrue((target / 'SUMMARY_KO.md').is_file())
            self.assertFalse((target / 'BATCH_REFERENCE_CHECK.json').exists())
            before = {p.name: p.read_bytes() for p in target.iterdir()}
            with self.assertRaisesRegex(m.BatchReferenceError, '^BATCH_REFERENCE_OUTPUT_EXISTS$'):
                m.check_batch(source, target)
            self.assertEqual(before, {p.name: p.read_bytes() for p in target.iterdir()})

    def test_worker_error_has_precedence_without_hiding_other_case_difference(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = write_batch(root / 'saved')
            edit_json(source / 'case-001/data', 'RESULTS.json',
                      lambda r: r['rows'][0]['model_output']['projection']['torque_float32'].update(bits_hex='00000000'))
            refresh(source)
            launch = m.reference._launch

            def fail_resumed(raw):
                if json.loads(raw)['scenario_id'] == 'R31_resumed':
                    raise m.reference.ReferenceCheckError('REFERENCE_WORKER_FAILED')
                return launch(raw)

            with patch.object(m.reference, '_launch', side_effect=fail_resumed):
                r = self.check(m, source, root / 'out', 'ERROR')
            self.assertEqual((r['error_cases'], r['different_cases'], r['numerical_difference_count']), (1, 1, 1))

    def test_runtime_and_missing_source_cannot_fallback(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = write_batch(root / 'saved')
            with patch.object(m.platform, 'python_version', return_value='3.12.0'):
                with self.assertRaisesRegex(m.BatchReferenceError, '^BATCH_REFERENCE_RUNTIME$'):
                    m.check_batch(source, root / 'runtime')
            with patch.object(m, 'ROOT', root / 'missing-component'):
                with self.assertRaises(ValueError):
                    m.check_batch(source, root / 'identity')
            self.assertFalse((root / 'runtime').exists())
            self.assertFalse((root / 'identity').exists())

    def test_moved_inputs_repeat_all_bytes_without_paths_or_input_labels(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = write_batch(root / 'saved')
            edit_batch(source, lambda r: r['cases'][0].update(input_name='PRIVATE_LABEL_<script>.json'))
            rehash_portable(source)
            shutil.copytree(source, root / 'moved')
            for i, value in enumerate([source, root / 'moved']):
                self.check(m, value, root / f'out-{i}')
            first = {p.relative_to(root / 'out-0'): p.read_bytes() for p in (root / 'out-0').rglob('*') if p.is_file()}
            second = {p.relative_to(root / 'out-1'): p.read_bytes() for p in (root / 'out-1').rglob('*') if p.is_file()}
            self.assertEqual(first, second)
            for raw in first.values():
                self.assertNotIn(str(root).encode(), raw)
                self.assertNotIn(b'PRIVATE_LABEL_', raw)


if __name__ == '__main__':
    unittest.main()
