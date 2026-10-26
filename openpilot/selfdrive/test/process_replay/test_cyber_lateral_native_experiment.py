from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from openpilot.cereal import messaging
from openpilot.selfdrive.test.process_replay import cyber_lateral_native_experiment as native_experiment
from openpilot.selfdrive.test.process_replay.cyber_lateral_native_experiment import (
  ExperimentIdentity,
  NativeOutputSummary,
  build_a3_messages,
  compare_native_outputs,
  main,
  run_native_experiment,
  summarize_native_outputs,
  validate_experiment_identity,
)


TEST_DEVELOPMENT_SEGMENT = 'development-route--fixture--29'


class TestDevelopmentManifest(unittest.TestCase):
  def test_accepts_only_explicit_development_entries_and_resolves_relative_paths(self):
    with tempfile.TemporaryDirectory() as temporary_directory:
      root = Path(temporary_directory)
      rlog = root / 'logs' / 'route--7' / 'rlog.zst'
      rlog.parent.mkdir(parents=True)
      rlog.write_bytes(b'development-input')
      manifest = root / 'development.json'
      manifest.write_text(json.dumps({
        'schema_version': 1,
        'role': 'development',
        'authority': {'holdout_opened': False, 'validation_opened': False},
        'entries': [{
          'route_segment': 'route--7',
          'rlog': 'logs/route--7/rlog.zst',
          'rlog_sha256': hashlib.sha256(rlog.read_bytes()).hexdigest(),
        }],
      }), encoding='utf-8')

      self.assertTrue(hasattr(native_experiment, 'load_development_manifest'))
      entries = native_experiment.load_development_manifest(manifest)

      self.assertEqual(entries, (native_experiment.DevelopmentReplayInput(
        'route--7', rlog.resolve(), hashlib.sha256(rlog.read_bytes()).hexdigest(),
      ),))

      document = json.loads(manifest.read_text(encoding='utf-8'))
      document['role'] = 'holdout'
      manifest.write_text(json.dumps(document), encoding='utf-8')
      with self.assertRaisesRegex(RuntimeError, 'development'):
        native_experiment.load_development_manifest(manifest)

  def test_rejects_opened_validation_and_entry_whose_parent_does_not_match_identity(self):
    with tempfile.TemporaryDirectory() as temporary_directory:
      root = Path(temporary_directory)
      rlog = root / 'logs' / 'wrong-parent' / 'rlog.zst'
      rlog.parent.mkdir(parents=True)
      rlog.write_bytes(b'development-input')
      manifest = root / 'development.json'
      document = {
        'schema_version': 1,
        'role': 'development',
        'authority': {'holdout_opened': False, 'validation_opened': True},
        'entries': [{
          'route_segment': 'route--7',
          'rlog': 'logs/wrong-parent/rlog.zst',
          'rlog_sha256': hashlib.sha256(rlog.read_bytes()).hexdigest(),
        }],
      }
      manifest.write_text(json.dumps(document), encoding='utf-8')
      with self.assertRaisesRegex(RuntimeError, 'unopened'):
        native_experiment.load_development_manifest(manifest)

      document['authority']['validation_opened'] = False
      manifest.write_text(json.dumps(document), encoding='utf-8')
      with self.assertRaisesRegex(RuntimeError, 'parent'):
        native_experiment.load_development_manifest(manifest)


class TestNativeOutputSummary(unittest.TestCase):
  def test_counts_and_discards_sendcan_while_hashing_only_car_output(self):
    car_output = messaging.new_message('carOutput')
    car_output.logMonoTime = 10
    car_output.carOutput.actuatorsOutput.torque = 0.25
    car_output.carOutput.actuatorsOutput.torqueOutputCan = 96
    car_output.carOutput.actuatorsOutput.steeringAngleDeg = 1.5
    sendcan = messaging.new_message('sendcan', 0)

    summary = summarize_native_outputs((sendcan.as_reader(), car_output.as_reader()))

    self.assertEqual(summary.car_output_count, 1)
    self.assertEqual(summary.sendcan_count_discarded, 1)
    self.assertEqual(summary.rows, ((10, 0.25, 96, 1.5),))
    self.assertEqual(summary.ordered_sha256, '2d2e6672016502fa3f3a75664c4f461acb9009e619fe3621771a8908d609c2e3')

  def test_compares_aligned_native_outputs_without_claiming_plant_metrics(self):
    baseline = NativeOutputSummary(
      rows=((1, 0.0, 0, 0.0), (2, 0.01, 4, 0.0)),
      ordered_sha256='baseline',
      sendcan_count_discarded=2,
    )
    candidate = NativeOutputSummary(
      rows=((1, 0.0, 0, 0.0), (2, 0.005, 2, 0.0)),
      ordered_sha256='candidate',
      sendcan_count_discarded=2,
    )

    comparison = compare_native_outputs(baseline, candidate)

    self.assertEqual(comparison['changed_raw_output_count'], 1)
    self.assertEqual(comparison['changed_raw_output_ratio'], 0.5)
    self.assertEqual(comparison['raw_candidate_minus_baseline']['max_abs'], 2.0)
    self.assertAlmostEqual(comparison['baseline_normalized_torque_derivative_per_s']['rms'], 1.0)
    self.assertAlmostEqual(comparison['candidate_normalized_torque_derivative_per_s']['rms'], 0.5)
    self.assertEqual(comparison['baseline_saturation_ratio'], 0.0)
    self.assertEqual(comparison['candidate_saturation_ratio'], 0.0)

    misaligned = NativeOutputSummary(
      rows=((3, 0.0, 0, 0.0), (4, 0.005, 2, 0.0)),
      ordered_sha256='misaligned',
      sendcan_count_discarded=2,
    )
    with self.assertRaisesRegex(RuntimeError, 'timestamp'):
      compare_native_outputs(baseline, misaligned)


class TestExperimentIdentity(unittest.TestCase):
  def test_accepts_only_exact_clean_head_segment_and_content_hash(self):
    with tempfile.TemporaryDirectory() as temporary_directory:
      root = Path(temporary_directory)
      rlog = root / TEST_DEVELOPMENT_SEGMENT / 'rlog.zst'
      rlog.parent.mkdir()
      rlog.write_bytes(b'approved-segment-29-fixture')
      subprocess.run(('git', 'init', '-q', str(root)), check=True)
      subprocess.run(('git', '-C', str(root), 'config', 'user.name', 'Cyber Test'), check=True)
      subprocess.run(('git', '-C', str(root), 'config', 'user.email', 'cyber-test@example.invalid'), check=True)
      subprocess.run(('git', '-C', str(root), 'add', '.'), check=True)
      subprocess.run(('git', '-C', str(root), 'commit', '-qm', 'fixture'), check=True)
      expected_head = subprocess.check_output(('git', '-C', str(root), 'rev-parse', 'HEAD'), text=True).strip()
      expected_sha256 = hashlib.sha256(rlog.read_bytes()).hexdigest()

      identity = validate_experiment_identity(
        root, rlog, expected_head, expected_sha256,
        approved_route_segment=TEST_DEVELOPMENT_SEGMENT,
      )

      self.assertEqual(identity.cyber_head, expected_head)
      self.assertEqual(identity.route_segment, TEST_DEVELOPMENT_SEGMENT)
      self.assertEqual(identity.rlog_sha256, expected_sha256)

      (root / 'dirty.txt').write_text('dirty', encoding='utf-8')
      with self.assertRaisesRegex(RuntimeError, 'clean'):
        validate_experiment_identity(
          root, rlog, expected_head, expected_sha256,
          approved_route_segment=TEST_DEVELOPMENT_SEGMENT,
        )

  def test_accepts_only_the_route_segment_selected_from_a_development_manifest(self):
    with tempfile.TemporaryDirectory() as temporary_directory:
      root = Path(temporary_directory)
      route_segment = 'development-route--7'
      rlog = root / route_segment / 'rlog.zst'
      rlog.parent.mkdir()
      rlog.write_bytes(b'frozen-development-fixture')
      subprocess.run(('git', 'init', '-q', str(root)), check=True)
      subprocess.run(('git', '-C', str(root), 'config', 'user.name', 'Cyber Test'), check=True)
      subprocess.run(('git', '-C', str(root), 'config', 'user.email', 'cyber-test@example.invalid'), check=True)
      subprocess.run(('git', '-C', str(root), 'add', '.'), check=True)
      subprocess.run(('git', '-C', str(root), 'commit', '-qm', 'fixture'), check=True)
      expected_head = subprocess.check_output(('git', '-C', str(root), 'rev-parse', 'HEAD'), text=True).strip()
      expected_sha256 = hashlib.sha256(rlog.read_bytes()).hexdigest()

      try:
        identity = validate_experiment_identity(
          root, rlog, expected_head, expected_sha256,
          approved_route_segment=route_segment,
        )
      except TypeError as error:
        self.fail(f'development identity selection is not implemented: {error}')

      self.assertEqual(identity.route_segment, route_segment)
      with self.assertRaisesRegex(RuntimeError, 'approved development'):
        validate_experiment_identity(
          root, rlog, expected_head, expected_sha256,
          approved_route_segment='different-route--8',
        )


class TestA3InputTransformation(unittest.TestCase):
  def test_uses_fixed_384_raw_rate_contract_and_resets_for_each_run(self):
    car_state = messaging.new_message('carState')
    car_state.logMonoTime = 1
    car_state.carState.vEgo = 5.0
    car_output = messaging.new_message('carOutput')
    car_output.logMonoTime = 2
    car_output.carOutput.actuatorsOutput.torque = 0.0
    car_output.carOutput.actuatorsOutput.torqueOutputCan = 0
    first_control = messaging.new_message('carControl')
    first_control.logMonoTime = 3
    first_control.carControl.actuators.torque = 1.0
    second_control = messaging.new_message('carControl')
    second_control.logMonoTime = 4
    second_control.carControl.actuators.torque = 1.0
    messages = tuple(message.as_reader() for message in (car_state, car_output, first_control, second_control))

    first_messages, first_summary = build_a3_messages(messages)
    second_messages, second_summary = build_a3_messages(messages)

    self.assertAlmostEqual(first_messages[2].carControl.actuators.torque, 3 / 384)
    self.assertAlmostEqual(first_messages[3].carControl.actuators.torque, 6 / 384)
    self.assertEqual(first_summary.evaluated_car_control_count, 2)
    self.assertEqual(first_summary.changed_car_control_count, 2)
    self.assertEqual(first_summary, second_summary)
    self.assertEqual(
      tuple(message.carControl.actuators.torque for message in first_messages[2:]),
      tuple(message.carControl.actuators.torque for message in second_messages[2:]),
    )
    self.assertEqual(first_control.carControl.actuators.torque, 1.0)
    self.assertEqual(second_control.carControl.actuators.torque, 1.0)


class TestNativeExperimentOrchestration(unittest.TestCase):
  @staticmethod
  def messages():
    car_state = messaging.new_message('carState')
    car_state.logMonoTime = 1
    car_state.carState.vEgo = 5.0
    car_output = messaging.new_message('carOutput')
    car_output.logMonoTime = 2
    car_output.carOutput.actuatorsOutput.torqueOutputCan = 0
    controls = []
    for timestamp in (3, 4):
      control = messaging.new_message('carControl')
      control.logMonoTime = timestamp
      control.carControl.actuators.torque = 1.0
      controls.append(control)
    return tuple(message.as_reader() for message in (car_state, car_output, *controls))

  @staticmethod
  def replay(messages):
    commands = [float(message.carControl.actuators.torque) for message in messages if message.which() == 'carControl']
    outputs = []
    for timestamp, command in zip((10, 20), commands, strict=True):
      output = messaging.new_message('carOutput')
      output.logMonoTime = timestamp
      output.carOutput.actuatorsOutput.torque = command
      output.carOutput.actuatorsOutput.torqueOutputCan = round(command * 384)
      outputs.append(output.as_reader())
    outputs.append(messaging.new_message('sendcan', 0).as_reader())
    return tuple(outputs)

  def test_a0_and_a3_are_repeatable_aggregate_only_reports(self):
    identity = ExperimentIdentity('a' * 40, TEST_DEVELOPMENT_SEGMENT, 'b' * 64)

    a0 = run_native_experiment(self.messages(), 'A0', identity, self.replay)
    a3 = run_native_experiment(self.messages(), 'A3', identity, self.replay)

    self.assertEqual(a0['state'], 'STEP7_NATIVE_A0_REPEATABLE')
    self.assertTrue(a0['native_replay']['runs_identical'])
    self.assertEqual(a0['native_replay']['car_output_count'], 2)
    self.assertEqual(a0['native_replay']['run_1_sendcan_count_discarded'], 1)
    self.assertEqual(a3['state'], 'STEP7_NATIVE_A3_REPEATABLE_NOT_PERFORMANCE_QUALIFIED')
    self.assertTrue(a3['native_replay']['a3_runs_identical'])
    self.assertEqual(a3['preprocessing']['changed_car_control_count'], 2)
    self.assertEqual(a3['comparison']['changed_raw_output_count'], 2)
    for report in (a0, a3):
      self.assertFalse(report['decision']['performance_pass'])
      self.assertFalse(report['decision']['promote_to_active_control'])
      self.assertFalse(report['authority']['sendcan_forwarded'])
      self.assertFalse(report['authority']['live_can'])
      self.assertFalse(report['authority']['vehicle_write'])

    with self.assertRaisesRegex(ValueError, 'A0 or A3'):
      run_native_experiment(self.messages(), 'A1', identity, self.replay)

  def test_sendcan_count_difference_fails_repeatability(self):
    identity = ExperimentIdentity('a' * 40, TEST_DEVELOPMENT_SEGMENT, 'b' * 64)
    call_count = 0

    def inconsistent_replay(messages):
      nonlocal call_count
      call_count += 1
      outputs = list(self.replay(messages))
      if call_count == 2:
        outputs.append(messaging.new_message('sendcan', 0).as_reader())
      return tuple(outputs)

    report = run_native_experiment(self.messages(), 'A0', identity, inconsistent_replay)

    self.assertEqual(report['state'], 'STEP7_NATIVE_A0_NONREPEATABLE')
    self.assertFalse(report['decision']['repeatability_pass'])

  def test_cli_selects_an_exact_entry_from_an_external_development_manifest(self):
    with tempfile.TemporaryDirectory() as temporary_directory:
      workspace = Path(temporary_directory)
      root = workspace / 'source'
      root.mkdir()
      route_segment = 'development-route--7'
      rlog = workspace / 'logs' / route_segment / 'rlog.zst'
      rlog.parent.mkdir(parents=True)
      rlog.write_bytes(b'frozen-development-cli-fixture')
      subprocess.run(('git', 'init', '-q', str(root)), check=True)
      subprocess.run(('git', '-C', str(root), 'config', 'user.name', 'Cyber Test'), check=True)
      subprocess.run(('git', '-C', str(root), 'config', 'user.email', 'cyber-test@example.invalid'), check=True)
      (root / 'tracked.txt').write_text('fixture', encoding='utf-8')
      subprocess.run(('git', '-C', str(root), 'add', '.'), check=True)
      subprocess.run(('git', '-C', str(root), 'commit', '-qm', 'fixture'), check=True)
      expected_head = subprocess.check_output(('git', '-C', str(root), 'rev-parse', 'HEAD'), text=True).strip()
      expected_sha256 = hashlib.sha256(rlog.read_bytes()).hexdigest()
      manifest = workspace / 'development.json'
      manifest.write_text(json.dumps({
        'schema_version': 1,
        'role': 'development',
        'authority': {'holdout_opened': False, 'validation_opened': False},
        'entries': [{
          'route_segment': route_segment,
          'rlog': str(rlog),
          'rlog_sha256': expected_sha256,
        }],
      }), encoding='utf-8')
      output_path = workspace / 'aggregate.json'

      try:
        exit_code = main([
          '--cyber-root', str(root),
          '--development-manifest', str(manifest),
          '--route-segment', route_segment,
          '--expected-cyber-head', expected_head,
          '--variant', 'A0',
          '--output', str(output_path),
        ], load_messages=lambda _path: self.messages(), replay=self.replay)
      except SystemExit as error:
        self.fail(f'development manifest CLI is not implemented: {error}')

      report = json.loads(output_path.read_text(encoding='utf-8'))
      self.assertEqual(exit_code, 0)
      self.assertEqual(report['identity']['route_segment'], route_segment)
      self.assertEqual(report['identity']['rlog_sha256'], expected_sha256)

  def test_cli_validates_identity_and_emits_json_without_raw_messages(self):
    with tempfile.TemporaryDirectory() as temporary_directory:
      root = Path(temporary_directory)
      rlog = root / TEST_DEVELOPMENT_SEGMENT / 'rlog.zst'
      rlog.parent.mkdir()
      rlog.write_bytes(b'approved-segment-29-cli-fixture')
      subprocess.run(('git', 'init', '-q', str(root)), check=True)
      subprocess.run(('git', '-C', str(root), 'config', 'user.name', 'Cyber Test'), check=True)
      subprocess.run(('git', '-C', str(root), 'config', 'user.email', 'cyber-test@example.invalid'), check=True)
      subprocess.run(('git', '-C', str(root), 'add', '.'), check=True)
      subprocess.run(('git', '-C', str(root), 'commit', '-qm', 'fixture'), check=True)
      expected_head = subprocess.check_output(('git', '-C', str(root), 'rev-parse', 'HEAD'), text=True).strip()
      expected_sha256 = hashlib.sha256(rlog.read_bytes()).hexdigest()
      stdout = io.StringIO()
      with tempfile.TemporaryDirectory() as output_directory:
        output_path = Path(output_directory) / 'aggregate.json'
        with redirect_stdout(stdout):
          exit_code = main([
            '--cyber-root', str(root),
            '--rlog', str(rlog),
            '--route-segment', TEST_DEVELOPMENT_SEGMENT,
            '--expected-cyber-head', expected_head,
            '--expected-rlog-sha256', expected_sha256,
            '--variant', 'A0',
            '--output', str(output_path),
          ], load_messages=lambda _path: self.messages(), replay=self.replay)

        report = json.loads(stdout.getvalue())
        self.assertEqual(json.loads(output_path.read_text(encoding='utf-8')), report)
        self.assertEqual(exit_code, 0)
        self.assertEqual(report['state'], 'STEP7_NATIVE_A0_REPEATABLE')
        self.assertEqual(report['identity']['rlog_sha256'], expected_sha256)
        self.assertNotIn('rows', report['native_replay'])

      with self.assertRaisesRegex(RuntimeError, 'outside'):
        main([
          '--cyber-root', str(root),
          '--rlog', str(rlog),
          '--route-segment', TEST_DEVELOPMENT_SEGMENT,
          '--expected-cyber-head', expected_head,
          '--expected-rlog-sha256', expected_sha256,
          '--variant', 'A0',
          '--output', str(root / 'must-not-dirty-source.json'),
        ], load_messages=lambda _path: self.messages(), replay=self.replay)


if __name__ == '__main__':
  unittest.main()
