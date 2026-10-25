"""Recorded timestamp candidates, never actual Controller-consumption reconstruction.

F46 remains immutable. Only header metadata, recorded commands and the verified
controlsState model-reference field are projected from the one authorized log.
"""
import argparse
import ast
from bisect import bisect_left, bisect_right
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from fractions import Fraction
from functools import cache
import hashlib
import importlib
import json
import re
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
F46_PINS = {
  'tools/cyberpilot/rlog_observer_regression_v1.py': '8a12a5e6052296c8a588c3840ea4eaa9da8781d265efb59089bd33bace196ef2',
  'tools/cyberpilot/tests/test_rlog_observer_regression_v1.py': 'a43f3b3c3a6461e52d159650b52a13124e710d0a9f40a467a43c5da9643c9330',
  'docs/cyberpilot/changes/rlog-observer-regression-v1.md': '5e0a7fc5e7deda7a77df88d1bbe8af608fd55b98979c5d597ced9a38b11a64d0',
}
F46_TAPE_SHA = '7b5ca64db3f897f7a98f6d8aaf9e11bcbdb81b54bc18c382d89087e16a6e928f'
F46_TAPE_BYTES = 9000564
DIRECT = ('carState', 'controlsState', 'selfdriveState', 'modelV2')
UNMAPPED = {'lateralManeuverPlan': 'lateralPlan', 'vehicleParameters': 'liveParameters', 'lateralDelay': 'liveDelay'}
REQUESTED = (*DIRECT, *UNMAPPED)
STATUSES = ('RECORDED_INPUT_CANDIDATE', 'TEMPORAL_BINDING_AMBIGUOUS', 'INPUT_MISSING',
            'SOURCE_SCHEMA_UNQUALIFIED', 'INTERNAL_STATE_UNAVAILABLE')
PRECEDENCE = ('SOURCE_SCHEMA_UNQUALIFIED', 'INPUT_MISSING', 'TEMPORAL_BINDING_AMBIGUOUS', 'RECORDED_INPUT_CANDIDATE')


def need(value, code):
  if not value:
    raise ValueError(code)


def sha(data):
  return hashlib.sha256(data).hexdigest()


@cache
def base():
  for name, expected in F46_PINS.items():
    path = ROOT / name
    need(path.is_file() and not path.is_symlink() and sha(path.read_bytes()) == expected, 'F46_SOURCE_DRIFT')
  if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
  return importlib.import_module('tools.cyberpilot.rlog_observer_regression_v1')


def canonical(value):
  return base().canonical(value)


@dataclass(frozen=True, slots=True)
class Stamp:
  ordinal: int
  service: str
  timestamp_ns: int
  valid: bool = True
  binding: str = ''
  model_reference_ns: int | None = None


def validate_order(events):
  previous = -1
  for event in events:
    need(type(event.ordinal) is int and event.ordinal > previous, 'WIRE_ORDER_MISMATCH')
    need(type(event.timestamp_ns) is int and type(event.valid) is bool, 'INVALID_HEADER')
    previous = event.ordinal


def order_report(events):
  validate_order(events)
  backwards, pairs, cross, adjacent_duplicates = [], {}, 0, 0
  for previous, current in zip(events, events[1:], strict=False):
    adjacent_duplicates += current.timestamp_ns == previous.timestamp_ns
    if current.timestamp_ns >= previous.timestamp_ns:
      continue
    backwards.append((previous.ordinal, current.ordinal, previous.service, current.service,
                      previous.timestamp_ns, current.timestamp_ns))
    cross += previous.service != current.service
    key = previous.service + '->' + current.service
    if key not in pairs:
      pairs[key] = {'count': 0, 'ordinal_range': [current.ordinal, current.ordinal], 'maximum_backward_ns': 0}
    pairs[key]['count'] += 1
    pairs[key]['ordinal_range'][1] = current.ordinal
    pairs[key]['maximum_backward_ns'] = max(pairs[key]['maximum_backward_ns'], previous.timestamp_ns - current.timestamp_ns)
  return {'record_count': len(events), 'reversals': len(backwards), 'cross_service_reversals': cross,
          'adjacent_equal_timestamps': adjacent_duplicates, 'pairs': pairs,
          'reversal_signature_sha256': sha(canonical(backwards)),
          'original_order_preserved': True, 'deadline_qualification': False}


def percentile(values, numerator):
  if not values:
    return None
  ordered = sorted(values)  # Distribution only; never reorders source records.
  position = Fraction((len(ordered) - 1) * numerator, 100)
  lower = position.numerator // position.denominator
  result = Fraction(ordered[lower]) + (position - lower) * (ordered[min(lower + 1, len(ordered)-1)] - ordered[lower])
  return {'numerator': result.numerator, 'denominator': result.denominator}


def service_stats(events, frequency_hz=None):
  delta = [b.timestamp_ns - a.timestamp_ns for a, b in zip(events, events[1:], strict=False)]
  frequency = Fraction(str(frequency_hz)) if frequency_hz else None
  return {'count': len(events), 'invalid_events': sum(not x.valid for x in events),
          'nonpositive_timestamps': sum(x.timestamp_ns <= 0 for x in events),
          'timestamp_reversals': sum(x < 0 for x in delta), 'duplicate_timestamps': sum(x == 0 for x in delta),
          'duration_ns': events[-1].timestamp_ns - events[0].timestamp_ns if events else None,
          'min_delta_ns': min(delta, default=None), 'max_delta_ns': max(delta, default=None),
          'p50_delta_ns': percentile(delta, 50), 'p95_delta_ns': percentile(delta, 95), 'p99_delta_ns': percentile(delta, 99),
          'declared_frequency_hz': float(frequency) if frequency else None,
          'over_nominal_period_count': sum(x > 0 and x * frequency > 10**9 for x in delta) if frequency else None,
          'nominal_exceedance_is_not_deadline_or_loss': True, 'deadline_qualification': False}


@dataclass(frozen=True)
class Series:
  service: str
  events: tuple[Stamp, ...]
  ordinals: tuple[int, ...]
  times: tuple[int, ...]
  prefix_bad: tuple[int, ...]
  binding: str | None


def make_index(service, events):
  events = tuple(events)
  validate_order(events)
  need(all(x.service == service for x in events), 'INCORRECT_SERVICE_BINDING')
  binding = events[0].binding if events else None
  need(all(x.binding == binding and re.fullmatch('[a-f0-9]{64}', x.binding) for x in events), 'INCORRECT_SOURCE_BINDING')
  bad = [0]
  for i, event in enumerate(events):
    error = event.timestamp_ns <= 0 or (i > 0 and event.timestamp_ns < events[i-1].timestamp_ns)
    bad.append(bad[-1] + int(error))
  return Series(service, events, tuple(x.ordinal for x in events), tuple(x.timestamp_ns for x in events), tuple(bad), binding)


def _prior(command, index, max_age_ns=None):
  end = bisect_left(index.ordinals, command.ordinal)
  result = {'status': 'INPUT_MISSING', 'candidate_ordinals': [], 'representative_ordinal': None,
            'recorded_age_ns': None, 'eligible_record_count': 0, 'reasons': [],
            'freshness': 'UNQUALIFIED', 'actual_consumption_proven': False}
  if end == 0:
    result['reasons'].append('NO_EARLIER_FILE_EVENT')
    return result
  if index.prefix_bad[end]:
    result['status'] = 'TEMPORAL_BINDING_AMBIGUOUS'
    result['reasons'].append('PER_SERVICE_ORDER_ERROR')
    return result
  position = bisect_right(index.times, command.timestamp_ns, 0, end)
  result['eligible_record_count'] = position
  if position == 0:
    result['reasons'].append('ONLY_FUTURE_MESSAGE_TIMESTAMPS')
    return result
  stamp = index.events[position-1]
  first = bisect_left(index.times, stamp.timestamp_ns, 0, position)
  options = index.events[first:position]
  # A duplicate maximum timestamp remains an ambiguous set, not a forced match.
  result['candidate_ordinals'] = [x.ordinal for x in options]
  result['recorded_age_ns'] = command.timestamp_ns - stamp.timestamp_ns
  if any(not x.valid for x in options):
    result['candidate_ordinals'] = []
    result['reasons'].append('INVALID_LATEST_EVENT')
  if len(options) > 1:
    result['reasons'].append('DUPLICATE_LATEST_TIMESTAMP')
  if stamp.timestamp_ns == command.timestamp_ns:
    result['reasons'].append('EQUAL_MESSAGE_TIMESTAMP')
  if position < end:
    result['reasons'].append('FUTURE_FILE_PREDECESSOR_BYPASSED')
  if base().assess_age(stamp.timestamp_ns, command.timestamp_ns, max_age_ns=max_age_ns) == 'STALE_INPUT':
    result['reasons'].append('DECLARED_MESSAGE_AGE_EXCEEDED')
  if len(result['candidate_ordinals']) == 1:
    result['representative_ordinal'] = stamp.ordinal
  result['status'] = 'TEMPORAL_BINDING_AMBIGUOUS' if result['reasons'] else 'RECORDED_INPUT_CANDIDATE'
  return result


def candidate(command, index, expected_service, *, max_age_ns=None):
  need(command.service == 'carControl' and expected_service in REQUESTED, 'WRONG_SERVICE_ROLE')
  need(index.service == expected_service, 'INCORRECT_SERVICE_BINDING')
  need(re.fullmatch('[a-f0-9]{64}', command.binding) and index.binding in (None, command.binding), 'INCORRECT_SOURCE_BINDING')
  if expected_service in UNMAPPED:
    return {'status': 'SOURCE_SCHEMA_UNQUALIFIED', 'candidate_ordinals': [], 'representative_ordinal': None,
            'recorded_age_ns': None, 'eligible_record_count': 0,
            'reasons': ['HISTORICAL_SERVICE_MAPPING_UNQUALIFIED'], 'freshness': 'UNQUALIFIED',
            'actual_consumption_proven': False}
  result = _prior(command, index, max_age_ns)
  result['role'] = 'CONTROLLER_DIAGNOSTIC_COMPANION' if expected_service == 'controlsState' else 'RECORDED_INPUT_MESSAGE_CANDIDATE'
  return result


def output_observation(command, index):
  need(command.service == 'carControl' and index.service == 'carOutput', 'WRONG_SERVICE_ROLE')
  need(re.fullmatch('[a-f0-9]{64}', command.binding) and index.binding in (None, command.binding), 'INCORRECT_SOURCE_BINDING')
  prior = _prior(command, index)
  start = bisect_right(index.ordinals, command.ordinal)
  post = None
  for position in range(start, len(index.events)):
    event = index.events[position]
    if event.timestamp_ns >= command.timestamp_ns:
      post = event.ordinal
      break
  return {'role': 'PROCESSED_COMMAND_OBSERVATION_ONLY', 'prior_ordinal': prior['representative_ordinal'],
          'post_ordinal': post, 'physical_response_qualified': False, 'proven_command_result_binding': False}


def primary(statuses):
  return next(x for x in PRECEDENCE if x in statuses)


@dataclass
class Coverage:
  statuses: Counter[str]
  candidate_commands: int
  ages: list[int]
  references: Counter[int]


def characterize(stamps, binding, nominal=None):
  stamps = tuple(stamps)
  validate_order(stamps)
  need(all(x.binding == binding for x in stamps), 'INCORRECT_SOURCE_BINDING')
  grouped = defaultdict(list)
  by_ordinal = {}
  for stamp in stamps:
    grouped[stamp.service].append(stamp)
    by_ordinal[stamp.ordinal] = stamp
  indexes = {name: make_index(name, grouped.get(name, ())) for name in (*REQUESTED, 'carOutput')}
  model_by_time = defaultdict(list)
  for event in grouped.get('modelV2', ()):
    model_by_time[event.timestamp_ns].append(event)
  counts, direct_counts = Counter(dict.fromkeys(STATUSES, 0)), Counter(dict.fromkeys(STATUSES, 0))
  secondary, output_counts = Counter(), Counter()
  witness = Counter(dict.fromkeys(('no_controlsState_candidate', 'reference_unavailable', 'reference_not_in_record',
                                   'exact_reference_in_record', 'eligible_before_command', 'reference_found_after_command',
                                   'latest_candidate_matches_logged_reference', 'latest_candidate_differs_from_logged_reference'), 0))
  coverage = {s: Coverage(Counter(dict.fromkeys(STATUSES, 0)), 0, [], Counter()) for s in REQUESTED}
  rows = []
  for command in grouped.get('carControl', ()):
    inputs = {name: candidate(command, indexes[name], name) for name in REQUESTED}
    status = primary([x['status'] for x in inputs.values()])
    direct_status = primary([inputs[s]['status'] for s in DIRECT])
    counts[status] += 1
    direct_counts[direct_status] += 1
    reasons = {'INTERNAL_STATE_UNAVAILABLE', 'ACTUAL_PRODUCER_CONSUMER_BINDING_UNPROVEN', 'CLOCK_ACQUISITION_UNQUALIFIED'}
    for name, value in inputs.items():
      lane = coverage[name]
      lane.statuses[value['status']] += 1
      if value['candidate_ordinals']:
        lane.candidate_commands += 1
        lane.ages.append(value['recorded_age_ns'])
        lane.references.update(value['candidate_ordinals'])
      reasons.update(name + ':' + reason for reason in value['reasons'])
    secondary.update(reasons)
    output = output_observation(command, indexes['carOutput'])
    output_counts['prior_observation_exists'] += output['prior_ordinal'] is not None
    output_counts['post_observation_exists'] += output['post_ordinal'] is not None
    control_ordinal = inputs['controlsState']['representative_ordinal']
    if control_ordinal is None:
      witness['no_controlsState_candidate'] += 1
    else:
      ref = by_ordinal[control_ordinal].model_reference_ns
      if not ref:
        witness['reference_unavailable'] += 1
      else:
        matching = model_by_time.get(ref, [])
        if not matching:
          witness['reference_not_in_record'] += 1
        else:
          witness['exact_reference_in_record'] += 1
          eligible = [x for x in matching if x.ordinal < command.ordinal and x.timestamp_ns <= command.timestamp_ns]
          if eligible:
            witness['eligible_before_command'] += 1
          else:
            witness['reference_found_after_command'] += 1
          model_ordinal = inputs['modelV2']['representative_ordinal']
          if model_ordinal is not None:
            witness['latest_candidate_matches_logged_reference' if by_ordinal[model_ordinal].timestamp_ns == ref
                    else 'latest_candidate_differs_from_logged_reference'] += 1
    rows.append({'command_ordinal': command.ordinal, 'command_timestamp_ns': command.timestamp_ns,
                 'primary_status': status, 'direct_four_status': direct_status, 'secondary_reasons': sorted(reasons),
                 'inputs': inputs, 'carOutput': output})
  number = len(rows)
  need(sum(counts.values()) == number == sum(direct_counts.values()), 'COVERAGE_ACCOUNTING_ERROR')
  summary = {
    'command_count': number, 'primary_counts': dict(counts),
    'primary_percentages': {k: 100*v/number if number else None for k, v in counts.items()},
    'primary_scope': list(REQUESTED), 'direct_primary_counts': dict(direct_counts),
    'direct_primary_scope': list(DIRECT), 'secondary_counts': dict(secondary),
    'all_file_order': order_report(stamps),
    'selected_six_order': order_report(tuple(x for x in stamps if x.service in base().FIELDS)),
    'per_service': {k: service_stats(v, (nominal or {}).get(k)) for k, v in grouped.items()},
    'input_coverage': {s: {'statuses': dict(v.statuses), 'candidate_commands': v.candidate_commands,
                          'candidate_percentage': 100*v.candidate_commands/number if number else None,
                          'unique_candidate_records': len(v.references), 'maximum_reuse': max(v.references.values(), default=0),
                          'min_recorded_age_ns': min(v.ages, default=None), 'max_recorded_age_ns': max(v.ages, default=None)}
                       for s, v in coverage.items()},
    'historical_services': {requested: {'status': 'HISTORICAL_SERVICE_MAPPING_UNQUALIFIED',
                                      'recorded_service': old, 'recorded_count': len(grouped.get(old, ())),
                                      'alias_used': False} for requested, old in UNMAPPED.items()},
    'carOutput_observations': dict(output_counts), 'model_reference_witness': dict(witness),
    'actual_controller_consumption_proven': False, 'native_exact_replay_proven': False,
    'internal_state': 'INTERNAL_STATE_UNAVAILABLE', 'physical_response': 'UNQUALIFIED',
    'timestamp_relation_scope': 'RECORDED_INTEGER_TIMESTAMP_RELATION_ONLY',
    'runtime_authorized': False, 'vehicle_authority': 'NONE', 'selected_candidate': None, 'selected_policy': None,
  }
  return summary, rows


def nominal_frequencies(source_root):
  tree = ast.parse((Path(source_root) / 'openpilot/cereal/services.py').read_text())
  def scalar(node):
    if isinstance(node, ast.Constant) and type(node.value) in (int, float):
      return Fraction(str(node.value))
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
      return scalar(node.left) / scalar(node.right)
    raise ValueError('INVALID_SERVICE_FREQUENCY')
  for node in tree.body:
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == '_services':
      need(isinstance(node.value, ast.Dict), 'INVALID_SERVICE_REGISTRY')
      return {key.value: float(scalar(value.elts[1])) for key, value in zip(node.value.keys, node.value.values, strict=True)}
  raise ValueError('SERVICE_REGISTRY_MISSING')


def decode(args, output):
  f46 = base()
  f46.verify_source(args.source_root, args.source_manifest)
  raw = f46.read_verified(args.raw, f46.RAW_SHA, f46.RAW_BYTES)
  need('qlog' not in Path(args.raw).name.lower(), 'RLOG_REQUIRED')
  preserved = f46.load_tape(f46.read_verified(args.f46_tape, F46_TAPE_SHA, F46_TAPE_BYTES))
  data = f46.decompress(raw)
  import capnp
  capnp.remove_import_hook()
  schema = capnp.load(str(Path(args.source_root) / 'openpilot/cereal/log.capnp'),
                      imports=[str(Path(args.source_root) / 'opendbc_repo/opendbc/car')])
  binding = sha(canonical({'raw_sha256': f46.RAW_SHA, 'schema_manifest': f46.MANIFEST_SHA, 'source': f46.SOURCE_COMMIT}))
  stamps, commands, counts = [], [], Counter()
  source_messages = 0
  for ordinal, (start, end) in enumerate(f46.message_slices(data)):
    with schema.Event.from_bytes(data[start:end]) as event:
      name = event.which()
      counts[name] += 1
      if name == 'initData':
        f46.validate_metadata(str(event.initData.gitSrcCommit) or str(event.initData.gitCommit), f46.RAW_SHA)
        need(not event.initData.dirty, 'DIRTY_RECORDED_SOURCE')
        source_messages += 1
      reference = int(event.controlsState.lateralPlanMonoTime) if name == 'controlsState' else None
      stamps.append(Stamp(ordinal, name, int(event.logMonoTime), bool(event.valid), binding, reference))
      if name == 'carControl':
        values = []
        for field in f46.FIELDS['carControl']:
          value = event.carControl
          for part in field.split('.'):
            value = getattr(value, part)
          values.append((field, value))
        commands.append(f46.Record(ordinal, name, int(event.logMonoTime), bool(event.valid), tuple(values), binding))
  need(source_messages == 1 and len(stamps) == 86400 and len(counts) == 57 and len(commands) == 6000, 'RECORD_COVERAGE_MISMATCH')
  command_bytes = f46.tape_bytes(commands)
  need(command_bytes == f46.tape_bytes(tuple(x for x in preserved if x.service == 'carControl')), 'COMMAND_FIDELITY_MISMATCH')
  old_selected = tuple(Stamp(x.ordinal, x.service, x.timestamp_ns, x.valid, x.binding) for x in preserved)
  selected = tuple(x for x in stamps if x.service in f46.FIELDS)
  old_order, new_order = order_report(old_selected), order_report(selected)
  need(new_order['reversals'] == old_order['reversals'] == 4450 and
       new_order['reversal_signature_sha256'] == old_order['reversal_signature_sha256'], 'F46_4450_RECORD_MISMATCH')
  f46.write_private(output / 'headers.jsonl', b''.join(canonical(asdict(x)) for x in stamps))
  f46.write_private(output / 'recorded_commands.jsonl', command_bytes)
  f46.write_private(output / 'reader.json', canonical({
    'raw_sha256': f46.RAW_SHA, 'recorded_source': f46.SOURCE_COMMIT, 'source_manifest_sha256': f46.MANIFEST_SHA,
    'binding': binding, 'command_count': len(commands), 'command_sha256': sha(command_bytes),
    'original_4450_signature': new_order['reversal_signature_sha256'], 'original_4450_records_verified': True,
    'implementation_sha256': sha(Path(__file__).read_bytes()), 'nominal_frequencies_hz': nominal_frequencies(args.source_root),
  }))


class PrivateParser(argparse.ArgumentParser):
  def error(self, message):
    raise ValueError('INVALID_ARGUMENTS')


def _main():
  parser = PrivateParser(prog='f47', description=__doc__)
  for name in ('raw', 'source-root', 'source-manifest', 'f46-tape', 'output'):
    parser.add_argument('--' + name, required=True)
  parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
  parser.add_argument('--output-dir-fd', type=int, help=argparse.SUPPRESS)
  parser.add_argument('--worker-proof-fd', type=int, help=argparse.SUPPRESS)
  output, owned, secure = None, False, None
  try:
    args = parser.parse_args()
    f46 = base()
    secure = f46.security()
    location = f46.validate_output(args.output)
    if args.worker:
      output = secure.from_worker(location, args.output_dir_fd, args.worker_proof_fd)
      with secure.private_decoder():
        decode(args, output)
      return 0
    need(args.output_dir_fd is None and args.worker_proof_fd is None, 'WORKER_OWNERSHIP_REQUIRED')
    output = secure.SecureDirectory.create(location)
    owned = True
    command = [sys.executable, '-B', str(Path(__file__).resolve()), '--worker', *sys.argv[1:]]
    result = secure.run_worker(command, output, timeout=180)
    if result.returncode:
      raise ValueError(secure.worker_error(result.stdout, 'F47_IMPLEMENTATION_FAIL:', f46.PUBLIC_ERROR_CODES))
    reader = json.loads(f46.read_regular(output / 'reader.json'))
    stamps = tuple(Stamp(**json.loads(line)) for line in f46.read_regular(output / 'headers.jsonl').splitlines())
    summary, rows = characterize(stamps, reader['binding'], reader['nominal_frequencies_hz'])
    summary.update({'schema': 'CYBERPILOT_F47_RECORDED_INPUT_CANDIDATES_V1', 'dataset': 'F41-C01',
                    'source_commit': f46.SOURCE_COMMIT, 'raw_sha256': f46.RAW_SHA,
                    'source_manifest_sha256': f46.MANIFEST_SHA, 'implementation_sha256': sha(Path(__file__).read_bytes()),
                    'preserved_command_sha256': reader['command_sha256'],
                    'original_4450_records_verified': reader['original_4450_records_verified'],
                    'D2': 'PERFORMANCE_NOT_EVALUATED', 'F19': 'LEGACY_UNRESOLVED', 'runtime': 'NO_GO'})
    f46.write_private(output / 'binding_rows.jsonl', b''.join(canonical(x) for x in rows))
    f46.write_private(output / 'summary.json', canonical(summary))
    names = ('headers.jsonl', 'recorded_commands.jsonl', 'binding_rows.jsonl', 'reader.json', 'summary.json')
    f46.write_private(output / 'result_sha256.json', canonical({n: sha(f46.read_regular(output / n)) for n in names}))
    print('F47_IMPLEMENTATION_PASS')
    return 0
  except Exception as error:
    code = secure.error_code(error, base().PUBLIC_ERROR_CODES) if secure is not None else (
      'INVALID_ARGUMENTS' if isinstance(error, ValueError) and error.args == ('INVALID_ARGUMENTS',)
      else 'UNEXPECTED_INTERNAL_ERROR')
    if owned and output is not None:
      try:
        base().write_private(output / 'failure.json', canonical({'status': 'F47_IMPLEMENTATION_FAIL', 'reason': code}))
      except Exception:
        pass
    print('F47_IMPLEMENTATION_FAIL:' + code)
    return 2
  finally:
    if output is not None:
      output.close()


def main():
  try:
    return _main()
  except Exception:
    print('F47_IMPLEMENTATION_FAIL:UNEXPECTED_INTERNAL_ERROR')
    return 2


if __name__ == '__main__':
  sys.exit(main())
