"""Synthetic-only tests for private recorded-command validation; no driving logs."""
import dataclasses
import hashlib
import inspect
import io
from contextlib import redirect_stdout
from unittest.mock import patch
import importlib
import importlib.util
import json
from pathlib import Path
import tempfile
import subprocess
import sys
import unittest


MODULE = 'tools.cyberpilot.rlog_observer_regression_v1'
BINDING = 'a' * 64


class TestRecordedCommandObserver(unittest.TestCase):
  def setUp(self):
    if importlib.util.find_spec(MODULE) is None:
      raise AssertionError('F46 replay/observer implementation is missing')
    self.api = importlib.import_module(MODULE)

  def command(self, ordinal=1, timestamp=100, torque=0.25, active=True, valid=True, binding=BINDING):
    return self.api.Record(ordinal, 'carControl', timestamp, valid, (
      ('actuators.torque', torque), ('actuators.steeringAngleDeg', 1.),
      ('actuators.curvature', .02), ('currentCurvature', .01),
      ('latActive', active), ('enabled', False), ('longActive', False),
    ), binding)

  def observe(self, records, **kwargs):
    return self.api.observe(tuple(records), BINDING, {'carControl': len(records)}, **kwargs)

  def test_signed_recorded_commands_and_file_order_are_preserved(self):
    records = (self.command(2, 100, -.25), self.command(8, 130, .5))
    before = self.api.tape_bytes(records)
    result = self.observe(records)
    self.assertEqual(before, self.api.tape_bytes(records))
    rows = [json.loads(line) for line in before.splitlines()]
    self.assertEqual([r['ordinal'] for r in rows], [2, 8])
    self.assertEqual([r['values']['actuators.torque'] for r in rows], [-.25, .5])
    self.assertEqual(result['command_count'], 2)
    self.assertEqual(result['valid_command_count'], 2)
    self.assertEqual(result['rate_summary']['count'], 1)
    self.assertAlmostEqual(result['rate_summary']['rms_per_s'], 25000000.)

  def test_record_is_immutable(self):
    with self.assertRaises(dataclasses.FrozenInstanceError):
      self.command().timestamp_ns = 0

  def test_timestamp_reversal_is_reported_without_sorting(self):
    records = (self.command(1, 100), self.command(2, 90))
    result = self.observe(records)
    self.assertEqual(result['diagnostics']['TIMESTAMP_REVERSAL'], 1)
    self.assertEqual(result['invalid_command_count'], 1)
    self.assertEqual([json.loads(x)['timestamp_ns'] for x in self.api.tape_bytes(records).splitlines()], [100, 90])

  def test_duplicate_message_invalidates_current_rate(self):
    result = self.observe((self.command(1, 100), self.command(2, 100)))
    self.assertEqual(result['diagnostics']['DUPLICATE_MESSAGE'], 1)
    self.assertEqual(result['rate_summary']['count'], 0)

  def test_missing_expected_message_is_not_hidden(self):
    result = self.api.observe((self.command(),), BINDING, {'carControl': 2})
    self.assertEqual(result['diagnostics']['MISSING_INPUT'], 1)
    self.assertFalse(result['expected_counts_match'])

  def test_missing_field_is_not_defaulted_to_zero(self):
    record = dataclasses.replace(self.command(), values=(('latActive', True),))
    result = self.observe((record,))
    self.assertEqual(result['diagnostics']['MISSING_INPUT'], 1)
    self.assertEqual(result['valid_command_count'], 0)

  def test_invalid_event_is_not_valid_command(self):
    result = self.observe((self.command(valid=False),))
    self.assertEqual(result['diagnostics']['INVALID_INPUT'], 1)
    self.assertEqual(result['valid_command_count'], 0)

  def test_nan_and_infinity_are_diagnosed_without_invented_values(self):
    for value in (float('nan'), float('inf'), -float('inf')):
      with self.subTest(value=str(value)):
        record = self.command(torque=value)
        result = self.observe((record,))
        self.assertEqual(result['diagnostics']['NONFINITE_VALUE'], 1)
        self.assertEqual(result['valid_command_count'], 0)
        encoded = json.loads(self.api.tape_bytes((record,)))
        self.assertIsInstance(encoded['values']['actuators.torque'], dict)

  def test_rate_overflow_is_rejected(self):
    result = self.observe((self.command(1, 1, -1e308), self.command(2, 2, 1e308)))
    self.assertEqual(result['diagnostics']['NONFINITE_RATE'], 1)
    self.assertEqual(result['rate_summary']['count'], 0)

  def test_first_sample_has_no_fabricated_history(self):
    self.assertEqual(self.observe((self.command(),))['rate_summary']['count'], 0)

  def test_inactive_does_not_zero_or_delete_recorded_command(self):
    record = self.command(torque=.25, active=False)
    result = self.observe((record,))
    self.assertEqual(result['state_counts']['lateral_inactive'], 1)
    self.assertEqual(json.loads(self.api.tape_bytes((record,)))['values']['actuators.torque'], .25)

  def test_driver_override_is_a_separate_recorded_fact(self):
    state = self.api.Record(1, 'carState', 95, True, (
      ('vEgo', 2.), ('steeringAngleDeg', 1.), ('steeringPressed', True), ('canValid', True),
    ), BINDING)
    result = self.api.observe((state, self.command(2, 100)), BINDING, {'carState': 1, 'carControl': 1})
    self.assertEqual(result['state_counts']['driver_override'], 1)
    self.assertEqual(result['state_counts']['lateral_active'], 1)
    self.assertEqual(result['input_binding'], 'INPUT_BINDING_UNQUALIFIED')

  def test_source_binding_exchange_is_blocked(self):
    with self.assertRaisesRegex(ValueError, 'INCORRECT_SOURCE_BINDING'):
      self.observe((self.command(binding='b' * 64),))

  def test_cross_segment_record_is_blocked(self):
    with self.assertRaisesRegex(ValueError, 'INCORRECT_SOURCE_BINDING'):
      self.observe((self.command(), self.command(2, 110, binding='c' * 64)))

  def test_source_identity_is_not_replaced_by_current_head(self):
    with self.assertRaisesRegex(ValueError, 'INCORRECT_SOURCE_IDENTITY'):
      self.api.validate_metadata('df8fc8b9d4094f03d8a426039bbe2d3c7b82759c', self.api.RAW_SHA)

  def test_undeclared_staleness_is_unqualified(self):
    self.assertEqual(self.api.assess_age(10, 100), 'UNQUALIFIED')
    self.assertEqual(self.observe((self.command(),))['staleness_qualification'], 'UNQUALIFIED')

  def test_declared_synthetic_message_age_is_stale(self):
    self.assertEqual(self.api.assess_age(10, 100, max_age_ns=20), 'STALE_INPUT')
    self.assertEqual(self.api.assess_age(90, 100, max_age_ns=20), 'WITHIN_DECLARED_AGE')

  def test_future_input_is_never_bound_as_prior(self):
    self.assertEqual(self.api.assess_age(110, 100, max_age_ns=20), 'INPUT_BINDING_UNQUALIFIED')

  def test_physical_freshness_and_controller_state_are_not_qualified(self):
    result = self.observe((self.command(),))
    self.assertEqual(result['freshness_qualification'], 'UNQUALIFIED')
    self.assertEqual(result['controller_state'], 'F46_INSUFFICIENT_RECORDED_STATE')
    self.assertIsNone(result['candidate_output'])
    self.assertEqual(result['diagnostics']['INCOMPLETE_CONTROLLER_STATE'], 1)

  def test_original_ordinal_reversal_is_blocked(self):
    with self.assertRaisesRegex(ValueError, 'WIRE_ORDER_MISMATCH'):
      self.observe((self.command(2, 100), self.command(1, 110)))

  def test_private_fields_cannot_enter_tape(self):
    bad = dataclasses.replace(self.command(), values=(*self.command().values, ('vin', 'synthetic-secret')))
    with self.assertRaisesRegex(ValueError, 'PRIVACY_VIOLATION'):
      self.api.tape_bytes((bad,))

  def test_non_allowlisted_service_is_blocked(self):
    bad = dataclasses.replace(self.command(), service='gpsLocationExternal')
    with self.assertRaisesRegex(ValueError, 'PRIVACY_VIOLATION'):
      self.api.tape_bytes((bad,))

  def test_private_output_is_outside_repository(self):
    with self.assertRaisesRegex(ValueError, 'UNSAFE_OUTPUT'):
      self.api.validate_output(Path(__file__).resolve().parents[1] / 'generated')
    with self.assertRaisesRegex(ValueError, 'UNSAFE_OUTPUT'):
      self.api.validate_output(Path('/mnt/c/OneDrive/generated'))

  def test_canonical_results_are_deterministic(self):
    records = (self.command(1, 100, -.25), self.command(2, 130, .5))
    self.assertEqual(self.api.canonical(self.observe(records)), self.api.canonical(self.observe(records)))

  def test_verified_reader_rejects_missing_and_wrong_hash(self):
    with tempfile.TemporaryDirectory() as folder:
      path = Path(folder) / 'synthetic.bin'
      with self.assertRaisesRegex(ValueError, 'FILE_UNAVAILABLE'):
        self.api.read_verified(path, '0' * 64, 1)
      path.write_bytes(b'x')
      with self.assertRaisesRegex(ValueError, 'FILE_IDENTITY_MISMATCH'):
        self.api.read_verified(path, '0' * 64, 1)
      self.assertEqual(self.api.read_verified(path, hashlib.sha256(b'x').hexdigest(), 1), b'x')

  def test_reader_rejects_symlink(self):
    with tempfile.TemporaryDirectory() as folder:
      path = Path(folder) / 'data'
      path.write_bytes(b'x')
      link = Path(folder) / 'link'
      link.symlink_to(path)
      with self.assertRaisesRegex(ValueError, 'FILE_UNAVAILABLE'):
        self.api.read_verified(link, hashlib.sha256(b'x').hexdigest(), 1)

  def test_wrong_schema_manifest_is_rejected(self):
    with tempfile.TemporaryDirectory() as folder:
      path = Path(folder) / 'manifest.json'
      path.write_text('{}')
      with self.assertRaisesRegex(ValueError, 'SCHEMA_MANIFEST_MISMATCH'):
        self.api.verify_source(Path(folder), path)

  def test_truncated_compression_is_blocked(self):
    import zstandard
    data = zstandard.ZstdCompressor().compress(b'synthetic')
    with self.assertRaisesRegex(ValueError, 'TRUNCATED_ZSTD'):
      self.api.decompress(data[:-2])
    self.assertEqual(self.api.decompress(data), b'synthetic')

  def test_truncated_message_table_is_blocked(self):
    with self.assertRaisesRegex(ValueError, 'TRUNCATED_CAPNP'):
      list(self.api.message_slices(b'abc'))

  def test_observer_has_no_actuator_result(self):
    result = self.observe((self.command(),))
    self.assertEqual(result['vehicle_authority'], 'NONE')
    self.assertFalse(result['runtime_authorized'])
    self.assertIsNone(result['selected_candidate'])
    self.assertIsNone(result['selected_policy'])


  def test_existing_output_is_never_modified_on_cli_failure(self):
    with tempfile.TemporaryDirectory() as folder:
      output = Path(folder) / 'previous'
      output.mkdir(mode=0o700)
      (output / 'keep.txt').write_text('preserve')
      process = subprocess.run([sys.executable, '-B', self.api.__file__, '--raw', folder + '/missing',
                                '--source-root', folder, '--source-manifest', folder + '/missing',
                                '--output', str(output)], capture_output=True, text=True, check=False)
      self.assertNotEqual(process.returncode, 0)
      self.assertEqual(sorted(p.name for p in output.iterdir()), ['keep.txt'])

  def test_cli_reports_exact_reader_binding_failure(self):
    with tempfile.TemporaryDirectory() as folder:
      process = subprocess.run([sys.executable, '-B', self.api.__file__, '--raw', folder + '/missing',
                                '--source-root', folder, '--source-manifest', folder + '/missing',
                                '--output', folder + '/new'], capture_output=True, text=True, check=False)
      self.assertEqual(process.returncode, 2)
      self.assertIn('FILE_UNAVAILABLE', process.stdout)
      self.assertNotIn(folder, process.stdout)

  def test_mutable_record_values_are_rejected(self):
    record = dataclasses.replace(self.command(), values=list(self.command().values))
    with self.assertRaisesRegex(ValueError, 'PRIVACY_VIOLATION'):
      self.api.tape_bytes((record,))


  def test_archive_time_error_is_distinct_from_per_service_reversal(self):
    result = self.observe((self.command(1, 100), self.command(2, 90)))
    self.assertEqual(result['diagnostics'].get('ARCHIVE_TIMESTAMP_REVERSAL'), 1)
    self.assertEqual(result['archive_cross_service_timestamp_reversals'], 0)

  def test_observer_reports_declared_message_staleness(self):
    model = self.api.Record(1, 'modelV2', 10, True, (
      ('frameId', 1), ('frameIdExtra', 1), ('timestampEof', 5),
    ), BINDING)
    self.assertIn('age_contract', inspect.signature(self.api.observe).parameters)
    result = self.api.observe((model, self.command(2, 100)), BINDING,
                              {'modelV2': 1, 'carControl': 1},
                              age_contract={'max_age_ns': 20, 'provenance': 'synthetic-common-clock'})
    self.assertEqual(result['diagnostics']['STALE_INPUT'], 1)
    self.assertEqual(result['freshness_qualification'], 'UNQUALIFIED')

  def test_observer_does_not_bind_a_prior_archived_future_timestamp(self):
    model = self.api.Record(1, 'modelV2', 110, True, (
      ('frameId', 1), ('frameIdExtra', 1), ('timestampEof', 5),
    ), BINDING)
    result = self.api.observe((model, self.command(2, 100)), BINDING, {'modelV2': 1, 'carControl': 1})
    self.assertEqual(result['diagnostics'].get('FUTURE_INPUT_REJECTED'), 1)

  def test_reversal_does_not_start_new_valid_history_before_high_water(self):
    result = self.observe((self.command(1, 100), self.command(2, 90), self.command(3, 95)))
    self.assertEqual(result['valid_command_count'], 1)


  def test_failure_artifact_write_error_does_not_leak_private_path(self):
    with tempfile.TemporaryDirectory() as folder:
      argv = ['replay', '--raw', folder + '/missing', '--source-root', folder,
              '--source-manifest', folder + '/missing', '--output', folder + '/new']
      stream = io.StringIO()
      with patch.object(sys, 'argv', argv), patch.object(self.api, 'write_private', side_effect=OSError('private-secret-path')):
        with redirect_stdout(stream):
          result = self.api.main()
      self.assertEqual(result, 2)
      self.assertNotIn('private-secret-path', stream.getvalue())


  def test_failure_path_stat_error_is_sanitized(self):
    with tempfile.TemporaryDirectory() as folder:
      argv = ['replay', '--raw', folder + '/missing', '--source-root', folder,
              '--source-manifest', folder + '/missing', '--output', folder + '/new']
      stream = io.StringIO()
      with patch.object(sys, 'argv', argv), patch.object(Path, 'exists', side_effect=OSError('private-stat-path')):
        with redirect_stdout(stream):
          result = self.api.main()
      self.assertEqual(result, 2)
      self.assertNotIn('private-stat-path', stream.getvalue())


if __name__ == '__main__':
  unittest.main()
