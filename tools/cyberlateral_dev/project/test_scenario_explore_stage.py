"""Corrupt internal stage records must reject, not escape as indexing errors."""

import contextlib
import importlib
import io
import json
import runpy
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from v1_helpers import ROOT


def canonical(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


class ExplorationStageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        cls.module = importlib.import_module('integration_tools.scenario_explore_run')
        cls.scratch = tempfile.TemporaryDirectory(prefix='r42-stage-record-tests-')
        cls.addClassCleanup(cls.scratch.cleanup)
        cls.root = Path(cls.scratch.name)
        cls.fixture = cls.root / 'complete-fixture'
        cls.module.run_exploration(42, 2, 16, cls.fixture)  # Real model/reference work once, not a fabricated oracle.
        cls.stage = json.loads((cls.fixture / 'workflow/reference/BATCH_REFERENCE_CHECK.json').read_bytes())
        cls.workflow = json.loads((cls.fixture / 'workflow/WORKFLOW.json').read_bytes())
        cls.frontend = staticmethod(runpy.run_path(str(ROOT / 'tools/scenario_explore.py'))['main'])

    def reject(self, raw, cli=False):
        with tempfile.TemporaryDirectory(dir=self.root) as tmp:
            output = Path(tmp) / 'out'

            def completed_workflow(inputs, target):
                # Replace only the expensive completed worker boundary with a
                # complete real saved fixture. R42 parsing/publication stays real.
                self.assertEqual([p.read_bytes() for p in inputs],
                                 [(self.fixture / 'generated' / p.name).read_bytes() for p in inputs])
                shutil.copytree(self.fixture / 'workflow', target)
                (target / 'reference/BATCH_REFERENCE_CHECK.json').write_bytes(raw)
                return json.loads(json.dumps(self.workflow))

            with patch.object(self.module.workflow, 'run_workflow', side_effect=completed_workflow):
                if cli:
                    stdout, stderr = io.StringIO(), io.StringIO()
                    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                        try:
                            code = self.frontend(['--seed', '42', '--cases', '2', '--steps', '16', '--output', str(output)])
                        except Exception as error:
                            self.fail('CLI escaped with ' + type(error).__name__)
                    self.assertEqual(code, 2)
                    self.assertEqual(stdout.getvalue(), '')
                    self.assertEqual(stderr.getvalue(), 'REJECTED: EXPLORATION_STAGE_RECORD\n')
                else:
                    try:
                        self.module.run_exploration(42, 2, 16, output)
                    except Exception as error:
                        self.assertIs(type(error), self.module.ExplorationError)
                        self.assertEqual(getattr(error, 'code', None), 'EXPLORATION_STAGE_RECORD')
                    else:
                        self.fail('Malformed stage record was accepted')
            for name in ['EXPLORATION.json', 'SUMMARY_KO.md', 'SHA256SUMS.txt', 'reproducers']:
                self.assertFalse((output / name).exists(), name)
            for n in [1, 2]:
                name = f'case-{n:03d}.json'
                self.assertEqual((output / 'generated' / name).read_bytes(), (self.fixture / 'generated' / name).read_bytes())

    def modified(self, mutate):
        value = json.loads(json.dumps(self.stage))
        mutate(value)
        return canonical(value)

    def test_nonobject_root_and_missing_required_fields_reject(self):
        for value in [None, [], 'stage', 1, {}]:
            with self.subTest(value=value):
                self.reject(canonical(value))
        for field in ['cases', 'status', 'reference_steps', 'numerical_difference_count', 'reference_helper_counts', 'matched_cases']:
            with self.subTest(missing=field):
                self.reject(self.modified(lambda r, key=field: r.pop(key)))

    def test_wrong_case_and_helper_containers_reject_before_traversal(self):
        for field, value in [('cases', None), ('cases', {}), ('cases', 'cases'),
                             ('reference_helper_counts', []), ('reference_helper_counts', None)]:
            with self.subTest(field=field, value=value):
                self.reject(self.modified(lambda r, key=field, v=value: r.update({key: v})))
        for value in [None, [], 'case', {}]:
            with self.subTest(case=value):
                self.reject(self.modified(lambda r, v=value: r['cases'].__setitem__(1, v)))

    def test_unhashable_and_wrong_nullable_case_fields_reject(self):
        for field, value in [('report', []), ('status', {}), ('case_id', []), ('source_status', None),
                             ('first_difference', []), ('first_difference', {}), ('first_difference', {'field': []}), ('error_code', {}),
                             ('reference_steps', '16'), ('difference_count', False)]:
            with self.subTest(field=field, value=value):
                self.reject(self.modified(lambda r, key=field, v=value: r['cases'][1].update({key: v})))
        for field in ['report', 'status', 'case_id', 'source_status', 'first_difference', 'error_code', 'reference_steps', 'difference_count']:
            with self.subTest(missing=field):
                self.reject(self.modified(lambda r, key=field: r['cases'][1].pop(key)))
        for field, value in [('status', []), ('matched_cases', True), ('reference_steps', '32')]:
            with self.subTest(summary=field):
                self.reject(self.modified(lambda r, key=field, v=value: r.update({key: v})))

    def test_invalid_serialized_bytes_are_bounded_and_rejected(self):
        raw = canonical(self.stage)
        malformed = [b'{', b'\xff', b' ' * (1048576 + 1), raw[:-2] + b',"status":"MATCH"}\n',
                     raw[:-2] + b',"extra":NaN}\n', b'[' * 65 + b'0' + b']' * 65,
                     (json.dumps(self.stage, indent=2) + '\n').encode()]
        for number, payload in enumerate(malformed):
            with self.subTest(payload=number):
                self.reject(payload)

    def test_late_corruption_cannot_publish_partial_reproducer_subset(self):
        def change(record):
            record['cases'][0].update(status='DIFFERENT', difference_count=1, first_difference={'field': 'controlled-difference'})
            record['cases'][1] = None

        self.reject(self.modified(change))

    def test_cli_reports_specific_rejection_without_traceback(self):
        for raw in [b'{', canonical([]), canonical({}), self.modified(lambda r: r['cases'][1].update(report=[]))]:
            with self.subTest(payload=raw[:40]):
                self.reject(raw, cli=True)


if __name__ == '__main__':
    unittest.main()
