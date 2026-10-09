"""Additive closed-loop aggregate evidence; historical replay and blockers immutable."""

import json
from pathlib import Path

from openpilot.tools.cyber_autotune import candidate_architecture as a
from openpilot.tools.cyber_autotune import smoothness_v0_publication as historical
from openpilot.tools.cyber_autotune.native_protocol import digest
from openpilot.tools.cyber_autotune.smoothness_closed_loop_policy import PUBLIC, load as policy, seal
from openpilot.tools.cyber_autotune.smoothness_v0_screen import write

FILES = {'binding': 'smoothness-closed-loop-execution-binding-v1.json', 'results': 'smoothness-closed-loop-results-v1.json',
         'interaction': 'smoothness-feedback-interaction-v1.json', 'readiness': 'smoothness-closed-loop-readiness-v1.json'}


def check_receipt(row):
  if type(row) is not dict or a.hash_object({k: v for k, v in row.items() if k != 'receipt_sha256'}) != row.get('receipt_sha256'):
    raise ValueError('CLOSED_LOOP_PUBLIC_RECEIPT_DRIFT')
  for field in ('qualification_allowed', 'reference_promotable', 'sealed_reference_allowed', 'vehicle_activation_allowed', 'production_authority'):
    if row.get(field) is not False:
      raise ValueError('CLOSED_LOOP_AUTHORITY_FIREWALL')
  return row


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
    path = PUBLIC / name
    if path.is_symlink() or any(p.is_symlink() for p in path.parents):
      raise ValueError('CLOSED_LOOP_PUBLICATION_SYMLINK')
    rows[key] = check_receipt(json.loads(path.read_bytes()))
  for name, sha in rows['binding']['executor_sources'].items():
    if digest((Path(__file__).parent / name).read_bytes()) != sha:
      raise ValueError('CLOSED_LOOP_EXECUTOR_SOURCE_DRIFT')
  if {k: rows[k] for k in ('interaction', 'readiness')} != build(rows['results'], rows['binding']):
    raise ValueError('CLOSED_LOOP_DERIVATIVE_RECEIPT_DRIFT')
  return rows


if __name__ == '__main__':
  result = check_receipt(json.loads((PUBLIC / FILES['results']).read_bytes()))
  binding = check_receipt(json.loads((PUBLIC / FILES['binding']).read_bytes()))
  for key, row in build(result, binding).items():
    write(PUBLIC / FILES[key], row)
