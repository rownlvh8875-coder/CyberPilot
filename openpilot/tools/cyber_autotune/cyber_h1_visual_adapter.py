"""Exact pinned H1 synthetic rows to visual frames; no execution or raw reader."""

import json
from pathlib import Path

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import cyber_lateral_h1_contract as h1
from openpilot.tools.cyber_autotune import cyber_lateral_h1_producer as producer
from openpilot.tools.cyber_autotune import cyber_lateral_h1_inspector as inspector
from openpilot.tools.cyber_autotune import cyber_lateral_h1_publication as source
from openpilot.tools.cyber_autotune import simulator_reuse_publication as reuse

ARM = 'UPSTREAM_BASELINE_CLOSED_LOOP'
SCENARIO = 'driver_events'
COUNT = 800
EXPECTED_FRAMES_SHA256 = '455f6b208b650ab24d7384aa00bfad66766de20f9b8da777dd12d2c85f2b0520'  # Exact pinned synthetic row conversion.
PAGE_SIZE = 100
TIER = 'T1_DESCRIPTIVE_COUNTERFACTUAL'
REASON = 'NO_EXACT_PAIRED_CURRENT_AND_CANDIDATE_H1_TRACES'
SIGNALS = {
  'desired_curvature_1pm': 'desired_curvature',
  'actual_curvature_pre_step_1pm': 'actual_curvature',
  'speed_mps': 'speed_mps',
  'roll_rad': 'roll_rad',
  'active': 'active',
  'steering_pressed': 'steeringPressed',
  'safety_limited': 'safety_limited',
  'curvature_limited': 'curvature_limited',
  'requested_pre_limit_torque': 'requested_torque',
  'pre_limit_torque': 'pre_limit_torque',
  'controller_limited_torque': 'controller_limited_torque',
  'pre_governor_torque': 'pre_governor_torque',
  'post_governor_torque': 'post_governor_torque',
  'final_requested_torque': 'final_requested_torque',
  'torque_output_can': 'torqueOutputCan',
  'normalized_rail_state': 'saturation_state',
  'applied_torque': 'applied_torque',
  'steering_angle_deg': 'steering_angle_deg',
  'steering_rate_deg_s': 'steering_rate_deg_s',
  'driver_torque': 'driver_torque',
}
PLANT = {
  'curvature_post_step_1pm': 'curvature',
  'yaw_rate_post_step_rad_s': 'yaw_rate',
  'heading_post_step_rad': 'heading',
  'pose_x_post_step_m': 'pose_x',
  'pose_y_post_step_m': 'pose_y',
}
IDENTITY = ('sample_index', 'process_epoch', 'loop_sequence', 'config_sequence', 'config_sha256', 'row_sha256', 'consumed_input_snapshot_sha256')
TIMING = ('capture_time_ns', 'decision_time_ns', 'completion_time_ns')
PIN_NAMES = ('cyber-visual-adapter-contract-v1.json', 'cyber-simulation-fidelity-contract-v1.json')


def mapping():
  return {
    'signals': SIGNALS,
    'plant_output': PLANT,
    'identity': list(IDENTITY),
    'timing': list(TIMING),
    'input_phase': 'CAPTURE_SAMPLE_K',
    'command_phase': 'DECISION_SAMPLE_K',
    'plant_phase': 'COMPLETION_K_PLUS_1',
    'conversion': 'EXACT_COPY_NO_INTERPOLATION_RESAMPLING_FILL_OR_RECONSTRUCTION',
  }


def policy():
  root = Path(__file__).parent
  return p.seal(
    {
      'schema': 'CYBER_H1_VISUAL_FRAMESET_POLICY_V1',
      'historical_h1_pins': source.PINS,
      'historical_contract_pins': {k: reuse.PINS[k] for k in PIN_NAMES},
      'source_files': {k: p.sha((root / k).read_bytes()) for k in ('cyber_h1_visual_adapter.py', 'cyber_h1_visual_catalog.py')},
      'frame_mapping_sha256': p.sha(p.canonical(mapping())),
      'tier': TIER,
      'arm': ARM,
      'samples': COUNT,
      'expected_frames_sha256': EXPECTED_FRAMES_SHA256,
      'dt_ns': h1.DT_NS,
      'page_size': PAGE_SIZE,
      'source': 'EXPLICIT_EXTERNAL_SEALED_SYNTHETIC_PACKAGE_ONLY',
      'comparison_ready': False,
      'comparison_reason': REASON,
      'holdout_opening': 'CLOSED',
      'opening_count': 0,
    }
  )


def schema():
  return p.seal(
    {
      'schema': 'CYBER_H1_VISUAL_FRAME_SCHEMA_V1',
      'mapping': mapping(),
      'field_names': [
        *IDENTITY,
        *TIMING,
        'frame_index',
        'relative_time_s',
        'dt_s',
        *SIGNALS,
        *PLANT,
        'event',
        'reset_events',
        'provenance',
        'unavailable',
        'service_health',
      ],
      'null_fields': {key: h1.UNAVAILABLE[value] for key, value in SIGNALS.items() if value in h1.UNAVAILABLE},
      'phase_semantics': 'INPUT/COMMAND K; PLANT AT COMPLETION K+1; NEVER SAME-TIME MEASUREMENT',
      'tier': TIER,
      'private_rows_publication': False,
    }
  )


def validate_source(package):
  pinned = source.load()
  producer.verify_package(package)
  expected = pinned['cyber-lateral-h1-synthetic-trace-v1.json']
  actual = inspector.aggregate(package)
  for key in (
    'row_count',
    'trace_sha256',
    'trace_receipt_sha256',
    'experiment_identity_sha256',
    'config_sha256',
    'policy_sha256',
    'consumed_snapshot_set_sha256',
    'complete_row_digest_set_sha256',
    'tier',
  ):
    if actual[key] != expected[key]:
      raise ValueError('VISUAL_PINNED_SOURCE_DRIFT')
  if package['row_count'] != COUNT or package['policy'] != pinned['cyber-lateral-h1-policy-v1.json']:
    raise ValueError('VISUAL_SOURCE_ROW_OR_POLICY_DRIFT')
  return pinned


def load_source(store):
  path = producer.store_path(store)
  if not path.is_file() or path.stat().st_size > inspector.MAX_PACKAGE_BYTES:
    raise ValueError('VISUAL_SOURCE_ROWS_UNAVAILABLE')
  try:
    package = json.loads(path.read_bytes())
    validate_source(package)
  except (KeyError, TypeError, json.JSONDecodeError) as exc:
    raise ValueError('VISUAL_SOURCE_ROWS_UNAVAILABLE') from exc
  return package


def frame(row):
  """Copy values only after whole-source validation; no observer/model invocation."""
  result = {k: row[k] for k in (*IDENTITY, *TIMING)}
  result.update({k: row['signals'][v] for k, v in SIGNALS.items()})
  result.update({k: row['plant_output'][v] for k, v in PLANT.items()})
  result.update(
    {
      'frame_index': row['sample_index'],
      'relative_time_s': row['capture_time_ns'] / 1e9,
      'dt_s': row['dt_ns'] / 1e9,
      'event': row['event'],
      'reset_events': producer.clone(row['reset_events']),
      'provenance': {
        **{k: row['provenance'][v] for k, v in SIGNALS.items()},
        **dict.fromkeys(PLANT, 'OWN_DESCRIPTIVE_PLANT_POST_STEP_NOT_PHYSICAL_MEASUREMENT'),
      },
      'unavailable': {k: row['unavailable'][v] for k, v in SIGNALS.items() if v in row['unavailable']},
      'service_health': producer.clone(row['service_health']),
    }
  )
  return result


def convert(package):
  pinned = validate_source(package)
  frames = [frame(row) for row in package['rows']]
  return p.seal(
    {
      'schema': 'CYBER_H1_VISUAL_FRAMESET_V1',
      'run_id': p.sha(p.canonical({'trace': package['trace_sha256'], 'mapping': mapping(), 'policy': policy()['receipt_sha256']})),
      'source_trace_sha256': package['trace_sha256'],
      'source_receipt_sha256': package['receipt_sha256'],
      'source_schema_sha256': pinned['cyber-lateral-h1-schema-v1.json']['receipt_sha256'],
      'source_config_sha256': package['configs'][0]['config_sha256'],
      'source_sha256': package['binding']['source_sha256'],
      'source_experiment_sha256': package['binding']['experiment_sha256'],
      'source_row_digest_set_sha256': p.sha(p.canonical([r['row_sha256'] for r in frames])),
      'source_snapshot_digest_set_sha256': p.sha(p.canonical([r['consumed_input_snapshot_sha256'] for r in frames])),
      'frame_mapping_sha256': p.sha(p.canonical(mapping())),
      'policy_sha256': policy()['receipt_sha256'],
      'evidence_tier': TIER,
      'verdict': 'SYNTHETIC_BASELINE_OBSERVATION_ONLY_NOT_ACCEPTANCE',
      'blockers': p.BLOCKERS,
      'arm_count': 1,
      'arms': [ARM],
      'scenario': SCENARIO,
      'frame_count': COUNT,
      'origin_time_ns': 0,
      'dt_ns': h1.DT_NS,
      'duration_ns': COUNT * h1.DT_NS,
      'coverage': {'input_rows': COUNT, 'output_frames': COUNT, 'dropped': 0, 'filled': 0, 'interpolated': 0},
      'unavailable_fields': frames[0]['unavailable'],
      'comparison_ready': False,
      'comparison_reason': REASON,
      'holdout_opening': 'CLOSED',
      'opening_count': 0,
      'frames': frames,
      'frames_sha256': p.sha(p.canonical(frames)),
    }
  )


def validate_frameset(fs):
  p.verify(fs)
  names = (
    'schema',
    'run_id',
    'source_trace_sha256',
    'source_receipt_sha256',
    'source_schema_sha256',
    'source_config_sha256',
    'source_sha256',
    'source_experiment_sha256',
    'source_row_digest_set_sha256',
    'source_snapshot_digest_set_sha256',
    'frame_mapping_sha256',
    'policy_sha256',
    'evidence_tier',
    'verdict',
    'blockers',
    'arm_count',
    'arms',
    'scenario',
    'frame_count',
    'origin_time_ns',
    'dt_ns',
    'duration_ns',
    'coverage',
    'unavailable_fields',
    'comparison_ready',
    'comparison_reason',
    'holdout_opening',
    'opening_count',
    'frames',
    'frames_sha256',
    *p.FIREWALL,
    'receipt_sha256',
  )
  producer.keys(fs, names)
  expected = source.load()['cyber-lateral-h1-synthetic-trace-v1.json']
  for name in ('arm_count', 'frame_count', 'origin_time_ns', 'dt_ns', 'duration_ns', 'opening_count'):
    if type(fs[name]) is not int:
      raise ValueError('VISUAL_INTEGER_METADATA')
  if type(fs['coverage']) is not dict or any(type(v) is not int for v in fs['coverage'].values()):
    raise ValueError('VISUAL_INTEGER_COVERAGE')
  if (
    fs['schema'] != 'CYBER_H1_VISUAL_FRAMESET_V1'
    or fs['frames_sha256'] != EXPECTED_FRAMES_SHA256
    or fs['source_schema_sha256'] != source.PINS['cyber-lateral-h1-schema-v1.json']
    or fs['source_sha256'] != h1.policy()['source_sha256']
    or fs['source_experiment_sha256'] != expected['experiment_identity_sha256']
    or fs['source_row_digest_set_sha256'] != expected['complete_row_digest_set_sha256']
    or fs['source_snapshot_digest_set_sha256'] != expected['consumed_snapshot_set_sha256']
    or fs['origin_time_ns'] != 0
    or fs['dt_ns'] != h1.DT_NS
    or fs['duration_ns'] != COUNT * h1.DT_NS
    or fs['scenario'] != SCENARIO
    or fs['blockers'] != p.BLOCKERS
    or fs['coverage'] != {'input_rows': 800, 'output_frames': 800, 'dropped': 0, 'filled': 0, 'interpolated': 0}
    or fs['unavailable_fields'] != schema()['null_fields']
    or fs['run_id'] != p.sha(p.canonical({'trace': fs['source_trace_sha256'], 'mapping': mapping(), 'policy': policy()['receipt_sha256']}))
    or fs['verdict'] != 'SYNTHETIC_BASELINE_OBSERVATION_ONLY_NOT_ACCEPTANCE'
    or fs['policy_sha256'] != policy()['receipt_sha256']
    or fs['frame_mapping_sha256'] != p.sha(p.canonical(mapping()))
    or fs['source_trace_sha256'] != expected['trace_sha256']
    or fs['source_receipt_sha256'] != expected['trace_receipt_sha256']
    or fs['source_config_sha256'] != expected['config_sha256']
    or fs['evidence_tier'] != TIER
    or fs['arm_count'] != 1
    or fs['arms'] != [ARM]
    or fs['frame_count'] != COUNT
    or len(fs['frames']) != COUNT
    or fs['comparison_ready'] is not False
    or fs['comparison_reason'] != REASON
    or fs['holdout_opening'] != 'CLOSED'
    or fs['opening_count'] != 0
    or fs['frames_sha256'] != p.sha(p.canonical(fs['frames']))
  ):
    raise ValueError('VISUAL_FRAMESET_INTEGRITY')
  frame_schema = schema()
  for i, f in enumerate(fs['frames']):
    if (
      set(f) != set(frame_schema['field_names'])
      or f['frame_index'] != i
      or f['sample_index'] != i
      or f['capture_time_ns'] != i * h1.DT_NS
      or f['completion_time_ns'] != (i + 1) * h1.DT_NS
      or f['decision_time_ns'] != i * h1.DT_NS + 1
      or f['relative_time_s'] != i * h1.DT_NS / 1e9
      or f['dt_s'] != 0.01
      or any(f[k] is not None for k in frame_schema['null_fields'])
      or f['unavailable'] != frame_schema['null_fields']
      or f['service_health'] != h1.service_health()
    ):
      raise ValueError('VISUAL_EXACT_FRAME_SCHEMA_PHASE_NULL')
  if (
    p.sha(p.canonical([r['row_sha256'] for r in fs['frames']])) != expected['complete_row_digest_set_sha256']
    or p.sha(p.canonical([r['consumed_input_snapshot_sha256'] for r in fs['frames']])) != expected['consumed_snapshot_set_sha256']
  ):
    raise ValueError('VISUAL_ORIGIN_SET_DRIFT')
  return fs


def main():
  import argparse
  from openpilot.tools.cyber_autotune import cyber_h1_visual_catalog as cat

  parser = argparse.ArgumentParser(description='Explicit synthetic H1 source to immutable local visual pages; no raw logs.')
  parser.add_argument('--source-store', required=True, type=Path)
  parser.add_argument('--output-store', required=True, type=Path)
  args = parser.parse_args()
  result = cat.persist(args.output_store, convert(load_source(args.source_store)))
  print(json.dumps({'run_id': result['run_id'], 'frame_count': result['frame_count'], 'receipt_sha256': result['receipt_sha256']}))


if __name__ == '__main__':
  main()
