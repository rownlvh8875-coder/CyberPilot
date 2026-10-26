"""Explicit frozen TA-B / SG-A own-feedback campaigns; detached H1 V1 observers."""

from dataclasses import asdict
from pathlib import Path
import platform

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import cyber_lateral_h1_contract as c
from openpilot.tools.cyber_autotune import cyber_lateral_h1_producer as h
from openpilot.tools.cyber_autotune import cyber_h1_pairing as q


class DisabledPassthrough:
  """Exact stateless disabled-stage contract; never invokes SG-A."""

  def __init__(self, source, config):
    self.source, self.config = source, config
    self.last_output = None

  def update(self, command, intervention):
    from openpilot.tools.cyber_autotune.candidate_role_contracts import GovernorCommand, InterventionInput, FinalOfflineTorqueCommand

    if (
      type(command) is not GovernorCommand
      or type(intervention) is not InterventionInput
      or command.core_source_sha256 != self.source
      or command.core_config_sha256 != self.config
    ):
      raise ValueError('PAIR_DISABLED_STAGE_CORE_IDENTITY')
    identity = p.sha(p.canonical({'mode': 'SG_DISABLED', 'source': self.source, 'config': self.config}))
    out = FinalOfflineTorqueCommand(
      command.normalized_torque, command.normalized_torque, command.normalized_torque, (), 'DISABLED_EXACT_PASSTHROUGH', self.source, self.config, identity
    )
    self.last_output = out
    return out


class TAArm:
  """Frozen TA standalone call path; each instance owns core/plant/pose/history."""

  def __init__(self, scenario):
    from openpilot.tools.cyber_autotune import trajectory_v0_screen as ta
    from openpilot.tools.cyber_autotune.trajectory_authority_core import Core
    from openpilot.tools.cyber_autotune.curvature_yaw_plant import CurvatureYawPlantState

    self.core = Core('CANONICAL_V0')
    self.governor = DisabledPassthrough(self.core.source_sha256, self.core.config_sha256)
    self.prior = None
    self.frames = ta.scenarios()[scenario]
    self.state = CurvatureYawPlantState(0.0, 0.0, tuple(0.0 for _ in range(ta.PLANT.delay_steps)))
    self.pose = (0.0, 0.0, 0.0)
    self.index = 0

  def advance(self, index):
    from openpilot.tools.cyber_autotune.smoothness_v0_screen import step
    from openpilot.tools.cyber_autotune.candidate_role_contracts import TrajectoryInput

    if type(index) is not int or index != self.index:
      raise ValueError('PAIR_EXACT_NEXT_SAMPLE')
    frame = self.frames[index]
    ti = TrajectoryInput(actual_curvature_1pm=self.state.curvature_1pm, **{k: v for k, v in frame.items() if k != 'phase'})
    out = self.core.update(ti)
    from openpilot.tools.cyber_autotune.candidate_role_contracts import InterventionInput

    intervention = InterventionInput(
      ti.time_s,
      ti.dt_s,
      ti.active,
      ti.steering_pressed,
      self.prior is not None and self.prior.steering_pressed and not ti.steering_pressed,
      self.prior is not None and not self.prior.active and ti.active,
    )
    final = self.governor.update(out.for_governor(), intervention)
    self.prior = ti
    self.state, self.pose, obs = step(self.state, final.final_requested_torque, frame, self.pose)
    self.index += 1
    return {
      'index': index,
      'input': asdict(ti),
      'phase': frame['phase'],
      **obs,
      'saturation': out.saturation_intent,
      'reset_events': self.core.trace['reset_events'],
      'trace': h.clone(self.core.trace),
    }


def arm_identity(kind, arm, context):
  q.provenance(kind, arm)
  hist = context['historical']
  return {
    'core': 'TA_B_V0_CANONICAL' if arm == 'TA_B_V0' else 'UNCHANGED_NATIVE_BASELINE',
    'governor': 'SG_A_V0_CANONICAL' if arm == 'SG_A_V0' else 'SG_DISABLED',
    'core_source_sha256': hist['h1_sources']['openpilot/tools/cyber_autotune/trajectory_authority_core.py'],
    'core_config_sha256': hist['ta_frozen_receipts']['config'] if arm == 'TA_B_V0' else hist['sg_binding']['baseline_core_identity']['config_sha256'],
    'governor_config_sha256': hist['sg_frozen_receipts']['config'],
    'candidate_arm': arm,
  }


def config(kind, arm, scenario, context):
  from openpilot.tools.cyber_autotune.trajectory_v0_screen import PLANT

  identity = arm_identity(kind, arm, context)
  data = {
    'campaign_kind': kind,
    'arm': arm,
    'scenario': scenario,
    'arm_identity': identity,
    'arm_identity_sha256': p.sha(p.canonical(identity)),
    'scenario_sha256': context['historical']['sg_binding']['scenario_input_sha256'][scenario],
    'scenario_policy_sha256': context['historical']['scenario_policy_sha256'],
    'plant_config_sha256': p.sha(p.canonical(asdict(PLANT))),
    'initial_plant_state_sha256': p.sha(p.canonical({'curvature': 0.0, 'yaw_rate': 0.0, 'delay': [0.0] * PLANT.delay_steps, 'pose': [0.0, 0.0, 0.0]})),
    'profile_sha256': context['historical']['sg_binding']['car_params_sha256'],
    'dt_ns': c.DT_NS,
  }
  return {
    'process_epoch': int(p.sha(p.canonical([kind, arm, scenario]))[:12], 16) + 1,
    'config_sequence': 1,
    'config': data,
    'config_sha256': p.sha(p.canonical(data)),
  }


def runtime(kind, arm, scenario):
  q.provenance(kind, arm)
  from openpilot.tools.cyber_autotune import smoothness_closed_loop as sg

  return TAArm(scenario) if arm == 'TA_B_V0' else sg.Arm(scenario, sg.ARMS[2] if arm == 'SG_A_V0' else sg.ARMS[0])


def run(kind, arm, scenario, context, *, observe=True):
  if type(observe) is not bool:
    raise ValueError('PAIR_EXACT_OBSERVER_BOOLEAN')
  cfg = config(kind, arm, scenario, context)
  rt = runtime(kind, arm, scenario)
  if rt.core.cp_sha256 != cfg['config']['profile_sha256']:
    raise ValueError('PAIR_RUNTIME_PROFILE_DRIFT')
  if arm != 'TA_B_V0':
    from openpilot.tools.cyber_autotune.smoothness_v0_screen import baseline_identity

    if baseline_identity(rt.core) != context['historical']['sg_binding']['baseline_core_identity']:
      raise ValueError('PAIR_RUNTIME_NATIVE_CONFIG_DRIFT')
  binding = {
    'experiment_sha256': p.sha(
      p.canonical(
        {'config': cfg, 'policy': context['receipt_sha256'], 'environment': {'python': platform.python_version(), 'clock': 'DETERMINISTIC_RELATIVE_NS'}}
      )
    ),
    'source_sha256': p.sha(p.canonical(context['sources'])),
    'expected_rows': len(rt.frames),
    'data_class': 'SYNTHETIC_ONLY',
    'tier': q.TIER,
    'dt_ns': c.DT_NS,
  }
  raw, rows = [], []
  for i in range(len(rt.frames)):
    source = rt.advance(i)
    raw.append(source)
    if observe:
      before = p.canonical(source)
      pre = source['requested'] if arm == 'TA_B_V0' else source['pre']
      row = h.make_row(binding, cfg, i, source['input'], pre, source['applied'], source, source['reset_events'])
      row['signals'].update(
        {'post_governor_torque': source['requested'], 'final_requested_torque': source['requested'], 'saturation_state': abs(source['requested']) == 1.0}
      )
      row['provenance'] = q.provenance(kind, arm)
      row['row_sha256'] = h.row_sha(row)
      rows.append(row)
      if p.canonical(source) != before:
        raise ValueError('PAIR_OBSERVER_MUTATED_EXPERIMENT')
  if not observe:
    return raw, None
  package = q.seal(
    {
      'schema': 'CYBER_H1_PAIRED_ARM_PACKAGE_V1',
      'policy': context,
      'policy_sha256': context['receipt_sha256'],
      'source_schema_sha256': c.schema()['receipt_sha256'],
      'binding': binding,
      'configs': [cfg],
      'rows': rows,
      'row_count': len(rows),
      'trace_sha256': p.sha(p.canonical(rows)),
      'row_digest_set_sha256': p.sha(p.canonical([r['row_sha256'] for r in rows])),
      'snapshot_set_sha256': p.sha(p.canonical([r['consumed_input_snapshot_sha256'] for r in rows])),
      'experiment_result_sha256': p.sha(p.canonical(raw)),
      'holdout_opening': 'CLOSED',
      'opening_count': 0,
      'production_observer_implemented': False,
    }
  )
  return raw, q.validate_package(package)


def execute(store):
  from openpilot.tools.cyber_autotune import cyber_h1_comparison_catalog as catalog
  from openpilot.tools.cyber_autotune import cyber_h1_paired_visual_adapter as adapter
  from openpilot.tools.cyber_autotune import trajectory_v0_publication as ta_public
  from openpilot.tools.cyber_autotune import smoothness_closed_loop_publication as sg_public
  from openpilot.tools.cyber_autotune import trajectory_v0_screen as ta
  from openpilot.tools.cyber_autotune import smoothness_closed_loop as sg

  root = h.store_path(store).parent
  context = q.policy()
  catalog.persist_exact(root / 'campaign-policy.json', context)  # Before ANY controller/plant execution.
  historical = {'TA_B': ta_public.load()['results'], 'SG_A': sg_public.load()['results']}
  entries = []
  for kind in q.CAMPAIGNS:
    for spec in context['scenario_rows']:
      name = spec['id']
      runtimes = [runtime(kind, arm, name) for arm in (q.BASELINE, q.CAMPAIGNS[kind][1])]
      if any(getattr(runtimes[0], key) is getattr(runtimes[1], key) for key in ('core', 'state', 'frames')):
        raise ValueError('PAIR_CROSS_ARM_STATE')
      if runtimes[0].core.controller.pid is runtimes[1].core.controller.pid:
        raise ValueError('PAIR_CROSS_ARM_PID')
      repeats = []
      observer_checks = []
      for repeat in (1, 2):
        packages = []
        for arm in (q.BASELINE, q.CAMPAIGNS[kind][1]):
          raw, package = run(kind, arm, name, context)
          # Exact existing historical full result bytes, not a new metric/verdict.
          original = ta.run_arm(name, 'CANONICAL_V0') if arm == 'TA_B_V0' else sg.run_arm(name, sg.ARMS[2] if arm == 'SG_A_V0' else sg.ARMS[0])
          if p.canonical(raw) != p.canonical(original):
            raise ValueError('PAIR_OBSERVER_NONINTERFERENCE_OR_FROZEN_EXECUTION')
          old = next(r for r in historical['TA_B' if arm == 'TA_B_V0' else 'SG_A']['scenarios'] if r['scenario'] == name)
          key = 'TA_V0_CANDIDATE' if arm == 'TA_B_V0' else sg.ARMS[2] if arm == 'SG_A_V0' else sg.ARMS[0]
          if package['experiment_result_sha256'] != old['arms'][key]['trace_sha256']:
            raise ValueError('PAIR_EXACT_HISTORICAL_RESULT_BYTES')
          catalog.persist_exact(root / f'repeat-{repeat}' / kind / name / arm / 'h1-package.json', package)
          observer_checks.append(package['experiment_result_sha256'])
          packages.append(package)
        manifest = q.pair(*packages)
        frameset = adapter.convert(*packages)
        catalog.persist_run(root / f'repeat-{repeat}', kind, name, packages, manifest, frameset)
        repeats.append((packages, manifest, frameset))
      if p.canonical(repeats[0]) != p.canonical(repeats[1]):
        raise ValueError('PAIR_EXACT_REPEATABILITY')
      entries.append(
        {
          'kind': kind,
          'scenario': name,
          'pair': repeats[0][1],
          'frameset': {k: v for k, v in repeats[0][2].items() if k != 'frames'},
          'observer_result_shas': observer_checks,
          'repeatability': 'EXACT_PASS',
        }
      )
  if q.policy() != context:
    raise ValueError('PAIR_EXECUTION_POLICY_DRIFT')
  for repeat in (1, 2):
    catalog.finish(root / f'repeat-{repeat}', entries)
  receipt = q.seal(
    {
      'schema': 'CYBER_H1_PAIRED_EXECUTION_V1',
      'policy_sha256': context['receipt_sha256'],
      'campaigns': 2,
      'scenarios_per_campaign': len(context['scenario_rows']),
      'arms_per_campaign': 2,
      'h1_packages': len(entries) * 4,
      'paired_framesets': len(entries) * 2,
      'rows_per_repeat': sum(e['pair']['sample_count'] * 2 for e in entries),
      'repeatability': 'EXACT_PASS',
      'observer_noninterference': 'EXACT_HISTORICAL_FULL_RESULT_BYTES',
      'runs': entries,
      'holdout_opening': 'CLOSED',
      'opening_count': 0,
    }
  )
  catalog.persist_exact(root / 'execution-receipt.json', receipt)
  return receipt


def main():
  import argparse
  import json

  parser = argparse.ArgumentParser(description='Explicit two separate frozen synthetic paired campaigns only.')
  parser.add_argument('--store', type=Path, required=True)
  args = parser.parse_args()
  result = execute(args.store)
  print(json.dumps({k: result[k] for k in ('receipt_sha256', 'h1_packages', 'paired_framesets', 'repeatability')}))


if __name__ == '__main__':
  main()
