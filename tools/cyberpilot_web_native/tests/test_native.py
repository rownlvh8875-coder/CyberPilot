"""Actual native Cereal messages into the unchanged production collector."""

import unittest

from tools.cyberpilot_web_native.fixtures import NativeFixture
from tools.cyberpilot_web_native.isolation import namespace


class NativeCollectorTests(unittest.TestCase):
  def setUp(self):
    self.context = namespace()
    self.sandbox = self.context.__enter__()
    self.addCleanup(self.context.__exit__, None, None, None)
    self.now = [10.0]
    self.fixture = NativeFixture(self.sandbox, clock=lambda: self.now[0])
    self.addCleanup(self.fixture.close)

  def test_real_native_types_and_four_topics(self):
    for topic in ('deviceState', 'selfdriveState', 'carState', 'managerState'):
      self.fixture.push(topic, 10)
    data = self.fixture.store.snapshot()['topics']
    self.assertTrue(data['deviceState']['data']['started'])
    self.assertEqual(data['deviceState']['data']['cpu_temp_c'], [42.5])
    self.assertTrue(data['selfdriveState']['data']['active'])
    self.assertTrue(data['carState']['data']['can_valid'])
    self.assertEqual(data['managerState']['data']['processes'][0]['name'], 'synthetic-worker')
    self.assertTrue(self.fixture.collector.sm.__class__.__module__.startswith('openpilot.cereal.messaging'))

  def test_invalid_native_message_hides_previous_values(self):
    self.fixture.push('carState', 10)
    self.fixture.push('carState', 20, valid=False)
    result = self.fixture.store.snapshot()['topics']['carState']
    self.assertEqual(result['status'], 'invalid')
    self.assertIsNone(result['data'])

  def test_duplicate_and_backward_native_samples_do_not_refresh(self):
    self.fixture.push('carState', 10)
    self.now[0] += 6
    self.fixture.push('carState', 10)
    self.fixture.push('carState', 9)
    result = self.fixture.store.snapshot()['topics']['carState']
    self.assertEqual(result['source_time_ns'], '10')
    self.assertEqual(result['status'], 'stale')
    self.assertIsNone(result['data'])

  def test_independent_native_topic_age(self):
    self.fixture.push('carState', 10)
    self.now[0] += 6
    self.fixture.push('deviceState', 20)
    data = self.fixture.store.snapshot()['topics']
    self.assertEqual(data['carState']['status'], 'stale')
    self.assertEqual(data['deviceState']['status'], 'live')

  def test_native_uint64_preserved_as_decimal_string(self):
    self.fixture.push('carState', 2**64 - 1)
    self.assertEqual(self.fixture.store.snapshot()['topics']['carState']['source_time_ns'], '18446744073709551615')

  def test_no_sample_does_not_expose_native_defaults(self):
    self.fixture.collector.poll()
    result = self.fixture.store.snapshot()['topics']['carState']
    self.assertEqual(result['status'], 'missing')
    self.assertIsNone(result['data'])

  def test_nonfinite_native_field_is_null(self):
    self.fixture.push('deviceState', 10, fields={'freeSpacePercent': float('nan')})
    self.assertIsNone(self.fixture.store.snapshot()['topics']['deviceState']['data']['free_space_percent'])

  def test_control_endpoint_cannot_be_published(self):
    with self.assertRaises(ValueError):
      self.fixture.push('sendcan', 10)
    self.assertFalse((self.sandbox.path / 'sendcan').exists())

  def test_source_restart_uses_new_store_and_lower_timestamp(self):
    self.fixture.push('carState', 900, fields={'canValid': True})
    previous_store = self.fixture.store
    self.fixture.close()
    restarted = NativeFixture(self.sandbox, clock=lambda: self.now[0])
    self.addCleanup(restarted.close)
    missing = restarted.store.snapshot()['topics']['carState']
    self.assertEqual(missing['status'], 'missing')
    self.assertIsNone(missing['data'])
    self.assertIsNot(restarted.store, previous_store)
    restarted.push('carState', 1, fields={'canValid': False})
    current = restarted.store.snapshot()['topics']['carState']
    self.assertEqual(current['status'], 'live')
    self.assertEqual(current['source_time_ns'], '1')
    self.assertFalse(current['data']['can_valid'])
    previous = previous_store.snapshot()['topics']['carState']
    self.assertEqual(previous['source_time_ns'], '900')
    self.assertTrue(previous['data']['can_valid'])
