"""R41 must not accept wrong preregistered metadata beside a correct saved run."""

import importlib
import json
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

import test_boundary_regression_pack as pack
from v1_helpers import ROOT, package_feature

FILENAME = 'long_fault_cycles_v1.json'


class BoundaryRegressionMetadataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(pack.EXPECTED.read_bytes())
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        package_feature()
        source = importlib.import_module('integration_tools.scenario_input')
        engine = importlib.import_module('integration_tools.scenario_engine')
        cls.record = engine.evaluate_scenario(source.read_scenario(pack.PACK / FILENAME))

    def reject(self, changes=None, missing=None):
        contract = deepcopy(self.contract)
        metadata = contract['cases'][FILENAME]
        if changes:
            metadata.update(changes)
        if missing:
            del metadata[missing]
        with tempfile.TemporaryDirectory(prefix='r41-metadata-test-') as tmp:
            path = Path(tmp) / 'mutated-reference.json'
            path.write_text(json.dumps(contract), encoding='utf-8')
            # Only select an external input file. Actual JSON loading and the
            # consumer assertions run unchanged; the real registered file is safe.
            with patch.object(pack, 'EXPECTED', path):
                with self.assertRaises(AssertionError):
                    pack.assert_saved_case(self, FILENAME, self.record)

    def test_wrong_period_cannot_hide_behind_hardcoded91(self):
        self.reject({'fault_period': 2})

    def test_wrong_cycle_count_is_not_ignored(self):
        self.reject({'complete_cycles': 99})

    def test_wrong_tail_count_is_not_ignored(self):
        self.reject({'tail_samples': 99})

    def test_wrong_suppressed_offsets_are_not_ignored(self):
        for offsets in [[], [89, 90, 180], [90, 89, 180, 181], [89, 90, 180, 181, 181]]:
            with self.subTest(offsets=offsets):
                self.reject({'suppressed_offsets': offsets})

    def test_equal_numeric_values_with_wrong_json_types_are_rejected(self):
        for field, value in [('sample_count', 184.0), ('fault_period', 91.0),
                             ('complete_cycles', 2.0), ('tail_samples', 2.0),
                             ('suppressed_offsets', [89.0, 90, 180, 181]), ('complete_cycles', True)]:
            with self.subTest(field=field, value=value):
                self.reject({field: value})

    def test_missing_previously_ignored_fields_have_no_fallback(self):
        for field in ['complete_cycles', 'tail_samples', 'suppressed_offsets']:
            with self.subTest(field=field):
                self.reject(missing=field)
