"""Synthetic-only F47 temporal candidate and order tests."""
import dataclasses
import contextlib
import io
import importlib
import importlib.util
import unittest
from unittest.mock import patch

MODULE = 'tools.cyberpilot.recorded_input_binding_v1'
TOKEN = 'a' * 64


class TestRecordedInputBinding(unittest.TestCase):
  def setUp(self):
    self.assertIsNotNone(importlib.util.find_spec(MODULE), 'F47 implementation is missing')
    self.api = importlib.import_module(MODULE)

  def stamp(self, ordinal, service, timestamp, *, valid=True, binding=TOKEN, reference=None):
    return self.api.Stamp(ordinal, service, timestamp, valid, binding, reference)

  def command(self, ordinal=10, timestamp=100):
    return self.stamp(ordinal, 'carControl', timestamp)

  def test_cross_service_reversal_keeps_file_order(self):
    rows = (self.stamp(1, 'modelV2', 90), self.stamp(2, 'carState', 30))
    result = self.api.order_report(rows)
    self.assertEqual(result['reversals'], 1)
    self.assertEqual(result['cross_service_reversals'], 1)
    self.assertEqual(result['pairs']['modelV2->carState']['ordinal_range'], [2, 2])
    self.assertEqual([x.timestamp_ns for x in rows], [90, 30])

  def test_per_service_reversal_is_not_repaired(self):
    rows = (self.stamp(1, 'carState', 90), self.stamp(2, 'carState', 30))
    index = self.api.make_index('carState', rows)
    result = self.api.candidate(self.command(), index, 'carState')
    self.assertEqual(result['status'], 'TEMPORAL_BINDING_AMBIGUOUS')
    self.assertIn('PER_SERVICE_ORDER_ERROR', result['reasons'])
    self.assertEqual(self.api.order_report(rows)['cross_service_reversals'], 0)

  def test_original_ordinal_sort_concealment_is_rejected(self):
    rows = (self.stamp(1, 'modelV2', 90), self.stamp(2, 'carState', 30))
    with self.assertRaisesRegex(ValueError, 'WIRE_ORDER_MISMATCH'):
      self.api.characterize(tuple(sorted(rows, key=lambda x: x.timestamp_ns)), TOKEN)

  def test_prior_candidate_does_not_use_future_timestamp(self):
    rows = (self.stamp(1, 'modelV2', 70), self.stamp(2, 'modelV2', 120))
    result = self.api.candidate(self.command(), self.api.make_index('modelV2', rows), 'modelV2')
    self.assertEqual(result['candidate_ordinals'], [1])
    self.assertEqual(result['status'], 'TEMPORAL_BINDING_AMBIGUOUS')
    self.assertIn('FUTURE_FILE_PREDECESSOR_BYPASSED', result['reasons'])

  def test_timestamp_prior_but_file_future_is_not_candidate(self):
    rows = (self.stamp(20, 'modelV2', 70),)
    result = self.api.candidate(self.command(), self.api.make_index('modelV2', rows), 'modelV2')
    self.assertEqual(result['candidate_ordinals'], [])
    self.assertEqual(result['status'], 'INPUT_MISSING')

  def test_missing_service_is_input_missing(self):
    result = self.api.candidate(self.command(), self.api.make_index('carState', ()), 'carState')
    self.assertEqual(result['status'], 'INPUT_MISSING')

  def test_historical_alias_is_not_silently_renamed(self):
    rows = (self.stamp(1, 'liveParameters', 70),)
    with self.assertRaisesRegex(ValueError, 'INCORRECT_SERVICE_BINDING'):
      self.api.candidate(self.command(), self.api.make_index('liveParameters', rows), 'vehicleParameters')
    result = self.api.candidate(self.command(), self.api.make_index('vehicleParameters', ()), 'vehicleParameters')
    self.assertEqual(result['status'], 'SOURCE_SCHEMA_UNQUALIFIED')
    self.assertEqual(result['candidate_ordinals'], [])

  def test_duplicate_latest_timestamp_stays_ambiguous(self):
    rows = (self.stamp(1, 'carState', 70), self.stamp(2, 'carState', 70))
    result = self.api.candidate(self.command(), self.api.make_index('carState', rows), 'carState')
    self.assertEqual(result['candidate_ordinals'], [1, 2])
    self.assertEqual(result['status'], 'TEMPORAL_BINDING_AMBIGUOUS')

  def test_same_time_as_command_is_not_proven_consumption(self):
    rows = (self.stamp(1, 'carState', 100),)
    result = self.api.candidate(self.command(), self.api.make_index('carState', rows), 'carState')
    self.assertEqual(result['status'], 'TEMPORAL_BINDING_AMBIGUOUS')
    self.assertIn('EQUAL_MESSAGE_TIMESTAMP', result['reasons'])

  def test_declared_synthetic_stale_age_is_detected(self):
    rows = (self.stamp(1, 'carState', 10),)
    result = self.api.candidate(self.command(), self.api.make_index('carState', rows), 'carState', max_age_ns=20)
    self.assertIn('DECLARED_MESSAGE_AGE_EXCEEDED', result['reasons'])
    self.assertEqual(result['status'], 'TEMPORAL_BINDING_AMBIGUOUS')

  def test_undeclared_age_remains_unqualified(self):
    rows = (self.stamp(1, 'carState', 10),)
    result = self.api.candidate(self.command(), self.api.make_index('carState', rows), 'carState')
    self.assertEqual(result['status'], 'RECORDED_INPUT_CANDIDATE')
    self.assertEqual(result['freshness'], 'UNQUALIFIED')

  def test_invalid_latest_event_is_not_replaced_with_older_valid(self):
    rows = (self.stamp(1, 'carState', 10), self.stamp(2, 'carState', 20, valid=False))
    result = self.api.candidate(self.command(), self.api.make_index('carState', rows), 'carState')
    self.assertEqual(result['candidate_ordinals'], [])
    self.assertIn('INVALID_LATEST_EVENT', result['reasons'])

  def test_reuse_is_not_forced_one_to_one(self):
    event = self.stamp(1, 'modelV2', 10)
    index = self.api.make_index('modelV2', (event,))
    self.assertEqual(self.api.candidate(self.command(2, 20), index, 'modelV2')['candidate_ordinals'], [1])
    self.assertEqual(self.api.candidate(self.command(3, 30), index, 'modelV2')['candidate_ordinals'], [1])

  def test_mixed_segment_binding_is_blocked(self):
    rows = (self.stamp(1, 'carState', 10, binding='b' * 64), self.command())
    with self.assertRaisesRegex(ValueError, 'INCORRECT_SOURCE_BINDING'):
      self.api.characterize(rows, TOKEN)

  def test_source_identity_exchange_is_blocked(self):
    rows = (self.stamp(1, 'modelV2', 10, binding='c' * 64), self.command())
    with self.assertRaisesRegex(ValueError, 'INCORRECT_SOURCE_BINDING'):
      self.api.characterize(rows, TOKEN)

  def test_incorrect_index_service_is_blocked(self):
    with self.assertRaisesRegex(ValueError, 'INCORRECT_SERVICE_BINDING'):
      self.api.make_index('carState', (self.stamp(1, 'carOutput', 10),))

  def test_caroutput_is_not_an_input_or_physical_sensor(self):
    rows = (self.stamp(1, 'carOutput', 10), self.stamp(20, 'carOutput', 110))
    index = self.api.make_index('carOutput', rows)
    with self.assertRaisesRegex(ValueError, 'WRONG_SERVICE_ROLE'):
      self.api.candidate(self.command(), index, 'carOutput')
    result = self.api.output_observation(self.command(), index)
    self.assertEqual(result['prior_ordinal'], 1)
    self.assertEqual(result['post_ordinal'], 20)
    self.assertFalse(result['physical_response_qualified'])
    self.assertFalse(result['proven_command_result_binding'])

  def test_complete_direct_candidates_do_not_invent_internal_state(self):
    rows = tuple(self.stamp(i + 1, s, (i + 1) * 10) for i, s in enumerate(self.api.DIRECT)) + (self.command(),)
    summary, commands = self.api.characterize(rows, TOKEN)
    self.assertEqual(summary['primary_counts']['SOURCE_SCHEMA_UNQUALIFIED'], 1)
    self.assertEqual(summary['direct_primary_counts']['RECORDED_INPUT_CANDIDATE'], 1)
    self.assertEqual(summary['secondary_counts']['INTERNAL_STATE_UNAVAILABLE'], 1)
    self.assertFalse(summary['native_exact_replay_proven'])
    self.assertEqual(len(commands), 1)

  def test_primary_partition_is_exact_and_secondary_can_overlap(self):
    rows = (self.command(1, 10), self.command(2, 20))
    summary, commands = self.api.characterize(rows, TOKEN)
    self.assertEqual(sum(summary['primary_counts'].values()), 2)
    self.assertEqual(summary['primary_counts']['SOURCE_SCHEMA_UNQUALIFIED'], 2)
    self.assertEqual(summary['secondary_counts']['INTERNAL_STATE_UNAVAILABLE'], 2)
    self.assertEqual(len(commands), 2)

  def test_prefix_order_error_does_not_look_ahead(self):
    rows = (self.stamp(1, 'carState', 10), self.stamp(20, 'carState', 5))
    result = self.api.candidate(self.command(), self.api.make_index('carState', rows), 'carState')
    self.assertEqual(result['status'], 'RECORDED_INPUT_CANDIDATE')

  def test_future_reference_is_not_used_as_input(self):
    rows = (self.stamp(1, 'controlsState', 10, reference=120), self.command(2, 100),
            self.stamp(3, 'modelV2', 120))
    summary, commands = self.api.characterize(rows, TOKEN)
    self.assertEqual(summary['model_reference_witness']['eligible_before_command'], 0)
    self.assertEqual(summary['model_reference_witness']['reference_found_after_command'], 1)
    self.assertEqual(commands[0]['inputs']['modelV2']['candidate_ordinals'], [])

  def test_logged_model_reference_is_evidence_not_full_binding(self):
    rows = (self.stamp(1, 'modelV2', 10), self.stamp(2, 'controlsState', 20, reference=10),
            self.command(3, 30))
    summary, _ = self.api.characterize(rows, TOKEN)
    self.assertEqual(summary['model_reference_witness']['eligible_before_command'], 1)
    self.assertFalse(summary['actual_controller_consumption_proven'])

  def test_original_service_metadata_is_immutable(self):
    with self.assertRaises(dataclasses.FrozenInstanceError):
      self.stamp(1, 'modelV2', 10).timestamp_ns = 20

  def test_order_signature_detects_record_loss(self):
    rows = (self.stamp(1, 'modelV2', 90), self.stamp(2, 'carState', 30))
    self.assertNotEqual(self.api.order_report(rows)['reversal_signature_sha256'],
                        self.api.order_report(rows[:1])['reversal_signature_sha256'])

  def test_duplicate_and_nominal_gap_statistics_are_separate(self):
    rows = (self.stamp(1, 'carState', 10000000), self.stamp(2, 'carState', 10000000),
            self.stamp(3, 'carState', 30000000))
    stats = self.api.service_stats(rows, frequency_hz=100)
    self.assertEqual(stats['duplicate_timestamps'], 1)
    self.assertEqual(stats['over_nominal_period_count'], 1)
    self.assertFalse(stats['deadline_qualification'])

  def test_zero_timestamp_is_not_valid_candidate(self):
    result = self.api.candidate(self.command(), self.api.make_index('carState', (self.stamp(1, 'carState', 0),)), 'carState')
    self.assertEqual(result['status'], 'TEMPORAL_BINDING_AMBIGUOUS')

  def test_canonical_summary_is_repeatable(self):
    rows = (self.stamp(1, 'modelV2', 10), self.command())
    a, _ = self.api.characterize(rows, TOKEN)
    b, _ = self.api.characterize(rows, TOKEN)
    self.assertEqual(self.api.canonical(a), self.api.canonical(b))

  def test_controlsstate_is_a_diagnostic_companion_not_sensed_input(self):
    row = self.stamp(1, 'controlsState', 10)
    result = self.api.candidate(self.command(), self.api.make_index('controlsState', (row,)), 'controlsState')
    self.assertEqual(result.get('role'), 'CONTROLLER_DIAGNOSTIC_COMPANION')


  def test_public_candidate_rejects_cross_source_index(self):
    index = self.api.make_index('carState', (self.stamp(1, 'carState', 10, binding='b' * 64),))
    with self.assertRaisesRegex(ValueError, 'INCORRECT_SOURCE_BINDING'):
      self.api.candidate(self.command(), index, 'carState')

  def test_public_output_rejects_cross_source_index(self):
    index = self.api.make_index('carOutput', (self.stamp(1, 'carOutput', 10, binding='b' * 64),))
    with self.assertRaisesRegex(ValueError, 'INCORRECT_SOURCE_BINDING'):
      self.api.output_observation(self.command(), index)

  def test_index_rejects_mixed_sources(self):
    rows = (self.stamp(1, 'carState', 10), self.stamp(2, 'carState', 20, binding='b' * 64))
    with self.assertRaisesRegex(ValueError, 'INCORRECT_SOURCE_BINDING'):
      self.api.make_index('carState', rows)

  def test_cli_malformed_arguments_do_not_echo_private_values(self):
    output, error = io.StringIO(), io.StringIO()
    args = ['f47', '--raw', 'SYNTHETIC', '--source-root', 'SYNTHETIC', '--source-manifest', 'SYNTHETIC',
            '--f46-tape', 'SYNTHETIC', '--output', 'SYNTHETIC', '--typo', 'PRIVATE_SENTINEL']
    with patch('sys.argv', args), contextlib.redirect_stdout(output), contextlib.redirect_stderr(error):
      try:
        code = self.api.main()
      except SystemExit as exception:
        code = exception.code
    self.assertEqual(code, 2)
    self.assertNotIn('PRIVATE_SENTINEL', output.getvalue() + error.getvalue())
    self.assertIn('INVALID_ARGUMENTS', output.getvalue() + error.getvalue())


if __name__ == '__main__':
  unittest.main()
