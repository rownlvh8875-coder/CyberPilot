"""Receipt-bound additive controller-to-plant audit. Reads synthetic history only."""

import argparse
import json
import math
from pathlib import Path
import platform

from openpilot.tools.cyber_autotune import controller_plant_authority as a
from openpilot.tools.cyber_autotune import controller_plant_experiment as experiment
from openpilot.tools.cyber_autotune import resolution_candidate_audit as prior_math
from openpilot.tools.cyber_autotune import resolution_candidate_evidence as prior
from openpilot.tools.cyber_autotune import resolution_candidate_repeat as recovery
from openpilot.tools.cyber_autotune import curvature_yaw_screening as screening
from openpilot.tools.cyber_autotune.native_protocol import canonical, digest

PUBLIC = prior.PUBLIC
CONTROL_ROLE = 'TEST_DIAGNOSTIC_ONLY_NOT_CANDIDATE'
INDEX_SHA = '221d286729dad01a45f5aed0f0277b37abd96aea91b7c930f779abd2d2ec03bc'
PREVIOUS_AUDIT_SHA = 'e6a0b566411beb07445d3827a321e53dddac1cf48872a2f0206bf86c648e04c0'
PREVIOUS_READINESS_SHA = '4f2511be42be79b24d4414d3d4683975ed5c7ff3e4104de8b10f08b7e1c3be18'
POLICY_NAME = 'controller-plant-authority-execution-policy-v1.json'
SIGNALS = {'desired_curvature': 'desired_curvature_1pm', 'requested_torque': 'requested_torque',
           'applied_torque': 'applied_normalized_torque', 'curvature': 'curvature_1pm',
           'yaw': 'yaw_rate_rps', 'heading': 'heading_rad', 'pose_y': 'pose_y_m'}
UNITS = {'desired_curvature': '1/m', 'requested_torque': 'normalized', 'applied_torque': 'normalized',
         'curvature': '1/m', 'yaw': 'rad/s', 'heading': 'rad', 'pose_y': 'm', 'pose_velocity': 'm/s'}
SOURCE_PATHS = ('controller_plant_authority.py', 'controller_plant_experiment.py', 'controller_plant_evidence.py',
                'curvature_yaw_plant.py', 'curvature_yaw_screening.py', 'curvature_yaw_v2_search.py',
                'curvature_yaw_native_worker.py', 'resolution_candidate_repeat.py')
ROOT = Path(__file__).resolve().parents[3]


def sources():
  paths = ['openpilot/tools/cyber_autotune/' + p for p in SOURCE_PATHS]
  paths += list(recovery.s.SUPPORT_FILES + recovery.s.CANDIDATE_FILES + recovery.s.EXPERIMENT_FILES)
  paths += ['openpilot/tools/cyber_autotune/' + n for n in
            ('native_protocol.py', 'resolution_candidate_audit.py', 'resolution_candidate_evidence.py')]
  paths += ['openpilot/selfdrive/controls/lib/latcontrol_torque.py', 'openpilot/selfdrive/controls/lib/latcontrol.py',
            'opendbc_repo/opendbc/car/interfaces.py', 'opendbc_repo/opendbc/car/hyundai/carcontroller.py',
            'opendbc_repo/opendbc/car/hyundai/values.py', 'opendbc_repo/opendbc/car/lateral.py']
  return {p: digest((ROOT / p).read_bytes()) for p in paths}


def old_index():
  return recovery.checked(json.loads((PUBLIC / 'measurement-resolution-candidate-recovery-index-v1.json').read_bytes()), INDEX_SHA)


def previous():
  return recovery.checked(json.loads((PUBLIC / 'measurement-resolution-candidate-audit-v1.json').read_bytes()), PREVIOUS_AUDIT_SHA)


def read_recovery(folder, proof):
  saved = json.loads((Path(folder) / (proof['case_id'] + '.json')).read_bytes())
  recovery.checked(saved, proof['recovery_receipt_sha256'])
  if saved['case_id'] != proof['case_id'] or saved['historical_result_sha256'] != proof['result_sha256']:
    raise ValueError('HISTORICAL_RECOVERY_IDENTITY_DRIFT')
  return saved


def prepare_policy(folder=None):
  if folder is None:
    value = json.loads((PUBLIC / POLICY_NAME).read_bytes())
    validate_policy(value)
    return value
  index = old_index()
  nominal = [read_recovery(folder, proof)['relocated_report'] for proof in index['cases'] if proof['role'] == 'EVALUATION']
  deltas = [abs(c['requested_torque'] - b['requested_torque']) for r in nominal for arm in r['arms'][2:]
            for b, c in zip(r['arms'][0]['samples'], arm['samples'], strict=True)]
  distribution = prior_math.stats(deltas)
  return a.seal({
    'schema': 'CONTROLLER_PLANT_AUTHORITY_EXECUTION_POLICY_V1', 'scope': CONTROL_ROLE,
    'previous_audit_sha256': PREVIOUS_AUDIT_SHA, 'recovery_index_sha256': INDEX_SHA,
    'recoveries': {p['case_id']: p['recovery_receipt_sha256'] for p in index['cases']},
    'sources': sources(), 'plant': screening.PLANT, 'reset': screening.RESET,
    'speeds_mps': [5., 17.5, 25.], 'steps': 401, 'input_modes': ['STEP', 'RAMP'], 'signs': [-1, 1],
    'amplitudes': [0., distribution['median'], distribution['p95'], distribution['maximum']],
    'amplitude_basis': 'EXACT_POOLED_NOMINAL_V1_V2_REQUESTED_DELTA_P50_P95_MAX_PLUS_ZERO',
    'historical_delta_distribution': distribution, 'distance_queries_m': list(prior_math.DISTANCES_M),
    'longer_queries_m': [35., 40.], 'interpolation': 'OBSERVED_POST_STEP_POSE_X_LINEAR_NO_EXTRAPOLATION',
    'oracle_tolerance': 'ANALYTIC_RIGHT_RIEMANN_BOUND_PLUS_DECLARED_FLOAT_ROUNDOFF_NOT_PERFORMANCE_THRESHOLD',
    'new_search': False, 'candidate_mutation': False, 'private_data_open': False,
  })


def validate_policy(policy):
  from openpilot.tools.cyber_autotune.controller_plant_policy import EXPECTED_SHA
  recovery.checked(policy, EXPECTED_SHA)
  if (policy.get('schema') != 'CONTROLLER_PLANT_AUTHORITY_EXECUTION_POLICY_V1' or policy.get('sources') != sources()
      or policy.get('plant') != screening.PLANT or policy.get('reset') != screening.RESET
      or policy.get('recovery_index_sha256') != INDEX_SHA or policy.get('previous_audit_sha256') != PREVIOUS_AUDIT_SHA
      or policy.get('recoveries') != {p['case_id']: p['recovery_receipt_sha256'] for p in old_index()['cases']}
      or policy.get('speeds_mps') != [5., 17.5, 25.] or policy.get('steps') != 401
      or policy.get('input_modes') != ['STEP', 'RAMP'] or policy.get('signs') != [-1, 1]
      or policy.get('distance_queries_m') != list(prior_math.DISTANCES_M)
      or policy.get('longer_queries_m') != [35., 40.]
      or any(policy.get(k) is not False for k in ('new_search', 'candidate_mutation', 'private_data_open',
                                                'qualification_allowed', 'reference_promotable', 'sealed_reference_allowed',
                                                'vehicle_activation_allowed', 'candidate_acceptance_allowed'))):
    raise ValueError('FROZEN_AUTHORITY_POLICY_REQUIRED')
  values = policy.get('amplitudes')
  distribution = policy.get('historical_delta_distribution', {})
  if values != [0., distribution.get('median'), distribution.get('p95'), distribution.get('maximum')]:
    raise ValueError('AMPLITUDE_DERIVATION_REQUIRED')
  for value in values:
    a.command(value, 'NORMALIZED_TORQUE')
  return policy


def decompose(base, candidate, dt, delay):
  if len(base) != len(candidate) or not base:
    raise ValueError('SAME_TIMEBASE_REQUIRED')
  if any(b['time_s'] != c['time_s'] for b, c in zip(base, candidate, strict=True)):
    raise ValueError('SAME_TIMEBASE_REQUIRED')
  if any(not math.isclose(y['time_s'] - x['time_s'], dt, abs_tol=1e-12, rel_tol=0.) for x, y in zip(base, base[1:], strict=False)):
    raise ValueError('DT_MISMATCH')
  deltas = {name: [c[field] - b[field] for b, c in zip(base, candidate, strict=True)] for name, field in SIGNALS.items()}
  ys = deltas['pose_y']
  deltas['pose_velocity'] = [(y - (ys[i - 1] if i else 0.)) / dt for i, y in enumerate(ys)]
  stats = {k: {**a.signal(v, dt), 'units': UNITS[k], 'integral_units': UNITS[k] + '*s'} for k, v in deltas.items()}
  chain = ('requested_torque', 'applied_torque', 'curvature', 'yaw', 'heading', 'pose_y')
  ratios = [{'from': x, 'to': y, 'l1_output_per_input': a.ratio(stats[y]['absolute_integral'], stats[x]['absolute_integral']),
             'units': UNITS[y] + '/(' + UNITS[x] + ')',
             'interpretation': 'SIGNAL_NORM_RATIO_NOT_CAUSAL_ATTENUATION'} for x, y in zip(chain, chain[1:], strict=False)]
  aligned = [0.] * min(delay, len(base)) + deltas['requested_torque'][:len(base) - delay] if delay else deltas['requested_torque']
  return {'signals': stats, 'stage_ratios': ratios,
          'delay_aligned_applied_residual_max': max(abs(x - y) for x, y in zip(aligned, deltas['applied_torque'], strict=True)),
          'delay_tail_requested_integral_abs': math.fsum(map(abs, deltas['requested_torque'][-delay:])) * dt if delay else 0.,
          'baseline_saturation_frames': sum(b['saturated'] for b in base),
          'candidate_saturation_frames': sum(c['saturated'] for c in candidate),
          'requested_limit_frames': sum(abs(c['requested_torque']) == 1. for c in candidate),
          'final_pose_y_delta_m': ys[-1],
          'maximum_pose_y_delta_m': max(map(abs, ys))}


def readiness(audit_sha):
  old = recovery.checked(json.loads((PUBLIC / 'measurement-resolution-candidate-readiness-v1.json').read_bytes()), PREVIOUS_READINESS_SHA)
  return a.seal({'schema': 'CONTROLLER_PLANT_AUTHORITY_READINESS_V1', 'status': 'CONTROLLER_PLANT_AUTHORITY_AUDIT_COMPLETE',
                 'audit_sha256': audit_sha, 'reference_calibration_track': 'BLOCKED_UNCHANGED',
                 'controller_plant_authority_track': 'AUDIT_COMPLETE_NOT_VEHICLE_VALIDATION',
                 'blockers': old['blockers'], 'previous_readiness_sha256': PREVIOUS_READINESS_SHA,
                 'reference_status': 'INDEPENDENT_REFERENCE_UNAVAILABLE', 'independent_meter_result': None,
                 'candidate_verdicts': old['candidate_verdicts'],
                 'next_plan': {'controller': 'REVIEW_ARCHITECTURE_AND_DESCRIPTIVE_PLANT_APPLICABILITY_BEFORE_ANY_NEW_EXPERIMENT',
                               'reference': 'PHYSICAL_UNCERTAINTY_POSE_AND_PIXEL_REGISTRATION_EVIDENCE_STILL_REQUIRED'},
                 'new_candidate_selected': False})


def controls(policy):
  validate_policy(policy)
  rows = []
  repeat = True
  for speed in policy['speeds_mps']:
    for amplitude in policy['amplitudes']:
      for mode in policy['input_modes']:
        for sign in policy['signs']:
          value = amplitude * sign
          trace = experiment.run_input(policy['plant'], policy['reset'], speed, value, mode, policy['steps'])
          again = experiment.run_input(policy['plant'], policy['reset'], speed, value, mode, policy['steps'])
          repeat &= trace == again
          query_rows = []
          for d in policy['distance_queries_m']:
            p = a.query(trace['samples'], d)
            query_rows.append({'distance_m': d, 'status': a.query_status(trace['samples'], d), 'state': p,
                               'local_sensitivity_semantics': 'FINITE_PERTURBATION_SECANT_NOT_DIFFERENTIAL_VEHICLE_GAIN',
                               'local_sensitivity': None if not p or value == 0 else {
                                 'curvature_per_torque_1pm': p['curvature_1pm'] / value,
                                 'yaw_per_torque_rad_s': p['yaw_rate_rps'] / value,
                                 'heading_per_torque_rad': p['heading_rad'] / value,
                                 'pose_y_per_torque_m': p['pose_y_m'] / value,
                                 'pose_y_per_curvature_m2': a.ratio(p['pose_y_m'], p['curvature_1pm'])}})
          rows.append({'speed_mps': speed, 'amplitude': value, 'mode': mode, 'role': CONTROL_ROLE,
                       'trace_sha256': digest(canonical(trace)), 'queries': query_rows,
                       **{k: v for k, v in trace.items() if k != 'samples'},
                       'final_state': trace['samples'][-1], 'samples_count': len(trace['samples'])})
  oracle_rows = [{'geometric_curvature_1pm': k, 'speed_mps': speed, 'dt_s': dt,
                  **a.oracle(k, speed, 4., dt)}
                 for k in (0., -.001, .001) for speed in policy['speeds_mps'] for dt in (.01, .005)]
  return a.seal({'schema': 'CONTROLLER_PLANT_POSITIVE_CONTROL_V1', 'execution_policy_sha256': policy['receipt_sha256'],
                 'role': CONTROL_ROLE, 'rows': rows, 'analytic_geometry_oracles': oracle_rows,
                 'exact_repeatability': repeat, 'negative_control_exact_zero': all(
                   r['final_state']['pose_y_m'] == 0. and r['final_state']['heading_rad'] == 0.
                   for r in rows if r['amplitude'] == 0.),
                 'analytic_recurrence_all_pass': all(r['analytic_recurrence_agrees'] for r in rows),
                 'standalone_reference_math_all_pass': all(r['within_riemann_bound'] for r in oracle_rows),
                 'original_geometry_oracles': [
                   {'geometric_curvature_1pm': k, 'speed_mps': v,
                    **experiment.original_geometry_oracle(policy['plant'], k, v, policy['steps'])}
                   for k in (0., -.001, .001) for v in policy['speeds_mps']],
                 'analytic_geometry_all_pass': all(
                   experiment.original_geometry_oracle(policy['plant'], k, v, policy['steps'])['within_discrete_bound']
                   for k in (0., -.001, .001) for v in policy['speeds_mps']),
                 'scope': 'DESCRIPTIVE_PLANT_LOCAL_SENSITIVITY_NOT_REAL_VEHICLE_GAIN'})


def build(folder, policy):
  validate_policy(policy)
  prior.guard()
  previous_report = previous()
  index = old_index()
  proof_by = {p['case_id']: p for p in index['cases']}
  old_by = {recovery.case_id(p): p for p in recovery.archived_cases()}
  rows, distances, visual, bindings = [], [], [], []
  for case_id, proof in sorted(proof_by.items()):
    saved = read_recovery(folder, proof)
    report = saved['relocated_report']
    # Re-validate complete immutable native receipts, not just aggregate claims.
    recovery.normalize_report(report, old_by[case_id])
    bindings.append({'case_id': case_id, 'receipt_sha256': saved['receipt_sha256'], 'role': proof['role']})
    if proof['role'] != 'EVALUATION':
      continue
    m = report['manifest']
    if m['plant_config'] != policy['plant'] or m['initial_state'] != policy['reset']:
      raise ValueError('NOMINAL_PLANT_OR_RESET_DRIFT')
    base = report['arms'][0]['samples']
    if base != report['arms'][1]['samples'] or not report['exact_repeatability']:
      raise ValueError('EXACT_CURRENT_ALIAS_REPEAT_REQUIRED')
    for i, name in ((1, 'CURRENT'), (2, 'V1'), (3, 'V2')):
      candidate = report['arms'][i]['samples']
      detail = decompose(base, candidate, m['plant_config']['dt_s'], m['plant_config']['delay_steps'])
      phases = []
      for phase in sorted({p['phase'] for p in base}):
        ids = [j for j, p in enumerate(base) if p['phase'] == phase]
        phase_stats = {k: a.signal([candidate[j][field] - base[j][field] for j in ids], m['plant_config']['dt_s'])
                       for k, field in SIGNALS.items()}
        # Non-contiguous phase slices must not invent derivative/sign adjacency.
        for stats in phase_stats.values():
          stats.pop('maximum_derivative_per_s')
          stats.pop('sign_changes')
        phases.append({'phase': phase, 'count': len(ids), 'signals': phase_stats,
                       'scope': 'DISJOINT_PHASE_VALUES_NO_CROSS_GAP_DERIVATIVES'})
      row = {'scenario': m['scenario'], 'candidate': name, 'historical_case_id': case_id, **detail,
             'phases': phases, 'exact_repeatability': True}
      rows.append(row)
      max_distance = min(base[-1]['pose_x_m'], candidate[-1]['pose_x_m'])
      for distance in (*policy['distance_queries_m'], *policy['longer_queries_m'], max_distance):
        b, c = a.query(base, distance), a.query(candidate, distance)
        distances.append({'scenario': m['scenario'], 'candidate': name, 'distance_m': distance,
                          'scope': 'DECLARED_5_30M_CONTEXT_ONLY' if distance in policy['distance_queries_m'] else 'LONGER_HORIZON_PLANT_CONTEXT_ONLY',
                          'status': 'AVAILABLE' if b and c else 'DISTANCE_NOT_REACHED',
                          'pose_y_delta_m': c['pose_y_m'] - b['pose_y_m'] if b and c else None,
                          'classification': None, 'meter_envelope_extended': False})
      for j in range(0, len(base), 10):
        visual.append({'scenario': m['scenario'], 'candidate': name, 'time_s': base[j]['time_s'],
                       'post_step_elapsed_s': (j + 1) * m['plant_config']['dt_s'], 'phase': base[j]['phase'],
                       'baseline_pose_x_m': base[j]['pose_x_m'],
                       **{k + '_delta': candidate[j][v] - base[j][v] for k, v in SIGNALS.items()}})
  if len(rows) != 33:
    raise ValueError('EXACT_ELEVEN_NOMINAL_CASES_REQUIRED')
  positive = controls(policy)
  if not all(positive[k] for k in ('exact_repeatability', 'negative_control_exact_zero',
                                  'analytic_recurrence_all_pass', 'analytic_geometry_all_pass')):
    raise ValueError('PLANT_OBSERVABILITY_CONTROL_FAILURE')
  for row in rows:
    if row['delay_aligned_applied_residual_max'] != 0.:
      raise ValueError('NOMINAL_DELAY_CHAIN_MISMATCH')
  attenuation = a.seal({'schema': 'CONTROLLER_PLANT_STAGE_ATTENUATION_V1', 'execution_policy_sha256': policy['receipt_sha256'],
                        'rows': rows, 'visual_samples': visual, 'distances': distances,
                        'integral_semantics': 'RECTANGLE_SUM_POST_STEP_SIGNAL_DT; SIGNED_AND_L1_SEPARATE',
                        'ratio_semantics': 'CROSS_UNIT_SIGNAL_NORM_RATIOS_NOT_DIMENSIONLESS_CAUSAL_ATTENUATION'})
  peaks = {name: {key: max(r['signals'][key]['maximum_absolute'] for r in rows if r['candidate'] == name)
                  for key in SIGNALS} for name in ('CURRENT', 'V1', 'V2')}
  audit = a.seal({
    'schema': 'CONTROLLER_TO_PLANT_AUTHORITY_AUDIT_V1', 'status': 'CONTROLLER_PLANT_AUTHORITY_AUDIT_COMPLETE',
    'verdict': 'PLANT_AUTHORITY_CONFIRMED', 'attribution': 'MIXED_OR_UNRESOLVED',
    'execution_policy_sha256': policy['receipt_sha256'], 'source_sha256': policy['sources'],
    'recovery_index_sha256': INDEX_SHA, 'previous_candidate_audit_sha256': PREVIOUS_AUDIT_SHA,
    'historical_bindings': bindings, 'historical_revalidated_cases': 70, 'nominal_cases': 11,
    'positive_control_sha256': positive['receipt_sha256'], 'stage_attenuation_sha256': attenuation['receipt_sha256'],
    'historical_verdicts': {k: v['status'] for k, v in previous_report['ledger'].items()},
    'current_alias': 'BASELINE_EXACT', 'v2_existing_violation_count': 37,
    'meter_envelope_sha256': previous_report['meter_sha256'], 'meter_envelope_recomputed': False,
    'reference_coverage': previous_report['coverage'], 'peak_deltas_whole_run': peaks,
    'dc_gain_by_speed': [{'speed_mps': v, 'curvature_per_requested_normalized_torque_1pm': -experiment.dc_gain(policy['plant'], v),
                          'acceleration_equivalent_mps2_per_normalized': experiment.dc_gain(policy['plant'], v) * v ** 2,
                          'native_linear_acceleration_factor': 4., 'physically_validated': False}
                         for v in policy['speeds_mps']],
    'unit_scale_sign_verdict': 'NO_DEFECT_FOUND_IN_PINNED_DESCRIPTIVE_CHAIN',
    'scope': 'DESCRIPTIVE_PLANT_COUNTERFACTUAL_EFFECT_NOT_REAL_VEHICLE_DYNAMICS',
    'limitations': ['NO_HYUNDAI_RAW_RATE_DRIVER_LIMITER_OR_QUANTIZATION_IN_PLANT',
                    'POST_STEP_STATES_LABELED_BY_FRAME_START_TIME',
                    'WORKER_OMITS_STOCK_INACTIVE_SATURATION_TIMER_RESET_NOT_TORQUE_PATH',
                    'YAW_AR_FILTERS_TARGET_RESIDUAL_NOT_ORDINARY_YAW_LAG',
                    'DESCRIPTIVE_GAIN_NOT_MATCHED_TO_NATIVE_FACTOR4_PHYSICAL_DYNAMICS'],
    'open_reference_terms': previous_report['open_terms'], 'new_search': False,
    'candidate_mutation': False, 'detector_mutation': False, 'private_data_open': False,
    'runtime_environment': {'python': platform.python_version(), 'machine': platform.machine()},
  })
  validate_policy(policy)
  return audit, attenuation, positive, readiness(audit['receipt_sha256'])


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--recovered', required=True)
  parser.add_argument('--output', required=True)
  parser.add_argument('--freeze-policy', action='store_true')
  args = parser.parse_args()
  if args.freeze_policy:
    policy = prepare_policy(args.recovered)
    recovery.immutable(Path(args.output) / POLICY_NAME, canonical(policy))
    print(policy['receipt_sha256'])
    return
  policy = prepare_policy()
  results = build(args.recovered, policy)
  for name, row in zip(('audit', 'stage-attenuation', 'positive-control', 'readiness'), results, strict=True):
    recovery.immutable(Path(args.output) / f'controller-plant-{name if name != "audit" else "authority-audit"}-v1.json', canonical(row))
    print(name, row['receipt_sha256'])


if __name__ == '__main__':
  main()
