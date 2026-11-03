"""Producer path errors are classified without hiding capture/parser/worker faults."""

import importlib
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scenario_fixture import document, encode
from v1_helpers import ROOT


class ScenarioProducerPathTests(unittest.TestCase):
    def modules(self):
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        names = ['scenario_batch_input', 'scenario_batch_run', 'scenario_workflow_input',
                 'scenario_workflow_run', 'scenario_explore_run', 'scenario_campaign_run']
        return tuple(importlib.import_module('integration_tools.' + name) for name in names)

    def reject(self, call, kind, code):
        try:
            call()
        except kind as error:
            self.assertEqual(error.code, code)
            return error
        except Exception as error:
            self.fail(f'Unclassified boundary failure: {type(error).__name__}')
        self.fail('Expected rejection missing')

    def outputs(self, root, output):
        capture, batch, _, workflow, exploration, campaign = self.modules()
        return [('batch', capture.BatchError, 'BATCH_IO', lambda: batch.run_batch([root / 'missing.json'], output)),
                ('workflow', capture.BatchError, 'BATCH_IO', lambda: workflow.run_workflow([root / 'missing.json'], output)),
                ('exploration', exploration.ExplorationError, 'EXPLORATION_IO', lambda: exploration.run_exploration(42, 1, 16, output)),
                ('campaign', campaign.CampaignError, 'CAMPAIGN_IO', lambda: campaign.run_campaign([42], 1, 16, output))]

    def isolated_cli(self, tool, arguments):
        code = ('import importlib.util,sys\n'
                'from unittest.mock import patch\n'
                'sys.path.insert(0,' + repr(str(ROOT)) + ')\n'
                'blocked={"cyberlateral_dev","numpy","capnp","openpilot","opendbc","cereal","integration_tools.verify"}\n'
                'class Barrier:\n'
                ' def find_spec(self,fullname,path=None,target=None):\n'
                '  if fullname in blocked or fullname.split(".")[0] in blocked: raise AssertionError("MODEL_IMPORT:"+fullname)\n'
                'sys.meta_path.insert(0,Barrier())\n'
                'from integration_tools import scenario_batch_run as b,scenario_workflow_run as w,scenario_explore_run as x,scenario_campaign_run as c\n'
                'spec=importlib.util.spec_from_file_location("actual_cli",' + repr(str(ROOT / 'tools' / tool)) + ')\n'
                'cli=importlib.util.module_from_spec(spec);spec.loader.exec_module(cli)\n'
                'with patch.object(b,"_source_hashes",side_effect=AssertionError("IDENTITY")),patch.object(b,"_worker",side_effect=AssertionError("WORKER")),patch.object(w,"_source_identity",side_effect=AssertionError("IDENTITY")),patch.object(x,"_source_identity",side_effect=AssertionError("IDENTITY")),patch.object(c,"_observe_identity",side_effect=AssertionError("IDENTITY")):\n'
                ' status=cli.main(' + repr(arguments) + ')\n'
                'assert not any(n in blocked or n.split(".")[0] in blocked for n in sys.modules)\n'
                'raise SystemExit(status)\n')
        return subprocess.run([sys.executable, '-I', '-B', '-c', code], capture_output=True, timeout=20, check=False)

    def cli_inputs(self, root):
        return [('scenario_batch.py', ['--input', str(root / 'missing.json')], 'BATCH_IO'),
                ('scenario_workflow.py', ['--input', str(root / 'missing.json')], 'BATCH_IO'),
                ('scenario_explore.py', ['--seed', '42', '--cases', '1', '--steps', '16'], 'EXPLORATION_IO'),
                ('scenario_campaign.py', ['--seed', '42', '--cases', '1', '--steps', '16'], 'CAMPAIGN_IO')]

    def test_capture_open_value_error_is_typed_with_original_cause(self):
        capture, *_ = self.modules()
        for original in [ValueError('private-open'), PermissionError('private-path')]:
            with patch.object(capture.os, 'open', side_effect=original):
                error = self.reject(lambda: capture._read(Path('unused')), capture.ScenarioError, 'SCENARIO_INPUT_FILE')
            self.assertIs(error.__cause__, original)

    def test_classified_capture_error_and_independently_saved_cause_remain(self):
        capture, *_ = self.modules()
        original_cause = OSError('saved-cause')
        classified = capture.ScenarioError('SCENARIO_SIZE')
        classified.__cause__ = original_cause
        with patch.object(capture.os, 'open', side_effect=classified), self.assertRaises(capture.ScenarioError) as caught:
            capture._read(Path('unused'))
        self.assertIs(caught.exception, classified)
        self.assertEqual(caught.exception.code, 'SCENARIO_SIZE')
        self.assertIs(caught.exception.__cause__, original_cause)

    def test_nul_capture_is_per_file_unavailable_and_workflow_still_refuses(self):
        capture, _, baseline, *_ = self.modules()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            try:
                items = capture.prepare_batch([root / 'bad\0input'], root / 'out')
            except Exception as error:
                self.fail(f'Unavailable input aborted capture: {type(error).__name__}')
            self.assertEqual(len(items), 1)
            self.assertEqual(items[0].rejection_code, 'SCENARIO_INPUT_FILE')
            self.assertIsNone(items[0].raw)
            self.assertIsNone(items[0].digest)
            self.assertIsNone(items[0].spec)
            self.reject(lambda: baseline.prepare_workflow([root / 'bad\0input'], root / 'out', None, root),
                        baseline.WorkflowError, 'WORKFLOW_INPUT_UNAVAILABLE')
            self.assertEqual(list(root.iterdir()), [])

    def test_all_nul_outputs_are_bounded_before_identity_or_model_workers(self):
        _, batch, _, workflow, exploration, campaign = self.modules()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with (patch.object(batch, '_source_hashes', side_effect=AssertionError('IDENTITY')),
                  patch.object(batch, '_worker', side_effect=AssertionError('WORKER')),
                  patch.object(workflow, '_source_identity', side_effect=AssertionError('IDENTITY')),
                  patch.object(exploration, '_source_identity', side_effect=AssertionError('IDENTITY')),
                  patch.object(campaign, '_observe_identity', side_effect=AssertionError('IDENTITY'))):
                for alias, kind, code, call in self.outputs(root, root / 'bad\0out'):
                    with self.subTest(frontend=alias):
                        error = self.reject(call, kind, code)
                        self.assertIsInstance(error.__cause__, ValueError)
            self.assertEqual(list(root.iterdir()), [])

    def test_workflow_baseline_nul_is_existing_location_error(self):
        _, _, baseline, workflow, *_ = self.modules()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'source.json'
            raw = encode(document())
            source.write_bytes(raw)
            with (patch.object(workflow, '_source_identity', side_effect=AssertionError('IDENTITY')),
                  patch.object(baseline, '_owned_files', side_effect=AssertionError('BASELINE_READ'))):
                error = self.reject(lambda: workflow.run_workflow([source], root / 'out', root / 'bad\0baseline'),
                                    baseline.WorkflowError, 'WORKFLOW_BASELINE_LOCATION')
            self.assertIsInstance(error.__cause__, ValueError)
            self.assertEqual(source.read_bytes(), raw)
            self.assertEqual(list(root.iterdir()), [source])

    def test_invalid_generation_parameters_still_win_before_output_path(self):
        *_, exploration, campaign = self.modules()
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'bad\0out'
            self.reject(lambda: exploration.run_exploration(42, 1, 1, output),
                        exploration.ExplorationError, 'EXPLORATION_PARAMETERS')
            self.reject(lambda: campaign.run_campaign([42], 1, 1, output), campaign.CampaignError, 'CAMPAIGN_PARAMETERS')
            self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_later_capture_and_parser_value_errors_are_not_preflight_errors(self):
        capture, *_ = self.modules()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'source.json'
            raw = encode(document())
            source.write_bytes(raw)
            for stage in ['_read', 'parse_scenario']:
                original = ValueError('later-' + stage)
                with patch.object(capture, stage, side_effect=original), self.assertRaises(ValueError) as caught:
                    capture.prepare_batch([source], root / 'out')
                self.assertIs(caught.exception, original)
                self.assertFalse((root / 'out').exists())
                self.assertEqual(source.read_bytes(), raw)

    def test_programmer_errors_and_interrupts_at_metadata_are_not_hidden(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for alias, _, _, call in self.outputs(root, root / 'out'):
                for original in [TypeError('programmer'), RuntimeError('metadata-defect'), KeyboardInterrupt(), SystemExit(7)]:
                    with (self.subTest(frontend=alias, kind=type(original).__name__),
                          patch.object(Path, 'exists', side_effect=original), self.assertRaises(type(original)) as caught):
                        call()
                    self.assertIs(caught.exception, original)
            self.assertEqual(list(root.iterdir()), [])

    def test_unclassified_metadata_failures_have_original_cause_and_scoped_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, output = Path(tmp), Path(tmp) / 'out'
            for method, target in [('exists', output), ('is_symlink', output), ('is_dir', root)]:
                actual = getattr(Path, method)
                for original in [PermissionError('private-path'), ValueError('private-value')]:
                    def fail(path, *args, target=target, actual=actual, original=original, **kwargs):
                        if path == target:
                            raise original
                        return actual(path, *args, **kwargs)

                    for alias, kind, code, call in self.outputs(root, output):
                        with self.subTest(frontend=alias, method=method), patch.object(Path, method, autospec=True, side_effect=fail):
                            error = self.reject(call, kind, code)
                            self.assertIs(error.__cause__, original)
            self.assertEqual(list(root.iterdir()), [])

    def test_classified_preflight_objects_and_saved_causes_are_not_rewrapped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for alias, kind, _, call in self.outputs(root, root / 'out'):
                original_cause = OSError('saved-original')
                classified = kind('CLASSIFIED_CODE')
                classified.__cause__ = original_cause
                with self.subTest(frontend=alias), patch.object(Path, 'exists', side_effect=classified), self.assertRaises(kind) as caught:
                    call()
                self.assertIs(caught.exception, classified)
                self.assertIs(caught.exception.__cause__, original_cause)

    def test_campaign_keeps_existing_exploration_prefix_and_cause_mapping(self):
        *_, exploration, campaign = self.modules()
        original_cause = OSError('original-metadata')
        classified = exploration.ExplorationError('EXPLORATION_OUTPUT_PARENT')
        classified.__cause__ = original_cause
        with patch.object(exploration, '_preflight', side_effect=classified):
            error = self.reject(lambda: campaign.run_campaign([42], 1, 16, Path('unused')),
                                campaign.CampaignError, 'CAMPAIGN_OUTPUT_PARENT')
        self.assertIs(error.__cause__, classified)
        self.assertIs(classified.__cause__, original_cause)

    def test_existing_output_parent_and_component_location_guards_keep_priority(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            existing = root / 'existing'
            existing.write_bytes(b'keep')
            for output, suffix in [(existing, 'OUTPUT_EXISTS'), (root / 'missing/out', 'OUTPUT_PARENT'),
                                   (ROOT / 'new-r55-output', 'OUTPUT_LOCATION')]:
                for alias, kind, _, call in self.outputs(root, output):
                    prefix = 'BATCH_' if alias in {'batch', 'workflow'} else alias.upper() + '_'
                    with self.subTest(frontend=alias, suffix=suffix):
                        self.reject(call, kind, prefix + suffix)
            self.assertEqual(existing.read_bytes(), b'keep')
            self.assertEqual(list(root.iterdir()), [existing])

    def test_batch_encoding_priority_differs_from_exploration_existing_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            existing = root / 'linux-\udcff'
            existing.write_bytes(b'keep')
            for alias, kind, _, call in self.outputs(root, existing):
                code = 'BATCH_PATH_ENCODING' if alias in {'batch', 'workflow'} else alias.upper() + '_OUTPUT_EXISTS'
                with self.subTest(frontend=alias):
                    self.reject(call, kind, code)
            self.assertEqual(existing.read_bytes(), b'keep')

    @unittest.skipIf(os.geteuid() == 0, 'Actual mode000 needs an unprivileged actor')
    def test_actual_permission_output_api_and_real_os_argv_cli_are_bounded(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            denied = root / 'denied'
            denied.mkdir()
            denied.chmod(0)
            try:
                for alias, kind, code, call in self.outputs(root, denied / 'out'):
                    with self.subTest(frontend=alias, interface='API'):
                        error = self.reject(call, kind, code)
                        self.assertIsInstance(error.__cause__, PermissionError)
                for tool, arguments, code in self.cli_inputs(root):
                    with self.subTest(tool=tool, interface='OS_ARGV'):
                        result = subprocess.run([sys.executable, '-I', '-B', ROOT / 'tools' / tool, *arguments,
                                                 '--output', denied / 'out'], capture_output=True, timeout=20, check=False)
                        self.assertEqual((result.returncode, result.stdout, result.stderr),
                                         (2, b'', ('REJECTED: ' + code + '\n').encode()))
            finally:
                denied.chmod(0o700)
            self.assertEqual(list(denied.iterdir()), [])
            self.assertEqual(list(root.iterdir()), [denied])

    def test_fresh_cli_nul_outputs_and_baseline_are_bounded_and_model_free(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for tool, arguments, code in self.cli_inputs(root):
                with self.subTest(tool=tool):
                    result = self.isolated_cli(tool, [*arguments, '--output', str(root / 'bad\0out')])
                    self.assertEqual((result.returncode, result.stdout, result.stderr),
                                     (2, b'', ('REJECTED: ' + code + '\n').encode()))
                    self.assertEqual(list(root.iterdir()), [])
            source = root / 'source.json'
            raw = encode(document())
            source.write_bytes(raw)
            result = self.isolated_cli('scenario_workflow.py', ['--input', str(source), '--output', str(root / 'out'),
                                                               '--baseline', str(root / 'bad\0baseline')])
            self.assertEqual((result.returncode, result.stdout, result.stderr), (2, b'', b'REJECTED: WORKFLOW_BASELINE_LOCATION\n'))
            self.assertEqual(source.read_bytes(), raw)
            self.assertEqual(list(root.iterdir()), [source])

    def test_unicode_capture_and_workflow_preparation_keep_owned_bytes(self):
        capture, _, baseline, *_ = self.modules()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / '입력.json'
            raw = encode(document())
            source.write_bytes(raw)
            items = capture.prepare_batch([source], root / '출력')
            prepared, owned, record = baseline.prepare_workflow([source], root / '출력', None, root)
            self.assertEqual(items, prepared)
            self.assertIsNone(owned)
            self.assertIsNone(record)
            self.assertEqual(items[0].raw, raw)
            self.assertIsNone(items[0].rejection_code)
            self.assertEqual(source.read_bytes(), raw)
            self.assertEqual(list(root.iterdir()), [source])

    def test_capture_nonregular_and_size_classifications_are_not_collapsed(self):
        capture, *_ = self.modules()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            directory, large = root / 'directory', root / 'large'
            directory.mkdir()
            large.write_bytes(b'x' * (capture.MAX_BYTES + 1))
            self.reject(lambda: capture._read(directory), capture.ScenarioError, 'SCENARIO_INPUT_FILE')
            self.reject(lambda: capture._read(large), capture.ScenarioError, 'SCENARIO_SIZE')

    def test_later_identity_failures_do_not_turn_into_preflight_io(self):
        _, batch, _, workflow, exploration, campaign = self.modules()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'source.json'
            raw = encode(document())
            source.write_bytes(raw)
            calls = [(batch, '_source_hashes', lambda: batch.run_batch([source], root / 'out')),
                     (workflow, '_source_identity', lambda: workflow.run_workflow([source], root / 'out')),
                     (exploration, '_source_identity', lambda: exploration.run_exploration(42, 1, 16, root / 'out')),
                     (campaign, '_observe_identity', lambda: campaign.run_campaign([42], 1, 16, root / 'out'))]
            for module, stage, call in calls:
                original = ValueError('later-identity')
                with self.subTest(stage=stage), patch.object(module, stage, side_effect=original), self.assertRaises(ValueError) as caught:
                    call()
                self.assertIs(caught.exception, original)
                self.assertFalse((root / 'out').exists())
            self.assertEqual(source.read_bytes(), raw)
