"""Synthetic F56 fidelity/admission tests; no private driving data or Controller."""
import copy
from dataclasses import replace
import hashlib
import importlib
import importlib.util
import io
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from tools.cyberpilot import rlog_observer_regression_v1 as recorded

NAME = 'tools.cyberpilot.recorded_command_invariant_gate_v1'
BINDING = 'a' * 64
CANARY = 'F56_SYNTHETIC_PRIVATE_CANARY'
SPEC = importlib.util.find_spec(NAME)
gate = importlib.import_module(NAME) if SPEC is not None else None


def command(ordinal, timestamp, torque, active=True, valid=True):
  return recorded.Record(ordinal, 'carControl', timestamp, valid, (
    ('actuators.torque', torque), ('actuators.steeringAngleDeg', 0.0),
    ('actuators.curvature', 0.0), ('currentCurvature', 0.0),
    ('latActive', active), ('enabled', True), ('longActive', False)), BINDING)


def changed(record, key, value):
  return replace(record, values=tuple((k, value if k == key else v) for k, v in record.values))


class InvariantTests(unittest.TestCase):
  def setUp(self):
    self.assertIsNotNone(gate, 'F56_IMPLEMENTATION_MISSING')
    self.records = (command(10, 1_000_000_000, 0.1),
                    command(20, 1_010_000_000, 0.2), command(30, 1_020_000_000, 0.3))
    self.rows = tuple(gate.Qualification(x.ordinal, x.timestamp_ns, 'SOURCE_SCHEMA_UNQUALIFIED', BINDING)
                      for x in self.records)

  def evaluate(self, observed=None, rows=None):
    return gate.evaluate(self.records, self.records if observed is None else observed,
                         self.rows if rows is None else rows, binding=BINDING)

  def test_identical_commands_pass_fidelity_and_block_all_controller_execution(self):
    result = self.evaluate()
    self.assertEqual(result['command_count'], 3)
    self.assertEqual(result['primary_counts'], {'SOURCE_SCHEMA_UNQUALIFIED': 3})
    self.assertEqual(result['admission']['blocked_commands'], 3)
    self.assertFalse(result['admission']['controller_execution_supported'])
    self.assertEqual(result['admission']['controller_invocations'], 0)
    self.assertIsNone(result['admission']['candidate_output'])
    self.assertEqual(result['admission']['status'], 'BLOCKED')
    self.assertEqual(result['data_origin'], 'UNATTESTED_PURE_INPUT')

  def test_forged_recorded_candidate_does_not_grant_controller_authority(self):
    rows = tuple(replace(x, primary_status='RECORDED_INPUT_CANDIDATE') for x in self.rows)
    result = self.evaluate(rows=rows)
    self.assertEqual(result['admission']['blocked_commands'], 3)
    self.assertFalse(result['runtime_authorized'])

  def test_6000_unqualified_commands_remain_6000_not_a_qualified_subset(self):
    records = tuple(command(i, 1_000_000_000 + i * 10_000_000, 0.0) for i in range(6000))
    rows = tuple(gate.Qualification(x.ordinal, x.timestamp_ns, 'SOURCE_SCHEMA_UNQUALIFIED', BINDING)
                 for x in records)
    result = gate.evaluate(records, records, rows, binding=BINDING)
    self.assertEqual(result['primary_counts']['SOURCE_SCHEMA_UNQUALIFIED'], 6000)
    self.assertEqual(result['admission']['blocked_commands'], 6000)

  def test_changed_command_is_rejected_instead_of_overwriting_baseline(self):
    original = recorded.tape_bytes(self.records)
    with self.assertRaisesRegex(ValueError, 'COMMAND_FIDELITY_MISMATCH'):
      self.evaluate((self.records[0], changed(self.records[1], 'actuators.torque', 0.25), self.records[2]))
    self.assertEqual(recorded.tape_bytes(self.records), original)

  def test_negative_zero_change_is_not_hidden_by_numeric_equality(self):
    records = (command(1, 100, -0.0),)
    rows = (gate.Qualification(1, 100, 'SOURCE_SCHEMA_UNQUALIFIED', BINDING),)
    with self.assertRaisesRegex(ValueError, 'COMMAND_FIDELITY_MISMATCH'):
      gate.evaluate(records, (command(1, 100, 0.0),), rows, binding=BINDING)

  def test_missing_duplicate_or_extra_command_is_rejected(self):
    for records in (self.records[:-1], (*self.records, self.records[-1]), ()):
      with self.subTest(count=len(records)), self.assertRaises(ValueError):
        self.evaluate(records)

  def test_original_wire_order_is_not_sorted_to_conceal_reversal(self):
    with self.assertRaises(ValueError):
      self.evaluate((self.records[1], self.records[0], self.records[2]))

  def test_duplicate_or_reversed_command_timestamp_is_rejected(self):
    for timestamp in (self.records[0].timestamp_ns, self.records[0].timestamp_ns - 1):
      with self.subTest(timestamp=timestamp), self.assertRaises(ValueError):
        self.evaluate((self.records[0], replace(self.records[1], timestamp_ns=timestamp), self.records[2]))

  def test_wrong_binding_or_service_is_rejected(self):
    for record in (replace(self.records[0], binding='b' * 64), replace(self.records[0], service='carOutput')):
      with self.subTest(service=record.service), self.assertRaises(ValueError):
        self.evaluate((record, *self.records[1:]))

  def test_nan_infinity_or_non_numeric_command_is_rejected(self):
    for value in (float('nan'), float('inf'), -float('inf'), True, 'secret'):
      with self.subTest(type=type(value).__name__), self.assertRaises(ValueError):
        self.evaluate((changed(self.records[0], 'actuators.torque', value), *self.records[1:]))

  def test_unknown_or_missing_field_is_rejected_before_statistics(self):
    for values in (self.records[0].values[:-1], (*self.records[0].values, ('GPS', 1.0))):
      with self.subTest(size=len(values)), self.assertRaises(ValueError):
        self.evaluate((replace(self.records[0], values=values), *self.records[1:]))

  def test_invalid_flag_type_is_not_coerced_to_bool(self):
    with self.assertRaises(ValueError):
      self.evaluate((changed(self.records[0], 'latActive', 1), *self.records[1:]))

  def test_qualification_missing_duplicate_or_future_mapping_is_rejected(self):
    variants = (self.rows[:-1], (self.rows[0], self.rows[0], self.rows[2]),
                (replace(self.rows[0], timestamp_ns=self.rows[0].timestamp_ns + 1), *self.rows[1:]),
                (replace(self.rows[0], binding='b' * 64), *self.rows[1:]))
    for rows in variants:
      with self.subTest(size=len(rows)), self.assertRaises(ValueError):
        self.evaluate(rows=rows)

  def test_unknown_status_cannot_be_promoted_to_pass(self):
    with self.assertRaises(ValueError):
      self.evaluate(rows=(replace(self.rows[0], primary_status='QUALIFIED'), *self.rows[1:]))

  def test_invalid_record_is_preserved_but_has_no_rate_continuation(self):
    records = (self.records[0], replace(self.records[1], valid=False), self.records[2])
    result = gate.evaluate(records, records, self.rows, binding=BINDING)
    self.assertEqual(result['invalid_commands'], 1)
    self.assertEqual(result['rate']['observed_pairs'], 0)

  def test_rate_is_observed_difference_not_a_physical_or_deadline_claim(self):
    result = self.evaluate()
    self.assertEqual(result['rate']['observed_pairs'], 2)
    self.assertAlmostEqual(result['rate']['rms_per_s'], 10.0)
    self.assertIsNone(result['rate']['first_rate'])
    self.assertEqual(result['rate']['reset_gap_qualification'], 'UNKNOWN')
    self.assertEqual(result['limit_qualification'], 'UNQUALIFIED')
    self.assertFalse(result['target_deadline_qualified'])

  def test_active_transition_is_not_a_continuous_rate_pair(self):
    records = (self.records[0], changed(self.records[1], 'latActive', False),
               changed(self.records[2], 'latActive', False))
    result = gate.evaluate(records, records, self.rows, binding=BINDING)
    self.assertEqual(result['rate']['observed_pairs'], 1)
    self.assertEqual(result['lateral_inactive_commands'], 2)

  def test_no_implicit_unit_rescaling_or_assumed_negative_command_limit(self):
    records = (command(1, 100, -12.0),)
    rows = (gate.Qualification(1, 100, 'SOURCE_SCHEMA_UNQUALIFIED', BINDING),)
    result = gate.evaluate(records, records, rows, binding=BINDING)
    self.assertEqual(result['command_count'], 1)
    self.assertEqual(result['limit_qualification'], 'UNQUALIFIED')

  def test_inputs_and_canonical_output_are_immutable_and_deterministic(self):
    before = copy.deepcopy(self.rows)
    a = gate.canonical(self.evaluate())
    b = gate.canonical(self.evaluate())
    self.assertEqual(a, b)
    self.assertEqual(self.rows, before)
    self.assertNotIn(CANARY.encode(), a)

  def test_no_controller_process_transport_or_schema_import(self):
    with patch.object(subprocess, 'Popen', side_effect=AssertionError('PROCESS_FORBIDDEN')), \
         patch.object(socket, 'socket', side_effect=AssertionError('TRANSPORT_FORBIDDEN')):
      result = self.evaluate()
    self.assertEqual(result['admission']['controller_invocations'], 0)
    self.assertIsNone(result['admission']['candidate_output'])


class BoundaryTests(unittest.TestCase):
  def setUp(self):
    self.assertIsNotNone(gate, 'F56_IMPLEMENTATION_MISSING')

  def test_unknown_loaded_module_location_fails_closed(self):
    with patch.object(recorded, '__file__', None):
      try:
        gate.modules()
      except Exception as error:
        self.assertIsInstance(error, ValueError)
        self.assertEqual(error.args[0], 'SOURCE_IDENTITY_MISMATCH')
      else:
        self.fail('UNQUALIFIED_MODULE_LOCATION_ACCEPTED')

  def test_output_inside_historical_input_is_rejected_before_any_read(self):
    with tempfile.TemporaryDirectory() as tmp:
      try:
        gate.run_private(tmp, tmp, Path(tmp) / 'new-output')
      except Exception as error:
        self.assertIsInstance(error, ValueError)
        self.assertEqual(error.args[0], 'OVERLAPPING_OUTPUT')
      else:
        self.fail('HISTORICAL_INPUT_OUTPUT_OVERLAP_ACCEPTED')
      self.assertFalse((Path(tmp) / 'new-output').exists())

  def test_pinned_private_artifact_read_and_hash_mismatch(self):
    with tempfile.TemporaryDirectory() as tmp:
      directory = gate.modules()[2].SecureDirectory.existing(tmp)
      try:
        directory.write('fixture.json', b'{}')
        self.assertEqual(gate.read_artifact(directory, 'fixture.json',
                         hashlib.sha256(b'{}').hexdigest(), 2), b'{}')
        with self.assertRaises(ValueError):
          gate.read_artifact(directory, 'fixture.json', '0' * 64, 2)
      finally:
        directory.close()

  def test_symlink_or_unsafe_artifact_name_is_rejected(self):
    with tempfile.TemporaryDirectory() as tmp:
      root = Path(tmp)
      (root / 'target').write_bytes(b'{}')
      os.chmod(root / 'target', 0o600)
      (root / 'link').symlink_to(root / 'target')
      directory = gate.modules()[2].SecureDirectory.existing(root)
      try:
        for name in ('link', '../target', '/target'):
          with self.subTest(name=name), self.assertRaises((ValueError, OSError)):
            gate.read_artifact(directory, name, hashlib.sha256(b'{}').hexdigest(), 2)
      finally:
        directory.close()

  def test_cli_argument_and_private_path_canary_are_not_printed(self):
    for args in (['--unknown', CANARY], ['--f46-results', '/tmp/' + CANARY, '--f47-results', '/missing',
                                         '--output', '/tmp/f56-output']):
      out, err = io.StringIO(), io.StringIO()
      with patch('sys.stdout', out), patch('sys.stderr', err):
        code = gate.main(args)
      self.assertNotEqual(code, 0)
      self.assertNotIn(CANARY, out.getvalue() + err.getvalue())
      self.assertNotIn('Traceback', out.getvalue() + err.getvalue())

  def test_nested_exception_does_not_cross_cli_boundary(self):
    out, err = io.StringIO(), io.StringIO()
    with patch.object(gate, 'run_private', side_effect=RuntimeError(CANARY)), \
         patch('sys.stdout', out), patch('sys.stderr', err):
      code = gate.main(['--f46-results', '/tmp/a', '--f47-results', '/tmp/b', '--output', '/tmp/c'])
    self.assertNotEqual(code, 0)
    self.assertNotIn(CANARY, out.getvalue() + err.getvalue())

  def test_existing_or_symlink_output_is_not_changed(self):
    with tempfile.TemporaryDirectory() as tmp:
      p = Path(tmp)
      (p / 'existing').mkdir(mode=0o700)
      (p / 'link').symlink_to(p / 'existing')
      sec = gate.modules()[2]
      for target in (p / 'existing', p / 'link'):
        with self.subTest(name=target.name), self.assertRaises((ValueError, OSError)):
          sec.SecureDirectory.create(target)
      self.assertEqual(list((p / 'existing').iterdir()), [])


if __name__ == '__main__':
  unittest.main()
