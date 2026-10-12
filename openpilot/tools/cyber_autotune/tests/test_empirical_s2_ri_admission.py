import unittest
import numpy as np
from importlib import import_module


def fixture(n=100):
  required = ('state.speed_mps', 'state.angle_deg', 'state.driver_pressed', 'state.driver_torque', 'state.gear',
              'state.fault_temporary', 'state.fault_permanent', 'command.raw', 'command.normalized', 'control.lat_active')
  a = {}
  for k in required:
    a[k] = np.full(n, 'drive', dtype='<U16') if k == 'state.gear' else np.zeros(n, dtype=np.float64)
    a[k+'.available'] = np.ones(n, dtype=bool)
  a['state.speed_mps'][:] = 20
  a['control.lat_active'][:] = 1
  a['state.angle_deg'] = (np.arange(n)*.1).astype(np.float32).astype(np.float64)
  a['grid_time_ns'] = np.arange(n, dtype=np.int64)*10_000_000+1_000_000_000
  a['legacy_diagnostic_valid'] = np.ones(n, dtype=bool)
  for kind in ('state', 'command', 'control'):
    for k in ('present', 'fresh'):
      a[kind+'.'+k] = np.ones(n, dtype=bool)
    a[kind+'.gap'] = np.zeros(n, dtype=bool)
    a[kind+'.event_valid'] = np.ones(n, dtype=np.int8)
    a[kind+'.time_ns'] = a['grid_time_ns'].copy()
    a[kind+'.age_ns'] = np.zeros(n, dtype=np.int64)
  return a


class TestS2RIAdmission(unittest.TestCase):
  def derive(self, a):
    return import_module('openpilot.tools.cyber_autotune.empirical_s2_ri_admission').derive(a)

  def test_valid_rows(self):
    d = self.derive(fixture())
    self.assertTrue(d['s2_ri_causal_valid'].all())
    self.assertTrue(d['model_eligible'].all())
    np.testing.assert_array_equal(d['within_s2_ri_causal_run_index'], np.arange(100))

  def test_deleted_nan_arbitrary_rate_and_historical_ids_ignored(self):
    a = fixture()
    expected = self.derive(a)
    for value, availability in ((np.full(100, np.nan), False), (np.arange(100.)+999, True)):
      b = {**a, 'state.rate': value, 'state.rate.available': np.full(100, availability),
           'causal_required_valid': np.zeros(100, bool), 'causal_run_id': np.full(100, -1),
           'within_causal_run_index': np.full(100, -1), 'run_boundary': np.ones(100, bool)}
      actual = self.derive(b)
      for key in expected:
        np.testing.assert_array_equal(actual[key], expected[key])

  def test_request_unavailable_ignored(self):
    a = fixture()
    expected = self.derive(a)
    a['control.requested'] = np.full(100, np.nan)
    a['control.requested.available'] = np.zeros(100, bool)
    for key, v in self.derive(a).items():
      np.testing.assert_array_equal(v, expected[key])

  def test_required_missing_breaks(self):
    a = fixture()
    a['command.normalized.available'][50] = False
    d = self.derive(a)
    self.assertFalse(d['s2_ri_causal_valid'][50])
    self.assertEqual(d['within_s2_ri_causal_run_index'][51], 0)

  def test_context_boundaries(self):
    for field in ('control.lat_active', 'state.driver_pressed', 'state.fault_temporary', 'state.fault_permanent'):
      with self.subTest(field=field):
        a = fixture()
        a[field][40:50] = 0 if field == 'control.lat_active' else 1
        d = self.derive(a)
        self.assertTrue(d['s2_ri_causal_valid'][40:50].all())
        self.assertFalse(d['model_eligible'][40:50].any())
        self.assertEqual(d['within_s2_ri_causal_run_index'][50], 0)
        self.assertEqual(d['streak_all'][50], 1)

  def test_gear_speed_exclusion(self):
    for key, value in (('state.speed_mps', 4.), ('state.gear', 'reverse')):
      a = fixture()
      a[key][20] = value
      d = self.derive(a)
      self.assertTrue(d['s2_ri_causal_valid'][20])
      self.assertFalse(d['model_eligible'][20])
      self.assertEqual(d['streak_all'][21], 1)

  def test_offgrid_exclusion(self):
    a = fixture()
    a['state.angle_deg'][20] = .11
    d = self.derive(a)
    self.assertFalse(d['model_eligible'][20])
    self.assertFalse(d['angle_grid_valid'][20])

  def test_rail_scopes_predeclared(self):
    a = fixture()
    a['command.raw'][20] = 409
    a['command.normalized'][20] = 1
    d = self.derive(a)
    self.assertTrue(d['model_eligible'][20])
    self.assertEqual(d['streak_non_rail'][20], 0)
    self.assertEqual(d['streak_non_rail'][21], 1)

  def test_bridge_conflict(self):
    a = fixture()
    a['command.raw'][20] = 1
    with self.assertRaisesRegex(ValueError, 'BRIDGE'):
      self.derive(a)

  def test_future_message(self):
    for kind in ('state', 'command', 'control'):
      a = fixture()
      a[kind+'.time_ns'][20] += 1
      with self.subTest(kind=kind), self.assertRaisesRegex(ValueError, 'FUTURE'):
        self.derive(a)

  def test_source_age_integrity(self):
    a = fixture()
    a['command.age_ns'][20] = 1
    with self.assertRaisesRegex(ValueError, 'AGE'):
      self.derive(a)

  def test_stale_and_invalid(self):
    for kind in ('state', 'command', 'control'):
      for field, value in (('fresh', False), ('present', False), ('gap', True), ('event_valid', 0)):
        a = fixture()
        a[kind+'.'+field][20] = value
        with self.subTest(kind=kind, field=field):
          self.assertFalse(self.derive(a)['s2_ri_causal_valid'][20])

  def test_regression_clock(self):
    a = fixture()
    a['state.time_ns'][20] = a['state.time_ns'][18]
    a['state.age_ns'][20] = 20_000_000
    with self.assertRaisesRegex(ValueError, 'REGRESSION'):
      self.derive(a)

  def test_repeated_state_break(self):
    a = fixture()
    a['state.time_ns'][20] = a['state.time_ns'][19]
    a['state.age_ns'][20] = 10_000_000
    for kind in ('command', 'control'):
      a[kind+'.time_ns'][20] = a['state.time_ns'][20]
    d = self.derive(a)
    self.assertFalse(d['s2_ri_causal_valid'][20])
    self.assertEqual(d['streak_all'][21], 1)

  def test_grid_gap_break(self):
    a = fixture()
    a['grid_time_ns'][50:] += 10_000_000
    for kind in ('state', 'command', 'control'):
      a[kind+'.time_ns'] = a['grid_time_ns'].copy()
    d = self.derive(a)
    self.assertEqual(d['within_s2_ri_causal_run_index'][50], 0)
    self.assertEqual(d['streak_all'][50], 1)

  def test_unknown_not_false(self):
    a = fixture()
    a['state.driver_pressed'][20] = np.nan
    a['state.driver_pressed.available'][20] = False
    self.assertFalse(self.derive(a)['model_eligible'][20])

  def test_non_boolean_availability(self):
    a = fixture()
    a['state.angle_deg.available'] = np.ones(100)
    with self.assertRaises(ValueError):
      self.derive(a)

  def test_no_mutation(self):
    a = fixture()
    before = {k: v.tobytes() for k, v in a.items()}
    for v in a.values():
      v.flags.writeable = False
    self.derive(a)
    self.assertEqual(before, {k: v.tobytes() for k, v in a.items()})

  def test_model_firewall_synthetic_extraction(self):
    from unittest.mock import patch
    import builtins
    original_import = builtins.__import__
    def blocked_import(name, *args, **kwargs):
      if name.startswith(('scipy', 'sklearn')):
        raise AssertionError('OPTIMIZER_OR_MODEL_IMPORT')
      return original_import(name, *args, **kwargs)
    with patch.object(np.linalg, 'lstsq', side_effect=AssertionError('FITTING')), \
         patch.object(np, 'polyfit', side_effect=AssertionError('FITTING')), \
         patch.object(builtins, '__import__', side_effect=blocked_import):
      d = self.derive(fixture())
    self.assertTrue(d['model_eligible'].all())

  def test_all_required_availability_enforced(self):
    from openpilot.tools.cyber_autotune.empirical_s2_ri_admission import REQUIRED
    for field in REQUIRED:
      a = fixture()
      a[field+'.available'][20] = False
      with self.subTest(field=field):
        self.assertFalse(self.derive(a)['s2_ri_causal_valid'][20])

  def test_endpoint_never_crosses_fault_or_inactive(self):
    from openpilot.tools.cyber_autotune.empirical_s2_ri_math import target_indices
    a = fixture()
    a['control.lat_active'][20:30] = 0
    d = self.derive(a)
    ix = target_indices({'streak': d['streak_all']})
    self.assertFalse(np.isin(np.arange(19, 30), ix).any())

  def test_20ms_ceiling_no_relaxation(self):
    a = fixture()
    a['command.time_ns'] -= 20_000_001
    a['command.age_ns'][:] = 20_000_001
    self.assertFalse(self.derive(a)['s2_ri_causal_valid'].any())
