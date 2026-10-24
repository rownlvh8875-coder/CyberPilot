"""Aggregate-only native replay evidence for STEP 7 lateral experiments."""
import argparse
from dataclasses import asdict, dataclass
import hashlib
import json
import math
from pathlib import Path
import struct
import subprocess

from openpilot.selfdrive.controls.lib.cyber_lateral.command_domain import (
  OfflineTorqueCommandContract, translate_raw_applied_command,
)
from openpilot.selfdrive.controls.lib.cyber_lateral.experiments import LateralExperimentVariant
from openpilot.selfdrive.controls.lib.cyber_lateral.optimizer import (
  CyberLateralOptimizer, OfflineOptimizerConfig, OptimizerStepInput,
)
from openpilot.selfdrive.controls.lib.cyber_lateral.steering_rate import SteeringRateLimits


RECORDED_COMMAND_CONTRACT = OfflineTorqueCommandContract(
  409, 3, 7, 0.01, 'recorded-carrot-5a970f1a-segment29',
)
CANDIDATE_COMMAND_CONTRACT = OfflineTorqueCommandContract(
  384, 3, 7, 0.01, 'cyber-native-card-384-contract',
)


@dataclass(frozen=True)
class DevelopmentReplayInput:
  route_segment: str
  rlog: Path
  rlog_sha256: str


def load_development_manifest(path: Path) -> tuple[DevelopmentReplayInput, ...]:
  manifest_path = path.resolve()
  document = json.loads(manifest_path.read_text(encoding='utf-8'))
  if document.get('schema_version') != 1 or document.get('role') != 'development':
    raise RuntimeError('manifest must declare schema version 1 development inputs')
  authority = document.get('authority', {})
  if authority.get('holdout_opened') is not False or authority.get('validation_opened') is not False:
    raise RuntimeError('development manifest must keep holdout and validation inputs unopened')
  entries = document.get('entries')
  if not isinstance(entries, list) or not entries:
    raise RuntimeError('development manifest must contain at least one entry')

  result = []
  for entry in entries:
    rlog = Path(entry['rlog'])
    if not rlog.is_absolute():
      rlog = manifest_path.parent / rlog
    if rlog.name != 'rlog.zst' or rlog.parent.name != entry['route_segment']:
      raise RuntimeError('development entry route identity must match the rlog parent')
    result.append(DevelopmentReplayInput(
      str(entry['route_segment']), rlog.resolve(), str(entry['rlog_sha256']),
    ))
  return tuple(result)


@dataclass(frozen=True)
class ExperimentIdentity:
  cyber_head: str
  route_segment: str
  rlog_sha256: str


def _sha256_file(path: Path) -> str:
  digest = hashlib.sha256()
  with path.open('rb') as stream:
    for block in iter(lambda: stream.read(1024 * 1024), b''):
      digest.update(block)
  return digest.hexdigest()


def _git(root: Path, *args: str) -> str:
  return subprocess.check_output(
    ('git', '-c', f'safe.directory={root}', '-C', str(root), *args), text=True,
  ).strip()


def validate_experiment_identity(cyber_root: Path, rlog: Path,
                                 expected_cyber_head: str,
                                 expected_rlog_sha256: str, *,
                                 approved_route_segment: str) -> ExperimentIdentity:
  root = cyber_root.resolve()
  log_path = rlog.resolve()
  if log_path.parent.name != approved_route_segment or log_path.name != 'rlog.zst':
    raise RuntimeError('rlog does not match the approved development route segment')
  actual_sha256 = _sha256_file(log_path)
  if actual_sha256 != expected_rlog_sha256:
    raise RuntimeError('rlog SHA-256 mismatch')
  actual_head = _git(root, 'rev-parse', 'HEAD')
  if actual_head != expected_cyber_head:
    raise RuntimeError('CyberPilot HEAD mismatch')
  if _git(root, 'status', '--porcelain=v1'):
    raise RuntimeError('CyberPilot source must be clean')
  return ExperimentIdentity(actual_head, approved_route_segment, actual_sha256)


@dataclass(frozen=True)
class NativeOutputSummary:
  rows: tuple[tuple[int, float, int, float], ...]
  ordered_sha256: str
  sendcan_count_discarded: int

  @property
  def car_output_count(self) -> int:
    return len(self.rows)


@dataclass(frozen=True)
class A3InputSummary:
  evaluated_car_control_count: int
  changed_car_control_count: int
  ordered_sha256: str


def build_a3_messages(messages) -> tuple[tuple, A3InputSummary]:
  limits = SteeringRateLimits(
    CANDIDATE_COMMAND_CONTRACT.max_magnitude_increase_per_s,
    CANDIDATE_COMMAND_CONTRACT.max_magnitude_decrease_per_s,
  )
  optimizer = CyberLateralOptimizer(OfflineOptimizerConfig(
    LateralExperimentVariant.A3,
    rate_limits=limits,
    baseline_max_magnitude_increase_per_s=CANDIDATE_COMMAND_CONTRACT.max_magnitude_increase_per_s,
    baseline_max_magnitude_decrease_per_s=CANDIDATE_COMMAND_CONTRACT.max_magnitude_decrease_per_s,
  ))
  latest_speed = None
  latest_raw_applied = None
  transformed = []
  evaluated = 0
  changed = 0
  digest = hashlib.sha256()

  for message in messages:
    kind = message.which()
    if kind == 'carState':
      latest_speed = float(message.carState.vEgo)
    elif kind == 'carOutput':
      latest_raw_applied = int(message.carOutput.actuatorsOutput.torqueOutputCan)

    if kind != 'carControl' or latest_speed is None or latest_raw_applied is None:
      transformed.append(message)
      continue

    requested = float(message.carControl.actuators.torque)
    applied = translate_raw_applied_command(
      latest_raw_applied, RECORDED_COMMAND_CONTRACT, CANDIDATE_COMMAND_CONTRACT,
    ).target_normalized
    result = optimizer.evaluate(OptimizerStepInput(
      speed_mps=latest_speed,
      baseline_command=requested,
      applied_command=applied,
      dt_s=CANDIDATE_COMMAND_CONTRACT.control_dt_s,
    ))
    if not result.valid or result.reason != 'ok':
      raise RuntimeError(f'A3 preprocessing failed closed: {result.reason}')
    builder = message.as_builder()
    builder.carControl.actuators.torque = result.candidate_command
    transformed.append(builder.as_reader())
    evaluated += 1
    changed += int(struct.pack('>d', requested) != struct.pack('>d', result.candidate_command))
    digest.update(struct.pack('>Qdd', int(message.logMonoTime), requested, result.candidate_command))

  return tuple(transformed), A3InputSummary(evaluated, changed, digest.hexdigest())


def summarize_native_outputs(outputs) -> NativeOutputSummary:
  rows = []
  digest = hashlib.sha256()
  sendcan_count = 0
  for message in outputs:
    kind = message.which()
    if kind == 'sendcan':
      sendcan_count += 1
      continue
    if kind != 'carOutput':
      continue

    actuators = message.carOutput.actuatorsOutput
    row = (
      int(message.logMonoTime),
      float(actuators.torque),
      int(actuators.torqueOutputCan),
      float(actuators.steeringAngleDeg),
    )
    if not all(math.isfinite(value) for value in (row[1], row[3])):
      raise RuntimeError('native replay produced nonfinite lateral output')
    digest.update(struct.pack('>Qdid', *row))
    rows.append(row)

  if not rows:
    raise RuntimeError('native replay produced no carOutput samples')
  return NativeOutputSummary(tuple(rows), digest.hexdigest(), sendcan_count)


def _percentile(values: list[float], fraction: float) -> float:
  ordered = sorted(values)
  position = (len(ordered) - 1) * fraction
  lower = math.floor(position)
  upper = math.ceil(position)
  if lower == upper:
    return float(ordered[lower])
  weight = position - lower
  return float(ordered[lower] * (1. - weight) + ordered[upper] * weight)


def _metrics(values: list[float]) -> dict[str, float]:
  absolute = [abs(value) for value in values]
  return {
    'mean_abs': sum(absolute) / len(absolute),
    'rms': math.sqrt(sum(value * value for value in values) / len(values)),
    'p95_abs': _percentile(absolute, 0.95),
    'max_abs': max(absolute),
  }


def compare_native_outputs(baseline: NativeOutputSummary,
                           candidate: NativeOutputSummary) -> dict:
  if baseline.car_output_count != candidate.car_output_count:
    raise RuntimeError('A0/A3 native carOutput count mismatch')
  if baseline.car_output_count < 2:
    raise RuntimeError('native comparison requires at least two carOutput samples')
  if [row[0] for row in baseline.rows] != [row[0] for row in candidate.rows]:
    raise RuntimeError('A0/A3 native carOutput timestamp mismatch')

  raw_delta = [
    float(candidate_row[2] - baseline_row[2])
    for baseline_row, candidate_row in zip(baseline.rows, candidate.rows, strict=True)
  ]
  baseline_derivative = [
    (current[1] - previous[1]) / CANDIDATE_COMMAND_CONTRACT.control_dt_s
    for previous, current in zip(baseline.rows[:-1], baseline.rows[1:], strict=True)
  ]
  candidate_derivative = [
    (current[1] - previous[1]) / CANDIDATE_COMMAND_CONTRACT.control_dt_s
    for previous, current in zip(candidate.rows[:-1], candidate.rows[1:], strict=True)
  ]
  changed_count = sum(delta != 0 for delta in raw_delta)
  return {
    'changed_raw_output_count': changed_count,
    'changed_raw_output_ratio': changed_count / len(raw_delta),
    'raw_candidate_minus_baseline': _metrics(raw_delta),
    'baseline_normalized_torque_derivative_per_s': _metrics(baseline_derivative),
    'candidate_normalized_torque_derivative_per_s': _metrics(candidate_derivative),
    'baseline_saturation_ratio': sum(
      abs(row[2]) >= CANDIDATE_COMMAND_CONTRACT.steer_max for row in baseline.rows
    ) / baseline.car_output_count,
    'candidate_saturation_ratio': sum(
      abs(row[2]) >= CANDIDATE_COMMAND_CONTRACT.steer_max for row in candidate.rows
    ) / candidate.car_output_count,
  }


def _authority_record() -> dict[str, bool]:
  return {
    'holdout_opened': False,
    'live_can': False,
    'sendcan_forwarded': False,
    'vehicle_write': False,
    'safety_limit_change': False,
    'deployment': False,
  }


def _decision_record() -> dict:
  return {
    'repeatability_pass': True,
    'performance_pass': False,
    'promote_to_active_control': False,
    'reason': 'native replay repeatability does not prove calibrated plant, lane-center, curve-response, or override benefit',
  }


def run_native_experiment(messages, variant: str, identity: ExperimentIdentity,
                          replay) -> dict:
  if variant not in ('A0', 'A3'):
    raise ValueError('native STEP 7 runner permits only A0 or A3')
  if not isinstance(identity, ExperimentIdentity):
    raise ValueError('identity must be an ExperimentIdentity')

  if variant == 'A0':
    first = summarize_native_outputs(replay(messages))
    second = summarize_native_outputs(replay(messages))
    repeatable = (
      first.ordered_sha256 == second.ordered_sha256 and
      first.rows == second.rows and
      first.sendcan_count_discarded == second.sendcan_count_discarded
    )
    decision = _decision_record()
    decision['repeatability_pass'] = repeatable
    return {
      'schema_version': 1,
      'state': 'STEP7_NATIVE_A0_REPEATABLE' if repeatable else 'STEP7_NATIVE_A0_NONREPEATABLE',
      'scope': 'isolated native card A0 controller-output repeatability; no plant or active authority',
      'variant': variant,
      'identity': asdict(identity),
      'native_replay': {
        'car_output_count': first.car_output_count,
        'run_1_sha256': first.ordered_sha256,
        'run_2_sha256': second.ordered_sha256,
        'runs_identical': repeatable,
        'run_1_sendcan_count_discarded': first.sendcan_count_discarded,
        'run_2_sendcan_count_discarded': second.sendcan_count_discarded,
      },
      'decision': decision,
      'authority': _authority_record(),
    }

  a3_messages, preprocessing = build_a3_messages(messages)
  baseline = summarize_native_outputs(replay(messages))
  first = summarize_native_outputs(replay(a3_messages))
  second = summarize_native_outputs(replay(a3_messages))
  repeatable = (
    first.ordered_sha256 == second.ordered_sha256 and
    first.rows == second.rows and
    first.sendcan_count_discarded == second.sendcan_count_discarded
  )
  decision = _decision_record()
  decision['repeatability_pass'] = repeatable
  return {
    'schema_version': 1,
    'state': ('STEP7_NATIVE_A3_REPEATABLE_NOT_PERFORMANCE_QUALIFIED'
              if repeatable else 'STEP7_NATIVE_A3_NONREPEATABLE'),
    'scope': 'isolated native card A0/A3 controller-output comparison; no plant or active authority',
    'variant': variant,
    'identity': asdict(identity),
    'preprocessing': asdict(preprocessing),
    'native_replay': {
      'car_output_count': baseline.car_output_count,
      'a0_sha256': baseline.ordered_sha256,
      'a3_run_1_sha256': first.ordered_sha256,
      'a3_run_2_sha256': second.ordered_sha256,
      'a3_runs_identical': repeatable,
      'a0_sendcan_count_discarded': baseline.sendcan_count_discarded,
      'a3_run_1_sendcan_count_discarded': first.sendcan_count_discarded,
      'a3_run_2_sendcan_count_discarded': second.sendcan_count_discarded,
    },
    'comparison': compare_native_outputs(baseline, first),
    'decision': decision,
    'authority': _authority_record(),
  }


def main(argv: list[str] | None = None, *, load_messages=None, replay=None) -> int:
  parser = argparse.ArgumentParser(description='Run aggregate-only Cyber lateral A0/A3 native replay')
  parser.add_argument('--cyber-root', type=Path, required=True)
  source = parser.add_mutually_exclusive_group(required=True)
  source.add_argument('--rlog', type=Path)
  source.add_argument('--development-manifest', type=Path)
  parser.add_argument('--route-segment')
  parser.add_argument('--expected-cyber-head', required=True)
  parser.add_argument('--expected-rlog-sha256')
  parser.add_argument('--variant', choices=('A0', 'A3'), required=True)
  parser.add_argument('--output', type=Path)
  args = parser.parse_args(argv)

  approved_route_segment = args.route_segment
  if args.development_manifest is not None:
    if args.route_segment is None:
      parser.error('--route-segment is required with --development-manifest')
    matches = [
      entry for entry in load_development_manifest(args.development_manifest)
      if entry.route_segment == args.route_segment
    ]
    if len(matches) != 1:
      raise RuntimeError('development manifest must contain exactly one selected route segment')
    selected = matches[0]
    rlog = selected.rlog
    expected_rlog_sha256 = selected.rlog_sha256
    approved_route_segment = selected.route_segment
  else:
    if args.route_segment is None:
      parser.error('--route-segment is required with --rlog')
    if args.expected_rlog_sha256 is None:
      parser.error('--expected-rlog-sha256 is required with --rlog')
    rlog = args.rlog
    expected_rlog_sha256 = args.expected_rlog_sha256

  identity = validate_experiment_identity(
    args.cyber_root, rlog, args.expected_cyber_head, expected_rlog_sha256,
    approved_route_segment=approved_route_segment,
  )
  if load_messages is None:
    from openpilot.tools.lib.logreader import LogReader

    def load_messages(path):
      return tuple(LogReader(str(path)))
  if replay is None:
    from openpilot.selfdrive.test.process_replay.cyber_lateral_replay import get_cyber_lateral_card_process_config
    from openpilot.selfdrive.test.process_replay.process_replay import replay_process

    def replay(messages):
      return replay_process(
        get_cyber_lateral_card_process_config(), messages, disable_progress=True,
      )

  report = run_native_experiment(tuple(load_messages(rlog.resolve())), args.variant, identity, replay)
  payload = json.dumps(report, indent=2, sort_keys=True)
  if args.output is not None:
    output_path = args.output.resolve()
    if output_path.is_relative_to(args.cyber_root.resolve()):
      raise RuntimeError('aggregate output must remain outside the clean CyberPilot source')
    with output_path.open('x', encoding='utf-8') as stream:
      stream.write(payload + '\n')
  print(payload)
  return 0 if report['decision']['repeatability_pass'] else 1


if __name__ == '__main__':
  raise SystemExit(main())
