"""Interpret the frozen authority run; never changes candidates or plant history."""

import argparse
import json
import math
from pathlib import Path

from openpilot.tools.cyber_autotune import controller_plant_authority as a
from openpilot.tools.cyber_autotune import controller_plant_evidence as e
from openpilot.tools.cyber_autotune.native_protocol import canonical, digest

CHAIN = [
  {'stage': 'desired_curvature', 'units': '1/m', 'semantics': 'FROZEN k; a_des=k*v^2; controller k=-geometric k (flat positive-response example)',
   'source': 'openpilot/tools/cyber_autotune/curvature_yaw_v2_search.py'},
  {'stage': 'LatControlTorque_internal', 'units': 'm/s^2', 'semantics':
   'measurement=k*v^2; PID+current feedforward-roll*g-offset+factor-scaled friction; reference delay15samples at .15s',
   'source': 'openpilot/selfdrive/controls/lib/latcontrol_torque.py'},
  {'stage': 'requested_normalized_torque', 'units': 'normalized [-1,1]', 'semantics':
   '-output_lataccel/latAccelFactor; PID acceleration limits +/-factor; no raw scaling',
   'source': 'openpilot/selfdrive/controls/lib/latcontrol_torque.py'},
  {'stage': 'raw_Hyundai_command', 'units': 'raw counts', 'semantics':
   'NOT EXECUTED; round(384*u) then driver/rate limits; 3/7 raw counts per100Hz; not amplitude gain in plant',
   'source': 'opendbc_repo/opendbc/car/hyundai/carcontroller.py', 'executed_in_historical_harness': False},
  {'stage': 'plant_actuator_queue', 'units': 'normalized', 'semantics':
   'plant_command=-requested; sole physical queue2steps=.02s; applied_normalized=-delayed_plant_command; no clipping (reject outside domain)',
   'source': 'openpilot/tools/cyber_autotune/curvature_yaw_plant.py'},
  {'stage': 'curvature_response', 'units': '1/m', 'semantics':
   'k_next=.92*k+(.004+.0002*v+.002/v)*delayed_plant_command+.001*roll; discrete coefficients; no extra dt',
   'source': 'openpilot/tools/cyber_autotune/curvature_yaw_plant.py'},
  {'stage': 'yaw_response', 'units': 'rad/s', 'semantics':
   'YAW_TARGET_RESIDUAL recurrence: yaw_next=-curvature_next*v+.75*(yaw_previous+curvature_previous*v); not ordinary yaw lag',
   'source': 'openpilot/tools/cyber_autotune/curvature_yaw_plant.py'},
  {'stage': 'heading', 'units': 'rad', 'semantics': 'heading_next=heading+yaw_next*.01; positive yaw turns positive pose-y',
   'source': 'openpilot/tools/cyber_autotune/curvature_yaw_v2_search.py'},
  {'stage': 'pose_x_pose_y', 'units': 'm', 'semantics':
   'x+=v*cos(updated_heading)*.01; y+=v*sin(updated_heading)*.01; post-step state, frame-start timestamp',
   'source': 'openpilot/tools/cyber_autotune/curvature_yaw_v2_search.py'},
]


def transfer_gains(pole, gain, dt):
  if not 0 <= pole < 1 or dt <= 0 or not all(math.isfinite(v) for v in (pole, gain, dt)):
    raise ValueError('STABLE_DISCRETE_TRANSFER_REQUIRED')
  return {'dc_curvature_gain': gain / (1 - pole), 'nyquist_curvature_gain': gain / (1 + pole),
          'nyquist_to_dc_ratio': (1 - pole) / (1 + pole),
          'pole_time_constant_s': 0. if pole == 0 else -dt / math.log(pole),
          'scope': 'DESCRIPTIVE_DISCRETE_TRANSFER_ONLY'}


def build(folder, run):
  policy = e.prepare_policy()
  paths = {'audit': 'controller-plant-authority-audit-v1.json',
           'stage': 'controller-plant-stage-attenuation-v1.json',
           'control': 'controller-plant-positive-control-v1.json'}
  data = {name: json.loads((Path(run) / file).read_bytes()) for name, file in paths.items()}
  for row in data.values():
    e.recovery.checked(row, row['receipt_sha256'])
    if row['execution_policy_sha256'] != policy['receipt_sha256']:
      raise ValueError('EXACT_EXECUTION_POLICY_REQUIRED')
  if (data['audit']['stage_attenuation_sha256'] != data['stage']['receipt_sha256']
      or data['audit']['positive_control_sha256'] != data['control']['receipt_sha256']):
    raise ValueError('AUTHORITY_RECEIPT_LINK_MISMATCH')
  timing = []
  for proof in e.old_index()['cases']:
    if proof['role'] != 'EVALUATION':
      continue
    r = e.read_recovery(folder, proof)['relocated_report']
    base = r['arms'][0]['samples']
    for i, name in ((2, 'V1'), (3, 'V2')):
      candidate = r['arms'][i]['samples']
      values = [c['requested_torque'] - b['requested_torque'] for b, c in zip(base, candidate, strict=True)]
      peak = max(range(len(values)), key=lambda j: abs(values[j]))
      early = [v for v, b in zip(values, base, strict=True) if 5 <= b['pose_x_m'] <= 30]
      nonzero = next((j for j, v in enumerate(values) if v != 0.), None)
      timing.append({'scenario': r['manifest']['scenario'], 'candidate': name,
                     'early_5_30m_requested_delta': a.signal(early, policy['plant']['dt_s']),
                     'peak_requested_delta': values[peak], 'peak_time_s': base[peak]['time_s'],
                     'peak_observed_baseline_x_m': base[peak]['pose_x_m'], 'peak_phase': base[peak]['phase'],
                     'first_nonzero_time_s': None if nonzero is None else base[nonzero]['time_s'],
                     'first_nonzero_x_m': None if nonzero is None else base[nonzero]['pose_x_m'],
                     'early_window_samples': len(early), 'whole_run_samples': len(values)})
  stage = [r for r in data['stage']['rows'] if r['candidate'] != 'CURRENT']
  cancellation = [{'scenario': r['scenario'], 'candidate': r['candidate'],
                   'requested_cancellation_ratio': r['signals']['requested_torque']['cancellation_ratio'],
                   'pose_increment_cancellation_ratio': r['signals']['pose_velocity']['cancellation_ratio'],
                   'requested_sign_changes': r['signals']['requested_torque']['sign_changes'],
                   'final_pose_y_delta_m': r['final_pose_y_delta_m'],
                   'maximum_pose_y_delta_m': r['maximum_pose_y_delta_m']} for r in stage]
  gains = []
  for v in policy['speeds_mps']:
    p = policy['plant']
    g = p['command_gain_1pm'] + p['command_speed_gain_s_per_m2'] * v + p['command_inv_speed_gain_per_s'] / v
    gains.append({'speed_mps': v, **transfer_gains(p['curvature_ar'], g, p['dt_s']),
                  'input_sign': 'MAGNITUDE_GAIN; SIGNED_REQUESTED_TORQUE_TO_CURVATURE_IS_NEGATIVE'})
  chain = [{**r, 'source_sha256': policy['sources'][r['source']], 'rate_hz': 100.,
            'reset': 'NEW_NATIVE_CONTROLLER_ZERO_PLANT_POSE_QUEUE_PER_ARM; NO_CROSS_ARM_CARRY',
            'source_role': 'PINNED_DESCRIPTIVE_SOURCE_NOT_PHYSICAL_CALIBRATION'} for r in CHAIN]
  prior = e.previous()
  results = {
    'A_candidate_output': {'status': 'SCENARIO_DEPENDENT_NOT_UNIFORMLY_NEGLIGIBLE',
                           'evidence': 'Low-speed torque deltas tiny; V2 high-speed exact zero in four cases; other whole-run peaks up to .392777 normalized.',
                           'counterevidence': 'Whole-run instantaneous peaks are not representative early-distance mean displacement.'},
    'B_plant_gain': {'status': 'WEAK_GAIN_HYPOTHESIS_NOT_SUPPORTED',
                    'evidence': 'Positive controls and independent recurrence pass. Strong DC gain ' +
                                  'and AR high-frequency attenuation are separately quantified.',
                    'counterevidence': 'Gain is descriptive and mismatched to native factor4 at high speed; this is not physical actuator authority.'},
    'C_unit_scale_sign_dt': {'status': 'NO_DEFECT_FOUND_IN_PINNED_DESCRIPTIVE_CHAIN',
                             'evidence': 'Original plant_trace matches signed circular arc within its analytic Euler discretization bound. ' +
                                  'No missing384 or double dt.',
                             'counterevidence': 'No raw actuator stage; timestamp and inactive saturation-reset limitations remain.'},
    'D_cancellation': {'status': 'SCENARIO_DEPENDENT_TEMPORAL_CANCELLATION',
                       'evidence': 'Signed/L1 torque and pose-increment integrals and sign changes retained per scenario; ' +
                                  'delay-aligned applied delta equals requested delta exactly.',
                       'counterevidence': 'Cancellation is not uniform and cannot explain exact-zero V2 outputs.'},
    'E_query_horizon': {'status': 'EARLY_DISTANCE_WINDOW_LIMITS_OBSERVED_EFFECT',
                        'evidence': '5–30m maxima remain frozen below envelope; larger whole-run effects occur later. 35/40/common max-x are context only.',
                        'counterevidence': 'Later maximum remains descriptive and does not overturn tracking or smoothness rejection.'},
    'F_smoothness_family': {'status': 'NOT_PROVEN_STRICTLY_SMOOTHNESS_ONLY',
                            'evidence': 'Torque oscillation/derivative differences coexist with nonzero trajectory changes ' +
                                  'and historical tracking regressions.',
                            'counterevidence': 'Current family is trajectory-small at declared early-distance diagnostic scale; ' +
                                  'no architecture acceptance follows.'},
  }
  return a.seal({'schema': 'CONTROLLER_PLANT_AUTHORITY_FINDINGS_V1', 'status': 'ATTRIBUTION_COMPLETE',
                 'verdict': 'PLANT_AUTHORITY_CONFIRMED', 'combined_attribution': 'MIXED_OR_UNRESOLVED',
                 'interpretation': 'SMALL_EARLY_EFFECT_WITH_SCENARIO_DEPENDENT_OUTPUT_DIFFERENCE_FILTERING_CANCELLATION_AND_LATE_TRANSIENTS',
                 'audit_sha256': data['audit']['receipt_sha256'], 'execution_policy_sha256': policy['receipt_sha256'],
                 'source_sha256': digest(Path(__file__).read_bytes()), 'signal_chain': chain,
                 'frequency_response': gains, 'timing': timing, 'cancellation': cancellation, 'hypotheses': results,
                 'historical_early_distance_summary': prior['nominal_summary']['distance_summary'],
                 'historical_whole_phase_context_sha256': digest(canonical(prior['phase_context'])),
                 'historical_verdicts': data['audit']['historical_verdicts'],
                 'counterevidence_policy': 'NO_ARBITRARY_NEGLIGIBLE_CM_THRESHOLD_NO_SINGLE_CAUSE_OR_PERFORMANCE_SCORE',
                 'next_action': 'NO_MICRO_SEARCH; AUDIT_PLANT_APPLICABILITY_AND_CONTROLLER_FAMILY_ARCHITECTURE_IN_A_SEPARATE_EXPERIMENT',
                 'calibration_track': 'CONTINUES_IN_PARALLEL_WITHOUT_BLOCKING_THIS_SYNTHETIC_AUDIT'})


if __name__ == '__main__':
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--recovered', required=True)
  parser.add_argument('--run', required=True)
  args = parser.parse_args()
  result = build(args.recovered, args.run)
  e.recovery.immutable(Path(args.run) / 'controller-plant-authority-findings-v1.json', canonical(result))
  print(result['receipt_sha256'])
