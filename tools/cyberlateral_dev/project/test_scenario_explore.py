"""R42 must retain real reference verdicts and complete reproducible sequences."""

import hashlib
import importlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scenario_compare_fixture import refresh
from scenario_report_fixture import edit_json
from v1_helpers import ROOT


class ExplorationTests(unittest.TestCase):
    def module(self):
        self.assertTrue((ROOT / 'integration_tools/scenario_explore_run.py').is_file(), 'Missing R42 exploration runner')
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        return importlib.import_module('integration_tools.scenario_explore_run')

    def check_manifest(self, root):
        for sums in root.rglob('*SHA256SUMS.txt'):
            for line in sums.read_text().splitlines():
                digest, name = line.split('  ')
                self.assertEqual(hashlib.sha256((sums.parent / name).read_bytes()).hexdigest(), digest)
        self.assertEqual({line.split('  ')[1] for line in (root / 'SHA256SUMS.txt').read_text().splitlines()},
                         {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p != root / 'SHA256SUMS.txt'})

    def test_real_match_has_generated_inputs_graphs_reference_counts_and_gates(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'out'
            r = m.run_exploration(42, 1, 16, output)
            self.assertEqual((r['status'], r['model_steps'], r['reference_steps'], m.exit_code(r)), ('MATCH', 16, 16, 0))
            self.assertEqual(r['findings'], [])
            self.assertEqual(json.loads((output / 'EXPLORATION.json').read_bytes()), r)
            self.assertEqual((output / 'EXPLORATION.json').read_bytes(),
                             (json.dumps(r, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode())
            self.assertTrue((output / 'workflow/batch/case-001/report/index.html').is_file())
            self.assertTrue((output / 'workflow/reference/case-001/REFERENCE_CHECK.json').is_file())
            self.assertFalse((output / 'reproducers').exists())
            self.assertEqual((r['gates']['R_BUDGET'], r['gates']['STATIC_EVIDENCE_GATE']), ('UNRESOLVED', 'FAIL'))
            self.assertTrue(all(r['gates'][k] is None for k in ['actual_r', 'T2', 'vehicle_scale']))
            self.assertTrue(all(r['gates'][k] == 0 for k in ['F61_calculator_executions', 'r_calculations', 'dt_calculations']))
            self.assertEqual(r['time_semantics'], 'INVOCATION_ORDER_ONLY_NOT_ELAPSED_TIME')
            self.assertNotIn(tmp, (output / 'EXPLORATION.json').read_text())
            self.check_manifest(output)

    def test_real_coherent_wrong_projection_is_detected_and_whole_input_preserved(self):
        m = self.module()
        check = m.workflow.reference.check_batch

        def mutate_then_check(source, output):
            edit_json(source / 'case-001/data', 'RESULTS.json',
                      lambda r: r['rows'][0]['model_output']['projection']['torque_float32'].update(bits_hex='00000000'))
            refresh(source)
            return check(source, output)

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'out'
            with patch.object(m.workflow.reference, 'check_batch', side_effect=mutate_then_check):
                r = m.run_exploration(42, 1, 16, output)
            self.assertEqual((r['status'], r['difference_count'], m.exit_code(r)), ('DIFFERENT', 1, 1))
            self.assertEqual(len(r['findings']), 1)
            finding = r['findings'][0]
            self.assertEqual(finding['case_status'], 'DIFFERENT')
            self.assertEqual(finding['first_difference']['field'], 'rows[0].model_output.projection.torque_float32.bits_hex')
            original = (output / 'generated/case-001.json').read_bytes()
            self.assertEqual((output / finding['reproducer']).read_bytes(), original)
            self.assertEqual(len(json.loads(original)['samples']), 16)
            self.assertEqual(finding['reproducer_scope'], 'FULL_ORIGINAL_SEQUENCE_NOT_MINIMIZED')
            self.assertEqual(finding['input_sha256'], hashlib.sha256(original).hexdigest())
            self.check_manifest(output)

    def test_reference_error_is_not_difference_or_match_and_keeps_reproducer(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'out'
            with patch.object(m.workflow.reference.reference, '_launch',
                              side_effect=m.workflow.reference.reference.ReferenceCheckError('REFERENCE_WORKER_FAILED')):
                r = m.run_exploration(42, 1, 16, output)
            self.assertEqual((r['status'], r['model_steps'], r['reference_steps'], m.exit_code(r)), ('ERROR', 16, 0, 2))
            self.assertIn('FAILED_WORK_MAY_BE_NONZERO', r['reference_steps_accounting'])
            self.assertEqual(r['findings'][0]['error_code'], 'REFERENCE_WORKER_FAILED')
            self.assertEqual((output / r['findings'][0]['reproducer']).read_bytes(), (output / 'generated/case-001.json').read_bytes())
            self.check_manifest(output)

    def test_all_nonmatching_cases_preserved_not_only_first(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'out'
            with patch.object(m.workflow.reference.reference, '_launch',
                              side_effect=m.workflow.reference.reference.ReferenceCheckError('REFERENCE_WORKER_FAILED')):
                r = m.run_exploration(42, 2, 16, output)
            self.assertEqual(r['status'], 'ERROR')
            self.assertEqual([f['case_id'] for f in r['findings']], ['case-001', 'case-002'])
            self.assertEqual([len(json.loads((output / f['reproducer']).read_bytes())['samples']) for f in r['findings']], [16, 16])

    def test_repeat_records_and_portable_batch_bytes_match_without_private_receipts(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            first, second = [Path(tmp) / name for name in ['one', 'two']]
            one, two = [m.run_exploration(42, 1, 16, output) for output in [first, second]]
            self.assertEqual(one, two)
            for name in ['EXPLORATION.json', 'GENERATION.json', 'SUMMARY_KO.md', 'generated/case-001.json',
                         'workflow/WORKFLOW.json', 'workflow/batch/PORTABLE_SHA256SUMS.txt']:
                self.assertEqual((first / name).read_bytes(), (second / name).read_bytes())
            for line in (first / 'workflow/batch/PORTABLE_SHA256SUMS.txt').read_text().splitlines():
                _, name = line.split('  ')
                self.assertEqual((first / 'workflow/batch' / name).read_bytes(), (second / 'workflow/batch' / name).read_bytes())
            self.assertNotEqual((first / 'workflow/RECEIPT.json').read_bytes(), (second / 'workflow/RECEIPT.json').read_bytes())

    def test_bad_parameters_and_output_guards_create_no_new_output(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'exists').mkdir()
            (root / 'exists/keep').write_bytes(b'keep')
            (root / 'dangling').symlink_to(root / 'missing')
            for target in [root / 'exists', root / 'dangling', root / 'no-parent/out', ROOT / 'new-r42-out']:
                with self.subTest(target=target), self.assertRaises(ValueError):
                    m.run_exploration(42, 1, 16, target)
            self.assertEqual((root / 'exists/keep').read_bytes(), b'keep')
            for args in [(True, 1, 16), (0, 0, 16), (0, 1, 257)]:
                with self.subTest(args=args), self.assertRaisesRegex(ValueError, 'EXPLORATION_PARAMETERS'):
                    m.run_exploration(*args, root / 'bad')
                self.assertFalse((root / 'bad').exists())

    def test_source_or_generated_input_change_prevents_completion(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            identity = m._source_identity()
            with patch.object(m, '_source_identity', side_effect=[identity, {'changed': '0' * 64}]):
                with self.assertRaisesRegex(ValueError, 'EXPLORATION_SOURCE_CHANGED'):
                    m.run_exploration(42, 1, 16, root / 'source-out')
            run = m.workflow.run_workflow

            def alter_owned(inputs, output):
                record = run(inputs, output)
                inputs[0].write_bytes(b'changed after worker')
                return record

            with patch.object(m.workflow, 'run_workflow', side_effect=alter_owned):
                with self.assertRaisesRegex(ValueError, 'EXPLORATION_INPUT_CHANGED'):
                    m.run_exploration(42, 1, 16, root / 'input-out')
            self.assertFalse((root / 'source-out/EXPLORATION.json').exists())
            self.assertFalse((root / 'input-out/EXPLORATION.json').exists())

    def test_worker_failure_preserves_inputs_but_no_completion_marker(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'out'
            with patch.object(m.workflow.batch, '_worker', side_effect=m.workflow.batch.BatchError('BATCH_WORKER_FAILED')):
                with self.assertRaisesRegex(ValueError, 'BATCH_WORKER_FAILED'):
                    m.run_exploration(42, 1, 16, output)
            self.assertTrue((output / 'generated/case-001.json').is_file())
            self.assertFalse((output / 'EXPLORATION.json').exists())
            self.assertFalse((output / 'SHA256SUMS.txt').exists())

    def test_contradictory_completion_count_never_becomes_match(self):
        m = self.module()
        run = m.workflow.run_workflow

        def wrong_count(inputs, output):
            record = run(inputs, output)
            return {**record, 'completed': 0}

        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(m.workflow, 'run_workflow', side_effect=wrong_count):
                r = m.run_exploration(42, 1, 16, Path(tmp) / 'out')
            self.assertEqual((r['status'], m.exit_code(r)), ('ERROR', 2))

    def test_generation_record_keeps_closed_gates_and_zero_generation_work(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'out'
            m.run_exploration(42, 1, 16, output)
            generated = json.loads((output / 'GENERATION.json').read_bytes())
            self.assertEqual(generated['model_executions'], 0)
            self.assertEqual(generated['gates']['R_BUDGET'], 'UNRESOLVED')
            self.assertEqual(generated['gates']['STATIC_EVIDENCE_GATE'], 'FAIL')

    def test_reference_summary_and_case_count_contradictions_cannot_match(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'out'
            m.run_exploration(42, 1, 16, output)
            produced = json.loads((output / 'workflow/WORKFLOW.json').read_bytes())
            original = json.loads((output / 'workflow/reference/BATCH_REFERENCE_CHECK.json').read_bytes())
            mutations = [('completed_cases', 0), ('matched_cases', 0), ('reference_steps', 0), ('error_cases', 1),
                         ('input_count', 0), ('different_cases', 1), ('input_rejections_confirmed', 1),
                         ('input_rejections_unverified', 1), ('rejection_mismatch_cases', 1),
                         ('numerical_difference_count', 1), ('matched_cases', True)]
            for field, value in mutations:
                changed = json.loads(json.dumps(original))
                changed[field] = value
                with self.subTest(field=field, value=value):
                    self.assertEqual(m._verdict(produced, changed, 1, 16), 'ERROR')
            for field, value in [('reference_steps', 0), ('reference_steps', True), ('difference_count', 1),
                                 ('difference_count', False), ('source_status', 'REJECTED')]:
                changed = json.loads(json.dumps(original))
                changed['cases'][0][field] = value
                with self.subTest(case_field=field, value=value):
                    self.assertEqual(m._verdict(produced, changed, 1, 16), 'ERROR')
            changed = json.loads(json.dumps(original))
            changed['reference_helper_counts']['limiter_traced'] = 0
            self.assertEqual(m._verdict(produced, changed, 1, 16), 'ERROR')


class ExplorationCLITests(unittest.TestCase):
    def tool(self):
        path = ROOT / 'tools/scenario_explore.py'
        self.assertTrue(path.is_file(), 'Missing R42 exploration CLI')
        return path

    def cli(self, *args):
        return subprocess.run([sys.executable, '-I', '-B', self.tool(), *map(str, args)], capture_output=True, timeout=90, check=False)

    def test_real_cli_canonical_stdout_and_complete_saved_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'out'
            p = self.cli('--seed', 42, '--cases', 1, '--steps', 16, '--output', output)
            self.assertEqual(p.returncode, 0, p.stderr.decode())
            self.assertEqual(p.stderr, b'')
            record = json.loads(p.stdout)
            self.assertEqual((record['status'], record['model_steps'], record['reference_steps']), ('MATCH', 16, 16))
            self.assertTrue((output / 'EXPLORATION.json').is_file())
            self.assertEqual(p.stdout, (json.dumps(record, sort_keys=True, separators=(',', ':')) + '\n').encode())

    def test_required_parameters_unsupported_vehicle_flags_and_collisions_reject(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'out'
            common = ['--seed', 42, '--cases', 1, '--steps', 16, '--output', output]
            for args in [[], common[:-2], common + ['--r', 0], common + ['--dt', 0.01], common + ['--input', 'car.json'],
                         ['--seed', -1, '--cases', 1, '--steps', 16, '--output', output]]:
                p = self.cli(*args)
                self.assertEqual(p.returncode, 2)
                self.assertEqual(p.stdout, b'')
                self.assertNotIn(b'Traceback', p.stderr)
                self.assertFalse(output.exists())
            output.mkdir()
            p = self.cli(*common)
            self.assertEqual(p.returncode, 2)
            self.assertEqual(list(output.iterdir()), [])

    def test_real_frontend_runs_without_model_numpy_or_native_imports(self):
        code = ('import runpy,sys\n'
                'class Barrier:\n'
                ' def find_spec(self,fullname,path=None,target=None):\n'
                '  if fullname.split(".")[0] in {"cyberlateral_dev","numpy","capnp","openpilot","opendbc","cereal"}: '
                'raise AssertionError("EXPLORE_FRONTEND_IMPORT:"+fullname)\n'
                'sys.meta_path.insert(0,Barrier())\n'
                'sys.argv=sys.argv[1:]\nrunpy.run_path(sys.argv[0],run_name="__main__")\n')
        with tempfile.TemporaryDirectory() as tmp:
            p = subprocess.run([sys.executable, '-I', '-B', '-c', code, self.tool(), '--seed', '42', '--cases', '1',
                                '--steps', '16', '--output', str(Path(tmp) / 'out')], capture_output=True, timeout=90, check=False)
            self.assertEqual(p.returncode, 0, p.stderr.decode())
            self.assertEqual(json.loads(p.stdout)['status'], 'MATCH')


if __name__ == '__main__':
    unittest.main()
