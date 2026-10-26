"""Explicit manual baseline-only offline observer. Existing experiment sources unmodified."""

from dataclasses import asdict
from pathlib import Path
import platform

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import cyber_lateral_h1_contract as c
from openpilot.tools.cyber_autotune import cyber_lateral_h1_producer as h


def run_once(*, observe=True):
  if type(observe) is not bool:
    raise ValueError('EXACT_OBSERVER_BOOLEAN')
  # Native runtime stays isolated in the already-authorized offline experiment.
  from openpilot.tools.cyber_autotune import smoothness_closed_loop as experiment
  from openpilot.tools.cyber_autotune import simulator_reuse_publication as reuse
  import numpy as np

  reuse.load()
  policy = c.policy()
  runtime = experiment.Arm(c.SCENARIO, experiment.ARMS[0])
  if runtime.governor._mode != 'SG_DISABLED' or type(runtime.core) is not experiment.NativeBaseline:
    raise ValueError('H1_UNCHANGED_BASELINE_DISABLED_GOVERNOR_ONLY')
  config = {
    'native_core': runtime.identity,
    'scenario': c.SCENARIO,
    'scenario_input_sha256': p.sha(p.canonical(runtime.frames)),
    'plant_config_sha256': p.sha(p.canonical(asdict(experiment.PLANT))),
    'governor_mode': 'SG_DISABLED',
    'dt_ns': c.DT_NS,
    'policy_sha256': policy['receipt_sha256'],
    'reset_policy_sha256': experiment.frozen()['config']['receipt_sha256'],
  }
  config_sha = p.sha(p.canonical(config))
  configs = [{'process_epoch': 1, 'config_sequence': 1, 'config': config, 'config_sha256': config_sha}]
  environment = {'python': platform.python_version(), 'numpy': np.__version__, 'machine': platform.machine(), 'clock': 'RELATIVE_INTEGER_NS_NO_RNG'}
  identity = {'source_sha256': policy['source_sha256'], 'config_sha256': config_sha, 'environment_sha256': p.sha(p.canonical(environment)), 'tier': c.TIER}
  binding = c.binding(p.sha(p.canonical(identity)), policy['source_sha256'], len(runtime.frames))
  producer = h.Producer(policy, binding, configs) if observe else None
  rows = []
  for i in range(len(runtime.frames)):
    source = runtime.advance(i)
    rows.append(source)
    if producer is not None:
      original = p.canonical(source)
      row = h.make_row(binding, configs[0], i, source['input'], source['pre'], source['applied'], source, source['reset_events'])
      if (
        row['native_input_sha256'] != source['feedback']['native_input_sha256']
        or source['pre'] != source['requested']
        or source['trace']['pre_governor'] != source['pre']
        or source['trace']['post_governor'] != source['requested']
      ):
        raise ValueError('H1_EXACT_CONSUMED_INPUT_AND_STAGE_BINDING')
      producer.append(row)
      if original != p.canonical(source):
        raise ValueError('H1_OBSERVER_MUTATED_EXPERIMENT')
  experiment.validate_trace(c.SCENARIO, rows, experiment.ARMS[0])
  return rows, producer.finish() if producer is not None else None


def execute(store):
  root = h.store_path(store).parent
  # These immutable receipts are saved BEFORE any controller/plant execution.
  frozen_policy = c.policy()
  p.persist(root / 'cyber-lateral-h1-policy-v1.json', frozen_policy)
  p.persist(root / 'cyber-lateral-h1-schema-v1.json', c.schema())
  if c.policy() != frozen_policy:
    raise ValueError('H1_SAVED_POLICY_DRIFT')
  first_rows, first = run_once()
  second_rows, second = run_once()
  if first['policy'] != frozen_policy or second['policy'] != frozen_policy:
    raise ValueError('H1_SAVED_POLICY_DRIFT')
  from openpilot.tools.cyber_autotune import smoothness_closed_loop as experiment

  plain = experiment.run_arm(c.SCENARIO, experiment.ARMS[0])
  if p.canonical(first) != p.canonical(second) or p.canonical(first_rows) != p.canonical(second_rows) or p.canonical(first_rows) != p.canonical(plain):
    raise ValueError('H1_REPEATABILITY_OR_OBSERVER_NONINTERFERENCE_FAILURE')
  h.persist(root / 'repeat-1', first)
  h.persist(root / 'repeat-2', second)
  from openpilot.tools.cyber_autotune.cyber_lateral_h1_inspector import aggregate

  summary = aggregate(first)
  result = p.seal(
    {
      'schema': 'CYBER_LATERAL_H1_EXECUTION_V1',
      'status': 'CYBER_LATERAL_H1_TRACE_REPEATABLE',
      'executions': 2,
      'unobserved_baseline_executions': 1,
      'experiment_result_sha256': p.sha(p.canonical(first_rows)),
      'observer_removed_result_sha256': p.sha(p.canonical(plain)),
      'experiment_identity_sha256': first['binding']['experiment_sha256'],
      'trace_receipt_sha256': first['receipt_sha256'],
      'trace_sha256': first['trace_sha256'],
      'config_sha256': first['configs'][0]['config_sha256'],
      'policy_sha256': first['policy_sha256'],
      'row_count': first['row_count'],
      'row_bytes_exact': True,
      'snapshot_bytes_exact': True,
      'receipt_exact': True,
      'observer_noninterference': 'EXACT_EXISTING_RUN_ARM_RESULT_BYTES',
      'summary': summary,
      'source_sha256': first['binding']['source_sha256'],
      'calibration_blockers': p.BLOCKERS,
      'holdout_opening': 'CLOSED',
      'opening_count': 0,
      'holdout_opener_implemented': False,
    }
  )
  p.persist(root / 'execution-receipt.json', result)
  return result


def main():
  import argparse
  import json

  parser = argparse.ArgumentParser(description='Explicit synthetic baseline H1 execution only; no raw logs or device.')
  parser.add_argument('--store', required=True, type=Path)
  args = parser.parse_args()
  print(json.dumps(execute(args.store), sort_keys=True, indent=2))


if __name__ == '__main__':
  main()
