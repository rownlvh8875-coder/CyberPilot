"""Saved schema consistency is not current CORE5 input compatibility."""

import hashlib
import importlib
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

from v1_helpers import ROOT, package_feature


def canonical(value): return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode()
def sha(raw): return hashlib.sha256(raw).hexdigest()


class CoreInputPreflightTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue((ROOT / 'integration_tools/core_sequence_input_preflight.py').is_file(), 'Missing CORE19 semantic preflight')
        package_feature()
        if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
        self.m: Any = importlib.import_module('integration_tools.core_sequence_input_preflight')
        self.reader = importlib.import_module('integration_tools.core_sequence_saved')
        self.producer = importlib.import_module('integration_tools.core_sequence_run')
        self.preparer = importlib.import_module('integration_tools.synthetic_model_input')
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup); self.root = Path(self.temp.name)
        self.folder = self.root / 'packet'; self.producer.run_sequence_case('sign-cycle', self.folder)

    def run_preflight(self, folder=None): return self.m.preflight_saved_sequence(self.folder if folder is None else folder)
    def snapshot(self): return {p.name: (p.read_bytes(), p.stat().st_mode) for p in self.folder.iterdir()}
    def edit(self, filename, change):
        path = self.folder / filename; data = json.loads(path.read_bytes()); change(data); path.write_bytes(canonical(data))
        (self.folder / 'SHA256SUMS.txt').write_bytes(''.join(sha((self.folder / n).read_bytes()) + '  ' + n + '\n' for n in ('INPUT.json', 'RESULTS.json')).encode())
    def reject_saved_label(self):
        self.edit('RESULTS.json', lambda r: r.update(status='REJECTED', sequence_completed=False, rejection_code='SEQUENCE_INPUT:2:MODEL_DRIVER',
            model_steps=0, completed_transition_count=0, rows=[], differing_transition_indices=[]))
    def semantic_reject(self, code, count=0):
        self.assertEqual(self.reader.inspect_saved_sequence(self.folder)['inspection_status'], 'SAVED_RECORDS_CONSISTENT')
        result = self.run_preflight(); self.assertEqual(result['preflight_status'], 'INPUTS_REJECTED')
        self.assertEqual(result['rejection_code'], code); self.assertEqual(result['validated_transition_count'], count)
        self.assertEqual(result['new_synthetic_model_steps'], 0); self.assertEqual(result['new_reference_steps'], 0)
        return result

    def test_three_saved_outcomes_remain_separate_from_input_compatibility(self):
        for case, saved, compatible, steps in (('sign-cycle', 'MATCH', True, 3), ('declared-difference', 'DIFFERENT', True, 3), ('late-invalid', 'REJECTED', False, 0)):
            folder = self.root / case; self.producer.run_sequence_case(case, folder); result = self.run_preflight(folder)
            self.assertEqual(result['saved_status'], saved); self.assertEqual(result['recorded_model_steps'], steps)
            self.assertEqual(result['preflight_status'], 'INPUTS_COMPATIBLE' if compatible else 'INPUTS_REJECTED')
            self.assertEqual(result['rejection_code'], None if compatible else 'SEQUENCE_INPUT:2:MODEL_DRIVER')
            self.assertEqual(result['validated_transition_count'], 3 if compatible else 2)

    def test_valid_input_with_saved_rejected_label_is_compatible(self):
        self.reject_saved_label(); result = self.run_preflight()
        self.assertEqual(result['saved_status'], 'REJECTED'); self.assertEqual(result['preflight_status'], 'INPUTS_COMPATIBLE')
        self.assertEqual(result['saved_rejection_code'], 'SEQUENCE_INPUT:2:MODEL_DRIVER'); self.assertIsNone(result['rejection_code'])

    def test_coherent_match_with_nondyadic_driver_rejects(self):
        self.edit('INPUT.json', lambda r: r['contexts'][0].update(current_driver_hex=(0.1).hex()))
        result = self.semantic_reject('SEQUENCE_INPUT:0:MODEL_DRIVER'); self.assertEqual(result['saved_status'], 'MATCH')

    def test_binary32_word_outside_native_range_rejects(self):
        self.edit('INPUT.json', lambda r: r['frames'][0]['request'].update(requested_binary32_be_hex='3f800001'))
        self.semantic_reject('SEQUENCE_INPUT:0:MODEL_LIMITER:LIMITER_REQUEST:REQUEST_WORD')

    def test_previous_request_is_quantized_not_trusted_integer_label(self):
        self.reject_saved_label(); self.edit('INPUT.json', lambda r: r['contexts'][0].update(previous_integer_request=-3))
        self.semantic_reject('SEQUENCE_INPUT:0:MODEL_PREVIOUS_REQUEST_MISMATCH')

    def test_request_and_gate_active_mismatch_rejects(self):
        self.edit('INPUT.json', lambda r: r['frames'][0]['request'].update(request_active=False))
        self.semantic_reject('SEQUENCE_INPUT:0:MODEL_ACTIVE_READS')

    def test_override_does_not_get_defaulted_away(self):
        self.edit('INPUT.json', lambda r: r['frames'][1]['request'].update(request_override=True))
        self.semantic_reject('SEQUENCE_INPUT:0:MODEL_OVERRIDE')

    def test_driver_and_angle_inclusive_bounds_are_accepted(self):
        for driver, angle in (('0x1.0000000000000p+10', '0x1.6800000000000p+7'), ('-0x1.0000000000000p+10', '-0x1.6800000000000p+7')):
            self.edit('INPUT.json', lambda r, d=driver, a=angle: r['contexts'][0].update(current_driver_hex=d, current_angle_deg_hex=a))
            self.assertEqual(self.run_preflight()['preflight_status'], 'INPUTS_COMPATIBLE')

    def test_driver_outside_bound_rejects(self):
        self.edit('INPUT.json', lambda r: r['contexts'][0].update(current_driver_hex=(1024.5).hex()))
        self.semantic_reject('SEQUENCE_INPUT:0:MODEL_DRIVER')

    def test_angle_outside_bound_rejects(self):
        self.edit('INPUT.json', lambda r: r['contexts'][0].update(current_angle_deg_hex=(180.5).hex()))
        self.semantic_reject('SEQUENCE_INPUT:0:MODEL_ANGLE')

    def test_overflow_underflow_and_noncanonical_zero_never_coerce(self):
        for text in ('0x1.0000000000000p+9999', '0x1.0000000000000p-9999', '0x0.0p+1'):
            with self.subTest(text=text):
                self.edit('INPUT.json', lambda r, t=text: r['contexts'][2].update(current_driver_hex=t))
                self.semantic_reject('INPUT_PREFLIGHT_FLOAT_ENCODING:2')

    def test_signed_zero_reaches_existing_preparer_without_normalization(self):
        self.edit('INPUT.json', lambda r: r['contexts'][0].update(current_driver_hex='-0x0.0p+0', current_angle_deg_hex='-0x0.0p+0'))
        observed = []; original = self.preparer.prepare_model_input
        def prepare(previous, current, context):
            observed.append((context.current_driver.hex(), context.current_angle_deg.hex())); return original(previous, current, context)
        with patch.object(self.m, 'prepare_model_input', side_effect=prepare): result = self.run_preflight()
        self.assertEqual(result['preflight_status'], 'INPUTS_COMPATIBLE'); self.assertEqual(observed[0], ('-0x0.0p+0', '-0x0.0p+0'))

    def test_late_invalid_pair_reports_successful_validation_prefix_only(self):
        self.edit('INPUT.json', lambda r: r['contexts'][2].update(current_angle_deg_hex=(0.1).hex()))
        result = self.semantic_reject('SEQUENCE_INPUT:2:MODEL_ANGLE', 2)
        self.assertEqual(result['declared_transition_count'], 3); self.assertNotIn('prepared', result)

    def test_time_is_ordered_int64_not_nominal_or_f61_projection(self):
        self.edit('INPUT.json', lambda r: [f['request'].update(sample_time_ns=-(1 << 63) + i) for i, f in enumerate(r['frames'])])
        self.assertEqual(self.run_preflight()['preflight_status'], 'INPUTS_COMPATIBLE')

    def test_no_model_step_or_reference_execution_during_preflight(self):
        before = self.snapshot()
        with patch.object(self.preparer.model, 'step', side_effect=AssertionError('model executed')), patch('os.write', side_effect=AssertionError('API write')):
            result = self.run_preflight()
        self.assertEqual(result['new_synthetic_model_steps'], 0); self.assertEqual(result['new_reference_steps'], 0)
        self.assertEqual(result['numeric_validation_work'], 'NONZERO_NOT_AGGREGATED'); self.assertEqual(before, self.snapshot())

    def test_each_regular_file_captured_once_readonly(self):
        original = os.open; paths = {}; opened = []
        def observe(path, flags, *a, **kw):
            self.assertFalse(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC))
            target = paths[kw['dir_fd']] / path if kw.get('dir_fd') in paths else Path(path).absolute()
            fd = original(path, flags, *a, **kw); paths[fd] = target
            if stat.S_ISREG(os.fstat(fd).st_mode): opened.append(target.name)
            return fd
        with patch('os.open', side_effect=observe): result = self.run_preflight()
        self.assertEqual(sorted(opened), ['INPUT.json', 'RESULTS.json', 'SHA256SUMS.txt'])
        self.assertEqual(result['captured_sha256'], {p.name: sha(p.read_bytes()) for p in self.folder.iterdir()})

    def test_checksum_failure_has_no_semantic_receipt(self):
        (self.folder / 'SHA256SUMS.txt').write_bytes(b'wrong')
        with self.assertRaises(self.m.InputPreflightError) as found: self.run_preflight()
        self.assertEqual(found.exception.code, 'INPUT_PREFLIGHT_SAVED:INSPECT_CHECKSUM')

    def test_bad_json_is_fixed_saved_error_not_numeric_rejection(self):
        (self.folder / 'INPUT.json').write_bytes(b'{}\n')
        self.edit('RESULTS.json', lambda r: None)
        with self.assertRaises(self.m.InputPreflightError) as found: self.run_preflight()
        self.assertEqual(found.exception.code, 'INPUT_PREFLIGHT_SAVED:INSPECT_RECORD')

    def test_missing_and_symlink_input_paths_reject(self):
        alias = self.root / 'alias'; alias.symlink_to(self.folder, target_is_directory=True)
        for path in (self.root / 'missing', alias):
            with self.subTest(path=path), self.assertRaises(self.m.InputPreflightError) as found: self.run_preflight(path)
            self.assertEqual(found.exception.code, 'INPUT_PREFLIGHT_SAVED:INSPECT_INPUT_FILE')

    def test_oversized_input_rejects_before_semantic_validation(self):
        (self.folder / 'INPUT.json').write_bytes(b' ' * 65537)
        with patch.object(self.m, 'prepare_model_input', side_effect=AssertionError('semantic access')), self.assertRaises(self.m.InputPreflightError) as found:
            self.run_preflight()
        self.assertEqual(found.exception.code, 'INPUT_PREFLIGHT_SAVED:INSPECT_SIZE')

    def test_readonly_input_bytes_modes_and_layout_are_preserved(self):
        for p in self.folder.iterdir(): p.chmod(0o444)
        self.folder.chmod(0o555); before = self.snapshot()
        result = self.run_preflight(); self.assertEqual(result['preflight_status'], 'INPUTS_COMPATIBLE')
        self.assertEqual(before, self.snapshot())

    def test_repeated_receipts_are_canonical_and_deterministic(self):
        one = canonical(self.run_preflight()); two = canonical(self.run_preflight())
        self.assertEqual(one, two); self.assertEqual(json.loads(one)['contract_id'], 'CORE19_SAVED_SYNTHETIC_INPUT_PREFLIGHT_V1')

    def test_no_prepared_f61_args_or_authority_are_exposed(self):
        result = self.run_preflight()
        for field in ('source_identity_reauthenticated', 'arithmetic_recomputed', 'prehistory_checked', 'v4_payload_allowed', 'f61_input_allowed', 'actual_activation_allowed'):
            self.assertIs(result[field], False)
        self.assertFalse(set(result) & {'prepared', 'model_input', 'model_state', 'f61_input', 'rate_budget_per_s'})
        self.assertEqual(result['gates']['R_BUDGET'], 'UNRESOLVED'); self.assertEqual(result['gates']['STATIC_EVIDENCE_GATE'], 'FAIL')

    def test_unexpected_preparer_failure_propagates(self):
        with patch.object(self.m, 'prepare_model_input', side_effect=RuntimeError('internal failure')), self.assertRaisesRegex(RuntimeError, '^internal failure$'):
            self.run_preflight()

    def test_saved_error_precedes_numeric_preparation(self):
        (self.folder / 'SHA256SUMS.txt').write_bytes(b'wrong')
        with patch.object(self.m, 'prepare_model_input', side_effect=AssertionError('semantic access')), self.assertRaises(self.m.InputPreflightError) as found:
            self.run_preflight()
        self.assertEqual(found.exception.code, 'INPUT_PREFLIGHT_SAVED:INSPECT_CHECKSUM')

    def test_returned_gate_mutation_does_not_change_later_receipts(self):
        result = self.run_preflight(); result['gates']['R_BUDGET'] = 'FORGED'; result['captured_sha256'].clear()
        next_result = self.run_preflight(); self.assertEqual(next_result['gates']['R_BUDGET'], 'UNRESOLVED')
        self.assertEqual(len(next_result['captured_sha256']), 3)

    def test_subprocess_blocks_producers_references_and_f61(self):
        script = '''import importlib.abc,json,sys
class Block(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  modules=('integration_tools.core_sequence_run','integration_tools.synthetic_sequence_check','integration_tools.synthetic_transition_check','integration_tools.sequence_reference','integration_tools.fixed_model_reference','numpy','openpilot','opendbc')
  if any(fullname==n or fullname.startswith(n+'.') for n in modules) or fullname.startswith(('integration_tools.f61_','integration_tools.scenario_run')):
   raise AssertionError('forbidden import:'+fullname)
sys.meta_path.insert(0,Block()); sys.path.insert(0,sys.argv[1]); sys.path.insert(0,sys.argv[1]+'/src')
from pathlib import Path
from integration_tools.core_sequence_input_preflight import preflight_saved_sequence
from integration_tools.scenario_output import canonical
print(canonical(preflight_saved_sequence(Path(sys.argv[2]))).decode(),end='')
'''
        result = subprocess.run([sys.executable, '-I', '-B', '-c', script, str(ROOT), str(self.folder)], capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr); self.assertEqual(result.stdout, canonical(self.run_preflight()))

    def test_invalid_hex_grammar_is_not_silently_repaired(self):
        self.edit('INPUT.json', lambda r: r['contexts'][0].update(current_driver_hex='not-a-number'))
        with self.assertRaises(self.m.InputPreflightError) as found: self.run_preflight()
        self.assertEqual(found.exception.code, 'INPUT_PREFLIGHT_SAVED:INSPECT_RECORD')

    def test_historical_identity_labels_are_not_reauthenticated(self):
        self.edit('RESULTS.json', lambda r: r['identity'].update(demo_cli_sha256='0' * 64, historical_marker=None))
        result = self.run_preflight(); self.assertEqual(result['preflight_status'], 'INPUTS_COMPATIBLE')
        self.assertFalse(result['source_identity_reauthenticated'])

    def test_recorded_rejection_code_does_not_replace_current_validation(self):
        self.reject_saved_label(); self.edit('RESULTS.json', lambda r: r.update(rejection_code='SEQUENCE_INPUT:2:MODEL_ANGLE'))
        self.edit('INPUT.json', lambda r: r['contexts'][2].update(current_driver_hex=(0.1).hex()))
        result = self.semantic_reject('SEQUENCE_INPUT:2:MODEL_DRIVER', 2)
        self.assertEqual(result['saved_rejection_code'], 'SEQUENCE_INPUT:2:MODEL_ANGLE')

    def test_invalid_model_order_is_rejected_by_saved_schema_first(self):
        self.reject_saved_label(); self.edit('INPUT.json', lambda r: r['contexts'][1].update(model_index=9))
        with patch.object(self.m, 'prepare_model_input', side_effect=AssertionError('semantic access')), self.assertRaises(self.m.InputPreflightError) as found:
            self.run_preflight()
        self.assertEqual(found.exception.code, 'INPUT_PREFLIGHT_SAVED:INSPECT_RECORD')
