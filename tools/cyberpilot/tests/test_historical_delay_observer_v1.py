"""Synthetic-only contracts; no real log or current LateralDelay builder."""
import contextlib
import dataclasses
import importlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

MODULE = 'tools.cyberpilot.historical_delay_observer_v1'


class TestHistoricalDelayObserver(unittest.TestCase):
  def setUp(self):
    self.assertIsNotNone(importlib.util.find_spec(MODULE), 'F49 implementation is missing')
    self.api = importlib.import_module(MODULE)

  def payload(self, *, ordinal=7, timestamp=100, status='estimated', valid=True, mean=0.25, std=0.125):
    return {'ordinal': ordinal, 'timestamp_ns': timestamp, 'historical_service': 'liveDelay',
            'event_valid': valid, 'units': 's',
            'fields': {'lateralDelayEstimate': mean, 'lateralDelayEstimateStd': std,
                       'status': status, 'validBlocks': 5, 'calPerc': 100}}

  def test_original_mean_std_float32_bits_are_preserved(self):
    value = self.api.project(self.payload()).to_dict()
    original = value['original_fields']
    self.assertEqual(original['liveDelay.lateralDelayEstimate']['value'], 0.25)
    self.assertEqual(original['liveDelay.lateralDelayEstimate']['float32_hex_le'], '0000803e')
    self.assertEqual(original['liveDelay.lateralDelayEstimateStd']['value'], 0.125)
    self.assertEqual(original['liveDelay.lateralDelayEstimateStd']['float32_hex_le'], '0000003e')

  def test_original_message_and_state_are_preserved(self):
    value = self.api.project(self.payload(status='invalid', valid=False)).to_dict()
    self.assertEqual(value['identity'], 'HISTORICAL_LIVE_DELAY_OBSERVATION_V1')
    self.assertEqual(value['original_message']['ordinal'], 7)
    self.assertEqual(value['original_message']['logMonoTime_ns'], 100)
    self.assertFalse(value['original_message']['event_valid'])
    self.assertEqual(value['original_state']['status']['name'], 'invalid')
    self.assertEqual(value['original_state']['status']['code'], 2)
    self.assertEqual(value['original_state']['validBlocks']['value'], 5)
    self.assertIn('PRODUCER_REPORTED_INVALID', value['diagnostics'])
    self.assertIn('EVENT_INVALID', value['diagnostics'])

  def test_historical_estimate_above_current_limit_is_not_clipped(self):
    value = self.api.project(self.payload(mean=0.875)).to_dict()
    self.assertEqual(value['observed_quantities']['historical_estimate_s'], 0.875)
    self.assertFalse(value['qualification']['current_service_equivalence'])

  def test_unestimated_zero_std_is_not_accuracy_or_measured_delay(self):
    value = self.api.project(self.payload(status='unestimated', std=0.0)).to_dict()
    self.assertEqual(value['original_state']['status']['code'], 0)
    self.assertIn('PRODUCER_REPORTED_UNESTIMATED', value['diagnostics'])
    self.assertIn('ZERO_STD_NOT_ACCURACY', value['diagnostics'])
    self.assertFalse(value['qualification']['physical_delay_qualified'])
    self.assertEqual(value['qualification']['producer_internal_state'], 'UNKNOWN')

  def test_absent_version_stays_unknown(self):
    value = self.api.project(self.payload()).to_dict()
    self.assertEqual(value['original_version']['state'], 'UNKNOWN')
    self.assertIsNone(value['original_version']['recorded_value'])

  def test_wrong_source_identity_is_blocked(self):
    with self.assertRaisesRegex(ValueError, 'SOURCE_IDENTITY_MISMATCH'):
      self.api.project(self.payload(), dataclasses.replace(self.api.Binding(), source_commit='a' * 40))

  def test_wrong_schema_identity_is_blocked(self):
    with self.assertRaisesRegex(ValueError, 'SCHEMA_IDENTITY_MISMATCH'):
      self.api.project(self.payload(), dataclasses.replace(self.api.Binding(), schema_sha256='b' * 64))

  def test_wrong_producer_identity_is_blocked(self):
    with self.assertRaisesRegex(ValueError, 'PRODUCER_IDENTITY_MISMATCH'):
      self.api.project(self.payload(), dataclasses.replace(self.api.Binding(), producer_sha256='b' * 64))

  def test_cross_segment_is_blocked(self):
    with self.assertRaisesRegex(ValueError, 'CROSS_SEGMENT_BINDING'):
      self.api.project(self.payload(), dataclasses.replace(self.api.Binding(), dataset_sha256='b' * 64))

  def test_current_service_is_not_accepted_as_history(self):
    payload = self.payload()
    payload['historical_service'] = 'lateralDelay'
    with self.assertRaisesRegex(ValueError, 'HISTORICAL_SERVICE_REQUIRED'):
      self.api.project(payload)

  def test_current_output_contract_is_rejected(self):
    with self.assertRaisesRegex(ValueError, 'CURRENT_SCHEMA_SYNTHESIS_BLOCKED'):
      self.api.project(self.payload(), target='LateralDelay')

  def test_version_synthesis_is_blocked(self):
    payload = self.payload()
    payload['fields']['version'] = 1
    with self.assertRaisesRegex(ValueError, 'UNRECORDED_VERSION'):
      self.api.project(payload)

  def test_top_level_version_synthesis_is_blocked(self):
    payload = self.payload()
    payload['version'] = 1
    with self.assertRaisesRegex(ValueError, 'UNRECORDED_VERSION'):
      self.api.project(payload)

  def test_missing_mean_is_blocked(self):
    payload = self.payload()
    del payload['fields']['lateralDelayEstimate']
    with self.assertRaisesRegex(ValueError, 'MISSING_MEAN'):
      self.api.project(payload)

  def test_missing_std_is_blocked(self):
    payload = self.payload()
    del payload['fields']['lateralDelayEstimateStd']
    with self.assertRaisesRegex(ValueError, 'MISSING_STD'):
      self.api.project(payload)

  def test_non_float_types_are_not_silently_coerced(self):
    for wrong in [True, 1, '0.25', None]:
      with self.subTest(wrong=wrong), self.assertRaisesRegex(ValueError, 'INVALID_FIELD_TYPE'):
        self.api.project(self.payload(mean=wrong))

  def test_nonfinite_values_are_blocked_without_input_mutation(self):
    for field in ['lateralDelayEstimate', 'lateralDelayEstimateStd']:
      for wrong in [float('nan'), float('inf'), -float('inf')]:
        payload = self.payload()
        payload['fields'][field] = wrong
        with self.subTest(field=field, value=repr(wrong)), self.assertRaisesRegex(ValueError, 'NONFINITE_VALUE'):
          self.api.project(payload)
        self.assertIs(payload['fields'][field], wrong)

  def test_non_float32_value_is_rejected_without_rounding(self):
    with self.assertRaisesRegex(ValueError, 'NOT_EXACT_FLOAT32'):
      self.api.project(self.payload(mean=0.1))

  def test_negative_std_is_blocked(self):
    with self.assertRaisesRegex(ValueError, 'NEGATIVE_STD'):
      self.api.project(self.payload(std=-0.125))

  def test_wrong_unit_is_blocked(self):
    payload = self.payload()
    payload['units'] = 'ms'
    with self.assertRaisesRegex(ValueError, 'INVALID_UNIT'):
      self.api.project(payload)

  def test_timestamp_reversal_is_not_sorted_away(self):
    rows = [self.payload(ordinal=1, timestamp=200), self.payload(ordinal=2, timestamp=100)]
    with self.assertRaisesRegex(ValueError, 'TIMESTAMP_REVERSAL'):
      self.api.observe(rows)
    self.assertEqual([x['timestamp_ns'] for x in rows], [200, 100])

  def test_duplicate_timestamp_is_blocked(self):
    with self.assertRaisesRegex(ValueError, 'DUPLICATE_TIMESTAMP'):
      self.api.observe([self.payload(ordinal=1), self.payload(ordinal=2)])

  def test_duplicate_message_ordinal_is_blocked(self):
    with self.assertRaisesRegex(ValueError, 'DUPLICATE_MESSAGE'):
      self.api.observe([self.payload(ordinal=1, timestamp=100), self.payload(ordinal=1, timestamp=200)])

  def test_decreasing_file_ordinal_is_blocked(self):
    with self.assertRaisesRegex(ValueError, 'ORIGINAL_ORDER_MISMATCH'):
      self.api.observe([self.payload(ordinal=2, timestamp=100), self.payload(ordinal=1, timestamp=200)])

  def test_zero_timestamp_is_blocked(self):
    with self.assertRaisesRegex(ValueError, 'INVALID_TIMESTAMP'):
      self.api.project(self.payload(timestamp=0))

  def test_unrecorded_producer_state_is_not_inferred(self):
    payload = self.payload()
    payload['producer_state'] = 'fully_known'
    with self.assertRaisesRegex(ValueError, 'UNRECORDED_FIELDS'):
      self.api.project(payload)

  def test_runtime_command_injection_is_blocked(self):
    payload = self.payload()
    payload['actuators'] = {'torque': 0.5}
    with self.assertRaisesRegex(ValueError, 'UNRECORDED_FIELDS'):
      self.api.project(payload)
    self.assertFalse(self.api.project(self.payload()).to_dict()['qualification']['runtime_authorized'])

  def test_input_and_observation_are_immutable_and_independent(self):
    payload = self.payload()
    before = json.dumps(payload, sort_keys=True)
    observed = self.api.project(payload)
    self.assertEqual(json.dumps(payload, sort_keys=True), before)
    payload['fields']['lateralDelayEstimate'] = 0.5
    self.assertEqual(observed.to_dict()['observed_quantities']['historical_estimate_s'], 0.25)
    field = 'mean_s'
    with self.assertRaises(dataclasses.FrozenInstanceError):
      setattr(observed.sample, field, 0.75)
    copy = observed.to_dict()
    copy['observed_quantities']['historical_estimate_s'] = 0.75
    self.assertEqual(observed.to_dict()['observed_quantities']['historical_estimate_s'], 0.25)

  def test_signed_zero_bits_are_preserved(self):
    value = self.api.project(self.payload(mean=-0.0)).to_dict()
    self.assertEqual(value['original_fields']['liveDelay.lateralDelayEstimate']['float32_hex_le'], '00000080')

  def test_unknown_status_is_blocked_without_default(self):
    with self.assertRaisesRegex(ValueError, 'INVALID_STATUS'):
      self.api.project(self.payload(status='unknown-new-enum'))

  def test_historical_state_range_warning_preserves_original_values(self):
    payload = self.payload()
    payload['fields']['validBlocks'] = -1
    value = self.api.project(payload).to_dict()
    self.assertEqual(value['original_state']['validBlocks']['value'], -1)
    self.assertIn('HISTORICAL_STATE_RANGE_WARNING', value['diagnostics'])

  def test_source_proof_is_not_claimed_for_an_arbitrary_projection(self):
    value = self.api.project(self.payload()).to_dict()
    self.assertEqual(value['qualification']['data_origin_verification'], 'REQUIRES_ASSOCIATED_READER_RECEIPT')
    self.assertFalse(value['qualification']['controller_consumption_proven'])

  def test_sequence_summary_preserves_count_and_unknown_state(self):
    values = self.api.observe([self.payload(ordinal=1, timestamp=100), self.payload(ordinal=2, timestamp=200, status='unestimated', std=0.0)])
    summary = self.api.summarize(values)
    self.assertEqual(summary['observation_count'], 2)
    self.assertEqual(summary['status_counts'], {'estimated': 1, 'unestimated': 1, 'invalid': 0})
    self.assertEqual(summary['producer_state_unknown_count'], 2)
    self.assertEqual(summary['time_order']['duration_ns'], 100)

  def test_same_input_is_canonical_byte_identical(self):
    payloads = [self.payload(ordinal=1, timestamp=100), self.payload(ordinal=2, timestamp=200)]
    a = self.api.summarize(self.api.observe(payloads))
    b = self.api.summarize(self.api.observe(payloads))
    self.assertEqual(self.api.canonical(a), self.api.canonical(b))

  def test_cli_argument_error_does_not_echo_private_values(self):
    args = ['f49', '--raw', 'SYNTHETIC', '--source-root', 'SYNTHETIC', '--source-manifest', 'SYNTHETIC',
            '--output', 'SYNTHETIC', '--bad', 'PRIVATE_SENTINEL']
    stdout, stderr = io.StringIO(), io.StringIO()
    with patch('sys.argv', args), contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
      code = self.api.main()
    self.assertEqual(code, 2)
    self.assertNotIn('PRIVATE_SENTINEL', stdout.getvalue() + stderr.getvalue())
    self.assertIn('INVALID_ARGUMENTS', stdout.getvalue())

  def test_cli_existing_output_and_raw_are_never_modified(self):
    with tempfile.TemporaryDirectory() as directory:
      root = Path(directory)
      inputs = root / 'inputs'
      inputs.mkdir()
      raw = inputs / 'private.zst'
      raw.write_bytes(b'SYNTHETIC_INPUT')
      output = root / 'output'
      output.mkdir(mode=0o700)
      marker = output / 'keep.txt'
      marker.write_bytes(b'KEEP')
      args = ['f49', '--raw', str(raw), '--source-root', str(root/'source'),
              '--source-manifest', str(root/'source'/'manifest.json'), '--output', str(output)]
      with patch('sys.argv', args), contextlib.redirect_stdout(io.StringIO()):
        self.assertEqual(self.api.main(), 2)
      self.assertEqual(marker.read_bytes(), b'KEEP')
      self.assertEqual(sorted(p.name for p in output.iterdir()), ['keep.txt'])
      self.assertEqual(raw.read_bytes(), b'SYNTHETIC_INPUT')

  def test_cli_wrong_raw_hash_fails_closed_and_keeps_readonly_input(self):
    with tempfile.TemporaryDirectory() as directory:
      root = Path(directory)
      inputs = root/'inputs'
      inputs.mkdir()
      raw = inputs/'private.zst'
      raw.write_bytes(b'SYNTHETIC_INPUT')
      raw.chmod(0o400)
      output = root/'output'
      args = ['f49', '--raw', str(raw), '--source-root', str(root/'source'),
              '--source-manifest', str(root/'source'/'manifest.json'), '--output', str(output)]
      stdout = io.StringIO()
      with patch('sys.argv', args), contextlib.redirect_stdout(stdout):
        self.assertEqual(self.api.main(), 2)
      self.assertNotIn(str(raw), stdout.getvalue())
      self.assertEqual(raw.read_bytes(), b'SYNTHETIC_INPUT')
      self.assertEqual(json.loads((output/'failure.json').read_text())['reason'], 'FILE_IDENTITY_MISMATCH')

  def test_pure_projection_does_not_import_vehicle_runtime(self):
    import sys
    before = set(sys.modules)
    self.api.project(self.payload()).to_dict()
    new = set(sys.modules) - before
    forbidden = ('openpilot.cereal.messaging', 'openpilot.selfdrive.controls.controlsd', 'openpilot.common.params')
    self.assertFalse(any(any(name.startswith(prefix) for prefix in forbidden) for name in new))


  def test_direct_worker_cannot_mutate_an_unrelated_existing_directory(self):
    with tempfile.TemporaryDirectory() as directory:
      root = Path(directory)
      output = root/'existing'
      output.mkdir(mode=0o700)
      (output/'keep.txt').write_bytes(b'KEEP')
      args = ['f49', '--worker', '--raw', str(root/'inputs'/'private.zst'),
              '--source-root', str(root/'source'), '--source-manifest', str(root/'source'/'manifest.json'),
              '--output', str(output)]
      def private_decoder_boundary(_args, folder):
        self.api.base().write_private(folder/'source_projection.jsonl', b'SYNTHETIC_ONLY')
      with patch('sys.argv', args), patch.object(self.api, 'decode', side_effect=private_decoder_boundary), contextlib.redirect_stdout(io.StringIO()):
        code = self.api.main()
      self.assertEqual(code, 2)
      self.assertEqual(sorted(x.name for x in output.iterdir()), ['keep.txt'])
      self.assertEqual((output/'keep.txt').read_bytes(), b'KEEP')


if __name__ == '__main__':
  unittest.main()
