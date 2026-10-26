"""Pure synthetic contract checks and closed metadata plans; no readers/writers or simulator runtime."""

from copy import deepcopy
import math
import re

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import simulator_reuse_contracts as c

SHA = re.compile(r'^[0-9a-f]{64}$')


def keys(row, names):
  if type(row) is not dict or set(row) != set(names):
    raise ValueError('EXACT_CONTRACT_FIELDS_REQUIRED')


def sha(value):
  if type(value) is not str or not SHA.fullmatch(value):
    raise ValueError('EXACT_SHA256_REQUIRED')
  return value


def uint(value):
  if type(value) is not int or not 0 <= value < (1 << 64):
    raise ValueError('UINT64_REQUIRED')
  return value


def snapshot_sha(row):
  return p.sha(p.canonical({k: v for k, v in row.items() if k != 'consumed_input_snapshot_sha256'}))


def validate_observations(traces, configs):
  if type(traces) is not list or not traces or type(configs) is not list:
    raise ValueError('SYNTHETIC_TRACE_AND_CONFIG_LIST_REQUIRED')
  table = {}
  for config in configs:
    keys(config, ('process_epoch', 'config_sequence', 'config', 'config_sha256'))
    identity = uint(config['process_epoch']), uint(config['config_sequence'])
    if config['config_sequence'] == 0 or sha(config['config_sha256']) != p.sha(p.canonical(config['config'])):
      raise ValueError('CONFIG_HASH_OR_SEQUENCE_DRIFT')
    if identity in table:
      raise ValueError('CONFIG_IDENTITY_COLLISION')
    table[identity] = config['config_sha256']
  seen_epochs = set()
  previous = None
  for row in traces:
    keys(
      row,
      (
        'schema',
        'process_epoch',
        'loop_sequence',
        'config_sequence',
        'config_sha256',
        'capture_time_ns',
        'decision_time_ns',
        'source_sha256',
        'signals',
        'services',
        'event',
        'synthetic_only',
        'consumed_input_snapshot_sha256',
      ),
    )
    if row['schema'] != 'CYBER_LATERAL_OBSERVATION_V1' or row['synthetic_only'] is not True or row['event'] not in c.EVENTS:
      raise ValueError('SYNTHETIC_LATERAL_CONTRACT_ONLY')
    epoch, loop, seq = (uint(row[key]) for key in ('process_epoch', 'loop_sequence', 'config_sequence'))
    capture, decision = uint(row['capture_time_ns']), uint(row['decision_time_ns'])
    if capture > decision or table.get((epoch, seq)) != sha(row['config_sha256']):
      raise ValueError('CONFIG_OR_CAUSAL_TIMING_DRIFT')
    sha(row['source_sha256'])
    keys(row['signals'], c.SIGNALS)
    for name, value in row['signals'].items():
      if value is None:
        continue
      if name in c.BOOL_SIGNALS:
        if type(value) is not bool:
          raise ValueError('NULLABLE_BOOLEAN_REQUIRED')
      elif type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError('NULLABLE_FINITE_SIGNAL_REQUIRED')
    keys(row['services'], c.SERVICES)
    for service in row['services'].values():
      keys(service, ('time_ns', 'updated', 'alive', 'freqOk', 'valid'))
      if service['time_ns'] is not None and uint(service['time_ns']) > capture:
        raise ValueError('FUTURE_SOURCE_INPUT')
      if any(value is not None and type(value) is not bool for key, value in service.items() if key != 'time_ns'):
        raise ValueError('NULLABLE_EXACT_MASK_REQUIRED')
    if sha(row['consumed_input_snapshot_sha256']) != snapshot_sha(row):
      raise ValueError('CONSUMED_SNAPSHOT_DRIFT')
    if previous is None or previous['process_epoch'] != epoch:
      if epoch in seen_epochs or loop != 1 or (previous is not None and row['event'] != 'SCENARIO_BOUNDARY'):
        raise ValueError('PROCESS_EPOCH_BOUNDARY_REQUIRED')
      seen_epochs.add(epoch)
    else:
      if (
        loop != previous['loop_sequence'] + 1
        or capture <= previous['capture_time_ns']
        or decision <= previous['decision_time_ns']
        or capture < previous['decision_time_ns']
      ):
        raise ValueError('LOOP_SEQUENCE_OR_CLOCK_DRIFT')
      changed = seq != previous['config_sequence']
      if changed and (seq != previous['config_sequence'] + 1 or row['event'] != 'CONFIG_CHANGE'):
        raise ValueError('EXPLICIT_CONFIG_CHANGE_REQUIRED')
      if not changed and row['event'] == 'CONFIG_CHANGE':
        raise ValueError('CONFIG_CHANGE_WITHOUT_NEW_CONFIG')
    previous = row
  return p.seal(
    {
      'schema': 'CYBER_SYNTHETIC_OBSERVATION_CHECK_V1',
      'status': 'CONTRACT_ONLY',
      'trace_count': len(traces),
      'epoch_count': len(seen_epochs),
      'execution_allowed': False,
      'synthetic_only': True,
      'trace_set_sha256': p.sha(p.canonical(traces)),
    }
  )


def exposure_plan(binding, previous):
  keys(binding, ('campaign_sha256', 'model_set_sha256', 'models', 'purpose', 'admission_sha256', 'metric_policy_sha256'))
  for key in ('campaign_sha256', 'model_set_sha256', 'admission_sha256', 'metric_policy_sha256'):
    sha(binding[key])
  models = binding['models']
  if type(models) is not list or not models or models != sorted(set(models)):
    raise ValueError('EXACT_SORTED_NONEMPTY_MODEL_SET_REQUIRED')
  for model in models:
    sha(model)
  if binding['model_set_sha256'] != p.sha(p.canonical(models)) or binding['purpose'] != 'FUTURE_UNTOUCHED_MODEL_EVALUATION':
    raise ValueError('MODEL_SET_OR_PURPOSE_DRIFT')
  if type(previous) is not list or len(previous) > 1:
    raise ValueError('ONE_IMMUTABLE_CLOSED_PLAN_ONLY')
  result = p.seal(
    {
      'schema': 'CYBER_HOLDOUT_EXPOSURE_PLAN_V1',
      'binding': deepcopy(binding),
      'binding_sha256': p.sha(p.canonical(binding)),
      'state': 'CLOSED',
      'opening_count': 0,
      'opening_receipt_sha256': None,
      'previous_receipt_sha256': None,
      'opening_allowed': False,
      'execution_allowed': False,
      'package_status': 'CLOSED_MISSING_ADMISSIBLE_MODEL',
    }
  )
  if previous and p.verify(previous[0]) != result:
    raise ValueError('EXPOSURE_IDENTITY_OR_OPENING_DRIFT')
  return result


def validate_claim(tier, claim):
  allowed = {
    'T0_REPLAY': {'REPLAY_CONSISTENCY'},
    'T1_DESCRIPTIVE_COUNTERFACTUAL': {'REPLAY_CONSISTENCY', 'DESCRIPTIVE_COUNTERFACTUAL', 'FINITE_HORIZON_DIAGNOSTIC'},
  }
  if tier not in allowed or claim not in allowed[tier]:
    raise ValueError('CLAIM_EXCEEDS_CURRENT_EVIDENCE_OR_AUTHORITY')
  return p.seal(
    {
      'schema': 'CYBER_SIMULATION_CLAIM_PLAN_V1',
      'tier': tier,
      'claim': claim,
      'status': 'CONTRACT_ONLY',
      'execution_allowed': False,
      'evidence_promoted': False,
    }
  )


def visual_plan(manifests, *, host='127.0.0.1'):
  if host != '127.0.0.1' or type(manifests) is not list or len(manifests) != 3:
    raise ValueError('LOOPBACK_EXACT_THREE_ARMS_REQUIRED')
  if {row.get('arm') for row in manifests} != set(c.ARMS):
    raise ValueError('BASELINE_CURRENT_CANDIDATE_REQUIRED')
  grid = None
  for row in manifests:
    keys(row, ('arm', 'source_receipt_sha256', 'time_grid', 'tier', 'provenance', 'field_map'))
    sha(row['source_receipt_sha256'])
    keys(row['time_grid'], ('count', 'dt_ns', 'origin_ns'))
    for value in row['time_grid'].values():
      uint(value)
    if row['time_grid']['count'] == 0 or row['time_grid']['dt_ns'] == 0 or row['time_grid']['origin_ns'] != 0:
      raise ValueError('RELATIVE_NONEMPTY_INTEGER_GRID_REQUIRED')
    if grid is not None and grid != row['time_grid']:
      raise ValueError('IDENTICAL_TIME_GRID_REQUIRED')
    grid = row['time_grid']
    if row['provenance'] != 'PUBLIC_SYNTHETIC_RECEIPT_ONLY' or row['tier'] not in c.TIERS[:2]:
      raise ValueError('NO_PRIVATE_DATA_OR_HIGHER_TIER_PROMOTION')
    keys(row['field_map'], c.VISUAL_FIELDS)
    # Schema bindings are intentionally unresolved. No guessed JSON pointers, frame conversion or field coercion.
    if any(value is not None for value in row['field_map'].values()):
      raise ValueError('SOURCE_SPECIFIC_FRAME_ADAPTER_NOT_IMPLEMENTED')
  return p.seal(
    {
      'schema': 'CYBER_VISUAL_ADAPTER_PLAN_V1',
      'status': 'CONTRACT_ONLY',
      'arms': deepcopy(sorted(manifests, key=lambda row: row['arm'])),
      'frame_mapping_sha256': p.sha(p.canonical(sorted(manifests, key=lambda row: row['arm']))),
      'execution_allowed': False,
      'frames_converted': False,
      'server_implemented': False,
      'blockers': p.BLOCKERS,
      'verdict': 'NO_NEW_CANDIDATE_OR_MODEL_EVALUATION',
      'host': host,
      'external_assets_allowed': False,
    }
  )
