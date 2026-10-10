"""Additive closed-loop aggregate evidence; historical replay and blockers immutable."""

import json
from pathlib import Path

from openpilot.tools.cyber_autotune import candidate_architecture as a
from openpilot.tools.cyber_autotune import smoothness_v0_publication as historical
from openpilot.tools.cyber_autotune.native_protocol import digest
from openpilot.tools.cyber_autotune.smoothness_closed_loop_policy import PUBLIC, load as policy, seal

FILES = {'binding': 'smoothness-closed-loop-execution-binding-v1.json', 'results': 'smoothness-closed-loop-results-v1.json',
         'interaction': 'smoothness-feedback-interaction-v1.json', 'readiness': 'smoothness-closed-loop-readiness-v1.json'}

TRANSPORT_SHA256 = 'f9c542fcbdfeccce49b738e6290be6961b30f891c9e0c16bb3111b88091cc646'

PINS = {
  'binding': '046aaec7019f3aa8125326f95b0df7ad8bdbef1813f3d2037db37fccccb8dc0e',
  'results': 'e2369657aa47cb447bdfbaa1dd72bb7eddc712b0747f34d64a94503e54ca5818',
  'interaction': '667c6b36f590c6bc4b9a19c6899024461498a812bc147c3622c3e5e359958f11',
  'readiness': '0326dad0852f57d04615f66975fcb879ba248464d05709b3915e7b3cb8f3657b',
}


def validate_pinned(key, row):
  check_receipt(row)
  if row['receipt_sha256'] != PINS[key]:
    raise ValueError('EXACT_FROZEN_CLOSED_LOOP_RECEIPT_REQUIRED')
  return row


def check_receipt(row):
  if type(row) is not dict or a.hash_object({k: v for k, v in row.items() if k != 'receipt_sha256'}) != row.get('receipt_sha256'):
    raise ValueError('CLOSED_LOOP_PUBLIC_RECEIPT_DRIFT')
  for field in ('qualification_allowed', 'reference_promotable', 'sealed_reference_allowed', 'vehicle_activation_allowed', 'production_authority'):
    if row.get(field) is not False:
      raise ValueError('CLOSED_LOOP_AUTHORITY_FIREWALL')
  return row



def result_transport(full):
  """Lossless publication packaging, without rerunning or reducing frozen evidence."""
  validate_pinned('results', full)
  shards = {}
  entries = []
  for row in full['scenarios']:
    name = f"smoothness-closed-loop-result-{row['scenario']}-v1.json"
    shard = seal({'schema': 'SMOOTHNESS_CLOSED_LOOP_SCENARIO_PUBLICATION_V1',
                  'full_result_receipt_sha256': PINS['results'], 'scenario_result': row})
    shards[name] = shard
    entries.append({'scenario': row['scenario'], 'file': name, 'receipt_sha256': shard['receipt_sha256']})
  manifest = seal({'schema': 'SMOOTHNESS_CLOSED_LOOP_RESULTS_PUBLICATION_MANIFEST_V1',
                   'full_result_receipt_sha256': PINS['results'],
                   'header': {k: v for k, v in full.items() if k not in ('scenarios', 'receipt_sha256')},
                   'scenario_shards': entries})
  return manifest, shards


def reconstruct_result(manifest, shards):
  check_receipt(manifest)
  if manifest.get('schema') != 'SMOOTHNESS_CLOSED_LOOP_RESULTS_PUBLICATION_MANIFEST_V1':
    raise ValueError('RESULT_TRANSPORT_SCHEMA')
  expected = [r['id'] for r in policy()['policy']['scenario_rows']]
  entries = manifest.get('scenario_shards', [])
  if [e.get('scenario') for e in entries] != expected:
    raise ValueError('RESULT_TRANSPORT_SCENARIOS')
  names = [f'smoothness-closed-loop-result-{name}-v1.json' for name in expected]
  if [e.get('file') for e in entries] != names or set(shards) != set(names):
    raise ValueError('RESULT_TRANSPORT_PATH_OR_MEMBERS')
  rows = []
  for entry in entries:
    shard = check_receipt(shards[entry['file']])
    if shard['receipt_sha256'] != entry['receipt_sha256']:
      raise ValueError('RESULT_TRANSPORT_SHARD_DRIFT')
    rows.append(shard['scenario_result'])
  full = {**manifest['header'], 'scenarios': rows, 'receipt_sha256': PINS['results']}
  validate_pinned('results', full)
  if result_transport(full) != (manifest, shards):
    raise ValueError('RESULT_TRANSPORT_CANONICAL_DRIFT')
  return full


def read_public(name):
  path = PUBLIC / name
  if path.is_symlink() or any(p.is_symlink() for p in path.parents):
    raise ValueError('CLOSED_LOOP_PUBLICATION_SYMLINK')
  return json.loads(path.read_bytes())


def build(results, binding):
  check_receipt(results)
  check_receipt(binding)
  if results['execution_binding_sha256'] != binding['receipt_sha256']:
    raise ValueError('EXACT_CLOSED_LOOP_EXECUTION_BINDING_REQUIRED')
  old = historical.load()
  prior = old['readiness']
  interaction = seal({
    'schema': 'SMOOTHNESS_FEEDBACK_INTERACTION_V1', 'results_sha256': results['receipt_sha256'],
    'execution_binding_sha256': binding['receipt_sha256'],
    'classification': results['feedback_interaction'], 'scope': 'DESCRIPTIVE_CLOSED_LOOP_ONLY',
    'scenarios': [{'scenario': r['scenario'], **r['interaction']} for r in results['scenarios']],
    'historical_replay_sha256': old['results']['receipt_sha256'],
    'historical_recalculated': False, 'stability_proof': False, 'performance_threshold': None})
  readiness = seal({
    'schema': 'SMOOTHNESS_CLOSED_LOOP_READINESS_V1', 'status': results['standalone_verdict'],
    'structural_status': results['status'], 'feedback_interaction': results['feedback_interaction'],
    'states': [results['status'], results['standalone_verdict'], 'COMPOSITION_NOT_AUTHORIZED',
               'SEARCH_NOT_AUTHORIZED', 'FROZEN_EVALUATION_NOT_AUTHORIZED'],
    'composition_recommendation': results['composition_recommendation'],
    'results_sha256': results['receipt_sha256'], 'execution_binding_sha256': binding['receipt_sha256'],
    'interaction_sha256': interaction['receipt_sha256'],
    'repeatability': results['repeatability'], 'executions': results['executions'],
    'historical_sg_receipts': {k: v['receipt_sha256'] for k, v in old.items()},
    'historical_sg_interpretation': 'SG_STANDALONE_TRADEOFF_ONLY',
    'ta_interpretation': prior['ta_interpretation'], 'historical_verdicts': prior['historical_verdicts'],
    'historical_roles': prior['historical_roles'], 'v2_historical_violations': 37,
    'reference_track': prior['reference_track'], 'reference_blocker_graph_sha256': prior['reference_blocker_graph_sha256'],
    'reference_track_modified': False, 'ta_enabled': False, 'composition_authorized': False,
    'search_authorized': False, 'frozen_evaluation_authorized': False, 'candidate_acceptance_authorized': False,
    'stability_proof': False, 'scope': 'FINITE_HORIZON_CLOSED_LOOP_STABILITY_DIAGNOSTIC',
    'limitations': ['Bounded input plant containment is not feedback convergence or real vehicle stability',
                    'Sustained oscillation and saturation can remain within source-derived envelope',
                    'Quarter blocks have unequal demand; only exact equivalent blocks support descriptive growth flags',
                    'No search, no changed SG config or metric policy, no new physical reference',
                    'No performance thresholds justified; no weighted objective score'],
    'independent_meter_result': None, 'total_physical_bound': None,
    'sealed_reference': 'NOT_GENERATED', 'vehicle_status': prior['vehicle_status'],
    'private_inputs_opened': False, 'production_sources_modified': False})
  return {'interaction': interaction, 'readiness': readiness}


def load():
  policy()
  rows = {}
  for key, name in FILES.items():
    row = read_public(name)
    if key == 'results':
      check_receipt(row)
      if row['receipt_sha256'] != TRANSPORT_SHA256:
        raise ValueError('RESULT_TRANSPORT_PIN_DRIFT')
      names = [f"smoothness-closed-loop-result-{r['id']}-v1.json" for r in policy()['policy']['scenario_rows']]
      row = reconstruct_result(row, {n: read_public(n) for n in names})
    rows[key] = validate_pinned(key, row)
  for name, sha in rows['binding']['executor_sources'].items():
    if digest((Path(__file__).parent / name).read_bytes()) != sha:
      raise ValueError('CLOSED_LOOP_EXECUTOR_SOURCE_DRIFT')
  if {k: rows[k] for k in ('interaction', 'readiness')} != build(rows['results'], rows['binding']):
    raise ValueError('CLOSED_LOOP_DERIVATIVE_RECEIPT_DRIFT')
  return rows


if __name__ == '__main__':
  load()
