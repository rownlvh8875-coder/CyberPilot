"""Immutable additive SG aggregate publication; never candidate/reference acceptance."""

import json
from pathlib import Path

from openpilot.tools.cyber_autotune import candidate_architecture as a
from openpilot.tools.cyber_autotune import trajectory_v0_publication as ta
from openpilot.tools.cyber_autotune.native_protocol import digest
from openpilot.tools.cyber_autotune.smoothness_v0_freeze import load as policies
from openpilot.tools.cyber_autotune.smoothness_v0_policy import PUBLIC, seal

PINS = {
  'binding': ('smoothness-v0-execution-binding-v1.json', '44026424a77e204b3f336c7cdf980187441a32f8b37682b9ea55aaff75c61222'),
  'readiness': ('smoothness-v0-readiness-v1.json', '6a658c860c8b201f059c591e6e6168b3131ba73fa45e1a3bbad46bf5d41663e4'),
  'results': ('smoothness-v0-experiment-results-v1.json', '17abb7e82eae7c16c61230299cbb4ae76e2f24af409206922ee2a0decfec96d1'),
}


def build_readiness(results, binding):
  prior = ta.load()['readiness']
  summaries = []
  for row in results['scenarios']:
    arms = row['arms']
    baseline = arms['UPSTREAM_BASELINE']['metrics']
    candidate = arms['SG_V0_CANDIDATE']['metrics']

    def compact(m):
      s = m['smoothness_primary']
      q = s['requested']
      return {
        'requested_derivative_p95_normalized_per_s': q['derivative_abs']['p95'],
        'requested_derivative_max_normalized_per_s': q['derivative_abs']['maximum'],
        'requested_derivative_rms_normalized_per_s': q['derivative_rms'],
        'applied_derivative_p95_normalized_per_s': s['applied']['derivative_abs']['p95'],
        'nonzero_reversals': q['nonzero_sign_reversals'],
        'output_rail_occupancy': q['saturation']['occupancy'],
        'core_input_rail_occupancy': s['pre_governor']['saturation']['occupancy'],
        'governor_limit_occupancy': s['governor_limit']['occupancy'],
        'total_variation': q['total_variation'],
        'high_frequency_energy': q['high_frequency_energy'],
        'tracking_p95_1pm': m['trajectory']['tracking']['p95'],
        'eligible_tracking_coverage': m['coverage'],
        'settling': s['settling'],
      }

    summaries.append(
      {
        'scenario': row['scenario'],
        'baseline': compact(baseline),
        'sg': compact(candidate),
        'effects': arms['SG_V0_CANDIDATE']['effect_vs_baseline'],
        'tracking_p95_direction': 'LOWER'
        if candidate['trajectory']['tracking']['p95'] < baseline['trajectory']['tracking']['p95']
        else 'HIGHER'
        if candidate['trajectory']['tracking']['p95'] > baseline['trajectory']['tracking']['p95']
        else 'EXACT_SAME',
      }
    )
  return seal(
    {
      'schema': 'SMOOTHNESS_V0_READINESS_V1',
      'status': 'SG_STANDALONE_TRADEOFF_ONLY',
      'states': [
        'SG_FAMILY_SELECTED',
        'SG_V0_IMPLEMENTED',
        'SG_STANDALONE_STRUCTURAL_PASS',
        'SG_STANDALONE_EFFECT_PRESENT',
        'SG_STANDALONE_TRADEOFF_ONLY',
        'COMPOSITION_NOT_AUTHORIZED',
        'SEARCH_NOT_AUTHORIZED',
        'FROZEN_EVALUATION_NOT_AUTHORIZED',
      ],
      'family': 'SG-A',
      'structural_status': results['status'],
      'standalone_verdict': 'SG_STANDALONE_TRADEOFF_ONLY',
      'summary': summaries,
      'scenarios': 11,
      'arms': 3,
      'repeats': 2,
      'executions': 66,
      'repeatability': 'EXACT_PASS',
      'selection_frozen_commit': '8cdb4476f',
      'implementation_commit_sha': binding['implementation_commit_sha'],
      'results_sha256': results['receipt_sha256'],
      'execution_binding_sha256': binding['receipt_sha256'],
      'historical_ta_readiness_sha256': prior['receipt_sha256'],
      'ta_interpretation': 'TA_STANDALONE_TRADEOFF_ONLY',
      'historical_verdicts': prior['historical_verdicts'],
      'historical_roles': prior['historical_roles'],
      'v2_historical_violations': 37,
      'reference_track': prior['reference_track'],
      'reference_blocker_graph_sha256': prior['reference_blocker_graph_sha256'],
      'reference_track_modified': False,
      'composition_recommendation': 'COMPOSITION_NOT_RECOMMENDED',
      'recommendation_reason': ('High-speed tracking regression and large descriptive replay displacement ' +
                              'coexist with derivative/saturation reduction; no feedback stability evidence'),
      'ta_enabled': False,
      'composition_authorized': False,
      'search_authorized': False,
      'frozen_evaluation_authorized': False,
      'candidate_acceptance_authorized': False,
      'performance_threshold': None,
      'threshold_status': 'THRESHOLD_UNJUSTIFIED',
      'execution_semantics': 'FROZEN_BASELINE_COMMAND_REPLAY_DESCRIPTIVE_PLANT',
      'feedback_loop_stability_evaluated': False,
      'physical_delay_owner': 'PLANT',
      'limitations': [
        'Small chatter and all observed reversal counts unchanged',
        'Derivative quantile/spectral improvement not a universal mathematical guarantee',
        'Intervention passthrough exempts event steps from ordinary projection step bound',
        'Baseline high/medium-speed plant already oscillatory/saturated; no real vehicle dynamics claim',
        'High-speed same-time peak pose delta61.276370m is descriptive counterevidence, not real vehicle path gain',
        'Event settling unavailable when input lacks final constant span; no zero-fill',
        'No meter-envelope performance classification or weighted score',
      ],
      'source_configuration_changed_after_results': False,
      'private_inputs_opened': False,
      'production_sources_modified': False,
      'independent_meter_result': None,
      'total_physical_bound': None,
      'sealed_reference': 'NOT_GENERATED',
      'vehicle_status': prior['vehicle_status'],
    }
  )


def validate(row):
  if type(row) is not dict or row.get('receipt_sha256') not in {sha for _, sha in PINS.values()}:
    raise ValueError('EXACT_SG_PUBLIC_RECEIPT_REQUIRED')
  if a.hash_object({k: v for k, v in row.items() if k != 'receipt_sha256'}) != row['receipt_sha256']:
    raise ValueError('SG_PUBLICATION_DRIFT')
  return row


def load():
  policies()
  result = {}
  for key, (name, sha) in PINS.items():
    path = PUBLIC / name
    if path.is_symlink() or any(p.is_symlink() for p in path.parents):
      raise ValueError('SG_PUBLICATION_SYMLINK')
    row = validate(json.loads(path.read_bytes()))
    if row['receipt_sha256'] != sha:
      raise ValueError('SG_FILE_BINDING_REQUIRED')
    result[key] = row
  binding = result['binding']
  for name, sha in binding['source_sha256'].items():
    if digest((Path(__file__).parent / name).read_bytes()) != sha:
      raise ValueError('SG_SOURCE_DRIFT')
  for name, sha in binding['native_support_sha256'].items():
    if digest((a.ROOT / name).read_bytes()) != sha:
      raise ValueError('SG_SUPPORT_DRIFT')
  if result['readiness'] != build_readiness(result['results'], binding):
    raise ValueError('SG_READINESS_BINDING_REQUIRED')
  return result
