"""Independent saved-result checks; coherent wrong arithmetic must not pass."""

import importlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from scenario_fixture import document, encode
from scenario_report_fixture import canonical, edit_json, layout_bundle, write_bundle
from v1_helpers import ROOT


class ScenarioReferenceTests(unittest.TestCase):
    def module(self):
        self.assertTrue((ROOT / 'integration_tools/scenario_reference_run.py').is_file(), 'Missing R38 independent saved-result checker')
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        return importlib.import_module('integration_tools.scenario_reference_run')

    def rewrite(self, source, change):
        from integration_tools.scenario_output import render_outputs
        from integration_tools.scenario_report_data import _spec

        record = json.loads((source / 'RESULTS.json').read_bytes())
        change(record)
        spec = _spec(json.loads((source / 'INPUT.json').read_bytes()))
        receipt = json.loads((source / 'RECEIPT.json').read_bytes())
        saved = {key: record[key] for key in ['model_steps', 'rows', 'final_state']}
        for name, raw in render_outputs(spec, saved, record['identity'], receipt).items():
            (source / name).write_bytes(raw)

    def check(self, module, source, target, status='MATCH'):
        result = module.check_saved(source, target)
        self.assertEqual(result['status'], status)
        self.assertEqual(result['new_model_executions'], 0)
        self.assertEqual(result['gates']['R_BUDGET'], 'UNRESOLVED')
        self.assertEqual(result['gates']['STATIC_EVIDENCE_GATE'], 'FAIL')
        self.assertIsNone(result['gates']['actual_r'])
        self.assertEqual({p.name for p in target.iterdir()}, {'REFERENCE_CHECK.json', 'SHA256SUMS.txt'})
        self.assertEqual((target / 'REFERENCE_CHECK.json').read_bytes(), canonical(result))
        return result

    def test_sign_and_resumed_saved_results_match_without_new_model(self):
        module = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for profile, count in [('sign', 4), ('resumed', 1)]:
                source = write_bundle(root / profile, profile)
                before = {p.name: p.read_bytes() for p in source.iterdir()}
                result = self.check(module, source, root / (profile + '-check'))
                self.assertEqual(result['reference_steps'], count)
                self.assertEqual(result['reference_helper_counts']['limiter_traced'], count)
                self.assertEqual(result['reference_helper_counts']['fault_explicit'], count)
                self.assertEqual(result['reference_forbidden_modules_loaded'], [])
                self.assertEqual(result['difference_count'], 0)
                self.assertEqual(before, {p.name: p.read_bytes() for p in source.iterdir()})

    def test_all_six_r35_valid_scenarios_match_selected_source_reference(self):
        module = self.module()
        from integration_tools.scenario_run import run_scenario

        reference = json.loads((ROOT / 'reference/r35_regression_expected_v1.json').read_bytes())
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            count = 0
            for i, filename in enumerate(reference['order'][:6]):
                source = root / f'case-{i}'
                run_scenario(ROOT / 'examples/r35' / filename, source)
                result = self.check(module, source, root / f'check-{i}')
                count += result['reference_steps']
            self.assertEqual(count, 38)

    def test_new_declared_scenario_not_whitelisted_to_catalog(self):
        module = self.module()
        from integration_tools.scenario_run import run_scenario

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            doc = document(3)
            doc['scenario_id'] = 'R38_new_declared_case'
            for row, q in zip(doc['samples'], [0.3, -0.0, -0.375], strict=True):
                row['request'] = q
            (root / 'new.json').write_bytes(encode(doc))
            run_scenario(root / 'new.json', root / 'saved')
            result = self.check(module, root / 'saved', root / 'check')
            self.assertEqual(result['reference_steps'], 3)

    def test_coherent_clip_quantization_fault_and_projection_mutations_differ(self):
        module = self.module()
        changes = [
            lambda r: r['rows'][0]['model_output']['trace']['downstream']['rate_clip']['lower'].update(value=-3),
            lambda r: r['rows'][0]['model_output']['trace']['quantization'].update(product_hex='0x1.4000000000000p+2'),
            lambda r: r['rows'][0]['model_output']['trace']['downstream'].update(fault_condition=True),
            lambda r: r['rows'][0]['model_output']['projection']['torque_float32'].update(bits_hex='00000000'),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for i, change in enumerate(changes):
                source = write_bundle(root / f'mutant-{i}')
                self.rewrite(source, change)
                result = self.check(module, source, root / f'check-{i}', 'DIFFERENT')
                self.assertGreater(result['difference_count'], 0)
                self.assertIsNotNone(result['first_difference'])

    def test_reference_state_does_not_consume_wrong_recorded_previous_output(self):
        module = self.module()

        def change(record):
            first, second = [row['model_output'] for row in record['rows'][:2]]
            first['projection'].update(integer_command=3, normalized_expression=0.1875,
                                       normalized_expression_hex='0x1.8000000000000p-3')
            first['trace']['downstream']['final_command'] = 3
            first['next_state']['previous_applied'] = 3
            first['trace']['downstream']['next_state']['previous_applied'] = 3
            record['rows'][1]['prepared']['state']['previous_applied'] = 3
            second['trace']['downstream']['limiter_previous'] = 3

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = write_bundle(root / 'wrong')
            self.rewrite(source, change)
            result = self.check(module, source, root / 'check', 'DIFFERENT')
            self.assertTrue(any('rows[1].prepared.state.previous_applied' == row['field'] for row in result['differences']))

    def test_late_invalid_input_rejects_before_reference_launch(self):
        module = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = write_bundle(root / 'bad')
            edit_json(source, 'INPUT.json', lambda r: r['samples'][-1].update(request_hex='0x1.0000000000001p+0'))
            with patch.object(module, '_launch', side_effect=AssertionError('REFERENCE_MUST_NOT_RUN')):
                with self.assertRaises(ValueError) as caught:
                    module.check_saved(source, root / 'check')
            self.assertEqual(str(caught.exception), 'REPORT_SCHEMA')
            self.assertFalse((root / 'check').exists())

    def test_existing_output_and_bad_locations_reject_before_input_read(self):
        module = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = write_bundle(root / 'saved')
            existing = root / 'existing'
            existing.mkdir()
            link = root / 'dangling'
            link.symlink_to(root / 'missing')
            for output in [existing, link, source / 'new', root / 'missing-parent' / 'new', ROOT / 'new-r38-output']:
                with self.subTest(output=output), patch.object(module, '_files', side_effect=AssertionError('INPUT_READ')):
                    with self.assertRaises(module.ReferenceCheckError):
                        module.check_saved(source, output)

    def test_invalid_checksum_and_partial_subset_reject_without_reference(self):
        module = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = write_bundle(root / 'bad')
            (source / 'RESULTS.json').write_bytes(b'{}')
            for i, expected in enumerate(['REPORT_CHECKSUM', 'REPORT_FILES']):
                with patch.object(module, '_launch', side_effect=AssertionError('REFERENCE_MUST_NOT_RUN')):
                    with self.assertRaises(ValueError) as caught:
                        module.check_saved(source, root / 'check')
                self.assertEqual(str(caught.exception), expected)
                if i == 0:
                    (source / 'RECEIPT.json').unlink()

    def test_looping_input_is_input_error_after_output_guards_without_reference(self):
        module = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'loop'
            source.symlink_to('loop')
            with patch.object(module, '_launch', side_effect=AssertionError('REFERENCE_MUST_NOT_RUN')):
                with self.assertRaisesRegex(ValueError, '^REPORT_INPUT_FILE$'):
                    module.check_saved(source, root / 'check')
                # Bad output still takes precedence over the unusable input.
                with self.assertRaisesRegex(ValueError, '^REFERENCE_OUTPUT_LOCATION$'):
                    module.check_saved(source, ROOT / 'new-r38-output')
            self.assertEqual(list(root.iterdir()), [source])

    def test_source_identity_failure_blocks_before_reference(self):
        module = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = write_bundle(root / 'saved')
            with (patch.object(module, 'ROOT', root / 'missing-component'),
                  patch.object(module, '_launch', side_effect=AssertionError('REFERENCE_MUST_NOT_RUN'))):
                with self.assertRaises(module.ReferenceCheckError) as caught:
                    module.check_saved(source, root / 'check')
            self.assertEqual(caught.exception.code, 'REFERENCE_SOURCE_IDENTITY')
            self.assertFalse((root / 'check').exists())

    def test_worker_failure_does_not_fallback_or_disclose_stderr(self):
        module = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = write_bundle(root / 'saved')
            failed = subprocess.CompletedProcess([], 1, b'', b'SECRET_PROCESS_DETAIL')
            with patch.object(module.subprocess, 'run', return_value=failed):
                with self.assertRaises(module.ReferenceCheckError) as caught:
                    module.check_saved(source, root / 'check')
            self.assertEqual(str(caught.exception), 'REFERENCE_WORKER_FAILED')
            self.assertFalse((root / 'check').exists())

    def test_source_change_during_reference_blocks_publication(self):
        module = self.module()
        identity = module._identity(ROOT)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = write_bundle(root / 'saved')
            with patch.object(module, '_identity', side_effect=[identity, {**identity, 'changed': True}]):
                with self.assertRaises(module.ReferenceCheckError) as caught:
                    module.check_saved(source, root / 'check')
            self.assertEqual(caught.exception.code, 'REFERENCE_SOURCE_CHANGED')
            self.assertFalse((root / 'check').exists())

    def test_moved_saved_inputs_and_reports_are_byte_identical(self):
        module = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = write_bundle(root / 'one')
            shutil.copytree(source, root / 'two')
            for i, name in enumerate(['one', 'two']):
                self.check(module, root / name, root / f'check-{i}')
            for name in ['REFERENCE_CHECK.json', 'SHA256SUMS.txt']:
                raw = (root / 'check-0' / name).read_bytes()
                self.assertEqual(raw, (root / 'check-1' / name).read_bytes())
                self.assertNotIn(str(root).encode(), raw)

    def test_detail_cap_still_counts_all_arithmetic_differences(self):
        module = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = layout_bundle(root / 'many', count=300)

            def change(record):
                for row in record['rows']:
                    row['model_output']['projection']['torque_float32']['bits_hex'] = '3f800000'

            self.rewrite(source, change)
            result = self.check(module, source, root / 'check', 'DIFFERENT')
            self.assertEqual(result['difference_count'], 300)
            self.assertEqual(len(result['differences']), 256)
            self.assertTrue(result['details_truncated'])

    def test_exact_imported_hash_mismatch_rejects_before_reference(self):
        module = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            component = root / 'component'
            component.mkdir()
            shutil.copyfile(ROOT / 'IMPORTED_ARTIFACT.json', component / 'IMPORTED_ARTIFACT.json')
            (component / 'build_backend.py').write_bytes(b'NOT_THE_PINNED_BUILD_BACKEND')
            with self.assertRaises(module.ReferenceCheckError) as caught:
                module._identity(component)
            self.assertEqual(caught.exception.code, 'REFERENCE_SOURCE_IDENTITY')
            self.assertEqual(str(caught.exception.__cause__), 'IMPORTED_HASH_MISMATCH:build_backend.py')

    def test_malformed_reference_reply_is_hard_error_not_partial_difference(self):
        module = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = write_bundle(root / 'saved')
            reply = module._launch((source / 'INPUT.json').read_bytes())
            del reply['rows'][0]['model_output']
            with patch.object(module, '_launch', return_value=reply):
                try:
                    module.check_saved(source, root / 'check')
                except Exception as error:
                    self.assertIsInstance(error, module.ReferenceCheckError)
                    self.assertEqual(str(error), 'REFERENCE_WORKER_RESULT')
                else:
                    self.fail('Malformed reference reply must reject, not publish')
            self.assertFalse((root / 'check').exists())

    def test_malformed_prepared_sample_state_and_extra_keys_are_worker_errors(self):
        module = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = write_bundle(root / 'saved')
            original = module._launch((source / 'INPUT.json').read_bytes())
            changes = [lambda r: r['rows'][0]['prepared'].pop('sample'),
                       lambda r: r['rows'][0]['prepared'].update(extra=True),
                       lambda r: r['rows'][0]['prepared'].update(state='not-state'),
                       lambda r: r['rows'][1]['prepared']['state'].update(previous_applied=3)]
            for i, change in enumerate(changes):
                reply = deepcopy(original)
                change(reply)
                with self.subTest(case=i), patch.object(module, '_launch', return_value=reply):
                    with self.assertRaises(module.ReferenceCheckError) as caught:
                        module.check_saved(source, root / f'check-{i}')
                    self.assertEqual(caught.exception.code, 'REFERENCE_WORKER_RESULT')
                    self.assertFalse((root / f'check-{i}').exists())

    def test_malformed_source_manifest_shapes_are_source_errors(self):
        module = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for manifest in [None, [], {'imported_files': []}, {'imported_files': None}]:
                (root / 'IMPORTED_ARTIFACT.json').write_bytes(canonical(manifest))
                with self.subTest(manifest=manifest):
                    try:
                        module._identity(root)
                    except Exception as error:
                        self.assertIsInstance(error, module.ReferenceCheckError)
                        self.assertEqual(str(error), 'REFERENCE_SOURCE_IDENTITY')
                    else:
                        self.fail('Malformed source identity must reject')


if __name__ == '__main__':
    unittest.main()
