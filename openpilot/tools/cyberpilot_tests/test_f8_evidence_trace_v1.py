"""Analytic row controls. These authored fixtures are not the historical F8 runs."""

from copy import deepcopy
import math
import unittest

from tools.cyberpilot import offline_multiobjective_gates_v1 as g
from tools.cyberpilot.f8_evidence_reader_v1 import F8Error
from tools.cyberpilot.f8_evidence_validation_v1 import fresh_native, verify_trace


def fixture(arm='A0', mode='NO_EXPLICIT_RESET'):
  initial = {'curvature_1pm': 0.0, 'yaw_rate_rad_s': 0.0, 'heading_rad': 0.05, 'x_m': 0.0, 'y_m': 0.0, 'command_history': [0.0, 0.0], 'applied_last': -0.05}
  inputs = [
    {
      'sequence': n,
      'time_ns': n * g.TIME_NS,
      'speed_mps': 7.5,
      'desired_curvature_1pm': 0.001,
      'roll_rad': 0.0,
      'noise_unit': 0.0,
      'active': True,
      'steering_pressed': False,
    }
    for n in range(8)
  ]
  reset = 3 if mode != 'NO_EXPLICIT_RESET' else None
  spec = {
    'dt_s': 0.01,
    'performance_qualified': False,
    'frames': inputs,
    'initial': initial,
    'reset_sequence': reset,
    'measurement': {
      'unit': 'm^-1',
      'coordinate': 'plant_curvature_positive_yaw_negative',
      'bias': 0.0,
      'noise_amplitude': 0.0,
      'delay_steps': 0,
      'variable_delay': False,
      'max_age_ns': 40000000,
    },
  }
  identity = {'role': 'UNCHANGED_NATIVE_BASELINE', 'source_sha256': 's', 'config_sha256': 'c'}
  state = {'candidate': None, 'physical': initial, 'native': fresh_native('EXPERIMENT_START'), 'reference_pose': [0.0, 0.0, 0.0]}
  item = {
    'arm': arm,
    'frames': 8,
    'source_sha256': 'fixture',
    'plant': g.PLANT,
    'status': 'EXECUTED_DIAGNOSTIC_ONLY',
    'native_identity': identity,
    'calls': {'native_update': 8, 'stock_update': 8, 'plant_step': 8},
    'initial_state': deepcopy(state),
    'initial_state_sha256': g.sha(g.canonical(state)),
    'input_sha256': g.sha(g.canonical(spec)),
  }
  item['calls']['governor' if arm == 'SG-A' else 'optimizer'] = 8
  rows, queue, pose, reference = [], [0.0, 0.0], [0.0, 0.0, 0.05], [0.0, 0.0, 0.0]
  k = yaw = 0.0
  ns, sg, rate = fresh_native('EXPERIMENT_START'), None, None
  prior, applied_before = '0' * 64, -0.05
  for n, f in enumerate(inputs):
    if n == reset:
      ns, rate = fresh_native('SCENARIO_BOUNDARY'), None
      if mode == 'RESET_MODE_B':
        sg = None
    events = ['EXPERIMENT_START'] if n == 0 else ['CONTROLLER_RESET'] if n == reset else []
    ni = {
      'desired_curvature_1pm': 0.001,
      'actual_curvature_1pm': k,
      'speed_mps': 7.5,
      'roll_rad': 0.0,
      'time_s': n * 0.01,
      'dt_s': 0.01,
      'active': True,
      'steering_pressed': False,
      'safety_limited': False,
      'curvature_limited': False,
    }
    native = 0.2 if n < 3 else -0.2
    if events:
      rate = None
    before_rate = rate
    if arm == 'SG-A':
      gs = ['EXPERIMENT_START'] if n == 0 or n == reset and mode == 'RESET_MODE_B' else []
      before_sg = sg
      command = native if gs or sg is None else max(sg - 1, min(sg + 1, native))
      sg = command
      src = {
        'state_before': before_sg,
        'state_after': sg,
        'reset_events': gs,
        'state_owner': 'SG',
        'physical_delay_owner': 'PLANT',
        'core_source_sha256': 's',
        'core_config_sha256': 'c',
        'action': 'FRESH_CURRENT_COMMAND_REBASE' if gs else 'UNITY_PASSTHROUGH',
      }
    else:
      command = g.rate_step(native, applied_before if rate is None else rate) if arm == 'A3' else native
      rate = command if arm == 'A3' else None
      src = {
        'valid': True,
        'variant': arm,
        'live_actuator_authority': False,
        'execution_stage': 'offline_only',
        'baseline_command': native,
        'candidate_command': command,
      }
    pb, posb = {'curvature_1pm': k, 'yaw_rate_rad_s': yaw, 'command_history': list(queue)}, list(pose)
    delayed = queue.pop(0)
    queue.append(-command)
    knew = 0.92 * k + 0.004 * delayed + 0.0002 * delayed * 7.5 + 0.002 * delayed / 7.5
    ynew = -knew * 7.5 + 0.75 * (yaw + k * 7.5)
    heading = pose[2] + ynew * 0.01
    pose = [pose[0] + 7.5 * math.cos(heading) * 0.01, pose[1] + 7.5 * math.sin(heading) * 0.01, heading]
    rh = reference[2] - 0.001 * 7.5 * 0.01
    reference = [reference[0] + 7.5 * math.cos(rh) * 0.01, reference[1] + 7.5 * math.sin(rh) * 0.01, rh]
    after = deepcopy(ns)
    after.update(prior_input=ni, pending_events=[])
    r = {
      'sequence': n,
      'time_ns': n * g.TIME_NS,
      'source_sha256': 'fixture',
      'input': f,
      'native_input': ni,
      'measurement': {
        'packet_sequence': n,
        'acquisition_sequence': n,
        'acquisition_time_ns': n * g.TIME_NS,
        'receive_time_ns': n * g.TIME_NS,
        'age_ns': 0,
        'priming': False,
        'raw_curvature_1pm': k,
        'curvature_1pm': k,
        'noise_1pm': 0.0,
        'bias_1pm': 0.0,
        'unit': 'm^-1',
        'coordinate': 'plant_curvature_positive_yaw_negative',
      },
      'native_request': native,
      'command': command,
      'candidate': {
        'source_result': src,
        'raw_candidate': command,
        'delivered': command,
        'delivery_gate': 'ACTIVE',
        'previous_candidate_before': before_rate,
        'candidate_state_after': rate,
      },
      'applied_before': applied_before,
      'applied': -delayed,
      'plant_before': pb,
      'plant_after': {'curvature_1pm': knew, 'yaw_rate_rad_s': ynew, 'command_history': list(queue)},
      'pose_before': posb,
      'pose_after': list(pose),
      'reference_pose': list(reference),
      'native_state_before': deepcopy(ns),
      'native_state_after': after,
      'reset_events': events,
      'previous_receipt_sha256': prior,
    }
    r['receipt_sha256'] = g.sha(g.canonical(r))
    prior = r['receipt_sha256']
    rows.append(r)
    ns, k, yaw, applied_before = after, knew, ynew, -delayed
  item['last_receipt_sha256'] = prior
  return rows, item, spec


def reseal(rows, item):
  prior = '0' * 64
  for row in rows:
    row['previous_receipt_sha256'] = prior
    row.pop('receipt_sha256', None)
    row['receipt_sha256'] = g.sha(g.canonical(row))
    prior = row['receipt_sha256']
  item['last_receipt_sha256'] = prior


class TraceBoundaryTests(unittest.TestCase):
  def test_valid_frozen_mapping_without_raw_alias(self):
    from dataclasses import FrozenInstanceError

    rows, item, spec = fixture()
    frames = verify_trace(rows, item, spec, 'NO_EXPLICIT_RESET', 'fixture')
    self.assertEqual((len(frames), frames[-1].time_s), (8, 0.08))
    self.assertNotEqual(frames[0].actual[2], 0)
    old = frames[0].actual
    rows[0]['pose_after'][0] = 12345
    self.assertEqual(frames[0].actual, old)
    for attribute in ('command', 'actual'):
      with self.subTest(attribute=attribute), self.assertRaises(FrozenInstanceError):
        setattr(frames[0], attribute, 0)

  def test_rate_state_determinism(self):
    rows, item, spec = fixture('A3')
    self.assertEqual(verify_trace(rows, item, spec, 'NO_EXPLICIT_RESET', 'fixture'), verify_trace(rows, item, spec, 'NO_EXPLICIT_RESET', 'fixture'))

  def test_two_governor_reset_modes(self):
    for mode in ('RESET_MODE_A', 'RESET_MODE_B'):
      rows, item, spec = fixture('SG-A', mode)
      self.assertEqual(len(verify_trace(rows, item, spec, mode, 'fixture')), 8)

  def test_wrong_reset_mode_is_rejected(self):
    rows, item, spec = fixture('SG-A', 'RESET_MODE_A')
    with self.assertRaises(F8Error):
      verify_trace(rows, item, spec, 'RESET_MODE_B', 'fixture')

  def test_resealed_semantic_attacks(self):
    changes = {
      'source': lambda r, i, s: r[0].update(source_sha256='fake'),
      'timestamp': lambda r, i, s: r[2].update(time_ns=-1),
      'missing_frame': lambda r, i, s: r.pop(),
      'duplicate_frame': lambda r, i, s: r.__setitem__(2, r[1].copy()),
      'coordinate': lambda r, i, s: r[0]['measurement'].update(coordinate='opposite'),
      'feedback': lambda r, i, s: r[2]['native_input'].update(actual_curvature_1pm=0.02),
      'plant': lambda r, i, s: r[3]['plant_after'].update(curvature_1pm=0.1),
      'provenance': lambda r, i, s: i['calls'].pop('native_update'),
      'cross_arm_candidate': lambda r, i, s: i['initial_state'].update(candidate=0.5),
      'cross_arm_native': lambda r, i, s: r[2]['native_state_before'].update(sat_time=123),
      'qualification': lambda r, i, s: r[0]['candidate']['source_result'].update(performance_qualified=True),
      'command': lambda r, i, s: r[0].update(command=1.01),
      'bool_number': lambda r, i, s: r[0].update(command=True),
      'delay': lambda r, i, s: r[2]['plant_before']['command_history'].__setitem__(0, 0.5),
    }
    for name, change in changes.items():
      with self.subTest(attack=name):
        rows, item, spec = fixture()
        change(rows, item, spec)
        reseal(rows, item)
        with self.assertRaises(F8Error):
          verify_trace(rows, item, spec, 'NO_EXPLICIT_RESET', 'fixture')
