"""Versioned paired H1 contracts. No controller, raw-log or vehicle IO."""

from pathlib import Path
import json
from functools import lru_cache

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import cyber_lateral_h1_contract as c
from openpilot.tools.cyber_autotune import cyber_lateral_h1_producer as h

CAMPAIGNS = {
  'TA_B': ('CYBER_H1_TA_B_STANDALONE_COMPARISON', 'TA_B_V0', 'TA_STANDALONE_TRADEOFF_ONLY'),
  'SG_A': ('CYBER_H1_SG_A_STANDALONE_COMPARISON', 'SG_A_V0', 'SG_CLOSED_LOOP_TRADEOFF_ONLY'),
}
BASELINE = 'UPSTREAM_BASELINE'
TIER = c.TIER
OWN = ('cyber_h1_pairing.py', 'cyber_h1_pair_producer.py', 'cyber_h1_paired_visual_adapter.py', 'cyber_h1_comparison_catalog.py')
FIREWALL = {k: v for k, v in p.FIREWALL.items() if k not in ('ta_execution', 'sg_execution')}


def seal(row):
  body = {**row, **FIREWALL}
  return {**body, 'receipt_sha256': p.sha(p.canonical(body))}


def verify(row):
  if type(row) is not dict or row.get('receipt_sha256') != p.sha(p.canonical({k: v for k, v in row.items() if k != 'receipt_sha256'})):
    raise ValueError('PAIR_RECEIPT_DRIFT')
  if any(row.get(k) is not v for k, v in FIREWALL.items()):
    raise ValueError('PAIR_AUTHORITY_FIREWALL')
  return row


@lru_cache(maxsize=1)
def _historical(stamp):
  from openpilot.tools.cyber_autotune import trajectory_v0_publication as ta
  from openpilot.tools.cyber_autotune import smoothness_closed_loop_publication as sg
  from openpilot.tools.cyber_autotune import trajectory_v0_freeze as tf
  from openpilot.tools.cyber_autotune import smoothness_v0_freeze as sf
  from openpilot.tools.cyber_autotune import cyber_h1_visual_publication as visual

  t, s, tv, sv = ta.load(), sg.load(), tf.load(), sf.load()
  visual.load()
  if t['readiness']['standalone_verdict'] != CAMPAIGNS['TA_B'][2] or s['readiness']['status'] != CAMPAIGNS['SG_A'][2]:
    raise ValueError('PAIR_HISTORICAL_VERDICT_CONFLICT')
  if tv['scenarios']['rows'] != sv['scenarios']['rows'] or tv['config']['family'] != 'TA-B':
    raise ValueError('PAIR_FROZEN_SCENARIO_FAMILY_CONFLICT')
  return {
    'ta_receipts': {k: v['receipt_sha256'] for k, v in t.items()},
    'sg_closed_loop_receipts': {k: v['receipt_sha256'] for k, v in s.items()},
    'ta_frozen_receipts': {k: v['receipt_sha256'] for k, v in tv.items()},
    'sg_frozen_receipts': {k: v['receipt_sha256'] for k, v in sv.items()},
    'ta_binding': t['binding'],
    'sg_binding': s['binding'],
    'scenario_rows': tv['scenarios']['rows'],
    'scenario_policy_sha256': tv['scenarios']['receipt_sha256'],
    'h1_policy_sha256': c.policy()['receipt_sha256'],
    'h1_schema_sha256': c.schema()['receipt_sha256'],
    'h1_sources': c.sources(),
    'single_arm_pins': visual.PINS,
    'composition_recommendation': 'COMPOSITION_NOT_RECOMMENDED',
    'composition': 'COMPOSITION_NOT_AUTHORIZED',
  }


def historical():
  # Cache only while every public input byte and bound source byte remains exact.
  # No private store is scanned; changed files force complete receipt-chain reload.
  stamp = tuple((f.name, p.sha(f.read_bytes())) for f in sorted(p.PUBLIC.glob('*.json')) if not f.name.startswith(('cyber-h1-paired-', 'cyber-h1-comparison-')))
  stamp += tuple(sorted(c.sources().items()))
  return h.clone(_historical(stamp))


def policy():
  evidence = historical()
  return seal(
    {
      'schema': 'CYBER_H1_PAIRED_CAMPAIGN_POLICY_V1',
      'historical': evidence,
      'sources': {n: p.sha((Path(__file__).parent / n).read_bytes()) for n in OWN},
      'campaigns': {k: list(v) for k, v in CAMPAIGNS.items()},
      'baseline_arm': BASELINE,
      'scenario_rows': evidence['scenario_rows'],
      'repeat_count': 2,
      'arm_count': 2,
      'dt_ns': c.DT_NS,
      'phase': 'INPUT/COMMAND K; PLANT COMPLETION K+1',
      'stimulus_schema': 'EXOGENOUS_STIMULUS_SNAPSHOT_V1',
      'observer_feedback_allowed': False,
      'candidate_acceptance': False,
      'frozen_candidate_evaluation': False,
      'tier': TIER,
      'holdout_opening': 'CLOSED',
      'opening_count': 0,
      'calibration_blockers': p.BLOCKERS,
      'experiment_kind': 'FROZEN_STANDALONE_SYNTHETIC_OBSERVATION_NOT_NEW_CANDIDATE_EVALUATION',
    }
  )


def provenance(kind, arm):
  result = dict(c.PROVENANCE)
  if arm == 'TA_B_V0':
    result['controller_limited_torque'] = 'FROZEN_TA_B_RETURN_NORMALIZED_POST_CONTROLLER_OUTPUT'
    result['pre_governor_torque'] = 'FROZEN_TA_B_OUTPUT_NOT_NATIVE_PRE_LIMIT_INTENT'
    result['post_governor_torque'] = 'DISABLED_PASSTHROUGH_EXACT_TA_OUTPUT'
  elif arm == 'SG_A_V0':
    result['post_governor_torque'] = 'FROZEN_SG_A_UNIT_DELTA_PROJECTOR_ORDINARY_SAMPLES_ONLY'
  elif arm != BASELINE:
    raise ValueError('PAIR_NO_CURRENT_OR_THIRD_ARM')
  if kind not in CAMPAIGNS or arm not in (BASELINE, CAMPAIGNS[kind][1]):
    raise ValueError('PAIR_SEPARATE_TA_SG_CAMPAIGNS_ONLY')
  return result


def stimulus(row, scenario, scenario_sha):
  native = row['consumed_input_snapshot']['native_input']
  return {
    'schema': 'EXOGENOUS_STIMULUS_SNAPSHOT_V1',
    'sample_index': row['sample_index'],
    **{k: row[k] for k in ('capture_time_ns', 'decision_time_ns', 'completion_time_ns', 'dt_ns')},
    **{k: native[k] for k in c.INPUTS if k != 'actual_curvature_1pm'},
    'event': row['event'],
    'reset_events': row['reset_events'],
    'scenario': scenario,
    'scenario_sha256': scenario_sha,
  }


def validate_package(package):
  verify(package)
  cfg = package['configs'][0]
  ident = cfg['config']
  kind, arm = ident['campaign_kind'], ident['arm']
  provenance(kind, arm)
  if (
    package['schema'] != 'CYBER_H1_PAIRED_ARM_PACKAGE_V1'
    or package['source_schema_sha256'] != c.schema()['receipt_sha256']
    or package['binding']['tier'] != TIER
    or package['binding']['source_sha256'] != p.sha(p.canonical(package['policy']['sources']))
    or package['policy_sha256'] != package['policy']['receipt_sha256']
    or package['holdout_opening'] != 'CLOSED'
    or package['opening_count'] != 0
  ):
    raise ValueError('PAIR_PACKAGE_SOURCE_TIER_OR_AUTHORITY')
  verify(package['policy'])
  if package['policy'] != policy():
    raise ValueError('PAIR_FIXED_POLICY_DRIFT')
  from openpilot.tools.cyber_autotune.cyber_h1_pair_producer import config as expected_config

  if cfg != expected_config(kind, arm, ident['scenario'], package['policy']):
    raise ValueError('PAIR_FROZEN_ARM_CONFIG_DRIFT')
  if p.sha(p.canonical(ident)) != cfg['config_sha256']:
    raise ValueError('PAIR_CONFIG_DIGEST')
  if ident['arm_identity_sha256'] != p.sha(p.canonical(ident['arm_identity'])):
    raise ValueError('PAIR_ARM_IDENTITY')
  history = package['policy']['historical']
  expected_source = history['h1_sources']
  for name, sha in {**expected_source, **{'openpilot/tools/cyber_autotune/' + k: v for k, v in package['policy']['sources'].items()}}.items():
    if p.sha((Path(__file__).resolve().parents[3] / name).read_bytes()) != sha:
      raise ValueError('PAIR_PINNED_SOURCE_DRIFT')
  spec = next((r for r in package['policy']['scenario_rows'] if r['id'] == ident['scenario']), None)
  if spec is None or ident['scenario_sha256'] != history['sg_binding']['scenario_input_sha256'][ident['scenario']]:
    raise ValueError('PAIR_SCENARIO_IDENTITY')
  count = spec['samples']
  if (
    type(package['row_count']) is not int
    or package['row_count'] != count
    or len(package['rows']) != count
    or package['binding']['expected_rows'] != count
    or len(package['configs']) != 1
  ):
    raise ValueError('PAIR_FULL_FROZEN_HORIZON')
  from openpilot.tools.cyber_autotune.trajectory_v0_screen import scenarios

  frozen_frames = scenarios()[ident['scenario']]
  previous = None
  for i, row in enumerate(package['rows']):
    # Reuse V1 exact common row-schema/timing/null checks on a detached validation
    # copy; original candidate stages/provenance are separately checked below.
    if row['provenance'] != provenance(kind, arm):
      raise ValueError('PAIR_STAGE_PROVENANCE')
    if (
      row['sample_index'] != i
      or row['loop_sequence'] != i + 1
      or row['process_epoch'] != cfg['process_epoch']
      or row['config_sequence'] != 1
      or row['row_sha256'] != h.row_sha(row)
    ):
      raise ValueError('PAIR_ROW_ORDER_OR_DIGEST')
    normalized = h.clone(row)
    normalized['provenance'] = dict(c.PROVENANCE)
    signals = row['signals']
    if (
      signals['controller_limited_torque'] != signals['pre_governor_torque']
      or signals['post_governor_torque'] != signals['final_requested_torque']
      or arm != 'SG_A_V0'
      and signals['pre_governor_torque'] != signals['post_governor_torque']
    ):
      raise ValueError('PAIR_STAGE_IDENTITY')
    for k in c.TORQUES:
      if abs(signals[k]) > 1:
        raise ValueError('PAIR_TORQUE_DOMAIN')
      if k != 'applied_torque':
        normalized['signals'][k] = signals['final_requested_torque']
    normalized['row_sha256'] = h.row_sha(normalized)
    h.validate_row(normalized, package['binding'], cfg)
    native = row['consumed_input_snapshot']['native_input']
    if {k: v for k, v in native.items() if k != 'actual_curvature_1pm'} != {k: v for k, v in frozen_frames[i].items() if k != 'phase'}:
      raise ValueError('PAIR_FROZEN_EXOGENOUS_INPUT_DRIFT')
    events = ['EXPERIMENT_START'] if previous is None else []
    if not native['active'] and (previous is None or previous['active']):
      events.append('INACTIVE')
    if native['steering_pressed'] and (previous is None or not previous['steering_pressed']):
      events.append('STEERING_PRESSED')
    if previous is not None and previous['steering_pressed'] and not native['steering_pressed']:
      events.append('RELEASE')
    if previous is not None and not previous['active'] and native['active']:
      events.append('REENGAGEMENT')
    if row['reset_events'] != events or row['event'] != ('SCENARIO_BOUNDARY' if i == 0 else (events[0] if events else 'ORDINARY')):
      raise ValueError('PAIR_INTERVENTION_RESET_ORDER')
    if i and row['capture_time_ns'] < package['rows'][i - 1]['completion_time_ns']:
      raise ValueError('PAIR_CROSS_LOOP_TIME')
    if i and native['actual_curvature_1pm'] != package['rows'][i - 1]['plant_output']['curvature']:
      raise ValueError('PAIR_OWN_FEEDBACK_ONLY')
    if not i and native['actual_curvature_1pm'] != 0:
      raise ValueError('PAIR_ZERO_INITIAL_PLANT')
    previous = native
  if (
    package['trace_sha256'] != p.sha(p.canonical(package['rows']))
    or package['row_digest_set_sha256'] != p.sha(p.canonical([r['row_sha256'] for r in package['rows']]))
    or package['snapshot_set_sha256'] != p.sha(p.canonical([r['consumed_input_snapshot_sha256'] for r in package['rows']]))
  ):
    raise ValueError('PAIR_TRACE_DIGEST_SET')
  return package


def pair(baseline, candidate):
  for pkg in (baseline, candidate):
    validate_package(pkg)
  a, b = (x['configs'][0]['config'] for x in (baseline, candidate))
  kind = a['campaign_kind']
  if (
    b['campaign_kind'] != kind
    or a['arm'] != BASELINE
    or b['arm'] != CAMPAIGNS[kind][1]
    or a['arm_identity_sha256'] == b['arm_identity_sha256']
    or baseline['configs'][0]['process_epoch'] == candidate['configs'][0]['process_epoch']
  ):
    raise ValueError('PAIR_DISTINCT_TWO_ARM_IDENTITY')
  for key in ('scenario', 'scenario_sha256', 'plant_config_sha256', 'initial_plant_state_sha256', 'profile_sha256', 'scenario_policy_sha256', 'dt_ns'):
    if a[key] != b[key]:
      raise ValueError('PAIR_SHARED_IDENTITY_DRIFT')
  if baseline['policy'] != candidate['policy']:
    raise ValueError('PAIR_POLICY_DRIFT')
  stimuli = []
  for left, right in zip(baseline['rows'], candidate['rows'], strict=True):
    x, y = (stimulus(r, a['scenario'], a['scenario_sha256']) for r in (left, right))
    if p.canonical(x) != p.canonical(y):
      raise ValueError('PAIR_EXOGENOUS_STIMULUS_DRIFT')
    stimuli.append(p.sha(p.canonical(x)))
  return seal(
    {
      'schema': 'CYBER_H1_PAIRED_CAMPAIGN_V1',
      'campaign_id': CAMPAIGNS[kind][0],
      'campaign_type': kind,
      'scenario': a['scenario'],
      'baseline_arm': BASELINE,
      'candidate_arm': CAMPAIGNS[kind][1],
      'historical_verdict': CAMPAIGNS[kind][2],
      'fidelity': TIER,
      'sample_count': len(stimuli),
      'dt_ns': c.DT_NS,
      'duration_ns': len(stimuli) * c.DT_NS,
      'shared_stimulus_set_sha256': p.sha(p.canonical(stimuli)),
      'baseline_trace_receipt_sha256': baseline['receipt_sha256'],
      'candidate_trace_receipt_sha256': candidate['receipt_sha256'],
      'baseline_trace_sha256': baseline['trace_sha256'],
      'candidate_trace_sha256': candidate['trace_sha256'],
      'baseline_arm_identity_sha256': a['arm_identity_sha256'],
      'candidate_arm_identity_sha256': b['arm_identity_sha256'],
      'plant_identity_sha256': a['plant_config_sha256'],
      'initial_plant_state_sha256': a['initial_plant_state_sha256'],
      'profile_sha256': a['profile_sha256'],
      'scenario_policy_sha256': a['scenario_policy_sha256'],
      'scenario_sha256': a['scenario_sha256'],
      'policy_sha256': baseline['policy_sha256'],
      'pairing_sha256': p.sha(p.canonical({'stimuli': stimuli, 'traces': [baseline['trace_sha256'], candidate['trace_sha256']]})),
      'blockers': p.BLOCKERS,
      'holdout_opening': 'CLOSED',
      'opening_count': 0,
    }
  )


def read_package(store):
  from openpilot.tools.cyber_autotune.cyber_h1_visual_catalog import read_json

  root = h.store_path(store).parent
  return validate_package(read_json(root, 'h1-package.json'))


def main():
  import argparse

  parser = argparse.ArgumentParser(description='Verify exact standalone synthetic two-arm pair; no raw logs.')
  parser.add_argument('--baseline-store', required=True)
  parser.add_argument('--candidate-store', required=True)
  args = parser.parse_args()
  print(json.dumps(pair(read_package(args.baseline_store), read_package(args.candidate_store)), sort_keys=True))


if __name__ == '__main__':
  main()
