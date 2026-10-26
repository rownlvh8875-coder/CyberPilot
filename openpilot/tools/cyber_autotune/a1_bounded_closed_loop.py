"""Fixed bounded A1 synthetic hypothesis over the existing generic closed loop.

This module does not change the rejected A1 fixtures, schedule limits, metric policy,
controller, plant, Params, profile or vehicle authority. Scale 1/2 is predeclared
before execution and is not a vehicle tune or a search result.
"""
import base64
from dataclasses import asdict
from pathlib import Path

from openpilot.tools.cyber_autotune import a1_closed_loop as existing
from openpilot.tools.cyber_autotune.a1_experiment import BASELINE_FACTOR, BASELINE_FRICTION, build_request, make_fixture
from openpilot.tools.cyber_autotune.a1_schedule import prepare_schedule
from openpilot.tools.cyber_autotune.native_protocol import canonical, digest
from openpilot.tools.cyber_autotune.synthetic_metrics import lateral_metrics
from openpilot.tools.cyber_autotune.synthetic_native_v2 import POLICY_SHA256, frozen_policy
from openpilot.tools.cyber_autotune.synthetic_pipeline import AUTHORITY, _compare, source_binding
from openpilot.tools.cyber_autotune.synthetic_stress_catalog import catalog, catalog_digest, frame_digest, frames, validate_frames
from openpilot.selfdrive.controls.lib.cyber_lateral.speed_aware_tune import SpeedAwareTuneTable, SpeedTunePoint


ROOT = Path(__file__).resolve().parents[3]
BOUNDED_SCALE = .5
CANDIDATES = ('bounded_factor', 'bounded_friction', 'bounded_combined')
SPEEDS_MPS = (0., 10., 20., 30.)
BASE_FACTOR_OFFSETS = (0., 1 / 64, 1 / 32, 0.)
BASE_FRICTION_OFFSETS = (0., 1 / 1024, 1 / 512, 0.)
PASS = 'COMPLETED_SYNTHETIC_ONLY'
SCOPE = 'FIXED_HALF_SCALE_A1_GENERIC_PLANT_NOT_VEHICLE_CALIBRATION'


def bounded_table(name):
  if type(name) is not str or name not in CANDIDATES:
    raise ValueError('UNDECLARED_BOUNDED_A1_ARM')
  use_factor = name in ('bounded_factor', 'bounded_combined')
  use_friction = name in ('bounded_friction', 'bounded_combined')
  points = tuple(
    SpeedTunePoint(
      speed,
      BASELINE_FACTOR + (offset_factor * BOUNDED_SCALE if use_factor else 0.),
      BASELINE_FRICTION + (offset_friction * BOUNDED_SCALE if use_friction else 0.),
      1.,
    )
    for speed, offset_factor, offset_friction in zip(SPEEDS_MPS, BASE_FACTOR_OFFSETS, BASE_FRICTION_OFFSETS, strict=True)
  )
  return SpeedAwareTuneTable(points, 'repository-owned-synthetic-a1-bounded-half-v1')


def _run_candidate(case_id, arm, delay_s):
  cases = {case.case_id: case for case in catalog() if case.axis == 'lateral'}
  if type(case_id) is not str or case_id not in cases or arm not in CANDIDATES:
    raise ValueError('UNDECLARED_BOUNDED_A1_CASE')
  case = cases[case_id]
  if type(delay_s) not in (int, float) or delay_s not in case.physical_delays_s:
    raise ValueError('UNDECLARED_PHYSICAL_DELAY')
  rows = frames(case)
  input_status = validate_frames(rows, case.dt_s)
  result = {
    'case_id': case_id, 'fixture': arm, 'physical_delay_s': delay_s,
    'input_sha256': frame_digest(rows), 'input_status': input_status,
    'policy_sha256': POLICY_SHA256, 'controller_executed': False, 'metrics': None,
    'physical_delay_owner': 'PLANT', 'controller_delay_queue_present': False,
    'time_semantics': 'INPUT_COMMAND_AT_INTERVAL_START_STATE_AT_INTERVAL_END',
    'vehicle_activation_allowed': False, **dict.fromkeys(AUTHORITY, False),
  }
  if input_status != case.expected_input_status:
    raise ValueError('SCENARIO_INPUT_EXPECTATION_MISMATCH')
  if input_status != 'VALID':
    return dict(result, status='REJECTED_INPUT', reason=input_status)

  from opendbc.car import structs
  import numpy as np

  native, _ = make_fixture(build_request('identity'))
  with structs.CarParams.from_bytes(base64.b64decode(native['car_params_base64'])) as reader:
    cp = reader.as_builder()
  table = bounded_table(arm)
  try:
    prepare_schedule(table, tuple(row.speed_mps for row in rows),
                     cp.lateralTuning.torque.latAccelFactor, cp.lateralTuning.torque.friction)
  except ValueError as exc:
    if str(exc) not in ('A1_TRANSITION_EXCEEDED', 'OUTSIDE_A1_SPEED_DOMAIN', 'OUTSIDE_SYNTHETIC_A1_BOUNDS'):
      raise
    return dict(result, status='BLOCKED', reason=str(exc))

  with np.errstate(over='raise', invalid='raise', divide='raise'):
    trace, config, receipt = existing._trace(case, rows, cp, table, delay_s)
    metrics = lateral_metrics(trace, case.dt_s)
  return dict(
    result, status=PASS, controller_executed=True, metrics=metrics, receipt=receipt,
    plant_sha256=digest(canonical(config)), base_car_params_sha256=native['car_params_sha256'],
    table_sha256=digest(canonical(asdict(table))),
    reset_sha256=digest(canonical({'controller': 'FRESH', 'plant': 'FRESH', 'delay_queue': 'ZERO', 'step_index': 0})),
  )


def run_matrix():
  policy = frozen_policy()
  if catalog_digest() != policy['catalog_sha256']:
    raise ValueError('SYNTHETIC_CATALOG_CHANGED')
  before = source_binding()
  variants = [(case.case_id, delay) for case in catalog() if case.axis == 'lateral' for delay in case.physical_delays_s]
  baseline = [existing.run_case(case_id, 'disabled', delay) for case_id, delay in variants]
  arms = {'baseline': baseline}
  for arm in CANDIDATES:
    arms[arm] = [_run_candidate(case_id, arm, delay) for case_id, delay in variants]

  comparisons = {}
  for arm in CANDIDATES:
    verdict = _compare({'results': baseline}, {'results': arms[arm]}, policy)
    reasons = list(verdict['reasons'])
    for row in arms[arm]:
      if row['input_status'] == 'VALID' and row['status'] != PASS:
        reasons.append('INCOMPLETE_VALID_COVERAGE')
      if row['metrics'] is not None:
        if row['metrics']['lane_edge_minimum_margin_m'] < 0:
          reasons.append(row['case_id'] + ':NEGATIVE_LANE_MARGIN')
        if row['metrics']['unresolved_recoveries'] != 0:
          reasons.append(row['case_id'] + ':UNRESOLVED_RECOVERY')
    comparisons[arm] = dict(
      verdict,
      status='REJECTED' if reasons else 'PASS_SYNTHETIC_ONLY',
      reasons=sorted(set(reasons)),
    )

  after = source_binding()
  if before != after or frozen_policy() != policy or catalog_digest() != policy['catalog_sha256']:
    raise ValueError('BOUNDED_A1_BINDING_CHANGED_DURING_RUN')
  return {
    'schema': 'a1-bounded-generic-closed-loop-v1', 'status': PASS, 'scope': SCOPE,
    'hypothesis': 'HALF_EXISTING_A1_OFFSETS_FIXED_BEFORE_EXECUTION',
    'bounded_scale': BOUNDED_SCALE, 'case_delay_count': len(variants), 'arms': arms,
    'comparisons': comparisons, 'policy_sha256': POLICY_SHA256,
    'source_binding_sha256': digest(canonical(before)),
    'deterministic_repeats': 'NOT_CHECKED_IN_SINGLE_RUN',
    'readiness': 'NOT_READY', 'vehicle_activation_allowed': False,
    **dict.fromkeys(AUTHORITY, False),
  }
