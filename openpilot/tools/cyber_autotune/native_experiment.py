"""Three-arm real native execution diagnostics, not physical qualification.

No candidate generation, raw-log loader, simulator, live transport or profile write.
Caller labels/CP/source declarations remain claims, not reviewed evidence authority.
"""
from dataclasses import dataclass
import math

from openpilot.tools.cyber_autotune.comparison import ARMS, SCENARIO_TAGS
from openpilot.tools.cyber_autotune.native_protocol import TIMESTEP_NS, canonical, decode_request, digest, encode_request, finite
from openpilot.tools.cyber_autotune.native_runner import MAX_TIMEOUT_S, run_native, validate_response


@dataclass(frozen=True)
class NativeArm:
  arm: str
  request: bytes


@dataclass(frozen=True)
class NativeExperiment:
  arms: tuple[NativeArm, ...]
  scenario_tags: tuple[str, ...]


def _prepare(experiment):
  if type(experiment) is not NativeExperiment or type(experiment.arms) is not tuple or len(experiment.arms) != len(ARMS):
    raise ValueError('INVALID_NATIVE_EXPERIMENT')
  tags = experiment.scenario_tags
  if (type(tags) is not tuple or not tags or any(type(tag) is not str or tag not in SCENARIO_TAGS for tag in tags) or
      len(set(tags)) != len(tags)):
    raise ValueError('INVALID_SCENARIO_TAGS')
  prepared = {}
  frame_binding = None
  for arm in experiment.arms:
    if type(arm) is not NativeArm or type(arm.arm) is not str or arm.arm not in ARMS or arm.arm in prepared:
      raise ValueError('INVALID_ARM_MATRIX')
    request = decode_request(arm.request)
    binding = digest(canonical({'frames': request['frames'], 'fingerprint': request['fingerprint']}))
    if frame_binding is not None and binding != frame_binding:
      raise ValueError('MISMATCHED_NATIVE_INPUTS')
    frame_binding = binding
    prepared[arm.arm] = encode_request(request)
  return prepared, frame_binding


def _one_run(payload, arm, repetition, timeout_s):
  request = decode_request(payload)
  status = 'INVALID_RESPONSE'
  samples = None
  trace_digest = None
  try:
    result = run_native(request, timeout_s=timeout_s)
    if type(result) is dict and type(result.get('status')) is str:
      if result['status'] == 'COMPLETED':
        validate_response(request, result)
        status = 'COMPLETED'
        trace_digest = result['ordered_trace_sha256']
        samples = tuple((row['time_ns'], row['requested_torque'], row['estimated_curvature_1pm']) for row in result['samples'])
      elif result['status'] in {'TIMEOUT', 'WORKER_FAILED', 'WORKER_UNAVAILABLE', 'UNSUPPORTED_PLATFORM', 'INVALID_RESPONSE'}:
        status = result['status']
  except ValueError:
    status = 'INVALID_RESPONSE'
  except Exception:
    status = 'EXECUTION_EXCEPTION'
  record = {'arm': arm, 'repetition': repetition, 'status': status, 'request_sha256': digest(payload),
            'source_head': request['source']['head'], 'opendbc_head': request['source']['opendbc_head'],
            'car_params_sha256': request['car_params_sha256'], 'ordered_trace_sha256': trace_digest,
            'sample_count': None if samples is None else len(samples)}
  return record, samples


def _rms(values):
  return math.sqrt(math.fsum(value * value for value in values) / len(values))


def _markdown(result):
  lines = ['# Native requested-torque diagnostics', '', f"Status: {result['status']}",
           'Scope: OFFLINE_NATIVE_DIAGNOSTICS_ONLY; no physical qualification or actuator authority.', '',
           '| Arm | Repetition | Execution | Samples |', '| --- | --- | --- | --- |']
  for run in result['runs']:
    count = 'missing' if run['sample_count'] is None else str(run['sample_count'])
    lines.append(f"| {run['arm']} | {run['repetition']} | {run['status']} | {count} |")
  lines.extend(('', 'Command difference diagnostics (normalized requested torque):'))
  for row in result['comparisons']:
    lines.append(f"- {row['arm']} vs {row['reference']}: RMSE={row['requested_torque_rmse_difference']:.8g}, " +
                 f"max={row['requested_torque_max_difference']:.8g}")
  lines.extend(('', 'Command rates are not physical steering jerk; requested bounds are not applied actuator saturation.',
                'Missing gates: ' + ', '.join(result['issues']), 'Runtime accepted: false. Promotable: false.'))
  return '\n'.join(lines) + '\n'


def run_experiment(experiment: NativeExperiment, *, timeout_s: float) -> dict:
  """Blocking offline six-run matrix; KeyboardInterrupt propagates after cleanup."""
  if not finite(timeout_s) or not 0 < timeout_s <= MAX_TIMEOUT_S:
    raise ValueError('INVALID_TIMEOUT')
  prepared, frame_binding = _prepare(experiment)
  runs = []
  traces = {}
  issues = []
  repeatability_failed = False
  for arm in ARMS:
    pair = []
    for repetition in range(2):
      record, samples = _one_run(prepared[arm], arm, repetition, timeout_s)
      runs.append(record)
      pair.append((record, samples))
    if any(record['status'] != 'COMPLETED' for record, _ in pair):
      issues.append(arm + '_EXECUTION_INCOMPLETE')
    elif pair[0][0]['ordered_trace_sha256'] != pair[1][0]['ordered_trace_sha256'] or pair[0][1] != pair[1][1]:
      issues.append(arm + '_REPEATABILITY_FAILED')
      repeatability_failed = True
    else:
      traces[arm] = pair[0][1]
  repeatable = len(traces) == len(ARMS)
  comparisons = []
  diagnostics = []
  if repeatable:
    for arm in ARMS:
      commands = tuple(row[1] for row in traces[arm])
      rates = tuple((current - previous) / (TIMESTEP_NS * 1e-9) for previous, current in zip(commands, commands[1:], strict=False))
      diagnostics.append({'arm': arm, 'command_rate_rms_ratio_per_s': _rms(rates),
                          'requested_bound_occupancy': sum(abs(value) == 1. for value in commands) / len(commands)})
    for reference, arm in ((ARMS[0], ARMS[1]), (ARMS[0], ARMS[2]), (ARMS[1], ARMS[2])):
      differences = tuple(a[1] - b[1] for a, b in zip(traces[arm], traces[reference], strict=True))
      comparisons.append({'reference': reference, 'arm': arm, 'requested_torque_rmse_difference': _rms(differences),
                          'requested_torque_max_difference': max(abs(value) for value in differences)})
  issues.extend(('METRIC_V2_PRODUCER_PENDING', 'EVIDENCE_AUTHORITY_PENDING', 'CLOSED_LOOP_PENDING',
                 'LONGITUDINAL_PENDING', 'TUNING_QUALIFICATION_PENDING'))
  result = {'status': 'FAIL' if repeatability_failed else 'REVALIDATION_REQUIRED',
            'scope': 'OFFLINE_NATIVE_DIAGNOSTICS_ONLY', 'inputs_sha256': frame_binding,
            'scenario_tags': list(experiment.scenario_tags), 'runs': runs, 'repeatable': repeatable,
            'comparisons': comparisons, 'diagnostics': diagnostics, 'issues': issues,
            'runtime_accepted': False, 'promotable': False}
  result['markdown'] = _markdown(result)
  return result
