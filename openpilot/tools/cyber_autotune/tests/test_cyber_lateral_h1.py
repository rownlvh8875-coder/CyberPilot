"""Synthetic-only H1 boundary tests. No raw log reader or device."""

from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import cyber_lateral_h1_contract as c
from openpilot.tools.cyber_autotune import cyber_lateral_h1_producer as h

SHA = 'a' * 64


def fixture(count=3):
  config = {'native_core_identity_sha256': SHA, 'governor': 'DISABLED'}
  configs = [{'process_epoch': 1, 'config_sequence': 1, 'config': config, 'config_sha256': p.sha(p.canonical(config))}]
  binding = c.binding(SHA, c.policy()['source_sha256'], count)
  rows = []
  for i in range(count):
    native = {
      'desired_curvature_1pm': 0.0,
      'actual_curvature_1pm': 0.0,
      'speed_mps': 20.0,
      'roll_rad': 0.0,
      'time_s': i * 0.01,
      'dt_s': 0.01,
      'active': True,
      'steering_pressed': False,
      'safety_limited': False,
      'curvature_limited': False,
    }
    rows.append(
      h.make_row(
        binding,
        configs[0],
        i,
        native,
        0.0,
        0.0,
        {'curvature': 0.0, 'yaw_rate': 0.0, 'heading': 0.0, 'pose_x': float(i), 'pose_y': 0.0},
        ['EXPERIMENT_START'] if i == 0 else [],
      )
    )
  return binding, configs, rows


def package():
  b, cs, rows = fixture()
  producer = h.Producer(c.policy(), b, cs)
  for row in rows:
    producer.append(row)
  return producer.finish()


def reseal(row):
  row['row_sha256'] = h.row_sha(row)
  return row


class TestH1Producer(unittest.TestCase):
  def test_schema(self):
    row = package()
    self.assertEqual(h.verify_package(row), row)
    self.assertEqual(row['row_count'], 3)

  def rejected(self, mutate):
    b, cs, rows = fixture()
    mutate(rows)
    for row in rows:
      reseal(row)
    with self.assertRaises(ValueError):
      producer = h.Producer(c.policy(), b, cs)
      for row in rows:
        producer.append(row)
      producer.finish()

  def test_extra_field(self):
    self.rejected(lambda r: r[0].update(extra=1))

  def test_missing_field(self):
    self.rejected(lambda r: r[0].pop('event'))

  def test_duplicate_loop(self):
    self.rejected(lambda r: r[1].update(loop_sequence=1))

  def test_missing_row(self):
    self.rejected(lambda r: r.pop(1))

  def test_missing_first(self):
    self.rejected(lambda r: r.pop(0))

  def test_missing_final(self):
    self.rejected(lambda r: r.pop())

  def test_decreasing_capture(self):
    self.rejected(lambda r: r[1].update(capture_time_ns=0))

  def test_capture_must_precede_decision(self):
    self.rejected(lambda r: r[0].update(decision_time_ns=0))

  def test_cross_loop_decision(self):
    self.rejected(lambda r: r[0].update(decision_time_ns=c.DT_NS + 1))

  def test_source_drift(self):
    self.rejected(lambda r: r[0].update(source_sha256='b' * 64))

  def test_config_drift(self):
    self.rejected(lambda r: r[0].update(config_sha256='b' * 64))

  def test_config_sequence_skip(self):
    self.rejected(lambda r: r[1].update(config_sequence=3, event='CONFIG_CHANGE'))

  def test_snapshot_drift(self):
    self.rejected(lambda r: r[0]['consumed_input_snapshot']['native_input'].update(speed_mps=21.0))

  def test_snapshot_has_no_outputs(self):
    self.assertEqual(set(package()['rows'][0]['consumed_input_snapshot']), {'native_input', 'source_time_ns', 'service_health'})

  def test_native_input_digest(self):
    row = package()['rows'][0]
    self.assertEqual(row['native_input_sha256'], p.sha(p.canonical(row['consumed_input_snapshot']['native_input'])))

  def test_null_missing(self):
    row = package()['rows'][0]
    for field in c.UNAVAILABLE:
      self.assertIsNone(row['signals'][field])
      self.assertEqual(row['unavailable'][field], c.UNAVAILABLE[field])

  def test_zero_fabrication(self):
    self.rejected(lambda r: r[0]['signals'].update(torqueOutputCan=0.0))

  def test_false_fabrication(self):
    self.rejected(lambda r: r[0]['service_health']['carState'].update(valid=False))

  def test_missing_reason(self):
    self.rejected(lambda r: r[0]['unavailable'].update(steering_rate_deg_s=''))

  def test_desired_independent_reference_rejected(self):
    self.rejected(lambda r: r[0]['provenance'].update(desired_curvature='INDEPENDENT_REFERENCE'))

  def test_can_physical_ack_rejected(self):
    self.rejected(lambda r: r[0]['provenance'].update(torqueOutputCan='EPS_ACKNOWLEDGED'))

  def test_nonfinite(self):
    b, cs, rows = fixture()
    rows[0]['signals']['speed_mps'] = float('inf')
    with self.assertRaises(ValueError):
      h.Producer(c.policy(), b, cs).append(rows[0])

  def test_wrong_stage(self):
    self.rejected(lambda r: r[0]['signals'].update(post_governor_torque=0.5))

  def test_pre_post_time_not_mixed(self):
    self.rejected(lambda r: r[0]['plant_output'].update(state_time_ns=0))

  def test_input_signal_binding(self):
    self.rejected(lambda r: r[0]['signals'].update(actual_curvature=0.2))

  def test_future_source(self):
    self.rejected(lambda r: r[0]['consumed_input_snapshot'].update(source_time_ns=1))

  def test_epoch_restart(self):
    b, cs, rows = fixture()
    cs.append({**cs[0], 'process_epoch': 2})
    for i in (1, 2):
      rows[i].update(process_epoch=2, loop_sequence=i)
    rows[1]['event'] = 'SCENARIO_BOUNDARY'
    rows[1]['reset_events'] = ['EXPERIMENT_START']
    producer = h.Producer(c.policy(), b, cs)
    for row in rows:
      producer.append(reseal(row))
    self.assertEqual(producer.finish()['row_count'], 3)

  def test_epoch_without_boundary(self):
    self.rejected(lambda r: r[1].update(process_epoch=2, loop_sequence=1))

  def test_config_change(self):
    b, cs, rows = fixture()
    conf = {'native_core_identity_sha256': SHA, 'governor': 'DISABLED', 'label': 'synthetic-config-test'}
    cs.append({'process_epoch': 1, 'config_sequence': 2, 'config': conf, 'config_sha256': p.sha(p.canonical(conf))})
    for i in (1, 2):
      rows[i].update(config_sequence=2, config_sha256=cs[1]['config_sha256'])
    rows[1]['event'] = 'CONFIG_CHANGE'
    producer = h.Producer(c.policy(), b, cs)
    for row in rows:
      producer.append(reseal(row))
    self.assertEqual(producer.finish()['configs'], cs)

  def test_configs_digest(self):
    b, cs, _ = fixture()
    cs[0]['config']['governor'] = 'ENABLED'
    with self.assertRaises(ValueError):
      h.Producer(c.policy(), b, cs)

  def test_caller_mutation_detached(self):
    b, cs, rows = fixture()
    producer = h.Producer(c.policy(), b, cs)
    before = deepcopy(rows)
    for row in rows:
      producer.append(row)
    rows[0]['signals']['speed_mps'] = 99.0
    self.assertEqual(producer.finish()['rows'], before)

  def test_append_after_finish(self):
    b, cs, rows = fixture()
    producer = h.Producer(c.policy(), b, cs)
    for row in rows:
      producer.append(row)
    producer.finish()
    with self.assertRaises(ValueError):
      producer.append(rows[0])

  def test_finish_repeatable(self):
    self.assertEqual(p.canonical(package()), p.canonical(package()))

  def test_fidelity_ceiling(self):
    b, cs, _ = fixture()
    b['tier'] = 'T2_EMPIRICAL_PLANT_CLOSED_LOOP'
    with self.assertRaises(ValueError):
      h.Producer(c.policy(), b, cs)

  def test_no_private_input_class(self):
    b, cs, _ = fixture()
    b['data_class'] = 'PRIVATE_LOG'
    with self.assertRaises(ValueError):
      h.Producer(c.policy(), b, cs)

  def test_policy_drift(self):
    b, cs, _ = fixture()
    policy = c.policy()
    policy['dt_ns'] = 1
    with self.assertRaises(ValueError):
      h.Producer(policy, b, cs)

  def test_immutable_persistence(self):
    with tempfile.TemporaryDirectory() as folder:
      row = package()
      h.persist(folder, row)
      path = Path(folder) / h.FILENAME
      data = path.read_bytes()
      h.persist(folder, row)
      self.assertEqual(path.read_bytes(), data)
      altered = deepcopy(row)
      altered['rows'][0]['event'] = 'INACTIVE'
      with self.assertRaises(ValueError):
        h.persist(folder, altered)
      self.assertEqual(path.read_bytes(), data)

  def test_symlink_store(self):
    with tempfile.TemporaryDirectory() as folder:
      path = Path(folder) / 'alias'
      path.symlink_to(folder, target_is_directory=True)
      with self.assertRaises(ValueError):
        h.persist(path, package())

  def test_repo_store_rejected(self):
    with self.assertRaises(ValueError):
      h.persist(p.PUBLIC, package())

  def test_event_without_transition(self):
    self.rejected(lambda r: r[1].update(event='RELEASE', reset_events=['RELEASE']))

  def test_reset_event_missing(self):
    self.rejected(lambda r: r[0].update(reset_events=[]))

  def test_binding_source_drift(self):
    b, cs, _ = fixture()
    b['source_sha256'] = SHA
    with self.assertRaises(ValueError):
      h.Producer(c.policy(), b, cs)

  def test_trace_target_symlink_no_open(self):
    with tempfile.TemporaryDirectory() as folder:
      path = Path(folder) / h.FILENAME
      path.symlink_to('/forbidden/raw/rlog')
      with self.assertRaises(ValueError):
        h.persist(folder, package())

  def test_row_digest(self):
    row = package()
    row['rows'][0]['signals']['speed_mps'] = 2.0
    with self.assertRaises(ValueError):
      h.verify_package(row)

  def test_dotdot_repo_store_rejected(self):
    with self.assertRaisesRegex(ValueError, 'H1_STORE_OUTSIDE'):
      h.store_path(Path('/tmp/..') / p.PUBLIC.parents[2].relative_to('/') / 'new-store')

  def test_dotdot_raw_root_rejected(self):
    with self.assertRaisesRegex(ValueError, 'H1_STORE_OUTSIDE'):
      h.store_path(Path('/tmp/..') / 'mnt' / 'd' / ('carrot' + 'log') / 'new-store')
