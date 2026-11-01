"""Numerically correct but contradictory auxiliary claims must fail publication."""

import copy
import importlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from native_claim_fixture import complete_claims
from test_native_coverage import observations
from v1_helpers import ROOT


class NativeClaimTests(unittest.TestCase):
    def modules(self):
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        self.assertTrue((ROOT / 'native_qualification/claims.py').is_file(), 'Missing auxiliary claim gate')
        return importlib.import_module('native_qualification.claims'), importlib.import_module('native_qualification.coverage')

    def test_complete_existing_worker_records_are_valid_without_model_import(self):
        before = set(sys.modules)
        claims, coverage = self.modules()
        for mode, count in [('R22', 5), ('R23', 4)]:
            data = complete_claims(observations(mode), mode)
            claims.validate_claims(data, mode)
            self.assertEqual(coverage.validate_coverage(data, mode), count)
        self.assertFalse(any(n.split('.')[0] in {'cyberlateral_dev', 'capnp', 'numpy'} for n in set(sys.modules) - before))

    def test_missing_root_and_row_claims_reject(self):
        claims, _ = self.modules()
        for mode in ['R22', 'R23']:
            data = complete_claims(observations(mode), mode)
            for key in ['schema_version', 'scope', 'package_version', 'model_reference_sha256', 'identity',
                        'actual_call_custody', 'forbidden_modules_loaded']:
                changed = copy.deepcopy(data)
                del changed[key]
                with self.assertRaisesRegex(ValueError, 'OBSERVATION_CLAIMS'):
                    claims.validate_claims(changed, mode)
            for key in ['oracle_parity', 'cc_sha256', 'cs_sha256']:
                changed = copy.deepcopy(data)
                del changed['cases'][0][key]
                with self.assertRaisesRegex(ValueError, 'OBSERVATION_CLAIMS'):
                    claims.validate_claims(changed, mode)

    def test_contradictory_identity_scope_reference_and_module_claims_reject(self):
        claims, _ = self.modules()
        for mode in ['R22', 'R23']:
            data = complete_claims(observations(mode), mode)
            for key, value in [('schema_version', True), ('scope', 'OTHER'), ('package_version', 'wrong'),
                               ('model_reference_sha256', 'f' * 64), ('identity', {}), ('actual_call_custody', 'QUALIFIED'),
                               ('forbidden_modules_loaded', ['numpy']), ('forbidden_modules_loaded', ())]:
                with self.assertRaisesRegex(ValueError, 'OBSERVATION_CLAIMS'):
                    claims.validate_claims({**data, key: value}, mode)

    def test_false_or_integer_oracle_and_noncanonical_hash_reject(self):
        claims, _ = self.modules()
        for mode in ['R22', 'R23']:
            for key, value in [('oracle_parity', False), ('oracle_parity', 1), ('cc_sha256', 'A' * 64),
                               ('cc_sha256', '1' * 63), ('cs_sha256', 1)]:
                data = complete_claims(observations(mode), mode)
                data['cases'][0][key] = value
                with self.assertRaisesRegex(ValueError, 'OBSERVATION_CLAIMS'):
                    claims.validate_claims(data, mode)

    def test_sequence_stamp_binding_order_and_time_claims_reject(self):
        claims, _ = self.modules()
        for key, value in [('state_binding', 'ACTUAL_HISTORY'), ('state_binding', 'EXPLICIT_FIXED_INITIAL_DATA'),
                           ('stamp', {'sequence_id': 'OTHER', 'invocation_index': 1, 'capture_id': 'entry_1'}),
                           ('stamp', {'sequence_id': 'R23_FIXED_SEQUENCE', 'invocation_index': True, 'capture_id': 'entry_1'}),
                           ('stamp', {'sequence_id': 'R23_FIXED_SEQUENCE', 'invocation_index': 1, 'capture_id': 'entry_0'})]:
            data = complete_claims(observations('R23'), 'R23')
            data['cases'][1][key] = value
            with self.assertRaisesRegex(ValueError, 'OBSERVATION_CLAIMS'):
                claims.validate_claims(data, 'R23')
        data = complete_claims(observations('R23'), 'R23')
        data['time_semantics'] = 'ACTUAL_ELAPSED_10MS'
        with self.assertRaisesRegex(ValueError, 'OBSERVATION_CLAIMS'):
            claims.validate_claims(data, 'R23')

    def test_r22_precision_custody_and_rejected_oracle_agreement_required(self):
        claims, _ = self.modules()
        for key, value in [('oracle_algorithm', 'SHARED_RUNTIME_ORACLE'), ('input_structure_only_not_F61', 1)]:
            data = complete_claims(observations('R22'), 'R22')
            data[key] = value
            with self.assertRaisesRegex(ValueError, 'OBSERVATION_CLAIMS'):
                claims.validate_claims(data, 'R22')
        for index, key, value in [(0, 'custody_claim', 'AUTHENTICATED'), (0, 'precision_claim', 'ROUNDED'),
                                   (7, 'oracle_rejection_code', 'OTHER')]:
            data = complete_claims(observations('R22'), 'R22')
            data['cases'][index][key] = value
            with self.assertRaisesRegex(ValueError, 'OBSERVATION_CLAIMS'):
                claims.validate_claims(data, 'R22')

    def test_parent_cannot_publish_identical_false_auxiliary_claims(self):
        self.modules()
        runner = importlib.import_module('native_qualification.run')
        for mode in ['R22', 'R23']:
            with tempfile.TemporaryDirectory() as scratch:
                root = Path(scratch)
                data = complete_claims(observations(mode), mode)
                data['cases'][0]['oracle_parity'] = False
                completed = subprocess.CompletedProcess([], 0, runner.canonical({'observations': data, 'receipt': {}}), b'')
                with patch.object(runner, 'verify_experiment'), patch.object(runner, 'verify_inputs'), \
                        patch.object(runner.subprocess, 'run', return_value=completed):
                    with self.assertRaisesRegex(ValueError, 'OBSERVATION_CLAIMS'):
                        runner.qualify(root / 'python', root / 'native', root / 'output', model_consumption=mode == 'R22',
                                       model_sequence=mode == 'R23', package_wheel=root / 'public')
                self.assertFalse((root / 'output').exists())


if __name__ == '__main__':
    unittest.main()
