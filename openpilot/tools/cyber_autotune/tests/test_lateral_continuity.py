"""Preadmitted synthetic epochs only; not live/device Shadow qualification."""
import copy
import importlib
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

from openpilot.tools.cyber_autotune import a1_experiment
from openpilot.tools.cyber_autotune.native_protocol import canonical, digest
from openpilot.tools.cyber_autotune.native_runner import ProcessOutcome, _run_process
from openpilot.tools.cyber_autotune.native_worker import _execute_request


class TestLateralContinuity(unittest.TestCase):
  def setUp(self):
    name = 'openpilot.tools.cyber_autotune.lateral_continuity'
    self.assertIsNotNone(importlib.util.find_spec(name), 'State-preserving chunk execution is not implemented')
    self.api = importlib.import_module(name)
    self.request = self.api.build_request([150, 151, 300])
    self.native, _ = a1_experiment.make_fixture(self.request['fixture_request'])

  def check_failure(self, result, status, code):
    self.assertEqual(result, {'status': status, 'worker_returncode': code,
                             'request_sha256': digest(self.api.encode_request(self.request)),
                             **dict.fromkeys(a1_experiment.AUTHORITIES, False)})

  def test_one_shot_and_many_partitions_preserve_output_and_state(self):
    baseline = self.api.execute_experiment(self.api.build_request([601]))
    for sizes in ([1, 149, 151, 300], [20, 130, 10, 40, 10, 40, 10, 40, 10, 291], [1] * 601):
      with self.subTest(chunks=len(sizes)):
        request = self.api.build_request(sizes)
        result = self.api.execute_experiment(request)
        self.api.validate_response(request, result)
        self.assertEqual(result['comparison'], baseline['comparison'])
        self.assertEqual(result['comparison']['baseline'], result['comparison']['candidate'])
        self.assertEqual(len(result['chunks']), len(sizes))
        self.assertEqual(result['scope'], 'OFFLINE_PREADMITTED_LATERAL_EPOCH_ONLY')
        self.assertTrue(all(result[name] is False for name in a1_experiment.AUTHORITIES))

  def test_each_advance_executes_exactly_its_frames_without_precomputing(self):
    from openpilot.selfdrive.controls.lib.latcontrol_torque import LatControlTorque
    reference = _execute_request(self.native, _capture_state=True)
    calls = []
    update = LatControlTorque.update

    def counted(controller, *args, **kwargs):
      calls.append(1)
      return update(controller, *args, **kwargs)

    with patch.object(LatControlTorque, 'update', counted), self.api._TorqueChunkCursor(self.native) as cursor:
      self.assertEqual(len(calls), 0)
      first = cursor.advance(20)
      self.assertEqual(len(calls), 20)
      self.assertEqual(first['end_state_sha256'], reference['a1']['states'][19]['state_sha256'])
      second = cursor.advance(581)
      self.assertEqual(len(calls), 601)
      self.assertEqual(second['start_index'], 20)
      self.assertEqual(second['end_index_exclusive'], 601)
      self.assertEqual(cursor.finish(), reference)
      self.assertEqual(len(calls), 601)

  def test_reset_at_boundary_is_not_equivalent_to_continuation(self):
    continuous = _execute_request(self.native, _capture_state=True)
    split = 240
    fresh = _execute_request(dict(self.native, frames=self.native['frames'][split:]), _capture_state=True)
    expected = continuous['samples'][split:]
    self.assertTrue(any(old['requested_torque'] != new['requested_torque']
                        for old, new in zip(expected, fresh['samples'], strict=True)))
    self.assertNotEqual(continuous['a1']['states'][split], fresh['a1']['states'][0])
    with self.api._TorqueChunkCursor(self.native) as cursor:
      cursor.advance(split)
      cursor.advance(601 - split)
      self.assertEqual(cursor.finish(), continuous)

  def test_cursor_owns_an_input_copy_and_never_mutates_caller(self):
    original = copy.deepcopy(self.native)
    expected = _execute_request(original, _capture_state=True)
    with self.api._TorqueChunkCursor(self.native) as cursor:
      self.assertEqual(self.native, original)
      self.native['frames'][0]['speed_mps'] = 999.
      self.native['source']['files'].clear()
      cursor.advance(150)
      cursor.advance(451)
      self.assertEqual(cursor.finish(), expected)
    self.assertEqual(original['frames'][0]['speed_mps'], 0.)

  def test_invalid_advances_are_terminal_not_implicit_resets(self):
    for size in (0, -1, True, 1.5, 602, [], '1'):
      with self.subTest(size=size), self.api._TorqueChunkCursor(self.native) as cursor:
        cursor.advance(10)
        with self.assertRaises(ValueError):
          cursor.advance(size)
        with self.assertRaises(ValueError):
          cursor.advance(1)
        with self.assertRaises(ValueError):
          cursor.finish()

  def test_incomplete_finish_and_completed_epoch_cannot_resume(self):
    with self.api._TorqueChunkCursor(self.native) as cursor:
      cursor.advance(300)
      with self.assertRaises(ValueError):
        cursor.finish()
      with self.assertRaises(ValueError):
        cursor.advance(301)
    with self.api._TorqueChunkCursor(self.native) as fresh:
      fresh.advance(601)
      completed = fresh.finish()
      with self.assertRaises(ValueError):
        fresh.finish()
      with self.assertRaises(ValueError):
        fresh.advance(1)
    self.assertEqual(completed, _execute_request(self.native, _capture_state=True))

  def test_partial_close_restores_import_path_and_new_epoch_starts_fresh(self):
    before = list(sys.path)
    with self.api._TorqueChunkCursor(self.native) as cursor:
      cursor.advance(25)
    self.assertEqual(sys.path, before)
    with self.assertRaises(ValueError):
      cursor.advance(1)
    with self.api._TorqueChunkCursor(self.native) as fresh:
      fresh.advance(601)
      actual = fresh.finish()
    self.assertEqual(sys.path, before)
    self.assertEqual(actual, _execute_request(self.native, _capture_state=True))

  def test_native_failure_closes_cursor_and_returns_no_partial_success(self):
    self.native['frames'][25]['desired_curvature_1pm'] = 1e308
    before = list(sys.path)
    with self.api._TorqueChunkCursor(self.native) as cursor:
      cursor.advance(25)
      with self.assertRaises(ValueError):
        cursor.advance(1)
      with self.assertRaises(ValueError):
        cursor.advance(575)
      with self.assertRaises(ValueError):
        cursor.finish()
    self.assertEqual(sys.path, before)

  def test_nonuniform_epoch_time_is_rejected_before_execution(self):
    for delta in (-10_000_000, 1, 10_000_000):
      native = copy.deepcopy(self.native)
      native['frames'][150]['time_ns'] += delta
      with self.subTest(delta=delta), patch.object(self.api, '_request_steps') as steps:
        with self.assertRaises(ValueError):
          self.api._TorqueChunkCursor(native)
        steps.assert_not_called()

  def test_invalid_partitions_never_launch_a_worker(self):
    for sizes in ([], [600], [602], [601, 0], [True, 600], [1.0, 600], [1] * 602, '601', None):
      request = copy.deepcopy(self.request)
      request['chunk_sizes'] = sizes
      with self.subTest(sizes=str(sizes)[:35]), patch.object(self.api, '_run_process') as launch:
        with self.assertRaises(ValueError):
          self.api.run_experiment(request, timeout_s=5.)
        launch.assert_not_called()

  def test_public_contract_rejects_other_fixtures_extra_fields_and_bad_json(self):
    for mode in ('identity', 'factor', 'combined'):
      request = copy.deepcopy(self.request)
      request['fixture_request']['fixture'] = mode
      with self.subTest(mode=mode), self.assertRaises(ValueError):
        self.api.encode_request(request)
    for change in ({'version': True}, {'frames': []}, {'overlay': {}}):
      with self.assertRaises(ValueError):
        self.api.encode_request(dict(self.request, **change))
    for payload in (b'{"version":1,"version":1}', b'{"v":NaN}', b'[]', b'\xff'):
      with self.assertRaises(ValueError):
        self.api.decode_request(payload)

  def test_changed_source_overlay_blocks_before_worker_launch(self):
    request = copy.deepcopy(self.request)
    name = next(iter(request['overlay']))
    request['overlay'][name] = '0' * 64
    with patch.object(self.api, '_run_process') as launch:
      result = self.api.run_experiment(request, timeout_s=5.)
      launch.assert_not_called()
    self.assertEqual(result['status'], 'BINDING_REJECTED')
    self.assertIsNone(result['worker_returncode'])
    self.assertTrue(all(result[key] is False for key in a1_experiment.AUTHORITIES))
    self.assertNotIn('comparison', result)

  def test_chunk_response_and_authority_rebinding_are_rejected(self):
    original = self.api.execute_experiment(self.request)
    for field, value in (('start_index', 1), ('end_index_exclusive', 149), ('end_state_sha256', '0' * 64),
                         ('first_time_ns', 1), ('last_time_ns', True)):
      result = copy.deepcopy(original)
      result['chunks'][0][field] = value
      result['chunks_sha256'] = digest(canonical(result['chunks']))
      with self.subTest(field=field), self.assertRaises(ValueError):
        self.api.validate_response(self.request, result)
    for field in a1_experiment.AUTHORITIES:
      with self.subTest(field=field), self.assertRaises(ValueError):
        self.api.validate_response(self.request, dict(original, **{field: True}))
    rebound = self.api.build_request([601])
    with self.assertRaises(ValueError):
      self.api.validate_response(rebound, original)
    result = copy.deepcopy(original)
    result['comparison']['candidate']['a1']['states'][150]['pid_i'] += .1
    with self.assertRaises(ValueError):
      self.api.validate_response(self.request, result)

  def test_supervisor_failure_precedence_never_leaks_output(self):
    cases = (('TIMEOUT', -9, b'PRIVATE_SENTINEL', 'TIMEOUT'),
             ('TIMEOUT', 0, b'PRIVATE_SENTINEL', 'TIMEOUT'),
             ('EXITED', 7, b'PRIVATE_SENTINEL', 'WORKER_FAILED'),
             ('EXITED', 0, b'{"PRIVATE_SENTINEL":true}', 'INVALID_RESPONSE'))
    for transport, code, output, status in cases:
      with self.subTest(status=status, code=code), patch.object(
          self.api, '_run_process', return_value=ProcessOutcome(transport, code, output, 123)):
        self.check_failure(self.api.run_experiment(self.request, timeout_s=5.), status, code)
    with patch.object(self.api, '_run_process', side_effect=OSError('PRIVATE_SENTINEL')):
      self.check_failure(self.api.run_experiment(self.request, timeout_s=5.), 'WORKER_UNAVAILABLE', None)

  def test_supervisor_rechecks_source_after_execution(self):
    result = self.api.execute_experiment(self.request)
    outcome = ProcessOutcome('EXITED', 0, canonical(result), 123)
    with patch.object(self.api, '_run_process', return_value=outcome), patch.object(
        self.api, '_verify_bindings', side_effect=[None, ValueError('SOURCE_CHANGED')]):
      self.check_failure(self.api.run_experiment(self.request, timeout_s=5.), 'INVALID_RESPONSE', 0)

  def test_real_isolated_worker_matches_and_repeats(self):
    first = self.api.run_experiment(self.request, timeout_s=20.)
    second = self.api.run_experiment(self.request, timeout_s=20.)
    self.assertEqual(first['status'], self.api.PASS)
    self.assertEqual(canonical(first), canonical(second))
    self.assertEqual(first, self.api.execute_experiment(self.request))

  def test_real_timeout_cannot_be_success(self):
    result = self.api.run_experiment(self.request, timeout_s=.001)
    self.assertEqual(result['status'], 'TIMEOUT')
    self.assertIs(type(result['worker_returncode']), int)
    self.check_failure(result, 'TIMEOUT', result['worker_returncode'])

  def test_raw_worker_rejection_does_not_reflect_supplied_content(self):
    worker = Path(self.api.__file__).with_name('lateral_continuity_worker.py')
    outcome = _run_process([sys.executable, '-I', str(worker)], b'{"PRIVATE_SENTINEL":"raw-log"}', 10.)
    self.assertEqual((outcome.status, outcome.returncode), ('EXITED', 1))
    self.assertEqual(outcome.stdout.strip(), canonical({'status': 'REJECTED', 'code': 'INVALID_OR_FAILED_CONTINUITY_REQUEST'}))


if __name__ == '__main__':
  unittest.main()
