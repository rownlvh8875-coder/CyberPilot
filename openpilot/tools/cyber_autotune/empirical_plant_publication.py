"""Exact frozen aggregate receipts. Resealing cannot change empirical evidence."""

import json
from pathlib import Path
from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune.empirical_plant_run import publication_guard, public_shapes

PINS = {
  'empirical-plant-validation-gates-v1.json': '908138c4866860f2a70d23ca773711a071c24960466d5d0ca1fbd63b3f16f48f',
  'empirical-plant-data-policy-v1.json': '7ea3c5f0f6b8165ea102dcc5f4fb127343d487e1819bd858c722d98033914a56',
  'empirical-plant-family-policy-v1.json': 'c1c1d5162e7304b13e11ec60fc92fc0be07c04d494c2b697fb4f00f89424e9c1',
  'empirical-plant-split-v1.json': '7c52c4ca964863dbab5a0a236e4068403fd25d99a69bcd095b813c31fd7e2ada',
  'empirical-plant-alignment-policy-v1.json': '7b8b4bcb66a25dc08d875a3422cbc396b42512f7533a2b3e871a1101253a1dcf',
  'empirical-plant-metric-policy-v1.json': 'e81b457764f1b7cb50ed1b31911d8f976d38fa819cd5dbd28df9564e9525c4a7',
  'real-log-signal-source-v1.json': 'ca01de3be7c30112b9a0c8ac247d63e123742878d0dca1fa15332c64402e0599',
  'empirical-plant-selection-v1.json': '47934437c0abbd9b43e34ad34741a2a0599dc0a45094cecfd1058ebccf33f0f7',
  'empirical-plant-holdout-validation-v1.json': 'df7f73c291057e3c2701387d4622e9a83057ca3b8046732efad48e1289b912fc',
  'real-log-signal-audit-v1.json': '788d9382f669056fb6085c7619bb1f4934e11487f0f4051d733bc9c3ba8de495',
  'descriptive-vs-empirical-plant-v1.json': '27a46ca0a6fdcd509d61ffe94f36dab29ce1e4e7d36619fe78e730807bdc64d8',
  'empirical-plant-readiness-v1.json': 'c58e5da7c9b6056ee97e352a452ece257f4c57d811a25b4c7fc0bffe28564341',
}

EXECUTOR_SHA256 = {
  'empirical_plant_model.py': 'd412012da7a3d3f077b7ecb2c9c9efe64040596d57a64b5b5e46d2d8508bb44a',
  'empirical_plant_policy.py': '3961101927faca0e64a731ff92484d563082390c001988a156056275743034df',
  'empirical_plant_run.py': 'd0d8d310d978cc6da022759584601aaa584e8bb1f12e13901df108bb05e07dda',
  'empirical_plant_signals.py': '0f018b5682f9309f3a913f0e1e8fac6a4a487b2de036c1dadeb50b3ee4a5effd',
}


def validate_pinned(name, row):
  if name not in PINS:
    raise ValueError('EXACT_EMPIRICAL_PUBLICATION_MEMBER_REQUIRED')
  p.verify(row)
  if row['receipt_sha256'] != PINS[name]:
    raise ValueError('EXACT_FROZEN_EMPIRICAL_RECEIPT_REQUIRED')
  if name in public_shapes():
    publication_guard(row, name)
  return row


def load():
  rows = {}
  for name in PINS:
    path = p.PUBLIC / name
    if any(x.is_symlink() for x in (path, *path.parents)):
      raise ValueError('NO_PUBLICATION_SYMLINK')
    rows[name] = validate_pinned(name, json.loads(path.read_bytes()))
  for name, expected in EXECUTOR_SHA256.items():
    if p.sha((Path(__file__).parent / name).read_bytes()) != expected:
      raise ValueError('EMPIRICAL_EXECUTOR_SOURCE_DRIFT')
  for name, expected in [
    ('empirical-plant-data-policy-v1.json', p.policy()),
    ('empirical-plant-family-policy-v1.json', p.family_policy()),
    ('empirical-plant-alignment-policy-v1.json', p.alignment_policy()),
    ('empirical-plant-metric-policy-v1.json', p.metric_policy()),
  ]:
    if rows[name] != expected:
      raise ValueError('FROZEN_EMPIRICAL_POLICY_DRIFT')
  selection = rows['empirical-plant-selection-v1.json']
  validation = rows['empirical-plant-holdout-validation-v1.json']
  readiness = rows['empirical-plant-readiness-v1.json']
  if (
    selection['execution_binding_sha256'] != validation['execution_binding_sha256']
    or readiness['validation_sha256'] != validation['receipt_sha256']
    or readiness['local_model_sha256'] != selection['local_model_sha256']
    or readiness['calibration_blockers'] != p.BLOCKERS
  ):
    raise ValueError('EMPIRICAL_PUBLIC_CROSS_BINDING_DRIFT')
  return rows


def gates(rows):
  validation = rows['empirical-plant-holdout-validation-v1.json']
  regimes = {}
  policy = p.metric_policy()
  for regime, result in validation['results'].items():
    if result['status'] != 'EVALUATED':
      regimes[regime] = {'status': 'UNAVAILABLE', 'better_than_each_naive_primary_rule': False}
      continue
    groups = {'one_step': result['one_step'], '100': result['rollout']['100']}
    comparisons = {}
    for group_name, group in groups.items():
      comparisons[group_name] = {
        naive: {
          metric: group['model'][metric] is not None and group[naive][metric] is not None and group['model'][metric] < group[naive][metric]
          for metric in policy['ready_primary_metrics']
        }
        for naive in p.family_policy()['naive']
      }
    enough = all(group['model']['count'] >= policy['minimum_samples'] for group in groups.values())
    passed = enough and all(value for group in comparisons.values() for naive in group.values() for value in naive.values())
    regimes[regime] = {
      'status': 'DIAGNOSTIC_ONLY',
      'better_than_each_naive_primary_rule': passed,
      'minimum_support_available': enough,
      'directional_comparisons': comparisons,
      'physical_delay_validated': False,
    }
  return p.seal(
    {
      'schema': 'EMPIRICAL_PLANT_VALIDATION_GATES_V1',
      'validation_sha256': validation['receipt_sha256'],
      'metric_policy_sha256': policy['receipt_sha256'],
      'regimes': regimes,
      'full_plant_ready': False,
      'yaw_unit_frame_proven': False,
      'clean_limit_mask_observable': False,
      'route_independent_generalization': False,
      'counterfactual_use_admitted': False,
      'calibration_blockers': p.BLOCKERS,
    }
  )
